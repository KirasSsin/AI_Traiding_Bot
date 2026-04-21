"""Bybit V5 WS consumer — bridges pybit callback to asyncio iteration."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from pybit.unified_trading import WebSocket


class BybitWSConsumer:
    """Wraps `pybit.WebSocket.kline_stream` into an `async for` iterator.

    pybit's WebSocket is callback-based and runs in its own thread. We bridge
    by pushing each callback payload into an `asyncio.Queue` that `stream()`
    consumes asynchronously.
    """

    def __init__(self, symbol: str, interval: str, testnet: bool) -> None:
        self._symbol = symbol
        self._interval = interval
        self._testnet = testnet
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws: Any = None

    def start(self) -> None:
        """Start underlying pybit WebSocket — must be called from an async context."""
        self._loop = asyncio.get_event_loop()
        self._ws = WebSocket(testnet=self._testnet, channel_type="spot")
        self._ws.kline_stream(
            interval=self._interval,
            symbol=self._symbol,
            callback=self._on_message,
        )

    def _on_message(self, msg: dict[str, Any]) -> None:
        """Called by pybit on each WS message — push first `data` item into queue."""
        data = msg.get("data") or []
        if not data:
            return
        # Use thread-safe loop scheduling: pybit callback runs on its own thread
        assert self._loop is not None
        self._loop.call_soon_threadsafe(self._queue.put_nowait, data[0])

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        """Async iterator of kline messages."""
        while True:
            msg = await self._queue.get()
            yield msg
