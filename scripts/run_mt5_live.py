"""
AntiGravity Trading Bot - LIVE MT5 Edition
Version 4.0 - "Pullback Sniper" (Trend Following v2.0)

v2.0 Strategy Redesign:
- ENTRY: Pullback to EMA18 (not EMA crossover)
- TIMEFRAME: H4 (was H1) - less noise, better signals
- R:R: 1:3 (SL 1.5x ATR, TP 4.5x ATR)
- FILTER: RSI pullback zone (35-65) + ADX > 20
- TRAILING: 4-level profit lock system
"""

import sys
import os
import time
import logging
from datetime import datetime
import pandas as pd
import MetaTrader5 as mt5

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.console import use_utf8_stdio

use_utf8_stdio()

import config
from core.data.mt5_connector import MT5Connector
from core.signals.strategy_engine import StrategyEngine
from core.risk.lot_sizing import size_position
from core.risk.risk_manager import RiskManager

# =============================================================================
# CONFIGURATION
# =============================================================================
PORTFOLIO = [
    {
        "symbol": "XAUUSDm",
        "mode": "gold_ha",
        "timeframe": mt5.TIMEFRAME_H4,  # v2.0: H4 (was H1)
    },  # Gold
    # Silver REMOVED - Contract size too large for small accounts
    {
        "symbol": "BTCUSDm",
        "mode": "gold_ha",
        "timeframe": mt5.TIMEFRAME_H4,  # v2.0: H4 (was H1)
    },  # Bitcoin
]

# --- PERSONAL GROWTH SAFETY ---
# The connector never sends login credentials: it attaches to whichever account
# the MT5 terminal is already signed into. That is convenient and keeps secrets
# out of the repo, but it also means a stray login is the only thing standing
# between this script and real orders. Refuse to start unless the account says
# it is a demo, and make going live something you have to opt into on purpose.
ALLOW_REAL_MONEY = False

# How far past the intended risk the smallest legal position may go before a
# trade is skipped entirely. See core/risk/lot_sizing.py.
MAX_RISK_OVERSHOOT = 1.5

MAX_TOTAL_POSITIONS = 3  # Max 3 positions
MAX_PER_SYMBOL = 1  # Max 1 position per symbol
COOLDOWN_MINUTES = 240  # v2.0: 4 hours (H4 candle period)
CHECK_INTERVAL_SEC = 60  # Check every minute
EMERGENCY_MAX_POSITIONS = 6  # Halt if exceeded

# --- RISK/REWARD v2.0 (Pullback Sniper) ---
RISK_PER_TRADE_PERCENT = 0.02  # Risk 2% (Agreed Standard)
SL_ATR_MULT = 1.5  # v2.0: Stop Loss = 1.5x ATR (tighter, pullback entry)
TP_ATR_MULT = 4.5  # v2.0: Take Profit = 4.5x ATR (R:R = 1:3)

# Tracking
last_trade_time = {}
last_signal = {}

# =============================================================================
# LOGGING SETUP
# =============================================================================
os.makedirs("logs", exist_ok=True)
log_file = f"logs/bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger("AntiGravity")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def calculate_lot_size(
    connector, symbol, account_balance, risk_pct, sl_distance, risk_manager=None
):
    """Lot size for one trade, or 0.0 when the trade should be skipped.

    All this does is fetch the broker's constraints and hand them to
    `size_position`, which is shared with the backtester so the two cannot
    drift apart again. It used to clamp up to the minimum lot without checking
    what that lot actually risked, which is how a 2% model came to risk 18% of
    a $300 account on every Gold trade.
    """
    spec = connector.get_instrument_spec(symbol)
    if spec is None:
        logger.error(f"Failed to get instrument spec for {symbol}")
        return 0.0

    risk_pct = (
        getattr(risk_manager, "risk_per_trade_pct", risk_pct)
        if risk_manager
        else risk_pct
    )
    requested_risk = account_balance * risk_pct

    sizing = size_position(requested_risk, sl_distance, spec, MAX_RISK_OVERSHOOT)

    if not sizing.tradeable:
        logger.warning(
            f"[RISK] {symbol} skipped: smallest allowed position risks "
            f"${sizing.risk_amount:.2f} against a ${requested_risk:.2f} budget "
            f"({sizing.overshoot:.1f}x). Reason: {sizing.reason}"
        )
        return 0.0

    logger.info(
        f"[RISK] {symbol} balance ${account_balance:.2f}, risk {risk_pct*100:.1f}% "
        f"= ${requested_risk:.2f} -> {sizing.lot} lots "
        f"(actual ${sizing.risk_amount:.2f})"
    )
    return sizing.lot


