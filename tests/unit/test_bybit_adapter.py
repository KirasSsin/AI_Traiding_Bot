"""Tests for BybitMarketAdapter.place_order (ADR 0020 sub-decision 1)."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from src.execution.bybit.adapter import BybitAPIError, BybitMarketAdapter, OrderAck
from src.execution.bybit.errors import ReasonCode
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
        "result": {"orderId": "EX-12345", "orderLinkId": "CID-abc"},
    }
    return r


def test_place_order_buy_returns_ack() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    ack = adapter.place_order(symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"), order_link_id="CID-abc")
    assert isinstance(ack, OrderAck)
    assert ack.order_id == "EX-12345"
    assert ack.order_link_id == "CID-abc"


def test_place_order_sell_passes_side_to_api() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    adapter.place_order(symbol="BTCUSDT", side="Sell", qty=Decimal("0.001"), order_link_id="CID-sell")
    _, kwargs = rest._http.place_order.call_args
    assert kwargs["category"] == "spot"
    assert kwargs["symbol"] == "BTCUSDT"
    assert kwargs["side"] == "Sell"
    assert kwargs["orderType"] == "Market"
    assert kwargs["marketUnit"] == "baseCoin"
    assert isinstance(kwargs["qty"], str)


def test_filter_violation_rejected_before_api_call() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    with pytest.raises(FilterViolation, match="qty"):
        adapter.place_order(symbol="BTCUSDT", side="Buy", qty=Decimal("0.00001"))
    rest._http.place_order.assert_not_called()


def test_api_error_mapped_to_reason_code() -> None:
    rest = MagicMock()
    rest._http.place_order.return_value = {
        "retCode": 110007,
        "retMsg": "insufficient balance",
        "result": {},
    }
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    with pytest.raises(BybitAPIError) as exc:
        adapter.place_order(symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"), order_link_id="CID-poor")
    assert exc.value.reason is ReasonCode.INSUFFICIENT_BALANCE
    assert exc.value.ret_code == 110007
