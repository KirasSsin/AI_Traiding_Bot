"""Sprint 40 — 3 new entry/exit reason codes for atr_breakout strategy (ADR 0060)."""

from src.risk.reason_codes import ReasonCode


def test_entry_long_atr_breakout_exists():
    """S40 ADR 0060 — atr_breakout entry signal."""
    assert ReasonCode.ENTRY_LONG_ATR_BREAKOUT.value == "ENTRY_LONG_ATR_BREAKOUT"


def test_exit_flat_atr_reverse_exists():
    """S40 ADR 0060 — opposite ATR breakout exit (reverse breakdown)."""
    assert ReasonCode.EXIT_FLAT_ATR_REVERSE.value == "EXIT_FLAT_ATR_REVERSE"


def test_exit_flat_atr_stop_ab_exists():
    """S40 ADR 0060 — ATR stop intrabar, atr_breakout-specific."""
    assert ReasonCode.EXIT_FLAT_ATR_STOP_AB.value == "EXIT_FLAT_ATR_STOP_AB"


def test_reason_code_total_count_56():
    """S40 ADR 0060 — adds 3 atr_breakout codes (53 → 56).

    Accounting:
    - S39 ADR 0059 baseline: 53
    - S40 ADR 0060 adds: +3 (ENTRY_LONG_ATR_BREAKOUT + EXIT_FLAT_ATR_REVERSE + EXIT_FLAT_ATR_STOP_AB)
    → 56 total
    """
    assert len(list(ReasonCode)) == 56
