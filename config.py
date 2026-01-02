# Grid Trading Configuration
# NOTE: This config is used by main.py for BACKTESTING ONLY.
# The live MT5 bot (scripts/run_mt5_live.py) uses its own hardcoded settings.
# This file contains legacy Binance settings from earlier development.


# Global Strategy Parameters (The Engine)
STRATEGY_PARAMS = {
    'grid_levels': 20,
    'grid_step_percent': 0.005,  # 0.5% Grid Step
    'take_profit_percent': 0.005,# 0.5% TP per grid level
    'ema_period': 200,           # Trend Filter
    'rsi_period': 14,            # Momentum
    'rsi_overbought': 70,        # Don't Buy above this
    'rsi_oversold': 30,          # Don't Sell below this
    'cooldown_minutes': 15,      # Anti-Machine Gun (Minutes)
    'max_active_grids': 5,       # Limit total open gridster (Simons)
    'min_atr_period': 14         # Volatility Window
}

# Global Risk Parameters (The Fortress)
# Global Risk Parameters (The Fortress)
RISK_PARAMS = {
    'max_drawdown_limit': 0.15,      # 15% Hard Stop (Circuit Breaker) - Default for Aggressive
    'stop_loss_atr_multiplier': 3.0, # Turtle 3x ATR Stops
    'kelly_fraction': 0.5,           # Thorp's Half-Kelly
    
    # --- FTMO / Prop Firm Specifics ---
    'ftmo_mode': True,               # Enable strict daily limits
    'daily_loss_limit_pct': 0.02,    # 2% Daily Hard Stop
    'daily_profit_target_pct': 0.01, # 1% Daily Target (Lock profit)
    'max_drawdown_ftmo_pct': 0.05,   # 5% Max Trailing Drawdown
    'max_holding_hours': 24,         # Force close if held > 24h
    
    # --- NEW: Enhanced Risk Engine (Option A) ---
    'martingale_detection_enabled': True,   # Detect increasing lot sizes
    'floating_loss_limit_pct': 0.03,        # 3% unrealized loss triggers CB
    'losing_streak_threshold': 3,           # N losses -> reduce risk by 50%
    'volatility_scaling_enabled': True,     # Scale size by ATR ratio
    'normal_atr': None,                     # Set dynamically or use historical avg
}

# Paper Trading Settings
PAPER_INITIAL_BALANCE = 100.0  # Initial capital per asset

# API Configuration
EXCHANGE_ID = 'kraken' # For Crypto

# --- Multi-Asset Portfolio Configuration ---
# Binance Spot Crypto Only
PORTFOLIO_CONFIG = [
    {
        'symbol': 'BTC/USDT',
        'type': 'crypto',
        'source': 'exchange', 
        'exchange_id': 'binanceus'
    },
    {
        'symbol': 'BTC/USDT',
        'type': 'crypto',
        'source': 'exchange', 
        'exchange_id': 'binanceus'
    }
    # Inactive / Examples
    # {
    #     'symbol': 'AAPL',
    #     'type': 'stock',
    #     'source': 'csv',      
    #     'csv_path': 'data/AAPL.csv'
    # },
    # {
    #     'symbol': 'EUR/USD',
    #     'type': 'forex',
    #     'source': 'csv',
    #     'csv_path': 'data/EURUSD.csv'
    # }
]
