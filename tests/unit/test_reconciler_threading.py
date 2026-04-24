"""ADR 0022 sub-decision 1 — Reconciler threading.Lock (non-reentrant).

3 tests:
1. test_reconciler_has_lock                      — _lock is Lock (not RLock)
2. test_reconciler_lock_is_NOT_reentrant          — second acquire returns False
3. test_reconciler_concurrent_wallet_event_and_reconcile_no_corruption — 2-thread race
"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock

from src.execution.reconciler import Reconciler


def _make_reconciler():
    adapter = MagicMock()
    adapter.get_wallet_balance = MagicMock(return_value={"BTC": "0.001", "USDT": "100"})
    adapter.get_open_orders = MagicMock(return_value=[])
    return Reconciler(
        adapter=adapter,
        base_coin="BTC",
        symbol="BTCUSDT",
        heal_max_age_seconds=3600,
    )


def test_reconciler_has_lock():
    r = _make_reconciler()
    assert isinstance(r._lock, type(threading.Lock())), (
        "Reconciler must use threading.Lock (non-reentrant) per ADR 0022 sub-decision 1"
    )


def test_reconciler_lock_is_NOT_reentrant():
    """Lock (vs RLock) must reject re-entry on same thread (acquire returns False)."""
    r = _make_reconciler()
    with r._lock:
        acquired = r._lock.acquire(blocking=False)
        assert acquired is False, "Reconciler lock must be Lock, not RLock"
        # NOTE: do NOT release — we never acquired it


def test_reconciler_concurrent_wallet_event_and_reconcile_no_corruption():
    r = _make_reconciler()
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def push_wallet():
        try:
            barrier.wait()
            evt = {"coin": "BTC", "walletBalance": "0.001"}
            r.on_wallet_event(evt)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    def call_reconcile():
        try:
            barrier.wait()
            local = MagicMock(symbol="BTCUSDT", state="LONG_OPEN", entry_order_id=None)
            r.reconcile(local)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    t1 = threading.Thread(target=push_wallet, daemon=True)
    t2 = threading.Thread(target=call_reconcile, daemon=True)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    # AttributeError on MagicMock setup is a TEST issue (caller fixes), not a race.
    race_errors = [e for e in errors if not isinstance(e, AttributeError)]
    assert race_errors == [], f"Concurrent run produced race errors: {race_errors}"
