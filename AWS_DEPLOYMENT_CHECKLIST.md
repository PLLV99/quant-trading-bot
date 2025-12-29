# AWS EC2 Deployment Checklist

Quick reference checklist for deploying bot to AWS.

## Before You Start
- [ ] AWS account created
- [ ] Credit card added (for verification)
- [ ] Exness demo account ready
- [ ] Downloaded bot files

---

## AWS Setup (30 minutes)

### Create EC2 Instance
- [ ] Login to AWS Console
- [ ] Navigate to EC2 → Launch Instance
- [ ] Name: `TradingBot-MT5`
- [ ] AMI: Windows Server 2022 Base
- [ ] Instance type: **t3.medium** (2 vCPU, 4GB RAM)
- [ ] Create key pair: `trading-bot-key.pem` (save securely!)
- [ ] Security Group: Allow RDP from My IP
- [ ] Storage: 50 GB gp3
- [ ] Launch instance

### Get Connection Details
- [ ] Wait for instance state: **Running**
- [ ] Copy Public IPv4 address: `___________________`
- [ ] Get Windows password (upload .pem file)
- [ ] Save password: `___________________`

---

## Connect to Server (10 minutes)

### Remote Desktop
- [ ] Open Remote Desktop (Win+R → `mstsc`)
- [ ] Enter IP address
- [ ] Username: `Administrator`
- [ ] Password: (from above)
- [ ] Connected successfully ✓

---

## Install Software (45 minutes)

### Python 3.11
```powershell
# In PowerShell (as Admin)
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe" -OutFile "python.exe"
.\python.exe /quiet InstallAllUsers=1 PrependPath=1
```
- [ ] Installed
- [ ] Verify: `python --version`

### MetaTrader 5
- [ ] Download from Exness website
- [ ] Install MT5
- [ ] Login to demo account
- [ ] Verify connection ✓

### Bot Files
- [ ] Upload via OneDrive/Google Drive, OR
- [ ] Copy via RDP clipboard
- [ ] Extract to: `C:\TradingBot`

### Dependencies
```powershell
cd C:\TradingBot
pip install -r requirements.txt
```
- [ ] Installed successfully

---

## Test Bot (15 minutes)

### Manual Test
```powershell
cd C:\TradingBot
python scripts\run_mt5_live.py
```
- [ ] Bot starts without errors
- [ ] Connected to MT5 ✓
- [ ] Monitoring symbols ✓
- [ ] Stop with Ctrl+C

### Using Scripts
- [ ] Test: `start_bot.bat`
- [ ] Test: `check_status.bat`
- [ ] Test: `stop_bot.bat`

---

## Setup Auto-Start (Optional)

- [ ] Win+R → `shell:startup`
- [ ] Create shortcut to `start_bot.bat`
- [ ] Move to startup folder
- [ ] Test by restarting EC2

---

## Monitor & Verify (24 hours)

### First Hour
- [ ] Bot running without crashes
- [ ] MT5 connected
- [ ] Check logs: `logs\bot_activity.log`

### After 24 Hours
- [ ] Bot still running
- [ ] Check demo account balance
- [ ] Review trades in MT5
- [ ] No errors in logs

---

## Access from Local PC

### Remote Desktop
```
Computer: <EC2_Public_IP>
Username: Administrator
Password: <saved_password>
```

### MT5 Mobile App
- [ ] Install MT5 on phone
- [ ] Login to Exness demo
- [ ] View trades remotely

---

## Cost Management

### Set Billing Alarm
- [ ] CloudWatch → Alarms → Create
- [ ] Alert when > $50/month
- [ ] Add email notification

### Stop When Not Needed
- [ ] EC2 → Stop instance (saves compute cost)
- [ ] Storage still charged (~$5/month)

---

## Troubleshooting

### Can't connect RDP?
- Check Security Group allows port 3389
- Verify Public IP is correct
- Instance must be Running

### Bot won't start?
- Check MT5 is logged in
- Verify Python installed: `python --version`
- Check logs for errors

### MT5 disconnected?
- Check internet connection
- Re-login to Exness
- Restart MT5

---

## Support Resources

- AWS EC2 Docs: https://docs.aws.amazon.com/ec2/
- MT5 Support: https://www.exness.com/support/
- Bot Logs: `C:\TradingBot\logs\`

---

**Setup Complete?** Monitor demo for 2-4 weeks before live trading!
