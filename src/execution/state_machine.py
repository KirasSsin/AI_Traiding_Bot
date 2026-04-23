"""12-state execution FSM. ADR 0019 sub-decision 2."""
from __future__ import annotations

from enum import StrEnum


class ExecutionState(StrEnum):
    INIT = "INIT"
    FLAT = "FLAT"
    ENTRY_PENDING = "ENTRY_PENDING"
    LONG_OPEN = "LONG_OPEN"
    OCO_ARMED = "OCO_ARMED"
    PARTIAL_FILL = "PARTIAL_FILL"
    EXIT_PENDING = "EXIT_PENDING"
    RECONCILING = "RECONCILING"
    HALTED = "HALTED"
    COOLDOWN = "COOLDOWN"
    ERROR = "ERROR"
    KILLED = "KILLED"


class ExecutionEvent(StrEnum):
    STATE_LOADED = "STATE_LOADED"
    ENTRY_PLACED = "ENTRY_PLACED"
    ENTRY_FILLED = "ENTRY_FILLED"
    ENTRY_REJECTED = "ENTRY_REJECTED"
    OCO_PLACED = "OCO_PLACED"
    PARTIAL_FILL = "PARTIAL_FILL"
    SL_HIT = "SL_HIT"
    TP_HIT = "TP_HIT"
    EXIT_FILLED = "EXIT_FILLED"
    EXIT_REJECTED = "EXIT_REJECTED"
    WS_RECONNECT = "WS_RECONNECT"
    RECONCILE_OK = "RECONCILE_OK"
    RECONCILE_DIVERGENCE = "RECONCILE_DIVERGENCE"
    RISK_HALT = "RISK_HALT"
    HALT_RESUME = "HALT_RESUME"
    COOLDOWN_DONE = "COOLDOWN_DONE"
    KILL_SWITCH = "KILL_SWITCH"
    MANUAL_RESET = "MANUAL_RESET"
    OCO_PARTIAL_TIMEOUT = "OCO_PARTIAL_TIMEOUT"


class IllegalTransitionError(RuntimeError):
    """Raised when (state, event) is not in TRANSITIONS table."""


TRANSITIONS: dict[tuple[ExecutionState, ExecutionEvent], ExecutionState] = {
    (ExecutionState.INIT, ExecutionEvent.STATE_LOADED): ExecutionState.FLAT,
    (ExecutionState.FLAT, ExecutionEvent.ENTRY_PLACED): ExecutionState.ENTRY_PENDING,
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.ENTRY_FILLED): ExecutionState.LONG_OPEN,
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.ENTRY_REJECTED): ExecutionState.FLAT,
    (ExecutionState.LONG_OPEN, ExecutionEvent.OCO_PLACED): ExecutionState.OCO_ARMED,
    (ExecutionState.OCO_ARMED, ExecutionEvent.PARTIAL_FILL): ExecutionState.PARTIAL_FILL,
    (ExecutionState.OCO_ARMED, ExecutionEvent.SL_HIT): ExecutionState.EXIT_PENDING,
    (ExecutionState.OCO_ARMED, ExecutionEvent.TP_HIT): ExecutionState.EXIT_PENDING,
    (ExecutionState.OCO_ARMED, ExecutionEvent.OCO_PARTIAL_TIMEOUT): ExecutionState.EXIT_PENDING,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.SL_HIT): ExecutionState.EXIT_PENDING,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.TP_HIT): ExecutionState.EXIT_PENDING,
    (ExecutionState.EXIT_PENDING, ExecutionEvent.EXIT_FILLED): ExecutionState.FLAT,
    (ExecutionState.EXIT_PENDING, ExecutionEvent.EXIT_REJECTED): ExecutionState.ERROR,
    (ExecutionState.OCO_ARMED, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.LONG_OPEN, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_OK): ExecutionState.OCO_ARMED,
    (ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_DIVERGENCE): ExecutionState.HALTED,
    (ExecutionState.OCO_ARMED, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.LONG_OPEN, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.HALTED, ExecutionEvent.HALT_RESUME): ExecutionState.COOLDOWN,
    (ExecutionState.COOLDOWN, ExecutionEvent.COOLDOWN_DONE): ExecutionState.FLAT,
    (ExecutionState.FLAT, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.LONG_OPEN, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.OCO_ARMED, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.HALTED, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.ERROR, ExecutionEvent.MANUAL_RESET): ExecutionState.FLAT,
}


def apply(state: ExecutionState, event: ExecutionEvent) -> ExecutionState:
    """Apply event to state. Raise IllegalTransitionError if not in table."""
    try:
        return TRANSITIONS[(state, event)]
    except KeyError as e:
        raise IllegalTransitionError(f"{state} + {event} not allowed") from e
