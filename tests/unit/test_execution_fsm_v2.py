"""ADR 0020 sub-decision 8 — FSM v2 enum expansion (4 new states + 8 new events)."""
from __future__ import annotations

from src.execution.state_machine import ExecutionEvent, ExecutionState


def test_new_states_present() -> None:
    for name in (
        "OCO_ARMING",
        "EXIT_SIBLING_CANCELLING",
        "EXIT_SIBLING_CANCEL_FAILED",
        "EXIT_SL_RESIDUAL",
    ):
        assert hasattr(ExecutionState, name), f"missing {name}"


def test_new_events_present() -> None:
    for name in (
        "TP_PLACED",
        "SL_PLACED",
        "SL_TRIGGERED",
        "SIBLING_CANCELLED",
        "SIBLING_CANCEL_FAILED",
        "BRACKET_TIMEOUT",
        "RESIDUAL_FLATTENED",
        "FLATTEN_FAILED",
    ):
        assert hasattr(ExecutionEvent, name), f"missing {name}"


def test_state_total_is_16() -> None:
    assert len(list(ExecutionState)) == 16


def test_event_total_is_27() -> None:
    assert len(list(ExecutionEvent)) == 27


def test_legacy_oco_placed_kept_as_alias() -> None:
    assert ExecutionEvent.OCO_PLACED.value == "OCO_PLACED"
