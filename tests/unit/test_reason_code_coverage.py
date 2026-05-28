"""Blanket coverage sweep over every ReasonCode member (S49 M8b).

test-engineer audit found only a subset of the 63 ReasonCode members asserted in
the suite. This parametrized sweep guarantees each member is reachable and has a
well-formed value, so future ADR amendments that add a code without a dedicated
test are still touched here (cheap regression net against the
RiskManager.assess() generic-fallback class of bugs — see ADR 0023 amendment / H6).
"""

from __future__ import annotations

import pytest
from src.risk.reason_codes import ReasonCode

ALL_CODES = list(ReasonCode)


def test_reason_code_enum_non_empty() -> None:
    assert len(ALL_CODES) >= 63  # 63 after S49 ADR 0023 amendment (H6)


@pytest.mark.parametrize("code", ALL_CODES, ids=[c.name for c in ALL_CODES])
def test_reason_code_value_well_formed(code: ReasonCode) -> None:
    """Each member: StrEnum, value == name, non-empty UPPER_SNAKE string."""
    assert isinstance(code, ReasonCode)
    assert isinstance(code.value, str)
    assert code.value, f"{code.name} has empty value"
    # Canonical convention: the value string equals the member name.
    assert code.value == code.name
    # UPPER_SNAKE_CASE (letters, digits, underscores; no lowercase).
    assert code.value == code.value.upper()
    assert all(ch.isalnum() or ch == "_" for ch in code.value)


@pytest.mark.parametrize("code", ALL_CODES, ids=[c.name for c in ALL_CODES])
def test_reason_code_round_trips_from_value(code: ReasonCode) -> None:
    """ReasonCode(value) reconstructs the same member (audit-log read path)."""
    assert ReasonCode(code.value) is code
    assert ReasonCode(str(code)) is code


def test_reason_code_values_are_unique() -> None:
    values = [c.value for c in ALL_CODES]
    assert len(set(values)) == len(values)


@pytest.mark.parametrize("code", ALL_CODES, ids=[c.name for c in ALL_CODES])
def test_reason_code_category_prefix_known(code: ReasonCode) -> None:
    """Each code maps to a known audit category by its leading prefix.

    Categories per reason-codes-schema: entry / scale / exit / reject / halt
    (plus the kill-switch sentinel). A code that drifts outside these prefixes
    would silently escape category aggregation in the audit log.
    """
    known_prefixes = (
        "ENTRY_",
        "SCALE_",
        "EXIT_",
        "REJECT_",
        "HALT_",
        "KILL_SWITCH",
    )
    assert code.value.startswith(known_prefixes), f"{code.name} has no known category prefix"
