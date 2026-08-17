# Quant Trading Bot — Post-Mortem Analysis

> **Document Type:** Engineering Post-Mortem  
> **System:** Quant Trading Bot — Algorithmic Trading System v1.0–v2.0  
> **Period:** Jan 4, 2026 → Mar 16, 2026 (72 days)  
> **Result:** Net Loss -$108.72 (-36.2% of initial capital)  
> **Author:** System Architect Review

---

## 1. System Architecture & Tech Stack

### Runtime Environment
| Component | Detail |
|-----------|--------|
| **Language** | Python 3.10+ |
| **Broker** | Exness (MT5Trial14, Demo, Hedge mode) |
| **API** | MetaTrader 5 Python Package (`MetaTrader5`) |
| **Execution Host** | Google Cloud Platform — Windows Server VM (e2-medium, 2 vCPU, 4GB RAM) |
| **Access** | Remote Desktop Protocol (RDP) |
| **Data Storage** | In-memory (pandas DataFrame), no persistent database |
| **Logging** | Python `logging` module → `logs/*.log` files |

### Architecture: Pipeline (Layered)

```
┌──────────────┐    ┌────────────────┐    ┌───────────────┐    ┌──────────────┐
│  DATA LAYER  │───▶│  SIGNAL LAYER  │───▶│  RISK LAYER   │───▶│  EXECUTION   │
│              │    │                │    │               │    │              │
│ mt5_connector│    │ strategy_engine│    │ risk_manager  │    │ run_mt5_live │
│ data_loader  │    │ (5-filter      │    │ (position     │    │ (MT5 API     │
│              │    │  pullback)     │    │  sizing, DD   │    │  order send) │
│              │    │                │    │  limits)      │    │              │
└──────────────┘    └────────────────┘    └───────────────┘    └──────────────┘
```

### Data Flow (Polling Model)
```
Every 60 seconds:
  1. mt5.copy_rates_from_pos(symbol, H4, 0, 100)  ← Pull 100 H4 candles
  2. StrategyEngine.add_indicators(df)              ← Calculate EMA/RSI/ADX/ATR
  3. StrategyEngine.generate_signal()               ← 5-filter decision
  4. RiskManager.check_trade_allowed()              ← DD/streak check
  5. calculate_lot_size()                           ← Position sizing
  6. mt5.order_send()                               ← Execute if all pass
```

**Data retrieval method:** Polling every 60 seconds via `mt5.copy_rates_from_pos()`. Not event-driven. No WebSocket. No webhook. The bot sleeps between polls using `time.sleep(60)`.

**No persistent storage:** All indicators are recalculated from scratch on each 60-second cycle. Trade history is only available via MT5's built-in history, not stored by the bot.

---

## 2. Trading Logic & Strategy

### v2.0 "Pullback Sniper" (Final Version)

**Timeframe:** H4 (4-hour candles)  
**Assets:** XAUUSDm (Gold), BTCUSDm (Bitcoin)  
**Account Type:** Standard (Hedge mode)

### Entry Rules — 5 Conditions (ALL must be TRUE)

| # | Filter | Long Condition | Short Condition | Code Reference |
|---|--------|---------------|----------------|---------------|
| 1 | **ADX > 20** | Trend must be strong enough | Same | `strategy_engine.py:384` |
| 2 | **Price vs EMA200** | Price > EMA200 (uptrend) | Price < EMA200 (downtrend) | `strategy_engine.py:389-390` |
| 3 | **EMA18 vs EMA35** | EMA18 > EMA35 (bullish momentum) | EMA18 < EMA35 (bearish) | `strategy_engine.py:393-394` |
| 4 | **RSI 35–65** | RSI in pullback zone (not overbought) | Same zone (not oversold) | `strategy_engine.py:399-401` |
| 5 | **Price near EMA18** | Price within 0.5× ATR of EMA18 | Same | `strategy_engine.py:404-405` |

**Cooldown:** 240 minutes (4 hours) between trades per symbol.  
**Max positions:** 3 total, 1 per symbol.

### Exit Rules

