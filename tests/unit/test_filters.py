"""Tests for BybitFilters."""

from decimal import Decimal

import pytest
from src.marketdata.filters import BybitFilters, FilterViolation

_V5_RESPONSE_SPOT_BTCUSDT = {
    "retCode": 0,
    "result": {
        "list": [
            {
                "symbol": "BTCUSDT",
                "lotSizeFilter": {
                    "basePrecision": "0.000001",
                    "quotePrecision": "0.00000001",
                    "minOrderQty": "0.000048",
                    "maxOrderQty": "71.73956243",
                    "minOrderAmt": "1",
                    "maxOrderAmt": "4000000",
                },
                "priceFilter": {"tickSize": "0.01"},
            }
        ]
    },
}


def test_from_instruments_info_parses_V5_shape() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    assert f.step_size == Decimal("0.000001")
    assert f.tick_size == Decimal("0.01")
    assert f.min_order_qty == Decimal("0.000048")
    assert f.max_order_qty == Decimal("71.73956243")
    assert f.min_order_amt == Decimal("1")


def test_round_qty_rounds_down_to_step() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    assert f.round_qty(Decimal("0.0012345678")) == Decimal("0.001234")
    assert f.round_qty(Decimal("0.001")) == Decimal("0.001")


def test_round_price_rounds_to_tick() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    assert f.round_price(Decimal("60123.456")) == Decimal("60123.45")


def test_validate_rejects_below_min_qty() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    with pytest.raises(FilterViolation, match="qty"):
        f.validate_order(qty=Decimal("0.00001"), price=Decimal("60000"))


def test_validate_rejects_below_min_notional() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    # 0.0001 * 0.01 = 0.000001 USDT << 1
    with pytest.raises(FilterViolation, match="min_order_amt"):
        f.validate_order(qty=Decimal("0.0001"), price=Decimal("0.01"))


def test_validate_accepts_valid_order() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    f.validate_order(qty=Decimal("0.001"), price=Decimal("60000"))  # 60 USDT > 1 min
