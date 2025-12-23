import signal
import sys
import os
import json
import time
import logging
import pandas as pd
from datetime import datetime
import config
from modules.risk_manager import RiskManager
from modules.strategy_engine import StrategyEngine
from modules.data_loader import DataLoader

# Setup Logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f"logs/paper_trading_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('PaperTrader')

class PaperTrader:
    """
    Paper Trading Environment
    Simulates real-time trading with persistent state.
    """
    def __init__(self, max_days=None):
        self.state_file = 'data/paper_portfolio.json'
        self.portfolio = self._load_state()
        self.running = True
        self.max_days = max_days
        self.start_time = time.time()
        self.last_log_time = 0
        
        # Signal Handlers
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)
        
        # Initialize Modules
        logger.info("Initializing Paper Trader modules...")
        self.loader = DataLoader(default_exchange_id=config.EXCHANGE_ID)
        self.risk_manager = RiskManager(config.RISK_PARAMS)
        
        # Strategy Instances (One per asset)
        self.strategies = {}
        for asset in config.PORTFOLIO_CONFIG:
            symbol = asset['symbol']
            self.strategies[symbol] = StrategyEngine(
                symbol=symbol, 
                risk_manager=self.risk_manager,
                config_override=config.STRATEGY_PARAMS
            )
            
            # Init empty state for new assets
            if symbol not in self.portfolio:
                self.portfolio[symbol] = {
                    'balance': 10000.0,
                    'inventory': 0.0,
                    'active_orders': [],
                    'trades': []
                }
        self._save_state()
        logger.info("Initialization Complete.")

    def terminate(self, signum, frame):
        logger.info("Signal received. Shutting down gracefully...")
        self.running = False

    def run(self):
        logger.info(f"=== Starting Paper Trading Loop ===")
        if self.max_days:
            logger.info(f"Auto-Stop enabled: {self.max_days} days")
            
        assets = [a['symbol'] for a in config.PORTFOLIO_CONFIG]
        logger.info(f"Monitoring Assets: {assets}")
        
        try:
            while self.running:
                # Check Duration
                if self.max_days:
                    elapsed_days = (time.time() - self.start_time) / (24 * 3600)
                    if elapsed_days >= self.max_days:
                        logger.info(f"Max duration ({self.max_days} days) reached. Stopping.")
                        break

                cur_time = time.time()
                # Log Status every 10s
                if cur_time - self.last_log_time > 10:
                    logger.info(f"--- Heartbeat: {datetime.now().strftime('%H:%M:%S')} ---")
                    self.last_log_time = cur_time

                for asset_conf in config.PORTFOLIO_CONFIG:
                    self._process_asset(asset_conf)
                
                self._save_state()
                
                # Sleep in chunks to allow faster interrupt
                # Sleep 60s total, check every 1s
                for _ in range(60): 
                    if not self.running: break
                    time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Paper Trading Stopped (KeyboardInterrupt).")
        except Exception as e:
            logger.error(f"Critical Error in Main Loop: {e}")
        finally:
            self._save_state()
            logger.info("Paper Trader Shutdown Complete.")
            sys.exit(0)

    def _process_asset(self, asset_conf):
        symbol = asset_conf['symbol']
        state = self.portfolio[symbol]
        strategy = self.strategies[symbol]
        
        # 1. Fetch Latest Data
        df = self.loader.fetch_latest_candles(asset_conf, limit=200)
        if df.empty:
            logger.warning(f"[{symbol}] No data received.")
            return

        current_price = df.iloc[-1]['close']
        high = df.iloc[-1]['high']
        low = df.iloc[-1]['low']
        
        # 2. Check Fills
        self._check_fills(symbol, high, low, current_price)
        
        # 3. Update Strategy
        latest_slice = strategy.add_indicators(df).iloc[-1]
        
        equity = state['balance'] + (state['inventory'] * current_price)
        self.risk_manager.update_account_status(equity)
        
        signal = strategy.generate_signal(current_price, latest_slice)
        
        # 4. Process Signal
        if signal.get('action') == 'update_grid':
            state['active_orders'] = []
            size = signal.get('suggested_size_per_grid', 0)
            if size > 0:
                for price in signal['buy_levels']:
                    if price < current_price:
                        state['active_orders'].append({'side': 'buy', 'price': price, 'size': size})
                for price in signal['sell_levels']:
                    if price > current_price and state['inventory'] > 0:
                         state['active_orders'].append({'side': 'sell', 'price': price, 'size': size})
        
        # Log basic status only occasionally or verbose? 
        # For now let's log only if something interesting happens or just regular heartbeat handles it.
        # But user asked for periodic logging. The Heartbeat handles the 'alive' check.
        # Maybe log equity updates?
        # logger.debug(f"[{symbol}] Price: {current_price:.2f} | Eq: ${equity:.0f}")

    def _check_fills(self, symbol, high, low, current_price):
        state = self.portfolio[symbol]
        remaining = []
        filled_count = 0
        
        for order in state['active_orders']:
            filled = False
            if order['side'] == 'buy' and low <= order['price']:
                cost = order['price'] * order['size']
                fee = cost * 0.001  # 0.1% Fee
                total_cost = cost + fee
                
                if state['balance'] >= total_cost:
                    state['balance'] -= total_cost
                    state['inventory'] += order['size']
                    state['trades'].append({
                        'side': 'buy', 
                        'price': order['price'], 
                        'size': order['size'], 
                        'fee': fee,
                        'time': str(datetime.now())
                    })
                    filled = True
                    logger.info(f"[{symbol}] BUY FILLED @ {order['price']:.2f} (Fee: ${fee:.2f})")
                    
            elif order['side'] == 'sell' and high >= order['price']:
                 if state['inventory'] >= order['size']:
                    rev = order['price'] * order['size']
                    fee = rev * 0.001 # 0.1% Fee
                    net_rev = rev - fee
                    
                    state['balance'] += net_rev
                    state['inventory'] -= order['size']
                    state['trades'].append({
                        'side': 'sell', 
                        'price': order['price'], 
                        'size': order['size'], 
                        'fee': fee,
                        'time': str(datetime.now())
                    })
                    filled = True
                    logger.info(f"[{symbol}] SELL FILLED @ {order['price']:.2f} (Fee: ${fee:.2f})")
            
            if filled:
                filled_count += 1
            else:
                remaining.append(order)
                
        state['active_orders'] = remaining
        if filled_count > 0:
            self._save_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_state(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.portfolio, f, indent=4)
