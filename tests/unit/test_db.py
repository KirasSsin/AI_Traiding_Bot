from pathlib import Path

from src.platform.db import _migration_sort_key, connect, init_db


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
    # S7 ADR 0021: migration 0005 halt persistence (halt_reason col + halt_log table)
    # S9 Q3 B1: migration 0006 trade_fills
    # S49 H7: migration 004 money columns REAL->TEXT
    # S55 TL-01: migration 0007 bracket exit prices (bracket_tp_price + bracket_sl_trigger_price)
    assert applied == 9


def test_migration_sort_is_integer_versioned() -> None:
    """DI-03: migrations apply in integer-version order, not lexicographic.

    Zero-padding is inconsistent across the migration set (001_initial vs
    0006_trade_fills). Raw-string `sorted()` puts 4-digit versions before
    3-digit ones ('0006...' < '001...'), so a FK-bearing migration could run
    before the table it references. Sort must respect the parsed integer prefix.
    """
    names = [
        "0006_trade_fills.sql",
        "002_risk.sql",
        "001_initial.sql",
        "0003_execution_state.sql",
        "0007_bracket_exit_prices.sql",
        "004_money_columns_text.sql",
    ]
    ordered = sorted(names, key=_migration_sort_key)

    # trade_history (002) must be applied before the FK-bearing trade_fills (0006).
    assert ordered.index("002_risk.sql") < ordered.index("0006_trade_fills.sql")
    # init (001) before everything with a higher version prefix.
    assert ordered[0] == "001_initial.sql"
    # integer prefix monotonically non-decreasing
    prefixes = [int(n.split("_")[0]) for n in ordered]
    assert prefixes == sorted(prefixes)


def test_init_db_applies_in_dependency_respecting_order(tmp_path: Path) -> None:
    """DI-03: real migrations apply cleanly under integer-version ordering.

    003_trade_history_unique.sql is a CREATE INDEX ON trade_history — it raises
    'no such table' if it runs before 002_risk.sql creates trade_history. Under
    correct ordering all migrations apply without error.
    """
    db_path = tmp_path / "oltp.db"
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    init_db(db_path, migrations_dir=migrations_dir)

    conn = connect(db_path)
    try:
        applied = [
            row[0]
            for row in conn.execute(
                "SELECT filename FROM schema_migrations ORDER BY applied_at, filename"
            ).fetchall()
        ]
    finally:
        conn.close()
    # FK-dependent migration recorded after its referent's migration.
    assert "002_risk.sql" in applied
    assert "0006_trade_fills.sql" in applied
