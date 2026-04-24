"""Sprint 8a — 3 new halt reason codes (ADR 0022 sub-decision 12)."""
from src.risk.reason_codes import ReasonCode


def test_reason_code_halt_runtime_crash_exists():
    assert ReasonCode.HALT_RUNTIME_CRASH.value == "HALT_RUNTIME_CRASH"


def test_reason_code_halt_bar_poll_stall_exists():
    assert ReasonCode.HALT_BAR_POLL_STALL.value == "HALT_BAR_POLL_STALL"


def test_reason_code_kill_switch_requested_exists():
    assert ReasonCode.KILL_SWITCH_REQUESTED.value == "KILL_SWITCH_REQUESTED"


def test_reason_code_total_count_45():
    """ADR 0021 baseline = 42; ADR 0022 adds 3 → 45 total."""
    assert len(list(ReasonCode)) == 45
