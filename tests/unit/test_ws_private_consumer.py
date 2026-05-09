"""BybitPrivateWSConsumer tests (ADR 0021 sub-decision 6)."""

from unittest.mock import MagicMock

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
        fill_recorder=MagicMock(),
    )
    assert c._coordinator is coord
    assert c._reconciler is reco


def test_consumer_on_disconnect_triggers_reconnect_event():
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord,
        reconciler=reco,
        fill_recorder=MagicMock(),
    )
    c.on_disconnect()
    # Reconnect path eventually calls coordinator.on_ws_reconnect
    coord.on_ws_reconnect.assert_called_once()


def test_check_alive_triggers_disconnect_when_silent_too_long():
    """Heartbeat watchdog backstop for pybit close-callback gap."""
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord,
        reconciler=reco,
        fill_recorder=MagicMock(),
    )
    fake_ws = MagicMock()
    fake_ws.last_ping_time = 0.0  # ancient ping → past silence window
    c._ws = fake_ws
    alive = c.check_alive(max_silence_seconds=1.0)
    assert alive is False
    coord.on_ws_reconnect.assert_called_once()


def test_check_alive_returns_true_when_no_ws():
    """No WS handle → returns False (callable doesn't crash)."""
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        fill_recorder=MagicMock(),
    )
    assert c.check_alive() is False


def test_parser_forwards_filled_event_with_fees():
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord,
        reconciler=reco,
        fill_recorder=MagicMock(),
    )
    msg = {
        "data": [
            {
                "orderLinkId": "oco-abc-TP-1",
                "orderId": "bybit-oid-1",
                "orderStatus": "Filled",
                "cumExecQty": "0.001",
                "cumExecFee": "0.0000012",
                "feeCurrency": "BTC",
                "avgPrice": "62500",
            }
        ]
    }
    c._on_order_raw(msg)
    coord.on_order_event.assert_called_once()
    evt = coord.on_order_event.call_args.args[0]
    assert evt["cumExecFee"] == "0.0000012"
    assert evt["feeCurrency"] == "BTC"


def test_parser_drops_filled_event_missing_cum_exec_fee(caplog):
    """ADR 0021 sub-decision 6: Filled w/o fees → ERROR log + drop (never forward None fees)."""
    coord = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord,
        reconciler=MagicMock(),
        fill_recorder=MagicMock(),
    )
    msg = {
        "data": [
            {
                "orderLinkId": "oco-abc-TP-1",
                "orderStatus": "Filled",
                "cumExecQty": "0.001",
                # cumExecFee MISSING
                "avgPrice": "62500",
            }
        ]
    }
    with caplog.at_level("ERROR"):
        c._on_order_raw(msg)
    coord.on_order_event.assert_not_called()
    assert any("cumExecFee" in rec.message for rec in caplog.records)


def test_parser_forwards_new_unfilled_event_without_fees():
    """New/Cancelled/Rejected → fees not expected, forward."""
    coord = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord,
        reconciler=MagicMock(),
        fill_recorder=MagicMock(),
    )
    msg = {
        "data": [
            {
                "orderLinkId": "oco-abc-SL-1",
                "orderStatus": "New",
                "cumExecQty": "0",
            }
        ]
    }
    c._on_order_raw(msg)
    coord.on_order_event.assert_called_once()


def test_wallet_event_routed_to_reconciler():
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=MagicMock(),
        reconciler=reco,
        fill_recorder=MagicMock(),
    )
    msg = {
        "data": [
            {
                "accountType": "UNIFIED",
                "coin": [{"coin": "BTC", "walletBalance": "0.001234"}],
            }
        ]
    }
    c._on_wallet_raw(msg)
    reco.on_wallet_event.assert_called_once_with({"coin": "BTC", "walletBalance": "0.001234"})


