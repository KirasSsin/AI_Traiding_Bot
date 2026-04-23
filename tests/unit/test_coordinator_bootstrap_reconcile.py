"""Tasks 21 + 22: Coordinator bootstrap composition + _bootstrap_done guards.

ADR 0021 sub-decisions 1 + 7.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.platform.db import connect, init_db

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_repo(tmp_path, db_name: str = "coord.db") -> tuple[ExecutionStateRepo, object]:
    """Return (repo, conn) for a fresh migrated DB."""
    db_path = tmp_path / db_name
    init_db(db_path, MIG_DIR)
    conn = connect(db_path)
    return ExecutionStateRepo(conn), conn


def _build_coord(repo: ExecutionStateRepo) -> "Coordinator":
    from src.execution.coordinator import Coordinator

    adapter = MagicMock()
    adapter.get_open_orders.return_value = []
    adapter.get_order_history.return_value = []
    reconciler = MagicMock()
    return Coordinator(
        adapter=adapter, repo=repo, reconciler=reconciler,
        symbol="BTCUSDT", base_coin="BTC",
    )


def _seed_row(repo: ExecutionStateRepo, state: ExecutionState, **overrides) -> None:
    base = dict(
        symbol="BTCUSDT",
        state=state,
        position_qty=Decimal("0"),
        entry_price=None,
        oco_main_order_id=None,
        bracket_id="abcdef12",
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=None,
        arming_started_at=None,
        last_attempt_num=0,
        updated_at=_now_iso(),
    )
    base.update(overrides)
    repo.upsert(ExecutionStateRow(**base))


# ===========================================================================
# Task 21 — bootstrap delegates to on_ws_reconnect
# ===========================================================================

def test_bootstrap_cold_start_marks_done_without_reconcile(tmp_path):
    """Cold start (no persisted row) → _bootstrap_done = True, reconciler not called."""
    repo, _ = _make_repo(tmp_path)
    coord = _build_coord(repo)

    coord.bootstrap()

    assert coord._bootstrap_done is True
    coord._reconciler.reconcile.assert_not_called()


def test_bootstrap_warm_start_calls_on_ws_reconnect(tmp_path):
    """Warm start with ENTRY_PENDING row → on_ws_reconnect is invoked + _bootstrap_done = True."""
    repo, _ = _make_repo(tmp_path)
    _seed_row(repo, ExecutionState.ENTRY_PENDING)
    coord = _build_coord(repo)

    with patch.object(coord, "on_ws_reconnect") as mock_reconnect:
        coord.bootstrap()

    mock_reconnect.assert_called_once()
    assert coord._bootstrap_done is True


def test_bootstrap_recovers_attempt_num_from_history(tmp_path):
    """Bootstrap with bracket_id recovers last_attempt_num from order history."""
    repo, _ = _make_repo(tmp_path)
    _seed_row(
        repo,
        ExecutionState.FLAT,
        bracket_id="abc",
        last_attempt_num=0,
    )
    coord = _build_coord(repo)
    # FLAT is not reconcilable → on_ws_reconnect won't call reconciler
    coord._adapter.get_open_orders.return_value = []
    coord._adapter.get_order_history.return_value = [
        {"orderLinkId": "oco-abc-TP-3"},
        {"orderLinkId": "oco-abc-SL-3"},
    ]

    coord.bootstrap()

    row = repo.get("BTCUSDT")
    assert row is not None
    assert row.last_attempt_num >= 3


# ===========================================================================
# Task 22 — _bootstrap_done assert guards
# ===========================================================================

def test_start_bracket_raises_before_bootstrap(tmp_path):
    """start_bracket must raise AssertionError if bootstrap() was not called."""
    repo, _ = _make_repo(tmp_path)
    coord = _build_coord(repo)

    with pytest.raises(AssertionError, match="bootstrap"):
        coord.start_bracket(
            entry_qty=Decimal("0.001"),
            entry_side="Buy",
            tp_price=Decimal("65000"),
            sl_trigger_price=Decimal("59000"),
        )


def test_on_order_event_raises_before_bootstrap(tmp_path):
    """on_order_event must raise AssertionError if bootstrap() was not called."""
    repo, _ = _make_repo(tmp_path)
    coord = _build_coord(repo)

    with pytest.raises(AssertionError, match="bootstrap"):
        coord.on_order_event({"orderLinkId": "x", "orderStatus": "Filled"})


def test_methods_work_after_bootstrap(tmp_path):
    """After cold-start bootstrap, on_order_event must NOT raise AssertionError."""
    repo, _ = _make_repo(tmp_path)
    coord = _build_coord(repo)

    coord.bootstrap()  # cold-start, no row

    # on_order_event may raise other errors (no row etc.) but not AssertionError
    try:
        coord.on_order_event({"orderLinkId": "oco-abc-entry-1", "orderStatus": "Filled"})
    except AssertionError:
        pytest.fail("on_order_event raised AssertionError after bootstrap()")
