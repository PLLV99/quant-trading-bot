
import json
import os
import sys

def load_portfolio(filepath='data/paper_portfolio.json'):
    if not os.path.exists(filepath):
        print(f"Error: Portfolio file not found at {filepath}")
        return {}
    with open(filepath, 'r') as f:
        return json.load(f)

def print_pnl():
    portfolio = load_portfolio()
    if not portfolio:
        return

    print("\n" + "="*60)
    print(f"{'ASSET':<10} | {'BALANCE':<10} | {'HOLDING':<10} | {'PRICE':<10} | {'EQUITY':<10} | {'PnL %':<8}")
    print("-" * 60)

    total_initial = 0
    total_equity = 0

    # Get initial balance from config or assume 100 based on recent change
    # But better to just sum current equity vs known initial.
    # Currently hardcoded known initial per asset = 100.
    INITIAL_PER_ASSET = 100.0

    for symbol, data in portfolio.items():
        balance = data.get('balance', 0.0)
        inventory = data.get('inventory', 0.0)
        last_price = data.get('last_price', 0.0)
        equity = data.get('equity', balance) # Default to balance if equity not saved yet

        # Calculate PnL
        pnl_pct = ((equity - INITIAL_PER_ASSET) / INITIAL_PER_ASSET) * 100
        
        # Color hack for terminal (Green/Red)
        pnl_str = f"{pnl_pct:+.2f}%"
        
        print(f"{symbol:<10} | {balance:<10.2f} | {inventory:<10.4f} | {last_price:<10.2f} | {equity:<10.2f} | {pnl_str:<8}")

        total_initial += INITIAL_PER_ASSET
        total_equity += equity

    print("-" * 60)
    total_pnl_pct = ((total_equity - total_initial) / total_initial) * 100
    print(f"{'TOTAL':<10} | {'':<10} | {'':<10} | {'':<10} | {total_equity:<10.2f} | {total_pnl_pct:+.2f}%")
    print("="*60 + "\n")

if __name__ == "__main__":
    print_pnl()