| Exit Type | Trigger | Code Reference |
|-----------|---------|---------------|
| **Stop Loss** | Entry − 1.5× ATR (long) / Entry + 1.5× ATR (short) | `run_mt5_live.py:55` |
| **Take Profit** | Entry + 4.5× ATR (long) / Entry − 4.5× ATR (short) | `run_mt5_live.py:56` |
| **Trailing Stop** (4 levels) | ≥1.0R → SL to breakeven | `run_mt5_live.py:161` |
| | ≥1.5R → Lock 0.75R profit | `run_mt5_live.py:162` |
| | ≥2.0R → Lock 1.5R profit | `run_mt5_live.py:163` |
| | ≥2.5R → Trail: SL = Price − 1R | `run_mt5_live.py:164` |

**R:R ratio:** 1:3 (SL = 1.5× ATR, TP = 4.5× ATR)

### Indicators Calculated

| Indicator | Period | Purpose |
|-----------|--------|---------|
| EMA 18 | 18 bars | Fast trend (pullback target) |
| EMA 35 | 35 bars | Medium trend (momentum confirmation) |
| EMA 200 | 200 bars | Macro trend filter |
| RSI | 14 bars | Overbought/oversold + pullback zone |
| ADX | 14 bars | Trend strength |
| ATR | 14 bars | Volatility for SL/TP/sizing |
| Bollinger Bands | 20 bars, 2σ | Squeeze detection (grid mode only) |
| Heikin Ashi | N/A | Smoothed candle direction |

---

## 3. Risk Management & Position Sizing

### Position Sizing Formula

```python
# From run_mt5_live.py:79-133
risk_amount = account_balance × 0.02          # 2% of balance
raw_lot = risk_amount / (contract_size × sl_distance)
lot = max(min_lot, min(raw_lot, max_lot))     # Clamp to broker limits

# Safety caps:
if balance < $300: max lot = 0.02
if balance < $500: max lot = 0.05
```

### The Fatal Flaw — Minimum Lot Size vs Actual Risk

| Asset | Min Lot | Contract Size | Typical ATR (H4) | SL (1.5× ATR) | Risk at Min Lot | Min Balance for 2% Risk |
|-------|---------|---------------|-------------------|----------------|-----------------|------------------------|
| **XAUUSDm** | 0.01 | 1 oz | ~$60 | ~$90 | **$90/trade** | **$4,500** |
| **BTCUSDm** | 0.01 | 1 BTC / 100 | ~$2,000 | ~$3,000 | **~$30/trade** | **$1,500** |
| **XAGUSDm** | 0.01 | 5,000 oz | ~$1.50 | ~$2.25 | **$112/trade** | **$5,625** |

**Actual account balance: $300 → Gold risk was 30% per trade, not 2%.**

The `calculate_lot_size()` function correctly computes `raw_lot = $6 / (1 × $90) = 0.067` but `max(0.01, 0.067)` rounds to minimum 0.01 — which still risks $90 on a $300 account.

### Risk Controls Summary

| Control | Config Value | Effective? |
|---------|-------------|-----------|
| Risk per trade | 2% | ❌ Bypassed by min lot |
| Max loss cap | $50/trade | ❌ Cannot reduce below min lot |
| Max drawdown | 15% | ⚠️ Triggers too late |
| Cooldown | 240 min | ✅ Works |
| Max positions | 3 total | ✅ Works |
| Losing streak halt | 4 consecutive | ✅ Works |
| Martingale detection | Enabled | ✅ Works |

### Overtrading Prevention

- **Cooldown:** 240-minute lockout per symbol after each trade
- **Max positions:** Hard limit of 3 concurrent (1 per symbol)
- **Emergency halt:** If > 6 positions detected, all trading stops
- **v1.x issue:** Original H1 timeframe + 60-min cooldown caused 211 trades in 49 days. v2.0 (H4 + 240-min) reduced to 12 trades in 23 days.

---

## 4. Known Issues & Edge Cases

### Critical: Capital-Instrument Mismatch
- **Root cause:** Broker minimum lot size (0.01) creates a risk floor that exceeds the 2% budget
- **Worst case:** Single Gold trade on 2026-02-03 lost **-$355.37** (117% of starting balance at that point)
- **Impact:** Max drawdown reached **90.98%**

