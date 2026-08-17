# Quant Trading Bot — Changelog & Post-Mortem

> Development history and performance analysis of the Quant Trading Bot algorithmic trading system.

---

## v2.0.0 — "Pullback Sniper" (Feb 22, 2026)

**Complete strategy redesign** after v1.x lost -$207 over 214 trades.

| Component | v1.x (Old) | v2.0 (New) |
|-----------|-----------|------------|
| Entry | EMA crossover | **Pullback to EMA18** |
| Timeframe | H1 | **H4** |
| SL | 2.5× ATR | **1.5× ATR** |
| TP | 5.0× ATR (1:2) | **4.5× ATR (1:3)** |
| ADX | > 25 | **> 20** |
| RSI filter | 20-80 | **35-65 pullback zone** |
| Cooldown | 60 min | **240 min** |

**Math:** Win 35% × 3R − Loss 65% × 1R = **+0.48R expected per trade**

### v2.0 Live Results (Feb 22 → Mar 16, 12 trades)

| Metric | Result |
|--------|--------|
| Net P&L | +$89.95 ($101 → $191) |
| Win Rate | 33% |
| Best Trade | XAUUSDm +$208.87 (TP hit) |
| Worst Trade | XAUUSDm -$90.40 (SL hit) |

---

## v1.x — Original Strategy (Jan 4 → Feb 22, 2026)

### Performance
- **Net P&L:** -$198.67 ($300 → $101)
- **Trades:** 211
- **Win Rate:** 31%
- **Profit Factor:** 0.91
- **Max Drawdown:** 90.98%

### Key Events
- **v1.0.0** (Jan 4) — Initial deployment with EMA crossover + grid logic
- **v1.0.1** (Jan 20) — Removed Oil & Silver (poor performance)
- **v1.1.0** (Feb 2) — Added Max Loss Cap $50/trade
- **v1.2.0** (Feb 7) — Fixed Max Loss Cap bug (wasn't applied to live script)
- **v1.3.0** (Feb 7) — Added ADX trend filter
- **v1.3.1** (Feb 7) — Changed to dynamic 2% risk (removed fixed $50 cap)

---

## v2.5.0 — Project Retirement & Post-Mortem (Mar 16, 2026)

### Decision: Stop live trading

**Final Account Status:**
- Starting Balance: $300
- Final Balance: $191.28
- Net Loss: -$108.72 (-36%)
- Total Trades: 223

### Root Cause Analysis

The strategy's R:R was sound (avg win $33.94 vs avg loss $16.57 = 2:1 ratio), but the system failed due to **capital-instrument mismatch**:

```
Problem:
  Gold minimum lot = 0.01 (cannot go lower)
  0.01 lot × $90 ATR = ~$90 risk per trade
  Account balance = $191
  Actual risk = 47% per trade (!)
  Intended risk = 2% per trade

  → Position sizing algorithm cannot function
    when broker minimum lot exceeds risk budget
```

### Lessons Learned

1. **Position sizing is constrained by broker minimums, not just math.**
   The Kelly Criterion and fractional risk models assume infinitely divisible position sizes. In practice, minimum lot sizes create a hard floor on risk-per-trade that can exceed the intended risk budget on small accounts.

2. **Asset selection must consider capital requirements.**
   Gold (XAUUSDm) requires ~$4,500 minimum balance to maintain 2% risk-per-trade at 0.01 lot. BTC was more appropriate for a $300 account.

3. **Profit Factor 0.96 on a $300 account is not failure — it's a capital problem.**
   The entry logic was competitive (R:R 2:1), but the edge was destroyed by oversized positions relative to the account.

4. **Max Loss Cap of $50 was bypassed by market structure.**
   Fixed dollar caps don't work when the instrument's minimum position size already exceeds the cap.

### What Worked
- Gold trending moves: +$208, +$181, +$168, +$153, +$424 individual trades
- BTC short during bearish periods: consistent $20-50 wins
- v2.0 Pullback Sniper logic: better entry timing than v1.x

### What Failed
- Running Gold on a $300 Standard account
- v1.x overtrading (211 trades in 49 days)
- Silver position (-$157 single trade, asset removed too late)

### Architecture Changes
- Restructured from `modules/` to `core/` (Pipeline Architecture)
- Removed 18 unused files (VPS docs, deployment scripts)
- Added Backtesting Engine with Monte Carlo simulation

---

*Last updated: March 16, 2026*
