# Anti-Fragile Trading Bot Specification
## "The Fortress" Architecture & Sniper Execution

**Version:** 2.0 (Live Codebase Synchronization)
**Last Updated:** 2026-01-16
**Modes:** Personal Wealth Building (Default) / FTMO Compliance (Optional Switch)

---

## 1. SYSTEM ARCHITECTURE

The system is divided into modular engines, designed for resilience ("Anti-Fragility") rather than just optimization.

### 1.1 Core Modules (`/modules`)
| Module | Class | Responsibility |
| :--- | :--- | :--- |
| `strategy_engine.py` | `StrategyEngine` | **The Brain:** Generates signals based on Price Action, Indicators, and Volatility. |
| `risk_manager.py` | `RiskManager` | **The Fortress:** Limits downside, manages position sizing, and prevents blowups. |
| `data_loader.py` | `DataLoader` | **The Feeder:** Fetches historical and live market data (MT5/CSV). |
| `backtester.py` | `Backtester` | **The Simulation:** Runs strategy against historical data to validate logic. |

---

## 2. STRATEGY ENGINE (`StrategyEngine`)

The bot currently implements two distinct strategy modes, selectable via `config.py`.

### 2.1 Mode A: Dynamic Grid (Legacy/Stabilizer)
*Designed for ranging markets to harvest volatility.*

*   **Logic:** Creates a "Breathing Grid" that expands/contracts with volatility (ATR).
*   **Dynamic Step:** `Grid Step = Base Step * (Current ATR / Base ATR)`
*   **Trend Filter:** Trades only in direction of Trend (EMA 200) or Both if Neutral.
*   **Entry:** Limit Orders placed above/below current price.
*   **Safety:** Grid pauses if Market enters "Squeeze" (Low Volatility) or Extreme Trend.

### 2.2 Mode B: Gold Heikin Ashi (The Sniper)
*Designed for impulsive trend moves (XAUUSD, BTC).*

*   **Candles:** Uses **Heikin Ashi** internally to smooth noise.
*   **Setup Conditions:**
    1.  **Macro Trend:** Price > EMA 200 (Bullish) or Price < EMA 200 (Bearish).
    2.  **Momentum:** RSI is favorable (e.g., 45-80 for Longs, 20-55 for Shorts).
    3.  **Trigger:** EMA 18 crosses EMA 35 (Bullish/Bearish Crossover).
*   **Exit:** Opposite Crossover or Stop Loss.

### 2.3 Mode C: Leverage Snowball (Future / Cent Account Only)
*Designed for exponentially growing small accounts using House Money.*

*   **Prerequisite:** MUST use a **Cent Account** to allow micro-granularity.
*   **Concept:**
    1.  **Entry:** Start with minimal risk (Effective Leverage 1:1).
    2.  **Pyramiding:** If Price > EMA 200 (Trend) AND Position is in Profit, use unrealized profit (Margin) to open more positions.
    3.  **Risk Free:** Once initial capital is doubled, withdraw principal. Trade only with profits.
    4.  **Trimming:** If Floating Profit > 20% of Balance, close 50% of positions to lock in cash flow.
*   **Status:** Pending Migration to Cent Account (Phase 3).

---

## 3. RISK MANAGER ("THE FORTRESS")

The `RiskManager` class implements advanced logic to protect capital. It operates independently of the Strategy to act as a "Circuit Breaker".

### 3.1 Core Constraints (Configurable)
*   **Max Drawdown:** Hard limit (Default: 15% for Personal, 5-10% for FTMO).
*   **Position Sizing:** Based on **Risk Per Trade** (e.g., 2% of Equity) divided by Stop Loss Distance.
*   **Stop Loss:** Dynamic based on ATR (e.g., 2.5x ATR).

### 3.2 Advanced Defense Mechanisms (Implemented)
1.  **Martingale Detection:**
    *   *Monitors:* Last 5 trade sizes.
    *   *Action:* If 3+ consecutive trades increase in size (dangerous doubling), **RESET** lot size to minimum.
    
