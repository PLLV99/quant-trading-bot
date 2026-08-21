import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for server/VPS
import matplotlib.pyplot as plt
import os


class PerformanceAnalyzer:
    """
    Professional Performance Analytics Engine.
    Calculates institutional-grade metrics from equity curve and trade history.
    """

    def __init__(
        self,
        equity_curve: list,
        trade_history: list,
        initial_balance: float,
        risk_free_rate: float = 0.04,
    ):
        self.equity_curve = equity_curve
        self.trade_history = trade_history
        self.initial_balance = initial_balance
        self.risk_free_rate = risk_free_rate  # Annual risk-free rate (4% default)

        # Build DataFrames
        self.df_equity = pd.DataFrame(equity_curve)
        if not self.df_equity.empty:
            self.df_equity["time"] = pd.to_datetime(self.df_equity["time"])
            self.df_equity.set_index("time", inplace=True)

        # Calculate core series
        self.equity_series = (
            self.df_equity["equity"] if not self.df_equity.empty else pd.Series()
        )
        self.daily_returns = self._calc_daily_returns()
        self.trade_pnls = self._calc_trade_pnls()

    # ───────────────────────────────────────────
    # Core Return Calculations
    # ───────────────────────────────────────────

    def _calc_daily_returns(self) -> pd.Series:
        """Resample equity to daily and compute returns."""
        if self.equity_series.empty:
            return pd.Series()
        daily_eq = self.equity_series.resample("D").last().dropna()
        return daily_eq.pct_change().dropna()

    def _calc_trade_pnls(self) -> list:
        """Match buy/sell pairs to compute per-trade P&L."""
        pnls = []
        open_trade = None
        for trade in self.trade_history:
            if trade["side"] == "buy" and open_trade is None:
                open_trade = trade
            elif trade["side"] == "sell" and open_trade is not None:
                entry_cost = open_trade["price"] * open_trade["size"]
                exit_revenue = trade["price"] * trade["size"]
                pnl = (
                    exit_revenue
                    - entry_cost
                    - open_trade.get("fee", 0)
                    - trade.get("fee", 0)
                )
                pnls.append(
                    {
                        "entry_time": open_trade["time"],
                        "exit_time": trade["time"],
                        "entry_price": open_trade["price"],
                        "exit_price": trade["price"],
                        "size": open_trade["size"],
                        "pnl": pnl,
                        "return_pct": (pnl / entry_cost) * 100 if entry_cost > 0 else 0,
                        "duration": (
                            trade["time"] - open_trade["time"]
                            if hasattr(trade["time"], "__sub__")
                            else None
                        ),
                    }
                )
                open_trade = None
        return pnls

    # ───────────────────────────────────────────
    # Performance Metrics
    # ───────────────────────────────────────────

    def total_return(self) -> float:
        """Total return percentage."""
        if self.equity_series.empty:
            return 0.0
        return ((self.equity_series.iloc[-1] / self.initial_balance) - 1) * 100

    def cagr(self) -> float:
        """Compound Annual Growth Rate."""
        if self.equity_series.empty or len(self.daily_returns) < 2:
            return 0.0
        total_days = (self.equity_series.index[-1] - self.equity_series.index[0]).days
        if total_days <= 0:
            return 0.0
        total_ret = self.equity_series.iloc[-1] / self.initial_balance
        return (total_ret ** (365 / total_days) - 1) * 100

    def sharpe_ratio(self) -> float:
        """Annualized Sharpe Ratio (daily returns)."""
        if len(self.daily_returns) < 2:
            return 0.0
        excess = self.daily_returns - (self.risk_free_rate / 252)
        if excess.std() == 0:
            return 0.0
        return (excess.mean() / excess.std()) * np.sqrt(252)

    def sortino_ratio(self) -> float:
        """Sortino Ratio — only penalizes downside volatility."""
        if len(self.daily_returns) < 2:
            return 0.0
        excess = self.daily_returns - (self.risk_free_rate / 252)
        downside = self.daily_returns[self.daily_returns < 0]
        if len(downside) == 0 or downside.std() == 0:
            return float("inf") if excess.mean() > 0 else 0.0
        return (excess.mean() / downside.std()) * np.sqrt(252)

    def calmar_ratio(self) -> float:
        """Calmar Ratio = CAGR / Max Drawdown."""
        dd = self.max_drawdown()
        c = self.cagr()
        if dd == 0:
            return float("inf") if c > 0 else 0.0
        return c / abs(dd)

    def max_drawdown(self) -> float:
        """Maximum drawdown percentage."""
        if self.equity_series.empty:
            return 0.0
        peaks = self.equity_series.cummax()
        dd = (self.equity_series - peaks) / peaks * 100
        return dd.min()

    def max_drawdown_duration(self) -> int:
        """Longest drawdown period in days."""
        if self.equity_series.empty:
            return 0
        peaks = self.equity_series.cummax()
        in_dd = self.equity_series < peaks
        if not in_dd.any():
            return 0
        # Count consecutive drawdown days
        groups = (~in_dd).cumsum()
        dd_groups = in_dd.groupby(groups).sum()
        return int(dd_groups.max()) if len(dd_groups) > 0 else 0

    def win_rate(self) -> float:
        """Win rate from completed trades."""
        if not self.trade_pnls:
            return 0.0
        wins = sum(1 for t in self.trade_pnls if t["pnl"] > 0)
        return (wins / len(self.trade_pnls)) * 100

    def profit_factor(self) -> float:
        """Gross Profit / Gross Loss."""
        if not self.trade_pnls:
            return 0.0
        gross_profit = sum(t["pnl"] for t in self.trade_pnls if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in self.trade_pnls if t["pnl"] < 0))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def expectancy(self) -> float:
        """Expected value per trade in dollars."""
        if not self.trade_pnls:
            return 0.0
        return sum(t["pnl"] for t in self.trade_pnls) / len(self.trade_pnls)

    def avg_win(self) -> float:
        """Average winning trade P&L."""
        wins = [t["pnl"] for t in self.trade_pnls if t["pnl"] > 0]
        return sum(wins) / len(wins) if wins else 0.0

    def avg_loss(self) -> float:
        """Average losing trade P&L."""
        losses = [t["pnl"] for t in self.trade_pnls if t["pnl"] < 0]
        return sum(losses) / len(losses) if losses else 0.0

    def payoff_ratio(self) -> float:
        """Average Win / Average Loss (absolute)."""
        al = self.avg_loss()
        if al == 0:
            return float("inf") if self.avg_win() > 0 else 0.0
        return abs(self.avg_win() / al)

    def get_all_metrics(self) -> dict:
        """Returns all metrics as a dictionary."""
        return {
            "Total Return (%)": round(self.total_return(), 2),
            "CAGR (%)": round(self.cagr(), 2),
            "Sharpe Ratio": round(self.sharpe_ratio(), 2),
            "Sortino Ratio": round(self.sortino_ratio(), 2),
            "Calmar Ratio": round(self.calmar_ratio(), 2),
            "Max Drawdown (%)": round(self.max_drawdown(), 2),
            "Max DD Duration (days)": self.max_drawdown_duration(),
            "Total Trades": len(self.trade_pnls),
            "Win Rate (%)": round(self.win_rate(), 2),
            "Profit Factor": round(self.profit_factor(), 2),
            "Expectancy ($)": round(self.expectancy(), 2),
            "Avg Win ($)": round(self.avg_win(), 2),
            "Avg Loss ($)": round(self.avg_loss(), 2),
            "Payoff Ratio": round(self.payoff_ratio(), 2),
            "Initial Balance ($)": round(self.initial_balance, 2),
            "Final Balance ($)": (
                round(self.equity_series.iloc[-1], 2)
                if not self.equity_series.empty
                else 0
            ),
        }


