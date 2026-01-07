# AntiGravity Bot Configuration
# Mode: PERSONAL WEALTH BUILDING (High Growth)

# Global Strategy Parameters (The Engine)
STRATEGY_PARAMS = {
    'grid_levels': 20,
    'grid_step_percent': 0.005,  # 0.5% Grid Step
    'take_profit_percent': 0.005,# 0.5% TP per grid level
    'ema_period': 200,           # Trend Filter
    'rsi_period': 14,            # Momentum
    'rsi_overbought': 70,        # Don't Buy above this
    'rsi_oversold': 30,          # Don't Sell below this
    'cooldown_minutes': 60,      # Anti-Overtrading (1 Hour)
    'max_active_grids': 5,       # Limit
    'min_atr_period': 14         # Volatility Window
}

# Global Risk Parameters (The Fortress) - FREEDOM EDITION
RISK_PARAMS = {
    # --- Capital Growth Mode (Rich Strategy) ---
    'ftmo_mode': True,               # ENABLED to use Daily Filters
    'daily_loss_limit_pct': 0.07,    # 7% Daily Stop Loss (User Request)
    'daily_profit_target_pct': 0.50, # 50% Daily Target (Effectively "No Cap" - Let it run)
    'max_holding_hours': 9999,       # Disable Time Limit (Swing Trade allowed)
    'max_drawdown_ftmo_pct': 0.15,   # Match Global Max DD
    
    # --- Safety Nets ---
    'max_drawdown_limit': 0.15,      # 15% Max DD (User Spec: 15% + Halt)
    'stop_loss_atr_multiplier': 2.5, 
    
    # --- Position Sizing ---
    'risk_per_trade_pct': 0.02,      # Risk 2% per trade (Optimal Growth)
    'max_leverage_use': 100,         
    
    # --- Advanced Features ---
    'martingale_detection_enabled': True,   
    'floating_loss_limit_pct': 0.15,        # Adjusted to match Max DD
    'losing_streak_threshold': 4,           
    'volatility_scaling_enabled': True,     
}

# Portfolio Config (Backtesting only - Live uses run_mt5_live.py)
PORTFOLIO_CONFIG = [
    {'symbol': 'XAUUSDm', 'type': 'metal'},
    {'symbol': 'BTCUSDm', 'type': 'crypto'},
    {'symbol': 'USOILm',  'type': 'commodity'}
]

# API Configuration
EXCHANGE_ID = 'mt5'
