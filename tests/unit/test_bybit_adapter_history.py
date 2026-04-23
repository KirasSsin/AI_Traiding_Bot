"""ADR 0020 sub-decision 9: get_open_orders + get_order_history support bootstrap
prior-attempt detection. Both pass through Bybit V5 result.list shape."""
from decimal import Decimal

from src.execution.bybit.adapter import BybitMarketAdapter
from src.marketdata.filters import BybitFilters


def _filters():
    return BybitFilters(
        symbol="BTCUSDT",
        step_size=Decimal("0.000001"),
        tick_size=Decimal("0.01"),
        min_order_qty=Decimal("0.000048"),
        max_order_qty=Decimal("71.73956243"),
        min_order_amt=Decimal("1"),
    )


class _FakeHTTP:
    def __init__(self, resp):
        self.resp = resp
        self.last_call = None

    def get_open_orders(self, **kwargs):
        self.last_call = ("get_open_orders", kwargs)
        return self.resp

    def get_order_history(self, **kwargs):
        self.last_call = ("get_order_history", kwargs)
        return self.resp


class _FakeRest:
    def __init__(self, resp):
        self._http = _FakeHTTP(resp)


def test_get_open_orders_returns_list_passthrough():
    items = [{"orderLinkId": "oco-abc-tp-1", "orderId": "EX1"}]
    rest = _FakeRest({"retCode": 0, "result": {"list": items}})
    adapter = BybitMarketAdapter(rest=rest, filters=_filters())
    out = adapter.get_open_orders(symbol="BTCUSDT")
    assert out == items
    name, kwargs = rest._http.last_call
    assert name == "get_open_orders"
    assert kwargs["category"] == "spot"
    assert kwargs["symbol"] == "BTCUSDT"


def test_get_open_orders_empty_list_when_no_result():
    rest = _FakeRest({"retCode": 0, "result": {}})
    adapter = BybitMarketAdapter(rest=rest, filters=_filters())
    assert adapter.get_open_orders(symbol="BTCUSDT") == []


def test_get_order_history_passes_limit():
    items = [{"orderLinkId": "oco-abc-sl-2", "orderId": "EX2"}]
    rest = _FakeRest({"retCode": 0, "result": {"list": items}})
    adapter = BybitMarketAdapter(rest=rest, filters=_filters())
    out = adapter.get_order_history(symbol="BTCUSDT", limit=50)
    assert out == items
    _name, kwargs = rest._http.last_call
    assert kwargs["limit"] == 50


def test_get_order_history_default_limit_50():
    rest = _FakeRest({"retCode": 0, "result": {"list": []}})
    adapter = BybitMarketAdapter(rest=rest, filters=_filters())
    adapter.get_order_history(symbol="BTCUSDT")
    _name, kwargs = rest._http.last_call
    assert kwargs["limit"] == 50
