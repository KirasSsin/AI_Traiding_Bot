"""Tests for ReasonCode enum extensions (Sprint 5 Task 1).

ADR ref: wiki/project/decisions/0019-sprint-5-execution-decisions.md sub-decision 4
"""

from src.risk.reason_codes import ReasonCode


def test_halt_reconcile_divergence_in_enum():
    assert ReasonCode.HALT_RECONCILE_DIVERGENCE.value == "HALT_RECONCILE_DIVERGENCE"


def test_exit_oco_partial_timeout_in_enum():
    assert ReasonCode.EXIT_OCO_PARTIAL_TIMEOUT.value == "EXIT_OCO_PARTIAL_TIMEOUT"


def test_total_reason_codes_count():
    assert len(ReasonCode) == 39  # was 31 → +8 in S6


def test_v2_count_is_39() -> None:
    assert len(list(ReasonCode)) == 39


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
