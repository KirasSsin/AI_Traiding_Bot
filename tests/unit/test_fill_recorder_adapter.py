"""FillRecorderAdapter — bridges Bybit V5 WS execution event → FillHistoryRepository.

S12 Q5 REVISE-additive (per ADR 0027):
- Always-on structlog audit
- Best-effort DB insert via lookup chain
- No new migrations (Q7 zero-migration constraint)

CURRENT SCHEMA REALITY (Step 5 Option B per task spec):
``execution_state`` table has NO ``entry_signal_id`` column. Coordinator does not
persist the entry signal_id alongside bracket_id. Therefore the lookup chain
WS orderId → execution_state.bracket_id → trade_history.entry_signal_id
breaks at the bracket_id↔trade_id gap. Until S13+ adds a schema link, the adapter
ALWAYS skips DB insert and emits structlog audit only. Adapter still calls
``find_by_order_id`` to make the gap visible in logs (and to be drop-in compatible
with the S13+ schema fix).
"""

from __future__ import annotations

import logging
import threading
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from src.risk.fill_history import FillHistoryRepository
from src.risk.fill_recorder_adapter import FillRecorderAdapter


def _make_evt(*, order_id: str = "BYBIT-ORD-1", exec_id: str = "EXEC-1") -> dict:
    """Minimal Bybit V5 execution topic item."""
    return {
        "orderId": order_id,
        "execId": exec_id,
        "execQty": "0.001",
        "execPrice": "50000.0",
        "execFee": "0.025",
        "feeRate": "0.001",
        "feeCurrency": "USDT",
        "execTime": "1735689600000",  # ms epoch
        "leavesQty": "0",  # 0 = fully filled (not partial)
    }


def test_adapter_emits_audit_log_for_every_event(caplog: pytest.LogCaptureFixture) -> None:
    """Layer 1: always-on audit. Every WS event → fill_event_received log line."""
    repo = MagicMock(spec=FillHistoryRepository)
    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=MagicMock(),
        trade_history_repo=MagicMock(),
    )
    with caplog.at_level(logging.INFO, logger="src.risk.fill_recorder_adapter"):
        adapter.on_fill_event(_make_evt())
    assert any("fill_event_received" in rec.message for rec in caplog.records)


def test_adapter_skips_db_insert_when_orderid_missing(caplog: pytest.LogCaptureFixture) -> None:
    """No orderId → log warning + skip insert (no crash)."""
    repo = MagicMock(spec=FillHistoryRepository)
    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=MagicMock(),
        trade_history_repo=MagicMock(),
    )
    evt_no_order = _make_evt()
    del evt_no_order["orderId"]

    with caplog.at_level(logging.WARNING, logger="src.risk.fill_recorder_adapter"):
        adapter.on_fill_event(evt_no_order)

    repo.insert_fill.assert_not_called()
    assert any("fill_event_unresolved_skipping_db" in rec.message for rec in caplog.records)


def test_adapter_skips_db_insert_when_state_row_not_found(caplog: pytest.LogCaptureFixture) -> None:
    """orderId present but no execution_state row matches → skip insert (race-condition safe)."""
    repo = MagicMock(spec=FillHistoryRepository)
    state_repo = MagicMock()
    state_repo.find_by_order_id.return_value = None  # no match
    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=state_repo,
        trade_history_repo=MagicMock(),
    )

    with caplog.at_level(logging.WARNING, logger="src.risk.fill_recorder_adapter"):
        adapter.on_fill_event(_make_evt())

    repo.insert_fill.assert_not_called()
    state_repo.find_by_order_id.assert_called_once_with("BYBIT-ORD-1")
    assert any("fill_event_unresolved_skipping_db" in rec.message for rec in caplog.records)