class MonteCarloSimulator:
    """
    Monte Carlo Analysis — Stress Tests Strategy Robustness.
    Shuffles trade returns to generate probability distributions.
    """

    def __init__(
        self, trade_pnls: list, initial_balance: float, n_simulations: int = 500
    ):
        self.trade_returns = [t["return_pct"] / 100 for t in trade_pnls]
        self.initial_balance = initial_balance
        self.n_simulations = n_simulations

    def run(self) -> dict:
        """Run Monte Carlo simulation. Returns dict with paths and stats."""
        if len(self.trade_returns) < 3:
            return {"paths": [], "stats": {}}

        n_trades = len(self.trade_returns)
        paths = []

        for _ in range(self.n_simulations):
            shuffled = np.random.choice(self.trade_returns, size=n_trades, replace=True)
            equity = [self.initial_balance]
            for ret in shuffled:
                equity.append(equity[-1] * (1 + ret))
            paths.append(equity)

        paths = np.array(paths)
        final_values = paths[:, -1]

        return {
            "paths": paths,
            "stats": {
                "median_final": round(float(np.median(final_values)), 2),
                "mean_final": round(float(np.mean(final_values)), 2),
                "p5_final": round(float(np.percentile(final_values, 5)), 2),
                "p25_final": round(float(np.percentile(final_values, 25)), 2),
                "p75_final": round(float(np.percentile(final_values, 75)), 2),
                "p95_final": round(float(np.percentile(final_values, 95)), 2),
                "prob_profit": round(
                    float(np.mean(final_values > self.initial_balance)) * 100, 1
                ),
                "prob_ruin": round(
                    float(np.mean(final_values < self.initial_balance * 0.5)) * 100, 1
                ),
            },
        }


