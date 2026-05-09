"""HaltGate — S35 δ TESTNET halt criteria evaluation (pre-s35-backlog HALT thresholds).

S39 T9 Item#10: boundary parametrized tests для DD_MULTIDAY + NO_TRADE_TIMEOUT.
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# S39 T9 Item#10 — DD_MULTIDAY boundary parametrized tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "multiday_dd,expected_trigger",
    [
        (Decimal("0.14"), None),  # below 15% threshold → no halt
        (Decimal("0.15"), HaltTrigger.DD_MULTIDAY),  # at exact threshold (inclusive >=)
        (Decimal("0.16"), HaltTrigger.DD_MULTIDAY),  # above threshold
        (Decimal("0.00"), None),  # zero DD → no halt
    ],
)
def test_dd_multiday_boundary_parametrized(
    multiday_dd: Decimal, expected_trigger: HaltTrigger | None
) -> None:
    """Item#10: exact boundary behavior для multiday_dd threshold (15% default, inclusive >=)."""
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.01"),  # well below intraday 20% threshold
        multiday_dd=multiday_dd,
        consecutive_losses=0,
        months_since_last_trade=0,
    )
    assert trigger == expected_trigger


# ---------------------------------------------------------------------------
# S39 T9 Item#10 — NO_TRADE_TIMEOUT boundary parametrized tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "months_since,expected_trigger",
    [
        (5, None),  # below 6-month threshold → no halt
        (6, HaltTrigger.NO_TRADE_TIMEOUT),  # at exact threshold (inclusive >=)
        (7, HaltTrigger.NO_TRADE_TIMEOUT),  # above threshold
        (0, None),  # just traded → no halt
    ],
)
def test_no_trade_timeout_boundary_parametrized(
    months_since: int, expected_trigger: HaltTrigger | None
) -> None:
    """Item#10: exact boundary behavior для months_since_last_trade threshold (6 months default, inclusive >=)."""
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.01"),  # well below intraday 20% threshold
        multiday_dd=Decimal("0.01"),  # well below multiday 15% threshold
        consecutive_losses=0,
        months_since_last_trade=months_since,
    )
    assert trigger == expected_trigger
