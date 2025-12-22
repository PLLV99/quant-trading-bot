# Grid Trading Configuration

# Trading Parameters
SYMBOL = 'BTC/USDT'
GRID_LEVELS = 10  # Number of grid lines
LOWER_PRICE_LIMIT = 90000  # Example lower bound
UPPER_PRICE_LIMIT = 110000 # Example upper bound
AMOUNT_PER_GRID = 0.001    # Amount of base asset per order

# Risk Management Parameters (inspired by Thorp/Kelly)
RISK_PARAMS = {
    'max_drawdown_limit': 0.15,  # Stop bot if drawdown exceeds 15%
    'stop_loss_pct': 0.05,       # Stop loss per trade or per grid position
    'max_position_size': 1.0,    # Max total exposure in BTC
    'kelly_fraction': 0.5        # Use Half-Kelly for sizing (conservative)
}

# API Configuration (Load from environment variables in real usage)
EXCHANGE_ID = 'binance'
