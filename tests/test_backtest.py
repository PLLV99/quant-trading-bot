import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.backtester import Backtester
from modules.strategy_engine import StrategyEngine
from modules.risk_manager import RiskManager

class MockConfig:
    def get(self, key, default):
        return default

def test_backtester_simulation():
    print("=== Testing Backtester (The Lab) ===\n")
    
    # 1. Setup
    risk_manager = RiskManager(MockConfig())
    strategy = StrategyEngine("BTC/USDT", risk_manager)
    backtester = Backtester(strategy, initial_balance=10000.0)
    
    # 2. Generate Synthetic Data (Sine Wave to trigger Grid Trades)
    # Price oscillates between 100 and 110
    length = 100
    x = np.linspace(0, 4*np.pi, length)
    base_price = 105
    amplitude = 5
    
    prices = base_price + amplitude * np.sin(x)
    
    data = pd.DataFrame({
        'close': prices,
        'high': prices + 0.5, # slight wick
        'low': prices - 0.5,
        'open': prices
    })
    
    # Pre-calc indicators for the Strategy (since we mocked them)
    data['atr'] = 2.0 # Fixed Volatility
    data['sma_trend'] = 105.0 # Neutral trend baseline
    
    # 3. Run Simulation
    backtester.run(data)
    
    # 4. Verification
    # We expect lots of trades because price is oscillating through the grid
    final_balance = backtester.equity_curve[-1]['equity']
    trades = len(backtester.trade_history)
    
    print(f"Final Balance: {final_balance:.2f}")
    print(f"Total Trades: {trades}")
    
    if trades > 5:
        print("[PASS] Grid Logic Triggered Multiple Trades.")
    else:
        print(f"[FAIL] Too few trades ({trades}). Grid might be broken.")
        
    # Check if we didn't lose everything (Bot safety)
    if final_balance > 5000:
         print("[PASS] Account Survived (Balance > 50% initial).")
    else:
         print("[FAIL] Account Blown!")

if __name__ == "__main__":
    test_backtester_simulation()
