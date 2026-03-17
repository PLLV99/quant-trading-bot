# AntiGravity — Algorithmic Trading System

> **Portfolio Project** — A complete algorithmic trading system built from scratch, demonstrating quantitative finance, risk management, and software engineering skills.

## Overview

AntiGravity is a Python-based algorithmic trading bot that implements a **Pullback Sniper** strategy on Gold (XAUUSDm) and Bitcoin (BTCUSDm) via MetaTrader 5. The system features ATR-based dynamic stop-loss/take-profit, multi-timeframe trend confirmation, and institutional-grade risk management.

### Key Features

- **Pullback Strategy Engine** — 5-condition entry (ADX, EMA crossover, RSI filter, price proximity, ATR-based SL/TP)
- **Risk Management** — Position sizing, daily drawdown limits, max loss caps, losing streak detection
- **Backtesting Engine** — Professional analytics with Sharpe/Sortino/Calmar ratios, Monte Carlo simulation
- **Live Execution** — MT5 API integration for real-time trading

## Architecture (Pipeline)

```
┌─────────┐   ┌──────────┐   ┌────────────┐   ┌───────────┐
│  DATA   │──▶│  SIGNAL  │──▶│    RISK    │──▶│ EXECUTION │
│  Layer  │   │  Layer   │   │   Layer    │   │   Layer   │
└─────────┘   └──────────┘   └────────────┘   └───────────┘
```

```
quant-trading-bot/
├── config.py                 # Strategy parameters & risk settings
├── main.py                   # Entry point
│
├── core/                     # Pipeline Architecture
│   ├── data/                 # Data Layer
│   │   ├── mt5_connector.py  # MetaTrader 5 API wrapper
│   │   └── data_loader.py    # Historical data fetching
│   ├── signals/              # Signal Layer
│   │   └── strategy_engine.py # Pullback Sniper v2.0
│   ├── risk/                 # Risk Layer
│   │   └── risk_manager.py   # Position sizing & drawdown control
│   └── analytics/            # Analytics Layer
│       ├── backtester.py     # Backtesting engine + Monte Carlo
│       └── paper_trader.py   # Paper trading simulator
│
├── scripts/                  # Executable scripts
│   └── run_backtest_v2.py    # Run backtests with full analytics
│
├── tests/                    # Unit tests
│   ├── test_strategy_v2.py
│   ├── test_risk.py
│   └── test_backtest.py
│
└── docs/                     # Documentation
    └── CHANGELOG.md
```

## Strategy: Pullback Sniper v2.0

Entry conditions (ALL must be true):
1. **ADX > 20** — Strong trend confirmed
2. **Price > EMA200** — Long-term uptrend
3. **EMA18 > EMA35** — Short-term momentum
4. **RSI 35–65** — Not overbought/oversold
5. **Price within 0.5× ATR of EMA18** — Pullback to value

Risk management:
- **Stop Loss:** 1.5× ATR below entry
- **Take Profit:** 4.5× ATR above entry (R:R = 1:3)
- **Risk per trade:** 2% of account

## Backtesting Engine

The backtesting engine provides institutional-grade analytics:

| Metric | Description |
|--------|-------------|
| Sharpe Ratio | Risk-adjusted returns (annualized) |
| Sortino Ratio | Downside-risk-adjusted returns |
| Calmar Ratio | CAGR / Max Drawdown |
| Monte Carlo | 500 random path simulations |
| Win Rate | Percentage of profitable trades |
| Profit Factor | Gross profit / Gross loss |
| Expectancy | Expected P&L per trade |

```bash
python scripts/run_backtest_v2.py
```

## Lessons Learned

This project was tested with real capital on a demo account ($300 initial balance, 223 trades over 2.5 months). Key findings:

- **Position sizing constraints**: Minimum lot sizes (0.01) on Gold created 32% risk-per-trade on small accounts, far exceeding the intended 2%. Capital requirements must be factored into strategy design.
- **Asset-specific performance**: The strategy performed well on Gold (clean trends) but poorly on Bitcoin (choppy, news-driven).
- **Strategy is not a product until capital-matched**: A profitable strategy on paper can lose money in practice due to broker constraints.

## Tech Stack

- **Language:** Python 3.10+
- **Broker API:** MetaTrader 5
- **Analysis:** pandas, NumPy, matplotlib
- **Testing:** pytest

## License

MIT
