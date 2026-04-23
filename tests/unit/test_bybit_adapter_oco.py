"""Tests for BybitMarketAdapter OCO extension (tpslMode). ADR 0019 sub-decision 1."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from src.execution.bybit.adapter import BybitMarketAdapter
from src.execution.models import OrderSide
from src.marketdata.filters import BybitFilters

_FILTERS = BybitFilters(
    symbol="BTCUSDT",
    step_size=Decimal("0.000001"),
    tick_size=Decimal("0.01"),
    min_order_qty=Decimal("0.000048"),
    max_order_qty=Decimal("71.73956243"),
    min_order_amt=Decimal("1"),
)


def _rest_ok() -> MagicMock:
    r = MagicMock()
    r._http.place_order.return_value = {
        "retCode": 0,
        "result": {"orderId": "EX-OCO-1", "orderLinkId": "CID-oco"},
    }
    return r


def test_place_market_order_with_oco_includes_tpsl_in_payload() -> None:
    rest = _rest_ok()
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    adapter.place_market_order(
        client_order_id="CID-oco",
        side=OrderSide.BUY,
        qty=Decimal("0.001"),
        reference_price=Decimal("60000"),
        take_profit=Decimal("61500.0"),
        stop_loss=Decimal("59250.0"),
        tpsl_mode="Full",
    )
    _, kwargs = rest._http.place_order.call_args
    assert kwargs["takeProfit"] == "61500.0"
    assert kwargs["stopLoss"] == "59250.0"
    assert kwargs["tpslMode"] == "Full"


def test_place_market_order_without_oco_omits_tpsl_fields() -> None:
    rest = _rest_ok()
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    adapter.place_market_order(
        client_order_id="CID-no-oco",
        side=OrderSide.BUY,
        qty=Decimal("0.001"),
        reference_price=Decimal("60000"),
    )
    _, kwargs = rest._http.place_order.call_args
    assert "takeProfit" not in kwargs
    assert "stopLoss" not in kwargs
    assert "tpslMode" not in kwargs


def test_place_market_order_with_only_sl_omits_tp() -> None:
    rest = _rest_ok()
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    adapter.place_market_order(
        client_order_id="CID-sl-only",
        side=OrderSide.BUY,
        qty=Decimal("0.001"),
        reference_price=Decimal("60000"),
        stop_loss=Decimal("59000.0"),
        tpsl_mode="Partial",
    )
    _, kwargs = rest._http.place_order.call_args
    assert kwargs["stopLoss"] == "59000.0"
    assert kwargs["tpslMode"] == "Partial"
    assert "takeProfit" not in kwargs
