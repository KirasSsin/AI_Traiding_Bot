"""BybitPrivateWSConsumer tests (ADR 0021 sub-decision 6)."""
from unittest.mock import MagicMock

import pytest

from src.execution.bybit.ws_private import BybitPrivateWSConsumer


def test_consumer_initializes_with_pybit_handle():
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord,
        reconciler=reco,
    )
    assert c._coordinator is coord
    assert c._reconciler is reco


def test_consumer_on_disconnect_triggers_reconnect_event():
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord, reconciler=reco,
    )
    c.on_disconnect()
    # Reconnect path eventually calls coordinator.on_ws_reconnect
    coord.on_ws_reconnect.assert_called_once()


def test_parser_forwards_filled_event_with_fees():
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord, reconciler=reco,
    )
    msg = {"data": [{
        "orderLinkId": "oco-abc-TP-1",
        "orderId": "bybit-oid-1",
        "orderStatus": "Filled",
        "cumExecQty": "0.001",
        "cumExecFee": "0.0000012",
        "feeCurrency": "BTC",
        "avgPrice": "62500",
    }]}
    c._on_order_raw(msg)
    coord.on_order_event.assert_called_once()
    evt = coord.on_order_event.call_args.args[0]
    assert evt["cumExecFee"] == "0.0000012"
    assert evt["feeCurrency"] == "BTC"


def test_parser_drops_filled_event_missing_cumExecFee(caplog):
    """ADR 0021 sub-decision 6: Filled w/o fees → ERROR log + drop (never forward None fees)."""
    coord = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord, reconciler=MagicMock(),
    )
    msg = {"data": [{
        "orderLinkId": "oco-abc-TP-1",
        "orderStatus": "Filled",
        "cumExecQty": "0.001",
        # cumExecFee MISSING
        "avgPrice": "62500",
    }]}
    with caplog.at_level("ERROR"):
        c._on_order_raw(msg)
    coord.on_order_event.assert_not_called()
    assert any("cumExecFee" in rec.message for rec in caplog.records)


def test_parser_forwards_new_unfilled_event_without_fees():
    """New/Cancelled/Rejected → fees not expected, forward."""
    coord = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord, reconciler=MagicMock(),
    )
    msg = {"data": [{
        "orderLinkId": "oco-abc-SL-1",
        "orderStatus": "New",
        "cumExecQty": "0",
    }]}
    c._on_order_raw(msg)
    coord.on_order_event.assert_called_once()


def test_wallet_event_routed_to_reconciler():
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=MagicMock(), reconciler=reco,
    )
    msg = {"data": [{
        "accountType": "UNIFIED",
        "coin": [{"coin": "BTC", "walletBalance": "0.001234"}],
    }]}
    c._on_wallet_raw(msg)
    reco.on_wallet_event.assert_called_once_with({"coin": "BTC", "walletBalance": "0.001234"})


def test_wallet_event_multi_coin_dispatched_individually():
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=MagicMock(), reconciler=reco,
    )
    msg = {"data": [{
        "coin": [
            {"coin": "BTC", "walletBalance": "0.001"},
            {"coin": "USDT", "walletBalance": "1000.0"},
        ],
    }]}
    c._on_wallet_raw(msg)
    assert reco.on_wallet_event.call_count == 2
