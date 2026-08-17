# Quant Trading Bot — Algorithmic Trading System

> **Portfolio Project** — A complete algorithmic trading system built from scratch, demonstrating quantitative finance, risk management, and software engineering skills.

## Overview

A Python-based algorithmic trading system implementing a **Pullback Sniper** strategy on Gold (XAUUSDm) and Bitcoin (BTCUSDm) via MetaTrader 5, with ATR-based dynamic stop-loss and take-profit, multi-timeframe trend confirmation, and layered risk controls.

### Key Features

- **Pullback Strategy Engine** — 5-condition entry (ADX, EMA crossover, RSI filter, price proximity, ATR-based SL/TP)
- **Risk Management** — Position sizing, daily drawdown limits, max loss caps, losing streak detection
- **Backtesting Engine** — Professional analytics with Sharpe/Sortino/Calmar ratios, Monte Carlo simulation
- **Live Execution** — MT5 API integration for real-time trading

## Architecture (Pipeline)

Each stage is a module, and the stage boundary is where the data changes shape:
prices in, a signal out, a signal plus a size out, an order placed.

```
┌────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│    DATA    │──▶│    SIGNAL    │──▶│     RISK     │──▶│  EXECUTION   │
│  MT5 API   │   │  strategy_   │   │    risk_     │   │  run_mt5_    │
│  (OHLC)    │   │  engine.py   │   │  manager.py  │   │   live.py    │
└────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
                  5-filter entry     sizing + limits     orders + trail
```

```
quant-trading-bot/
├── config.py                    # Strategy parameters & risk settings
├── main.py                      # Entry point
│
├── core/
│   ├── signals/
│   │   └── strategy_engine.py   # Pullback Sniper v2.0 — indicators + 5-filter entry
│   ├── risk/
│   │   └── risk_manager.py      # Position sizing, drawdown limits, streak detection
│   └── analytics/
│       ├── backtester.py        # Backtesting engine + Monte Carlo
│       └── paper_trader.py      # Paper trading simulator
│
├── scripts/                     # Executable entry points
│   ├── run_mt5_live.py          # Live execution — MT5 connection, 4-level trailing stop
│   ├── run_backtest_v2.py       # Full backtest with analytics
│   ├── quick_backtest.py        # Fast iteration on strategy parameters
│   └── analyze_report.py        # Post-run trade report analysis
│
├── tests/                       # pytest
│   ├── test_strategy.py         test_strategy_v2.py
│   ├── test_risk.py             test_risk_enhanced.py    test_risk_ftmo.py
│   └── test_backtest.py
│
└── docs/
    ├── CHANGELOG.md
    └── POST_MORTEM_ANALYSIS.md  # Why a 2:1 R:R strategy still lost money
```

> There is no separate `core/data/` module — the MetaTrader 5 connection lives in the
> scripts that need it (`run_mt5_live.py` for live trading, `run_backtest_v2.py` for
> historical data), since that is the only place the broker API is touched.

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

- **Theoretical position sizing ≠ practical position sizing.** The Kelly Criterion and fractional risk models assume infinitely divisible position sizes. In practice, a broker's minimum lot size (0.01) creates a hard floor on risk-per-trade. For Gold, this meant 32% risk-per-trade instead of the intended 2%.
- **Capital-instrument mismatch is the real killer.** The strategy's R:R ratio was sound (avg win $34 vs avg loss $17 = 2:1), but Profit Factor was 0.96 because oversized positions destroyed the edge. Minimum balance for Gold at 2% risk: ~$4,500.
- **Asset-specific performance matters.** Gold produced large wins during trends (+$208, +$424) but catastrophic losses during volatility spikes (-$355). Bitcoin was more capital-appropriate but had lower win rate (37%).
- **A 1.5× ATR stop-loss is useless if the minimum pip value forces 100% portfolio risk.** Risk management must account for the minimum viable execution size of each instrument.

## Tech Stack

- **Language:** Python 3.10+
- **Broker API:** MetaTrader 5
- **Analysis:** pandas, NumPy, matplotlib
- **Testing:** pytest

## License

MIT
