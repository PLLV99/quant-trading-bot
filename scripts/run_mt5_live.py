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

# defaults to cp1252 and raises UnicodeEncodeError on the first line printed,
# so force UTF-8 rather than stripping the output back to ASCII.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The reports below use box-drawing characters and emoji. A Windows console
# defaults to cp1252 and raises UnicodeEncodeError on the first line printed,
# so force UTF-8 rather than stripping the output back to ASCII.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config
from core.data.mt5_connector import MT5Connector
from core.signals.strategy_engine import StrategyEngine
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
    symbol, account_balance, risk_pct, sl_distance, risk_manager=None
):
    """
    Calculates dynamic lot size based on Risk %.
    v1.3.1: FIXED - Always use 2% of balance (removed fixed $50 cap)

    For $198 balance: Max loss = $3.96 per trade
    For $500 balance: Max loss = $10 per trade
    """
    if sl_distance == 0:
        return 0.01

    # v1.3.1 FIX: ONLY use percentage, no fixed dollar cap
    if risk_manager:
        risk_pct_from_config = getattr(risk_manager, "risk_per_trade_pct", 0.02)
    else:
        risk_pct_from_config = risk_pct

    # Risk amount = 2% of balance (dynamic, not fixed!)
    risk_amount = account_balance * risk_pct_from_config

    logger.info(
        f"[RISK] Balance: ${account_balance:.2f}, Risk {risk_pct_from_config*100:.1f}% = ${risk_amount:.2f}"
    )

    # Get Contract Size
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        logger.error(f"Failed to get info for {symbol}")
        return 0.01

    contract_size = symbol_info.trade_contract_size
    min_lot = symbol_info.volume_min
    max_lot = symbol_info.volume_max
    step_lot = symbol_info.volume_step

    # Formula: Volume = Risk / (ContractSize * SL_Price_Diff)
    raw_lot = risk_amount / (contract_size * sl_distance)

    # Round to step
    lot = round(raw_lot / step_lot) * step_lot

    # Cap limits
    lot = max(min_lot, min(lot, max_lot))

    # v1.3.1: Stricter safety cap for small accounts
    if account_balance < 300 and lot > 0.02:
        logger.warning(f"[SAFETY] Small account cap: {lot:.2f} -> 0.02 lots")
        lot = 0.02
    elif account_balance < 500 and lot > 0.05:
        logger.warning(f"[SAFETY] Medium account cap: {lot:.2f} -> 0.05 lots")
        lot = 0.05

    return lot


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
                        symbol, balance, RISK_PER_TRADE_PERCENT, sl_dist, risk_manager
                    )

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
                        symbol, balance, RISK_PER_TRADE_PERCENT, sl_dist, risk_manager
                    )

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
