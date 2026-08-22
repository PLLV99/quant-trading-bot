"""
Tests for the dollar-risk-to-lot-size conversion.

The live account lost money here, so the cases below are mostly the awkward
ones: sizes that fall under the broker's minimum, sizes that do not divide
evenly into the lot step, and the specific $300 Gold position that started all
of this.
"""

import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.risk.lot_sizing import InstrumentSpec, minimum_viable_balance, size_position

# Real Exness values, read off mt5.symbol_info() on 21 Aug 2026.
GOLD = InstrumentSpec(contract_size=100.0, min_lot=0.01, lot_step=0.01, max_lot=200.0)
BTC = InstrumentSpec(contract_size=1.0, min_lot=0.01, lot_step=0.01, max_lot=200.0)

# 1.5x ATR on XAUUSDm H4 at the time, in dollars per ounce.
GOLD_STOP = 53.66


def test_the_three_hundred_dollar_gold_trade_is_refused():
    """The trade this whole module exists because of.

    2% of $300 is $6. The smallest position Gold allows risks $53.66 — nearly
    nine times the budget. The old code took it anyway.
    """
    sizing = size_position(requested_risk=6.00, stop_distance=GOLD_STOP, spec=GOLD)

    assert not sizing.tradeable
    assert sizing.lot == 0
    assert sizing.overshoot == pytest.approx(8.94, rel=0.01)
    assert "min_lot_risks" in sizing.reason


def test_a_funded_account_trades_normally():
    """2% of $10,000 comfortably clears the minimum, so nothing is refused."""
    sizing = size_position(requested_risk=200.0, stop_distance=GOLD_STOP, spec=GOLD)

    assert sizing.tradeable
    assert sizing.lot == pytest.approx(0.03)
    assert sizing.risk_amount <= 200.0


def test_size_rounds_down_never_up():
    """Between two legal sizes, take the one that respects the risk budget.

    0.0373 lots sits between 0.03 and 0.04. Rounding to nearest would pick
    0.04 and quietly exceed the budget; the whole point here is not to do that.
    """
    sizing = size_position(requested_risk=200.0, stop_distance=GOLD_STOP, spec=GOLD)

    assert sizing.lot == pytest.approx(0.03)
    assert sizing.overshoot <= 1.0


def test_minimum_lot_is_accepted_when_the_overshoot_is_small():
    """Refusing every trade that clips its budget would refuse nearly all of them.

    $45 is 2% of $2,250. That buys 0.008 lots, under the broker's minimum, so
    the only choice is 0.01 — which risks $53.66. Over budget, but by 19%, not
    by nine times, and the trade goes ahead.
    """
    sizing = size_position(requested_risk=45.0, stop_distance=GOLD_STOP, spec=GOLD)

    assert sizing.tradeable
    assert sizing.lot == pytest.approx(GOLD.min_lot)
    assert sizing.reason == "at_min_lot"
    assert sizing.overshoot == pytest.approx(1.19, rel=0.01)


def test_overshoot_tolerance_is_configurable():
    """A stricter tolerance refuses a trade the default would allow."""
    args = dict(requested_risk=40.0, stop_distance=GOLD_STOP, spec=GOLD)

    assert size_position(**args, max_overshoot=1.5).tradeable
    assert not size_position(**args, max_overshoot=1.2).tradeable


def test_max_lot_is_respected():
    sizing = size_position(
        requested_risk=1_000_000.0, stop_distance=1.0, spec=BTC
    )

    assert sizing.lot == pytest.approx(BTC.max_lot)
    assert sizing.reason == "at_max_lot"


@pytest.mark.parametrize(
    "requested_risk, stop_distance",
    [(0.0, 10.0), (-5.0, 10.0), (100.0, 0.0), (100.0, -10.0)],
)
def test_degenerate_inputs_never_produce_a_trade(requested_risk, stop_distance):
    """A zero stop distance used to divide by zero somewhere upstream."""
    sizing = size_position(requested_risk, stop_distance, GOLD)

    assert not sizing.tradeable
    assert sizing.reason == "invalid_inputs"


def test_contract_size_changes_everything():
    """Same lot, same stop, wildly different risk — this is why BTC survived.

    Gold is 100 units per lot, BTC is 1. The minimum Gold position risks a
    hundred times what the minimum BTC position does at the same stop distance.
    """
    gold = size_position(requested_risk=10.0, stop_distance=50.0, spec=GOLD)
    btc = size_position(requested_risk=10.0, stop_distance=50.0, spec=BTC)

    assert not gold.tradeable
    assert btc.tradeable


def test_minimum_viable_balance_matches_the_refusal_boundary():
    """The number the post-mortem was reaching for, derived rather than guessed."""
    floor = minimum_viable_balance(
        stop_distance=GOLD_STOP, spec=GOLD, risk_per_trade_pct=0.02
    )

    assert floor == pytest.approx(1788.7, rel=0.01)

    # A hair under the boundary is refused; a hair over is accepted.
    assert not size_position(floor * 0.99 * 0.02, GOLD_STOP, GOLD).tradeable
    assert size_position(floor * 1.01 * 0.02, GOLD_STOP, GOLD).tradeable


def test_minimum_viable_balance_is_infinite_without_a_risk_budget():
    assert minimum_viable_balance(GOLD_STOP, GOLD, risk_per_trade_pct=0.0) == float(
        "inf"
    )
