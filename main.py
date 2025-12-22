import argparse
import sys
import pandas as pd
import numpy as np
import config

from modules.strategy_engine import StrategyEngine
from modules.risk_manager import RiskManager
from modules.backtester import Backtester
from modules.data_loader import DataLoader

def run_backtest_portfolio(days=30):
    """
    Runs backtest on all assets defined in PORTFOLIO_CONFIG.
    """
    print(f"\n=== [Anti-Fragile Portfolio] Running Multi-Asset Backtest ({days} Days) ===")
    
    loader = DataLoader(default_exchange_id=config.EXCHANGE_ID)
    
    portfolio_results = []
    total_initial_balance = 0
    total_final_balance = 0
    
    # Iterate through each asset
    for asset_conf in config.PORTFOLIO_CONFIG:
        symbol = asset_conf['symbol']
        print(f"\n>>> Processing {symbol} ({asset_conf['type']})...")
        
        # 1. Load Data
        data = loader.load_data(asset_config=asset_conf, days=days)
        
        if data.empty:
            print(f"   [Skip] No data found for {symbol}.")
            continue
            
        # 2. Setup Bot Instance for this asset
        # Note: In a real portfolio, RiskManager might manage Shared Capital.
        # Here we simulate Independent Sub-Accounts (e.g. $10k each).
        asset_initial_balance = 10000.0
        
        risk_manager = RiskManager(config.RISK_PARAMS)
        strategy_engine = StrategyEngine(symbol=symbol, risk_manager=risk_manager, config_override=config.STRATEGY_PARAMS)
        backtester = Backtester(strategy_engine, initial_balance=asset_initial_balance)
        
        # 3. Run Simulation
        try:
            backtester.run(data)
            
            # 4. Collect Stats
            final_bal = backtester.equity_curve[-1]['equity']
            pnl = final_bal - asset_initial_balance
            ret_pct = (pnl / asset_initial_balance) * 100
            
            # Max DD
            peaks = pd.Series([x['equity'] for x in backtester.equity_curve]).cummax()
            dd = (pd.Series([x['equity'] for x in backtester.equity_curve]) - peaks) / peaks
            max_dd = dd.min() * 100
            
            portfolio_results.append({
                'Symbol': symbol,
                'Type': asset_conf['type'],
                'Return %': ret_pct,
                'Max DD %': max_dd,
                'Trades': len(backtester.trade_history),
                'Profit $': pnl
            })
            
            total_initial_balance += asset_initial_balance
            total_final_balance += final_bal
            
        except Exception as e:
            print(f"   [Error] Backtest failed for {symbol}: {e}")
            
    # 5. Generate Portfolio Report
    print("\n\n" + "="*50)
    print("       PORTFOLIO PERFORMANCE REPORT")
    print("="*50)
    
    if not portfolio_results:
        print("No trades executed.")
        return

    df_res = pd.DataFrame(portfolio_results)
    # Format for pretty printing
    print(df_res[['Symbol', 'Type', 'Return %', 'Max DD %', 'Trades', 'Profit $']].to_string(index=False, float_format="%.2f"))
    
    print("-" * 50)
    total_pnl = total_final_balance - total_initial_balance
    total_ret = (total_pnl / total_initial_balance) * 100
    print(f"TOTAL PORTFOLIO RETURN: {total_ret:.2f}%  (${total_pnl:.2f})")
    print("="*50)


def main():
    parser = argparse.ArgumentParser(description="Quantitative Grid Trading Bot (Anti-Fragile)")
    parser.add_argument('--mode', choices=['live', 'backtest', 'paper'], default='backtest', help='Operation mode')
    parser.add_argument('--symbol', type=str, default=None, help='(Optional) Run specific symbol only')
    parser.add_argument('--days', type=float, default=30.0, help='Backtest duration')
    
    args = parser.parse_args()
    
    if args.mode == 'backtest':
        run_backtest_portfolio(days=args.days)
        
    elif args.mode == 'paper':
        from modules.paper_trader import PaperTrader
        print("--- JOINING THE MATRIX (Paper Trading Mode) ---")
        trader = PaperTrader(max_days=args.days)
        trader.run()
    elif args.mode == 'live':
        print("WARNING: LIVE TRADING MODE.")
        sys.exit()

if __name__ == "__main__":
    main()
