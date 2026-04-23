"""ADR 0020 sub-decision 4 — walletBalance is canonical Spot position truth."""
from decimal import Decimal
from src.execution.bybit.adapter import BybitMarketAdapter


def test_get_order_returns_status_snapshot(fake_rest, fake_filters):
    fake_rest.next_get_order = {
        "orderId": "OID1", "orderLinkId": "oco-abc-tp-1",
        "orderStatus": "Filled", "cumExecQty": "0.001",
        "cumExecFee": "0.0000005", "feeCurrency": "BTC",
        "avgPrice": "70000.00",
    }
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    snap = adapter.get_order(symbol="BTCUSDT", order_id="OID1")
    assert snap.order_status == "Filled"
    assert snap.cum_exec_qty == Decimal("0.001")
    assert snap.cum_exec_fee == Decimal("0.0000005")
    assert snap.fee_currency == "BTC"
    assert snap.avg_price == Decimal("70000.00")


def test_get_wallet_balance_btc_handles_empty_available(fake_rest, fake_filters):
    """ADR 0020 sub-decision 4: availableToWithdraw='' when funds locked — coerce to 0."""
    fake_rest.next_wallet = {
        "coin": "BTC",
        "walletBalance": "0.00100000",
        "availableToWithdraw": "",  # empty when locked in open orders
        "locked": "0.00100000",
    }
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    snap = adapter.get_wallet_balance(coin="BTC")
    assert snap.wallet_balance == Decimal("0.00100000")
    assert snap.available == Decimal("0")
    assert snap.locked == Decimal("0.00100000")
