import sys
import os
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from main import run_backtest_portfolio

def run_comparison():
    print("\n\n" + "="*60)
    print(" CHAMPION (Original) vs CHALLENGER (FTMO Hybrid) ")
    print("="*60)

    # 1. Run Champion (Aggressive/Original)
    print("\n--- 1. Running AGGRESSIVE Mode (No Daily Limits) ---")
    config.RISK_PARAMS['ftmo_mode'] = False
    config.RISK_PARAMS['max_drawdown_limit'] = 0.15 # Original 15%
    results_agg = run_backtest_portfolio(days=30, strategy_mode='grid')
    
    # Calculate Aggregates
    agg_profit = sum(r['Profit $'] for r in results_agg) if results_agg else 0
    agg_dd = max(r['Max DD %'] for r in results_agg) if results_agg else 0
    agg_trades = sum(r['Trades'] for r in results_agg) if results_agg else 0

    # 2. Run Challenger (FTMO Safe Mode)
    print("\n--- 2. Running FTMO SAFE Mode (Daily Limits Active) ---")
    config.RISK_PARAMS['ftmo_mode'] = True
    config.RISK_PARAMS['max_drawdown_limit'] = 0.05 # FTMO 5%
    results_ftmo = run_backtest_portfolio(days=30, strategy_mode='grid')

    # Calculate Aggregates
    ftmo_profit = sum(r['Profit $'] for r in results_ftmo) if results_ftmo else 0
    ftmo_dd = max(r['Max DD %'] for r in results_ftmo) if results_ftmo else 0
    ftmo_trades = sum(r['Trades'] for r in results_ftmo) if results_ftmo else 0

    # 3. Side-by-Side Comparison
    print("\n\n" + "="*60)
    print(" FINAL VERDICT: 30-Day Simulation ")
    print("="*60)
    
    # Create DataFrame for pretty print
    df_compare = pd.DataFrame({
        'Metric': ['Total Profit ($)', 'Max Drawdown (%)', 'Total Trades', 'Safety Status'],
        'Original (Aggressive)': [
            f"${agg_profit:.2f}", 
            f"-{agg_dd:.2f}%", 
            agg_trades, 
            "RISKY (Possible Blowout)" if agg_dd > 10 else "MODERATE"
        ],
        'New FTMO Hybrid': [
            f"${ftmo_profit:.2f}", 
            f"-{ftmo_dd:.2f}%", 
            ftmo_trades, 
            "SAFE (Passed)" if ftmo_dd < 5 else "FAILED (Needs Tweak)"
        ]
    })
    
    print(df_compare.to_string(index=False))
    print("\n")
    
    if ftmo_profit >= agg_profit and ftmo_dd < agg_dd:
        print(" RECOMMENDATION: The FTMO Hybrid is STRICTLY BETTER (More profit, less risk).")
    elif ftmo_dd < agg_dd:
        print(" RECOMMENDATION: Trade-off accepted. Lower risk is worth the slightly lower profit.")
    else:
        print(" WARNING: The FTMO logic might be too restrictive or buggy. Review needed.")
    print("="*60)

if __name__ == "__main__":
    run_comparison()
