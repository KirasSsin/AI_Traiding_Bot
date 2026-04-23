"""Tests for Reconciler.fetch_exchange_state (Sprint 5 Task 6).

ADR ref: wiki/project/decisions/0019-sprint-5-execution-decisions.md sub-decision 3
"""
import pytest
pytestmark = pytest.mark.skip(reason="ADR 0020 sub-decision 4: Reconciler Protocol rewritten (get_position removed); S5 tests superseded by test_reconciler_wallet_protocol.py + test_reconciler_fetch_v2.py + test_reconciler_entry_price.py. Preserved for history.")

from decimal import Decimal
from unittest.mock import Mock

try:
    from src.execution.reconciler import (
        ExchangeState,
        OpenOrderSnapshot,
        PositionSnapshot,
        Reconciler,
    )
except ImportError:
    ExchangeState = OpenOrderSnapshot = PositionSnapshot = Reconciler = None  # type: ignore[assignment,misc]


def test_fetch_exchange_state_with_oco_order_and_position():
    client = Mock()
    client.get_open_orders.return_value = [
        {
            "orderId": "abc123",
            "side": "Sell",
            "orderType": "Market",
            "qty": "0.5",
            "price": "0",
            "takeProfit": "75000",
            "stopLoss": "65000",
            "orderLinkId": "client-1",
        }
    ]
    client.get_position.return_value = {"size": "0.5", "avgPrice": "70000"}

    state = Reconciler(client).fetch_exchange_state("BTCUSDT")

    assert state.symbol == "BTCUSDT"
    assert len(state.open_orders) == 1
    o = state.open_orders[0]
    assert o.order_id == "abc123"
    assert o.qty == Decimal("0.5")
    assert o.price is None        # "0" → None
    assert o.take_profit == Decimal("75000")
    assert o.stop_loss == Decimal("65000")
    assert o.order_link_id == "client-1"
    assert state.position.qty == Decimal("0.5")
    assert state.position.avg_price == Decimal("70000")


def test_fetch_exchange_state_flat_no_orders():
    client = Mock()
    client.get_open_orders.return_value = []
    client.get_position.return_value = None

    state = Reconciler(client).fetch_exchange_state("BTCUSDT")

    assert state.open_orders == ()
    assert state.position.qty == Decimal("0")
    assert state.position.avg_price is None


def test_fetch_exchange_state_position_with_zero_size_treated_as_flat():
    client = Mock()
    client.get_open_orders.return_value = []
    client.get_position.return_value = {"size": "0", "avgPrice": "0"}

    state = Reconciler(client).fetch_exchange_state("BTCUSDT")

    assert state.position.qty == Decimal("0")
    assert state.position.avg_price is None


def test_fetch_exchange_state_nonzero_qty_with_zero_avg_price_normalizes_to_none():
    """Defensive: avgPrice='0' on a non-zero position is invalid → avg_price=None.

    Matches _normalize_order pattern (treats '0' as missing-data sentinel).
    Prevents Coordinator._persist from writing entry_price=Decimal('0') to state.
    """
    client = Mock()
    client.get_open_orders.return_value = []
    client.get_position.return_value = {"size": "0.5", "avgPrice": "0"}

    state = Reconciler(client).fetch_exchange_state("BTCUSDT")

    assert state.position.qty == Decimal("0.5")
    assert state.position.avg_price is None


def test_fetch_exchange_state_nonzero_qty_with_empty_avg_price_normalizes_to_none():
    client = Mock()
    client.get_open_orders.return_value = []
    client.get_position.return_value = {"size": "0.5", "avgPrice": ""}

    state = Reconciler(client).fetch_exchange_state("BTCUSDT")

    assert state.position.qty == Decimal("0.5")
    assert state.position.avg_price is None


def test_fetch_exchange_state_calls_client_with_symbol():
    client = Mock()
    client.get_open_orders.return_value = []
    client.get_position.return_value = None

    Reconciler(client).fetch_exchange_state("ETHUSDT")

    client.get_open_orders.assert_called_once_with("ETHUSDT")
    client.get_position.assert_called_once_with("ETHUSDT")


def test_open_order_snapshot_is_frozen():
    import dataclasses
    import pytest
    snap = OpenOrderSnapshot(
        order_id="x", side="Buy", order_type="Market",
        qty=Decimal("1"), price=None, take_profit=None,
        stop_loss=None, order_link_id=None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.order_id = "y"  # type: ignore[misc]
