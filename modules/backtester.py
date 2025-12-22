import pandas as pd
import numpy as np

class Backtester:
    """
    The Lab (Simulation Engine)
    Simulates the strategy against historical data.
    Assumptions:
    - No slippage (Limit orders)
    - 0.1% Fee per trade
    """
    def __init__(self, strategy_engine, initial_balance=10000.0):
        self.strategy = strategy_engine
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.inventory = 0.0 # Coin amount
        self.active_orders = [] # List of {'side': 'buy/sell', 'price': 100, 'size': 0.1}
        self.trade_history = []
        self.equity_curve = []
        
        # Stats
        self.fee_rate = 0.001 # 0.1%
        
    def run(self, data: pd.DataFrame):
        """
        Main Loop: Iterates through price history (OHLCV).
        """
        print(f"--- Starting Backtest on {len(data)} candles ---")
        
        # Pre-calculate indicators
        # In real-time we calc row by row, but for speed in backtest:
        data = self._prepare_indicators(data)
        
        for index, row in data.iterrows():
            current_price = row['close']
            high = row['high']
            low = row['low']
            timestamp = index
            
            # 1. Update Portfolio Value (Mark-to-Market)
            portfolio_value = self.balance + (self.inventory * current_price)
            
            # Update Risk Manager with current equity (for Drawdown tracking)
            self.strategy.risk_manager.update_account_status(portfolio_value)
            
            self.equity_curve.append({'time': timestamp, 'equity': portfolio_value})
            
            # 2. Check Order Fills (Engine)
            self._check_fills(high, low, timestamp)
            
            # 3. Generate Strategy Signals
            # Create a "slice" of data up to this point to simulate real-time
            # (In production backtests, we might optimize this, but this is safe)
            market_slice = row # In our strategy logic we just passed the row
            
            signal = self.strategy.generate_signal(current_price, market_slice)
            
            # 4. Process Signal
            if signal.get('action') == 'update_grid':
                # Replace active orders with new grid
                # (For simplicity in this V1, we cancel all and replace)
                self.active_orders = [] 
                
                size = signal.get('suggested_size_per_grid', 0)
                if size > 0:
                    for price in signal['buy_levels']:
                        self.active_orders.append({'side': 'buy', 'price': price, 'size': size})
                    for price in signal['sell_levels']:
                        # Only sell if we have inventory? For grid bot, usually yes.
                        # But for "Anti-Fragile", maybe we short? Let's stick to Spot Long Grid.
                        if self.inventory > 0:
                             self.active_orders.append({'side': 'sell', 'price': price, 'size': size})
        
        self._generate_report()
    
    def _prepare_indicators(self, data):
        # We need to compute ATR and SMA just like the strategy does
        return self.strategy.add_indicators(data)

    def _check_fills(self, high, low, timestamp):
        """
        Checks if any active orders were in the High-Low range of this candle.
        """
        remaining_orders = []
        for order in self.active_orders:
            filled = False
            
            # BUY ORDER: Fill if Low <= Order Price
            if order['side'] == 'buy' and low <= order['price']:
                cost = order['price'] * order['size']
                if self.balance >= cost:
                    self.balance -= cost
                    self.inventory += order['size']
                    fee = cost * self.fee_rate
                    self.balance -= fee
                    
                    self.trade_history.append({'time': timestamp, 'side': 'buy', 'price': order['price'], 'size': order['size'], 'fee': fee})
                    filled = True
            
            # SELL ORDER: Fill if High >= Order Price
            elif order['side'] == 'sell' and high >= order['price']:
                if self.inventory >= order['size']:
                    revenue = order['price'] * order['size']
                    self.balance += revenue
                    self.inventory -= order['size']
                    fee = revenue * self.fee_rate
                    self.balance -= fee
                    
                    self.trade_history.append({'time': timestamp, 'side': 'sell', 'price': order['price'], 'size': order['size'], 'fee': fee})
                    filled = True
            
            if not filled:
                remaining_orders.append(order)
                
        self.active_orders = remaining_orders

    def _generate_report(self):
        start_eq = self.initial_balance
        end_eq = self.equity_curve[-1]['equity']
        pnl = end_eq - start_eq
        ret_pct = (pnl / start_eq) * 100
        
        # Max Drawdown
        peaks = pd.Series([x['equity'] for x in self.equity_curve]).cummax()
        drawdowns = (pd.Series([x['equity'] for x in self.equity_curve]) - peaks) / peaks
        max_dd = drawdowns.min() * 100
        
        print("\n=== [The Lab] Backtest Report ===")
        print(f"Initial Balance: ${start_eq:.2f}")
        print(f"Final Balance:   ${end_eq:.2f}")
        print(f"Total Return:    {ret_pct:.2f}%")
        print(f"Max Drawdown:    {max_dd:.2f}%")
        print(f"Total Trades:    {len(self.trade_history)}")
        print("===============================\n")
