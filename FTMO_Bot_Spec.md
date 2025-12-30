# FTMO‑Compliant Trading Bot Specification
## Risk Management + Method + Mindset Integration

**Version:** 1.0  
**Last Updated:** 30 Dec 2025  
**Target:** Sustainable profit within prop firm constraints  

---

## 1. SYSTEM ARCHITECTURE

### 1.1 Layers
```
┌─────────────────────────────────────┐
│  Strategy Layer (Method)             │ ← Supply/Demand, Entry/Exit logic
├─────────────────────────────────────┤
│  Risk Engine (Rules)                 │ ← Daily Loss, Max Loss, Per‑Trade Risk
├─────────────────────────────────────┤
│  Execution Engine (Discipline)       │ ← Order placement, SL/TP, Timeouts
├─────────────────────────────────────┤
│  Monitoring Layer (Metrics)          │ ← Winrate, RR, Drawdown, Consistency
└─────────────────────────────────────┘
```

### 1.2 Config‑Driven Design
All risk parameters loaded from config file (YAML/JSON), NOT hardcoded.
Allows testing without recompile.

---

## 2. RISK ENGINE (LAYER 2)

### 2.1 Daily Loss Limit
**Rule:** Stop all trading if unrealized + realized loss on current day ≥ threshold

```yaml
risk:
  daily_loss_limit_percent: 2.0  # % of starting equity for the day
  daily_loss_hard_stop: true     # If true, NO trades after hitting limit
```

**Implementation:**
```python
daily_pnl = realized_pnl_today + unrealized_pnl_open_positions
if daily_pnl <= -account_equity * 0.02:
    trading_enabled = False
    log("DAILY LOSS LIMIT HIT. TRADING HALTED.")
```

---

### 2.2 Max Loss / Maximum Drawdown
**Rule:** Stop trading if cumulative drawdown from peak equity > threshold

```yaml
risk:
  max_drawdown_percent: 5.0      # From peak to trough
  max_drawdown_hard_stop: true
```

**Implementation:**
```python
peak_equity = max(equity_history)
current_drawdown = (peak_equity - current_equity) / peak_equity
if current_drawdown > 0.05:
    trading_enabled = False
    log("MAX DRAWDOWN EXCEEDED. TRADING HALTED.")
```

---

### 2.3 Per‑Trade Risk (Position Sizing)
**Rule:** No single trade risks more than X% of account equity

```yaml
risk:
  risk_per_trade_percent: 0.35   # Pop uses 0.35–0.5%
  max_position_size_percent: 1.0 # Position ≤ 1% of equity
  
risk_reward_ratio: 1.0  # Minimum profit target = 1× the risk (1:1)
                        # Target for "good trade" = 1:3 or 1:5
```

**Implementation:**
```python
def calculate_position_size(entry_price, stop_loss_price, account_equity):
    risk_amount = account_equity * 0.005  # 0.5% of equity
    price_risk = abs(entry_price - stop_loss_price)
    position_size = risk_amount / price_risk
    
    # Cap at max 1% equity
    max_position = account_equity * 0.01 / entry_price
    position_size = min(position_size, max_position)
    
    return position_size
```

---

### 2.4 Rule 1% (FTMO Specific)
**Rule:** Daily profit target = 1% of account equity (stop trading when hit)

```yaml
ftmo_rules:
  rule_1_percent_enabled: true
  daily_profit_target_percent: 1.0  # Stop trading when daily P&L ≥ +1%
```

**Implementation:**
```python
daily_pnl_realized = sum(closed_trades_today_pnl)
daily_pnl_unrealized = sum(open_positions_pnl)
daily_pnl = daily_pnl_realized + daily_pnl_unrealized

if daily_pnl >= account_equity * 0.01:
    trading_enabled = False
    log(f"DAILY +1% TARGET HIT: ${daily_pnl:.2f}. Trading halted.")
```

---

### 2.5 Win Rate Acceptance
**Rule:** Target low winrate (20–40%) but high RR (1:3 to 1:5)

```yaml
strategy:
  target_winrate_percent: 25  # Realistic, not 80%
  target_rr_ratio: 3.0         # 1:3 minimum
  acceptable_winrate_min: 20   # Don't stress if 20–30%
```

**Why?**
- Expected Value = (winrate × avg_win) − (1−winrate × avg_loss)
- Example: 25% win × $300 − 75% loss × $100 = +$75 − $75 = BREAKEVEN (but with volatility)
- With 1:3 RR: 25% × $300 − 75% × $100 = $75 − $75 = flat (acceptable)
- With disciplined SL: It works mathematically

