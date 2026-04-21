"""SQLite connection helpers + schema migrations."""

import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    """Open SQLite connection with sane defaults (WAL, foreign keys)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path, migrations_dir: Path) -> None:
    """Apply all `.sql` migrations in lexicographic order. Idempotent."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(filename TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        applied = {
            row[0] for row in conn.execute("SELECT filename FROM schema_migrations").fetchall()
        }
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            if sql_file.name in applied:
                continue
            with sql_file.open("r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.execute(
                "INSERT INTO schema_migrations (filename, applied_at) VALUES (?, datetime('now'))",
                (sql_file.name,),
            )
            conn.commit()
    finally:
        conn.close()
