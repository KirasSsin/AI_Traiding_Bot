"""Tests for Reconciler.reconcile diff logic (Sprint 5 Task 7).

ADR ref: wiki/project/decisions/0019-sprint-5-execution-decisions.md sub-decision 3
"""
import pytest
pytestmark = pytest.mark.skip(reason="ADR 0020 sub-decision 4: Reconciler Protocol rewritten (get_position removed); S5 tests superseded by test_reconciler_wallet_protocol.py + test_reconciler_fetch_v2.py + test_reconciler_entry_price.py. Preserved for history.")

from decimal import Decimal
from unittest.mock import Mock

try:
    from src.execution.reconciler import (
        Reconciler,
        ReconcileVerdict,
    )
    from src.execution.state_machine import ExecutionState
    from src.execution.state_repo import ExecutionStateRow
except ImportError:
    Reconciler = ReconcileVerdict = ExecutionState = ExecutionStateRow = None  # type: ignore[assignment,misc]


def _row(state, qty="0", oco_id=None, entry=None):
    return ExecutionStateRow(
        symbol="BTCUSDT",
        state=state,
        position_qty=Decimal(qty),
        entry_price=Decimal(entry) if entry else None,
        oco_main_order_id=oco_id,
        updated_at="2026-04-23T10:00:00+00:00",
    )


def _client_flat():
    c = Mock()
    c.get_open_orders.return_value = []
    c.get_position.return_value = None
    return c


def _client_with_position(qty="0.5", avg="70000", oco_id="abc123"):
    c = Mock()
    c.get_open_orders.return_value = [{
        "orderId": oco_id,
        "side": "Sell",
        "orderType": "Market",
        "qty": qty,
        "price": "0",
        "takeProfit": "75000",
        "stopLoss": "65000",
        "orderLinkId": "client-1",
    }]
    c.get_position.return_value = {"size": qty, "avgPrice": avg}
    return c


# Case 1: no local row
def test_reconcile_no_local_exchange_flat_ok():
    r = Reconciler(_client_flat()).reconcile("BTCUSDT", None)
    assert r.verdict == ReconcileVerdict.OK
    assert r.local_row is None


def test_reconcile_no_local_exchange_has_position_divergence():
    r = Reconciler(_client_with_position()).reconcile("BTCUSDT", None)
    assert r.verdict == ReconcileVerdict.DIVERGENCE
    assert "no local state" in r.detail


# Case 2: local flat-equivalent
def test_reconcile_local_flat_exchange_flat_ok():
    r = Reconciler(_client_flat()).reconcile("BTCUSDT", _row(ExecutionState.FLAT))
    assert r.verdict == ReconcileVerdict.OK


def test_reconcile_local_init_exchange_flat_ok():
    r = Reconciler(_client_flat()).reconcile("BTCUSDT", _row(ExecutionState.INIT))
    assert r.verdict == ReconcileVerdict.OK


def test_reconcile_local_cooldown_exchange_flat_ok():
    r = Reconciler(_client_flat()).reconcile("BTCUSDT", _row(ExecutionState.COOLDOWN))
    assert r.verdict == ReconcileVerdict.OK


def test_reconcile_local_flat_but_exchange_has_position_divergence():
    r = Reconciler(_client_with_position()).reconcile(
        "BTCUSDT", _row(ExecutionState.FLAT)
    )
    assert r.verdict == ReconcileVerdict.DIVERGENCE
    assert "qty=0.5" in r.detail


# Case 3: local active position
def test_reconcile_local_oco_armed_matches_exchange_ok():
    r = Reconciler(_client_with_position(qty="0.5", oco_id="abc123")).reconcile(
        "BTCUSDT",
        _row(ExecutionState.OCO_ARMED, qty="0.5", oco_id="abc123"),
    )
    assert r.verdict == ReconcileVerdict.OK


def test_reconcile_qty_mismatch_beyond_eps_divergence():
    r = Reconciler(_client_with_position(qty="0.5", oco_id="abc123")).reconcile(
        "BTCUSDT",
        _row(ExecutionState.OCO_ARMED, qty="0.4", oco_id="abc123"),
    )
    assert r.verdict == ReconcileVerdict.DIVERGENCE
    assert "qty mismatch" in r.detail


def test_reconcile_qty_within_eps_ok():
    # diff = 1e-9 < 1e-8 eps
    r = Reconciler(_client_with_position(qty="0.500000001", oco_id="abc123")).reconcile(
        "BTCUSDT",
        _row(ExecutionState.OCO_ARMED, qty="0.500000000", oco_id="abc123"),
    )
    assert r.verdict == ReconcileVerdict.OK


def test_reconcile_oco_order_missing_on_exchange_divergence():
    # Exchange has different orderId
    c = _client_with_position(qty="0.5", oco_id="other-id")
    r = Reconciler(c).reconcile(
        "BTCUSDT",
        _row(ExecutionState.OCO_ARMED, qty="0.5", oco_id="abc123"),
    )
    assert r.verdict == ReconcileVerdict.DIVERGENCE
    assert "abc123" in r.detail
    assert "missing" in r.detail


def test_reconcile_long_open_no_oco_yet_qty_match_ok():
    # local in LONG_OPEN (oco not placed yet) — only qty must match
    c = Mock()
    c.get_open_orders.return_value = []
    c.get_position.return_value = {"size": "0.5", "avgPrice": "70000"}
    r = Reconciler(c).reconcile(
        "BTCUSDT",
        _row(ExecutionState.LONG_OPEN, qty="0.5", oco_id=None),
    )
    assert r.verdict == ReconcileVerdict.OK