def test_wallet_event_multi_coin_dispatched_individually():
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=MagicMock(),
        reconciler=reco,
        fill_recorder=MagicMock(),
    )
    msg = {
        "data": [
            {
                "coin": [
                    {"coin": "BTC", "walletBalance": "0.001"},
                    {"coin": "USDT", "walletBalance": "1000.0"},
                ],
            }
        ]
    }
    c._on_wallet_raw(msg)
    assert reco.on_wallet_event.call_count == 2


def test_execution_event_dispatched_to_fill_recorder() -> None:
    """S9 Q3 B1: WS execution topic message routes к FillRecorder.on_fill_event.

    Verifies _on_execution_raw extracts fill data from Bybit V5 execution
    schema and dispatches one event per fill.
    """
    fill_recorder = MagicMock()

    consumer = BybitPrivateWSConsumer(
        api_key="test",
        api_secret="test",
        endpoint="testnet.bybit.com",
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        fill_recorder=fill_recorder,  # NEW kwarg
    )

    msg = {
        "topic": "execution",
        "data": [
            {
                "execId": "exec_abc",
                "orderId": "order_1",
                "symbol": "BTCUSDT",
                "execQty": "0.5",
                "execPrice": "100000",
                "execFee": "0.05",
                "feeCurrency": "USDT",
                "execType": "Trade",
                "isMaker": False,
                "execTime": "1745582400000",
            },
        ],
    }
    consumer._on_execution_raw(msg)

    fill_recorder.on_fill_event.assert_called_once()
    call_evt = fill_recorder.on_fill_event.call_args[0][0]
    assert call_evt["execId"] == "exec_abc"
    assert call_evt["execQty"] == "0.5"


def test_execution_event_handles_multiple_fills() -> None:
    """S9 Q3 B1: One WS message с multiple fills dispatches each separately."""
    fill_recorder = MagicMock()
    consumer = BybitPrivateWSConsumer(
        api_key="t",
        api_secret="t",
        endpoint="testnet.bybit.com",
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        fill_recorder=fill_recorder,
    )
    msg = {
        "topic": "execution",
        "data": [
            {"execId": "e1", "execQty": "0.3"},
            {"execId": "e2", "execQty": "0.2"},
        ],
    }
    consumer._on_execution_raw(msg)
    assert fill_recorder.on_fill_event.call_count == 2


def test_execution_event_swallows_handler_exception() -> None:
    """S9 Q3 B1: Exception в fill_recorder.on_fill_event logged + dropped (mirror order/wallet pattern)."""
    fill_recorder = MagicMock()
    fill_recorder.on_fill_event.side_effect = RuntimeError("boom")
    consumer = BybitPrivateWSConsumer(
        api_key="t",
        api_secret="t",
        endpoint="testnet.bybit.com",
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        fill_recorder=fill_recorder,
    )
    # Should not raise — exception swallowed + logged
    consumer._on_execution_raw({"topic": "execution", "data": [{"execId": "x"}]})


def test_reconnect_triggers_check_alive_re_probe() -> None:
    """S39 T8 H2 regression: after disconnect → reconnect → check_alive must be called
    to verify WS subscription was re-attached.

    Prevents silent dead-WS scenario where reconcile delivers AGREE on stale state.
    Per S38 T3 bybit-api-reviewer finding.
    """
    from unittest.mock import patch

    coord = MagicMock()
    consumer = BybitPrivateWSConsumer(
        api_key="test_key",
        api_secret="test_secret",
        endpoint="wss://stream-testnet.bybit.com/v5/private",
        coordinator=coord,
        reconciler=MagicMock(),
        fill_recorder=MagicMock(),
    )

    # Mock check_alive to track calls
    with patch.object(consumer, "check_alive", return_value=True) as mock_check_alive:
        # Simulate disconnect — should trigger reconnect handler + re-probe
        consumer.on_disconnect()

        # check_alive must be called at least once after on_disconnect
        # to verify subscription re-attached
        assert (
            mock_check_alive.call_count >= 1
        ), "S39 T8 H2 gap: post-disconnect re-probe missing — silent dead-WS risk"
