"""Tests for BybitWSConsumer."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from src.marketdata.bybit.ws import BybitWSConsumer


@pytest.mark.asyncio
async def test_stream_yields_messages_from_callback() -> None:
    """Simulate pybit WebSocket pushing 2 messages via callback."""
    captured_cb = []

    def fake_kline_stream(interval, symbol, callback):  # type: ignore[no-untyped-def]  # noqa: ARG001
        captured_cb.append(callback)

    mock_ws_cls = MagicMock()
    mock_ws_cls.return_value.kline_stream.side_effect = fake_kline_stream

    with patch("src.marketdata.bybit.ws.WebSocket", mock_ws_cls):
        consumer = BybitWSConsumer(symbol="BTCUSDT", interval="60", testnet=True)
        consumer.start()

        # Simulate pybit pushing messages
        assert len(captured_cb) == 1
        cb = captured_cb[0]
        cb({"topic": "kline.60.BTCUSDT", "data": [{"start": 1, "confirm": True}]})
        cb({"topic": "kline.60.BTCUSDT", "data": [{"start": 2, "confirm": False}]})

        # Collect via async iterator (bounded by timeout)
        received = []

        async def collect() -> None:
            async for msg in consumer.stream():
                received.append(msg)
                if len(received) == 2:
                    return

        await asyncio.wait_for(collect(), timeout=1.0)

    assert len(received) == 2
    assert received[0]["start"] == 1
    assert received[1]["start"] == 2


@pytest.mark.asyncio
async def test_start_creates_ws_with_correct_params() -> None:
    mock_ws_cls = MagicMock()
    with patch("src.marketdata.bybit.ws.WebSocket", mock_ws_cls):
        consumer = BybitWSConsumer(symbol="BTCUSDT", interval="60", testnet=True)
        consumer.start()
    mock_ws_cls.assert_called_once_with(testnet=True, channel_type="spot")
    mock_ws_cls.return_value.kline_stream.assert_called_once()
    _, kwargs = mock_ws_cls.return_value.kline_stream.call_args
    assert kwargs["interval"] == "60"
    assert kwargs["symbol"] == "BTCUSDT"
