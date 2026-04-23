"""ADR 0020 sub-decision 11: stuck OCO_ARMING > TTL → BRACKET_TIMEOUT → HALTED."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow


def _seed(repo, *, state, arming_started_at, updated_at):
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT",
        state=state,
        position_qty=Decimal("0.001"),
        entry_price=Decimal("65000"),
        oco_main_order_id=None,
        bracket_id="abcd1234",
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=Decimal("0.001"),
        arming_started_at=arming_started_at,
        last_attempt_num=1,
        updated_at=updated_at,
    ))


def _make_coordinator(tmp_path: Path) -> tuple[Coordinator, ExecutionStateRepo]:
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    coord = Coordinator(adapter=None, repo=repo, reconciler=None,
                        symbol="BTCUSDT", base_coin="BTC")
    return coord, repo


@pytest.fixture
def coordinator_arming_recent(tmp_path):
    coord, repo = _make_coordinator(tmp_path)
    now = datetime.now(tz=UTC)
    _seed(
        repo,
        state=ExecutionState.OCO_ARMING,
        arming_started_at=(now - timedelta(seconds=30)).isoformat(),
        updated_at=now.isoformat(),
    )
    return type("H", (), {"coordinator": coord, "repo": repo, "now": now})()


@pytest.fixture
def coordinator_arming_stale(tmp_path):
    coord, repo = _make_coordinator(tmp_path)
    now = datetime.now(tz=UTC)
    _seed(
        repo,
        state=ExecutionState.OCO_ARMING,
        arming_started_at=(now - timedelta(seconds=90)).isoformat(),
        updated_at=now.isoformat(),
    )
    return type("H", (), {"coordinator": coord, "repo": repo, "now": now})()


@pytest.fixture
def coordinator_long_open(tmp_path):
    coord, repo = _make_coordinator(tmp_path)
    now = datetime.now(tz=UTC)
    _seed(
        repo,
        state=ExecutionState.LONG_OPEN,
        arming_started_at=None,
        updated_at=now.isoformat(),
    )
    return type("H", (), {"coordinator": coord, "repo": repo, "now": now})()


def test_arming_within_ttl_no_halt(coordinator_arming_recent):
    h = coordinator_arming_recent
    h.coordinator.reconcile_arming_ttl(now=h.now, ttl_seconds=60)
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.OCO_ARMING


def test_arming_beyond_ttl_halts(coordinator_arming_stale):
    h = coordinator_arming_stale
    h.coordinator.reconcile_arming_ttl(now=h.now, ttl_seconds=60)
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED


def test_reconcile_no_op_when_state_not_oco_arming(coordinator_long_open):
    h = coordinator_long_open
    h.coordinator.reconcile_arming_ttl(now=h.now, ttl_seconds=60)
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.LONG_OPEN
