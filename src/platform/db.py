"""SQLite connection helpers + schema migrations."""

import re
import sqlite3
from pathlib import Path

# Allowlist for migration filenames — alphanumerics, dot, underscore, hyphen.
# Used by init_db() to gate filenames before f-string interpolation into the
# atomic tracking INSERT (executescript does not accept SQL parameters).
_MIGRATION_FILENAME_RE = re.compile(r"[A-Za-z0-9._-]+")



def connect(db_path: Path) -> sqlite3.Connection:
    """Open SQLite connection with sane defaults (WAL, foreign keys)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path, migrations_dir: Path) -> None:
    """Apply all `.sql` migrations in lexicographic order.

    Each migration body + its schema_migrations tracking row are applied as a
    single atomic transaction: either both commit or both roll back. Prevents
    partial application on crash (data-integrity review — ADR 0021 follow-up).
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(filename TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        conn.commit()
        applied = {
            row[0] for row in conn.execute("SELECT filename FROM schema_migrations").fetchall()
        }
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            if sql_file.name in applied:
                continue
            script_sql = sql_file.read_text(encoding="utf-8")
            # Inline tracking INSERT inside the migration transaction so both
            # commit atomically via executescript()'s BEGIN/COMMIT wrapper.
            # executescript() does not accept parameters, so the filename is
            # f-string-formatted; gate on a strict allowlist (alnum + ._-) to
            # block any SQL-injection vector through filename content.
            if not _MIGRATION_FILENAME_RE.fullmatch(sql_file.name):
                raise ValueError(
                    f"migration filename outside allowlist [A-Za-z0-9._-]: {sql_file.name!r}"
                )
            atomic_script = (
                "BEGIN;\n"
                f"{script_sql}\n"
                "INSERT INTO schema_migrations (filename, applied_at) "
                f"VALUES ('{sql_file.name}', datetime('now'));\n"
                "COMMIT;\n"
            )
            # executescript() runs within its own BEGIN/COMMIT scope; on
            # parse or execution error it rolls back automatically.
            conn.executescript(atomic_script)
    finally:
        conn.close()
