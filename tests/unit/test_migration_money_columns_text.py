"""H7 (S49): money columns REAL -> TEXT (Decimal-as-TEXT precision rule).

Migration 004_money_columns_text.sql rebuilds orders/fills/positions so their
monetary columns are TEXT, matching the Decimal-as-TEXT convention used by every
other money table (trade_history, trade_fills, execution_state). Float storage
silently truncates values beyond IEEE-754 double precision.
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

from src.platform.db import connect, init_db

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"

# (table, money columns expected to be TEXT after migration 004)
_MONEY_COLUMNS = {
    "orders": {"orig_qty", "executed_qty", "price"},
    "fills": {"qty", "price", "fee"},
    "positions": {"qty", "avg_entry_price", "realized_pnl"},
}


def _column_types(conn: sqlite3.Connection, table: str) -> dict[str, str]:
    return {row[1]: row[2].upper() for row in conn.execute(f"PRAGMA table_info({table})")}


def test_migration_applies_cleanly_on_fresh_db(tmp_path) -> None:
    """Full migration chain applies without error and is re-runnable (idempotent)."""
    db_path = tmp_path / "money.db"
    init_db(db_path, MIG_DIR)
    init_db(db_path, MIG_DIR)  # second run must be a no-op (already tracked)
    conn = connect(db_path)
    try:
        applied = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations")}
        assert "004_money_columns_text.sql" in applied
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"orders", "fills", "positions"}.issubset(tables)
    finally:
        conn.close()


def test_money_columns_are_text_after_migration(tmp_path) -> None:
    """orders/fills/positions money columns declared TEXT (not REAL)."""
    db_path = tmp_path / "money.db"
    init_db(db_path, MIG_DIR)
    conn = connect(db_path)
    try:
        for table, money_cols in _MONEY_COLUMNS.items():
            types = _column_types(conn, table)
            for col in money_cols:
                assert col in types, f"{table}.{col} missing"
                assert (
                    types[col] == "TEXT"
                ), f"{table}.{col} declared {types[col]}, expected TEXT (Decimal-as-TEXT)"
    finally:
        conn.close()


def test_decimal_text_roundtrips_exact_for_orders(tmp_path) -> None:
    """A Decimal beyond double precision round-trips losslessly via TEXT columns."""
    db_path = tmp_path / "money.db"
    init_db(db_path, MIG_DIR)
    conn = connect(db_path)
    try:
        qty = Decimal("0.123456789012345678")  # > IEEE-754 double precision
        price = Decimal("65432.10")
        conn.execute(
            "INSERT INTO orders (client_order_id, symbol, side, type, status, "
            "orig_qty, executed_qty, price, created_at, updated_at) "
            "VALUES (?, ?, 'BUY', 'LIMIT', 'NEW', ?, '0', ?, ?, ?)",
            (
                "ord-1",
                "BTCUSDT",
                str(qty),
                str(price),
                "2026-05-29T00:00:00+00:00",
                "2026-05-29T00:00:00+00:00",
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT orig_qty, price FROM orders WHERE client_order_id='ord-1'"
        ).fetchone()
        assert Decimal(row[0]) == qty
        assert Decimal(row[1]) == price
    finally:
        conn.close()


def test_decimal_text_roundtrips_exact_for_fills_and_positions(tmp_path) -> None:
    """fills + positions money columns round-trip Decimal-as-TEXT exactly."""
    db_path = tmp_path / "money.db"
    init_db(db_path, MIG_DIR)
    conn = connect(db_path)
    try:
        conn.execute(
            "INSERT INTO orders (client_order_id, symbol, side, type, status, "
            "orig_qty, executed_qty, price, created_at, updated_at) "
            "VALUES ('ord-f', 'BTCUSDT', 'BUY', 'MARKET', 'FILLED', '1', '1', NULL, "
            "'2026-05-29T00:00:00+00:00', '2026-05-29T00:00:00+00:00')"
        )
        fee = Decimal("0.000000012345678901")
        conn.execute(
            "INSERT INTO fills (client_order_id, trade_id, qty, price, fee, fee_asset, "
            "is_maker, filled_at) VALUES ('ord-f', 1, ?, ?, ?, 'USDT', 0, ?)",
            (str(Decimal("0.001")), str(Decimal("50000.5")), str(fee), "2026-05-29T00:00:00+00:00"),
        )
        pnl = Decimal("-123.456789012345678")
        conn.execute(
            "INSERT INTO positions (position_id, symbol, side, qty, avg_entry_price, "
            "opened_at, realized_pnl) VALUES ('pos-1', 'BTCUSDT', 'LONG', ?, ?, ?, ?)",
            (str(Decimal("0.001")), str(Decimal("50000.5")), "2026-05-29T00:00:00+00:00", str(pnl)),
        )
        conn.commit()

        f = conn.execute("SELECT qty, price, fee FROM fills WHERE trade_id=1").fetchone()
        assert Decimal(f[2]) == fee
        p = conn.execute("SELECT realized_pnl FROM positions WHERE position_id='pos-1'").fetchone()
        assert Decimal(p[0]) == pnl
    finally:
        conn.close()
