"""Tests for ReasonCode StrEnum, HaltState StrEnum, and RiskAssessment frozen pydantic model.

Tasks 3 + 4 — Sprint 4 Risk.

NOTE: The wiki reason-codes.md header says "6+7+8+7=28" but the exits section actually
lists 8 codes (including EXIT_CIRCUIT_BREAKER) and halts lists 7. True total = 29.
The plan test asserts 28 which conflicts with the enumerated codes. We follow the wiki's
enumerated codes (all present in the wiki page) and assert len == 29.
Follow-up: ADR amendment to fix wiki header arithmetic (6+8+8+7=29 not 28).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.risk.models import HaltState, RiskAssessment
from src.risk.reason_codes import ReasonCode

# ---------------------------------------------------------------------------
# Task 3 — ReasonCode StrEnum
# ---------------------------------------------------------------------------

EXPECTED_CODES = {
    # Entry (6)
    "ENTRY_LONG_TREND_FOLLOWING",
    "ENTRY_SHORT_TREND_FOLLOWING",
    "ENTRY_LONG_PULLBACK",
    "ENTRY_SHORT_PULLBACK",
    "SCALE_IN_LONG",
    "SCALE_IN_SHORT",
    # Scale / exits (8 — wiki lists EXIT_CIRCUIT_BREAKER here despite header saying 7)
    "SCALE_OUT_PARTIAL",
    "EXIT_SL_HIT",
    "EXIT_TP_HIT",
    "EXIT_TRAILING_STOP",
    "EXIT_SIGNAL_FLIP",
    "EXIT_TIME_STOP",
    "EXIT_MANUAL_OVERRIDE",
    "EXIT_CIRCUIT_BREAKER",
    # Rejects (8)
    "REJECT_RISK_EXCEEDED",
    "REJECT_INSUFFICIENT_BALANCE",
    "REJECT_STALE_DATA",
    "REJECT_RATE_LIMITED",
    "REJECT_CLOCK_DRIFT",
    "REJECT_MIN_NOTIONAL",
    "REJECT_FILTER_PRICE",
    "REJECT_DUPLICATE_SIGNAL",
    # Halts (7 — wiki lists 7 despite header saying 6)
    "HALT_DRAWDOWN_L1",
    "HALT_DRAWDOWN_L2",
    "HALT_DRAWDOWN_L3",
    "HALT_FLASH_CRASH",
    "HALT_DATA_QUALITY",
    "HALT_EXCHANGE_OUTAGE",
    "HALT_KILL_SWITCH",
}


@pytest.mark.parametrize("code_name", sorted(EXPECTED_CODES))
def test_each_code_present(code_name: str) -> None:
    """Every code from wiki/trading/concepts/reason-codes.md must exist."""
    assert hasattr(ReasonCode, code_name), f"ReasonCode missing: {code_name}"


def test_all_codes_exact_set() -> None:
    actual = {code.name for code in ReasonCode}
    assert actual == EXPECTED_CODES, (
        f"Missing: {EXPECTED_CODES - actual}; Extra: {actual - EXPECTED_CODES}"
    )


def test_reason_code_count() -> None:
    # 6 entry + 8 exits + 8 rejects + 7 halts = 29
    assert len(ReasonCode) == 29


def test_reason_code_is_str() -> None:
    assert isinstance(ReasonCode.HALT_DRAWDOWN_L1, str)
    assert ReasonCode.HALT_DRAWDOWN_L1 == "HALT_DRAWDOWN_L1"


def test_risk_relevant_codes_accessible() -> None:
    """Codes used by S4 risk manager must be accessible."""
    _ = ReasonCode.REJECT_RISK_EXCEEDED
    _ = ReasonCode.HALT_DRAWDOWN_L1
    _ = ReasonCode.HALT_DRAWDOWN_L2
    _ = ReasonCode.HALT_DRAWDOWN_L3
    _ = ReasonCode.HALT_FLASH_CRASH
    _ = ReasonCode.HALT_KILL_SWITCH
    _ = ReasonCode.EXIT_CIRCUIT_BREAKER


# ---------------------------------------------------------------------------
# Task 4 — HaltState StrEnum
# ---------------------------------------------------------------------------

def test_halt_state_has_five_values() -> None:
    assert len(HaltState) == 5


def test_halt_state_values() -> None:
    assert {h.value for h in HaltState} == {"L0", "L1", "L2", "L3", "FLASH"}


def test_halt_state_is_str() -> None:
    assert isinstance(HaltState.L0, str)
    assert HaltState.FLASH == "FLASH"


# ---------------------------------------------------------------------------
# Task 4 — RiskAssessment helpers
# ---------------------------------------------------------------------------

def _approved(**overrides) -> dict:
    base = dict(
        signal_id=uuid4(),
        approved=True,
        qty=Decimal("0.001"),
        sl_price=Decimal("49000"),
        tp_price=Decimal("53000"),
        kelly_phase=1,
        kelly_fraction=Decimal("0.01"),
        halt_state=HaltState.L0,
        reason_code=ReasonCode.ENTRY_LONG_TREND_FOLLOWING,
        assessed_at=datetime.now(UTC),
    )
    base.update(overrides)
    return base


def _rejected(**overrides) -> dict:
    base = dict(
        signal_id=uuid4(),
        approved=False,
        qty=None,
        sl_price=None,
        tp_price=None,
        kelly_phase=1,
        kelly_fraction=Decimal("0"),
        halt_state=HaltState.L1,
        reason_code=ReasonCode.REJECT_RISK_EXCEEDED,
        assessed_at=datetime.now(UTC),
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Task 4 — RiskAssessment basic construction
# ---------------------------------------------------------------------------

def test_approved_assessment_constructs() -> None:
    ra = RiskAssessment(**_approved())
    assert ra.approved is True
    assert ra.qty == Decimal("0.001")


def test_rejected_assessment_constructs() -> None:
    ra = RiskAssessment(**_rejected())
    assert ra.approved is False
    assert ra.qty is None


# ---------------------------------------------------------------------------
# Task 4 — frozen model
# ---------------------------------------------------------------------------

def test_risk_assessment_frozen() -> None:
    ra = RiskAssessment(**_approved())
    with pytest.raises((TypeError, ValidationError)):
        ra.approved = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Task 4 — model_validator: approved=True requires qty > 0
# ---------------------------------------------------------------------------

def test_approved_true_requires_qty() -> None:
    with pytest.raises(ValidationError, match="qty"):
        RiskAssessment(**_approved(qty=None))


def test_approved_true_requires_qty_nonzero() -> None:
    with pytest.raises(ValidationError, match="qty"):
        RiskAssessment(**_approved(qty=Decimal("0")))


def test_approved_true_requires_sl_price() -> None:
    with pytest.raises(ValidationError, match="sl_price"):
        RiskAssessment(**_approved(sl_price=None))


def test_approved_true_requires_tp_price() -> None:
    with pytest.raises(ValidationError, match="tp_price"):
        RiskAssessment(**_approved(tp_price=None))


def test_approved_true_requires_tp_gt_sl() -> None:
    with pytest.raises(ValidationError, match="tp_price"):
        RiskAssessment(**_approved(sl_price=Decimal("53000"), tp_price=Decimal("49000")))


def test_approved_true_tp_equal_sl_rejected() -> None:
    with pytest.raises(ValidationError, match="tp_price"):
        RiskAssessment(**_approved(sl_price=Decimal("50000"), tp_price=Decimal("50000")))


# ---------------------------------------------------------------------------
# Task 4 — model_validator: approved=False constraints
# ---------------------------------------------------------------------------

def test_approved_false_allows_qty_none() -> None:
    ra = RiskAssessment(**_rejected(qty=None))
    assert ra.qty is None


def test_approved_false_allows_qty_zero() -> None:
    ra = RiskAssessment(**_rejected(qty=Decimal("0")))
    assert ra.qty == Decimal("0")


def test_approved_false_rejects_nonzero_qty() -> None:
    with pytest.raises(ValidationError, match="qty"):
        RiskAssessment(**_rejected(qty=Decimal("0.001")))


# ---------------------------------------------------------------------------
# Task 4 — serialization
# ---------------------------------------------------------------------------

def test_decimal_serialized_as_string_in_json() -> None:
    ra = RiskAssessment(**_approved())
    j = ra.model_dump_json()
    # Decimal fields must appear as quoted strings, not bare numbers
    assert '"0.001"' in j or '"0.01"' in j


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        RiskAssessment(**_approved(unexpected_field="x"))
