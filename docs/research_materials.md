# Recommended Research Materials for Project Context

## 1. Theoretical Foundations (The "Brain")
*   **"The Kelly Criterion" by Edward Thorp**: Source for our Risk Management (0.5x Fractional Kelly).
*   **"The Original Turtle Trading Rules"**: Source for our ATR-based stops and volatility handling.
*   **"Principles" by Ray Dalio**: Source for "Volatility Targeting" and risk parity concepts.

## 2. Strategy Logic (The "Engine")
*   **"Grid Trading Strategy - A Quantitative Approach"**: Reference for arithmetic vs geometric spacing.
*   **"CCXT Library Documentation"**: Manual for connecting to exchanges.

## 3. Project Context
*   **Current System**: MetaTrader 5 (Exness) - Gold/EUR/Oil/BTC (Sniper Portfolio)
*   **Main Entry Point**: `scripts/run_mt5_live.py` - Live trading bot
*   **Backtesting**: `main.py` - Historical simulation
*   **Strategy**: "Sniper" M15 Strategy (Heikin Ashi + EMA 9/21/50 + RSI)

