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

    def __init__(self, strategy_engine, initial_balance=10000.0, verbose=True):
        self.strategy = strategy_engine
        self.initial_balance = initial_balance
        self.verbose = verbose
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
            signal = self.strategy.generate_signal(current_price, market_slice)

            # 4. Process Signal
            if signal.get("action") == "update_grid":
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
