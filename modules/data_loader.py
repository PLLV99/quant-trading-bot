import ccxt
import pandas as pd
import os
import time

class DataLoader:
    """
    Data Fetcher
    Connects to exchanges (via CCXT) or loads CSVs.
    """
    def __init__(self, default_exchange_id='kraken'):
        self.default_exchange_id = default_exchange_id
        self.exchanges = {} 
        
    def _get_exchange(self, exchange_id):
        """Lazy load exchange instances."""
        if exchange_id not in self.exchanges:
            try:
                # print(f"[DataLoader] Connecting to {exchange_id}...")
                exchange_class = getattr(ccxt, exchange_id)
                self.exchanges[exchange_id] = exchange_class({
                    'enableRateLimit': True,
                })
            except AttributeError:
                print(f"[DataLoader] Error: Exchange '{exchange_id}' not found in CCXT.")
                return None
        return self.exchanges.get(exchange_id)

    def load_data(self, asset_config, days=30):
        """
        Factory method to load historical data.
        """
        symbol = asset_config['symbol']
        source = asset_config.get('source', 'exchange')
        exchange_id = asset_config.get('exchange_id', self.default_exchange_id)
        
        print(f"[DataLoader] Loading data for {symbol} (Source: {source}, Exchange: {exchange_id})...")
        
        if source == 'exchange':
            return self._fetch_from_exchange(symbol, exchange_id, days=days)
        elif source == 'csv':
            return self._load_from_csv(asset_config.get('csv_path'), days=days)
        else:
            return pd.DataFrame()

    def fetch_latest_candles(self, asset_config, limit=200, timeframe='1h'):
        """
        Fetches just enough recent history to calc indicators (Real-Time Mode).
        """
        symbol = asset_config['symbol']
        source = asset_config.get('source', 'exchange')
        exchange_id = asset_config.get('exchange_id', self.default_exchange_id)
        
        if source == 'exchange':
            exchange = self._get_exchange(exchange_id)
            if not exchange: return pd.DataFrame()
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('datetime', inplace=True)
                cols = ['open', 'high', 'low', 'close', 'volume']
                df[cols] = df[cols].apply(pd.to_numeric)
                return df
            except Exception as e:
                print(f"[Error] Fetch latest failed for {symbol}: {e}")
                return pd.DataFrame()
                
        elif source == 'csv':
            # return tail of CSV
            return self._load_from_csv(asset_config.get('csv_path'), rows=limit)
            
        return pd.DataFrame()

    def _fetch_from_exchange(self, symbol, exchange_id, timeframe='1h', days=30):
        """History Fetcher"""
        exchange = self._get_exchange(exchange_id)
        if not exchange: return pd.DataFrame()
        
        limit = 1000
        since = int(exchange.milliseconds() - (days * 24 * 60 * 60 * 1000))
        all_ohlcv = []
        
        print(f"   -> Fetching {days} days from {exchange_id}...")
        while since < exchange.milliseconds():
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, int(since), limit)
                if not ohlcv: break
                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                if len(ohlcv) < limit: break
            except Exception as e:
                print(f"   [Error] Fetch failed: {e}")
                break
                
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            cols = ['open', 'high', 'low', 'close', 'volume']
            df[cols] = df[cols].apply(pd.to_numeric)
        return df

    def _load_from_csv(self, filepath, days=None, rows=None):
        """CSV Loader (Supports days or fixed row count)"""
        if not filepath or not os.path.exists(filepath):
            # Generate dummy if missing
            return self._generate_dummy_data(days if days else 30)
            
        try:
            df = pd.read_csv(filepath)
            df.columns = [c.lower() for c in df.columns]
            if 'date' in df.columns: df['datetime'] = pd.to_datetime(df['date'])
            elif 'timestamp' in df.columns: df['datetime'] = pd.to_datetime(df['timestamp'])
            df.set_index('datetime', inplace=True)
            
            if rows:
                return df.iloc[-rows:]
            elif days:
                return df.iloc[-(days*24):]
            return df
        except:
            return pd.DataFrame()

    def _generate_dummy_data(self, days):
        """Helper to prevent crashes if user hasn't uploaded CSV yet"""
        import numpy as np
        periods = days * 24
        dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='h')
        base = 150.0 
        prices = base + np.cumsum(np.random.randn(periods))
        
        df = pd.DataFrame(index=dates)
        df['close'] = prices
        df['open'] = prices + np.random.randn(periods)
        df['high'] = df[['open','close']].max(axis=1) + 1
        df['low'] = df[['open','close']].min(axis=1) - 1
        df['volume'] = 1000
        return df