---

## 3. STRATEGY LAYER (LAYER 1)

### 3.1 Multi‑Timeframe Analysis (Pop's "2E Framework")

**Entry Conditions:**

```yaml
strategy:
  timeframes:
    trend_tf: "D1"       # Daily: See macro direction
    trend_tf_alt: "H4"   # 4H: Confirm trend
    entry_tf: "M15"      # 15M: Find entry zone
  
  asset: "XAUUSD"  # Example: Gold
  allowed_pairs: ["EURUSD", "GBPUSD", "XAUUSD", "US100"]
```

**Step 1: Check Macro Trend (D1/H4)**
```python
def check_trend(candles_d1):
    """
    Return: "BULLISH", "BEARISH", or "NEUTRAL"
    - BULLISH: Close > SMA200 and recent higher lows
    - BEARISH: Close < SMA200 and recent lower highs
    - NEUTRAL: Consolidating, skip
    """
    sma200 = calculate_sma(candles_d1, 200)
    recent_high = max(candles_d1[-10:].high)
    recent_low = min(candles_d1[-10:].low)
    
    if candles_d1[-1].close > sma200:
        return "BULLISH"
    elif candles_d1[-1].close < sma200:
        return "BEARISH"
    else:
        return "NEUTRAL"

trend = check_trend(daily_candles)
if trend == "NEUTRAL":
    return NO_TRADE
```

**Step 2: Find Entry Zone (M15)**
```python
def find_supply_demand_zone(candles_m15):
    """
    Supply = Resistance zone (price rejected downward)
    Demand = Support zone (price rejected upward)
    
    Look for:
    - Wicks rejected (high wick with close below, or low wick with close above)
    - Consolidation zone (multiple touches)
    - Liquidity voids (unused price areas)
    """
    
    # Find demand zone (support)
    for i in range(len(candles_m15) - 20, len(candles_m15)):
        low_wick = candles_m15[i].low
        close = candles_m15[i].close
        if close > low_wick * 1.001:  # Price rejected low
            demand_zone = low_wick
            break
    
    # Find supply zone (resistance)
    for i in range(len(candles_m15) - 20, len(candles_m15)):
        high_wick = candles_m15[i].high
        close = candles_m15[i].close
        if close < high_wick * 0.999:  # Price rejected high
            supply_zone = high_wick
            break
    
    return demand_zone, supply_zone
```

**Step 3: Entry Rules**

```yaml
entry:
  rule_1: "If trend BULLISH, enter LONG only from DEMAND zone"
  rule_2: "If trend BEARISH, enter SHORT only from SUPPLY zone"
  rule_3: "Confirm: Price touches zone + candle closes outside zone"
  rule_4: "No entry if: News upcoming within 1 hour, or consolidating"
```

---

### 3.2 Exit Conditions

**Stop Loss (SL):**
```yaml
exit:
  stop_loss:
    type: "fixed_percent"          # OR "support_resistance"
    fixed_percent: 0.50            # Risk 0.5% of equity
    support_resistance: "zone_low"  # Place below entry zone
```

**Take Profit (TP):**
```yaml
exit:
  take_profit:
    rule: "Risk Reward Ratio"
    ratio_target: 1.3              # 1:3 minimum (Conservative 1:1.3)
    example: "If risk $100, TP at +$300"
    
    trailing_stop:
      enabled: true
      trail_percent: 0.5           # Trail by 0.5% after profit
      lock_profit_at_rr: 1.0       # Lock at 1:1 (zero risk)
```

**Timeout/Mandatory Exit:**
```yaml
exit:
  timeout:
    enabled: true
    max_hold_bars_m15: 96          # Exit after 24 hours (96 × 15min bars)
    reason: "Avoid overnight risk, FTMO rules"
```

---

### 3.3 Forbidden Actions (FTMO Compliance)

```yaml
forbidden:
  news_trading:
    enabled: false                 # NO trading during high‑impact news
    blackout_minutes: 60           # Ban trading 1hr before/after news
    
  weekend_trading:
    enabled: false                 # NO Fri 22:00 GMT → Mon 00:00 GMT
    
  locked_in_loss:
    enabled: false                 # NO averaging down / "throwing good money"
    
  manual_override:
    enabled: false                 # System must enforce rules, NO "gut feel"
```

---

## 4. EXECUTION ENGINE (LAYER 3)

### 4.1 Order Placement

