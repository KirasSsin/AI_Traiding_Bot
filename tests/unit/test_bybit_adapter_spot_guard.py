"""ADR 0020 sub-decision 3 — banned-field guard for Spot V5 (probe v1: ErrCode 170130)."""
from __future__ import annotations
from decimal import Decimal
import pytest
from src.execution.bybit.adapter import BybitMarketAdapter

BANNED_FIELDS = ("tpslMode", "takeProfit", "stopLoss", "tpOrderType", "slOrderType", "triggerDirection")


@pytest.mark.parametrize("field", BANNED_FIELDS)
def test_place_market_rejects_banned_spot_fields(field, fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    with pytest.raises(ValueError, match=f"banned for Bybit Spot V5: {field}"):
        adapter.place_order(
            symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"),
            extra_payload={field: "any"},
        )


def test_place_market_rejects_marketunit_quotecoin(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    with pytest.raises(ValueError, match="marketUnit=quoteCoin banned"):
        adapter.place_order(
            symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"),
            extra_payload={"marketUnit": "quoteCoin"},
        )


def test_place_market_passes_marketunit_basecoin(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    adapter.place_order(symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"))
    payload = fake_rest.last_payload
    assert payload["marketUnit"] == "baseCoin"
    assert payload["category"] == "spot"
