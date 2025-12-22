import time
import random
import config

class StrategyEngine:
    def __init__(self, symbol, risk_manager):
        self.symbol = symbol
        self.risk_manager = risk_manager
        self.grid_levels = []
        self.current_position = 0.0
        self.initialize_grid()

    def initialize_grid(self):
        """Generates linear grid levels between lower and upper limits."""
        step = (config.UPPER_PRICE_LIMIT - config.LOWER_PRICE_LIMIT) / config.GRID_LEVELS
        for i in range(config.GRID_LEVELS + 1):
            price = config.LOWER_PRICE_LIMIT + (i * step)
            self.grid_levels.append(price)
        print(f"Grid initialized with {len(self.grid_levels)} levels: {self.grid_levels}")

    def get_market_price(self):
        # Placeholder for real market data
        # Simulating a random walk for paper trading
        base = 100000
        noise = random.uniform(-1000, 1000)
        return base + noise

    def execute_logic(self, current_price):
        """
        Core Grid Logic:
        - If price drops below a level -> Buy (Accumulate)
        - If price rises above a level -> Sell (Distribute)
        """
        # Simplified logic for demo
        for level in self.grid_levels:
            if abs(current_price - level) < 100: # Threshold
                print(f"Price {current_price:.2f} near Level {level:.2f}")
                # Logic to check if we should buy or sell would go here
                # checking if we already have an open order at this level etc.

    def run_paper_trading(self):
        print("Starting Paper Trading execution loop...")
        try:
            while True:
                price = self.get_market_price()
                print(f"Current Market Price: {price:.2f}")
                
                # Check Risk
                if not self.risk_manager.check_trade_allowed(self.current_position, 0):
                    print("Trading halted due to risk checks.")
                    break
                
                self.execute_logic(price)
                
                time.sleep(2) # simulate delay
        except KeyboardInterrupt:
            print("\nPaper trading stopped.")

    def run_live_trading(self):
        raise NotImplementedError("Live trading requires API keys and exchange connection.")
