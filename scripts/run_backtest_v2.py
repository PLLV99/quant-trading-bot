"""
AntiGravity Backtesting Engine v2.0
Run: python scripts/run_backtest_v2.py

Runs v2.0 Pullback Sniper strategy against MT5 historical data.
Generates professional performance report with Monte Carlo analysis.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import config
from modules.strategy_engine import StrategyEngine
from modules.risk_manager import RiskManager
from modules.backtester import Backtester

# ═══════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════
INITIAL_BALANCE = 10000.0
SL_ATR_MULT = 1.5  # v2.0: Stop Loss = 1.5x ATR
TP_ATR_MULT = 4.5  # v2.0: Take Profit = 4.5x ATR (R:R = 1:3)
STRATEGY_MODE = "gold_ha"
BACKTEST_DAYS = 90  # 3 months of data


def generate_sample_data(days=90, asset="gold"):
    """
    Generate realistic synthetic OHLCV data for backtesting
    when MT5 is not available.
    """
    np.random.seed(42)  # Reproducible results
    periods = days * 6  # H4 = 6 candles per day

    if asset == "gold":
        base_price = 2000.0
        volatility = 15.0  # ~$15 per H4 candle
    elif asset == "btc":
        base_price = 40000.0
        volatility = 500.0
    else:
        base_price = 100.0
        volatility = 2.0

    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq="4h")

    # Generate trending + mean-reverting price series
    trend = np.cumsum(np.random.randn(periods) * 0.3) * volatility * 0.1
    noise = np.random.randn(periods) * volatility
    mean_revert = np.zeros(periods)
    for i in range(1, periods):
        mean_revert[i] = mean_revert[i - 1] * 0.95 + noise[i] * 0.3

    closes = base_price + trend + mean_revert

    # Generate OHLCV from close
    df = pd.DataFrame(index=dates)
    df["close"] = closes
    df["open"] = df["close"].shift(1).fillna(base_price)

    # High/Low with realistic wicks
    wick_size = volatility * 0.5 * np.abs(np.random.randn(periods))
    df["high"] = df[["open", "close"]].max(axis=1) + wick_size
    df["low"] = df[["open", "close"]].min(axis=1) - wick_size
    df["volume"] = np.random.randint(1000, 10000, periods)

    return df


def try_load_mt5_data(symbol="XAUUSDm", timeframe_h4=True, days=90):
    """Attempt to load data from MT5 if available."""
    try:
        import MetaTrader5 as mt5

        if not mt5.initialize():
            return None

        if timeframe_h4:
            tf = mt5.TIMEFRAME_H4
        else:
            tf = mt5.TIMEFRAME_H1

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, days * 6)
        mt5.shutdown()

        if rates is None:
            return None

        df = pd.DataFrame(rates)
        df["datetime"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("datetime", inplace=True)
        df.rename(columns={"tick_volume": "volume"}, inplace=True)
        return df[["open", "high", "low", "close", "volume"]]
    except Exception:
        return None


def main():
    print("═" * 50)
    print("  AntiGravity Backtest Engine v2.0")
    print("  Strategy: Pullback Sniper (R:R 1:3)")
    print("═" * 50)

    # Try MT5 first, fall back to synthetic data
    print("\n  Loading data...")
    data = try_load_mt5_data("XAUUSDm", days=BACKTEST_DAYS)

    if data is not None:
        print(f"  ✅ Loaded {len(data)} candles from MT5 (XAUUSDm H4)")
        data_source = "MT5 Live Data"
    else:
        print("  ⚠️  MT5 not available — using synthetic Gold data")
        data = generate_sample_data(days=BACKTEST_DAYS, asset="gold")
        data_source = "Synthetic Data (seed=42)"

    print(f"  Source: {data_source}")
    print(f"  Period: {data.index[0].date()} → {data.index[-1].date()}")

    # Setup
    risk_manager = RiskManager(config.RISK_PARAMS)
    strategy_engine = StrategyEngine(
        symbol="XAUUSDm",
        risk_manager=risk_manager,
        config_override=config.STRATEGY_PARAMS,
    )

    backtester = Backtester(
        strategy_engine,
        initial_balance=INITIAL_BALANCE,
        verbose=True,
        strategy_mode=STRATEGY_MODE,
        sl_atr_mult=SL_ATR_MULT,
        tp_atr_mult=TP_ATR_MULT,
    )

    # Run
    backtester.run(data)

    # Export trade log
    if backtester.analyzer and backtester.analyzer.trade_pnls:
        df_trades = pd.DataFrame(backtester.analyzer.trade_pnls)
        trade_log_path = os.path.join(
            os.path.dirname(__file__), "..", "backtest_trades.csv"
        )
        df_trades.to_csv(trade_log_path, index=False)
        print(f"\n  Trade log saved: {os.path.abspath(trade_log_path)}")

    print("\n  Backtest complete. ✅")


if __name__ == "__main__":
    main()
