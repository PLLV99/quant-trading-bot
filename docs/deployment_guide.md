# 🚀 Trading Bot Deployment Guide (Binance Mode)

This guide details how to deploy the "Anti-Fragile" Quantitative Trading Bot on a VPS (Virtual Private Server) using Docker.

## 1. System Architecture
**Current Configuration:**
- **Exchange:** Binance (Spot)
- **Assets:** BTC/USDT, ETH/USDT, BNB/USDT
- **Strategy:**
    - **Dynamic Grid:** Spacing adjusts with Volatility (ATR).
    - **Trend Filter:** No Longs if Trend is Bearish (SMA 200).
    - **Circuit Breaker:** Halts trading if Drawdown > 15%.
- **Mode:** Paper Trading (Real-Time Simulation).

## 2. Prerequisites
- A VPS (e.g., DigitalOcean Droplet, AWS EC2) with Docker installed.
- **Git** installed.

## 3. Google Cloud Free Tier & Safe Setup (Recommendation)
For a cost-effective and safe deployment, we recommend using **Google Cloud Platform (GCP)** within its Always Free Tier.

### ✅ Infrastructure Choice
- **Instance Type:** `e2-micro` (2 vCPUs, 1 GB memory).
- **Region:** `us-west1`, `us-central1`, or `us-east1` (check current Free Tier eligible regions).
- **Disk:** 30GB Standard Persistent Disk.

### ⚠️ Critical Gotchas: How to Avoid Unexpected Costs (MUST READ)
Even though GCP has an "Always Free" tier, there are traps that can lead to charges. Follow these rules strictly:

#### 1. Region Selection (Vital!)
- **FREE:** `us-central1`, `us-west1`, `us-east1` ONLY.
- **NOT FREE:** `asia-southeast1` (Singapore), `asia-east1` (Taiwan), `europe-west1` (Belgium), etc.
- **Consequence:** Using the wrong region results in immediate charges ($5-10/month).

#### 2. Disk Type Selection
- **FREE:** `Standard persistent disk` (Max 30GB).
- **NOT FREE:** `SSD persistent disk`, `Balanced persistent disk`.
- **Consequence:** Using SSD results in charges ($1-5/month).

#### 3. IP Address (Static IP Warning)
- **FREE:** Ephemeral (Dynamic) IP while the instance is running.
- **NOT FREE:** Static IP if the instance is STOPPED.
- **Consequence:** If you stop the bot but keep a Static IP reserved, you are charged ~$0.01/hour ($7/month).
- **Solution:** Use Ephemeral IP or remember to 'Release' the Static IP if you destroy the instance.

#### 4. Network Egress
- **FREE:** 1GB/month traffic to the internet.
- **Status:** This trading bot uses very little data (~100MB/month), so it is safe.
- **Warning:** Do not run bandwidth-heavy tasks (web server, huge downloads) on this instance.

#### 5. The "Kill Switch": Billing Budget
- **Action:** Go to Billing > Budgets & Alerts.
- **Set Budget:** **$1.00** (or $5).
- **Alerts:** Email at 50%, 90%, 100%.
- **Why:** If you made a mistake (e.g., wrong region), you will know within hours, not at the end of the month.

### 🛡️ System Security
**Firewall Rules (VPC Network > Firewall):**
- **Allow:** `tcp:22` (SSH).
- **Block:** All other incoming ports (80, 443, etc. are not needed).
- **Best Practice:** Restrict SSH access to "My IP" only if possible.

> **Note:** If configured correctly (e2-micro + valid region + within egress limits), running this bot should be **free or extremely cheap** (<$1/mo).

## 4. Pro Tips: Real-World Stability (Life Hacks) 💡
Since `e2-micro` has limited RAM (1GB), follow these steps to prevent it from crashing ("OOM Kill"):

### 1. Create Swap Memory (Virtual RAM) - **Highly Recommended**
Run these commands on your VPS host immediately after login. This creates a 2GB "safety net" on the disk.
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
*Why?* Without this, if your bot suddenly uses 1.1GB RAM locally, the server crashes. With Swap, it just slows down slightly but stays alive.

### 2. Hardening SSH (Security)
Disable password login to stop Brute Force attacks (Chinese/Russian bots scan port 22 24/7).
1. Ensure you can login with your **SSH Key**.
2. Edit config: `sudo nano /etc/ssh/sshd_config`
3. Set: `PasswordAuthentication no`
4. Restart SSH: `sudo service ssh restart`

### 3. Log Rotation (Prevent Disk Full)
Logs can eat up your 30GB disk over months. Docker can limit this automatically.
Add this to your `docker-compose.yml` (under `trading-bot` service):
```yaml
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 5. Quick Start (Docker)
Execute these commands on your VPS:

### Step 1: Clone & Navigate
```bash
git clone https://github.com/PLLV99/quant-trading-bot.git
cd quant-trading-bot
```

### Step 2: Build the Container
```bash
docker-compose build
```

### Step 3: Launch (Paper Mode - 7 Days)
This runs the bot in the background (`-d`). It will automatically restart if the server reboots.
```bash
docker-compose up -d
```

### Step 4: Monitor Status
Check logs to confirm the bot is alive.
```bash
# View active logs
docker-compose logs -f

# Check active processes
docker ps
```

## 6. Maintenance

### Stop the Bot
```bash
docker-compose down
```

### View Trade Reports (Logs)
Logs are saved to the host's `logs/` directory.
```bash
cat logs/paper_trading_*.log
```

### Switch to LIVE Trading
1. Edit `docker-compose.yml`: Change `command` to `--mode live`.
2. (**Important**) Ensure API Keys are set in `.env` (passed safely).
3. Restart: `docker-compose up -d --build`
