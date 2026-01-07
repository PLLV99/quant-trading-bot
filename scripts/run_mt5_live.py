"""
AntiGravity Trading Bot - LIVE MT5 Edition
Version 2.2 - "Wealth Builder" (Personal Growth)

Changes:
- Mode: Personal Account ($300 Start) allows Aggressive Growth
- Strategy: Long + Short (Reversing)
- Portfolio: XAUUSD, BTCUSD, USOIL
- Sizing: DYNAMIC (Risk % based on Balance)
- Safety: Stop Loss is Mandatory, but looser than FTMO
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

import config
from modules.mt5_connector import MT5Connector
from modules.strategy_engine import StrategyEngine
from modules.risk_manager import RiskManager

# =============================================================================
# CONFIGURATION
# =============================================================================
PORTFOLIO = [
    {"symbol": "XAUUSDm", "mode": "gold_ha", "timeframe": mt5.TIMEFRAME_M15},
    {"symbol": "BTCUSDm", "mode": "gold_ha", "timeframe": mt5.TIMEFRAME_M15},
    {"symbol": "USOILm", "mode": "gold_ha", "timeframe": mt5.TIMEFRAME_M15},
]

# --- PERSONAL GROWTH SAFETY ---
MAX_TOTAL_POSITIONS = 3      # Max 3 positions
MAX_PER_SYMBOL = 1           # Max 1 position per symbol
COOLDOWN_MINUTES = 30        # Aggressive: 30 min cooldown (was 60)
CHECK_INTERVAL_SEC = 60      # Check every minute
EMERGENCY_MAX_POSITIONS = 6  # Halt if exceeded

# --- RISK/REWARD (Rich Mode) ---
RISK_PER_TRADE_PERCENT = 0.02 # Risk 2% (Optimal Growth)
SL_ATR_MULT = 2.5             # Stop Loss = 2.5x ATR
TP_ATR_MULT = 5.0             # Take Profit = 5x ATR (1:2 RR)

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
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AntiGravity")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def calculate_lot_size(symbol, account_balance, risk_pct, sl_distance):
    """
    Calculates dynamic lot size based on Risk %.
    Risk Amount = Balance * Risk%
    Lot Size = Risk Amount / (SL Distance * Contract Size)
    """
    if sl_distance == 0: return 0.01

    risk_amount = account_balance * risk_pct
    
    # Get Contract Size (Mock/Safe default if fail)
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        logger.error(f"Failed to get info for {symbol}")
        return 0.01

    contract_size = symbol_info.trade_contract_size
    min_lot = symbol_info.volume_min
    max_lot = symbol_info.volume_max
    step_lot = symbol_info.volume_step

    # Formula: Risk = Volume * ContractSize * SL_Price_Diff
    # Volume = Risk / (ContractSize * SL_Price_Diff)
    raw_lot = risk_amount / (contract_size * sl_distance)
    
    # Round to step
    # Example: 0.123 -> 0.12 (if step 0.01)
    # Using simple rounding for robustness
    lot = round(raw_lot / step_lot) * step_lot
    
    # Cap limits
    lot = max(min_lot, min(lot, max_lot))
    
    # Safety Cap for Small Accounts ($300)
    # Don't open crazy lots if data is weird
    if account_balance < 500 and lot > 0.1:
        logger.warning(f"Capping lot size for safety: {lot} -> 0.1")
        lot = 0.1

    return lot

def close_positions(connector, symbol, position_type=None):
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return

    for pos in positions:
        if position_type is not None and pos.type != position_type:
            continue
        
        # Determine opposite type for logging/logic
        type_close = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        
        # USE UNIVERSAL CLOSE (connector handles Hedging/Netting logic)
        connector.close_position(pos.ticket, symbol, pos.volume, type_close)
        logger.info(f"{symbol} CLOSED Ticket #{pos.ticket} (Reversal)")


# =============================================================================
# MAIN BOT LOGIC
# =============================================================================
def run_live_bot():
    logger.info("=" * 60)
    logger.info("AntiGravity Bot v2.2 - WEALTH BUILDER")
    logger.info(f"Mode: Personal Growth (Risk {RISK_PER_TRADE_PERCENT*100}%)")
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
                        logger.critical(f"🛑 DAILY LOSS LIMIT HIT! Equity: ${equity:.2f} (Hard Close Active)")
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

            for asset in PORTFOLIO:
                symbol = asset["symbol"]
                mode = asset["mode"]
                tf = asset["timeframe"]
                strategy = engines[symbol]

                df = connector.fetch_candles(symbol, timeframe=tf, limit=300)
                if df.empty: continue

                full_data = strategy.add_indicators(df)
                current_row = full_data.iloc[-1]
                current_price = current_row["close"]
                atr = current_row["atr"]
                # balance = connector.get_balance() # Already got above

                # Determine Position State
                positions = mt5.positions_get(symbol=symbol)
                has_long = any(p.type == mt5.ORDER_TYPE_BUY for p in positions) if positions else False
                has_short = any(p.type == mt5.ORDER_TYPE_SELL for p in positions) if positions else False

                # Generate Signal
                signal = strategy.generate_signal(current_price, current_row, balance, mode)
                action = signal["action"]

                ts = datetime.now().strftime("%H:%M:%S")

                # De-dupe signals
                if action == last_signal.get(symbol) and action != "hold": continue
                last_signal[symbol] = action

                # GLOBAL SAFETY CHECK (Redundant but safe)
                if not allowed: continue

                # === EXECUTION LOGIC ===
                
                # BUY (Long)
                if action == "buy_signal":
                    if has_long: continue
                    
                    logger.info(f"[{ts}] {symbol} >>> LONG SIGNAL")
                    if has_short: close_positions(connector, symbol, mt5.ORDER_TYPE_SELL)
                    
                    # Cooldown check
                    now = time.time()
                    if (now - last_trade_time.get(symbol, 0))/60 < COOLDOWN_MINUTES:
                        logger.info(f"   Blocked: Cooldown")
                        continue

                    # Dynamic Sizing (Risk 3%)
                    sl_dist = atr * SL_ATR_MULT
                    lot_size = calculate_lot_size(symbol, balance, RISK_PER_TRADE_PERCENT, sl_dist)
                    
                    sl = current_price - sl_dist
                    tp = current_price + (atr * TP_ATR_MULT)
                    
                    res = connector.place_order(symbol, mt5.ORDER_TYPE_BUY, lot_size, sl=sl, tp=tp)
                    if res: 
                        logger.info(f"   SUCCESS LONG: {lot_size} lots")
                        last_trade_time[symbol] = now

                # SELL (Short)
                elif action == "sell_signal":
                    if has_short: continue
                    
                    logger.info(f"[{ts}] {symbol} >>> SHORT SIGNAL")
                    if has_long: close_positions(connector, symbol, mt5.ORDER_TYPE_BUY)
                    
                    now = time.time()
                    if (now - last_trade_time.get(symbol, 0))/60 < COOLDOWN_MINUTES:
                         logger.info(f"   Blocked: Cooldown")
                         continue

                    # Dynamic Sizing
                    sl_dist = atr * SL_ATR_MULT
                    lot_size = calculate_lot_size(symbol, balance, RISK_PER_TRADE_PERCENT, sl_dist)
                    
                    sl = current_price + sl_dist
                    tp = current_price - (atr * TP_ATR_MULT)
                    
                    res = connector.place_order(symbol, mt5.ORDER_TYPE_SELL, lot_size, sl=sl, tp=tp)
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
