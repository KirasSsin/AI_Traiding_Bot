"""FSM — KILL_SWITCH_REQUESTED event from active states → HALTED.

ADR 0022 sub-decision 5. Distinct from S7 KILL_SWITCH (→ KILLED terminal).
"""
import pytest
from src.execution.state_machine import (
    ExecutionEvent,
    ExecutionState,
    IllegalTransitionError,
    apply,
)


@pytest.mark.parametrize(
    "src_state",
    [
        ExecutionState.FLAT,
        ExecutionState.ENTRY_PENDING,
        ExecutionState.LONG_OPEN,
        ExecutionState.OCO_ARMING,
        ExecutionState.OCO_ARMED,
        ExecutionState.EXIT_PENDING,
        ExecutionState.EXIT_SIBLING_CANCELLING,
        ExecutionState.EXIT_SIBLING_CANCEL_FAILED,
        ExecutionState.EXIT_SL_RESIDUAL,
        ExecutionState.PARTIAL_FILL,
        ExecutionState.RECONCILING,
    ],
)
def test_kill_switch_requested_transitions_to_halted(src_state):
    assert apply(src_state, ExecutionEvent.KILL_SWITCH_REQUESTED) == ExecutionState.HALTED


def test_kill_switch_requested_illegal_from_killed():
    """Already-killed state cannot be halted again."""
    with pytest.raises(IllegalTransitionError):
        apply(ExecutionState.KILLED, ExecutionEvent.KILL_SWITCH_REQUESTED)


def test_kill_switch_requested_illegal_from_halted():
    """No self-loop on HALTED — explicit design decision (avoids masking primary halt_reason).

    Idempotency must be enforced at the caller (Coordinator.request_halt should check
    state == HALTED before invoking _set_halt). FSM rejects redundant halt as illegal.
    """
    with pytest.raises(IllegalTransitionError):
        apply(ExecutionState.HALTED, ExecutionEvent.KILL_SWITCH_REQUESTED)


def test_legacy_kill_switch_still_terminal():
    """S7 KILL_SWITCH → KILLED preserved (back-compat regression check)."""
    assert apply(ExecutionState.LONG_OPEN, ExecutionEvent.KILL_SWITCH) == ExecutionState.KILLED
