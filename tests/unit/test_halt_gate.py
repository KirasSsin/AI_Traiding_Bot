"""HaltGate — S35 δ TESTNET halt criteria evaluation (pre-s35-backlog HALT thresholds)."""

from decimal import Decimal

import pytest
from src.risk.halt_gate import HaltGate, HaltTrigger


def _gate() -> HaltGate:
    return HaltGate(
        dd_intraday_threshold=Decimal("0.20"),
        dd_multiday_threshold=Decimal("0.15"),
        consecutive_losses_threshold=5,
        no_trade_months_threshold=6,
    )


def test_intraday_dd_triggers_halt() -> None:
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.21"),
        multiday_dd=Decimal("0.05"),
        consecutive_losses=0,
        months_since_last_trade=0,
    )
    assert trigger == HaltTrigger.DD_INTRADAY


def test_multiday_dd_triggers_halt() -> None:
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.05"),
        multiday_dd=Decimal("0.16"),
        consecutive_losses=0,
        months_since_last_trade=0,
    )
    assert trigger == HaltTrigger.DD_MULTIDAY


def test_consecutive_losses_triggers_halt() -> None:
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.05"),
        multiday_dd=Decimal("0.05"),
        consecutive_losses=5,
        months_since_last_trade=0,
    )
    assert trigger == HaltTrigger.CONSECUTIVE_LOSSES


def test_no_trade_timeout_triggers_halt() -> None:
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.05"),
        multiday_dd=Decimal("0.05"),
        consecutive_losses=0,
        months_since_last_trade=7,
    )
    assert trigger == HaltTrigger.NO_TRADE_TIMEOUT


def test_no_trigger_returns_none() -> None:
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.05"),
        multiday_dd=Decimal("0.05"),
        consecutive_losses=2,
        months_since_last_trade=1,
    )
    assert trigger is None


def test_first_trigger_wins_intraday_priority() -> None:
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.25"),
        multiday_dd=Decimal("0.20"),
        consecutive_losses=10,
        months_since_last_trade=0,
    )
    assert trigger == HaltTrigger.DD_INTRADAY


def test_invalid_thresholds_raise() -> None:
    with pytest.raises(ValueError, match="dd_intraday_threshold must be positive"):
        HaltGate(
            dd_intraday_threshold=Decimal("0"),
            dd_multiday_threshold=Decimal("0.15"),
            consecutive_losses_threshold=5,
            no_trade_months_threshold=6,
        )
    with pytest.raises(ValueError, match="dd_multiday_threshold must be positive"):
        HaltGate(
            dd_intraday_threshold=Decimal("0.20"),
            dd_multiday_threshold=Decimal("0"),
            consecutive_losses_threshold=5,
            no_trade_months_threshold=6,
        )
    with pytest.raises(ValueError, match="consecutive_losses_threshold must be >= 1"):
        HaltGate(
            dd_intraday_threshold=Decimal("0.20"),
            dd_multiday_threshold=Decimal("0.15"),
            consecutive_losses_threshold=0,
            no_trade_months_threshold=6,
        )
    with pytest.raises(ValueError, match="no_trade_months_threshold must be >= 1"):
        HaltGate(
            dd_intraday_threshold=Decimal("0.20"),
            dd_multiday_threshold=Decimal("0.15"),
            consecutive_losses_threshold=5,
            no_trade_months_threshold=0,
        )
