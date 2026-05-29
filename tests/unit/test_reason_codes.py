"""Tests for ReasonCode enum extensions (Sprint 5 Task 1).

ADR ref: wiki/project/decisions/0019-sprint-5-execution-decisions.md sub-decision 4
"""

from src.risk.reason_codes import ReasonCode


def test_halt_reconcile_divergence_in_enum():
    assert ReasonCode.HALT_RECONCILE_DIVERGENCE.value == "HALT_RECONCILE_DIVERGENCE"


def test_exit_oco_partial_timeout_in_enum():
    assert ReasonCode.EXIT_OCO_PARTIAL_TIMEOUT.value == "EXIT_OCO_PARTIAL_TIMEOUT"


def test_total_reason_codes_count():
    assert (
        len(ReasonCode) == 65
    )  # 31 (S5) +8 (S6 ADR 0020) +3 (S7 ADR 0021) +3 (S8a ADR 0022) +4 (S36 ADR 0055) +1 (S37 ADR 0057) +3 (S39 ADR 0059) +3 (S40 ADR 0060) +7 (S49 H6 ADR 0023 amendment) +2 (S50 ADR 0067 Supertrend)


def test_v2_count_is_56() -> None:
    assert len(list(ReasonCode)) == 65


def test_s7_codes_present() -> None:
    """ADR 0021: bootstrap reconcile + exit-reconcile codes."""
    for name in (
        "HALT_BOOTSTRAP_AMBIGUOUS",
        "HALT_EXIT_RECONCILE_DIVERGENCE",
        "EXIT_RECONCILE_DETECTED",
    ):
        assert hasattr(ReasonCode, name), f"missing {name}"
        assert ReasonCode[name].value == name


def test_new_halt_codes_present() -> None:
    for name in (
        "HALT_BRACKET_INCOMPLETE",
        "HALT_OCO_ARM_TIMEOUT",
        "HALT_OCO_SIBLING_STUCK",
        "HALT_PARTIAL_FILL_BELOW_MIN",
        "HALT_FLATTEN_FAILED",
        "HALT_PHANTOM_SL",
    ):
        assert hasattr(ReasonCode, name), f"missing {name}"


def test_new_exit_and_reject_codes_present() -> None:
    assert hasattr(ReasonCode, "EXIT_STOP_RESIDUAL_FLATTEN")
    assert hasattr(ReasonCode, "REJECT_ORDER_ALREADY_TERMINAL")


def test_new_codes_string_value_matches_name() -> None:
    for name in (
        "HALT_BRACKET_INCOMPLETE",
        "HALT_OCO_ARM_TIMEOUT",
        "HALT_OCO_SIBLING_STUCK",
        "HALT_PARTIAL_FILL_BELOW_MIN",
        "HALT_FLATTEN_FAILED",
        "HALT_PHANTOM_SL",
        "EXIT_STOP_RESIDUAL_FLATTEN",
        "REJECT_ORDER_ALREADY_TERMINAL",
    ):
        assert ReasonCode[name].value == name
