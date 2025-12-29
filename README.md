# 🤖 AntiGravity Trading Bot (Exness MT5 Edition)

High-performance Quantitative Trading Bot designed for **Gold (XAUUSD)** and **Crypto (BTC/ETH)** on Exness MetaTrader 5.

## 🚀 Features
- **Multi-Asset Support:** Trades Gold, Bitcoin, and Ethereum simultaneously.
- **Strategy:** Heikin Ashi Trend Following + EMA Crossovers (18/35/200).
- **Risk Management:** Anti-Fragile sizing, Kelly Criterion, and ATR-based Stops.
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
- **Risk Settings:** Edit `config.py`.
