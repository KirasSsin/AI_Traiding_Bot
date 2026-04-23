"""Regression test: migration runner must be atomic (ADR 0021 follow-up)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.platform.db import init_db


def test_migration_runner_atomic_on_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If executescript() crashes mid-migration, no partial commit and no tracking row.

    Simulates: migration body fails → re-run must be safe (no duplicate-column errors).
    """
    db_path = tmp_path / "atomic.db"
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Migration 1: valid — baseline table.
    (migrations_dir / "001_init.sql").write_text(
        "CREATE TABLE t1 (id INTEGER PRIMARY KEY, name TEXT);\n"
        "INSERT INTO t1 (name) VALUES ('a');\n"
    )
    # Migration 2: invalid SQL — must fail, leaving DB unchanged.
    (migrations_dir / "002_broken.sql").write_text(
        "ALTER TABLE t1 ADD COLUMN x TEXT;\n"
        "THIS IS NOT VALID SQL;\n"
    )

    # First init: 001 applies, 002 fails.
    with pytest.raises(sqlite3.OperationalError):
        init_db(db_path, migrations_dir)

    # Verify: 001 applied + tracked, 002 rolled back + NOT tracked.
    conn = sqlite3.connect(str(db_path))
    try:
        applied = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations").fetchall()}
        assert "001_init.sql" in applied
        assert "002_broken.sql" not in applied
        # Column `x` must NOT exist — 002 rolled back atomically.
        cols = {row[1] for row in conn.execute("PRAGMA table_info(t1)").fetchall()}
        assert "x" not in cols
    finally:
        conn.close()


def test_migration_runner_idempotent_on_rerun(tmp_path: Path) -> None:
    """Re-run on fully-applied DB is no-op."""
    db_path = tmp_path / "rerun.db"
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "001_init.sql").write_text(
        "CREATE TABLE t (id INTEGER PRIMARY KEY);\n"
    )

    init_db(db_path, migrations_dir)
    init_db(db_path, migrations_dir)  # second run must not raise

    conn = sqlite3.connect(str(db_path))
    try:
        count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        assert count == 1
    finally:
        conn.close()
