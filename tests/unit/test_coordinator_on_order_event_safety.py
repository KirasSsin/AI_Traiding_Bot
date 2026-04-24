"""Sprint 6 trading-logic-reviewer blockers #1 + #2 — on_order_event production-safety.

Blocker #1: ENTRY_FILLED handler missing → FSM stuck at ENTRY_PENDING; arm_oco unreachable.
Blocker #2: WS event ordering races raise IllegalTransitionError, killing the worker.

These tests establish on_order_event invariants:
  - Entry Filled event drives ENTRY_PENDING → LONG_OPEN (Blocker #1).
  - Entry PartiallyFilled is a no-op (spot Market entries fill atomically; defensive).
  - Events for non-bracket orderLinkIds (no oco- prefix) are ignored cleanly.
  - Late / out-of-order events arriving in a terminal or post-routed state
    (FLAT, HALTED, EXIT_SIBLING_CANCELLING, EXIT_SL_RESIDUAL) do NOT raise.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow

BRACKET_ID = "abcd1234"
ENTRY_LID = f"oco-{BRACKET_ID}-entry-1"
TP_LID = f"oco-{BRACKET_ID}-tp-1"
SL_LID = f"oco-{BRACKET_ID}-sl-1"


def _seed(repo: ExecutionStateRepo, *, state: ExecutionState,
          tp_oid: str | None = "TP-OID", sl_oid: str | None = "SL-OID") -> None:
    now = datetime.now(tz=UTC).isoformat()
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT",
        state=state,
        position_qty=Decimal("0.001"),
        entry_price=Decimal("65000"),
        oco_main_order_id=None,
        bracket_id=BRACKET_ID,
        oco_tp_order_id=tp_oid,
        oco_sl_order_id=sl_oid,
        expected_oco_qty=Decimal("0.001"),
        arming_started_at=None,
        last_attempt_num=1,
        updated_at=now,
    ))


class _StubAdapter:
    def __init__(self) -> None:
        self.cancels: list[str] = []

    def cancel_order(self, *, symbol: str, order_id: str):  # noqa: D401
        self.cancels.append(order_id)
        from types import SimpleNamespace
        return SimpleNamespace(cancelled=True, reason_code=None)


def _make_coordinator(tmp_path: Path) -> tuple[Coordinator, ExecutionStateRepo, _StubAdapter]:
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    adapter = _StubAdapter()
    coord = Coordinator(adapter=adapter, repo=repo, reconciler=None,
                        symbol="BTCUSDT", base_coin="BTC")
    coord._bootstrap_done = True  # tests pre-date Task 22 guard; bypass for routing tests
    return coord, repo, adapter


# --- Blocker #1: ENTRY_FILLED handler --------------------------------------

def test_entry_filled_transitions_to_long_open(tmp_path):
    coord, repo, _ = _make_coordinator(tmp_path)
    _seed(repo, state=ExecutionState.ENTRY_PENDING, tp_oid=None, sl_oid=None)
    coord.on_order_event({
        "orderLinkId": ENTRY_LID,
        "orderStatus": "Filled",
        "cumExecQty": "0.001",
    })
    assert repo.get("BTCUSDT").state == ExecutionState.LONG_OPEN


def test_entry_partially_filled_is_noop(tmp_path):
    coord, repo, _ = _make_coordinator(tmp_path)
    _seed(repo, state=ExecutionState.ENTRY_PENDING, tp_oid=None, sl_oid=None)
    coord.on_order_event({
        "orderLinkId": ENTRY_LID,
        "orderStatus": "PartiallyFilled",
        "cumExecQty": "0.0005",
    })
    assert repo.get("BTCUSDT").state == ExecutionState.ENTRY_PENDING


def test_unknown_link_id_ignored(tmp_path):
    coord, repo, _ = _make_coordinator(tmp_path)
    _seed(repo, state=ExecutionState.OCO_ARMED)
    coord.on_order_event({
        "orderLinkId": "manual-cancel-foo",
        "orderStatus": "Filled",
    })
    assert repo.get("BTCUSDT").state == ExecutionState.OCO_ARMED


# --- Blocker #2: late / out-of-order WS events do not crash ----------------

def test_partial_fill_after_flat_does_not_raise(tmp_path):
    """Late SL PartiallyFilled echo arrives after sibling-cancel landed in FLAT.

    Must NOT raise IllegalTransitionError(FLAT, PARTIAL_FILL).
    """
    coord, repo, _ = _make_coordinator(tmp_path)
    _seed(repo, state=ExecutionState.FLAT)
    coord.on_order_event({
        "orderLinkId": SL_LID,
        "orderStatus": "PartiallyFilled",
        "leavesQty": "0.0001",
    })
    assert repo.get("BTCUSDT").state == ExecutionState.FLAT


def test_sl_triggered_in_exit_sl_residual_does_not_raise(tmp_path):
    """Triggered echo arrives after PartiallyFilled already routed us to EXIT_SL_RESIDUAL.

    Must NOT raise IllegalTransitionError(EXIT_SL_RESIDUAL, SL_TRIGGERED).
    """
    coord, repo, _ = _make_coordinator(tmp_path)
    _seed(repo, state=ExecutionState.EXIT_SL_RESIDUAL)
    coord.on_order_event({
        "orderLinkId": SL_LID,
        "orderStatus": "Triggered",
    })
    assert repo.get("BTCUSDT").state == ExecutionState.EXIT_SL_RESIDUAL


def test_tp_filled_in_halted_does_not_raise(tmp_path):
    """Late TP Fill echo after the bracket already halted (e.g. arming TTL).

    Must NOT raise IllegalTransitionError(HALTED, TP_HIT).
    """
    coord, repo, _ = _make_coordinator(tmp_path)
    _seed(repo, state=ExecutionState.HALTED)
    coord.on_order_event({
        "orderLinkId": TP_LID,
        "orderStatus": "Filled",
    })
    assert repo.get("BTCUSDT").state == ExecutionState.HALTED


def test_sl_triggered_in_exit_sibling_cancelling_does_not_raise(tmp_path):
    """Duplicate SL Triggered echo while we are already cancelling the sibling.

    Must NOT raise IllegalTransitionError(EXIT_SIBLING_CANCELLING, SL_TRIGGERED).
    """
    coord, repo, _ = _make_coordinator(tmp_path)
    _seed(repo, state=ExecutionState.EXIT_SIBLING_CANCELLING)
    coord.on_order_event({
        "orderLinkId": SL_LID,
        "orderStatus": "Triggered",
    })
    assert repo.get("BTCUSDT").state == ExecutionState.EXIT_SIBLING_CANCELLING
