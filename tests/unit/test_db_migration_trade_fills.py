"""Verify migration 0006 creates trade_fills table with expected schema.

Sprint 9 Q3 B1.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.platform.db import init_db

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def test_migration_0006_creates_trade_fills_table(tmp_path: Path) -> None:
    """trade_fills table exists with expected columns + FK к trade_history."""
    db_path = tmp_path / "test.db"
    init_db(db_path, MIG_DIR)
    conn = sqlite3.connect(str(db_path))
    cols = conn.execute("PRAGMA table_info(trade_fills)").fetchall()
    col_names = [c[1] for c in cols]
    assert col_names == [
        "fill_id", "parent_trade_id", "exec_id", "fill_qty",
        "fill_price", "fill_fee", "fee_currency", "is_partial",
        "fill_ts", "recorded_at",
    ]
    # Verify FK
    fks = conn.execute("PRAGMA foreign_key_list(trade_fills)").fetchall()
    assert len(fks) == 1
    assert fks[0][2] == "trade_history"  # references table
    assert fks[0][4] == "trade_id"  # references column

    # Verify UNIQUE INDEX on exec_id (idempotency)
    idxs = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='trade_fills'"
    ).fetchall()
    assert any("UNIQUE" in (idx[1] or "") and "exec_id" in (idx[1] or "") for idx in idxs)


def test_migration_0006_idempotent(tmp_path: Path) -> None:
    """Re-running migrations does not fail."""
    db_path = tmp_path / "test.db"
    init_db(db_path, MIG_DIR)
    init_db(db_path, MIG_DIR)  # Should not raise


def test_migration_0006_fk_enforced_at_insert(tmp_path: Path) -> None:
    """FK к trade_history enforced — INSERT с invalid parent_trade_id raises.

    Verifies declarative FK actually prevents orphan fills (vs schema-only check).
    Requires PRAGMA foreign_keys = ON (default OFF в bare sqlite3.connect).
    """
    db_path = tmp_path / "test.db"
    init_db(db_path, MIG_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        conn.execute(
            """INSERT INTO trade_fills (
                parent_trade_id, exec_id, fill_qty, fill_price, fill_fee,
                fee_currency, is_partial, fill_ts, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                999999,  # non-existent parent
                "exec_orphan", "0.5", "100000", "0.05",
                "USDT", 0,
                "2026-04-25T12:00:00+00:00",
                "2026-04-25T12:00:01+00:00",
            ),
        )
        conn.commit()
