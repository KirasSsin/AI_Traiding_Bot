"""Tests for migrations/002_risk.sql idempotency and schema correctness."""

import sqlite3
from pathlib import Path

import pytest

from src.platform.db import connect, init_db

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    init_db(db_path, MIGRATIONS_DIR)
    return connect(db_path)


def test_trade_history_table_exists(db: sqlite3.Connection) -> None:
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='trade_history'"
    ).fetchall()
    assert len(rows) == 1


def test_equity_snapshots_table_exists(db: sqlite3.Connection) -> None:
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='equity_snapshots'"
    ).fetchall()
    assert len(rows) == 1


def test_trade_history_columns(db: sqlite3.Connection) -> None:
    cols = {row[1] for row in db.execute("PRAGMA table_info(trade_history)").fetchall()}
    expected = {
        "trade_id", "symbol", "entry_signal_id", "entry_ts", "exit_ts",
        "qty", "entry_price", "exit_price", "pnl_quote", "pnl_pct",
        "fees_paid", "reason_code", "kelly_phase", "recorded_at",
    }
    assert expected <= cols


def test_equity_snapshots_columns(db: sqlite3.Connection) -> None:
    cols = {row[1] for row in db.execute("PRAGMA table_info(equity_snapshots)").fetchall()}
    expected = {
        "snapshot_id", "ts", "realized_equity", "unrealized_pnl",
        "total_equity", "source",
    }
    assert expected <= cols


def test_kelly_phase_check_constraint(db: sqlite3.Connection) -> None:
    """kelly_phase CHECK(IN (1,2,3,4)) должен отклонить 0 и 5."""
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO trade_history VALUES "
            "(NULL,'BTCUSDT','sig-1','2026-01-01T00:00:00','2026-01-01T01:00:00',"
            "'0.001','50000','51000','10','0.02','0.5','ENTRY_LONG_TREND_FOLLOWING',0,'2026-01-01T01:00:00')"
        )


def test_equity_source_check_constraint(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO equity_snapshots VALUES "
            "(NULL,'2026-01-01T00:00:00','10000','0','10000','INVALID_SOURCE')"
        )


def test_idempotent_double_init(tmp_path: Path) -> None:
    """Повторный init_db не должен падать."""
    db_path = tmp_path / "idempotent.db"
    init_db(db_path, MIGRATIONS_DIR)
    init_db(db_path, MIGRATIONS_DIR)  # должно пройти без ошибки


def test_state_table_exists(db: sqlite3.Connection) -> None:
    """state таблица из 001_initial.sql должна существовать (реюзается S4)."""
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='state'"
    ).fetchall()
    assert len(rows) == 1
