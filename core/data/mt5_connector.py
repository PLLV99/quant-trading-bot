"""
Data layer — the only module that touches the MetaTrader 5 API.

Everything above this layer (signals, risk, analytics) works on plain
DataFrames, so it stays importable on machines without the terminal.

MetaTrader5 is Windows-only and talks to the locally running MT5 terminal over
IPC, not to the broker directly. The terminal holds the broker session, which
is why it must be open and signed in before any of this works — and why the
account the terminal is signed into is the account that gets traded.
"""

import pandas as pd

from core.risk.lot_sizing import InstrumentSpec


class MT5Connector:
    """Thin wrapper over the MetaTrader 5 terminal API.

    Methods return falsy values instead of raising, so a caller can fall back
    to another data source rather than crash when the terminal is closed.
    """

    def __init__(self):
        self._mt5 = None

    # ── connection ────────────────────────────────────────────────────────
    def connect(self) -> bool:
        """True only when the terminal is running and authorised."""
        try:
            import MetaTrader5 as mt5
        except ImportError:
            return False

        if not mt5.initialize():
            return False

        self._mt5 = mt5
        return True

    def shutdown(self) -> None:
        if self._mt5 is not None:
            self._mt5.shutdown()
            self._mt5 = None

    def last_error(self):
        return self._mt5.last_error() if self._mt5 else (0, "not connected")

    # ── account ───────────────────────────────────────────────────────────
    def get_account_info(self):
        """Account record, or None when not connected.

        `trade_mode` is worth checking before letting anything trade:
        0 = demo, 1 = contest, 2 = real.
        """
        return self._mt5.account_info() if self._mt5 else None

    def get_balance(self) -> float:
        info = self.get_account_info()
        return float(info.balance) if info else 0.0

    def timeframe(self, name: str):
        """Resolve a timeframe name ("H1", "H4", "M15", ...) to its mt5 constant.

        Saves callers from importing MetaTrader5 just to name a timeframe,
        which is the whole point of keeping the API in one module.
        """
        if self._mt5 is None:
            return None
        try:
            return getattr(self._mt5, f"TIMEFRAME_{name.upper()}")
        except AttributeError:
            raise ValueError(f"Unknown MT5 timeframe: {name!r}") from None

    def get_instrument_spec(self, symbol: str):
        """Broker order-size constraints for `symbol`, or None if unknown.

        The single place these four numbers are read. Both the live bot and the
        backtester size positions from this, so neither can quietly assume a
        lot size the broker would reject.
        """
        if self._mt5 is None:
            return None

        info = self._mt5.symbol_info(symbol)
        if info is None:
            return None

        return InstrumentSpec(
            contract_size=info.trade_contract_size,
            min_lot=info.volume_min,
            lot_step=info.volume_step,
            max_lot=info.volume_max,
        )

    # ── market data ───────────────────────────────────────────────────────
    def fetch_candles(self, symbol: str, limit: int = 288, timeframe=None) -> pd.DataFrame:
        """Most recent `limit` candles as an OHLCV frame indexed by datetime.

        `timeframe` takes an mt5.TIMEFRAME_* constant; it defaults to H1.
        Returns an empty DataFrame when the symbol is unknown or the terminal
        is not connected, so callers check `.empty` rather than catching.
        """
        if self._mt5 is None:
            return pd.DataFrame()

        if timeframe is None:
            timeframe = self._mt5.TIMEFRAME_H1

        rates = self._mt5.copy_rates_from_pos(symbol, timeframe, 0, limit)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df["datetime"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("datetime", inplace=True)
        df.rename(columns={"tick_volume": "volume"}, inplace=True)
        return df[["open", "high", "low", "close", "volume"]]

    # ── orders ────────────────────────────────────────────────────────────
    def _filling_modes(self):
        """Brokers accept different filling policies; try them in order."""
        mt5 = self._mt5
        return [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN]

    def _send(self, request: dict):
        """Send a request, retrying across filling modes on a filling rejection."""
        mt5 = self._mt5
        result = None
        for filling in self._filling_modes():
            request["type_filling"] = filling
            result = mt5.order_send(request)
            if result is None:
                continue
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return result
            if result.retcode != mt5.TRADE_RETCODE_INVALID_FILL:
                return result  # a real rejection — do not keep retrying
        return result

    def place_order(self, symbol: str, order_type, lot: float, sl=None, tp=None):
        """Open a market position. Returns the result, or None if it failed."""
        if self._mt5 is None:
            return None
        mt5 = self._mt5

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 20260101,
            "comment": "quant-trading-bot",
            "type_time": mt5.ORDER_TIME_GTC,
        }
        if sl is not None:
            request["sl"] = float(sl)
        if tp is not None:
            request["tp"] = float(tp)

        result = self._send(request)
        return result if result and result.retcode == mt5.TRADE_RETCODE_DONE else None

    def close_position(self, ticket: int, symbol: str, volume: float, order_type):
        """Close an open position by sending the opposite order against it.

        `order_type` is the closing side, which the caller already worked out.
        Passing `position` makes this correct on hedging accounts, where
        several positions can exist on the same symbol.
        """
        if self._mt5 is None:
            return None
        mt5 = self._mt5

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "position": int(ticket),
            "price": price,
            "deviation": 20,
            "magic": 20260101,
            "comment": "quant-trading-bot close",
            "type_time": mt5.ORDER_TIME_GTC,
        }

        result = self._send(request)
        return result if result and result.retcode == mt5.TRADE_RETCODE_DONE else None
