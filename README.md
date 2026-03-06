# AntiGravity — Algorithmic Trading System

**End-to-end quantitative trading bot** for Gold (XAUUSD) and Bitcoin (BTC) on MetaTrader 5.  
Built with Python, featuring a multi-filter signal engine, institutional-grade risk management, and live execution.

---

## Performance

| Metric | v1.x (Baseline) | v2.0 (Current) |
|--------|-----------------|----------------|
| Net P&L | -$207 | **+$231** |
| Profit Factor | 0.91 | **9.22** |
| Win Rate | 31% | **62.5%** |
| Max Drawdown | 90% | **5.5%** |
| Trades | 214 (49 days) | 8 (8 days) |

> v2.0 was redesigned after diagnosing negative expectancy in v1.x using statistical analysis.  
> See [CHANGELOG](docs/CHANGELOG.md) for the full evolution from v1.0 → v2.0.

---

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  MT5 Terminal │────▶│  Strategy Engine  │────▶│ Risk Manager │
│  (Data Feed)  │     │  (Signal Gen)    │     │  (Gatekeeper) │
└──────────────┘     └──────────────────┘     └──────────────┘
                              │                       │
                              ▼                       ▼
                     ┌──────────────────┐     ┌──────────────┐
                     │  Order Execution  │◀───│Position Sizing│
                     └──────────────────┘     └──────────────┘
                              │
                              ▼
                     ┌──────────────────────────────────┐
                     │  Trailing Stop (4-Level System)   │
                     │  BE → Lock 0.75R → Lock 1.5R → Trail │
                     └──────────────────────────────────┘
```

### Core Modules

| Module | Description |
|--------|-------------|
| [`strategy_engine.py`](modules/strategy_engine.py) | Technical indicator calculation (EMA, ATR, RSI, ADX, Bollinger Bands) and signal generation via 5-filter pullback system |
| [`risk_manager.py`](modules/risk_manager.py) | Position sizing (Kelly Criterion / Fixed Fractional), circuit breakers, drawdown control, martingale detection, volatility scaling |
| [`mt5_connector.py`](modules/mt5_connector.py) | MT5 API integration — market data ingestion, order execution, position management |
| [`run_mt5_live.py`](scripts/run_mt5_live.py) | Live trading engine — main event loop, trailing stop management, trade lifecycle |

---

## Strategy: Pullback Sniper (v2.0)

**Core Idea:** Enter on pullbacks to moving average, not on crossovers.  
This provides tighter stop losses and better risk:reward.

### Entry Conditions (ALL must be true)

```
LONG Signal:
  1. ADX > 20           (market is trending)
  2. Price > EMA 200     (macro uptrend)
  3. EMA 18 > EMA 35     (bullish momentum)
  4. RSI in [35, 65]     (not overbought — pullback zone)
  5. Price within 0.5×ATR of EMA 18  (pullback detected)
```

### Risk Management

| Component | Implementation |
|-----------|---------------|
| Position Sizing | 2% Fixed Fractional (Half-Kelly) with $50 max loss cap |
| Stop Loss | 1.5× ATR from entry |
| Take Profit | 4.5× ATR from entry (R:R = 1:3) |
| Trailing Stop | 4-level: Breakeven at 1R → Lock 0.75R at 1.5R → Lock 1.5R at 2R → Dynamic trail at 2.5R+ |
| Circuit Breaker | Halves position size at 15% drawdown |
| Volatility Scaling | Reduces size when ATR > 1.5× normal |
| Martingale Detection | Detects increasing lot sizes after losses → resets to minimum |
| Cooldown | 240-minute minimum between trades (H4 timeframe) |

### Why Pullback > Crossover?

```
Expectancy = (Win% × Avg_Win) − (Loss% × Avg_Loss)

v1.x (Crossover, R:R 1:2):  (0.31 × 2) − (0.69 × 1) = −0.07R  ← Losing
v2.0 (Pullback, R:R 1:3):   (0.35 × 3) − (0.65 × 1) = +0.40R  ← Winning
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| Broker API | MetaTrader 5 |
| Data Processing | pandas, numpy |
| Indicators | Custom (EMA, ATR, RSI, ADX, Bollinger Bands, Heikin Ashi) |
| Testing | pytest, custom test suite |
| Deployment | Windows VPS, Git-based CI |
| Version Control | Git + GitHub |

---

## Quick Start

### Prerequisites
- Windows OS (PC or VPS)
- MetaTrader 5 (logged in to broker)
- Python 3.12+

### Installation
```bash
git clone https://github.com/PLLV99/quant-trading-bot.git
cd quant-trading-bot
pip install -r requirements.txt
```

### Run
```bash
# Ensure MT5 is open with Algo Trading enabled (green button)
python scripts/run_mt5_live.py
```

### Test
```bash
python tests/test_strategy_v2.py
```

---

## Project Structure

```
quant-trading-bot/
├── config.py                 # Strategy & risk parameters
├── main.py                   # Backtest entry point
├── modules/
│   ├── strategy_engine.py    # Signal generation (5-filter system)
│   ├── risk_manager.py       # Position sizing & risk controls
│   ├── mt5_connector.py      # Broker API integration
│   ├── backtester.py         # Vectorized backtesting engine
│   ├── data_loader.py        # Market data loading & preprocessing
│   └── paper_trader.py       # Paper trading simulator
├── scripts/
│   ├── run_mt5_live.py       # Live trading engine
│   └── analyze_report.py     # Trade report analysis
├── tests/
│   ├── test_strategy_v2.py   # v2.0 pullback strategy tests
│   ├── test_risk.py          # Risk manager tests
│   └── test_risk_enhanced.py # Enhanced risk feature tests
└── docs/
    └── CHANGELOG.md          # Version history & design decisions
```

---

## License

This project is for educational and demonstration purposes.
