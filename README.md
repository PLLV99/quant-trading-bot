# 🤖 AntiGravity Trading Bot (Exness MT5 Edition)

High-performance Quantitative Trading Bot designed for **Gold (XAUUSD)** and **Crypto (BTC/ETH)** on Exness MetaTrader 5.

## 🚀 Features
- **Multi-Asset Support:** Trades Gold, Euro, Oil, and Bitcoin.
- **Strategy:** "Sniper" Heikin Ashi + EMA (9/21/50) + RSI Filter on M15.
- **Risk Management:** $6 Hard Cap per trade (Anti-Fragile), 2.5x ATR dynamic stops.
- **Platform:** Exness MetaTrader 5 (Windows).

## 🛠️ Installation

### Prerequisites
1.  **Windows OS** (PC or Cloud VPS)
2.  **MetaTrader 5** (logged in to Exness)
3.  **Python 3.11**

### Setup
```bash
# 1. Create Virtual Environment (Optional but recommended)
py -3.11 -m venv .venv
.venv\Scripts\activate

# 2. Install Dependencies
pip install -r requirements.txt
```

## ▶️ How to Run
Ensure MT5 is open and Algo Trading is ENABLED (Green Play Button).

```bash
python scripts/run_mt5_live.py
```

The bot will launch and start monitoring `XAUUSDm`, `EURUSDm`, `USOILm`, and `BTCUSDm`.

## ⚙️ Configuration
- **Assets:** Edit `scripts/run_mt5_live.py` (Modify the `PORTFOLIO` list).
- **Strategy:** Edit `modules/strategy_engine.py` (EMA/RSI settings).
- **Risk:** Edit `modules/risk_manager.py` ($6 cap rule).
