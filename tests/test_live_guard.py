"""
Tests for the demo-account guard in scripts/run_mt5_live.py.

The connector never sends credentials — it attaches to whichever account the
MT5 terminal happens to be signed into. That makes this check the only thing
between a stray login and real orders, so it gets tested like one.
"""

import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

# The live script imports MetaTrader5 at module level, which only exists on a
# Windows box with the terminal installed.
pytest.importorskip("MetaTrader5")

import run_mt5_live as live

DEMO, CONTEST, REAL = 0, 1, 2


class FakeAccount:
    def __init__(self, trade_mode, trade_allowed=True):
        self.trade_mode = trade_mode
        self.trade_allowed = trade_allowed
        self.login = 999
        self.server = "Fake-Server"
        self.balance = 5000.0


class FakeConnector:
    """Only get_account_info() is reached before the guard decides."""

    def __init__(self, account):
        self._account = account

    def get_account_info(self):
        return self._account


@pytest.fixture(autouse=True)
def default_to_refusing_real_money(monkeypatch):
    monkeypatch.setattr(live, "ALLOW_REAL_MONEY", False)


def test_demo_account_is_allowed():
    assert live.account_is_tradeable(FakeConnector(FakeAccount(DEMO)))


def test_real_money_account_is_refused():
    """The case this guard exists for."""
    assert not live.account_is_tradeable(FakeConnector(FakeAccount(REAL)))


def test_contest_account_is_refused():
    """Not a demo either — anything that is not trade_mode 0 has to opt in."""
    assert not live.account_is_tradeable(FakeConnector(FakeAccount(CONTEST)))


def test_real_money_runs_when_explicitly_allowed(monkeypatch):
    """The flag has to actually work, or someone will delete the guard instead."""
    monkeypatch.setattr(live, "ALLOW_REAL_MONEY", True)
    assert live.account_is_tradeable(FakeConnector(FakeAccount(REAL)))


def test_demo_with_algo_trading_off_is_refused():
    """Orders would be rejected one by one anyway; fail once, up front, with a reason."""
    assert not live.account_is_tradeable(
        FakeConnector(FakeAccount(DEMO, trade_allowed=False))
    )


def test_missing_account_info_is_refused():
    """A connected terminal can still hand back None. Never assume demo."""
    assert not live.account_is_tradeable(FakeConnector(None))
