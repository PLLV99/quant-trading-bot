import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


class Backtester:
    """
    The Lab (Simulation Engine)
    Simulates the strategy against historical data.
    Assumptions:
    - No slippage (Limit orders)
    - 0.1% Fee per trade
    """

    def __init__(self, strategy_engine, initial_balance=10000.0, verbose=True, strategy_mode='grid'):
        self.strategy = strategy_engine
        self.initial_balance = initial_balance
        self.verbose = verbose
        self.strategy_mode = strategy_mode  # 'grid' or 'gold_ha'
        self.balance = initial_balance
        self.inventory = 0.0  # Coin amount
        self.active_orders = (
            []
        )  # List of {'side': 'buy/sell', 'price': 100, 'size': 0.1}
        self.trade_history = []
        self.equity_curve = []

        # Stats
        self.fee_rate = 0.001  # 0.1%

    def run(self, data: pd.DataFrame):
        """
        Main Loop: Iterates through price history (OHLCV).
        """
        if self.verbose:
            print(f"--- Starting Backtest on {len(data)} candles ---")

        # Pre-calculate indicators
        data = self._prepare_indicators(data)

        for index, row in data.iterrows():
            current_price = row["close"]
            high = row["high"]
            low = row["low"]
            timestamp = index

            # 1. Update Portfolio Value (Mark-to-Market)
            portfolio_value = self.balance + (self.inventory * current_price)

            # Update Risk Manager with current equity (for Drawdown tracking)
            self.strategy.risk_manager.update_account_status(portfolio_value)

            self.equity_curve.append(
                {"time": timestamp, "equity": portfolio_value, "price": current_price}
            )

            # 2. Check Order Fills (Engine)
            self._check_fills(high, low, timestamp)

            # 3. Generate Strategy Signals
            market_slice = row
            signal = self.strategy.generate_signal(current_price, market_slice, strategy_mode=self.strategy_mode)

            # 4. Process Signal
            if self.strategy_mode == 'gold_ha':
                # Heikin Ashi Strategy: Buy/Sell signals (not grid)
                action = signal.get("action")
                
                if action == "buy_signal" and self.inventory == 0:
                    # Enter long position
                    size = self._calculate_position_size(current_price, row.get("atr", current_price * 0.02))
                    cost = current_price * size
                    if self.balance >= cost:
                        self.balance -= cost
                        self.inventory += size
                        fee = cost * self.fee_rate
                        self.balance -= fee
                        
                        self.trade_history.append({
                            "time": timestamp,
                            "side": "buy",
                            "price": current_price,
                            "size": size,
                            "fee": fee,
                            "cost": cost,
                        })
                
                elif action == "sell_signal" and self.inventory > 0:
                    # Exit long position
                    revenue = current_price * self.inventory
                    self.balance += revenue
                    fee = revenue * self.fee_rate
                    self.balance -= fee
                    
                    self.trade_history.append({
                        "time": timestamp,
                        "side": "sell",
                        "price": current_price,
                        "size": self.inventory,
                        "fee": fee,
                        "revenue": revenue,
                    })
                    self.inventory = 0.0
                    
            elif signal.get("action") == "update_grid":
                # Original Grid Strategy
                self.active_orders = []

                size = signal.get("suggested_size_per_grid", 0)
                if size > 0:
                    for price in signal["buy_levels"]:
                        # Only place buy if affordable
                        cost = price * size
                        if self.balance >= cost:
                            self.active_orders.append(
                                {"side": "buy", "price": price, "size": size}
                            )

                    for price in signal["sell_levels"]:
                        if self.inventory > 0:
                            self.active_orders.append(
                                {"side": "sell", "price": price, "size": size}
                            )

        self._generate_report()

    def _calculate_position_size(self, current_price, atr):
        """
        Calculate position size for Heikin Ashi strategy.
        Uses 2% risk per trade similar to main risk manager.
        """
        base_risk_pct = 0.02  # 2% of balance
        dollar_risk = self.balance * base_risk_pct
        
        # Risk per share = 3x ATR (stop loss distance)
        stop_distance = atr * 3.0
        
        if stop_distance > 0:
            position_size = dollar_risk / stop_distance
            # Cap at 10% of balance to avoid over-leverage
            max_position_value = self.balance * 0.1
            max_size = max_position_value / current_price
            return min(position_size, max_size)
        
        return 0.0


    def _prepare_indicators(self, data):
        return self.strategy.add_indicators(data)

    def _check_fills(self, high, low, timestamp):
        remaining_orders = []
        for order in self.active_orders:
            filled = False

            # BUY ORDER: Fill if Low <= Order Price
            if order["side"] == "buy" and low <= order["price"]:
                cost = order["price"] * order["size"]
                if self.balance >= cost:
                    self.balance -= cost
                    self.inventory += order["size"]
                    fee = cost * self.fee_rate
                    self.balance -= fee

                    self.trade_history.append(
                        {
                            "time": timestamp,
                            "side": "buy",
                            "price": order["price"],
                            "size": order["size"],
                            "fee": fee,
                            "cost": cost,
                        }
                    )
                    filled = True

            # SELL ORDER: Fill if High >= Order Price
            elif order["side"] == "sell" and high >= order["price"]:
                if self.inventory >= order["size"]:
                    revenue = order["price"] * order["size"]
                    self.balance += revenue
                    self.inventory -= order["size"]
                    fee = revenue * self.fee_rate
                    self.balance -= fee

                    self.trade_history.append(
                        {
                            "time": timestamp,
                            "side": "sell",
                            "price": order["price"],
                            "size": order["size"],
                            "fee": fee,
                            "revenue": revenue,
                        }
                    )
                    filled = True

            if not filled:
                remaining_orders.append(order)

        self.active_orders = remaining_orders

    def _generate_report(self):
        start_eq = self.initial_balance
        end_eq = self.equity_curve[-1]["equity"]
        pnl = end_eq - start_eq
        ret_pct = (pnl / start_eq) * 100

        # Prepare Data Series
        equity_series = pd.Series([x["equity"] for x in self.equity_curve])

        # Max Drawdown
        peaks = equity_series.cummax()
        drawdowns = (equity_series - peaks) / peaks
        max_dd = drawdowns.min() * 100

        # Win Rate & Profit Factor
        winning_trades = 0
        losing_trades = 0  # Difficult to track exactly in grid without FIFO, but can approx via total PnL
        # Grid trading win rate is deceptive. We use realized PnL from sells vs buys.
        # Simplified: Count closed cycles? No, simpler to just track Portfolio metrics.

        # Sharpe Ratio (Daily)
        # Resample to daily returns
        try:
            # Convert equity curve to DataFrame
            df_equity = pd.DataFrame(self.equity_curve)
            df_equity["time"] = pd.to_datetime(df_equity["time"])
            df_equity.set_index("time", inplace=True)

            daily_returns = (
                df_equity["equity"].resample("D").last().pct_change().dropna()
            )

            if len(daily_returns) > 1:
                sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(365)
            else:
                sharpe_ratio = 0.0
        except Exception:
            sharpe_ratio = 0.0

        if self.verbose:
            print("\n=== [The Lab] Advanced Backtest Report ===")
            print(f"Initial Balance: ${start_eq:,.2f}")
            print(f"Final Balance:   ${end_eq:,.2f}")
            print(f"Total Return:    {ret_pct:.2f}%")
            print(f"Max Drawdown:    {max_dd:.2f}%")
            print(f"Sharpe Ratio:    {sharpe_ratio:.2f}")
            print(f"Total Trades:    {len(self.trade_history)}")
            print("===============================\n")

            self.plot_equity_curve()

    def plot_equity_curve(self, filename="backtest_result.png"):
        """Generates a chart of Equity and Price action."""
        df = pd.DataFrame(self.equity_curve)
        if df.empty:
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # Plot 1: Equity Curve
        ax1.plot(df["time"], df["equity"], label="Equity ($)", color="green")
        ax1.set_title("Portfolio Equity")
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Plot 2: Price vs Trades
        ax2.plot(df["time"], df["price"], label="Asset Price", color="gray", alpha=0.5)

        # Scatter buys/sells
        buys = [t for t in self.trade_history if t["side"] == "buy"]
        sells = [t for t in self.trade_history if t["side"] == "sell"]

        if buys:
            buy_times = [t["time"] for t in buys]
            buy_prices = [t["price"] for t in buys]
            ax2.scatter(
                buy_times, buy_prices, marker="^", color="green", label="Buy", s=50
            )

        if sells:
            sell_times = [t["time"] for t in sells]
            sell_prices = [t["price"] for t in sells]
            ax2.scatter(
                sell_times, sell_prices, marker="v", color="red", label="Sell", s=50
            )

        ax2.set_title("Price Action & Trades")
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        plt.tight_layout()
        plt.savefig(filename)
        print(f"Chart saved to {os.path.abspath(filename)}")
        plt.close()
