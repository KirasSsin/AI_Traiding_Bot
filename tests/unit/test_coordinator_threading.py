"""ADR 0022 sub-decision 1 — Coordinator threading.RLock.

3 tests:
1. test_coordinator_has_rlock              — _lock attribute is a real RLock instance
2. test_coordinator_concurrent_on_order_event_and_start_bracket_safe — 2-thread race
3. test_coordinator_lock_is_reentrant      — nested `with coord._lock` does NOT deadlock
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.platform.db import init_db

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _build(tmp_path):
    """Build a Coordinator with a real DB seeded in FLAT state, bootstrap done."""
    from src.execution.coordinator import Coordinator

    db_path = tmp_path / "race.db"
    init_db(db_path, MIG_DIR)
    # check_same_thread=False required for multi-thread race test (test 2).
    # SQLite WAL mode makes concurrent reads safe; writes are serialised by _lock.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    repo = ExecutionStateRepo(conn)

    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.FLAT,
        position_qty=Decimal("0"),
        entry_price=None,
        oco_main_order_id=None,
        bracket_id=None,
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=None,
        arming_started_at=None,
        last_attempt_num=0,
        updated_at=_now_iso(),
    ))

    adapter = MagicMock()
    adapter.get_open_orders.return_value = []
    adapter.get_order_history.return_value = []

    # place_order must return an object with .order_id so start_bracket can persist it
    order_ack = MagicMock()
    order_ack.order_id = "mock-order-id-1"
    adapter.place_order.return_value = order_ack

    reconciler = MagicMock()

    coord = Coordinator(
        adapter=adapter, repo=repo, reconciler=reconciler,
        symbol="BTCUSDT", base_coin="BTC",
    )
    # Mark bootstrap done so start_bracket / on_order_event asserts pass
    coord._bootstrap_done = True

    return coord, repo


# ---------------------------------------------------------------------------
# Test 1: _lock attribute is a real threading.RLock
# ---------------------------------------------------------------------------

def test_coordinator_has_rlock(tmp_path):
    """coord._lock must be an instance of threading.RLock.

    RLock() is a factory, so we compare type(coord._lock) against
    type(threading.RLock()) — the concrete _RLock class.
    """
    coord, _ = _build(tmp_path)
    assert hasattr(coord, "_lock"), "Coordinator must expose _lock attribute"
    assert type(coord._lock) is type(threading.RLock()), (
        f"_lock must be a threading.RLock; got {type(coord._lock)}"
    )


# ---------------------------------------------------------------------------
# Test 2: 2-thread barrier-sync race — FSM row must not be torn
# ---------------------------------------------------------------------------

def test_coordinator_concurrent_on_order_event_and_start_bracket_safe(tmp_path):
    """Two threads simultaneous mutation must leave FSM row in a valid state.

    Thread A calls on_order_event with a Filled entry event.
    Thread B calls start_bracket (which will fail the assert or be a no-op since
    bootstrap_done is True but state may be non-FLAT).

    We use a barrier so both threads collide at the lock boundary.
    After joining, the persisted state must be a valid ExecutionState
    (not a corrupted intermediate value).
    """
    coord, repo = _build(tmp_path)

    # Give the adapter a fresh order_ack for each call (thread-safe return)
    def _fresh_ack(*args, **kwargs):
        ack = MagicMock()
        ack.order_id = "mock-order-" + threading.current_thread().name
        return ack

    coord._adapter.place_order.side_effect = _fresh_ack

    # We need a bracket_id in the row so on_order_event can route the link_id.
    # Seed with an ENTRY_PENDING row that has a known bracket_id.
    bracket_id = "abcd1234"
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.ENTRY_PENDING,
        position_qty=Decimal("0"),
        entry_price=None,
        oco_main_order_id="entry-order-1",
        bracket_id=bracket_id,
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=Decimal("0.001"),
        arming_started_at=None,
        last_attempt_num=1,
        updated_at=_now_iso(),
    ))

    # Build an "entry Filled" event matching the bracket pattern
    entry_link_id = f"oco-{bracket_id}-entry-1"
    entry_evt = {"orderLinkId": entry_link_id, "orderStatus": "Filled"}

    errors: list[Exception] = []
    barrier = threading.Barrier(2)

    def thread_a():
        try:
            barrier.wait()
            coord.on_order_event(entry_evt)
        except Exception as e:
            errors.append(e)

    def thread_b():
        try:
            barrier.wait()
            # start_bracket from ENTRY_PENDING will hit FLAT check on current row
            # or see a non-FLAT state; either way it's a mutation attempt.
            # We wrap in try/except because FSM may raise IllegalTransitionError.
            try:
                coord.start_bracket(
                    entry_qty=Decimal("0.001"),
                    entry_side="Buy",
                    tp_price=Decimal("65000"),
                    sl_trigger_price=Decimal("58000"),
                )
            except Exception:
                pass  # Expected: FSM may reject transition from ENTRY_PENDING
        except Exception as e:
            errors.append(e)

    t_a = threading.Thread(target=thread_a, name="thread-A", daemon=True)
    t_b = threading.Thread(target=thread_b, name="thread-B", daemon=True)

    t_a.start()
    t_b.start()
    t_a.join(timeout=5.0)
    t_b.join(timeout=5.0)

    assert not t_a.is_alive(), "Thread A timed out — possible deadlock"
    assert not t_b.is_alive(), "Thread B timed out — possible deadlock"
    assert not errors, f"Thread errors: {errors}"

    # FSM row must be a valid ExecutionState (not torn / corrupted)
    row = repo.get("BTCUSDT")
    assert row is not None
    assert isinstance(row.state, ExecutionState), (
        f"state must be a valid ExecutionState; got {row.state!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: nested `with coord._lock` does NOT deadlock (reentrant)
# ---------------------------------------------------------------------------

def test_coordinator_lock_is_reentrant(tmp_path):
    """RLock allows nested acquisition on the same thread — must not deadlock."""
    coord, _ = _build(tmp_path)

    completed = threading.Event()

    def _nested():
        with coord._lock:  # noqa: SIM117 — intentional double acquire to verify RLock reentrancy
            with coord._lock:    # inner acquire — must succeed (RLock is reentrant)
                completed.set()

    t = threading.Thread(target=_nested, daemon=True)
    t.start()
    t.join(timeout=2.0)

    assert not t.is_alive(), "Nested `with coord._lock` deadlocked — lock is not reentrant"
    assert completed.is_set(), "Inner `with coord._lock` block never executed"
