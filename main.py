import argparse
import sys
from modules.strategy_engine import StrategyEngine
from modules.risk_manager import RiskManager
from modules.backtester import Backtester
import config

def main():
    parser = argparse.ArgumentParser(description="Quantitative Grid Trading Bot")
    parser.add_argument('--mode', choices=['live', 'backtest', 'paper'], default='paper', help='Operation mode')
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='Trading pair symbol')
    
    args = parser.parse_args()
    
    print(f"Starting Bot in {args.mode.upper()} mode for {args.symbol}...")
    
    # Initialize Core Modules
    risk_manager = RiskManager(config.RISK_PARAMS)
    strategy_engine = StrategyEngine(symbol=args.symbol, risk_manager=risk_manager)
    
    if args.mode == 'backtest':
        print("Initializing Backtester...")
        backtester = Backtester(strategy_engine)
        backtester.run(days=30)
    elif args.mode == 'paper':
        print("Starting Paper Trading Loop...")
        strategy_engine.run_paper_trading()
    elif args.mode == 'live':
        print("WARNING: LIVE TRADING MODE.")
        confirmation = input("Type 'CONFIRM' to proceed with real money: ")
        if confirmation == 'CONFIRM':
            strategy_engine.run_live_trading()
        else:
            print("Live trading cancelled.")
            sys.exit()

if __name__ == "__main__":
    main()
