"""Invariant: every halt-class ReasonCode is wired in Coordinator.request_halt.

Sprint 8b T7 (ADR 0023). Failure surface when a new HALT_* / KILL_SWITCH_*
code in the allow-list below is not dispatched correctly by Coordinator.

Selection rule (allow-list): codes that enter via Coordinator.request_halt
(operator/runtime-initiated). FSM-internal halts (drawdown, flash crash,
bracket lifecycle, reconcile divergence) are excluded — they hit _set_halt
directly inside on_ws_reconnect / risk handlers / etc.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.platform.db import init_db
from src.risk.reason_codes import ReasonCode

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


# Allow-list of halt-class ReasonCode that flow through Coordinator.request_halt.
# Per ADR 0023: each entry MUST have explicit dispatch branch in request_halt.
_REQUEST_HALT_CODES = frozenset({
    ReasonCode.KILL_SWITCH_REQUESTED,
    ReasonCode.HALT_RUNTIME_CRASH,
    ReasonCode.HALT_BAR_POLL_STALL,
})


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _build(tmp_path, *, initial_state: ExecutionState = ExecutionState.FLAT):
    """Build Coordinator + repo with a real DB seeded in given state.

    Mirrors tests/unit/test_coordinator_request_halt.py::_build (DAMP for tests).
    """
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


@pytest.mark.parametrize(
    "code",
    sorted(_REQUEST_HALT_CODES, key=lambda rc: rc.name),
    ids=lambda rc: rc.name,
)
def test_request_halt_dispatches_every_allow_listed_code(code, tmp_path):
    """Every code in _REQUEST_HALT_CODES lands FSM in HALTED with matching halt_reason.

    If this test fails for an existing code, the dispatch branch in
    Coordinator.request_halt is broken — see ADR 0023.

    If a new HALT_* / KILL_SWITCH_* code is added that flows through
    request_halt, the dev MUST add it to _REQUEST_HALT_CODES above AND
    add the explicit dispatch branch in coordinator. Reviewer prompt
    CRITICAL section (ADR 0023) is the human gate; this test is the
    mechanical gate for the existing allow-list.
    """
    coord, repo, _ = _build(tmp_path, initial_state=ExecutionState.FLAT)
    coord.request_halt(code)
    row = repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED, (
        f"ReasonCode {code.name} did not transition FSM to HALTED — "
        f"got state={row.state.name}; missing dispatch in Coordinator.request_halt? "
        "See ADR 0023."
    )
    assert row.halt_reason == code.value, (
        f"halt_reason={row.halt_reason!r} != expected={code.value!r}"
    )
