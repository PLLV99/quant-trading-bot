# 🔐 VPS Migration & Security Checklist

เช็คลิสต์สำหรับย้าย Trading Bot ไป VPS ใหม่ (หลังหมด Google Cloud Free Credits)

---

## 📋 Phase 1: เลือก VPS Provider

### ตัวเลือกแนะนำ (ถูก + ปลอดภัย)

| Provider | Plan | RAM | ราคา/เดือน | Link |
|----------|------|-----|-----------|------|
| **Contabo** | VPS S | 4GB | €4.99 (~$6) | contabo.com |
| **Hetzner** | CX21 | 4GB | €5.83 (~$7) | hetzner.com |
| **Vultr** | Cloud | 4GB | $24 | vultr.com |

### ข้อกำหนด Minimum
- [ ] OS: **Windows Server 2019/2022**
- [ ] RAM: **4GB ขึ้นไป**
- [ ] Storage: **50GB SSD**
- [ ] Location: ใกล้ Broker Server (Europe/US)

---

## 📋 Phase 2: Setup VPS ใหม่

### 2.1 เมื่อได้ VPS
- [ ] จด **IP Address**: `_______________`
- [ ] จด **Username**: `Administrator`
- [ ] ตั้ง **Password ใหม่** (16+ ตัว, มี A-Z, a-z, 0-9, !@#)
- [ ] **เก็บ Password ปลอดภัย** (ใช้ Password Manager)

### 2.2 Connect ครั้งแรก
```
1. เปิด Remote Desktop (Win+R → mstsc)
2. ใส่ IP Address
3. Username: Administrator
4. Password: [ที่จดไว้]
```

---

## 🔒 Phase 3: Security Hardening (สำคัญมาก!)

### 3.1 Windows Update
- [ ] Settings → Windows Update → Check for updates
- [ ] Install ทั้งหมด แล้ว Restart

### 3.2 เปลี่ยน RDP Port (ป้องกัน Brute Force)
```powershell
# Run as Administrator
# เปลี่ยนจาก 3389 เป็น port อื่น (เช่น 54321)

Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name 'PortNumber' -Value 54321

# Restart RDP Service
Restart-Service -Name TermService -Force

# จำไว้! ครั้งหน้าต้องใส่ IP:54321 ใน Remote Desktop
```

### 3.3 Windows Firewall
- [ ] Control Panel → Windows Defender Firewall → Turn On
- [ ] เปิดแค่ port ที่ใช้:
  - **RDP Port ใหม่** (54321 หรือที่ตั้งไว้)
  - **443** (HTTPS for MT5)

```powershell
# Block port 3389 เดิม
New-NetFirewallRule -DisplayName "Block Old RDP" -Direction Inbound -LocalPort 3389 -Protocol TCP -Action Block

# Allow port ใหม่
New-NetFirewallRule -DisplayName "Allow New RDP" -Direction Inbound -LocalPort 54321 -Protocol TCP -Action Allow
```

### 3.4 Disable Unnecessary Services
```powershell
# ปิด Remote Registry (ไม่จำเป็น)
Set-Service -Name RemoteRegistry -StartupType Disabled
Stop-Service -Name RemoteRegistry

# ปิด Windows Remote Management
Set-Service -Name WinRM -StartupType Disabled
```

### 3.5 Anti-Brute Force (แนะนำ)
- [ ] ติดตั้ง **RdpGuard** หรือ **fail2ban for Windows**
- หรือใช้ VPS ที่มี DDoS protection built-in

---

## 📋 Phase 4: Install Software

### 4.1 Python 3.11
```powershell
# Download & Install
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe" -OutFile "C:\python.exe"
Start-Process C:\python.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait
```
- [ ] Verify: `python --version`

### 4.2 MetaTrader 5
- [ ] Download จาก Exness
- [ ] Install
- [ ] **Login ด้วย DEMO account ก่อน!**
- [ ] Enable Algo Trading (Tools → Options → Expert Advisors)

### 4.3 Bot Files
- [ ] Upload files ผ่าน OneDrive/Google Drive
- [ ] หรือ Copy ผ่าน RDP clipboard
- [ ] Extract ไปที่ `C:\TradingBot`

```powershell
cd C:\TradingBot
pip install -r requirements.txt
```

---

## 🔑 Phase 5: Exness Security (สำคัญที่สุด!)

### 5.1 เปิด 2FA บน Exness
- [ ] Login Exness Personal Area
- [ ] Settings → Security → Two-Factor Authentication
- [ ] ใช้ Google Authenticator หรือ Authy

### 5.2 Trading Password แยก
- [ ] ตั้ง Trading Password แยกจาก Master Password
- [ ] ใช้ Trading Password ใน MT5

### 5.3 IP Restriction (ถ้ามี)
- [ ] จำกัด IP ที่ login ได้ (ถ้า Exness รองรับ)

---

## ✅ Phase 6: Test Before Go Live

### 6.1 Test Bot
```powershell
cd C:\TradingBot
python scripts\run_mt5_live.py
```
- [ ] Bot connects to MT5 ✓
- [ ] Bot sees prices ✓
- [ ] Bot can place demo trade ✓

### 6.2 Test Auto-Restart
- [ ] Double-click `loop_bot.bat`
- [ ] ปิด PowerShell → ดูว่า restart ได้

### 6.3 Test RDP Reconnect
- [ ] Disconnect RDP
- [ ] Reconnect ด้วย port ใหม่ (IP:54321)

---

## 📋 Phase 7: Go Live Checklist

**ก่อนใส่เงินจริง:**
- [ ] รัน DEMO อย่างน้อย **1 สัปดาห์** บน VPS ใหม่
- [ ] ไม่มี crash / disconnect
- [ ] Security checklist ครบทุกข้อ
- [ ] 2FA Exness เปิดแล้ว
- [ ] Password แข็งแรง (16+ ตัว)

---

## 🚨 Emergency Contacts

| สถานการณ์ | ทำอะไร |
|-----------|--------|
| VPS ไม่ตอบสนอง | Contact Provider Support |
| สงสัยโดน Hack | 1. หยุด Bot 2. เปลี่ยน Password ทุกที่ 3. เช็ค Exness trades |
| MT5 Disconnect | Restart MT5, เช็ค internet |
| Bot Crash | ดู logs, รัน `loop_bot.bat` |

---

## 💰 Cost Summary

| รายการ | ราคา/เดือน |
|--------|-----------|
| VPS (Contabo) | ~$6 |
| Domain (ไม่จำเป็น) | $0 |
| MT5 | ฟรี |
| Bot | ฟรี |
| **รวม** | **~$6/เดือน** |

---

## 📝 Notes

```
VPS IP: _______________
RDP Port: _______________
Username: Administrator
Password: [เก็บใน Password Manager]

Exness Account: _______________
MT5 Server: _______________
```

---

**Last Updated:** January 2026
