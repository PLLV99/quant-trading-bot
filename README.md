# Quant Trading Bot — Algorithmic Trading System

> **Portfolio Project** — A complete algorithmic trading system built from scratch, demonstrating quantitative finance, risk management, and software engineering skills.

## Overview

A Python-based algorithmic trading system implementing a **Pullback Sniper** strategy on Gold (XAUUSDm) and Bitcoin (BTCUSDm) via MetaTrader 5, with ATR-based dynamic stop-loss and take-profit, multi-timeframe trend confirmation, and layered risk controls.

### Key Features

- **Pullback Strategy Engine** — 5-condition entry (ADX, EMA crossover, RSI filter, price proximity, ATR-based SL/TP)
- **Risk Management** — Position sizing, daily drawdown limits, max loss caps, losing streak detection
- **Backtesting Engine** — Professional analytics with Sharpe/Sortino/Calmar ratios, Monte Carlo simulation
- **Live Execution** — MT5 API integration for real-time trading

## Quick Start

Dependencies are managed with [uv](https://docs.astral.sh/uv/), which fetches the
right Python (3.14) for you:

```bash
uv sync --extra mt5
```

Run the backtest:

```bash
uv run python scripts/run_backtest_v2.py
```

Run the tests:

```bash
uv run python -m pytest tests/ -q
```

`--extra mt5` installs the MetaTrader 5 bindings. They are Windows-only and need
the MT5 terminal installed and signed in — the connector attaches to whatever
account the terminal already holds, so there are no credentials to store. Drop
the extra and everything except live trading still works: the backtester falls
back to synthetic Gold data.

If uv reports `invalid peer certificate: UnknownIssuer`, your network is
intercepting TLS — add `--native-tls` to each command so uv trusts the Windows
certificate store.

### Live trading

`scripts/run_mt5_live.py` refuses to start on anything but a demo account. It has
no credentials of its own — it attaches to whichever account the MT5 terminal is
already signed into — so it checks `trade_mode` and stops unless the terminal
reports a demo. Going live is an explicit `ALLOW_REAL_MONEY = True` in that file,
not something a stray login can do for you.

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
│
├── core/
│   ├── data/
│   │   └── mt5_connector.py     # The only module that touches the MT5 API
│   ├── signals/
│   │   └── strategy_engine.py   # Pullback Sniper v2.0 — indicators + 5-filter entry
│   ├── risk/
│   │   ├── lot_sizing.py        # Dollar risk → a lot size the broker will accept
│   │   └── risk_manager.py      # Drawdown limits, streak detection, volatility scaling
│   ├── analytics/
│   │   └── backtester.py        # Backtesting engine + Monte Carlo
│   └── console.py               # Forces UTF-8 output so Windows consoles survive the reports
│
├── scripts/                     # Executable entry points
│   ├── run_mt5_live.py          # Live execution — MT5 connection, 4-level trailing stop
│   ├── run_backtest_v2.py       # Full backtest with analytics
│   ├── quick_backtest.py        # Fast iteration on strategy parameters
│   ├── analyze_report.py        # Post-run trade report analysis
│   └── *.bat                    # Windows wrappers — start / stop / check status
│
├── tests/                       # pytest — 44 tests
│   ├── test_strategy.py         test_strategy_v2.py
│   ├── test_risk.py             test_risk_enhanced.py    test_risk_ftmo.py
│   └── test_backtest.py
│
└── docs/
    ├── CHANGELOG.md
    └── POST_MORTEM_ANALYSIS.md  # Why a 2:1 R:R strategy still lost money
```

> The signal, risk, backtest, and data-loading paths all reach the broker through
> `core/data/mt5_connector.py`, so everything except live trading can be exercised
> on a machine with no terminal attached. `run_mt5_live.py` is the honest exception:
> it still calls the MT5 API directly for order and position bookkeeping, and moving
> that behind the connector is the next refactor this repo wants.

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
- **Minimum lot check:** if the smallest position the broker will accept risks more
  than 1.5× the intended amount, the trade is skipped rather than resized

That last rule is the one this project was built to learn. A 2% risk model on a
$300 account wants 0.0011 lots of Gold; the broker's floor is 0.01, which risks
18% of the account. The old code clamped up to the floor and said nothing, and
223 live trades later a strategy with a genuine 2:1 edge had a profit factor of
0.96. `core/risk/lot_sizing.py` is now the single place that conversion happens,
and both the live bot and the backtester go through it — so the backtest can no
longer pass by holding positions no broker would fill.

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
uv run python scripts/run_backtest_v2.py
```

## Lessons Learned

This project was tested with real capital on a demo account ($300 initial balance, 223 trades over 2.5 months). Key findings:

- **Theoretical position sizing ≠ practical position sizing.** The Kelly Criterion and fractional risk models assume infinitely divisible position sizes. In practice, a broker's minimum lot size (0.01) creates a hard floor on risk-per-trade. For Gold, this meant 32% risk-per-trade instead of the intended 2%.
- **Capital-instrument mismatch is the real killer.** The strategy's R:R ratio was sound (avg win $34 vs avg loss $17 = 2:1), but Profit Factor was 0.96 because oversized positions destroyed the edge. Minimum balance for Gold at 2% risk: ~$4,500.
- **Asset-specific performance matters.** Gold produced large wins during trends (+$208, +$424) but catastrophic losses during volatility spikes (-$355). Bitcoin was more capital-appropriate but had lower win rate (37%).
- **A 1.5× ATR stop-loss is useless if the minimum pip value forces 100% portfolio risk.** Risk management must account for the minimum viable execution size of each instrument.

## Tech Stack

- **Language:** Python 3.14
- **Broker API:** MetaTrader 5
- **Analysis:** pandas, NumPy, matplotlib
- **Testing:** pytest
- **Packaging:** uv (locked via `uv.lock`)

## License

MIT
