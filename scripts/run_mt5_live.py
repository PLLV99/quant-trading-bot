import sys
import os
import time
import pandas as pd
import MetaTrader5 as mt5

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from modules.mt5_connector import MT5Connector
from modules.strategy_engine import StrategyEngine
from modules.risk_manager import RiskManager

# --- CONFIGURATION ---
PORTFOLIO = [
    {"symbol": "XAUUSDm", "mode": "gold_ha", "timeframe": mt5.TIMEFRAME_M15},
    {"symbol": "EURUSDm", "mode": "gold_ha", "timeframe": mt5.TIMEFRAME_M15},
    {"symbol": "USOILm", "mode": "gold_ha", "timeframe": mt5.TIMEFRAME_M15},  # Oil (Energy sector)
    {"symbol": "BTCUSDm", "mode": "gold_ha", "timeframe": mt5.TIMEFRAME_M15},
]
CHECK_INTERVAL_SEC = 60  # Check every minute


def run_live_bot():
    print(f"\n[LIVE BOT] Launching AntiGravity Multi-Asset Bot...")
    print(f"   Portfolio: {[p['symbol'] for p in PORTFOLIO]}")

    # 1. Initialize Components
    connector = MT5Connector()
    if not connector.connect():
        return

    # Initialize Risk Manager
    risk_manager = RiskManager(config.RISK_PARAMS)

    # Initialize Engine (Reused for logic, symbol updated per loop)
    # We create one engine instance per symbol to keep state if needed
    engines = {}
    for p in PORTFOLIO:
        engines[p["symbol"]] = StrategyEngine(
            symbol=p["symbol"], risk_manager=risk_manager
        )

    print("\n[LIVE BOT] System Active. Waiting for signals... (Press Ctrl+C to Stop)")

    try:
        while True:
            for asset in PORTFOLIO:
                symbol = asset["symbol"]
                mode = asset["mode"]
                tf = asset["timeframe"]
                strategy = engines[symbol]

                # 2. Fetch Data
                df = connector.fetch_candles(symbol, timeframe=tf, limit=300)

                if df.empty:
                    print(f"   [WARNING] No data for {symbol}. Skipping...")
                    continue

                # 3. Calculate Indicators
                full_data = strategy.add_indicators(df)
                current_row = full_data.iloc[-1]
                current_price = current_row["close"]

                # 4. Check Current Positions
                positions = mt5.positions_get(symbol=symbol)
                current_volume = 0.0
                if positions:
                    current_volume = sum([p.volume for p in positions])
                
                # Get Balance for Risk Manager
                current_balance = connector.get_balance()

                # 5. Generate Signal
                signal = strategy.generate_signal(
                    current_price, current_row, current_balance, strategy_mode=mode
                )
                action = signal["action"]
                trend = signal["trend"]

                # Print Heartbeat
                ts = pd.to_datetime(current_row.name).strftime("%H:%M")
                # Only print interesting updates to avoid noise
                # print(f"[{ts}] {symbol} | Price: {current_price:.2f} | Trend: {trend} | Action: {action}")

                # 6. Execute Trade Logic
                if action == "buy_signal":
                    if current_volume == 0:
                        print(f"[{ts}] {symbol} >>> BUY SIGNAL! Executing...")

                        atr = current_row["atr"]
                        volume = 0.01  # Fixed 0.01 for Demo Test

                        # Stop Loss distance (wider for crypto?)
                        sl_mult = 2.0
                        if "BTC" in symbol or "ETH" in symbol:
                            sl_mult = 3.0  # Looser SL for Crypto

                        sl_price = current_price - (atr * sl_mult)

                        res = connector.place_order(
                            symbol, mt5.ORDER_TYPE_BUY, volume, sl=sl_price
                        )
                        if res:
                            print(f"       >>> SUCCESS: Ticket {res.order}")

                elif action == "sell_signal":
                    if current_volume > 0:
                        print(f"[{ts}] {symbol} >>> SELL SIGNAL! Closing...")
                        for pos in positions:
                            type_close = (
                                mt5.ORDER_TYPE_SELL
                                if pos.type == mt5.ORDER_TYPE_BUY
                                else mt5.ORDER_TYPE_BUY
                            )
                            close_price = (
                                mt5.symbol_info_tick(symbol).bid
                                if type_close == mt5.ORDER_TYPE_SELL
                                else mt5.symbol_info_tick(symbol).ask
                            )
                            connector.place_order(
                                symbol, type_close, pos.volume, price=close_price
                            )
                            print(f"       >>> CLOSED: Ticket {pos.ticket}")

            # End of Portfolio Loop
            # Small sleep to yield CPU
            time.sleep(CHECK_INTERVAL_SEC)

    except KeyboardInterrupt:
        print("\n[LIVE BOT] Stopping...")
        connector.shutdown()
    except Exception as e:
        print(f"\n[LIVE BOT] CRITICAL ERROR: {e}")
        connector.shutdown()


if __name__ == "__main__":
    run_live_bot()