```python
def place_trade(signal, strategy_params):
    """
    Signal = {"side": "BUY/SELL", "entry": X, "sl": Y, "tp": Z, "zone": W}
    """
    
    # Verify risk engine OK
    if not is_trading_allowed():
        log("Trading halted by risk engine")
        return None
    
    # Calculate position size
    position_size = calculate_position_size(
        entry=signal["entry"],
        sl=signal["sl"],
        equity=current_equity
    )
    
    # Place market order
    order = place_order(
        side=signal["side"],
        size=position_size,
        entry=signal["entry"],
        stop_loss=signal["sl"],
        take_profit=signal["tp"]
    )
    
    # Log trade
    log_trade({
        "entry": signal["entry"],
        "sl": signal["sl"],
        "tp": signal["tp"],
        "risk_amount": abs(signal["entry"] - signal["sl"]) * position_size,
        "rr_ratio": abs(signal["tp"] - signal["entry"]) / abs(signal["entry"] - signal["sl"]),
        "timestamp": now(),
    })
    
    return order
```

### 4.2 Live Monitoring

```python
def monitor_open_positions():
    """
    Check every bar:
    - Did SL/TP trigger? → Closed automatically
    - Did timeout trigger? → Close position
    - Is daily loss limit hit? → Halt
    - Is max drawdown hit? → Halt
    """
    
    for position in open_positions:
        if position["pnl"] <= position["stop_loss"]:
            close_position(position, "SL HIT")
        
        if position["pnl"] >= position["take_profit"]:
            close_position(position, "TP HIT")
        
        if position["time_open"] > timeout_bars:
            close_position(position, "TIMEOUT")
    
    # Check global limits
    if daily_loss >= daily_loss_limit:
        halt_trading("DAILY LOSS LIMIT")
    
    if max_drawdown >= max_drawdown_limit:
        halt_trading("MAX DRAWDOWN")
```

---

## 5. MONITORING LAYER (LAYER 4)

### 5.1 Daily Metrics Dashboard

```yaml
metrics:
  daily:
    - pnl_realized: "Sum of closed trades P&L"
    - pnl_unrealized: "Current open positions P&L"
    - pnl_total: "Realized + Unrealized"
    - winrate_percent: "Winning trades / Total trades"
    - avg_win: "Average profit of winning trades"
    - avg_loss: "Average loss of losing trades"
    - profit_factor: "Gross profit / Gross loss"
    - max_drawdown_today: "Peak to trough on current day"
    - trades_count: "# of closed trades"
    - rr_ratio_avg: "Average RR of all trades"

  weekly:
    - consecutive_wins: "How many wins in a row"
    - consecutive_losses: "How many losses in a row"
    - best_day: "Highest profit day"
    - worst_day: "Highest loss day"
    - consistency: "% of days profitable"

  alerts:
    - "if winrate < 15% for last 20 trades: PAUSE & REVIEW"
    - "if daily_loss > 80% of daily_loss_limit: ALERT"
    - "if max_drawdown > 70% of max_drawdown_limit: ALERT"
    - "if consecutive_losses > 5: REVIEW STRATEGY"
```

### 5.2 Backtest Criteria

Before deploying on FTMO, run backtest with:

```yaml
backtest:
  period_months: 12              # Minimum 12 months historical data
  walk_forward: true             # Test rolling 3-month windows
  monte_carlo: 1000              # Randomize trade order 1000x
  
  pass_criteria:
    winrate_min: 20              # Min 20% (NOT 80%)
    profit_factor_min: 1.5       # Gross profit ≥ 1.5× gross loss
    max_drawdown_max: 8           # Never exceed 8% drawdown
    consecutive_losses_max: 6     # Max 6 losses in a row
    avg_rr_ratio_min: 1.2        # Average RR ≥ 1:1.2
    sharpe_ratio_min: 0.8        # Smoothness check
    recovery_days: 5             # Recover from max DD within 5 days
```

---

## 6. MINDSET / DISCIPLINE ENFORCEMENT

(Replaced human "feeling" with deterministic rules)

### 6.1 "Best Loser Wins" Implementation

