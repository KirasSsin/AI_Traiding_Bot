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


from src.execution.state_machine import TRANSITIONS, apply


def test_transitions_count_exact_v2() -> None:
    # S5 had 29; ADR 0020 sub-decision 8 adds 25 net new unique keys
    # (27 entries minus 2 override-existing keys → 29+25=54). Sub-decision 10
    # (Task 22) adds (OCO_ARMED, FLATTEN_FAILED) → HALTED → 55.
    assert len(TRANSITIONS) == 55


def test_exit_sibling_cancel_failed_has_ws_reconnect_and_kill() -> None:
    # Reviewer concern: retry-island state must support WS reconnect + kill.
    assert apply(ExecutionState.EXIT_SIBLING_CANCEL_FAILED, ExecutionEvent.WS_RECONNECT) == ExecutionState.RECONCILING
    assert apply(ExecutionState.EXIT_SIBLING_CANCEL_FAILED, ExecutionEvent.KILL_SWITCH) == ExecutionState.KILLED


def test_long_open_to_oco_arming_on_tp_placed() -> None:
    assert apply(ExecutionState.LONG_OPEN, ExecutionEvent.TP_PLACED) == ExecutionState.OCO_ARMING


def test_oco_arming_to_oco_armed_on_sl_placed() -> None:
    assert apply(ExecutionState.OCO_ARMING, ExecutionEvent.SL_PLACED) == ExecutionState.OCO_ARMED


def test_oco_armed_to_sibling_cancelling_on_tp_hit() -> None:
    assert apply(ExecutionState.OCO_ARMED, ExecutionEvent.TP_HIT) == ExecutionState.EXIT_SIBLING_CANCELLING


def test_oco_armed_to_sibling_cancelling_on_sl_triggered() -> None:
    assert apply(ExecutionState.OCO_ARMED, ExecutionEvent.SL_TRIGGERED) == ExecutionState.EXIT_SIBLING_CANCELLING


def test_sibling_cancelling_to_flat_on_success() -> None:
    assert apply(ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.SIBLING_CANCELLED) == ExecutionState.FLAT


def test_oco_armed_to_sl_residual_on_partial_fill() -> None:
    assert apply(ExecutionState.OCO_ARMED, ExecutionEvent.PARTIAL_FILL) == ExecutionState.EXIT_SL_RESIDUAL


def test_sl_residual_to_flat_on_residual_flattened() -> None:
    assert apply(ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.RESIDUAL_FLATTENED) == ExecutionState.FLAT


def test_oco_arming_to_halted_on_bracket_timeout() -> None:
    assert apply(ExecutionState.OCO_ARMING, ExecutionEvent.BRACKET_TIMEOUT) == ExecutionState.HALTED


def test_exit_pending_to_halted_on_flatten_failed() -> None:
    assert apply(ExecutionState.EXIT_PENDING, ExecutionEvent.FLATTEN_FAILED) == ExecutionState.HALTED
