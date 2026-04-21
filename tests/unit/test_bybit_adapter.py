"""Tests for BybitMarketAdapter.place_market_order."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from src.execution.bybit.adapter import BybitAPIError, BybitMarketAdapter
from src.execution.bybit.errors import ReasonCode
from src.execution.models import Order, OrderSide, OrderStatus, OrderType
from src.marketdata.filters import BybitFilters, FilterViolation

_FILTERS = BybitFilters(
    symbol="BTCUSDT",
    step_size=Decimal("0.000001"),
    tick_size=Decimal("0.01"),
    min_order_qty=Decimal("0.000048"),
    max_order_qty=Decimal("71.73956243"),
    min_order_amt=Decimal("1"),
)


def _rest_ok_place() -> MagicMock:
    r = MagicMock()
    r._http.place_order.return_value = {
        "retCode": 0,
        "result": {
            "orderId": "EX-12345",
            "orderLinkId": "CID-abc",
        },
    }
    return r


def test_place_market_buy_returns_order() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    order = adapter.place_market_order(
        client_order_id="CID-abc",
        side=OrderSide.BUY,
        qty=Decimal("0.001"),
        reference_price=Decimal("60000"),
    )
    assert isinstance(order, Order)
    assert order.client_order_id == "CID-abc"
    assert order.exch_order_id == "EX-12345"
    assert order.side is OrderSide.BUY
    assert order.type is OrderType.MARKET
    assert order.status is OrderStatus.NEW


def test_place_market_sell_passes_side_to_api() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    adapter.place_market_order(
        client_order_id="CID-sell",
        side=OrderSide.SELL,
        qty=Decimal("0.001"),
        reference_price=Decimal("60000"),
    )
    _, kwargs = rest._http.place_order.call_args
    assert kwargs["category"] == "spot"
    assert kwargs["symbol"] == "BTCUSDT"
    assert kwargs["side"] == "Sell"
    assert kwargs["orderType"] == "Market"
    assert isinstance(kwargs["qty"], str)


def test_filter_violation_rejected_before_api_call() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    with pytest.raises(FilterViolation, match="qty"):
        adapter.place_market_order(
            client_order_id="CID-tiny",
            side=OrderSide.BUY,
            qty=Decimal("0.00001"),  # below min_order_qty
            reference_price=Decimal("60000"),
        )
    rest._http.place_order.assert_not_called()


def test_api_error_mapped_to_reason_code() -> None:
    rest = MagicMock()
    rest._http.place_order.return_value = {
        "retCode": 110007,
        "retMsg": "insufficient balance",
        "result": {},
    }
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    with pytest.raises(BybitAPIError) as exc:
        adapter.place_market_order(
            client_order_id="CID-poor",
            side=OrderSide.BUY,
            qty=Decimal("0.001"),
            reference_price=Decimal("60000"),
        )
    assert exc.value.reason is ReasonCode.INSUFFICIENT_BALANCE
    assert exc.value.ret_code == 110007
