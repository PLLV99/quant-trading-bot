import pandas as pd
import numpy as np
import time
import config


class StrategyEngine:
    """
    The Engine (Strategy Core)
    Implements:
    1. Dynamic Grid Spacing (ATR-based 'Breathing' Mesh)
    2. Trend Following Filter (Simons' Don't fight the trend)
    3. Integration with 'The Fortress' (Risk Manager)
    """

    def __init__(self, symbol, risk_manager, config_override=None):
        self.symbol = symbol
        self.risk_manager = risk_manager

        # Default Config (can be overridden)
        self.config = {
            "grid_levels": 10,       # Reduced from 20
            "base_grid_step_pct": 0.01,
            "trend_ma_period": 50,   # Trend Filter (was 200) - Faster for M15
            "ema_fast": 9,           # Was 18
            "ema_medium": 21,        # Was 35
            "min_atr_period": 14,
            "rsi_period": 14,
        }
        if config_override:
            self.config.update(config_override)

        # State
        self.grid_buy_orders = []  # List of prices
        self.grid_sell_orders = []  # List of prices
        self.current_trend = "neutral"  # bullish, bearish, neutral

    def add_indicators(self, price_history):
        """
        Calculates ATR, SMAs, and Heikin Ashi.
        """
        # Calculate ATR
        high_low = price_history["high"] - price_history["low"]
        high_close = np.abs(price_history["high"] - price_history["close"].shift())
        low_close = np.abs(price_history["low"] - price_history["close"].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)

        # Simple ATR (Rolling Mean of TR)
        price_history["atr"] = true_range.rolling(self.config["min_atr_period"]).mean()


        # Calculate Trend (EMA 50, 9, 21)
        price_history["ema_200"] = (
            price_history["close"].ewm(span=self.config["trend_ma_period"], adjust=False).mean()
        )
        price_history["ema_18"] = (
            price_history["close"].ewm(span=self.config["ema_fast"], adjust=False).mean()
        )
        price_history["ema_35"] = (
            price_history["close"].ewm(span=self.config["ema_medium"], adjust=False).mean()
        )
        
        # Calculate RSI
        delta = price_history["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config["rsi_period"]).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config["rsi_period"]).mean()
        rs = gain / loss
        price_history["rsi"] = 100 - (100 / (1 + rs))

        # Calculate Heikin Ashi
        price_history = self._calculate_heikin_ashi(price_history)

        return price_history

    def _calculate_heikin_ashi(self, df):
        """
        Transforms standard OHLC into Heikin Ashi Candles.
        HA_Close = (Open + High + Low + Close) / 4
        HA_Open = (Prev_HA_Open + Prev_HA_Close) / 2
        HA_High = Max(High, HA_Open, HA_Close)
        HA_Low = Min(Low, HA_Open, HA_Close)
        """
        ha_df = df.copy()

        ha_df["ha_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

        # Calculate HA Open (Requires loop or efficient shift)
        # Efficient Vectorized approach is hard for HA_Open recursive. Loop is safer for correctness.
        # Given dataframe size usually small in chunks, loop is fine.
        ha_open = [df["open"].iloc[0]]  # Initialize with first real open
        for i in range(1, len(df)):
            ha_open.append((ha_open[-1] + ha_df["ha_close"].iloc[i - 1]) / 2)

        ha_df["ha_open"] = ha_open
        ha_df["ha_high"] = ha_df[["high", "ha_open", "ha_close"]].max(axis=1)
        ha_df["ha_low"] = ha_df[["low", "ha_open", "ha_close"]].min(axis=1)

        return ha_df

    def fetch_market_data(self, price_history):
        """
        Ingests price history (DataFrame) to calculate indicators.
        Expected columns: ['close', 'high', 'low']
        """
        price_history = self.add_indicators(price_history)
        return price_history  # Return FULL DF now, not just slice, because HA needs history

    def calculate_dynamic_grid(self, current_price, current_atr, base_atr=None):
        """
        Generates Grid Levels that 'breathe' with volatility.
        Formula: Step Size = Base Step * (Current ATR / Reference ATR)
        """
        if base_atr is None:
            base_atr = (
                current_price * 0.02
            )  # Assuming 2% vol as baseline if not provided

        # Volatility Adjustment Factor
        # If Vol is high, grid widens (to capture noise).
        # If Vol is low, grid tightens (to scalp).
        vol_factor = max(0.5, current_atr / base_atr)

        dynamic_step = (current_price * self.config["base_grid_step_pct"]) * vol_factor

        lower_limit = current_price * 0.90  # +/- 10% range for demo
        upper_limit = current_price * 1.10

        # Create Levels
        self.grid_buy_orders = []
        self.grid_sell_orders = []

        # Buy Levels (Below current price)
        price = current_price - dynamic_step
        while price > lower_limit:
            self.grid_buy_orders.append(price)
            price -= dynamic_step

        # Sell Levels (Above current price)
        price = current_price + dynamic_step
        while price < upper_limit:
            self.grid_sell_orders.append(price)
            price += dynamic_step

        return dynamic_step, len(self.grid_buy_orders) + len(self.grid_sell_orders)

    def determine_trend(self, current_price, sma_value):
        """
        Jim Simons Style: Logic filters.
        """
        if current_price > sma_value:
            return "bullish"
        elif current_price < sma_value:
            return "bearish"
        return "neutral"

    def generate_signal(self, current_price, market_data, strategy_mode="grid"):
        """
        Main Decision Function.
        Supports 'grid' (Original) and 'gold_ha' (Heikin Ashi Trend)
        """
        # 1. Update Indicators
        # market_data is now expected to be the Last Row of the DF with all indicators
        # Extract scalar values if Series is passed
        atr = market_data["atr"].iloc[-1] if hasattr(market_data["atr"], 'iloc') else market_data["atr"]
        ema_200 = market_data["ema_200"].iloc[-1] if hasattr(market_data["ema_200"], 'iloc') else market_data["ema_200"]

        # 2. Check Trend (General)
        # For Grid: SMA vs Price. For Gold: EMA 200 vs Price.
        self.current_trend = "bullish" if current_price > ema_200 else "bearish"

        if strategy_mode == "gold_ha":
            return self._generate_gold_signal(current_price, market_data)

        # --- ORGINAL GRID LOGIC BELOW ---

        sma = market_data.get("sma_trend", ema_200)  # Fallback
        # Extract scalar if needed
        if hasattr(sma, 'iloc'):
            sma = sma.iloc[-1]
        self.current_trend = self.determine_trend(current_price, sma)

        # 3. Dynamic Grid Logic
        step_size, num_levels = self.calculate_dynamic_grid(current_price, atr)

        # print(f"[Strategy] Price: {current_price:.2f} | Trend: {self.current_trend} | ATR: {atr:.2f}")

        # 4. Filter Logic (Simons)
        allow_buys = True
        if self.current_trend == "bearish":
            # print("           [STOP] Trend is Bearish. Pausing Buy Grid creation.")
            allow_buys = False

        # 5. Risk Check
        safe_size = self.risk_manager.calculate_position_size(
            account_balance=config.PAPER_INITIAL_BALANCE,
            current_volatility_atr=atr,
            price=current_price,
        )

        return {
            "action": "update_grid",
            "buy_levels": self.grid_buy_orders if allow_buys else [],
            "sell_levels": self.grid_sell_orders,
            "suggested_size_per_grid": safe_size,
            "trend": self.current_trend,
        }

    def _generate_gold_signal(self, current_price, row):
        """
        Gold Heikin Ashi Logic:
        Buy: Price > EMA 200 AND EMA 18 > EMA 35 (Crossover/Stacked)
        Sell: Exit when EMA 18 < EMA 35 (Cross down)
        """
        # Extract scalar values from Series if needed
        ema_18 = row["ema_18"].iloc[-1] if hasattr(row["ema_18"], 'iloc') else row["ema_18"]
        ema_35 = row["ema_35"].iloc[-1] if hasattr(row["ema_35"], 'iloc') else row["ema_35"]
        ema_200 = row["ema_200"].iloc[-1] if hasattr(row["ema_200"], 'iloc') else row["ema_200"]
        rsi = row.get("rsi", 50)
        if hasattr(rsi, 'iloc'):
            rsi = rsi.iloc[-1]

        signal = {"action": "hold", "trend": self.current_trend}

        # Core Logic
        # 1. Uptrend Filter: Price MUST be above EMA 50 (Macro Trend)
        is_uptrend_macro = current_price > ema_200

        # 2. Entry Trigger: EMA 9 is above EMA 21
        is_bullish_cross = ema_18 > ema_35
        
        # 3. RSI Momentum Filter (New)
        # Buy only if RSI > 50 (Momentum is Bullish) but < 70 (Not Overbought)
        is_momentum_good = 50 < rsi < 80

        if is_uptrend_macro and is_bullish_cross and is_momentum_good:
            signal["action"] = "buy_signal"  # Signal to enter Long

        elif ema_18 < ema_35:
            signal["action"] = "sell_signal"  # Signal to Exit Long

        return signal

    def run_paper_trading(self):
        print("Paper Trading not fully implemented in Strategy Class yet.")
