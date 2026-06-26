"""SQLite connection helpers + schema migrations."""

import re
import sqlite3
from pathlib import Path

# Allowlist for migration filenames — alphanumerics, dot, underscore, hyphen.
# Used by init_db() to gate filenames before f-string interpolation into the
# atomic tracking INSERT (executescript does not accept SQL parameters).
_MIGRATION_FILENAME_RE = re.compile(r"[A-Za-z0-9._-]+")

# Leading integer version prefix, e.g. "0006" in "0006_trade_fills.sql".
_MIGRATION_VERSION_RE = re.compile(r"^(\d+)_")


def _migration_sort_key(filename: str) -> tuple[int, str]:
    """Order migrations by parsed integer version, not raw string.

    Zero-padding is inconsistent across the set ("001_initial" vs
    "0006_trade_fills"), so lexicographic `sorted()` would place 4-digit
    versions before 3-digit ones ('0006...' < '001...') and could apply a
    FK-bearing migration before the table it references. Sorting on the parsed
    integer prefix yields dependency-respecting order regardless of padding;
    the raw filename is a deterministic tie-break for any colliding versions.
    Files without a leading-integer prefix sort last (version -> infinity).
    """
    match = _MIGRATION_VERSION_RE.match(filename)
    version = int(match.group(1)) if match else 2**63
    return (version, filename)


def connect(db_path: Path) -> sqlite3.Connection:
    """Open SQLite connection with sane defaults (WAL, foreign keys)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path, migrations_dir: Path) -> None:
    """Apply all `.sql` migrations in integer-version order.

    Files are ordered by their parsed leading integer prefix (see
    `_migration_sort_key`), NOT raw string — zero-padding is inconsistent
    across the set, so lexicographic sort would mis-order dependency-bearing
    migrations (a FK/index migration could run before its referenced table).

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
        migration_files = sorted(
            migrations_dir.glob("*.sql"), key=lambda p: _migration_sort_key(p.name)
        )
        # Deterministic-order assertion: dependency-bearing migrations must apply
        # in non-decreasing integer-version order (guards against silent return
        # to lexicographic ordering — DI-03).
        versions = [_migration_sort_key(p.name)[0] for p in migration_files]
        assert versions == sorted(versions), (
            "migrations not in integer-version order: " f"{[p.name for p in migration_files]}"
        )
        for sql_file in migration_files:
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
