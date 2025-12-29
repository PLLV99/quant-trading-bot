import random
import numpy as np
import matplotlib.pyplot as plt

def monte_carlo_simulation(
    starting_balance=300,
    risk_per_trade_pct=0.02,  # 2% risk
    win_rate=0.45,            # Conservative 45% win rate for trend following
    risk_reward_ratio=2.0,    # Win = 2x Risk
    trades_per_month=20,
    months=12,
    num_simulations=1000
):
    results = []
    ruin_count = 0
    ruin_threshold = 50  # Basically useless account size

    print(f"--- Simulation Parameters ---")
    print(f"Start Balance: ${starting_balance}")
    print(f"Win Rate: {win_rate*100}%")
    print(f"Risk/Reward: 1:{risk_reward_ratio}")
    print(f"Trades/Month: {trades_per_month}")
    print(f"Simulations: {num_simulations}")
    print("-" * 30)

    for i in range(num_simulations):
        balance = starting_balance
        equity_curve = [balance]
        total_trades = trades_per_month * months
        
        for trade in range(total_trades):
            # Calculate Risk Amount (Max 5% cap for micro account realities, Min $2)
            risk_amt = balance * risk_per_trade_pct
            risk_amt = max(2.0, min(risk_amt, balance * 0.05)) 
            
            if random.random() < win_rate:
                profit = risk_amt * risk_reward_ratio
                balance += profit
            else:
                balance -= risk_amt
            
            if balance < ruin_threshold:
                ruin_count += 1
                break
            
            equity_curve.append(balance)
        
        if balance >= ruin_threshold:
            results.append(balance)

    # Statistics
    results = np.array(results)
    avg_final = np.mean(results)
    median_final = np.median(results)
    ruin_prob = (ruin_count / num_simulations) * 100
    
    print(f"Risk of Ruin (<$50): {ruin_prob:.2f}%")
    print(f"Median Final Balance: ${median_final:.2f}")
    print(f"Average Final Balance: ${avg_final:.2f}")
    print(f"Max Result: ${np.max(results):.2f}")
    print(f"Min Result (Non-Ruin): ${np.min(results):.2f}")
    
    # ROI Calculation
    median_roi = ((median_final - starting_balance) / starting_balance) * 100
    print(f"Median ROI: {median_roi:.2f}%")

if __name__ == "__main__":
    # Scenario A: Conservative (Trend Following struggles)
    print("\n>>> SCENARIO A: Conservative / Choppy Market")
    monte_carlo_simulation(win_rate=0.35, risk_reward_ratio=2.5) # Low win rate, high R:R
    
    # Scenario B: Moderate (Standard Performance)
    print("\n>>> SCENARIO B: Moderate / Balanced")
    monte_carlo_simulation(win_rate=0.45, risk_reward_ratio=2.0)
    
    # Scenario C: Aggressive / Optimized (Good Trend)
    print("\n>>> SCENARIO C: Optimized / Strong Trend")
    monte_carlo_simulation(win_rate=0.55, risk_reward_ratio=2.0)
