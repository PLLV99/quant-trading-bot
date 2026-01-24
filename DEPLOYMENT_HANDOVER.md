# 🦅 The AntiGravity Trading System (v3.0) - Comprehensive Report
*For AI Analysis / NotebookLM Review*

---

## 1. Executive Summary
**Goal:** Grow a small $300 account to $5000+ avoiding liquidation.
**Current Status:** Recovering from high drawdown. Shifted from "Martingale Grid" to "Trend Sniper".
**Key Action:** Stopped trading Oil (USOIL). Focusing on Gold (XAUUSD) & Bitcoin (BTCUSD).

---

## 2. Historical Performance (The Problem)
*Analysis of previous ~160 trades (Version 2.0 Logic):*
*   **Win Rate:** ~30% (Too low for 2.0 Strategy)
*   **Max Drawdown:** 72% (Critically high - caused by Martingale doubling on Oil)
*   **Profit Factor:** 0.92 (Losing money slightly)
*   **Root Cause:**
    1.  Grid trading against strong trends (fighting the market).
    2.  Martingale doubling lot sizes during losses.
    3.  Trading low-margin assets (Oil) with too small effective portfolio.

---

## 3. The Solution: Version 3.0 "Sniper & Squeeze"
*Implemented Jan 2026 to fix above issues.*

### A. Strategy Logic (Trend Following)
1.  **Macro Filter:** Price MUST be above **200 EMA** to Buy (or below to Sell). No more fighting trends.
2.  **Volatility Filter (The Squeeze):** If Bollinger Band Width < 0.15%, **HALT TRADING**. Wait for breakout.
3.  **Entry Trigger:** EMA Crossover (Fast/Slow) confirmed by Heikin Ashi candles.

### B. Risk Management (The Fortress)
1.  **Martingale:** ❌ **DISABLED**. No more increasing lots after losses.
2.  **Stop Loss:** Dynamic based on ATR (Volatility).
3.  **Asset Selection:** Removed USOIL. Trade only High-Beta (Gold/BTC) that trends well.

---

## 4. Future Roadmap: "Leverage Snowball" (Mode C)
*Strategies for Phase 2 (Cent Account Migration)*

**Concept:** Since $300 is too small for proper position sizing on Standard accounts, we plan to move to a Cent Account (30,000 cents).

**The "Snowball" Plan:**
1.  **Entry:** Open initial position with minimal risk (0.01 Cent Lot).
2.  **Accumulation:** If Price > 200 EMA and trade is profitable -> Use "House Money" (Unrealized Profit) to add positions.
3.  **Risk Free:** Once floated profit > Initial Risk, move Stop Loss to Breakeven.
4.  **Cash Out:** Trim 50% of positions when Floating Profit hits 20% of Balance.

---

## 5. Deployment Instructions (For Manual Review)
1.  **Immediate:** Stop old bot.
2.  **Sunday Market Open:** Manually close all Legacy positions (Gold +$150, Oil +$3).
3.  **Launch:** Start v3.0 script (`run_mt5_live.py`) on clean portfolio.

---

## ❓ Questions for Analysis (Ask NotebookLM)
1.  Is the shift from Martingale to Trend Sniper (200 EMA) sufficient to fix the 72% drawdown history?
2.  Does the "Leverage Snowball" strategy on a Cent Account mathematically succeed better than standard DCA for Gold?
3.  Are there any blind spots in the "Bollinger Squeeze" filter that could miss breakouts?
