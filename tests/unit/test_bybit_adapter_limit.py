"""ADR 0020 sub-decision 2 — TP leg of 3-order Spot OCO (Limit Sell @ TP, GTC)."""
from decimal import Decimal
from src.execution.bybit.adapter import BybitMarketAdapter


def test_place_limit_order_payload_shape(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    ack = adapter.place_limit_order(
        symbol="BTCUSDT", side="Sell", qty=Decimal("0.001"),
        price=Decimal("70000.00"), order_link_id="oco-abc-tp-1",
    )
    payload = fake_rest.last_payload
    assert payload["category"] == "spot"
    assert payload["orderType"] == "Limit"
    assert payload["timeInForce"] == "GTC"
    assert payload["marketUnit"] == "baseCoin"
    assert payload["price"] == "70000.00"
    assert payload["orderLinkId"] == "oco-abc-tp-1"
    assert ack.order_id == fake_rest.fake_order_id