def test_adapter_skips_db_insert_when_state_row_resolved_but_signal_id_unstored(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Bracket resolved BUT execution_state has no entry_signal_id link (current schema).

    Honest reality: even с full lookup, parent_trade_id cannot be derived without
    a schema migration adding signal_id↔bracket_id. Adapter logs gap + skips.
    Deferred к S13+.
    """
    repo = MagicMock(spec=FillHistoryRepository)
    state_repo = MagicMock()
    # ExecutionStateRow has bracket_id but NO entry_signal_id field — current schema
    state_row_mock = MagicMock(spec=["bracket_id", "symbol"])
    state_row_mock.bracket_id = "BR-001"
    state_row_mock.symbol = "BTCUSDT"
    state_repo.find_by_order_id.return_value = state_row_mock

    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=state_repo,
        trade_history_repo=MagicMock(),
    )

    with caplog.at_level(logging.WARNING, logger="src.risk.fill_recorder_adapter"):
        adapter.on_fill_event(_make_evt())

    repo.insert_fill.assert_not_called()
    assert any(
        "fill_event_unresolved_skipping_db" in rec.message
        and ("bracket_id" in rec.message or "S13" in rec.message)
        for rec in caplog.records
    )


def test_adapter_does_not_crash_on_malformed_event() -> None:
    """Empty / malformed event → skip + log; never raises (WS thread protection)."""
    repo = MagicMock(spec=FillHistoryRepository)
    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=MagicMock(),
        trade_history_repo=MagicMock(),
    )
    # Empty dict — no orderId, no nothing
    adapter.on_fill_event({})
    # Garbage types
    adapter.on_fill_event({"orderId": "X", "execTime": "not-a-number"})

    repo.insert_fill.assert_not_called()


def test_build_fill_record_static_helper_maps_v5_fields_correctly() -> None:
    """Pure helper: Bybit V5 evt → FillRecord with Decimal monetary + UTC ts.

    Helper preserved for S13+ when lookup chain becomes resolvable. Tested in
    isolation так что schema-dependent insert path не блокирует verification of
    mapping correctness.
    """
    from datetime import UTC, datetime

    record = FillRecorderAdapter._build_fill_record(
        evt=_make_evt(),
        parent_trade_id=42,
    )
    assert record.parent_trade_id == 42
    assert record.exec_id == "EXEC-1"
    assert record.fill_qty == Decimal("0.001")
    assert record.fill_price == Decimal("50000.0")
    assert record.fill_fee == Decimal("0.025")
    assert record.fee_currency == "USDT"
    assert record.is_partial is False  # leavesQty=0
    assert record.fill_ts == datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)


def test_build_fill_record_partial_fill_detected_via_leaves_qty_nonzero() -> None:
    """leavesQty > 0 → is_partial=True."""
    evt_partial = _make_evt()
    evt_partial["leavesQty"] = "0.0005"
    record = FillRecorderAdapter._build_fill_record(evt=evt_partial, parent_trade_id=42)
    assert record.is_partial is True


# ---------------------------------------------------------------------------
# H5 (S49): thread-safety — WS callback thread shares SQLite connection family
# with main-thread Risk/State repos. The read+insert critical section must run
# under a lock so a concurrent main-thread tick cannot interleave.
# ---------------------------------------------------------------------------


def test_adapter_holds_lock_during_critical_section() -> None:
    """The state_repo lookup + insert run while the adapter's lock is held.

    Asserts the lock is acquired before find_by_order_id and not yet released
    when insert_fill is reached — i.e. the whole read→insert path is serialized.
    """
    lock = threading.Lock()
    repo = MagicMock(spec=FillHistoryRepository)
    state_repo = MagicMock()

    # Resolve the chain far enough to reach insert: state_row carries an
    # entry_signal_id, trade_history resolves a trade_id.
    state_row = MagicMock(spec=["entry_signal_id", "bracket_id", "symbol"])
    state_row.entry_signal_id = "sig-1"
    state_row.bracket_id = "BR-1"
    state_row.symbol = "BTCUSDT"

    locked_during_lookup: list[bool] = []
    locked_during_insert: list[bool] = []

    def _find(_order_id):
        locked_during_lookup.append(lock.locked())
        return state_row

    state_repo.find_by_order_id.side_effect = _find

    trade_history_repo = MagicMock()
    trade_history_repo.find_trade_id_by_signal.return_value = 7

    def _insert(_record):
        locked_during_insert.append(lock.locked())

    repo.insert_fill.side_effect = _insert

    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=state_repo,
        trade_history_repo=trade_history_repo,
        lock=lock,
    )
    adapter.on_fill_event(_make_evt())

    repo.insert_fill.assert_called_once()
    assert locked_during_lookup == [True], "lock must be held during state_repo lookup"
    assert locked_during_insert == [True], "lock must be held during insert_fill"
    assert not lock.locked(), "lock must be released after on_fill_event returns"


def test_adapter_creates_default_lock_when_none_injected() -> None:
    """A dedicated lock is created if none is injected (backwards compatible ctor)."""
    adapter = FillRecorderAdapter(
        repo=MagicMock(spec=FillHistoryRepository),
        state_repo=MagicMock(),
        trade_history_repo=MagicMock(),
    )
    assert isinstance(adapter._lock, type(threading.Lock()))


def test_adapter_serializes_concurrent_fill_events() -> None:
    """Stress: two WS-thread on_fill_event calls never interleave the critical section.

    A barrier inside find_by_order_id forces both threads to contend; the lock
    must serialize them so insert_fill calls do not overlap.
    """
    lock = threading.Lock()
    repo = MagicMock(spec=FillHistoryRepository)
    state_repo = MagicMock()
    trade_history_repo = MagicMock()
    trade_history_repo.find_trade_id_by_signal.return_value = 1

    state_row = MagicMock(spec=["entry_signal_id", "bracket_id", "symbol"])
    state_row.entry_signal_id = "sig"
    state_row.bracket_id = "BR"
    state_row.symbol = "BTCUSDT"

    active = 0
    max_concurrent = 0
    guard = threading.Lock()

    def _find(_order_id):
        nonlocal active, max_concurrent
        with guard:
            active += 1
            max_concurrent = max(max_concurrent, active)
        return state_row

    def _insert(_record):
        nonlocal active
        with guard:
            active -= 1

    state_repo.find_by_order_id.side_effect = _find
    repo.insert_fill.side_effect = _insert

    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=state_repo,
        trade_history_repo=trade_history_repo,
        lock=lock,
    )

    threads = [
        threading.Thread(target=adapter.on_fill_event, args=(_make_evt(exec_id=f"E-{i}"),))
        for i in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert max_concurrent == 1, (
        f"critical section was entered concurrently (max={max_concurrent}); "
        "lock did not serialize WS-thread fill inserts"
    )
