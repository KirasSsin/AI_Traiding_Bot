"""Tests for S50 T4 Supertrend reason codes (63 -> 65 per ADR 0067)."""

from src.risk.reason_codes import ReasonCode


def test_supertrend_entry_code_exists() -> None:
    assert ReasonCode.ENTRY_LONG_SUPERTREND.value == "ENTRY_LONG_SUPERTREND"


def test_supertrend_exit_code_exists() -> None:
    assert ReasonCode.EXIT_FLAT_SUPERTREND_FLIP.value == "EXIT_FLAT_SUPERTREND_FLIP"


def test_total_reason_code_count_is_65() -> None:
    assert len(list(ReasonCode)) == 65


def test_no_duplicate_reason_code_values() -> None:
    values = [code.value for code in ReasonCode]
    assert len(values) == len(set(values))
