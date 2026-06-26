"""S55 PHASE 6 ARCH-02-REG-01 — bootstrap must release the RLock across REST I/O.

THE REGRESSION (adversarially confirmed on HEAD):
S55 ARCH-02 hoisted reconcile's blocking REST fetches OUTSIDE the Coordinator
RLock in ``on_ws_reconnect`` (3-window pattern). BUT ``bootstrap`` wrapped its
WHOLE body — ``_recover_attempt_num`` (get_open_orders + get_order_history) AND
``on_ws_reconnect`` — inside ONE outer ``with self._lock:``. The RLock is
REENTRANT, so on_ws_reconnect's window-2 release does NOT actually release the
lock while bootstrap still holds the outer acquisition. Net: on the warm-start /
crash-recovery path (the highest-risk path), the RLock is held across BOTH
blocking REST sections — the exact lock-hold-across-REST-I/O hazard ARCH-02 set
out to remove. A pybit WS thread that fires during bootstrap's REST fetch blocks
for seconds (orphan-TP-self-fill → phantom-short risk).

FIX: bootstrap runs its blocking REST I/O with the RLock RELEASED, locking only
the narrow non-I/O mutations. These tests assert:
  1. The Coordinator RLock is FREE (acquirable by another thread) while
     bootstrap's _recover_attempt_num REST fetch is in flight.
  2. Existing behavior preserved: bootstrap still sets _bootstrap_done, still
     applies the reconcile verdict, cold-start still noops.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from src.execution.bybit.adapter import OrderSnapshot, WalletSnapshot
from src.execution.reconciler import Reconciler
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.platform.db import init_db

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_repo(tmp_path):
    db_path = tmp_path / "bootstrap_hoist.db"
    init_db(db_path, MIG_DIR)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return ExecutionStateRepo(conn)


def _persist_warm_start_row(repo, *, bracket_id="abcd1234"):
    """A persisted OCO_ARMED row → bootstrap takes the FULL path (recover + reconcile)."""
    repo.upsert(
        ExecutionStateRow(
            symbol="BTCUSDT",
            state=ExecutionState.OCO_ARMED,
            position_qty=Decimal("0.001"),
            entry_price=Decimal("60000"),
            oco_main_order_id="entry-1",
            bracket_id=bracket_id,
            oco_tp_order_id="tp-1",
            oco_sl_order_id="sl-1",
            expected_oco_qty=Decimal("0.001"),
            arming_started_at=None,
            last_attempt_num=1,
            updated_at=_now_iso(),
        )
    )


def _filled_entry_snapshot(bracket_id="abcd1234"):
    return OrderSnapshot(
        order_id="entry-1",
        order_link_id=f"oco-{bracket_id}-entry-1",
        order_status="Filled",
        cum_exec_qty=Decimal("0.001"),
        cum_exec_fee=Decimal("0"),
        fee_currency="BTC",
        avg_price=Decimal("60000"),
    )


# ---------------------------------------------------------------------------
# Test 1 (RED on HEAD): RLock is FREE during bootstrap's _recover_attempt_num fetch.
# ---------------------------------------------------------------------------


def test_bootstrap_does_not_hold_lock_during_recover_rest_fetch(tmp_path):
    """While bootstrap's _recover_attempt_num REST fetch is in flight, the
    Coordinator RLock must be available so a WS-thread on_order_event can proceed.

    Thread B runs bootstrap → _recover_attempt_num, whose get_open_orders blocks.
    While blocked, thread W tries to acquire coord._lock non-blocking. With the
    fetch off-lock, the RLock is FREE → W acquires it.
    Pre-fix: bootstrap holds the outer RLock across the whole body → W is blocked.
    """
    from src.execution.coordinator import Coordinator

    repo = _make_repo(tmp_path)
    _persist_warm_start_row(repo)

    slow_fetch_started = threading.Event()
    release_fetch = threading.Event()

    adapter = MagicMock()
    adapter.get_wallet_balance.return_value = WalletSnapshot(
        coin="BTC",
        wallet_balance=Decimal("0.001"),
        available=Decimal("0.001"),
        locked=Decimal("0"),
    )

    def _blocking_open_orders(*_args, **_kwargs):
        slow_fetch_started.set()
        # Block as the real REST backoff would, bounded so a wrong assertion
        # path cannot hang the suite forever.
        release_fetch.wait(timeout=5.0)
        return []

    adapter.get_open_orders.side_effect = _blocking_open_orders
    adapter.get_order_history.return_value = []
    adapter.get_order.return_value = _filled_entry_snapshot()

    reconciler = Reconciler(
        adapter=adapter, base_coin="BTC", symbol="BTCUSDT", heal_max_age_seconds=3600
    )
    coord = Coordinator(
        adapter=adapter, repo=repo, reconciler=reconciler, symbol="BTCUSDT", base_coin="BTC"
    )

    errors: list[BaseException] = []

    def thread_b():
        try:
            coord.bootstrap()
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    t_b = threading.Thread(target=thread_b, name="bootstrap", daemon=True)
    t_b.start()

    assert slow_fetch_started.wait(timeout=5.0), "bootstrap recover fetch never started"

    lock_acquired_during_fetch: list[bool] = []

    def thread_w():
        got = coord._lock.acquire(blocking=False)
        lock_acquired_during_fetch.append(got)
        if got:
            coord._lock.release()

    t_w = threading.Thread(target=thread_w, name="ws-probe", daemon=True)
    t_w.start()
    t_w.join(timeout=5.0)

    release_fetch.set()
    t_b.join(timeout=5.0)

    assert not t_b.is_alive(), "bootstrap timed out"
    assert errors == [], f"bootstrap raised: {errors}"
    assert lock_acquired_during_fetch == [True], (
        "Coordinator RLock was HELD during bootstrap's _recover_attempt_num REST "
        "fetch — a WS-thread on_order_event would be BLOCKED for the full backoff "
        "window (orphan TP self-fill → phantom short). bootstrap must release the "
        "RLock across REST I/O, completing the ARCH-02 hoist on the warm-start path."
    )


# ---------------------------------------------------------------------------
# Test 2: existing behavior preserved — full path applies verdict + _bootstrap_done.
# ---------------------------------------------------------------------------


def test_bootstrap_full_path_applies_reconcile_verdict_and_sets_done(tmp_path):
    """Warm-start row + Filled entry snapshot → reconcile AGREE verdict applied
    (OCO_ARMED stays OCO_ARMED via RECONCILE_OK), _bootstrap_done set True,
    bootstrap_at stamped, last_attempt_num recovered."""
    from src.execution.coordinator import Coordinator

    repo = _make_repo(tmp_path)
    _persist_warm_start_row(repo)

    adapter = MagicMock()
    adapter.get_wallet_balance.return_value = WalletSnapshot(
        coin="BTC",
        wallet_balance=Decimal("0.001"),
        available=Decimal("0.001"),
        locked=Decimal("0"),
    )
    # Recover evidence: an open order at attempt 3 → last_attempt_num must rise.
    adapter.get_open_orders.return_value = [
        {"orderLinkId": "oco-abcd1234-tp-3", "orderStatus": "New"}
    ]
    adapter.get_order_history.return_value = []
    adapter.get_order.return_value = _filled_entry_snapshot()

    reconciler = Reconciler(
        adapter=adapter, base_coin="BTC", symbol="BTCUSDT", heal_max_age_seconds=3600
    )
    coord = Coordinator(
        adapter=adapter, repo=repo, reconciler=reconciler, symbol="BTCUSDT", base_coin="BTC"
    )

    coord.bootstrap()

    assert coord._bootstrap_done is True
    row = repo.get("BTCUSDT")
    assert row is not None
    # AGREE verdict on the quiet armed path keeps the state OCO_ARMED.
    assert row.state == ExecutionState.OCO_ARMED
    assert row.bootstrap_at is not None
    assert row.last_attempt_num == 3


def test_bootstrap_cold_start_noops_and_sets_done(tmp_path):
    """No persisted row → cold start: _bootstrap_done True, no REST fetch."""
    from src.execution.coordinator import Coordinator

    repo = _make_repo(tmp_path)  # empty

    adapter = MagicMock()
    reconciler = Reconciler(
        adapter=adapter, base_coin="BTC", symbol="BTCUSDT", heal_max_age_seconds=3600
    )
    coord = Coordinator(
        adapter=adapter, repo=repo, reconciler=reconciler, symbol="BTCUSDT", base_coin="BTC"
    )

    coord.bootstrap()

    assert coord._bootstrap_done is True
    assert repo.get("BTCUSDT") is None
    adapter.get_open_orders.assert_not_called()
    adapter.get_order_history.assert_not_called()
