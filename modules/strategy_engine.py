import pandas as pd
import numpy as np
import time

class StrategyEngine:
    """
    The Engine (Strategy Core)
    Implements:
    1. Dynamic Grid Spacing (ATR-based 'Breathing' Mesh)
    2. Trend Following Filter (Simons' Don't fight the trend)
    3. Integration with 'The Fortress' (Risk Manager)
    """

    def __init__(self, symbol, risk_manager, config_override=None):
        self.symbol = symbol
        self.risk_manager = risk_manager
        
        # Default Config (can be overridden)
        self.config = {
            'grid_levels': 20,
            'base_grid_step_pct': 0.01, # 1% base step
            'trend_ma_period': 200,      # Simple Moving Average for Trend
            'min_atr_period': 14
        }
        if config_override:
            self.config.update(config_override)

        # State
        self.grid_buy_orders = []  # List of prices
        self.grid_sell_orders = [] # List of prices
        self.current_trend = 'neutral' # bullish, bearish, neutral

    def add_indicators(self, price_history):
        """
        Calculates ATR and SMA on the dataframe.
        """
        # Calculate ATR
        high_low = price_history['high'] - price_history['low']
        high_close = np.abs(price_history['high'] - price_history['close'].shift())
        low_close = np.abs(price_history['low'] - price_history['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        # Simple ATR (Rolling Mean of TR)
        price_history['atr'] = true_range.rolling(self.config['min_atr_period']).mean()
        
        # Calculate Trend (SMA)
        price_history['sma_trend'] = price_history['close'].rolling(self.config['trend_ma_period']).mean()
        
        return price_history

    def fetch_market_data(self, price_history):
        """
        Ingests price history (DataFrame) to calculate indicators.
        Expected columns: ['close', 'high', 'low']
        """
        price_history = self.add_indicators(price_history)
        return price_history.iloc[-1] # Return latest slice

    def calculate_dynamic_grid(self, current_price, current_atr, base_atr=None):
        """
        Generates Grid Levels that 'breathe' with volatility.
        Formula: Step Size = Base Step * (Current ATR / Reference ATR)
        """
        if base_atr is None:
            base_atr = current_price * 0.02 # Assuming 2% vol as baseline if not provided
            
        # Volatility Adjustment Factor
        # If Vol is high, grid widens (to capture noise).
        # If Vol is low, grid tightens (to scalp).
        vol_factor = max(0.5, current_atr / base_atr) 
        
        dynamic_step = (current_price * self.config['base_grid_step_pct']) * vol_factor
        
        lower_limit = current_price * 0.90 # +/- 10% range for demo
        upper_limit = current_price * 1.10
        
        # Create Levels
        self.grid_buy_orders = []
        self.grid_sell_orders = []
        
        # Buy Levels (Below current price)
        price = current_price - dynamic_step
        while price > lower_limit:
            self.grid_buy_orders.append(price)
            price -= dynamic_step
            
        # Sell Levels (Above current price)
        price = current_price + dynamic_step
        while price < upper_limit:
            self.grid_sell_orders.append(price)
            price += dynamic_step
            
        return dynamic_step, len(self.grid_buy_orders) + len(self.grid_sell_orders)

    def determine_trend(self, current_price, sma_value):
        """
        Jim Simons Style: Logic filters.
        """
        if current_price > sma_value:
            return 'bullish'
        elif current_price < sma_value:
            return 'bearish'
        return 'neutral'

    def generate_signal(self, current_price, market_data):
        """
        Main Decision Function.
        """
        # 1. Update Indicators
        atr = market_data['atr']
        sma = market_data['sma_trend']
        
        # 2. Check Trend
        self.current_trend = self.determine_trend(current_price, sma)
        
        # 3. Dynamic Grid Logic
        # (In a real bot, we would only recalculate grid on significant events, 
        # but for this engine we calculate potential levels)
        step_size, num_levels = self.calculate_dynamic_grid(current_price, atr)
        
        print(f"[Strategy] Price: {current_price:.2f} | Trend: {self.current_trend} | ATR: {atr:.2f}")
        print(f"           Grid Step: {step_size:.2f} (Vol Adjusted)")
        
        # 4. Filter Logic (Simons)
        # Don't open Long Grids if Trend is Bearish (Safety First)
        allow_buys = True
        if self.current_trend == 'bearish':
            print("           [STOP] Trend is Bearish. Pausing Buy Grid creation.")
            allow_buys = False
            
        # 5. Risk Check (The Fortress)
        # Ask Risk Manager for Safe Position Size
        safe_size = self.risk_manager.calculate_position_size(
            account_balance=10000, # Mock balance
            current_volatility_atr=atr,
            price=current_price
        )
        
        return {
            'action': 'update_grid',
            'buy_levels': self.grid_buy_orders if allow_buys else [],
            'sell_levels': self.grid_sell_orders,
            'suggested_size_per_grid': safe_size,
            'trend': self.current_trend
        }

    def run_paper_trading(self):
        print("Paper Trading not fully implemented in Strategy Class yet.")
