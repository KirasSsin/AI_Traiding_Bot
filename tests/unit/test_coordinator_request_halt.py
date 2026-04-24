"""Coordinator.request_halt(reason) — public halt entry-point used by RuntimeManager.

ADR 0022 sub-decisions 5/6/11. Wraps existing _set_halt (S7 γ-pattern):
- halt_reason column: primary-wins (first non-null write only)
- halt_log audit table: always appends every call
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.platform.db import init_db
from src.risk.reason_codes import ReasonCode

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _build(tmp_path, *, initial_state: ExecutionState = ExecutionState.FLAT):
    """Build Coordinator + repo with a real DB seeded in given state."""
    db_path = tmp_path / "rh.db"
    init_db(db_path, MIG_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    repo = ExecutionStateRepo(conn)
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT",
        state=initial_state,
        position_qty=Decimal("0"),
        entry_price=None,
        oco_main_order_id=None,
        bracket_id=None,
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=None,
        arming_started_at=None,
        last_attempt_num=0,
        updated_at=_now_iso(),
    ))
    coord = Coordinator(
        adapter=MagicMock(),
        repo=repo,
        reconciler=MagicMock(),
        symbol="BTCUSDT",
        base_coin="BTC",
    )
    coord._bootstrap_done = True
    return coord, repo, db_path


def test_request_halt_sets_halt_reason(tmp_path):
    """First request_halt writes halt_reason column."""
    coord, repo, _ = _build(tmp_path)
    coord.request_halt(ReasonCode.KILL_SWITCH_REQUESTED)
    row = repo.get("BTCUSDT")
    assert row.halt_reason == "KILL_SWITCH_REQUESTED"


def test_request_halt_primary_wins_does_not_overwrite(tmp_path):
    """ADR 0021 γ-rule: first halt_reason wins, subsequent calls leave column unchanged."""
    coord, repo, _ = _build(tmp_path, initial_state=ExecutionState.LONG_OPEN)
    coord.request_halt(ReasonCode.HALT_RUNTIME_CRASH)
    coord.request_halt(ReasonCode.KILL_SWITCH_REQUESTED)
    row = repo.get("BTCUSDT")
    assert row.halt_reason == "HALT_RUNTIME_CRASH", "primary halt_reason must not be overwritten"


def test_request_halt_appends_to_halt_log(tmp_path):
    """halt_log audit table always appends — both calls land as separate rows."""
    coord, _, db_path = _build(tmp_path, initial_state=ExecutionState.LONG_OPEN)
    coord.request_halt(ReasonCode.HALT_RUNTIME_CRASH)
    coord.request_halt(ReasonCode.HALT_BAR_POLL_STALL)
    audit_conn = sqlite3.connect(str(db_path))
    rows = audit_conn.execute(
        "SELECT reason FROM halt_log WHERE symbol='BTCUSDT' ORDER BY id"
    ).fetchall()
    audit_conn.close()
    reasons = [r[0] for r in rows]
    assert "HALT_RUNTIME_CRASH" in reasons
    assert "HALT_BAR_POLL_STALL" in reasons
    assert len(reasons) == 2, f"expected 2 audit rows, got {len(reasons)}"


# === S8b T1: FSM-transition tests (RED before fix, GREEN after) ===


def test_request_halt_kill_switch_transitions_to_halted(tmp_path):
    """KILL_SWITCH_REQUESTED dispatches KILL_SWITCH_REQUESTED event → HALTED."""
    coord, repo, _ = _build(tmp_path, initial_state=ExecutionState.FLAT)
    coord.request_halt(ReasonCode.KILL_SWITCH_REQUESTED)
    row = repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED
    assert row.halt_reason == ReasonCode.KILL_SWITCH_REQUESTED.value


def test_request_halt_runtime_crash_transitions_to_halted(tmp_path):
    """HALT_RUNTIME_CRASH dispatches RISK_HALT event → HALTED."""
    coord, repo, _ = _build(tmp_path, initial_state=ExecutionState.LONG_OPEN)
    coord.request_halt(ReasonCode.HALT_RUNTIME_CRASH)
    row = repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED
    assert row.halt_reason == ReasonCode.HALT_RUNTIME_CRASH.value


def test_request_halt_bar_poll_stall_transitions_to_halted(tmp_path):
    """HALT_BAR_POLL_STALL dispatches RISK_HALT event → HALTED."""
    coord, repo, _ = _build(tmp_path, initial_state=ExecutionState.OCO_ARMED)
    coord.request_halt(ReasonCode.HALT_BAR_POLL_STALL)
    row = repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED
    assert row.halt_reason == ReasonCode.HALT_BAR_POLL_STALL.value


def test_request_halt_idempotent_when_already_halted(tmp_path):
    """Second request_halt keeps primary halt_reason (S7 γ) and stays HALTED."""
    coord, repo, _ = _build(tmp_path, initial_state=ExecutionState.FLAT)
    coord.request_halt(ReasonCode.KILL_SWITCH_REQUESTED)
    coord.request_halt(ReasonCode.HALT_RUNTIME_CRASH)
    row = repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED
    # primary-wins per S7 γ — first non-null halt_reason sticks
    assert row.halt_reason == ReasonCode.KILL_SWITCH_REQUESTED.value
