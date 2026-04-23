from pathlib import Path

from src.platform.db import connect, init_db


def test_init_db_creates_all_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "oltp.db"
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    init_db(db_path, migrations_dir=migrations_dir)

    conn = connect(db_path)
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cur.fetchall()}
    finally:
        conn.close()

    expected = {
        "orders",
        "fills",
        "positions",
        "events",
        "runs",
        "config",
        "state",
        "audit_index",
        "schema_migrations",
    }
    assert expected <= tables, f"missing tables: {expected - tables}"


def test_wal_mode_enabled(tmp_path: Path) -> None:
    db_path = tmp_path / "oltp.db"
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    init_db(db_path, migrations_dir=migrations_dir)

    conn = connect(db_path)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    assert mode.lower() == "wal"


def test_init_db_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "oltp.db"
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    init_db(db_path, migrations_dir=migrations_dir)
    init_db(db_path, migrations_dir=migrations_dir)
    conn = connect(db_path)
    try:
        applied = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    finally:
        conn.close()
    assert applied == 5
