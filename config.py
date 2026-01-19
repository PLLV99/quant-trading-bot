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
    "ftmo_mode": False,  # DISABLE DAILY LIMITS (User: "Old version worked")
    "daily_loss_limit_pct": 0.10,  # Placeholder (Not used)
    "daily_profit_target_pct": 0.00,  # Placeholder
    "max_holding_hours": 9999,  # Disable Time Limit (Swing Trade allowed)
    "max_drawdown_ftmo_pct": 0.15,  # Match Global Max DD
    # --- Safety Nets ---
    "max_drawdown_limit": 0.15,  # 15% Max DD (User Spec: 15% + Halt)
    "stop_loss_atr_multiplier": 2.5,
    # --- Position Sizing (BALANCED: ~10-15% monthly target) ---
    "risk_per_trade_pct": 0.03,  # Risk 3% per trade (balanced)
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
    {"symbol": "USOILm", "name": "Oil", "risk_weight": 0.6},
]

# API Configuration
EXCHANGE_ID = "mt5"
