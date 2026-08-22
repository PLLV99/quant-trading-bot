"""
Turning a dollar risk into an order size the broker will actually accept.

This is the step that broke the live account. A risk model says "risk 2% of
$300, so $6 on this trade", and the arithmetic obliges: at a $53 stop distance
on Gold that is 0.0011 lots. No broker fills 0.0011 lots. The floor is 0.01,
which risks $53 — not 2% of the account but 18% of it, and nothing in the
older code said so.

Three separate places used to do this conversion and none of them agreed. The
backtester held fractional lots, so it was quietly measuring a strategy that
could not be executed and could never have surfaced the problem. The live
script clamped up to the minimum without comparing the result to the risk it
was supposed to respect. Everything routes through here now.

The module is deliberately free of MetaTrader5 and of config: it takes numbers
and returns numbers, so the awkward cases are cheap to test.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentSpec:
    """What the broker will accept for one symbol.

    Straight off `mt5.symbol_info()`: `trade_contract_size`, `volume_min`,
    `volume_step`, `volume_max`. Gold is 100 oz per lot with a 0.01 minimum;
    BTC is 1 coin per lot with the same minimum.
    """

    contract_size: float
    min_lot: float
    lot_step: float
    max_lot: float = 100.0

    def value_per_lot(self, price_distance: float) -> float:
        """What a one-lot position gains or loses over `price_distance`."""
        return self.contract_size * price_distance


@dataclass(frozen=True)
class Sizing:
    """The decision, with enough context to log why."""

    lot: float
    risk_amount: float
    requested_risk: float
    reason: str

    @property
    def tradeable(self) -> bool:
        return self.lot > 0

    @property
    def overshoot(self) -> float:
        """How many times the intended risk this position actually takes."""
        if self.requested_risk <= 0:
            return 0.0
        return self.risk_amount / self.requested_risk


def size_position(
    requested_risk: float,
    stop_distance: float,
    spec: InstrumentSpec,
    max_overshoot: float = 1.5,
) -> Sizing:
    """Convert a dollar risk into a legal lot size, or refuse the trade.

    Args:
        requested_risk: what the risk model wants to put at stake, in account
            currency.
        stop_distance: distance from entry to stop, in price units.
        spec: the broker's constraints for this symbol.
        max_overshoot: how far past `requested_risk` the smallest legal
            position may go before the trade is refused. 1.5 allows a position
            to risk half again what was intended; the $300 Gold case overshoots
            by nine times.

    Returns:
        A `Sizing`. `lot == 0` means do not place this trade — either the
        inputs were degenerate or the smallest position the broker allows
        risks more than `max_overshoot` permits.

    Sizes are rounded **down** to the lot step. Rounding to nearest can push a
    position over its risk budget for no reason other than arithmetic, and
    between two legal sizes the smaller one is the one that respects the model.
    """
    if stop_distance <= 0 or requested_risk <= 0 or spec.contract_size <= 0:
        return Sizing(0.0, 0.0, requested_risk, "invalid_inputs")

    risk_per_lot = spec.value_per_lot(stop_distance)
    raw_lot = requested_risk / risk_per_lot

    # Round down to a whole number of lot steps.
    steps = int(raw_lot / spec.lot_step)
    lot = steps * spec.lot_step

    if lot < spec.min_lot:
        # The intended risk buys less than the broker's smallest order. The
        # only options are the minimum lot or no trade at all, so ask whether
        # the minimum is still tolerable rather than clamping up in silence.
        floor_risk = spec.min_lot * risk_per_lot
        if floor_risk > requested_risk * max_overshoot:
            return Sizing(
                0.0,
                floor_risk,
                requested_risk,
                f"min_lot_risks_{floor_risk / requested_risk:.1f}x_intended",
            )
        return Sizing(spec.min_lot, floor_risk, requested_risk, "at_min_lot")

    if lot > spec.max_lot:
        lot = spec.max_lot
        return Sizing(lot, lot * risk_per_lot, requested_risk, "at_max_lot")

    return Sizing(lot, lot * risk_per_lot, requested_risk, "ok")


def minimum_viable_balance(
    stop_distance: float,
    spec: InstrumentSpec,
    risk_per_trade_pct: float,
    max_overshoot: float = 1.5,
) -> float:
    """Smallest balance at which this instrument can be traded within its risk budget.

    The number the post-mortem was reaching for. Below this, the broker's
    minimum lot forces more risk than the model allows and `size_position`
    refuses the trade. Gold at 2% with a ~$54 stop lands near $1,800 with the
    default tolerance; tighten `max_overshoot` toward 1.0 and it climbs.
    """
    if risk_per_trade_pct <= 0 or max_overshoot <= 0:
        return float("inf")
    floor_risk = spec.min_lot * spec.value_per_lot(stop_distance)
    return floor_risk / (risk_per_trade_pct * max_overshoot)
