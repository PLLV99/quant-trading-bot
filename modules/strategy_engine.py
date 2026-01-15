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
            "grid_levels": 10,  # Reduced from 20
            "base_grid_step_pct": 0.01,
            "trend_ma_period": 50,  # Trend Filter (was 200) - Faster for M15
            "ema_fast": 9,  # Was 18
            "ema_medium": 21,  # Was 35
            "min_atr_period": 14,
            "rsi_period": 14,
        }
        if config_override:
            self.config.update(config_override)

        # State
        self.grid_buy_orders = []  # List of prices
        self.grid_sell_orders = []  # List of prices
        self.current_trend = "neutral"  # bullish, bearish, neutral
        self.last_trade_time = None  # Cooldown tracker

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
            price_history["close"]
            .ewm(span=self.config["trend_ma_period"], adjust=False)
            .mean()
        )
        price_history["ema_18"] = (
            price_history["close"]
            .ewm(span=self.config["ema_fast"], adjust=False)
            .mean()
        )
        price_history["ema_35"] = (
            price_history["close"]
            .ewm(span=self.config["ema_medium"], adjust=False)
            .mean()
        )

        # Calculate RSI
        delta = price_history["close"].diff()
        gain = (
            (delta.where(delta > 0, 0)).rolling(window=self.config["rsi_period"]).mean()
        )
        loss = (
            (-delta.where(delta < 0, 0))
            .rolling(window=self.config["rsi_period"])
            .mean()
        )
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

        BETA ENGINE UPDATE:
        - For Gold (XAU), we use wider steps (1.5% - 2.0%) to capture Alpha moves and avoid Chop.
        """
        if base_atr is None:
            base_atr = (
                current_price * 0.02
            )  # Assuming 2% vol as baseline if not provided

        # Volatility Adjustment Factor
        # If Vol is high, grid widens (to capture noise).
        # If Vol is low, grid tightens (to scalp).
        vol_factor = max(0.5, current_atr / base_atr)

        # BETA ENGINE: Widen grid for Gold to avoid chop
        base_step_pct = self.config["base_grid_step_pct"]
        if "XAU" in self.symbol or "BTC" in self.symbol:
            base_step_pct = 0.015  # 1.5% Base Step for Gold/BTC (was 1%)
            vol_factor = max(
                1.0, vol_factor
            )  # Don't shrink below 1.0 for volatile assets

        dynamic_step = (current_price * base_step_pct) * vol_factor

        # Anti-Chop Check: Ensure step is significantly larger than spread (e.g. 5x)
        # Assuming avg spread ~30-50 pts. Step should be > 200 pts.
        # dynamic_step is price delta. verify it > min_dist

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

    def generate_signal(
        self, current_price, market_data, current_balance, strategy_mode="grid"
    ):
        """
        Main Decision Function.
        Supports 'grid' (Original) and 'gold_ha' (Heikin Ashi Trend)
        """
        # 1. Update Indicators
        # market_data is now expected to be the Last Row of the DF with all indicators
        # Extract scalar values if Series is passed
        atr = (
            market_data["atr"].iloc[-1]
            if hasattr(market_data["atr"], "iloc")
            else market_data["atr"]
        )
        ema_200 = (
            market_data["ema_200"].iloc[-1]
            if hasattr(market_data["ema_200"], "iloc")
            else market_data["ema_200"]
        )

        # 2. Check Trend (General)
        # For Grid: SMA vs Price. For Gold:        # --- NEW: Sniper Filters (Phase 2 Upgrade) ---

        # 0. Cooldown Check (Anti-Machine Gun)
        current_time = market_data.name  # Timestamp
        if self.last_trade_time:
            time_diff = (current_time - self.last_trade_time).total_seconds() / 60
            cooldown_min = config.STRATEGY_PARAMS.get("cooldown_minutes", 15)
            if time_diff < cooldown_min:
                # Still cooling down
                return {"action": "hold", "reason": "cooldown_active"}

        # 1. Trend Filter (EMA 200)
        # We need to make sure we have enough data
        ema_trend = market_data.get("ema_200", None)
        if ema_trend is None and "close" in market_data:
            # Fallback if not pre-calculated (rough approx or wait)
            # Ideally backtester provides this. If not, we skip filter or warn.
            pass

        # 2. RSI Momentum
        rsi = market_data.get("rsi", 50)
        rsi_ob = config.STRATEGY_PARAMS.get("rsi_overbought", 70)
        rsi_os = config.STRATEGY_PARAMS.get("rsi_oversold", 30)

        # --- Strategy Logic ---

        if strategy_mode == "grid":
            # --- Original Grid Logic REFACTORED for Sniper Mode ---

            # 1. Filter Check (Trend & RSI)
            trend_allows_buy = True
            if ema_trend:
                if current_price < ema_trend:
                    trend_allows_buy = False  # Bearish Trend -> NO BUYS

            momentum_allows_buy = True
            if rsi > rsi_ob:
                momentum_allows_buy = False

            # 2. Risk Manager Check (Gatekeeper)
            if not self.risk_manager.check_trade_allowed("buy", current_price):
                return {"action": "hold", "reason": "risk_manager_reject"}

            # 3. Dynamic Grid Calculation
            # Calculate levels based on ATR
            self.calculate_dynamic_grid(current_price, atr)

            # 4. Position Sizing
            safe_size = self.risk_manager.calculate_position_size(
                account_balance=current_balance,
                current_volatility_atr=atr,
                price=current_price,
            )

            # 5. Construct Signal
            # Only include Buy Levels if Filters Pass
            final_buy_levels = (
                self.grid_buy_orders
                if (trend_allows_buy and momentum_allows_buy)
                else []
            )

            # If both buy/sell empty?
            if not final_buy_levels and not self.grid_sell_orders:
                return {"action": "hold", "reason": "filters_blocked_all"}

            return {
                "action": "update_grid",
                "buy_levels": final_buy_levels,
                "sell_levels": self.grid_sell_orders,
                "suggested_size_per_grid": safe_size,
                "trend": "bullish" if trend_allows_buy else "bearish",
            }

        elif strategy_mode == "gold_ha":
            return self._generate_gold_signal(current_price, market_data)

    def _generate_gold_signal(self, current_price, row):
        """
        Gold Heikin Ashi Logic:
        Buy: Price > EMA 200 AND EMA 18 > EMA 35 (Crossover/Stacked)
        Sell: Exit when EMA 18 < EMA 35 (Cross down)
        """
        # Extract scalar values from Series if needed
        ema_18 = (
            row["ema_18"].iloc[-1] if hasattr(row["ema_18"], "iloc") else row["ema_18"]
        )
        ema_35 = (
            row["ema_35"].iloc[-1] if hasattr(row["ema_35"], "iloc") else row["ema_35"]
        )
        ema_200 = (
            row["ema_200"].iloc[-1]
            if hasattr(row["ema_200"], "iloc")
            else row["ema_200"]
        )
        rsi = row.get("rsi", 50)
        if hasattr(rsi, "iloc"):
            rsi = rsi.iloc[-1]

        signal = {"action": "hold", "trend": self.current_trend}

        # Core Logic
        # 1. Macro Trend Filter (EMA 200)
        is_uptrend_macro = current_price > ema_200
        is_downtrend_macro = current_price < ema_200

        # 2. RSI Momentum Filter (50 < RSI < 80 for Long, 20 < RSI < 50 for Short)
        # Using wider bands for crypto/gold volatility
        is_momentum_long = 45 < rsi < 80
        is_momentum_short = 20 < rsi < 55

        # 3. Entry Triggers (EMA Crossover)
        # EMA 18 > EMA 35 = Bullish Momentum
        is_bullish_cross = ema_18 > ema_35
        # EMA 18 < EMA 35 = Bearish Momentum
        is_bearish_cross = ema_18 < ema_35

        # --- LONG SIGNAL ---
        if is_uptrend_macro and is_bullish_cross and is_momentum_long:
            signal["action"] = "buy_signal"
            signal["trend"] = "bullish"

        # --- SHORT SIGNAL ---
        elif is_downtrend_macro and is_bearish_cross and is_momentum_short:
            signal["action"] = "sell_signal"
            signal["trend"] = "bearish"

        # --- EXIT SIGNALS (Reversal) ---
        # If we are in opposite cross, we might want to exit even if not full reversal
        # For simple reversing strategy, the opposite signal acts as exit.

        return signal

    def run_paper_trading(self):
        print("Paper Trading not fully implemented in Strategy Class yet.")