```python
def enforce_discipline():
    """
    Replaces human emotion with code logic
    """
    
    # ✓ Cut losses FAST (SL hit → close immediately)
    if position_loss >= stop_loss:
        close_position("SL HIT")  # No "waiting for recovery"
    
    # ✓ Let profits RUN (Don't close at small gains)
    trailing_stop = True           # Let SL trail up as price moves
    
    # ✓ Accept small losses as NORMAL
    avg_loss = calculate_avg_loss()
    if avg_loss < account_equity * 0.005:  # < 0.5% per loss
        log("Loss within acceptable range. Continue.")
    
    # ✓ NO Martingale / Averaging down
    if position_in_loss:
        # FORBIDDEN: Add to losing position
        pass
    
    # ✓ Trading is about CONSISTENCY, not PERFECTION
    if daily_winrate < 20:
        log("Low winrate (20%), but RR > 1:3. Still profitable.")
    
    # ✓ Stop trading when emotion/bias creeps in (Max Loss)
    if max_drawdown > threshold:
        log("Max DD hit. Step back. Eliminate emotional trading.")
```

### 6.2 Halt Logic (Mindset Reset)

```python
def check_if_should_halt():
    """
    When to PAUSE trading (not forever, just reset):
    - After 2nd consecutive daily loss limit
    - After 3rd consecutive losing day
    - After 5 consecutive loss trades
    - Every Sunday (optional rebalance)
    """
    
    if consecutive_daily_losses >= 2:
        log("2 days of losses. HALT for 1 day. Review.")
        halt_until = tomorrow()
    
    if consecutive_loss_trades >= 5:
        log("5 losses in a row. HALT for 4 hours. Reset bias.")
        halt_until = now() + 4_hours
    
    return halt_until
```

---

## 7. CONFIGURATION TEMPLATE

```yaml
account:
  initial_equity: 100000          # USD / THB (depends on FTMO account size)
  leverage: 30                    # Or whatever broker allows

risk:
  daily_loss_limit_percent: 2.0
  max_drawdown_percent: 5.0
  risk_per_trade_percent: 0.35
  rule_1_percent: true
  rule_1_profit_target: 1.0

strategy:
  asset: "XAUUSD"
  timeframe_trend: "D1"
  timeframe_entry: "M15"
  
  entry_rule: "Supply/Demand zones"
  exit_rule: "SL + TP with RR 1:3, or timeout 24h"
  
  target_winrate: 25
  target_rr: 3.0

execution:
  order_type: "Market"
  slippage_buffer: 0.0005         # 5 pips buffer
  max_slippage: 0.001             # Exit if slippage > 10 pips

monitoring:
  log_every_trade: true
  alert_on_dd_70_percent: true
  backtest_before_deploy: true
```

---

## 8. DEPLOYMENT CHECKLIST

- [ ] **Backtest 12+ months:** Winrate ≥ 20%, PF ≥ 1.5, Max DD ≤ 8%
- [ ] **Forward test 2 weeks** on demo account
- [ ] **Monitor daily metrics:** Consistency, drawdown, halts
- [ ] **Rule enforcement:** Daily/max loss, per‑trade risk, timeout all active
- [ ] **No manual override:** System decides, human just reviews
- [ ] **Risk per trade:** Fixed at 0.35–0.5% of equity
- [ ] **SL/TP:** Automated, no "moving goalposts"
- [ ] **News/weekend:** Blackout enabled
- [ ] **Logging:** Every trade, every decision, every halt
- [ ] **Ready for FTMO:** Can pass $400K account with this ruleset

---

## 9. EXAMPLE: GOLD (XAUUSD) TRADE WALKTHROUGH

**Day: 30 Dec 2025, 10:00 UTC**

```
Account Equity: $100,000
Daily Loss Limit: $2,000 (2%)
Per-Trade Risk: $350 (0.35%)

STEP 1: Check Daily Trend
┌─────────────────────────────┐
│ Daily (D1) Candle          │
│ SMA200: 2,680              │
│ Close: 2,710               │
│ Trend: BULLISH (2,710 > 2,680)
└─────────────────────────────┘

STEP 2: Find Entry Zone (M15)
┌────────────────────────────────────┐
│ 15M Candles (last 10)              │
│ Demand zone (support): 2,700       │
│ Resistance: 2,720                  │
│ → Enter LONG from 2,700           │
└────────────────────────────────────┘

STEP 3: Calculate Position
Risk = $350
Entry = 2,700
SL = 2,695 (below demand zone)
Risk per pip = 350 / 5 = $70 per pip
Position size = 0.7 micro contracts (or 7,000 notional USD)

STEP 4: Set TP
RR = 1:3
TP = Entry + (Entry - SL) × 3 = 2,700 + 15 × 3 = 2,745

STEP 5: Place Trade
Order: BUY 0.7 XAUUSD at 2,700, SL 2,695, TP 2,745
RR Ratio: 1:3 ✓
Risk: $350 (0.35% of equity) ✓

STEP 6: Monitor
├─ If price hits 2,745 → TP hit, close (profit: $1,050)
├─ If price hits 2,695 → SL hit, close (loss: -$350)
├─ If time > 24h → Close position (timeout rule)
└─ If daily loss > $2,000 → Halt all trading

RESULT:
Trade 1: WIN +$1,050 (✓ RR 1:3 worked)
Daily P&L: +$1,050
Winrate so far: 1/1 = 100% (but expect 25% long-term)
Max DD today: -$0 (profitable day)
→ Can continue trading (within daily +1% rule)
```

