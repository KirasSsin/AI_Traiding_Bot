"""S7 FSM additions (ADR 0021 sub-decision 2)."""
from __future__ import annotations

import pytest

from src.execution.state_machine import (
    ExecutionEvent,
    ExecutionState,
    IllegalTransitionError,
    apply,
)


# --- Task 4: event enum additions ---


def test_reconcile_entry_filled_event_exists() -> None:
    assert ExecutionEvent.RECONCILE_ENTRY_FILLED.name == "RECONCILE_ENTRY_FILLED"


def test_reconcile_exited_event_exists() -> None:
    assert ExecutionEvent.RECONCILE_EXITED.name == "RECONCILE_EXITED"


# --- Task 5: ENTRY_PENDING + WS_RECONNECT -> RECONCILING ---


def test_entry_pending_ws_reconnect_goes_to_reconciling() -> None:
    """ADR 0021 sub-dec 2 — bootstrap/reconnect from transient entry state."""
    result = apply(ExecutionState.ENTRY_PENDING, ExecutionEvent.WS_RECONNECT)
    assert result is ExecutionState.RECONCILING


# --- Task 6: EXIT_PENDING + WS_RECONNECT -> RECONCILING ---


def test_exit_pending_ws_reconnect_goes_to_reconciling() -> None:
    """ADR 0021 sub-dec 2 — reconnect during exit flow."""
    result = apply(ExecutionState.EXIT_PENDING, ExecutionEvent.WS_RECONNECT)
    assert result is ExecutionState.RECONCILING


# --- Task 7: RECONCILING + RECONCILE_ENTRY_FILLED -> LONG_OPEN (HEAL-narrow) ---


def test_reconciling_heal_entry_filled_goes_to_long_open() -> None:
    """ADR 0021: HEAL-narrow — coordinator later calls arm_oco from LONG_OPEN."""
    result = apply(ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_ENTRY_FILLED)
    assert result is ExecutionState.LONG_OPEN


# --- Task 8: RECONCILING + RECONCILE_EXITED -> FLAT + illegal guards ---


def test_reconciling_reconcile_exited_goes_to_flat() -> None:
    """ADR 0021: clean fill-during-disconnect — position==0 on exchange -> FLAT."""
    result = apply(ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_EXITED)
    assert result is ExecutionState.FLAT


def test_illegal_reconcile_entry_filled_from_flat() -> None:
    """New events legal ONLY from RECONCILING."""
    with pytest.raises(IllegalTransitionError):
        apply(ExecutionState.FLAT, ExecutionEvent.RECONCILE_ENTRY_FILLED)


def test_illegal_reconcile_exited_from_long_open() -> None:
    """RECONCILE_EXITED from LONG_OPEN is illegal (must go via RECONCILING)."""
    with pytest.raises(IllegalTransitionError):
        apply(ExecutionState.LONG_OPEN, ExecutionEvent.RECONCILE_EXITED)
