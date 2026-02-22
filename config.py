# AntiGravity Bot Configuration
# Mode: PERSONAL WEALTH BUILDING (High Growth)
# v2.0: Pullback Sniper Strategy

# Global Strategy Parameters (The Engine)
STRATEGY_PARAMS = {
    "grid_levels": 20,
    "grid_step_percent": 0.005,  # 0.5% Grid Step
    "take_profit_percent": 0.005,  # 0.5% TP per grid level
    "ema_period": 200,  # Trend Filter
    "ema_fast": 18,  # Fast EMA for crossover
    "ema_medium": 35,  # Medium EMA for crossover
    "trend_ma_period": 200,  # Macro trend filter
    "rsi_period": 14,  # Momentum
    "rsi_overbought": 80,  # Extreme OB (safety net)
    "rsi_oversold": 20,  # Extreme OS (safety net)
    # v2.0 NEW: Pullback Sniper Parameters
    "rsi_pullback_low": 35,  # RSI pullback zone lower bound
    "rsi_pullback_high": 65,  # RSI pullback zone upper bound
    "pullback_atr_threshold": 0.5,  # Price must be within 0.5x ATR of EMA18
    "adx_threshold": 20,  # v2.0: Lowered from 25 to 20
    "cooldown_minutes": 240,  # v2.0: 4 hours (H4 timeframe)
    "max_active_grids": 5,  # Limit
    "min_atr_period": 14,  # Volatility Window
}

# Global Risk Parameters (The Fortress) - FREEDOM EDITION
RISK_PARAMS = {
    # --- Capital Growth Mode (Rich Strategy) ---
    "ftmo_mode": False,  # DISABLE DAILY LIMITS
    "daily_loss_limit_pct": 0.10,  # Not used
    "daily_profit_target_pct": 0.00,  # Not used
    "max_holding_hours": 9999,  # Disable Time Limit
    "max_drawdown_ftmo_pct": 0.15,  # 15%
    # --- Safety Nets ---
    "max_drawdown_limit": 0.15,  # 15% Max DD
    "stop_loss_atr_multiplier": 1.5,  # v2.0: Tighter SL (pullback entry = closer SL)
    # --- Position Sizing ---
    "risk_per_trade_pct": 0.02,  # Risk 2% per trade
    "max_loss_per_trade_usd": 50,  # MAX LOSS CAP: Never lose more than $50 per trade
    "max_leverage_use": 100,
    # --- Advanced Features ---
    "martingale_detection_enabled": True,
    "floating_loss_limit_pct": 0.15,  # Adjusted to match Max DD
    "losing_streak_threshold": 4,
    "volatility_scaling_enabled": True,
}

# Portfolio Config (Backtesting only - Live uses run_mt5_live.py)
PORTFOLIO_CONFIG = [
    {"symbol": "XAUUSDm", "name": "Gold", "risk_weight": 1.0},
    # Silver REMOVED - Too risky for small accounts
    {"symbol": "BTCUSDm", "name": "Bitcoin", "risk_weight": 0.8},
]


# API Configuration
EXCHANGE_ID = "mt5"
