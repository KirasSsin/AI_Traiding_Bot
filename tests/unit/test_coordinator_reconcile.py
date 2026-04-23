"""Tests for Coordinator.handle_ws_reconnect (Sprint 5 Task 8).

SUPERSEDED by Sprint 6 Task 22 bootstrap (ADR 0020 sub-decision 4 rewrote Reconciler API).
Kept for git history; skipped at collection.
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.skip(
    reason="superseded by Sprint 6 Task 22 bootstrap; legacy S5 Reconciler API removed"
)

try:
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import (
        ExchangeState,
        OpenOrderSnapshot,
        PositionSnapshot,
        ReconcileResult,
        ReconcileVerdict,
    )
    from src.execution.state_machine import ExecutionState
    from src.execution.state_repo import ExecutionStateRow
except ImportError:
    pass


def _row(state, qty="0.5", oco_id="abc123", entry="70000"):
    return ExecutionStateRow(
        symbol="BTCUSDT",
        state=state,
        position_qty=Decimal(qty),
        entry_price=Decimal(entry),
        oco_main_order_id=oco_id,
        updated_at="2026-04-23T10:00:00+00:00",
    )


def _exchange_with_position(qty="0.5", oco_id="abc123", entry="70000"):
    return ExchangeState(
        symbol="BTCUSDT",
        open_orders=(
            OpenOrderSnapshot(
                order_id=oco_id, side="Sell", order_type="Market",
                qty=Decimal(qty), price=None,
                take_profit=Decimal("75000"), stop_loss=Decimal("65000"),
                order_link_id="client-1",
            ),
        ),
        position=PositionSnapshot(
            symbol="BTCUSDT", qty=Decimal(qty), avg_price=Decimal(entry),
        ),
    )


def _exchange_flat():
    return ExchangeState(
        symbol="BTCUSDT", open_orders=(),
        position=PositionSnapshot(symbol="BTCUSDT", qty=Decimal("0"), avg_price=None),
    )


def test_ws_reconnect_oco_armed_ok_returns_to_oco_armed():
    repo = MagicMock()
    repo.get.return_value = _row(ExecutionState.OCO_ARMED)
    rec = MagicMock()
    rec.reconcile.return_value = ReconcileResult(
        ReconcileVerdict.OK, _exchange_with_position(), repo.get.return_value, "ok"
    )

    coord = Coordinator(repo=repo, reconciler=rec, symbol="BTCUSDT")
    final = coord.handle_ws_reconnect()

    assert final == ExecutionState.OCO_ARMED
    rec.reconcile.assert_called_once_with("BTCUSDT", repo.get.return_value)
    assert repo.upsert.called
    persisted = repo.upsert.call_args.args[0]
    assert persisted.state == ExecutionState.OCO_ARMED
    assert persisted.position_qty == Decimal("0.5")
    assert persisted.oco_main_order_id == "abc123"


def test_ws_reconnect_divergence_goes_to_halted():
    repo = MagicMock()
    repo.get.return_value = _row(ExecutionState.OCO_ARMED, qty="0.5")
    rec = MagicMock()
    ex = _exchange_with_position(qty="0.3")
    rec.reconcile.return_value = ReconcileResult(
        ReconcileVerdict.DIVERGENCE, ex, repo.get.return_value, "qty mismatch"
    )

    coord = Coordinator(repo=repo, reconciler=rec, symbol="BTCUSDT")
    final = coord.handle_ws_reconnect()

    assert final == ExecutionState.HALTED
    persisted = repo.upsert.call_args.args[0]
    assert persisted.state == ExecutionState.HALTED
    assert persisted.position_qty == Decimal("0.3")


def test_ws_reconnect_when_flat_short_circuits_no_reconcile():
    repo = MagicMock()
    repo.get.return_value = _row(ExecutionState.FLAT, qty="0", oco_id=None, entry="0")
    rec = MagicMock()

    coord = Coordinator(repo=repo, reconciler=rec, symbol="BTCUSDT")
    final = coord.handle_ws_reconnect()

    assert final == ExecutionState.FLAT
    rec.reconcile.assert_not_called()
    repo.upsert.assert_not_called()


def test_ws_reconnect_when_no_local_row_returns_init_no_reconcile():
    repo = MagicMock()
    repo.get.return_value = None
    rec = MagicMock()

    coord = Coordinator(repo=repo, reconciler=rec, symbol="BTCUSDT")
    final = coord.handle_ws_reconnect()

    assert final == ExecutionState.INIT
    rec.reconcile.assert_not_called()
    repo.upsert.assert_not_called()


def test_ws_reconnect_long_open_ok_returns_to_oco_armed():
    """LONG_OPEN → RECONCILING → OCO_ARMED on RECONCILE_OK (per FSM table)."""
    repo = MagicMock()
    repo.get.return_value = _row(ExecutionState.LONG_OPEN, qty="0.5", oco_id=None)
    rec = MagicMock()
    ex = ExchangeState(
        symbol="BTCUSDT", open_orders=(),
        position=PositionSnapshot(
            symbol="BTCUSDT", qty=Decimal("0.5"), avg_price=Decimal("70000"),
        ),
    )
    rec.reconcile.return_value = ReconcileResult(
        ReconcileVerdict.OK, ex, repo.get.return_value, "ok"
    )

    coord = Coordinator(repo=repo, reconciler=rec, symbol="BTCUSDT")
    final = coord.handle_ws_reconnect()

    assert final == ExecutionState.OCO_ARMED
    persisted = repo.upsert.call_args.args[0]
    assert persisted.oco_main_order_id is None
    assert persisted.position_qty == Decimal("0.5")
    assert persisted.entry_price == Decimal("70000")


def test_ws_reconnect_partial_fill_divergence_to_halted():
    repo = MagicMock()
    repo.get.return_value = _row(ExecutionState.PARTIAL_FILL, qty="0.5")
    rec = MagicMock()
    ex = _exchange_flat()
    rec.reconcile.return_value = ReconcileResult(
        ReconcileVerdict.DIVERGENCE, ex, repo.get.return_value,
        "local PARTIAL_FILL but exchange flat",
    )

    coord = Coordinator(repo=repo, reconciler=rec, symbol="BTCUSDT")
    final = coord.handle_ws_reconnect()

    assert final == ExecutionState.HALTED
    persisted = repo.upsert.call_args.args[0]
    assert persisted.state == ExecutionState.HALTED
    assert persisted.position_qty == Decimal("0")
    assert persisted.entry_price is None
    assert persisted.oco_main_order_id is None
