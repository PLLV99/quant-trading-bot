import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.strategy_engine import StrategyEngine
from modules.risk_manager import RiskManager

class MockConfig:
    def get(self, key, default):
        return default

def test_strategy_engine():
    print("=== Testing Strategy Engine (The Engine) ===\n")
    
    # 1. Setup
    risk_manager = RiskManager(MockConfig())
    engine = StrategyEngine(symbol="BTC/USDT", risk_manager=risk_manager)
    
    # 2. Mock Data (Bullish Trend, Low Vol)
    # Price going UP, Low Volatility
    dates = pd.date_range(start='2024-01-01', periods=300, freq='h')
    data_bull = pd.DataFrame({
        'high': np.linspace(100, 200, 300) + 1,
        'low': np.linspace(100, 200, 300) - 1,
        'close': np.linspace(100, 200, 300)
    }, index=dates)
    
    # 3. Test Signal Generation
    print("Test Consition 1: Bullish Trend + Low Vol")
    latest_slice = engine.fetch_market_data(data_bull.copy())
    signal = engine.generate_signal(current_price=200, market_data=latest_slice)
    
    # VERIFY: Should allow buys
    if len(signal['buy_levels']) > 0 and signal['trend'] == 'bullish':
        print("[PASS] Bullish Trend recognized. Buy Grid Active.")
    else:
        print(f"[FAIL] Trend Check Failed. Trend: {signal['trend']}, Buys: {len(signal['buy_levels'])}")
        
    # 4. Test Dynamic Grid (High Volatility)
    print("\nTest Condition 2: Dynamic Grid Breathing")
    
    # Scenario A: Low Vol (ATR ~ 2.0 from previous test)
    step_low_vol, _ = engine.calculate_dynamic_grid(current_price=200, current_atr=2.0, base_atr=2.0)
    print(f"Low Vol Grid Step: {step_low_vol:.2f}")
    
    # Scenario B: High Vol (ATR Spikes to 10.0)
    step_high_vol, _ = engine.calculate_dynamic_grid(current_price=200, current_atr=10.0, base_atr=2.0)
    print(f"High Vol Grid Step: {step_high_vol:.2f}")
    
    # VERIFY: Grid should widen by approx 5x (10/2)
    ratio = step_high_vol / step_low_vol
    if 4.8 < ratio < 5.2:
        print(f"[PASS] Grid Breathing Logic Works! (Grid widened {ratio:.1f}x as Vol increased 5x)")
    else:
        print(f"[FAIL] Grid Logic Failed. Ratio: {ratio}")

    # 5. Test Trend Filter (Bearish)
    print("\nTest Condition 3: Bearish Trend Filter")
    # Generate Bearish Data
    data_bear = pd.DataFrame({
        'high': np.linspace(200, 100, 300) + 1,
        'low': np.linspace(200, 100, 300) - 1,
        'close': np.linspace(200, 100, 300)
    }, index=dates)
    
    latest_slice_bear = engine.fetch_market_data(data_bear.copy())
    signal_bear = engine.generate_signal(current_price=100, market_data=latest_slice_bear)
    
    # VERIFY: Should BLOCK buys
    if len(signal_bear['buy_levels']) == 0 and signal_bear['trend'] == 'bearish':
        print("[PASS] Bearish Trend Filter Works. Buy Grid Paused.")
    else:
        print(f"[FAIL] Filter Failed. Trend: {signal_bear['trend']}, Buys: {len(signal_bear['buy_levels'])}")

if __name__ == "__main__":
    test_strategy_engine()
