"""S47 T9 — bybit retCode taxonomy classification tests (M1 finding).

Verifies that codes 10001/110001/170131 resolve to meaningful ReasonCode
categories instead of UNKNOWN_ERROR (bybit-api-reviewer S38 M1 finding).

Adapter note: 110001 is intentionally kept as REJECT_ORDER_ALREADY_TERMINAL
(not ORDER_NOT_FOUND) because adapter.py line 213 pins this exact identity
check for non-fatal cancel-of-filled-order logic.
"""

from __future__ import annotations

import pytest
from src.execution.bybit.errors import ReasonCode, map_error


@pytest.mark.parametrize(
    "code,expected",
    [
        # S47 T9 new entries — were UNKNOWN_ERROR before this fix
        (10001, ReasonCode.INVALID_PARAM),
        # 110001 already mapped; adapter pins REJECT_ORDER_ALREADY_TERMINAL
        (110001, ReasonCode.REJECT_ORDER_ALREADY_TERMINAL),
        # 170131 already mapped to FILTER_VIOLATION (kept, consistent with S38 original mapping)
        (170131, ReasonCode.FILTER_VIOLATION),
        # Unknown code must still fall through to UNKNOWN_ERROR
        (999999, ReasonCode.UNKNOWN_ERROR),
    ],
)
def test_s47_t9_retcode_taxonomy(code: int, expected: ReasonCode) -> None:
    """All three M1 codes resolve to a meaningful category (not UNKNOWN_ERROR)."""
    result = map_error(code)
    assert result is expected


def test_invalid_param_in_enum() -> None:
    """INVALID_PARAM member present в ReasonCode enum после S47 T9 extension."""
    assert "INVALID_PARAM" in {r.value for r in ReasonCode}


def test_no_unknown_error_for_10001() -> None:
    """10001 was the primary M1 gap — confirm it no longer returns UNKNOWN_ERROR."""
    assert map_error(10001) is not ReasonCode.UNKNOWN_ERROR
