# AntiGravity Bot Configuration
# Mode: PERSONAL WEALTH BUILDING (High Growth)

# Global Strategy Parameters (The Engine)
STRATEGY_PARAMS = {
    "grid_levels": 20,
    "grid_step_percent": 0.005,  # 0.5% Grid Step
    "take_profit_percent": 0.005,  # 0.5% TP per grid level
    "ema_period": 200,  # Trend Filter
    "rsi_period": 14,  # Momentum
    "rsi_overbought": 80,  # Loosened from 70 (more trades)
    "rsi_oversold": 20,  # Loosened from 30 (more trades)
    "cooldown_minutes": 60,  # Anti-Overtrading (1 Hour)
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
    "stop_loss_atr_multiplier": 2.5,
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
