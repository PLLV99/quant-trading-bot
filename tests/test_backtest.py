"""
Test Suite for the Backtester.

Checks the simulation loop end to end: that signals turn into fills, that every
candle is marked to market, and that stops and targets land where the ATR
multipliers say they should.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.analytics.backtester import Backtester
from core.risk.risk_manager import RiskManager
from core.signals.strategy_engine import StrategyEngine

SL_ATR_MULT = 1.5
TP_ATR_MULT = 4.5


class MockConfig:
    def get(self, key, default):
        return default


def make_backtester(strategy_mode="gold_ha"):
    return Backtester(
        StrategyEngine("XAUUSD", RiskManager(MockConfig())),
        initial_balance=10_000.0,
        verbose=False,
        strategy_mode=strategy_mode,
        sl_atr_mult=SL_ATR_MULT,
        tp_atr_mult=TP_ATR_MULT,
    )


def trending_market(periods=500, leg=20, step=6.0, retrace=0.8, up_fraction=0.6):
    """A staircase uptrend: strong legs up, partial retracements back down.

    The pullback strategy needs all five of its filters to line up at once —
    trend, momentum, ADX, an RSI that has cooled into 35-65, and price back
    near the EMA18. A smooth ramp or a plain sine wave satisfies none of them
    and produces zero trades, so the fixture has to actually pull back.
    """
    prices = [1800.0]
    for i in range(1, periods):
        climbing = (i % leg) < leg * up_fraction
        prices.append(prices[-1] + (step if climbing else -step * retrace))
    close = np.array(prices)
    index = pd.date_range(start="2024-01-01", periods=periods, freq="4h")
    return pd.DataFrame(
        {"open": close, "high": close + 2, "low": close - 2, "close": close},
        index=index,
    )


@pytest.fixture(scope="module")
def finished_backtest():
    backtester = make_backtester()
    backtester.run(trending_market())
    return backtester


def entries(backtester):
    """trade_history interleaves entries and exits; only entries carry a stop."""
    return [t for t in backtester.trade_history if "sl" in t]


def exits(backtester):
    return [t for t in backtester.trade_history if "reason" in t]


def test_simulation_executes_trades(finished_backtest):
    assert len(entries(finished_backtest)) > 0


def test_equity_curve_marks_every_candle(finished_backtest):
    assert len(finished_backtest.equity_curve) == 500


def test_account_survives_a_trending_market(finished_backtest):
    """A trend follower given a clean trend should not blow up on it."""
    assert finished_backtest.equity_curve[-1]["equity"] > 5_000


def test_stops_and_targets_bracket_the_entry(finished_backtest):
    """Every fill must have its stop below entry and target above (inverted for shorts)."""
    for trade in entries(finished_backtest):
        entry = trade["price"]
        if trade["side"] == "buy":
            assert trade["sl"] < entry < trade["tp"]
        else:
            assert trade["tp"] < entry < trade["sl"]


def test_reward_to_risk_matches_the_atr_multipliers(finished_backtest):
    """SL 1.5x ATR against TP 4.5x ATR is the 1:3 the strategy advertises."""
    expected = TP_ATR_MULT / SL_ATR_MULT
    for trade in entries(finished_backtest):
        risk = abs(trade["price"] - trade["sl"])
        reward = abs(trade["tp"] - trade["price"])
        assert reward / risk == pytest.approx(expected, rel=1e-6)


def test_every_position_is_closed_by_a_stop_or_a_target(finished_backtest):
    """No position should leak out of the loop unaccounted for."""
    reasons = {t["reason"] for t in exits(finished_backtest)}
    assert reasons <= {"stop_loss", "take_profit", "end_of_data"}


def test_analyzer_is_available_after_run(finished_backtest):
    metrics = finished_backtest.analyzer.get_all_metrics()
    assert metrics["Total Trades"] == len(exits(finished_backtest))


def test_grid_mode_also_runs():
    """The legacy grid path still has to survive a full simulation."""
    backtester = make_backtester(strategy_mode="grid")
    backtester.run(trending_market())
    assert len(backtester.equity_curve) == 500


def test_run_rejects_a_non_datetime_index():
    """A positional index silently breaks the daily reset — fail loudly instead."""
    data = trending_market(periods=60).reset_index(drop=True)
    with pytest.raises(TypeError, match="DatetimeIndex"):
        make_backtester().run(data)


# ─────────────────────────────────────────────────────────────────────
# Broker constraints
# ─────────────────────────────────────────────────────────────────────

from core.risk.lot_sizing import InstrumentSpec

GOLD = InstrumentSpec(contract_size=100.0, min_lot=0.01, lot_step=0.01, max_lot=200.0)


def make_broker_backtester(balance, leverage=100.0):
    """A backtester held to real Gold lot sizes on a margined account."""
    return Backtester(
        StrategyEngine("XAUUSDm", RiskManager(MockConfig())),
        initial_balance=balance,
        verbose=False,
        strategy_mode="gold_ha",
        sl_atr_mult=SL_ATR_MULT,
        tp_atr_mult=TP_ATR_MULT,
        instrument=GOLD,
        leverage=leverage,
    )


def test_positions_are_whole_lot_steps():
    """The point of the whole exercise: no more 0.0037-lot positions."""
    backtester = make_broker_backtester(100_000)
    backtester.run(trending_market())

    for trade in entries(backtester):
        lots = trade["size"] / GOLD.contract_size
        assert lots >= GOLD.min_lot
        assert round(lots / GOLD.lot_step) == pytest.approx(
            lots / GOLD.lot_step, abs=1e-9
        )


def test_a_tiny_account_is_refused_rather_than_oversized():
    """$300 of Gold is the trade that broke the live account.

    The old backtester sized it fractionally and reported a profit. It should
    now decline to trade at all and say why.
    """
    backtester = make_broker_backtester(300)
    backtester.run(trending_market())

    assert entries(backtester) == []
    assert backtester.skipped_trades
    assert all("min_lot" in s["reason"] for s in backtester.skipped_trades)


def test_a_funded_account_still_trades():
    """The guard must not simply refuse everything."""
    backtester = make_broker_backtester(100_000)
    backtester.run(trending_market())

    assert len(entries(backtester)) > 0
    assert backtester.skipped_trades == []


def test_margin_is_posted_not_the_full_notional():
    """At 1:100 a position worth many times the account still has to fit."""
    backtester = make_broker_backtester(100_000)
    backtester.run(trending_market())

    first = entries(backtester)[0]
    notional = first["price"] * first["size"]
    assert first["cost"] == pytest.approx(notional / 100.0)


def test_fractional_sizing_survives_without_an_instrument():
    """No spec means synthetic data with no broker behind it — keep the old model."""
    backtester = make_backtester()
    backtester.run(trending_market())

    assert backtester.instrument is None
    assert len(entries(backtester)) > 0
