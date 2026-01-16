"""
Portfolio Comparison Backtest - Compares 3 strategies
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


def run_single_backtest(mt5, assets, initial_balance=300.0, days=30):
    """Run backtest on specific assets"""
    total_pnl = 0
    max_dd = 0
    trades = 0

    for asset in assets:
        symbol = asset["symbol"]
        candles = days * 24
        data = mt5.fetch_candles(symbol, limit=candles)

        if data.empty:
            continue

        risk_manager = RiskManager(config.RISK_PARAMS)
        strategy = StrategyEngine(
            symbol=symbol,
            risk_manager=risk_manager,
            config_override=config.STRATEGY_PARAMS,
        )
        backtester = Backtester(
            strategy,
            initial_balance=initial_balance / len(assets),
            strategy_mode="gold_ha",
        )

        try:
            backtester.run(data)
            final = (
                backtester.equity_curve[-1]["equity"]
                if backtester.equity_curve
                else initial_balance / len(assets)
            )
            pnl = final - (initial_balance / len(assets))
            total_pnl += pnl
            trades += len(backtester.trade_history)

            if backtester.equity_curve:
                equities = pd.Series([x["equity"] for x in backtester.equity_curve])
                peaks = equities.cummax()
                dd = ((equities - peaks) / peaks).min() * 100
                if dd < max_dd:
                    max_dd = dd
        except:
            pass

    return total_pnl, max_dd, trades


def main():
    print("=" * 60)
    print("   PORTFOLIO COMPARISON BACKTEST (30 Days)")
    print("=" * 60)

    mt5 = MT5Connector()
    if not mt5.connect():
        print("Cannot connect to MT5")
        return

    initial = 300.0
    days = 30

    # Define portfolios
    portfolios = {
        "A) Gold Only": [{"symbol": "XAUUSDm"}],
        "B) Gold + BTC": [{"symbol": "XAUUSDm"}, {"symbol": "BTCUSDm"}],
        "C) Full": [
            {"symbol": "XAUUSDm"},
            {"symbol": "XAGUSDm"},
            {"symbol": "BTCUSDm"},
            {"symbol": "USOILm"},
        ],
    }

    results = []
    vps_cost = 6.0  # $6/month

    for name, assets in portfolios.items():
        print(f"\nTesting {name}...")
        pnl, dd, trades = run_single_backtest(mt5, assets, initial, days)
        net_profit = pnl - vps_cost
        results.append(
            {
                "Portfolio": name,
                "Gross PnL": f"${pnl:.2f}",
                "VPS Cost": f"-${vps_cost:.2f}",
                "Net Profit": f"${net_profit:.2f}",
                "Max DD": f"{dd:.1f}%",
                "Trades": trades,
                "Worth It?": "YES" if net_profit > 0 else "NO",
            }
        )

    print("\n" + "=" * 60)
    print("                  RESULTS COMPARISON")
    print("=" * 60)
    df = pd.DataFrame(results)
    print(df.to_string(index=False))

    mt5.shutdown()


if __name__ == "__main__":
    main()
