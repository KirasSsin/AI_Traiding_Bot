"""Execution FSM. ADR 0019 sub-decision 2 + ADR 0020 sub-decision 8 (v2 expansion).

States: 12 base + 4 OCO-emulation (16 enum members; 5 conceptual halt-substates
ride on HALTED + halt_reason: ReasonCode per ADR 0020 sub-decision 8).
"""
from __future__ import annotations

from enum import StrEnum


class ExecutionState(StrEnum):
    INIT = "INIT"
    FLAT = "FLAT"
    ENTRY_PENDING = "ENTRY_PENDING"
    LONG_OPEN = "LONG_OPEN"
    OCO_ARMING = "OCO_ARMING"  # ADR 0020 sub-decision 8
    OCO_ARMED = "OCO_ARMED"
    PARTIAL_FILL = "PARTIAL_FILL"  # legacy S5 — unreachable in v2 (PARTIAL_FILL event → EXIT_SL_RESIDUAL); kept for state-load back-compat
    EXIT_PENDING = "EXIT_PENDING"
    EXIT_SIBLING_CANCELLING = "EXIT_SIBLING_CANCELLING"  # ADR 0020 sub-decision 8
    EXIT_SIBLING_CANCEL_FAILED = "EXIT_SIBLING_CANCEL_FAILED"  # ADR 0020 sub-decision 8
    EXIT_SL_RESIDUAL = "EXIT_SL_RESIDUAL"  # ADR 0020 sub-decision 4 (IOC partial)
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
    OCO_PLACED = "OCO_PLACED"  # legacy S5 alias for "both legs Untriggered"
    TP_PLACED = "TP_PLACED"  # ADR 0020 sub-decision 8
    SL_PLACED = "SL_PLACED"  # ADR 0020 sub-decision 8
    PARTIAL_FILL = "PARTIAL_FILL"
    SL_HIT = "SL_HIT"
    SL_TRIGGERED = "SL_TRIGGERED"  # ADR 0020 sub-decision 3 (Triggered != Filled)
    TP_HIT = "TP_HIT"
    SIBLING_CANCELLED = "SIBLING_CANCELLED"  # ADR 0020 sub-decision 8
    SIBLING_CANCEL_FAILED = "SIBLING_CANCEL_FAILED"  # ADR 0020 sub-decision 8
    BRACKET_TIMEOUT = "BRACKET_TIMEOUT"  # ADR 0020 sub-decision 10 (TTL=60s)
    RESIDUAL_FLATTENED = "RESIDUAL_FLATTENED"  # ADR 0020 sub-decision 4
    FLATTEN_FAILED = "FLATTEN_FAILED"  # ADR 0020 sub-decision 11
    EXIT_FILLED = "EXIT_FILLED"
    EXIT_REJECTED = "EXIT_REJECTED"
    WS_RECONNECT = "WS_RECONNECT"
    RECONCILE_OK = "RECONCILE_OK"
    RECONCILE_DIVERGENCE = "RECONCILE_DIVERGENCE"
    RISK_HALT = "RISK_HALT"
    HALT_RESUME = "HALT_RESUME"
    COOLDOWN_DONE = "COOLDOWN_DONE"
    KILL_SWITCH = "KILL_SWITCH"
    KILL_SWITCH_REQUESTED = "KILL_SWITCH_REQUESTED"  # ADR 0022 sub-decision 5 — operator HALT (NOT terminal)
    MANUAL_RESET = "MANUAL_RESET"
    OCO_PARTIAL_TIMEOUT = "OCO_PARTIAL_TIMEOUT"
    # ADR 0021 sub-decision 2: HEAL-narrow + clean-exited reconcile outcomes
    RECONCILE_ENTRY_FILLED = "RECONCILE_ENTRY_FILLED"
    RECONCILE_EXITED = "RECONCILE_EXITED"


class IllegalTransitionError(RuntimeError):
    """Raised when (state, event) is not in TRANSITIONS table."""


