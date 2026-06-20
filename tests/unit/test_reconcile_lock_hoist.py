"""S55 Batch 1 HIGH ARCH-02 — reconcile REST I/O must be hoisted OUTSIDE locks.

THE DEFECT (adversarially confirmed):
``Coordinator.on_ws_reconnect`` acquires the Coordinator RLock, then calls
``reconciler.reconcile`` which acquires the Reconciler.Lock. BOTH locks held
simultaneously. Inside reconcile, the exchange-state fetches (get_wallet_balance /
get_open_orders / get_order) do REST calls whose ``_retry_with_backoff`` sleeps
up to ~15.5s on rate-limit codes — ALL while both locks are held. During that
window the pybit WS thread's ``on_order_event`` is BLOCKED on the Coordinator
RLock, and ``on_order_event`` handles the SL-trigger sibling-cancel whose timing
window is the 0ms Bybit Spot Triggered→Filled gap. Blocking it for seconds →
orphan TP self-fills → phantom short on Spot.

FIX: hoist all exchange-state fetching OUTSIDE the locks — snapshot FIRST (no
locks), THEN acquire the lock only to run the PURE classify over the snapshot +
apply the verdict transition.

These tests assert the lock-hold window EXCLUDES the REST fetches:
  1. Reconciler.reconcile does NOT hold the Reconciler.Lock during get_open_orders.
  2. Coordinator.on_ws_reconnect does NOT hold the Coordinator RLock while the
     reconciler fetch is in flight → on_order_event from another thread is NOT
     blocked during the (slow) fetch window.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from src.execution.bybit.adapter import OrderSnapshot, WalletSnapshot
from src.execution.reconciler import LocalState, Reconciler
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.platform.db import init_db

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


# ---------------------------------------------------------------------------
# Test 1: Reconciler.reconcile fetches exchange state with the Lock RELEASED.
# ---------------------------------------------------------------------------


def test_reconcile_does_not_hold_lock_during_rest_fetch():
    """The Reconciler.Lock must NOT be held while get_open_orders runs.

    Probe: the mocked get_open_orders records, at call time, whether the
    Reconciler.Lock is currently free (acquirable by another notional thread).
    With the I/O hoisted, the lock is free during the REST call.
    """
    adapter = MagicMock()
    adapter.get_wallet_balance.return_value = WalletSnapshot(
        coin="BTC", wallet_balance=Decimal("0.001"), available=Decimal("0.001"), locked=Decimal("0")
    )

    reco = Reconciler(adapter=adapter, base_coin="BTC", symbol="BTCUSDT", heal_max_age_seconds=3600)

    lock_free_at_fetch: list[bool] = []

    def _probe_open_orders(*_args, **_kwargs):
        # Acquire from THIS thread non-blocking: a non-reentrant Lock that is
        # already held by reconcile() on this same thread would return False.
        got = reco._lock.acquire(blocking=False)
        lock_free_at_fetch.append(got)
        if got:
            reco._lock.release()
        return []

    adapter.get_open_orders.side_effect = _probe_open_orders

    local = LocalState(
        state="LONG_OPEN", position_qty=Decimal("0.001"), symbol="BTCUSDT", entry_order_id=None
    )
    reco.reconcile(local)  # binary path

    assert lock_free_at_fetch == [True], (
        "Reconciler.Lock was HELD during get_open_orders — REST I/O still runs "
        "under the lock; hoist did not move the fetch out"
    )


# ---------------------------------------------------------------------------
# Test 2: Coordinator.on_ws_reconnect must NOT block on_order_event during fetch.
# ---------------------------------------------------------------------------


def _build_coord(tmp_path, *, slow_fetch_started, release_fetch):
    """Coordinator + real Reconciler whose REST fetch blocks until released."""
    from src.execution.coordinator import Coordinator

    db_path = tmp_path / "hoist.db"
    init_db(db_path, MIG_DIR)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    repo = ExecutionStateRepo(conn)

    bracket_id = "abcd1234"
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

    # Real adapter mock whose get_open_orders blocks (simulates ~15.5s backoff sleep).
    adapter = MagicMock()
    adapter.get_wallet_balance.return_value = WalletSnapshot(
        coin="BTC",
        wallet_balance=Decimal("0.001"),
        available=Decimal("0.001"),
        locked=Decimal("0"),
    )

    def _blocking_open_orders(*_args, **_kwargs):
        slow_fetch_started.set()
        # Block here as the real REST backoff would, but bounded so the test
        # cannot hang forever if the assertion path is wrong.
        release_fetch.wait(timeout=5.0)
        return []

    adapter.get_open_orders.side_effect = _blocking_open_orders
    adapter.get_order.return_value = OrderSnapshot(
        order_id="entry-1",
        order_link_id=f"oco-{bracket_id}-entry-1",
        order_status="Filled",
        cum_exec_qty=Decimal("0.001"),
        cum_exec_fee=Decimal("0"),
        fee_currency="BTC",
        avg_price=Decimal("60000"),
    )

    reconciler = Reconciler(
        adapter=adapter, base_coin="BTC", symbol="BTCUSDT", heal_max_age_seconds=3600
    )

    coord = Coordinator(
        adapter=adapter, repo=repo, reconciler=reconciler, symbol="BTCUSDT", base_coin="BTC"
    )
    coord._bootstrap_done = True
    return coord, repo


def test_on_ws_reconnect_does_not_block_on_order_event_during_fetch(tmp_path):
    """While on_ws_reconnect's reconcile fetch is in flight, the Coordinator RLock
    must be available so a WS-thread on_order_event can proceed (SL-cancel window).

    Thread R runs on_ws_reconnect → reconcile, whose get_open_orders blocks.
    While blocked, thread W tries to acquire coord._lock non-blocking. With the
    fetch hoisted OUT of the RLock, the lock is FREE → W acquires it.
    Pre-fix: the RLock is held across the whole reconcile → W is blocked.
    """
    slow_fetch_started = threading.Event()
    release_fetch = threading.Event()
    coord, _repo = _build_coord(
        tmp_path, slow_fetch_started=slow_fetch_started, release_fetch=release_fetch
    )

    errors: list[BaseException] = []

    def thread_r():
        try:
            coord.on_ws_reconnect()
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    t_r = threading.Thread(target=thread_r, name="reconcile", daemon=True)
    t_r.start()

    # Wait until the REST fetch is in flight (lock-hold window under test).
    assert slow_fetch_started.wait(timeout=5.0), "reconcile fetch never started"

    # Probe the Coordinator RLock from another thread WHILE the fetch blocks.
    lock_acquired_during_fetch: list[bool] = []

    def thread_w():
        got = coord._lock.acquire(blocking=False)
        lock_acquired_during_fetch.append(got)
        if got:
            coord._lock.release()

    t_w = threading.Thread(target=thread_w, name="ws-probe", daemon=True)
    t_w.start()
    t_w.join(timeout=5.0)

    # Unblock the fetch so on_ws_reconnect can finish.
    release_fetch.set()
    t_r.join(timeout=5.0)

    assert not t_r.is_alive(), "on_ws_reconnect timed out"
    assert errors == [], f"on_ws_reconnect raised: {errors}"
    assert lock_acquired_during_fetch == [True], (
        "Coordinator RLock was HELD during the reconcile REST fetch — a WS-thread "
        "on_order_event would be BLOCKED for the full ~15.5s backoff window "
        "(orphan TP self-fill → phantom short). REST I/O must be hoisted out of the lock."
    )
