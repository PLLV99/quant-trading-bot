"""
Quick Backtest Script - Fetches data from MT5 and runs strategy tests.
Usage: python scripts/quick_backtest.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.mt5_connector import MT5Connector
from modules.strategy_engine import StrategyEngine
from modules.risk_manager import RiskManager
from modules.backtester import Backtester
import config
import pandas as pd


def run_backtest():
    print("=" * 60)
    print("      ANTIGRAVITY BOT - QUICK BACKTEST (MT5 Data)")
    print("=" * 60)

    # Connect to MT5
    mt5 = MT5Connector()
    if not mt5.connect():
        print("❌ Cannot connect to MT5. Make sure MT5 is open and logged in.")
        return

    # Assets to test
    assets = [
        {"symbol": "XAUUSDm", "name": "Gold"},
        {"symbol": "XAGUSDm", "name": "Silver"},
        {"symbol": "BTCUSDm", "name": "Bitcoin"},
        {"symbol": "USOILm", "name": "Oil"},
    ]

    results = []
    initial_balance = 300.0  # Match user's starting balance

    for asset in assets:
        symbol = asset["symbol"]
        print(f"\n>>> Testing {asset['name']} ({symbol})...")

        # Fetch 12 days of H1 candles (same as live trading period)
        candles = 12 * 24  # 12 days x 24 hours
        data = mt5.fetch_candles(symbol, limit=candles)

        if data.empty:
            print(f"   [Skip] No data for {symbol}")
            continue

        print(f"   📊 Got {len(data)} candles")

        # Setup strategy and backtester
        risk_manager = RiskManager(config.RISK_PARAMS)
        strategy = StrategyEngine(
            symbol=symbol,
            risk_manager=risk_manager,
            config_override=config.STRATEGY_PARAMS,
        )
        backtester = Backtester(
            strategy, initial_balance=initial_balance, strategy_mode="gold_ha"
        )

        # Run backtest
        try:
            backtester.run(data)

            # Collect results
            final_balance = (
                backtester.equity_curve[-1]["equity"]
                if backtester.equity_curve
                else initial_balance
            )
            pnl = final_balance - initial_balance
            ret_pct = (pnl / initial_balance) * 100
            trades = len(backtester.trade_history)

            # Calculate max drawdown
            if backtester.equity_curve:
                equities = pd.Series([x["equity"] for x in backtester.equity_curve])
                peaks = equities.cummax()
                dd = (equities - peaks) / peaks
                max_dd = dd.min() * 100
            else:
                max_dd = 0

            results.append(
                {
                    "Asset": asset["name"],
                    "Symbol": symbol,
                    "Return %": round(ret_pct, 2),
                    "Max DD %": round(max_dd, 2),
                    "Trades": trades,
                    "PnL $": round(pnl, 2),
                }
            )

        except Exception as e:
            print(f"   [Error] {e}")

    # Print results
    print("\n" + "=" * 60)
    print("               BACKTEST RESULTS")
    print("=" * 60)

    if results:
        df = pd.DataFrame(results)
        print(df.to_string(index=False))

        # Total
        total_pnl = sum(r["PnL $"] for r in results)
        total_ret = (total_pnl / (initial_balance * len(results))) * 100
        print("-" * 60)
        print(f"TOTAL PnL: ${total_pnl:.2f} ({total_ret:.2f}%)")
    else:
        print("No results. Check if symbols are correct.")

    mt5.shutdown()


if __name__ == "__main__":
    run_backtest()
