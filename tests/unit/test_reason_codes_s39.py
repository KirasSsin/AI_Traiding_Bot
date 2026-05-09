"""Sprint 39 — 3 new entry/exit reason codes for volume_breakout strategy (ADR 0059)."""

from src.risk.reason_codes import ReasonCode


def test_entry_long_volume_breakout_exists():
    """S39 ADR 0059 — volume_breakout entry signal."""
    assert ReasonCode.ENTRY_LONG_VOLUME_BREAKOUT.value == "ENTRY_LONG_VOLUME_BREAKOUT"


def test_exit_flat_volume_channel_exists():
    """S39 ADR 0059 — Donchian channel exit (volume_breakout)."""
    assert ReasonCode.EXIT_FLAT_VOLUME_CHANNEL.value == "EXIT_FLAT_VOLUME_CHANNEL"


def test_exit_flat_atr_stop_vb_exists():
    """S39 ADR 0059 — ATR stop intrabar, volume_breakout-specific."""
    assert ReasonCode.EXIT_FLAT_ATR_STOP_VB.value == "EXIT_FLAT_ATR_STOP_VB"


def test_reason_code_total_count_53():
    """S39 ADR 0059 — adds 3 volume_breakout codes (50 → 53).

    Accounting:
    - S37 ADR 0057 baseline: 50 (HALT_UNKNOWN_SYMBOL)
    - S39 ADR 0059 adds: +3 (ENTRY_LONG_VOLUME_BREAKOUT + EXIT_FLAT_VOLUME_CHANNEL + EXIT_FLAT_ATR_STOP_VB)
    → 53 total
    """
    assert len(list(ReasonCode)) == 53
