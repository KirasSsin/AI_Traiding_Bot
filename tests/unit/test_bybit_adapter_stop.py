"""ADR 0020 sub-decision 2 — SL leg of 3-order Spot OCO (Stop Market, orderFilter=StopOrder).

Bybit Spot silently rewrites timeInForce GTC→IOC (probe v3-D); we omit timeInForce
from payload and document the override at exit-handling layer (EXIT_SL_RESIDUAL).
"""
from decimal import Decimal
from src.execution.bybit.adapter import BybitMarketAdapter


def test_place_stop_market_payload_shape(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    ack = adapter.place_stop_market_order(
        symbol="BTCUSDT", side="Sell", qty=Decimal("0.001"),
        trigger_price=Decimal("60000.00"), order_link_id="oco-abc-sl-1",
    )
    p = fake_rest.last_payload
    assert p["category"] == "spot"
    assert p["orderType"] == "Market"
    assert p["orderFilter"] == "StopOrder"
    assert p["triggerPrice"] == "60000.00"
    assert p["triggerBy"] == "LastPrice"
    assert p["marketUnit"] == "baseCoin"
    assert p["orderLinkId"] == "oco-abc-sl-1"
    assert "timeInForce" not in p  # Bybit rewrites GTC→IOC silently (probe v3-D)
    assert ack.order_id == fake_rest.fake_order_id