### Bug: Max Loss Cap Bypass (Fixed in v1.2.0)
- `run_mt5_live.py` used its own `calculate_lot_size()` that ignored `RiskManager.max_loss_per_trade_usd`
- Result: Trades between v1.1.0 and v1.2.0 still exceeded $50 max loss
- Fix date: Feb 7, 2026

### Bug: Dynamic Risk Still Fails on Small Accounts
- After v1.3.1 switched to pure 2% risk, the formula outputs lot sizes < 0.01
- Python clamps to `min_lot = 0.01` which is still oversized
- **Unfixable on Standard account** — structural limitation of broker

### Edge Case: Silver (XAGUSDm) One-Shot Kill
- Silver was included in v1.0 portfolio
- Single trade on 2026-01-16: **-$157.50** (47% of balance at that time)
- Silver contract = 5,000 oz → even 0.01 lot = massive exposure
- Removed in v1.0.1 but too late

### High Volatility Events That Caused Max Damage

| Date | Asset | Event | Loss | Balance After |
|------|-------|-------|------|--------------|
| 2026-01-16 | XAGUSDm | Silver SL hit | -$157.50 | $108.71 |
| 2026-01-18 | XAUUSDm | Gold weekend gap | -$65.31 | $266.21 |
| 2026-01-29 | XAUUSDm | Two Gold SLs in 9 min | -$264.29 | $396.53 |
| 2026-02-03 | XAUUSDm | Gold reversal (SL hit) | -$355.37 | $546.90 |
| 2026-02-03 | XAUUSDm | Second Gold SL same day | -$216.52 | $330.38 |
| 2026-02-04 | XAUUSDm | Gold SL chain | -$161.23 | $179.28 |

**Pattern:** All catastrophic losses came from Gold and Silver on Standard account with minimum lot sizing.

---

## 5. Infrastructure & Costs

### Google Cloud Platform Usage

| Resource | Spec | Cost Driver |
|----------|------|------------|
| **VM Type** | e2-medium (2 vCPU, 4GB RAM) | Compute hours |
| **OS** | Windows Server (license fee embedded) | Disk + license |
| **Disk** | 50GB SSD (Balanced Persistent Disk) | Storage |
| **Network** | RDP traffic + MT5 data polling | Egress |
| **Uptime** | 24/7 (bot must run continuously) | **100% utilization** |

### What Consumed the Free Credit

```
$300 Free Credit breakdown (estimated):

1. Compute (VM running 24/7):     ~$48/month × 2.5 months = ~$120
   - e2-medium = ~$0.067/hr × 720 hrs/month
   
2. Windows License surcharge:      ~$15/month × 2.5 = ~$37
   - GCP charges extra for Windows VMs
   
3. Persistent Disk (50GB SSD):     ~$8.50/month × 2.5 = ~$21
   
4. Network Egress:                 ~$5/month × 2.5 = ~$12

Total estimated burn:              ~$190 of $300 credit
Remaining at shutdown:             ~$110
```

### Why 24/7 Was Required
- MT5 market data only available while connected
- No webhook or push notification from broker
- Bot uses polling (`time.sleep(60)`) — must be running to detect signals
- Missing a signal = missing a trade opportunity

### Cost Optimization Failure
- **No auto-shutdown:** VM ran 24/7 including weekends (markets closed Sat-Sun)
- **No serverless option:** MT5 requires Windows desktop environment → cannot use Cloud Functions or containers
- **Windows tax:** ~30% premium over Linux VM for same specs

---

## Appendix: Final Statistics

```
Account:         415089870 (Demo, Hedge, Standard)
Initial Balance: $300.00
Final Balance:   $191.28
Net P/L:         -$108.72 (-36.2%)

Total Trades:    223
Win Rate:        31.84% (71 wins / 152 losses)
Profit Factor:   0.96
Sharpe Ratio:    0.06

Gross Profit:    $2,410.06
Gross Loss:      -$2,518.78

Avg Win:         $33.94
Avg Loss:        -$16.57
Payoff Ratio:    2.05:1

Max Drawdown:    90.98% ($820.85)
Largest Win:     +$424.55 (Gold TP)
Largest Loss:    -$355.37 (Gold SL)

Max Consecutive Wins:   5
Max Consecutive Losses:  9
```

---

*Document generated: May 3, 2026*