def close_positions(connector, symbol, position_type=None):
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return

    for pos in positions:
        if position_type is not None and pos.type != position_type:
            continue

        # Determine opposite type for logging/logic
        type_close = (
            mt5.ORDER_TYPE_SELL
            if pos.type == mt5.ORDER_TYPE_BUY
            else mt5.ORDER_TYPE_BUY
        )

        # USE UNIVERSAL CLOSE (connector handles Hedging/Netting logic)
        connector.close_position(pos.ticket, symbol, pos.volume, type_close)
        logger.info(f"{symbol} CLOSED Ticket #{pos.ticket} (Reversal)")


def manage_trailing_stop():
    """
    v2.0 Trailing Stop - 4-Level Profit Lock System (for 1:3 R:R)

    Level 1: >= 1.0R → SL to Breakeven (entry)
    Level 2: >= 1.5R → SL locks 0.75R profit
    Level 3: >= 2.0R → SL locks 1.5R profit
    Level 4: >= 2.5R → Trail: SL = Price - 1R (dynamic)
    """
    positions = mt5.positions_get()
    if not positions:
        return

    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        entry_price = pos.price_open
        current_sl = pos.sl
        current_tp = pos.tp
        current_price = pos.price_current
        pos_type = pos.type  # 0 = BUY, 1 = SELL

        # Skip if no SL set
        if current_sl == 0:
            continue

        # Calculate R (risk distance) from original SL
        if pos_type == mt5.ORDER_TYPE_BUY:
            original_risk = entry_price - current_sl  # For BUY, SL is below entry
            current_profit_distance = current_price - entry_price
        else:  # SELL
            original_risk = current_sl - entry_price  # For SELL, SL is above entry
            current_profit_distance = entry_price - current_price

        # Skip if original_risk is invalid (SL already moved past entry)
        if original_risk <= 0:
            continue

        # Calculate current R multiple
        r_multiple = current_profit_distance / original_risk

        # Get symbol info for tick size
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            continue
        tick_size = symbol_info.trade_tick_size

        new_sl = None
        level_name = ""

        # === LEVEL 1: BREAKEVEN at 1R ===
        if r_multiple >= 1.0:
            if pos_type == mt5.ORDER_TYPE_BUY:
                breakeven_sl = entry_price + (tick_size * 5)
                if current_sl < breakeven_sl:
                    new_sl = breakeven_sl
                    level_name = "BREAKEVEN"
            else:
                breakeven_sl = entry_price - (tick_size * 5)
                if current_sl > breakeven_sl:
                    new_sl = breakeven_sl
                    level_name = "BREAKEVEN"

        # === LEVEL 2: LOCK 0.75R at 1.5R ===
        if r_multiple >= 1.5:
            if pos_type == mt5.ORDER_TYPE_BUY:
                lock_sl = entry_price + (original_risk * 0.75)
                if lock_sl > current_sl:
                    new_sl = lock_sl
                    level_name = "LOCK 0.75R"
            else:
                lock_sl = entry_price - (original_risk * 0.75)
                if lock_sl < current_sl:
                    new_sl = lock_sl
                    level_name = "LOCK 0.75R"

        # === LEVEL 3: LOCK 1.5R at 2R ===
        if r_multiple >= 2.0:
            if pos_type == mt5.ORDER_TYPE_BUY:
                lock_sl = entry_price + (original_risk * 1.5)
                if lock_sl > current_sl:
                    new_sl = lock_sl
                    level_name = "LOCK 1.5R"
            else:
                lock_sl = entry_price - (original_risk * 1.5)
                if lock_sl < current_sl:
                    new_sl = lock_sl
                    level_name = "LOCK 1.5R"

        # === LEVEL 4: DYNAMIC TRAIL at 2.5R+ ===
        if r_multiple >= 2.5:
            if pos_type == mt5.ORDER_TYPE_BUY:
                trailing_sl = current_price - original_risk
                if trailing_sl > current_sl:
                    new_sl = trailing_sl
                    level_name = f"TRAIL {r_multiple:.1f}R"
            else:
                trailing_sl = current_price + original_risk
                if trailing_sl < current_sl:
                    new_sl = trailing_sl
                    level_name = f"TRAIL {r_multiple:.1f}R"

        # === APPLY NEW SL ===
        if new_sl is not None:
            new_sl = round(new_sl / tick_size) * tick_size

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": symbol,
                "sl": new_sl,
                "tp": current_tp,
            }

            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"[{level_name}] {symbol} #{ticket}: SL -> {new_sl:.3f}")
            else:
                error = result.retcode if result else "No result"
                logger.warning(
                    f"[TRAIL FAIL] {symbol} #{ticket}: Could not modify SL. Error: {error}"
                )


