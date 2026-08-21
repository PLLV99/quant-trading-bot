"""
Test Suite for StrategyEngine (grid mode).

Covers the three things the grid path is responsible for: recognising trend,
breathing the grid with volatility, and refusing to buy into a downtrend.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.risk.risk_manager import RiskManager
from core.signals.strategy_engine import StrategyEngine


class MockConfig:
    def get(self, key, default):
        return default


def make_engine():
    """A fresh engine per scenario — grid levels and cooldown are instance state."""
    return StrategyEngine(symbol="BTC/USDT", risk_manager=RiskManager(MockConfig()))


def make_market(start, end, periods=300, amplitude=8.0, wavelength=40.0):
    """Synthetic OHLC with a linear trend plus a sine wobble.

    The wobble matters: a perfectly straight ramp pins RSI at 0 or 100, which
    the momentum filter reads as exhaustion and blocks every entry. Real price
    action oscillates around its trend, so the test data does too.
    """
    t = np.arange(periods)
    close = np.linspace(start, end, periods) + amplitude * np.sin(
        2 * np.pi * t / wavelength
    )
    index = pd.date_range(start="2024-01-01", periods=periods, freq="h")
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close},
        index=index,
    )


def latest_row(engine, data):
    """generate_signal() consumes the last row, not the whole frame."""
    return engine.fetch_market_data(data).iloc[-1]


@pytest.fixture
def bullish_signal():
    engine = make_engine()
    row = latest_row(engine, make_market(100, 200))
    return engine.generate_signal(
        current_price=float(row["close"]), market_data=row, current_balance=10_000.0
    )


@pytest.fixture
def bearish_signal():
    engine = make_engine()
    row = latest_row(engine, make_market(200, 100))
    return engine.generate_signal(
        current_price=float(row["close"]), market_data=row, current_balance=10_000.0
    )


def test_uptrend_opens_the_buy_grid(bullish_signal):
    """Price above EMA200 with neutral momentum should arm buy levels."""
    assert bullish_signal["trend"] == "bullish"
    assert len(bullish_signal["buy_levels"]) > 0


def test_downtrend_pauses_the_buy_grid(bearish_signal):
    """The whole point of the trend filter: never catch a falling knife."""
    assert bearish_signal["trend"] == "bearish"
    assert bearish_signal["buy_levels"] == []


def test_downtrend_still_sells(bearish_signal):
    """Only buys are gated — sell levels stay live in a downtrend."""
    assert len(bearish_signal["sell_levels"]) > 0


def test_position_size_is_positive(bullish_signal):
    assert bullish_signal["suggested_size_per_grid"] > 0


def test_grid_widens_proportionally_with_volatility():
    """Step size scales linearly with ATR: 5x the volatility, 5x the step."""
    engine = make_engine()
    step_low, _ = engine.calculate_dynamic_grid(
        current_price=200, current_atr=2.0, base_atr=2.0
    )
    step_high, _ = engine.calculate_dynamic_grid(
        current_price=200, current_atr=10.0, base_atr=2.0
    )
    assert step_high / step_low == pytest.approx(5.0, rel=0.05)


def test_grid_does_not_shrink_below_base_step():
    """Volatile symbols floor the multiplier at 1.0 so the grid never over-tightens."""
    engine = make_engine()
    step_base, _ = engine.calculate_dynamic_grid(
        current_price=200, current_atr=2.0, base_atr=2.0
    )
    step_quiet, _ = engine.calculate_dynamic_grid(
        current_price=200, current_atr=0.5, base_atr=2.0
    )
    assert step_quiet == pytest.approx(step_base)