class Backtester:
    """
    Professional Backtesting Engine v2.0
    Simulates trading strategies against historical data with
    institutional-grade analytics and Monte Carlo stress testing.

    Features:
    - SL/TP simulation (ATR-based)
    - Per-trade P&L tracking
    - PerformanceAnalyzer integration
    - Monte Carlo robustness testing
    - Professional multi-panel charts
    """

    def __init__(
        self,
        strategy_engine,
        initial_balance=10000.0,
        verbose=True,
        strategy_mode="gold_ha",
        sl_atr_mult=1.5,
        tp_atr_mult=4.5,
    ):
        self.strategy = strategy_engine
        self.initial_balance = initial_balance
        self.verbose = verbose
        self.strategy_mode = strategy_mode
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.balance = initial_balance
        self.inventory = 0.0
        self.active_orders = []
        self.trade_history = []
        self.equity_curve = []

        # v2.0: Track open position for SL/TP
        self.open_position = None  # {'entry_price', 'size', 'sl', 'tp', 'side', 'time'}

        # Stats
        self.fee_rate = 0.001  # 0.1%
        self.analyzer = None  # Set after run()

    def run(self, data: pd.DataFrame):
        """
        Main simulation loop.
        Iterates through OHLCV data, generates signals, simulates fills.

        `data` must be indexed by timestamp: the daily-reset and cooldown
        logic both read the index as a datetime.
        """
        if not isinstance(data.index, pd.DatetimeIndex):
            raise TypeError(
                "Backtester.run() needs a DatetimeIndex — the daily loss reset "
                f"and the signal cooldown both read the index as a timestamp, but got {type(data.index).__name__}. "
                "Set one with data.index = pd.to_datetime(data['time'])."
            )

        if self.verbose:
            print(f"────────────────────────────────────────────")
            print(f"  BACKTEST ENGINE v2.0")
            print(f"  Strategy: {self.strategy_mode}")
            print(
                f"  Candles: {len(data)} | SL: {self.sl_atr_mult}x ATR | TP: {self.tp_atr_mult}x ATR"
            )
            print(f"────────────────────────────────────────────")

        # Pre-calculate indicators
        data = self._prepare_indicators(data)

        last_date = None

        for index, row in data.iterrows():
            current_price = row["close"]
            high = row["high"]
            low = row["low"]
            timestamp = index
            atr = row.get("atr", current_price * 0.02)

            # --- Day Reset Logic ---
            current_date = timestamp.date()
            if last_date is None or current_date != last_date:
                self.strategy.risk_manager.reset_daily_stats(
                    self.balance + (self.inventory * current_price)
                )
                last_date = current_date

            # --- Check SL/TP on open position ---
            if self.open_position:
                self._check_sl_tp(high, low, timestamp)

            # 1. Update Portfolio Value (Mark-to-Market)
            portfolio_value = self.balance + (self.inventory * current_price)
            self.strategy.risk_manager.update_account_status(portfolio_value)

            # --- Check Daily Limits ---
            is_allowed, reason = self.strategy.risk_manager.check_daily_status(
                portfolio_value
            )

            self.equity_curve.append(
                {"time": timestamp, "equity": portfolio_value, "price": current_price}
            )

            if not is_allowed:
                self.active_orders = []
                continue

            # 2. Check Order Fills (legacy grid)
            if self.strategy_mode == "grid":
                self._check_fills(high, low, timestamp)

            # 3. Generate Strategy Signals
            signal = self.strategy.generate_signal(
                current_price,
                row,
                current_balance=portfolio_value,
                strategy_mode=self.strategy_mode,
            )

            # 4. Process Signal
            if self.strategy_mode == "gold_ha":
                action = signal.get("action")

                if action == "buy_signal" and self.inventory == 0:
                    # Enter LONG
                    size = self._calculate_position_size(current_price, atr)
                    cost = current_price * size
                    if self.balance >= cost and size > 0:
                        fee = cost * self.fee_rate
                        self.balance -= cost + fee
                        self.inventory += size

                        sl_price = current_price - (atr * self.sl_atr_mult)
                        tp_price = current_price + (atr * self.tp_atr_mult)

                        self.open_position = {
                            "side": "buy",
                            "entry_price": current_price,
                            "size": size,
                            "sl": sl_price,
                            "tp": tp_price,
                            "time": timestamp,
                        }

                        self.trade_history.append(
                            {
                                "time": timestamp,
                                "side": "buy",
                                "price": current_price,
                                "size": size,
                                "fee": fee,
                                "cost": cost,
                                "sl": sl_price,
                                "tp": tp_price,
                            }
                        )
                        self.strategy.last_trade_time = timestamp

                elif action == "sell_signal" and self.inventory > 0:
                    # Exit LONG (signal-based)
                    self._close_position(current_price, timestamp, reason="signal")

            elif signal.get("action") == "update_grid":
                # Legacy Grid Strategy
                self.active_orders = []
                size = signal.get("suggested_size_per_grid", 0)
                if size > 0:
                    for price in signal["buy_levels"]:
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

        # Close any remaining open position at last price
        if self.open_position and self.inventory > 0:
            last_price = data.iloc[-1]["close"]
            self._close_position(last_price, data.index[-1], reason="end_of_data")

        # Build Performance Analyzer
        self.analyzer = PerformanceAnalyzer(
            self.equity_curve, self.trade_history, self.initial_balance
        )

        if self.verbose:
            self._print_report()
            self.plot_results()

    def _check_sl_tp(self, high, low, timestamp):
        """Check if SL or TP was hit on current bar."""
        pos = self.open_position
        if not pos:
            return

        if pos["side"] == "buy":
            # Check SL (low <= sl)
            if low <= pos["sl"]:
                self._close_position(pos["sl"], timestamp, reason="stop_loss")
            # Check TP (high >= tp)
            elif high >= pos["tp"]:
                self._close_position(pos["tp"], timestamp, reason="take_profit")

    def _close_position(self, exit_price, timestamp, reason=""):
        """Close current open position."""
        if self.inventory <= 0:
            return
        revenue = exit_price * self.inventory
        fee = revenue * self.fee_rate
        self.balance += revenue - fee

        self.trade_history.append(
            {
                "time": timestamp,
                "side": "sell",
                "price": exit_price,
                "size": self.inventory,
                "fee": fee,
                "revenue": revenue,
                "reason": reason,
            }
        )
        self.inventory = 0.0
        self.open_position = None
        self.strategy.last_trade_time = timestamp

    def _calculate_position_size(self, current_price, atr):
        """Position sizing using fractional risk model."""
        import config

        base_risk_pct = config.RISK_PARAMS.get("risk_per_trade_pct", 0.02)
        dollar_risk = self.balance * base_risk_pct
        stop_distance = atr * self.sl_atr_mult

        if stop_distance > 0:
            position_size = dollar_risk / stop_distance
            max_position_value = self.balance * 0.1
            max_size = max_position_value / current_price
            return min(position_size, max_size)
        return 0.0

    def _prepare_indicators(self, data):
        return self.strategy.add_indicators(data)

    def _check_fills(self, high, low, timestamp):
        """Legacy grid order fill check."""
        remaining_orders = []
        for order in self.active_orders:
            filled = False
            if order["side"] == "buy" and low <= order["price"]:
                cost = order["price"] * order["size"]
                if self.balance >= cost:
                    fee = cost * self.fee_rate
                    self.balance -= cost + fee
                    self.inventory += order["size"]
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
                    self.strategy.last_trade_time = timestamp
            elif order["side"] == "sell" and high >= order["price"]:
                if self.inventory >= order["size"]:
                    revenue = order["price"] * order["size"]
                    fee = revenue * self.fee_rate
                    self.balance += revenue - fee
                    self.inventory -= order["size"]
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
                    self.strategy.last_trade_time = timestamp
            if not filled:
                remaining_orders.append(order)
        self.active_orders = remaining_orders

    # ───────────────────────────────────────────
    # Reporting & Visualization
    # ───────────────────────────────────────────

    def _print_report(self):
        """Print professional performance report."""
        if not self.analyzer:
            return
        metrics = self.analyzer.get_all_metrics()

        print("\n" + "═" * 50)
        print("  BACKTEST PERFORMANCE REPORT")
        print("═" * 50)

        # Portfolio
        print(f"\n  {'Initial Balance:':<25} ${metrics['Initial Balance ($)']:>12,.2f}")
        print(f"  {'Final Balance:':<25} ${metrics['Final Balance ($)']:>12,.2f}")
        print(f"  {'Total Return:':<25} {metrics['Total Return (%)']:>12.2f}%")
        print(f"  {'CAGR:':<25} {metrics['CAGR (%)']:>12.2f}%")

        # Risk-Adjusted
        print(f"\n  {'─── Risk-Adjusted ───'}")
        print(f"  {'Sharpe Ratio:':<25} {metrics['Sharpe Ratio']:>12.2f}")
        print(f"  {'Sortino Ratio:':<25} {metrics['Sortino Ratio']:>12.2f}")
        print(f"  {'Calmar Ratio:':<25} {metrics['Calmar Ratio']:>12.2f}")
        print(f"  {'Max Drawdown:':<25} {metrics['Max Drawdown (%)']:>12.2f}%")
        print(
            f"  {'Max DD Duration:':<25} {metrics['Max DD Duration (days)']:>10d} days"
        )

        # Trade Stats
        print(f"\n  {'─── Trade Statistics ───'}")
        print(f"  {'Total Trades:':<25} {metrics['Total Trades']:>12d}")
        print(f"  {'Win Rate:':<25} {metrics['Win Rate (%)']:>12.2f}%")
        print(f"  {'Profit Factor:':<25} {metrics['Profit Factor']:>12.2f}")
        print(f"  {'Expectancy:':<25} ${metrics['Expectancy ($)']:>12.2f}")
        print(f"  {'Avg Win:':<25} ${metrics['Avg Win ($)']:>12.2f}")
        print(f"  {'Avg Loss:':<25} ${metrics['Avg Loss ($)']:>12.2f}")
        print(f"  {'Payoff Ratio:':<25} {metrics['Payoff Ratio']:>12.2f}")

        print("\n" + "═" * 50)

        # Monte Carlo
        if len(self.analyzer.trade_pnls) >= 3:
            print("\n  Running Monte Carlo Simulation (500 paths)...")
            mc = MonteCarloSimulator(
                self.analyzer.trade_pnls, self.initial_balance, n_simulations=500
            )
            mc_results = mc.run()
            if mc_results["stats"]:
                stats = mc_results["stats"]
                print(f"\n  {'─── Monte Carlo Results ───'}")
                print(
                    f"  {'Probability of Profit:':<25} {stats['prob_profit']:>10.1f}%"
                )
                print(f"  {'Probability of Ruin:':<25} {stats['prob_ruin']:>10.1f}%")
                print(
                    f"  {'Median Final Balance:':<25} ${stats['median_final']:>10,.2f}"
                )
                print(f"  {'5th Percentile:':<25} ${stats['p5_final']:>10,.2f}")
                print(f"  {'95th Percentile:':<25} ${stats['p95_final']:>10,.2f}")
                print("═" * 50)

    def plot_results(self, filename="backtest_result.png"):
        """Generate professional 4-panel performance chart."""
        if not self.analyzer or self.analyzer.equity_series.empty:
            return

        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle(
            "AntiGravity Backtest — Performance Report", fontsize=14, fontweight="bold"
        )

        # Panel 1: Equity Curve
        ax1 = axes[0, 0]
        eq = self.analyzer.equity_series
        ax1.plot(eq.index, eq.values, color="#2196F3", linewidth=1.5, label="Equity")
        ax1.fill_between(
            eq.index,
            self.initial_balance,
            eq.values,
            where=eq.values >= self.initial_balance,
            alpha=0.15,
            color="green",
        )
        ax1.fill_between(
            eq.index,
            self.initial_balance,
            eq.values,
            where=eq.values < self.initial_balance,
            alpha=0.15,
            color="red",
        )
        ax1.axhline(y=self.initial_balance, color="gray", linestyle="--", alpha=0.5)
        ax1.set_title("Equity Curve")
        ax1.set_ylabel("Balance ($)")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Panel 2: Drawdown
        ax2 = axes[0, 1]
        peaks = eq.cummax()
        dd = (eq - peaks) / peaks * 100
        ax2.fill_between(dd.index, dd.values, 0, color="red", alpha=0.3)
        ax2.plot(dd.index, dd.values, color="red", linewidth=0.8)
        ax2.set_title(f"Drawdown (Max: {dd.min():.1f}%)")
        ax2.set_ylabel("Drawdown (%)")
        ax2.grid(True, alpha=0.3)

        # Panel 3: Trade P&L Distribution
        ax3 = axes[1, 0]
        if self.analyzer.trade_pnls:
            pnls = [t["pnl"] for t in self.analyzer.trade_pnls]
            colors = ["#4CAF50" if p > 0 else "#F44336" for p in pnls]
            ax3.bar(range(len(pnls)), pnls, color=colors, alpha=0.8)
            ax3.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)
            ax3.set_title(f"Trade P&L (Win Rate: {self.analyzer.win_rate():.1f}%)")
            ax3.set_xlabel("Trade #")
            ax3.set_ylabel("P&L ($)")
        else:
            ax3.text(0.5, 0.5, "No completed trades", ha="center", va="center")
        ax3.grid(True, alpha=0.3)

        # Panel 4: Monte Carlo
        ax4 = axes[1, 1]
        if len(self.analyzer.trade_pnls) >= 3:
            mc = MonteCarloSimulator(
                self.analyzer.trade_pnls, self.initial_balance, n_simulations=200
            )
            mc_results = mc.run()
            if len(mc_results["paths"]) > 0:
                for path in mc_results["paths"][:200]:
                    ax4.plot(path, color="blue", alpha=0.02, linewidth=0.5)
                # Highlight percentiles
                median_path = np.median(mc_results["paths"], axis=0)
                p5_path = np.percentile(mc_results["paths"], 5, axis=0)
                p95_path = np.percentile(mc_results["paths"], 95, axis=0)
                ax4.plot(median_path, color="blue", linewidth=2, label="Median")
                ax4.plot(
                    p5_path, color="red", linewidth=1, linestyle="--", label="5th %ile"
                )
                ax4.plot(
                    p95_path,
                    color="green",
                    linewidth=1,
                    linestyle="--",
                    label="95th %ile",
                )
                ax4.axhline(
                    y=self.initial_balance, color="gray", linestyle="--", alpha=0.5
                )
                prob = mc_results["stats"]["prob_profit"]
                ax4.set_title(f"Monte Carlo ({prob:.0f}% Profit Probability)")
                ax4.legend(fontsize=8)
        else:
            ax4.text(
                0.5, 0.5, "Need 3+ trades\nfor Monte Carlo", ha="center", va="center"
            )
        ax4.set_ylabel("Balance ($)")
        ax4.set_xlabel("Trade #")
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches="tight")
        print(f"\n  Chart saved: {os.path.abspath(filename)}")
        plt.close()
