import MetaTrader5 as mt5
import pandas as pd
import time
import os
from datetime import datetime


class MT5Connector:
    """
    Bridge to Exness via MetaTrader 5 desktop terminal.
    Requires MT5 to be running and logged in.
    """

    def __init__(self):
        self.connected = False

    def connect(self):
        """Initializes connection to MT5 terminal."""
        if not mt5.initialize():
            print(f"❌ [MT5] Initialization failed: {mt5.last_error()}")
            return False

        print(f"[MT5] Connected to: {mt5.terminal_info().name}")
        print(
            f"   Account: {mt5.account_info().login} | Server: {mt5.account_info().server}"
        )
        self.connected = True
        return True

    def fetch_candles(self, symbol, timeframe=mt5.TIMEFRAME_H1, limit=200):
        """
        Fetches OHLCV data from MT5.
        Timeframe mapping: H1=16385, D1=16408, etc.
        """
        if not self.connected:
            self.connect()

        # Ensure symbol is valid (e.g., 'XAUUSDm')
        # Note: Exness symbols often have suffixes like 'm' or 'k' depending on account type.

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, limit)

        if rates is None:
            print(f"[MT5] No data for {symbol}. Check symbol name (suffixes?).")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df["datetime"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("datetime", inplace=True)

        # Rename cols to match our system
        df.rename(columns={"tick_volume": "volume"}, inplace=True)
        return df[["open", "high", "low", "close", "volume"]]

    def get_balance(self):
        if not self.connected:
            self.connect()
        acct = mt5.account_info()
        if acct:
            return acct.balance
        return 0.0

    def place_order(self, symbol, order_type, volume, price=None, sl=0.0, tp=0.0):
        """
        Places Market or Pending order.
        order_type: mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL
        """
        if not self.connected:
            self.connect()

        action = mt5.TRADE_ACTION_DEAL  # Market execution usually

        request = {
            "action": action,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price if price else mt5.symbol_info_tick(symbol).ask,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 123456,
            "comment": "AntiGravity Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Check result
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[MT5] Order Failed: {result.comment} ({result.retcode})")
            return None

        print(f"[MT5] Order Executed: {result.order}")
        return result

    def shutdown(self):
        mt5.shutdown()
