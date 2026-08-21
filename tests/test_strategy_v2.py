"""
AntiGravity Bot v2.0 - Strategy Tests
Tests for the Pullback Sniper strategy logic.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
from core.risk.risk_manager import RiskManager
from core.signals.strategy_engine import StrategyEngine


def make_engine():
    """Create a test StrategyEngine instance."""
    risk_manager = RiskManager(config.RISK_PARAMS)
    return StrategyEngine(symbol="XAUUSDm", risk_manager=risk_manager)


def make_staircase_data(n=300, leg=20, step=6.0, retrace=0.8, up_fraction=0.6,
                        start=4500.0, descending=False):
    """A trend built from strong legs and partial retracements.

    A straight ramp cannot exercise the entry: it pins RSI at 100, which the
    momentum filter reads as exhaustion, and it never lets price come back to
    the EMA18. Only a market that actually retraces satisfies all five filters
    at once, so the fixture has to breathe.
    """
    prices = [start]
    for i in range(1, n):
        climbing = (i % leg) < leg * up_fraction
        delta = step if climbing else -step * retrace
        prices.append(prices[-1] + (-delta if descending else delta))

    close = np.array(prices)
    dates = pd.date_range(start="2026-01-01", periods=n, freq="4h")
    return pd.DataFrame(
        {"open": close, "high": close + 2, "low": close - 2, "close": close},
        index=dates,
    )


def make_no_pullback_data(n=300):
    """
    Create data where trend is strong but NO pullback (price far from EMA18).
    This should NOT generate a signal (waiting for pullback).
    """
    dates = pd.date_range(start="2026-01-01", periods=n, freq="4h")

    # Strong uptrend, accelerating at end (away from EMA18)
    base = np.linspace(4500, 5000, n)
    spike = np.zeros(n)
    spike[-5:] = np.linspace(30, 100, 5)  # price shoots up at end

    close = base + spike

    return pd.DataFrame(
        {"open": close - 2, "high": close + 5, "low": close - 8, "close": close},
        index=dates,
    )


def make_sideways_data(n=300):
    """Directionless chop: an oscillation buried in noise, so ADX stays low.

    A clean sine wave is not chop as ADX measures it — each half-cycle is a
    tidy directional run and ADX reads 60+. The noise is what breaks the
    directional persistence and drives ADX under the threshold.
    """
    dates = pd.date_range(start="2026-01-01", periods=n, freq="4h")
    rng = np.random.default_rng(7)
    close = 4700 + np.sin(np.linspace(0, 10 * np.pi, n)) * 10 + rng.normal(0, 10, n)

    return pd.DataFrame(
        {"open": close - 1, "high": close + 3, "low": close - 3, "close": close},
        index=dates,
    )


def collect_signals(engine, data, warmup=250):
    """Run the strategy bar by bar and return every signal after the warmup."""
    full = engine.add_indicators(data)
    signals = []
    for _, row in full.iloc[warmup:].iterrows():
        signals.append(engine.generate_signal(float(row["close"]), row, 1000, "gold_ha"))
    return signals


def last_signal(engine, data):
    full = engine.add_indicators(data)
    row = full.iloc[-1]
    return engine.generate_signal(float(row["close"]), row, 1000, "gold_ha"), row


def test_pullback_indicator():
    """Test that pullback detection columns are correctly added."""
    engine = make_engine()
    full = engine.add_indicators(make_staircase_data())

    assert "pullback_buy" in full.columns, "pullback_buy column missing!"
    assert "pullback_sell" in full.columns, "pullback_sell column missing!"
    assert "pullback_distance" in full.columns, "pullback_distance column missing!"


def test_pullback_buy_needs_price_above_ema18():
    """A dip *through* the EMA18 is not a long setup — it is a failed one.

    pullback_buy is deliberately one-sided: price has to hold above the EMA18
    while coming back to it. This pins that asymmetry down.
    """
    engine = make_engine()
    full = engine.add_indicators(make_staircase_data())
    dipped = full["close"] < full["ema_18"]

    assert not full.loc[dipped, "pullback_buy"].any()


def test_uptrend_pullback_fires_a_long():
    """The core entry: an uptrend that retraces to the EMA18 must produce a buy."""
    signals = collect_signals(make_engine(), make_staircase_data())
    actions = [s["action"] for s in signals]

    assert "buy_signal" in actions
    assert "sell_signal" not in actions, "Should never short an uptrend"

    entry = next(s for s in signals if s["action"] == "buy_signal")
    assert entry["trend"] == "bullish"
    assert entry["reason"].startswith("pullback_long")


def test_downtrend_pullback_fires_a_short():
    """Mirror image: a downtrend that rallies back to the EMA18 must produce a sell."""
    signals = collect_signals(make_engine(), make_staircase_data(descending=True))
    actions = [s["action"] for s in signals]

    assert "sell_signal" in actions
    assert "buy_signal" not in actions, "Should never long a downtrend"

    entry = next(s for s in signals if s["action"] == "sell_signal")
    assert entry["trend"] == "bearish"
    assert entry["reason"].startswith("pullback_short")


def test_no_signal_without_pullback():
    """Price far from EMA18 means the move is already gone — wait for the retrace."""
    signal, row = last_signal(make_engine(), make_no_pullback_data())

    assert row["pullback_distance"] > config.STRATEGY_PARAMS["pullback_atr_threshold"]
    assert signal["action"] == "hold"
    assert signal["reason"] == "waiting_for_pullback"


def test_sideways_no_signal():
    """Test that sideways market generates no signal (ADX too low)."""
    signal, row = last_signal(make_engine(), make_sideways_data())

    assert row["adx"] < config.STRATEGY_PARAMS["adx_threshold"]
    assert signal["action"] == "hold"
    assert signal["reason"].startswith("adx_too_low")


def test_config_params():
    """Test that v2.0 config params are set correctly."""
    params = config.STRATEGY_PARAMS

    assert params.get("pullback_atr_threshold") == 0.5, "pullback_atr_threshold wrong!"
    assert params.get("rsi_pullback_low") == 35, "rsi_pullback_low wrong!"
    assert params.get("rsi_pullback_high") == 65, "rsi_pullback_high wrong!"
    assert params.get("adx_threshold") == 20, "adx_threshold wrong!"
    assert params.get("cooldown_minutes") == 240, "cooldown_minutes wrong!"

    risk = config.RISK_PARAMS
    assert risk.get("stop_loss_atr_multiplier") == 1.5, "SL ATR mult wrong!"
