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
    for name in ("0003_execution_state.sql", "0004_execution_state_v2.sql", "0005_halt_persistence.sql"):
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


# --- Sprint 7: halt persistence fields (ADR 0021 sub-decision 5) ---

def test_execution_state_row_default_halt_persistence_fields_none():
    """ADR 0021 sub-decision 5: 4 new fields default to None."""
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
        updated_at="2026-04-24T00:00:00+00:00",
    )
    assert row.halt_reason is None
    assert row.last_exit_reason is None
    assert row.last_reconcile_at is None
    assert row.bootstrap_at is None


def test_execution_state_repo_persists_halt_fields(conn):
    """upsert + get round-trip preserves halt_reason / last_exit_reason / last_reconcile_at / bootstrap_at."""
    repo = ExecutionStateRepo(conn)
    row = ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.HALTED,
        position_qty=Decimal("0.001"),
        entry_price=Decimal("62000"),
        oco_main_order_id=None,
        bracket_id="abc-1234",
        oco_tp_order_id="tp-1",
        oco_sl_order_id="sl-1",
        expected_oco_qty=Decimal("0.001"),
        arming_started_at=None,
        last_attempt_num=2,
        updated_at="2026-04-24T12:34:56+00:00",
        halt_reason="HALT_OCO_ARM_TIMEOUT",
        last_exit_reason=None,
        last_reconcile_at="2026-04-24T12:30:00+00:00",
        bootstrap_at="2026-04-24T12:00:00+00:00",
    )
    repo.upsert(row)
    fetched = repo.get("BTCUSDT")
    assert fetched is not None
    assert fetched.halt_reason == "HALT_OCO_ARM_TIMEOUT"
    assert fetched.last_exit_reason is None
    assert fetched.last_reconcile_at == "2026-04-24T12:30:00+00:00"
    assert fetched.bootstrap_at == "2026-04-24T12:00:00+00:00"


def test_execution_state_repo_pre_s7_row_reads_null_halt_fields(conn):
    """Backward compat: row written without halt fields reads back as None (defaults)."""
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
        updated_at="2026-04-24T00:00:00+00:00",
        # halt fields omitted — defaults None
    )
    repo.upsert(row)
    fetched = repo.get("BTCUSDT")
    assert fetched.halt_reason is None
    assert fetched.last_exit_reason is None
    assert fetched.last_reconcile_at is None
    assert fetched.bootstrap_at is None
