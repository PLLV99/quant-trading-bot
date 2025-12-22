import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.risk_manager import RiskManager

class MockConfig:
    def get(self, key, default):
        return default

def test_anti_fragile_logic():
    print("=== Testing Anti-Fragile Risk Manager ===\n")
    
    # 1. Initialize
    rm = RiskManager(MockConfig())
    account_balance = 10000.0
    rm.update_account_status(account_balance) # Seed initial balance
    
    # 2. Scenerio A: Normal Market (Low Volatility)
    # ATR = 10 (Price ~1000) -> Vol is low
    atr_low = 10.0
    size_normal = rm.calculate_position_size(account_balance, atr_low, price=1000)
    print(f"Scenario A (Normal Vol): Position Size = {size_normal:.4f} units")
    
    # 3. Scenario B: High Volatility Event (Dalio Logic)
    # ATR spikes to 20 (Doubled)
    atr_high = 20.0
    size_high = rm.calculate_position_size(account_balance, atr_high, price=1000)
    print(f"Scenario B (High Vol):   Position Size = {size_high:.4f} units")
    
    # VERIFY: Size should be roughly HALVED
    if 0.4 < (size_high / size_normal) < 0.6:
        print("[PASS] Dalio Volatility Sizing worked (Size halved as Vol doubled).")
    else:
        print("[FAIL] Dalio Logic failed.")
        
    # 4. Scenario C: Drawdown Event (Taleb Logic)
    # Lose 15% of portfolio
    print("\n--- Simulating 15% Drawdown ---")
    rm.update_account_status(8500.0) # Peak was 10000 -> 15% DD
    
    # Calculate size again under High Vol + Circuit Breaker
    size_panic = rm.calculate_position_size(account_balance, atr_high, price=1000)
    print(f"Scenario C (Defense):    Position Size = {size_panic:.4f} units")
    
    # VERIFY: Should be HALF of Scenario B
    if 0.4 < (size_panic / size_high) < 0.6:
        print("[PASS] Taleb Circuit Breaker worked (Leverage cut by 50%).")
    else:
        print("[FAIL] Circuit Breaker failed.")

    # 5. Turtle Stops
    stop_price = rm.get_adaptive_stop_loss(entry_price=1000, atr=10, side='buy')
    print(f"\nTurtle Stop Check: Entry 1000, ATR 10, Multiplier 3x -> Stop should be 970")
    if stop_price == 970:
        print(f"[PASS] Stop Price = {stop_price}")
    else:
        print(f"[FAIL] Calc Stop = {stop_price}")

if __name__ == "__main__":
    test_anti_fragile_logic()
