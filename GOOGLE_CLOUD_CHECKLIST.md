# Google Cloud Deployment - Quick Checklist

Use this to track your progress deploying to Google Cloud.

---

## ☁️ Phase 1: Account Setup (15 min)

- [ ] Go to [cloud.google.com](https://cloud.google.com)
- [ ] Click "Get started for free"
- [ ] Login with Google account
- [ ] Add credit card (won't be charged)
- [ ] Claim **$300 free credit** ✅
- [ ] Create project: `trading-bot-project`
- [ ] Verify credits showing in console

---

## 🖥️ Phase 2: Create VM (20 min)

- [ ] Enable Compute Engine API
- [ ] Create VM instance
  - Name: `trading-bot-vm`
  - Region: `us-central1` or `northamerica-northeast1`
  - Machine: **e2-medium** (2 vCPU, 4GB)
  - OS: **Windows Server 2022**
  - Disk: 50 GB SSD
- [ ] Create firewall rule for RDP (port 3389)
- [ ] Start VM
- [ ] Copy External IP: `___.___.___.___`

---

## 🔐 Phase 3: Connect (10 min)

- [ ] Set Windows password in console
- [ ] Save username: `________________`
- [ ] Save password: `________________`
- [ ] Connect via RDP:
  - **Windows:** Win+R → `mstsc`
  - **Mac:** Microsoft Remote Desktop app
  - **Browser:** "Open in browser window"
- [ ] Connected successfully ✅

---

## 📦 Phase 4: Install Software (45 min)

### Python
```powershell
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe" -OutFile "C:\python.exe"
Start-Process C:\python.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait
```
- [ ] Installed
- [ ] Verify: `python --version` shows 3.11.x

### MetaTrader 5
- [ ] Download from Exness
- [ ] Install MT5
- [ ] Login to demo account
- [ ] Verify green connection icon ✅

### Bot Files
- [ ] Upload via Google Drive/OneDrive
- [ ] Extract to `C:\TradingBot`
- [ ] Run: `pip install -r requirements.txt`
- [ ] All dependencies installed ✅

---

## 🤖 Phase 5: Test Bot (15 min)

- [ ] Run: `python scripts\run_mt5_live.py`
- [ ] Bot starts without errors
- [ ] See: "Connected to Exness" ✅
- [ ] See: "Monitoring XAUUSDm..." ✅
- [ ] Stop with Ctrl+C

### Test Control Scripts
- [ ] `start_bot.bat` works
- [ ] `check_status.bat` shows status
- [ ] `stop_bot.bat` stops bot

---

## 📊 Phase 6: Monitoring (24 hours)

### First Hour
- [ ] Bot running continuously
- [ ] No errors in console
- [ ] MT5 connected (green icon)
- [ ] Check logs: `type logs\bot_activity.log`

### After 24 Hours
- [ ] Bot still running
- [ ] Check demo balance in MT5 app
- [ ] Review any trades made
- [ ] Check for errors in logs

---

## 💰 Phase 7: Cost Setup

- [ ] Billing → Budgets → Create budget alert
  - Amount: $100/month
  - Alerts at: 50%, 90%, 100%
- [ ] Add email for notifications
- [ ] Check free credit balance

---

## 🔄 Daily Operations

### Check Bot Status
```powershell
.\scripts\check_status.bat
```

### View Recent Logs
```powershell
Get-Content logs\bot_activity.log -Tail 20
```

### Stop VM (Save money)
```
Google Console → Compute Engine → STOP
```

### Start VM
```
Google Console → Compute Engine → START
```

---

## 📱 Remote Monitoring

### From Phone
- [ ] Install MT5 app
- [ ] Login to Exness demo
- [ ] See trades remotely

### From Laptop (Anywhere)
- [ ] RDP to External IP
- [ ] Check bot status
- [ ] View Python console

---

## ⚠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't connect RDP | Check firewall, VM is running |
| Python not found | Reinstall, add to PATH |
| MT5 disconnected | Re-login to Exness |
| Bot errors | Check logs, verify MT5 logged in |

---

## ✅ Success Criteria

- [ ] Bot runs 24 hours without crash
- [ ] Demo account showing trades
- [ ] No critical errors in logs
- [ ] Can control from remote PC/phone
- [ ] Free credits still available

---

**Need help?** Check detailed guide in `implementation_plan.md`

**Estimated total time:** 2-3 hours  
**Cost for 3 months:** FREE ($300 credit)
