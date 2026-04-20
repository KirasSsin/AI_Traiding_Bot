from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.execution.models import Fill, Order, OrderSide, OrderStatus, OrderType


def test_order_valid():
    o = Order(
        client_order_id="c-abc-123",
        exch_order_id="42",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        status=OrderStatus.NEW,
        orig_qty=Decimal("0.001"),
        executed_qty=Decimal("0"),
        price=None,
        created_at=datetime(2026, 4, 20, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 20, 1, tzinfo=timezone.utc),
    )
    assert o.status == OrderStatus.NEW


def test_order_executed_not_exceed_orig():
    with pytest.raises(ValidationError, match="executed_qty"):
        Order(
            client_order_id="c-1",
            exch_order_id=None,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            status=OrderStatus.PARTIALLY_FILLED,
            orig_qty=Decimal("0.001"),
            executed_qty=Decimal("0.002"),
            price=None,
            created_at=datetime(2026, 4, 20, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 20, 1, tzinfo=timezone.utc),
        )


def test_fill_valid():
    f = Fill(
        client_order_id="c-1",
        trade_id=100,
        qty=Decimal("0.001"),
        price=Decimal("60000"),
        fee=Decimal("0.06"),
        fee_asset="USDT",
        is_maker=False,
        filled_at=datetime(2026, 4, 20, 1, tzinfo=timezone.utc),
    )
    assert f.qty == Decimal("0.001")
