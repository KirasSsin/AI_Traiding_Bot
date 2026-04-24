"""Task 20: Coordinator.on_ws_reconnect — unified reconcile path.

ADR 0021 sub-decisions 1+2+3. Tests use real DB (pattern from test_halt_persistence.py).
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.execution.reconciler import LocalState, ReconcileResult
from src.execution.state_machine import ExecutionEvent, ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.platform.db import connect, init_db

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _seed_coord_at_state(tmp_path, state: ExecutionState, **row_overrides):
    """Build Coordinator + real repo seeded at a given state."""
    from src.execution.coordinator import Coordinator

    db_path = tmp_path / "coord.db"
    init_db(db_path, MIG_DIR)
    conn = connect(db_path)
    repo = ExecutionStateRepo(conn)

    base = dict(
        symbol="BTCUSDT",
        state=state,
        position_qty=Decimal("0"),
        entry_price=None,
        oco_main_order_id=None,
        bracket_id="abcdef12",
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=None,
        arming_started_at=None,
        last_attempt_num=0,
        updated_at=_now_iso(),
    )
    base.update(row_overrides)
    repo.upsert(ExecutionStateRow(**base))

    adapter = MagicMock()
    adapter.get_open_orders.return_value = []
    adapter.get_order_history.return_value = []
    reconciler = MagicMock()

    coord = Coordinator(
        adapter=adapter, repo=repo, reconciler=reconciler,
        symbol="BTCUSDT", base_coin="BTC",
    )
    return coord, repo, reconciler, adapter


# ---------------------------------------------------------------------------
# Test 1: HEAL_ENTRY_FILLED → LONG_OPEN
# ---------------------------------------------------------------------------

def test_on_ws_reconnect_heal_entry_filled_transitions_to_long_open(tmp_path):
    """ENTRY_PENDING + HEAL_ENTRY_FILLED verdict → state becomes LONG_OPEN."""
    coord, repo, reconciler, _ = _seed_coord_at_state(
        tmp_path,
        ExecutionState.ENTRY_PENDING,
        position_qty=Decimal("0"),
        expected_oco_qty=Decimal("0.001"),
    )
    reconciler.reconcile.return_value = ReconcileResult(
        verdict="HEAL_ENTRY_FILLED",
        exch_qty=Decimal("0.001"),
        entry_price=Decimal("62000"),
        halt_reason=None,
        heal_context={"avgPrice": "62000"},
    )

    coord.on_ws_reconnect()

    assert repo.get("BTCUSDT").state == ExecutionState.LONG_OPEN

    # Verify expected_state was passed to reconciler
    call_kwargs = reconciler.reconcile.call_args.kwargs
    assert call_kwargs.get("expected_state") == ExecutionState.ENTRY_PENDING


# ---------------------------------------------------------------------------
# Test 2: DIVERGENCE from ENTRY_PENDING → HALTED with halt_reason
# ---------------------------------------------------------------------------

def test_on_ws_reconnect_divergence_halts_with_reason(tmp_path):
    """ENTRY_PENDING + DIVERGENCE verdict → HALTED + halt_reason persisted."""
    coord, repo, reconciler, _ = _seed_coord_at_state(
        tmp_path,
        ExecutionState.ENTRY_PENDING,
    )
    reconciler.reconcile.return_value = ReconcileResult(
        verdict="DIVERGENCE",
        exch_qty=Decimal("0"),
        halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
        heal_context={"sub_reason": "test"},
    )

    coord.on_ws_reconnect()

    row = repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED
    assert row.halt_reason == "HALT_BOOTSTRAP_AMBIGUOUS"


# ---------------------------------------------------------------------------
# Test 3: EXITED from EXIT_PENDING → FLAT
# ---------------------------------------------------------------------------

def test_on_ws_reconnect_exited_from_exit_pending_transitions_to_flat(tmp_path):
    """EXIT_PENDING + EXITED verdict → state becomes FLAT."""
    coord, repo, reconciler, _ = _seed_coord_at_state(
        tmp_path,
        ExecutionState.EXIT_PENDING,
        position_qty=Decimal("0.001"),
    )
    reconciler.reconcile.return_value = ReconcileResult(
        verdict="EXITED",
        exch_qty=Decimal("0"),
        halt_reason=None,
        heal_context=None,
    )

    coord.on_ws_reconnect()

    assert repo.get("BTCUSDT").state == ExecutionState.FLAT


# ---------------------------------------------------------------------------
# Test 4: AGREE from OCO_ARMING → OCO_ARMED (RECONCILE_OK path)
# ---------------------------------------------------------------------------

def test_on_ws_reconnect_agree_from_oco_arming_transitions_to_oco_armed(tmp_path):
    """OCO_ARMING + AGREE verdict → RECONCILE_OK → OCO_ARMED."""
    coord, repo, reconciler, _ = _seed_coord_at_state(
        tmp_path,
        ExecutionState.OCO_ARMING,
        position_qty=Decimal("0.001"),
    )
    reconciler.reconcile.return_value = ReconcileResult(
        verdict="AGREE",
        exch_qty=Decimal("0.001"),
        entry_price=Decimal("60000"),
        halt_reason=None,
    )

    coord.on_ws_reconnect()

    assert repo.get("BTCUSDT").state == ExecutionState.OCO_ARMED


# ---------------------------------------------------------------------------
# Test 5: FLAT state → noop (reconciler not called)
# ---------------------------------------------------------------------------

def test_on_ws_reconnect_flat_state_is_noop(tmp_path):
    """FLAT is not reconcilable — reconciler.reconcile must NOT be called."""
    coord, repo, reconciler, _ = _seed_coord_at_state(
        tmp_path,
        ExecutionState.FLAT,
    )

    coord.on_ws_reconnect()

    reconciler.reconcile.assert_not_called()
    assert repo.get("BTCUSDT").state == ExecutionState.FLAT
