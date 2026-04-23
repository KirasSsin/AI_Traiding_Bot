"""Schema tests for migration 0005 (ADR 0021 sub-decisions 5+9).

This file will be EXTENDED in later Sprint 7 tasks (Tasks 9, 10) with
_set_halt idempotency tests. For Task 1 it covers schema-only.
"""
import sqlite3
from pathlib import Path


MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply all .sql files in migrations/ in lexicographic order."""
    for mig_path in sorted(MIG_DIR.glob("*.sql")):
        conn.executescript(mig_path.read_text())


def test_migration_0005_adds_halt_columns(tmp_path):
    """4 new columns on execution_state: halt_reason, last_exit_reason, last_reconcile_at, bootstrap_at."""
    db = sqlite3.connect(tmp_path / "test.db")
    try:
        _apply_migrations(db)
        cols = {row[1] for row in db.execute("PRAGMA table_info(execution_state)")}
        assert {"halt_reason", "last_exit_reason", "last_reconcile_at", "bootstrap_at"}.issubset(cols), (
            f"missing halt persistence columns; got: {sorted(cols)}"
        )
    finally:
        db.close()


def test_migration_0005_creates_halt_log_table(tmp_path):
    """halt_log table + composite index halt_log_symbol_ts."""
    db = sqlite3.connect(tmp_path / "test.db")
    try:
        _apply_migrations(db)
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "halt_log" in tables, f"halt_log table missing; got tables: {sorted(tables)}"
        indexes = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        assert "halt_log_symbol_ts" in indexes, f"index missing; got: {sorted(indexes)}"
    finally:
        db.close()


def test_migration_0005_halt_log_columns(tmp_path):
    """halt_log schema: id PK AUTOINCREMENT, symbol TEXT NOT NULL, ts TEXT NOT NULL, reason TEXT NOT NULL, context_json TEXT NOT NULL."""
    db = sqlite3.connect(tmp_path / "test.db")
    try:
        _apply_migrations(db)
        cols = {row[1]: row for row in db.execute("PRAGMA table_info(halt_log)")}
        assert set(cols) == {"id", "symbol", "ts", "reason", "context_json"}
        # All non-id columns NOT NULL (notnull == 1)
        for c in ("symbol", "ts", "reason", "context_json"):
            assert cols[c][3] == 1, f"{c} should be NOT NULL"
    finally:
        db.close()
