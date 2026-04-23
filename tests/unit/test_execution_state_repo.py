# tests/unit/test_execution_state_repo.py
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "exec.db"
    conn = sqlite3.connect(db)
    for name in ("0003_execution_state.sql", "0004_execution_state_v2.sql"):
        conn.executescript((MIGRATIONS / name).read_text())
    return conn


def test_upsert_and_get_roundtrip(conn):
    repo = ExecutionStateRepo(conn)
    row = ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.OCO_ARMED,
        position_qty=Decimal("0.01234567"),
        entry_price=Decimal("65432.10"),
        oco_main_order_id="abc-123",
        bracket_id=None,
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=None,
        arming_started_at=None,
        last_attempt_num=1,
        updated_at="2026-04-23T10:00:00+00:00",
    )
    repo.upsert(row)
    got = repo.get("BTCUSDT")
    assert got == row


def test_get_unknown_returns_none(conn):
    repo = ExecutionStateRepo(conn)
    assert repo.get("ETHUSDT") is None


def test_decimal_precision_preserved(conn):
    repo = ExecutionStateRepo(conn)
    qty = Decimal("0.123456789012345678")  # > IEEE-754 double precision
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT", state=ExecutionState.LONG_OPEN,
        position_qty=qty, entry_price=Decimal("100"),
        oco_main_order_id=None, bracket_id=None, oco_tp_order_id=None,
        oco_sl_order_id=None, expected_oco_qty=None, arming_started_at=None,
        last_attempt_num=1, updated_at="2026-04-23T10:00:00+00:00",
    ))
    assert repo.get("BTCUSDT").position_qty == qty