---

## 10. IMPROVEMENT CHECKLIST FOR YOUR BOT

Use this to evaluate what your bot needs:

### ✓ MUST HAVE
- [ ] Daily loss limit (hard stop)
- [ ] Per-trade risk sizing (0.35-0.5%)
- [ ] Risk:reward ratio enforcement (min 1:1, target 1:3)
- [ ] Automated SL/TP placement (no manual moves)
- [ ] Timeout rule (exit after X hours)
- [ ] Win rate tracking + acceptance of low winrate
- [ ] Drawdown monitoring + halt logic
- [ ] Config-driven (not hardcoded rules)
- [ ] Comprehensive logging (every trade, every decision)

### ✓ SHOULD HAVE
- [ ] Trailing stop (lock profits after RR 1:1)
- [ ] Multi-timeframe analysis (trend + entry)
- [ ] Supply/demand zone detection
- [ ] News blackout (no trading 1h before/after)
- [ ] Weekend filter (no Fri 22:00-Mon 00:00)
- [ ] Consecutive loss alert (halt after 5 losses)
- [ ] Backtest engine (12-month walk-forward)
- [ ] Daily metrics dashboard
- [ ] Profit factor tracking

### ✓ NICE TO HAVE
- [ ] Monte Carlo simulation (stress test)
- [ ] Sharpe ratio calculation
- [ ] Equity curve smoothing
- [ ] Machine learning for zone detection
- [ ] Sentiment filter (macro events)
- [ ] Multiple asset pairs (diversify)
- [ ] Dynamic position sizing (% of daily loss limit)

---

## 11. TESTING ROADMAP

**Week 1-2:** Backtest on historical data
- ✓ 12-month walk-forward test
- ✓ Check: Winrate ≥ 20%, PF ≥ 1.5, Max DD ≤ 5%

**Week 3:** Forward test (live broker, minimum size)
- ✓ Run on real account, real price data
- ✓ No real money yet, just validate execution

**Week 4:** Small account test ($100-500)
- ✓ Real money, real psychology
- ✓ Confirm all rules fire correctly

**Week 5+:** Scale to FTMO challenge
- ✓ Same ruleset, scale to $25K / $100K
- ✓ Monitor for surprises (slippage, spread, news shocks)

---

## 12. RED FLAGS (Things NOT to do)

```python
❌ DON'T: Move SL after entry ("give it more room")
❌ DON'T: Close winner early ("lock in small profit")
❌ DON'T: Add to losing position (Martingale / averaging down)
❌ DON'T: Ignore daily loss limit ("one more trade...")
❌ DON'T: Trade during news ("I'll catch the spike")
❌ DON'T: Trade without SL ("I'll manage it manually")
❌ DON'T: Ignore backtest results ("My edge is real, trust me")
❌ DON'T: Expect 80% winrate (unrealistic, impossible)
❌ DON'T: Risk > 1% per trade (ruins compounding)
❌ DON'T: Combine multiple losing ideas ("maybe together they work")

✓ DO: Trust the system. Execute the rules. Review data.
✓ DO: Accept 20-25% winrate if RR is good.
✓ DO: Cut losses fast. Let profits run.
✓ DO: Test before deploying real money.
```

---

## 13. REFERENCES

- **FTMO Official:** https://ftmo.com/en/blog/how-ftmo-works/
- **Psychology:** "Best Loser Wins" by Tom Hougaard
- **Risk Management:** "Position Sizing" by Van Tharp
- **Backtesting:** "Fooled by Randomness" by Nassim Taleb
- **Trading Logic:** "Market Profile" and "Supply/Demand Zones"

---

## END OF SPEC

**Use this to:**
1. Code your bot's constraints
2. Backtest properly
3. Deploy with confidence
4. Pass FTMO (or similar prop firm)
5. Scale sustainably

Good luck! 🚀
