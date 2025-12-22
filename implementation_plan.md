# Quantitative Trading Bot Implementation Plan

## Goal Description
Develop a quantitative trading bot that generates consistent 4-5% monthly profits using a Grid Trading strategy. The logic is inspired by the risk management principles of Edward Thorp (Kelly Criterion), the quantitative rigor of Jim Simons, and the "Anti-Fragile" concepts of Nassim Taleb.

## User Review Required
> [!IMPORTANT]
> - Confirm the specific tokens/pairs for the grid (e.g., BTC/USDT, ETH/USDT).
> - Review the risk limits (max drawdown tolerance defined in Safety Core).

## Proposed Changes

### Documentation
- [NEW] `docs/risk_protocols.md`: Detailed "Safety First" rules documentation based on World-Class investors.

### Safety Core (Priority #1) - "The Fortress" (Anti-Fragile Design)
#### [MODIFY] `trading_bot/modules/risk_manager.py`
- **Dynamic Volatility Sizing (Ray Dalio)**:
    - *Logic*: Position sizing must be *inverse* to volatility.
    - *Action*: If Crypto volatility (ATR) spikes 2x, automatically cut position size by 50%. This keeps dollar-risk constant regardless of market chaos.
- **Adaptive Stops (Turtle Trading)**:
    - *Logic*: Use ATR (Average True Range) for stops to respect "Market Noise".
    - *Action*: Implement **3x ATR** stops (instead of fixed %). This prevents getting shaken out by normal crypto swings.
- **Smart Circuit Breaker (Anti-Fragile)**:
    - *Logic*: "Bend, don't break."
    - *Action*: If Max Drawdown > 15%, reduce *leverage/size* by 50% instead of halting operations completely. This allows the bot to recover safely.
- **Kelly Criterion Sizing (Edward Thorp)**:
    - *Logic*: Implement "0.5x Fractional Kelly" to mathematically calculate the optimal bet size vs. bankroll.

### Strategy Logic - "The Engine" (Jim Simons Style)
#### [MODIFY] `trading_bot/modules/strategy_engine.py`
- **Dynamic Grid Spacing (Anti-Fragile)**:
    - *Logic*: Grid spacing should breathe with volatility.
    - *Action*: `Grid Step = Base Step * (Current ATR / Base ATR)`.
    - *Result*: In high vol, grid widens (captures big swings, fewer fees). In low vol, grid tightens (scalps small moves).
- **Trend Following Filters (Simons)**:
    - *Logic*: Add signal processing. Do not open Long Grids if the primary trend (Moving Average/MACD) is Bearish.
- **API Health Check (Data Integrity)**:
    - *Logic*: Ensure data is "fresh" before calculating any signal. If API latency is high, pause execution to prevent trading on stale data.

## Verification Plan

### Automated Tests
- Run `python main.py --mode backtest` to verify logic against historical data.

### Manual Verification
- Run `python main.py --mode paper` and monitor console output for trade signals vs. known indicators.