# MAIN BOT LOGIC
# =============================================================================
def account_is_tradeable(connector) -> bool:
    """Refuse to trade anything but a demo account, unless told otherwise.

    trade_mode is reported by the terminal: 0 = demo, 1 = contest, 2 = real.
    """
    account = connector.get_account_info()
    if account is None:
        logger.error("Connected, but the terminal returned no account info.")
        return False

    if account.trade_mode != 0 and not ALLOW_REAL_MONEY:
        kind = {1: "contest", 2: "REAL MONEY"}.get(account.trade_mode, "unknown")
        logger.critical(
            f"Refusing to start: account {account.login} on {account.server} is a "
            f"{kind} account (trade_mode={account.trade_mode}). "
            f"Set ALLOW_REAL_MONEY = True if this is deliberate."
        )
        return False

    if not account.trade_allowed:
        logger.error(
            f"Account {account.login} has trading disabled. Enable Algo Trading "
            f"in the terminal toolbar, or check that the account is not read-only."
        )
        return False

    label = "demo" if account.trade_mode == 0 else f"trade_mode={account.trade_mode}"
    logger.info(
        f"Account {account.login} ({account.server}) confirmed {label} — "
        f"balance ${account.balance:,.2f}"
    )
    return True


def run_live_bot():
    logger.info("=" * 60)
    logger.info("AntiGravity Bot v4.0 - PULLBACK SNIPER")
    logger.info(
        f"Mode: Pullback Sniper v2.0 (Risk {RISK_PER_TRADE_PERCENT*100}%, RR 1:3, H4)"
    )
    logger.info(f"Portfolio: {[p['symbol'] for p in PORTFOLIO]}")
    logger.info("=" * 60)

    connector = MT5Connector()
    if not connector.connect():
        logger.error("Failed to connect!")
        return

    if not account_is_tradeable(connector):
        connector.shutdown()
        return

    # Use config risk params (already updated for Personal mode)
    risk_manager = RiskManager(config.RISK_PARAMS)

    engines = {}
    for p in PORTFOLIO:
        engines[p["symbol"]] = StrategyEngine(p["symbol"], risk_manager)

    logger.info("System Active. Good luck!")

    try:
        while True:
            # --- SAFETY CHECK (Every Loop) ---
            account_info = connector.get_account_info()
            if account_info:
                equity = account_info.equity
                balance = account_info.balance

                # Check Daily Limits (Pass EQUITY to capture floating loss)
                allowed, reason = risk_manager.check_daily_status(equity)

                if not allowed:
                    if reason == "DAILY_LOSS_LIMIT":
                        logger.critical(
                            f"🛑 DAILY LOSS LIMIT HIT! Equity: ${equity:.2f} (Hard Close Active)"
                        )
                        # Force Close ALL Positions
                        for asset in PORTFOLIO:
                            close_positions(connector, asset["symbol"])

                        logger.critical("Sleeping for 1 hour to prevent re-entry...")
                        time.sleep(3600)
                        continue

                    elif reason == "DAILY_PROFIT_TARGET":
                        logger.info(f"🎉 Daily Profit Target Hit! Locking in gains.")
                        # Logic to close or just stop new trades?
                        # Default: Stop new trades, let trails run?
                        # Simple version: Close all (Take Profit)
                        # But user wants "Let Run", so maybe we don't close here?
                        # Config has Profit Target 50% (unreachable), so this block strictly won't hit.
                        pass

            # --- TRAILING STOP & BREAKEVEN (Every Loop) ---
            manage_trailing_stop()

            for asset in PORTFOLIO:
                symbol = asset["symbol"]
                mode = asset["mode"]
                tf = asset["timeframe"]
                strategy = engines[symbol]

                df = connector.fetch_candles(symbol, timeframe=tf, limit=300)
                if df.empty:
                    continue

                full_data = strategy.add_indicators(df)
                current_row = full_data.iloc[-1]
                current_price = current_row["close"]
                atr = current_row["atr"]
                # balance = connector.get_balance() # Already got above

                # Determine Position State
                positions = mt5.positions_get(symbol=symbol)
                has_long = (
                    any(p.type == mt5.ORDER_TYPE_BUY for p in positions)
                    if positions
                    else False
                )
                has_short = (
                    any(p.type == mt5.ORDER_TYPE_SELL for p in positions)
                    if positions
                    else False
                )

                # Generate Signal
                signal = strategy.generate_signal(
                    current_price, current_row, balance, mode
                )
                action = signal["action"]

                ts = datetime.now().strftime("%H:%M:%S")

                # De-dupe signals
                if action == last_signal.get(symbol) and action != "hold":
                    continue
                last_signal[symbol] = action

                # GLOBAL SAFETY CHECK (Redundant but safe)
                if not allowed:
                    continue

                # === EXECUTION LOGIC ===

                # BUY (Long)
                if action == "buy_signal":
                    if has_long:
                        continue

                    logger.info(f"[{ts}] {symbol} >>> LONG SIGNAL")
                    if has_short:
                        close_positions(connector, symbol, mt5.ORDER_TYPE_SELL)

                    # Cooldown check
                    now = time.time()
                    if (now - last_trade_time.get(symbol, 0)) / 60 < COOLDOWN_MINUTES:
                        logger.info(f"   Blocked: Cooldown")
                        continue

                    # Dynamic Sizing with Max Loss Cap (v1.2 FIX)
                    sl_dist = atr * SL_ATR_MULT
                    lot_size = calculate_lot_size(
                        connector, symbol, balance, RISK_PER_TRADE_PERCENT,
                        sl_dist, risk_manager,
                    )

                    if lot_size <= 0:
                        continue

                    sl = current_price - sl_dist
                    tp = current_price + (atr * TP_ATR_MULT)

                    res = connector.place_order(
                        symbol, mt5.ORDER_TYPE_BUY, lot_size, sl=sl, tp=tp
                    )
                    if res:
                        logger.info(f"   SUCCESS LONG: {lot_size} lots")
                        last_trade_time[symbol] = now

                # SELL (Short)
                elif action == "sell_signal":
                    if has_short:
                        continue

                    logger.info(f"[{ts}] {symbol} >>> SHORT SIGNAL")
                    if has_long:
                        close_positions(connector, symbol, mt5.ORDER_TYPE_BUY)

                    now = time.time()
                    if (now - last_trade_time.get(symbol, 0)) / 60 < COOLDOWN_MINUTES:
                        logger.info(f"   Blocked: Cooldown")
                        continue

                    # Dynamic Sizing with Max Loss Cap (v1.2 FIX)
                    sl_dist = atr * SL_ATR_MULT
                    lot_size = calculate_lot_size(
                        connector, symbol, balance, RISK_PER_TRADE_PERCENT,
                        sl_dist, risk_manager,
                    )

                    if lot_size <= 0:
                        continue

                    sl = current_price + sl_dist
                    tp = current_price - (atr * TP_ATR_MULT)

                    res = connector.place_order(
                        symbol, mt5.ORDER_TYPE_SELL, lot_size, sl=sl, tp=tp
                    )
                    if res:
                        logger.info(f"   SUCCESS SHORT: {lot_size} lots")
                        last_trade_time[symbol] = now

            time.sleep(CHECK_INTERVAL_SEC)

    except KeyboardInterrupt:
        logger.info("Stopped.")
    finally:
        connector.shutdown()


if __name__ == "__main__":
    run_live_bot()
