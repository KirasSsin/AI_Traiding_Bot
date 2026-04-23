"""Shared pytest fixtures. Populated in later sprints."""
from decimal import Decimal

import pytest


@pytest.fixture
def fake_rest():
    class _FakeHttp:
        def __init__(self):
            self.last_payload = None

        def place_order(self, **kwargs):
            self.last_payload = kwargs
            return {"retCode": 0, "result": {"orderId": "EX-FAKE-1", "orderLinkId": "FAKE-LINK"}}

    class _FakeRest:
        def __init__(self):
            self._http = _FakeHttp()

        @property
        def last_payload(self):
            return self._http.last_payload

    return _FakeRest()


@pytest.fixture
def fake_filters():
    from src.marketdata.filters import BybitFilters

    return BybitFilters(
        symbol="BTCUSDT",
        step_size=Decimal("0.000001"),
        tick_size=Decimal("0.01"),
        min_order_qty=Decimal("0.000048"),
        max_order_qty=Decimal("71.73956243"),
        min_order_amt=Decimal("1"),
    )