2.  **Losing Streak Circuit Breaker:**
    *   *Monitors:* Consecutive losses.
    *   *Action:* If losses > `losing_streak_threshold` (e.g., 4), **REDUCE** risk by 50% until a win occurs.

3.  **Volatility Scaling:**
    *   *Monitors:* Current ATR vs "Normal" ATR.
    *   *Action:* 
        *   **High Volatility:** Reduce position size (0.5x).
        *   **Low Volatility:** Slightly increase position size (1.25x).

4.  **Floating Loss Guard:**
    *   *Monitors:* Unrealized PnL.
    *   *Action:* If Floating Loss > Limit (e.g., 15%), **BLOCK** new trades to prevent over-exposure.

---

## 4. CONFIGURATION (`config.py`)

Current active configuration structure.

### 4.1 Global Strategy Params
```python
STRATEGY_PARAMS = {
    'grid_levels': 20,           # Depth of grid
    'ema_period': 200,           # Macro Trend
    'cooldown_minutes': 60,      # Anti-Overtrading
    'min_atr_period': 14         # Volatility Window
}
```

### 4.2 Risk Params (Freedom Edition)
```python
RISK_PARAMS = {
    'ftmo_mode': False,          # True = Enforce strict daily limits
    'max_drawdown_limit': 0.15,  # 15% Hard Stop
    'risk_per_trade_pct': 0.02,  # 2% Capital Risk
    'martingale_detection_enabled': True,
    'volatility_scaling_enabled': True
}
```

---

### 3.3 Implemented Upgrades (Phase 2 Completed)
*   **Bollinger Band Squeeze:** Prevents trading during extreme low volatility (BB Width < 0.15%).
*   **Re-enabled EMA 200:** Returned to 200 EMA for stronger trend filtering.

### 5.2 Adaptive Parameters
*   **Goal:** Adjust EMA/RSI periods based on market regime.
*   **Logic:** 
    *   High Volatility -> Longer EMAs (Filter noise).
    *   Low Volatility -> Shorter EMAs (Faster reaction).

---
---

## 6. DEPLOYMENT SNAPSHOT (v3.0 Live)
*Last Updated: 2026-01-23*

### 6.1 Current Operational Status
*   **Active Assets:** XAUUSDm (Gold), BTCUSDm (Bitcoin)
*   **Disabled Assets:** USOILm (Oil) - ❌ REMOVED due to high risk/volatility for this account size.
*   **Target Account:** Moving to **Cent Account** in Phase 2.

### 6.2 Active Roadmap
1.  **Phase 1 (Current):** Stabilize and grow $300 -> $500 using Trend Sniper (Mode B).
2.  **Phase 2:** Migrate to Cent Account for granular sizing.
3.  **Phase 3:** Activate "Leverage Snowball" (Mode C).

---

## 7. AI SAFETY ANALYSIS (From NotebookLM Review)
*Critical feedback incorporated on 2026-01-23*

### 7.1 Confirmed Decisions
*   ✅ **Killing USOIL:** Statistically correct. $10 per point risk is too high (3.3% risk) for a $300 account.
*   ✅ **200 EMA Filter:** Necessary to stop fighting trends, but must be aware of "Lagging" nature during V-Shape reversals.

### 7.2 The "Glass Cannon" Warning (For Snowball Mode)
*   **Risk:** Pyramiding increases average entry price. A single flash crash can wipe out all profit + capital.
*   **Mandatory Fix:** When implementing Mode C (Snowball), code MUST include **"Aggressive Trailing Stop"** that moves SL to Breakeven for *every* new layer added.

### 7.3 The Cent Account Mandate
*   **Verdict:** Moving to Cent is not optional; it is mathematically required for the "Snowball" strategy to work safely on <$5000 capital.

**End of Specification**