TRANSITIONS: dict[tuple[ExecutionState, ExecutionEvent], ExecutionState] = {
    (ExecutionState.INIT, ExecutionEvent.STATE_LOADED): ExecutionState.FLAT,
    (ExecutionState.FLAT, ExecutionEvent.ENTRY_PLACED): ExecutionState.ENTRY_PENDING,
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.ENTRY_FILLED): ExecutionState.LONG_OPEN,
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.ENTRY_REJECTED): ExecutionState.FLAT,
    (ExecutionState.LONG_OPEN, ExecutionEvent.OCO_PLACED): ExecutionState.OCO_ARMED,
    # NOTE: (OCO_ARMED, PARTIAL_FILL) and (OCO_ARMED, TP_HIT) handled by S6
    # OVERRIDE block below (route through bracket-aware paths). Removed here
    # to eliminate duplicate dict-key shadows (silent overrides → ruff F601).
    (ExecutionState.OCO_ARMED, ExecutionEvent.SL_HIT): ExecutionState.EXIT_PENDING,
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
    # === ADR 0020 sub-decision 8: OCO emulation transitions (v2) ===
    # Bracket arm path: entry filled → place TP → place SL → armed
    (ExecutionState.LONG_OPEN, ExecutionEvent.TP_PLACED): ExecutionState.OCO_ARMING,
    (ExecutionState.OCO_ARMING, ExecutionEvent.SL_PLACED): ExecutionState.OCO_ARMED,
    (ExecutionState.OCO_ARMING, ExecutionEvent.BRACKET_TIMEOUT): ExecutionState.HALTED,
    (ExecutionState.OCO_ARMING, ExecutionEvent.ENTRY_REJECTED): ExecutionState.HALTED,
    (ExecutionState.OCO_ARMING, ExecutionEvent.PARTIAL_FILL): ExecutionState.HALTED,
    (ExecutionState.OCO_ARMING, ExecutionEvent.SL_TRIGGERED): ExecutionState.HALTED,
    # Sibling cancel path: TP fill or SL trigger → cancel sibling → FLAT
    (ExecutionState.OCO_ARMED, ExecutionEvent.SL_TRIGGERED): ExecutionState.EXIT_SIBLING_CANCELLING,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.SIBLING_CANCELLED): ExecutionState.FLAT,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.SIBLING_CANCEL_FAILED): ExecutionState.EXIT_SIBLING_CANCEL_FAILED,
    (ExecutionState.EXIT_SIBLING_CANCEL_FAILED, ExecutionEvent.SIBLING_CANCELLED): ExecutionState.FLAT,
    (ExecutionState.EXIT_SIBLING_CANCEL_FAILED, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.EXIT_SIBLING_CANCEL_FAILED, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.EXIT_SIBLING_CANCEL_FAILED, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    # OVERRIDE legacy S5: TP_HIT/PARTIAL_FILL now route through bracket-aware paths
    (ExecutionState.OCO_ARMED, ExecutionEvent.TP_HIT): ExecutionState.EXIT_SIBLING_CANCELLING,
    (ExecutionState.OCO_ARMED, ExecutionEvent.PARTIAL_FILL): ExecutionState.EXIT_SL_RESIDUAL,
    # IOC residual path
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.RESIDUAL_FLATTENED): ExecutionState.FLAT,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.FLATTEN_FAILED): ExecutionState.HALTED,
    # Flatten cascade from EXIT_PENDING (sub-decision 11)
    (ExecutionState.EXIT_PENDING, ExecutionEvent.FLATTEN_FAILED): ExecutionState.HALTED,
    # Flatten cascade from OCO_ARMED (sub-decision 10): emergency flatten on
    # reconcile divergence / risk halt invoked while bracket is armed.
    (ExecutionState.OCO_ARMED, ExecutionEvent.FLATTEN_FAILED): ExecutionState.HALTED,
    # WS reconnect from new states
    (ExecutionState.OCO_ARMING, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    # Risk halt + kill switch from new states
    (ExecutionState.OCO_ARMING, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    # === ADR 0022 sub-decision 6 fix-up (S8b T1): RISK_HALT from pending/reconciling states ===
    # Symmetric with KILL_SWITCH_REQUESTED rows for same source states (lines 144/148/153).
    # Absent rows caused RuntimeManager.run() except-handler to raise IllegalTransitionError,
    # propagating out of except, leaving DB split-brain.
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.EXIT_PENDING, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.RECONCILING, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.OCO_ARMING, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    # === ADR 0021 sub-decision 2: S7 resilience — WS-reconnect wiring + HEAL paths ===
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.EXIT_PENDING, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_ENTRY_FILLED): ExecutionState.LONG_OPEN,
    (ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_EXITED): ExecutionState.FLAT,
    # === ADR 0022 sub-decision 5: KILL_SWITCH_REQUESTED — operator HALT (NOT terminal) ===
    (ExecutionState.FLAT, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.LONG_OPEN, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.OCO_ARMING, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.OCO_ARMED, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.EXIT_PENDING, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.EXIT_SIBLING_CANCEL_FAILED, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.RECONCILING, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
}


def apply(state: ExecutionState, event: ExecutionEvent) -> ExecutionState:
    """Apply event to state. Raise IllegalTransitionError if not in table."""
    try:
        return TRANSITIONS[(state, event)]
    except KeyError as e:
        raise IllegalTransitionError(f"{state} + {event} not allowed") from e
