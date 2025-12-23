# Grid Trading Configuration

# Global Strategy Parameters (The Engine)
STRATEGY_PARAMS = {
    'grid_levels': 20,
    'base_grid_step_pct': 0.01,  # 1% standard step
    'trend_ma_period': 200,      # Trend Filter (Simons)
    'min_atr_period': 14         # Volatility Window
}

# Global Risk Parameters (The Fortress)
RISK_PARAMS = {
    'max_drawdown_limit': 0.15,      # 15% Hard Stop (Circuit Breaker)
    'stop_loss_atr_multiplier': 3.0, # Turtle 3x ATR Stops
    'kelly_fraction': 0.5            # Thorp's Half-Kelly
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
        'exchange_id': 'binance'
    },
    {
        'symbol': 'ETH/USDT',
        'type': 'crypto',
        'source': 'exchange',
        'exchange_id': 'binance'
    },
    {
        'symbol': 'BNB/USDT',
        'type': 'crypto',
        'source': 'exchange',
        'exchange_id': 'binance'
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
