"""Shared pytest fixtures. Populated in later sprints."""
from decimal import Decimal

import pytest


@pytest.fixture
def fake_rest():
    class _FakeHttp:
        fake_order_id = "EX-FAKE-1"

        def __init__(self):
            self.last_payload = None
            self.next_ret_code = 0
            self.next_get_order = None
            self.next_wallet = None

        def _maybe_error(self, result=None):
            if self.next_ret_code != 0:
                code = self.next_ret_code
                self.next_ret_code = 0
                return {"retCode": code, "retMsg": "fake", "result": {}}
            return {"retCode": 0, "result": result or {}}

        def place_order(self, **kwargs):
            self.last_payload = kwargs
            return self._maybe_error({"orderId": self.fake_order_id, "orderLinkId": kwargs.get("orderLinkId", "FAKE-LINK")})

        def cancel_order(self, **kwargs):
            self.last_payload = kwargs
            return self._maybe_error({"orderId": kwargs.get("orderId"), "orderLinkId": ""})

        def cancel_all_orders(self, **kwargs):
            self.last_payload = kwargs
            return self._maybe_error({"list": []})

        def get_order(self, **kwargs):
            self.last_payload = kwargs
            data = self.next_get_order
            self.next_get_order = None
            return self._maybe_error({"list": [data]} if data else {"list": []})

        def get_wallet_balance(self, **kwargs):
            self.last_payload = kwargs
            w = self.next_wallet
            self.next_wallet = None
            return self._maybe_error({"list": [{"coin": [w]}]} if w else {"list": []})

    class _FakeRest:
        fake_order_id = _FakeHttp.fake_order_id

        def __init__(self):
            self._http = _FakeHttp()

        @property
        def last_payload(self):
            return self._http.last_payload

        @last_payload.setter
        def last_payload(self, v):
            self._http.last_payload = v

        @property
        def next_ret_code(self):
            return self._http.next_ret_code

        @next_ret_code.setter
        def next_ret_code(self, v):
            self._http.next_ret_code = v

        @property
        def next_get_order(self):
            return self._http.next_get_order

        @next_get_order.setter
        def next_get_order(self, v):
            self._http.next_get_order = v

        @property
        def next_wallet(self):
            return self._http.next_wallet

        @next_wallet.setter
        def next_wallet(self, v):
            self._http.next_wallet = v

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
