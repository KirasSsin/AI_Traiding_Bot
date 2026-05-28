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
        assert {"halt_reason", "last_exit_reason", "last_reconcile_at", "bootstrap_at"}.issubset(
            cols
        ), f"missing halt persistence columns; got: {sorted(cols)}"
    finally:
        db.close()


def test_migration_0005_creates_halt_log_table(tmp_path):
    """halt_log table + composite index halt_log_symbol_ts."""
    db = sqlite3.connect(tmp_path / "test.db")
    try:
        _apply_migrations(db)
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "halt_log" in tables, f"halt_log table missing; got tables: {sorted(tables)}"
        indexes = {
            row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
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


# ---------------------------------------------------------------------------
# Task 9: _set_halt idempotency (ADR 0021 sub-decision 5 γ pattern)
# ---------------------------------------------------------------------------
import json
from decimal import Decimal

from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.platform.db import connect, init_db


def _now_iso_for_test() -> str:
    from datetime import UTC, datetime

    return datetime.now(tz=UTC).isoformat()


def _seed_repo(tmp_path) -> ExecutionStateRepo:
    """Build a repo with one BTCUSDT row in OCO_ARMING (the typical pre-halt state)."""
    db_path = tmp_path / "halt_test.db"
    init_db(db_path, MIG_DIR)
    conn = connect(db_path)
    repo = ExecutionStateRepo(conn)
    repo.upsert(
        ExecutionStateRow(
            symbol="BTCUSDT",
            state=ExecutionState.OCO_ARMING,
            position_qty=Decimal("0.001"),
            entry_price=Decimal("50000"),
            oco_main_order_id=None,
            bracket_id="abcdef12",
            oco_tp_order_id="oco-abcdef12-tp-1",
            oco_sl_order_id="oco-abcdef12-sl-1",
            expected_oco_qty=Decimal("0.001"),
            arming_started_at=_now_iso_for_test(),
            last_attempt_num=1,
            updated_at=_now_iso_for_test(),
        )
    )
    return repo


def test_set_halt_first_call_writes_column_and_log(tmp_path):
    repo = _seed_repo(tmp_path)
    repo._set_halt(
        symbol="BTCUSDT",
        reason="HALT_OCO_ARM_TIMEOUT",
        context={"state_at_halt": "OCO_ARMING", "position_qty": "0.001"},
    )
    row = repo.get("BTCUSDT")
    assert row is not None
    assert row.halt_reason == "HALT_OCO_ARM_TIMEOUT"
    log_rows = list(
        repo._conn.execute(
            "SELECT reason, context_json FROM halt_log WHERE symbol=?",
            ("BTCUSDT",),
        )
    )
    assert len(log_rows) == 1
    assert log_rows[0][0] == "HALT_OCO_ARM_TIMEOUT"
    assert json.loads(log_rows[0][1])["state_at_halt"] == "OCO_ARMING"


def test_set_halt_secondary_call_log_appends_primary_preserved(tmp_path):
    """ADR 0021 sub-decision 5: secondary halt appends log; halt_reason column unchanged."""
    repo = _seed_repo(tmp_path)
    repo._set_halt(
        symbol="BTCUSDT", reason="HALT_OCO_ARM_TIMEOUT", context={"state_at_halt": "OCO_ARMING"}
    )
    repo._set_halt(
        symbol="BTCUSDT", reason="HALT_RECONCILE_DIVERGENCE", context={"state_at_halt": "HALTED"}
    )
    row = repo.get("BTCUSDT")
    assert row is not None
    assert row.halt_reason == "HALT_OCO_ARM_TIMEOUT"  # primary wins
    log_rows = list(
        repo._conn.execute(
            "SELECT reason FROM halt_log WHERE symbol=? ORDER BY id",
            ("BTCUSDT",),
        )
    )
    assert [r[0] for r in log_rows] == ["HALT_OCO_ARM_TIMEOUT", "HALT_RECONCILE_DIVERGENCE"]


def test_set_halt_no_row_logs_only(tmp_path):
    """If no execution_state row exists yet, _set_halt still appends to halt_log (audit-first)."""
    db_path = tmp_path / "no_row.db"
    init_db(db_path, MIG_DIR)
    conn = connect(db_path)
    repo = ExecutionStateRepo(conn)
    repo._set_halt(
        symbol="ETHUSDT", reason="HALT_BOOTSTRAP_AMBIGUOUS", context={"sub_reason": "stale_age"}
    )
    log_rows = list(
        repo._conn.execute(
            "SELECT reason FROM halt_log WHERE symbol=?",
            ("ETHUSDT",),
        )
    )
    assert log_rows == [("HALT_BOOTSTRAP_AMBIGUOUS",)]


class _ExecuteSpyConn:
    """Proxy wrapping a real sqlite3.Connection, recording the order of executed SQL.

    sqlite3.Connection.execute is read-only (cannot monkeypatch), so the repo is
    constructed against this proxy. ``with conn:`` must keep transactional
    semantics, hence __enter__/__exit__ delegate to the wrapped connection.
    """

    def __init__(self, conn):
        self._conn = conn
        self.issued: list[str] = []

    def execute(self, sql, *args, **kwargs):
        self.issued.append(sql)
        return self._conn.execute(sql, *args, **kwargs)

    def __enter__(self):
        return self._conn.__enter__()

    def __exit__(self, *exc):
        return self._conn.__exit__(*exc)


def test_set_halt_audit_insert_before_state_update(tmp_path):
    """ADR 0021 sub-decision 5 (write-ahead audit): halt_log INSERT executes BEFORE
    the execution_state UPDATE within the same transaction.

    Guards against future split-txn refactor introducing an audit gap (UPDATE
    commits, INSERT lost). Verified by tracking the order of issued SQL statements.
    """
    seeded = _seed_repo(tmp_path)
    spy = _ExecuteSpyConn(seeded._conn)
    repo = ExecutionStateRepo(spy)  # type: ignore[arg-type]

    repo._set_halt(
        symbol="BTCUSDT",
        reason="HALT_OCO_ARM_TIMEOUT",
        context={"state_at_halt": "OCO_ARMING"},
    )

    insert_idx = next(i for i, s in enumerate(spy.issued) if "INSERT INTO halt_log" in s)
    update_idx = next(i for i, s in enumerate(spy.issued) if "UPDATE execution_state" in s)
    assert insert_idx < update_idx, (
        f"halt_log INSERT (idx {insert_idx}) must precede execution_state UPDATE "
        f"(idx {update_idx}) per write-ahead audit invariant; issued order: {spy.issued}"
    )


# ---------------------------------------------------------------------------
# Task 10: Coordinator persists halt_reason + context at HALT callsites
# ---------------------------------------------------------------------------
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

_REQUIRED_CTX_KEYS = (
    "state_at_halt",
    "position_qty",
    "oco_tp_id",
    "oco_sl_id",
    "expected_qty",
    "last_event",
    "last_attempt_num",
    "arming_started_at",
)


def _build_coord_in_oco_arming(tmp_path):
    """Construct Coordinator with a real repo seeded in OCO_ARMING."""
    from src.execution.coordinator import Coordinator

    db_path = tmp_path / "coord_halt.db"
    init_db(db_path, MIG_DIR)
    conn = connect(db_path)
    repo = ExecutionStateRepo(conn)
    started_at = (datetime.now(tz=UTC) - timedelta(seconds=120)).isoformat()  # >TTL
    repo.upsert(
        ExecutionStateRow(
            symbol="BTCUSDT",
            state=ExecutionState.OCO_ARMING,
            position_qty=Decimal("0.001"),
            entry_price=Decimal("50000"),
            oco_main_order_id=None,
            bracket_id="abcdef12",
            oco_tp_order_id="oco-abcdef12-tp-1",
            oco_sl_order_id="oco-abcdef12-sl-1",
            expected_oco_qty=Decimal("0.001"),
            arming_started_at=started_at,
            last_attempt_num=1,
            updated_at=_now_iso_for_test(),
        )
    )
    adapter = MagicMock()
    reconciler = MagicMock()
    coord = Coordinator(
        adapter=adapter,
        repo=repo,
        reconciler=reconciler,
        symbol="BTCUSDT",
        base_coin="BTC",
    )
    return coord, repo


def test_coordinator_arming_ttl_halt_persists_reason_and_context(tmp_path):
    """ADR 0021 sub-decision 5: BRACKET_TIMEOUT path persists HALT_OCO_ARM_TIMEOUT + full ctx."""
    coord, repo = _build_coord_in_oco_arming(tmp_path)
    coord.reconcile_arming_ttl(ttl_seconds=60)  # row's started_at is 120s ago
    row = repo.get("BTCUSDT")
    assert row is not None
    assert row.state == ExecutionState.HALTED
    assert row.halt_reason == "HALT_OCO_ARM_TIMEOUT"
    log_row = list(
        repo._conn.execute(
            "SELECT reason, context_json FROM halt_log " "WHERE symbol=? ORDER BY id DESC LIMIT 1",
            ("BTCUSDT",),
        )
    )[0]
    assert log_row[0] == "HALT_OCO_ARM_TIMEOUT"
    ctx = json.loads(log_row[1])
    for key in _REQUIRED_CTX_KEYS:
        assert key in ctx, f"missing required ctx key: {key}"
    assert ctx["state_at_halt"] == "OCO_ARMING"  # captured BEFORE FSM transition
    assert ctx["last_event"] == "BRACKET_TIMEOUT"
    assert ctx["last_attempt_num"] == 1
