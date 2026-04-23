"""ADR 0020 sub-decisions 2 & 6 — cancel + 110001 classifier (REJECT_ORDER_ALREADY_TERMINAL)."""
from src.execution.bybit.adapter import BybitMarketAdapter
from src.execution.bybit.errors import ReasonCode


def test_cancel_order_happy(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    res = adapter.cancel_order(symbol="BTCUSDT", order_id="OID123")
    p = fake_rest.last_payload
    assert p["category"] == "spot"
    assert p["symbol"] == "BTCUSDT"
    assert p["orderId"] == "OID123"
    assert res.cancelled is True
    assert res.reason_code is None


def test_cancel_order_already_terminal_returns_reason_code(fake_rest, fake_filters):
    """ADR 0020 sub-decision 6: Bybit returns 110001 when cancelling already-Filled order.
    Adapter must classify this as REJECT_ORDER_ALREADY_TERMINAL (non-fatal race)."""
    fake_rest.next_ret_code = 110001
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    res = adapter.cancel_order(symbol="BTCUSDT", order_id="OID999")
    assert res.cancelled is False
    assert res.reason_code == ReasonCode.REJECT_ORDER_ALREADY_TERMINAL


def test_cancel_all_orders_payload(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    adapter.cancel_all_orders(symbol="BTCUSDT")
    p = fake_rest.last_payload
    assert p == {"category": "spot", "symbol": "BTCUSDT"}
