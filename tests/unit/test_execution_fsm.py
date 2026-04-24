# tests/unit/test_execution_fsm.py
import pytest
from src.execution.state_machine import (
    ExecutionState, ExecutionEvent, apply, IllegalTransitionError, TRANSITIONS,
)

LEGAL = [
    (ExecutionState.INIT, ExecutionEvent.STATE_LOADED, ExecutionState.FLAT),
    (ExecutionState.FLAT, ExecutionEvent.ENTRY_PLACED, ExecutionState.ENTRY_PENDING),
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.ENTRY_FILLED, ExecutionState.LONG_OPEN),
    (ExecutionState.LONG_OPEN, ExecutionEvent.OCO_PLACED, ExecutionState.OCO_ARMED),
    # ADR 0020 sub-decision 8 — semantic override: see test_execution_fsm_v2.py
    (ExecutionState.OCO_ARMED, ExecutionEvent.PARTIAL_FILL, ExecutionState.EXIT_SL_RESIDUAL),  # ADR 0020 sub-decision 8 override
    (ExecutionState.OCO_ARMED, ExecutionEvent.SL_HIT, ExecutionState.EXIT_PENDING),
    # ADR 0020 sub-decision 8 — semantic override: see test_execution_fsm_v2.py
    (ExecutionState.OCO_ARMED, ExecutionEvent.TP_HIT, ExecutionState.EXIT_SIBLING_CANCELLING),  # ADR 0020 sub-decision 8 override
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.SL_HIT, ExecutionState.EXIT_PENDING),
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.TP_HIT, ExecutionState.EXIT_PENDING),
    (ExecutionState.EXIT_PENDING, ExecutionEvent.EXIT_FILLED, ExecutionState.FLAT),
    (ExecutionState.OCO_ARMED, ExecutionEvent.WS_RECONNECT, ExecutionState.RECONCILING),
    (ExecutionState.LONG_OPEN, ExecutionEvent.WS_RECONNECT, ExecutionState.RECONCILING),
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.WS_RECONNECT, ExecutionState.RECONCILING),
    (ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_OK, ExecutionState.OCO_ARMED),
    (ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_DIVERGENCE, ExecutionState.HALTED),
    (ExecutionState.OCO_ARMED, ExecutionEvent.RISK_HALT, ExecutionState.HALTED),
    (ExecutionState.LONG_OPEN, ExecutionEvent.RISK_HALT, ExecutionState.HALTED),
    (ExecutionState.HALTED, ExecutionEvent.HALT_RESUME, ExecutionState.COOLDOWN),
    (ExecutionState.COOLDOWN, ExecutionEvent.COOLDOWN_DONE, ExecutionState.FLAT),
    (ExecutionState.FLAT, ExecutionEvent.KILL_SWITCH, ExecutionState.KILLED),
    (ExecutionState.LONG_OPEN, ExecutionEvent.KILL_SWITCH, ExecutionState.KILLED),
    (ExecutionState.OCO_ARMED, ExecutionEvent.KILL_SWITCH, ExecutionState.KILLED),
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.KILL_SWITCH, ExecutionState.KILLED),
    (ExecutionState.HALTED, ExecutionEvent.KILL_SWITCH, ExecutionState.KILLED),
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.ENTRY_REJECTED, ExecutionState.FLAT),
    (ExecutionState.EXIT_PENDING, ExecutionEvent.EXIT_REJECTED, ExecutionState.ERROR),
    (ExecutionState.ERROR, ExecutionEvent.MANUAL_RESET, ExecutionState.FLAT),
    (ExecutionState.OCO_ARMED, ExecutionEvent.OCO_PARTIAL_TIMEOUT, ExecutionState.EXIT_PENDING),
]

@pytest.mark.parametrize("src,event,dst", LEGAL)
def test_legal_transition(src, event, dst):
    assert apply(src, event) == dst

def test_illegal_transition_raises():
    with pytest.raises(IllegalTransitionError):
        apply(ExecutionState.FLAT, ExecutionEvent.SL_HIT)

def test_kill_terminal():
    with pytest.raises(IllegalTransitionError):
        apply(ExecutionState.KILLED, ExecutionEvent.STATE_LOADED)

def test_transitions_count_exact():
    """Lock the exact transition count. Adding/removing requires ADR update."""
    assert len(TRANSITIONS) == 73  # +11 KILL_SWITCH_REQUESTED (ADR 0022) +3 RISK_HALT for ENTRY_PENDING/EXIT_PENDING/RECONCILING (S8b T1 fix-up; future ADR 0023)
