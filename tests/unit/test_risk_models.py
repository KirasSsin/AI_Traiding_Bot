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
    # Scale / exits (10 — S5 added EXIT_OCO_PARTIAL_TIMEOUT; S6 added EXIT_STOP_RESIDUAL_FLATTEN)
    "SCALE_OUT_PARTIAL",
    "EXIT_SL_HIT",
    "EXIT_TP_HIT",
    "EXIT_TRAILING_STOP",
    "EXIT_SIGNAL_FLIP",
    "EXIT_TIME_STOP",
    "EXIT_MANUAL_OVERRIDE",
    "EXIT_CIRCUIT_BREAKER",
    "EXIT_OCO_PARTIAL_TIMEOUT",
    "EXIT_STOP_RESIDUAL_FLATTEN",
    # Rejects (9 — S6 added REJECT_ORDER_ALREADY_TERMINAL for retCode 110001 race)
    "REJECT_RISK_EXCEEDED",
    "REJECT_INSUFFICIENT_BALANCE",
    "REJECT_STALE_DATA",
    "REJECT_RATE_LIMITED",
    "REJECT_CLOCK_DRIFT",
    "REJECT_MIN_NOTIONAL",
    "REJECT_FILTER_PRICE",
    "REJECT_DUPLICATE_SIGNAL",
    "REJECT_ORDER_ALREADY_TERMINAL",
    # Halts (22 — S5 added HALT_RECONCILE_DIVERGENCE; S6 added 6 OCO/bracket halts per ADR 0020;
    #         S7 added HALT_BOOTSTRAP_AMBIGUOUS + HALT_EXIT_RECONCILE_DIVERGENCE per ADR 0021;
    #         S8a added HALT_RUNTIME_CRASH + HALT_BAR_POLL_STALL per ADR 0022;
    #         S36 added 4 HaltGate triggers per ADR 0055; S37 added HALT_UNKNOWN_SYMBOL per ADR 0057)
    "HALT_DRAWDOWN_L1",
    "HALT_DRAWDOWN_L2",
    "HALT_DRAWDOWN_L3",
    "HALT_FLASH_CRASH",
    "HALT_DATA_QUALITY",
    "HALT_EXCHANGE_OUTAGE",
    "HALT_KILL_SWITCH",
    "HALT_RECONCILE_DIVERGENCE",
    "HALT_BRACKET_INCOMPLETE",
    "HALT_OCO_ARM_TIMEOUT",
    "HALT_OCO_SIBLING_STUCK",
    "HALT_PARTIAL_FILL_BELOW_MIN",
    "HALT_FLATTEN_FAILED",
    "HALT_PHANTOM_SL",
    "HALT_BOOTSTRAP_AMBIGUOUS",
    "HALT_EXIT_RECONCILE_DIVERGENCE",
    "HALT_RUNTIME_CRASH",
    "HALT_BAR_POLL_STALL",
    # Reconcile-detected exit (S7 ADR 0021 sub-decision 3)
    "EXIT_RECONCILE_DETECTED",
    # Sentinel-triggered kill (S8a ADR 0022 sub-decision 12)
    "KILL_SWITCH_REQUESTED",
    # S36 ADR 0055 SD-4 — δ TESTNET HaltGate triggers
    "HALT_S36_DD_INTRADAY",
    "HALT_S36_DD_MULTIDAY",
    "HALT_S36_CONSECUTIVE_LOSSES",
    "HALT_S36_NO_TRADE_TIMEOUT",
    # S37 ADR 0057 SD-1+SD-2 — symbol fail-closed
    "HALT_UNKNOWN_SYMBOL",
    # S39 ADR 0059 — volume_breakout strategy entry/exit codes
    "ENTRY_LONG_VOLUME_BREAKOUT",
    "EXIT_FLAT_VOLUME_CHANNEL",
    "EXIT_FLAT_ATR_STOP_VB",
}


@pytest.mark.parametrize("code_name", sorted(EXPECTED_CODES))
def test_each_code_present(code_name: str) -> None:
    """Every code from wiki/trading/concepts/reason-codes.md must exist."""
    assert hasattr(ReasonCode, code_name), f"ReasonCode missing: {code_name}"


def test_all_codes_exact_set() -> None:
    actual = {code.name for code in ReasonCode}
    assert (
        actual == EXPECTED_CODES
    ), f"Missing: {EXPECTED_CODES - actual}; Extra: {actual - EXPECTED_CODES}"


def test_reason_code_count() -> None:
    # 7 entry + 12 exits + 9 rejects + 25 halts = 53
    # (S5: 31, S6 ADR 0020 +8 → 39, S7 ADR 0021 +3 → 42, S8a ADR 0022 +3 → 45, S36 ADR 0055 +4 → 49, S37 ADR 0057 +1 → 50, S39 ADR 0059 +3 → 53)
    assert len(ReasonCode) == 53


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
