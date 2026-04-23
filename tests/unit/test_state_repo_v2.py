from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(tmp_path / "test.db")
    db.execute("PRAGMA journal_mode = WAL;")
    for name in (
        "001_initial.sql",
        "0003_execution_state.sql",
        "0004_execution_state_v2.sql",
    ):
        db.executescript((MIGRATIONS / name).read_text())
    return db


def test_v2_round_trip_with_new_columns(conn: sqlite3.Connection) -> None:
    repo = ExecutionStateRepo(conn)
    row = ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.OCO_ARMED,
        position_qty=Decimal("0.000643"),
        entry_price=Decimal("65000.5"),
        oco_main_order_id=None,
        bracket_id="b3a1c2d4-0000-4000-8000-000000000001",
        oco_tp_order_id="tp-oid-1",
        oco_sl_order_id="sl-oid-1",
        expected_oco_qty=Decimal("0.000643"),
        arming_started_at="2026-04-23T12:00:00+00:00",
        last_attempt_num=1,
        updated_at="2026-04-23T12:00:01+00:00",
    )
    repo.upsert(row)
    got = repo.get("BTCUSDT")
    assert got == row


def test_v2_nullable_new_columns_when_flat(conn: sqlite3.Connection) -> None:
    repo = ExecutionStateRepo(conn)
    row = ExecutionStateRow(
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
        last_attempt_num=1,
        updated_at="2026-04-23T12:00:00+00:00",
    )
    repo.upsert(row)
    got = repo.get("BTCUSDT")
    assert got == row
