# 🚀 Deployment Guide - MT5 Gold/Crypto Bot

## System Requirements

### Windows VPS (Recommended)
- **Provider**: Google Cloud, AWS, or any Windows VPS
- **OS**: Windows Server 2019/2022
- **RAM**: 4GB minimum (8GB recommended)
- **CPU**: 2 cores minimum

### Software Requirements
1. **MetaTrader 5** (Exness account)
2. **Python 3.11**
3. **Git** (for cloning)

---

## Deployment Steps

### 1. Setup VPS
Create a Windows VPS on your preferred cloud provider.

### 2. Install MetaTrader 5
1. Download MT5 from Exness
2. Login to your trading account
3. Enable **Algo Trading** (Tools → Options → Expert Advisors → Allow Algo Trading)

### 3. Install Python
```powershell
# Download Python 3.11 from python.org
# During installation, check "Add Python to PATH"
```

### 4. Clone Repository
```powershell
git clone https://github.com/YOUR_USERNAME/trading_bot.git
cd trading_bot
```

### 5. Install Dependencies
```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 6. Run the Bot
```powershell
python scripts\run_mt5_live.py
```

---

## Configuration

## Configuration

### Assets (Sniper Portfolio)
- **XAUUSDm** (Gold) - The "King"
- **EURUSDm** (Euro) - Stability
- **USOILm** (Oil) - Energy Play
- **BTCUSDm** (Bitcoin) - High Growth

To modify: Edit `scripts/run_mt5_live.py` → `PORTFOLIO` variable

### Sniper Strategy Settings
The bot is pre-configured for **M15 Timeframe** with:
- **EMA**: 9 / 21 / 50
- **RSI**: 14 (Momentum > 50)
- **Risk**: Hard cap $6 per trade

### Risk Settings
Edit `modules/risk_manager.py` to adjust:
- `risk_per_trade_usd`: Currently set to **6.0**
- `stop_loss_distance`: Currently set to **2.5x ATR**

---

## Running 24/7

### Option 1: Keep VPS Running
Just leave the script running in PowerShell. The bot will loop continuously.

### Option 2: Windows Task Scheduler
Create a scheduled task to auto-start the bot on VPS reboot.

---

## Monitoring

The bot prints trade signals to console:
```
[12:30] XAUUSDm >>> BUY SIGNAL! Executing...
        >>> SUCCESS: Ticket 123456789
```

Check MT5 terminal for:
- Open positions
- Trade history
- Account balance

---

## Safety Notes

> [!CAUTION]
> - Always test on **DEMO account** first
> - Monitor the bot regularly (especially first 24 hours)
> - Set stop losses on MT5 level as backup
> - Keep MT5 terminal OPEN and logged in

---

## Troubleshooting

**Bot won't connect to MT5?**
- Ensure MT5 is open and logged in
- Check "Algo Trading" is enabled (green play button)

**No trades executing?**
- Check console for error messages
- Verify symbols are correct (XAUUSDm vs XAUUSD)
- Ensure account has sufficient margin

**Bot crashes?**
- Check Python version (must be 3.11)
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
