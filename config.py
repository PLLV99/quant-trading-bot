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
    # --- Capital Growth Mode ---
    'ftmo_mode': False,              # DISABLE FTMO RULES
    
    # --- Safety Nets (Loose) ---
    'max_drawdown_limit': 0.30,      # 30% Max Drawdown (Aggressive Growth)
    'stop_loss_atr_multiplier': 2.5, # Tighter Stops
    
    # --- Position Sizing ---
    'risk_per_trade_pct': 0.03,      # Risk 3% per trade (Aggressive Compounding)
    'max_leverage_use': 100,         # Use up to 1:100 leverage
    
    # --- Advanced Features ---
    'martingale_detection_enabled': True,   # Prevention
    'floating_loss_limit_pct': 0.10,        # 10% Floating Loss Limit
    'losing_streak_threshold': 4,           # 4 losses -> Reduce size
    'volatility_scaling_enabled': True,     # Adapt to market chaos
}

# Portfolio Config (Backtesting only - Live uses run_mt5_live.py)
PORTFOLIO_CONFIG = [
    {'symbol': 'XAUUSDm', 'type': 'metal'},
    {'symbol': 'BTCUSDm', 'type': 'crypto'},
    {'symbol': 'USOILm',  'type': 'commodity'}
]

# API Configuration
EXCHANGE_ID = 'mt5'
