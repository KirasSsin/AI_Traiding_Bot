import asyncio
import logging
import time
from typing import Callable, List, Optional, Any

from pybit.unified_trading import WebSocket, HTTP
from src.core.models import Kline

logger = logging.getLogger(__name__)

class BybitDataConsumer:
    """
    Connects to Bybit V5 using the official pybit client to stream Kline data.
    Seeds historical klines via REST for indicator warm-up.
    """
    def __init__(
        self,
        symbol: str,
        interval: str,
        max_buffer_size: int = 1000,
        testnet: bool = True,
        category: str = "linear",
        demo: bool = False,
        rest_poll_interval_seconds: int = 2,
    ):
        self.symbol = symbol.upper()
        self.interval = interval
        self.max_buffer_size = max_buffer_size
        self.testnet = testnet
        self.category = category
        self.demo = demo
        self.rest_poll_interval_seconds = rest_poll_interval_seconds
        
        self.kline_buffer: List[Kline] = []
        self.callbacks: List[Callable[[Kline], None]] = []
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws: Optional[WebSocket] = None
        self._http: Optional[HTTP] = None
        self._ws_failed = False
        self._poll_task: Optional[asyncio.Task] = None
        self._last_polled_ts: Optional[int] = None
        self._last_live_ts: Optional[int] = None
        self._last_live_price: Optional[float] = None

        self.data_source: str = "NONE"
        self.last_update_ts: Optional[int] = None
        self.last_rest_poll_ts: Optional[float] = None
        self.last_ws_message_ts: Optional[float] = None
        self.last_rest_message_ts: Optional[float] = None

    def register_callback(self, callback: Callable[[Kline], None]):
        """Register a function to be called whenever a new kline update arrives."""
        self.callbacks.append(callback)

    async def start(self):
        """Start REST warm-up and WebSocket streaming."""
        self._running = True
        self._loop = asyncio.get_running_loop()
        self._http = HTTP(testnet=self.testnet, demo=self.demo)

        await self._seed_historical_buffer()
        await asyncio.to_thread(self._start_ws_stream)
        if self._ws_failed:
            logger.warning("WebSocket unavailable. Falling back to REST polling.")
            self._poll_task = asyncio.create_task(self._poll_klines_loop())

    async def stop(self):
        """Gracefully stop the consumer."""
        self._running = False
        if self._ws:
            await asyncio.to_thread(self._ws.exit)
        if self._poll_task:
            self._poll_task.cancel()
        logger.info("BybitDataConsumer stopped.")

    def _start_ws_stream(self):
        """Blocking setup for pybit WebSocket."""
        try:
            self._ws = WebSocket(
                testnet=self.testnet,
                demo=self.demo,
                channel_type=self.category,
            )
            interval_ws = self._coerce_interval_for_ws()
            if interval_ws is None:
                logger.error(f"Invalid interval for WebSocket: {self.interval}")
                self._ws_failed = True
                return
            self._ws.kline_stream(interval_ws, self.symbol, self._on_ws_message)
            logger.info(f"Subscribed to pybit kline stream: {self.interval} {self.symbol}")
        except Exception as e:
            logger.error(f"Failed to start pybit WebSocket: {e}")
            self._ws_failed = True

    def _coerce_interval_for_ws(self) -> Optional[int]:
        try:
            return int(self.interval)
        except (TypeError, ValueError):
            return None

    def _on_ws_message(self, message: dict):
        """Handle pybit WS messages; runs in WS thread."""
        if not self._running:
            return
        if not isinstance(message, dict):
            return
        data = message.get("data")
        if not isinstance(data, list):
            return

        for item in data:
            kline = self._parse_ws_kline(item)
            if not kline:
                continue

            if kline.is_closed:
                self.kline_buffer.append(kline)
                if len(self.kline_buffer) > self.max_buffer_size:
                    self.kline_buffer.pop(0)

            self._dispatch_kline(kline, source="WS")

    def _parse_ws_kline(self, data: Any) -> Optional[Kline]:
        try:
            if not isinstance(data, dict):
                return None
            timestamp = data.get("start") or data.get("startTime")
            if timestamp is None:
                return None
            return Kline(
                symbol=self.symbol,
                interval=self.interval,
                timestamp=int(timestamp),
                open=float(data.get("open")),
                high=float(data.get("high")),
                low=float(data.get("low")),
                close=float(data.get("close")),
                volume=float(data.get("volume")),
                is_closed=bool(data.get("confirm")),
            )
        except Exception as e:
            logger.error(f"Error parsing WS kline: {e}")
            return None

    async def _seed_historical_buffer(self):
        if not self._http:
            return
        try:
            response = await asyncio.to_thread(
                self._http.get_kline,
                category=self.category,
                symbol=self.symbol,
                interval=str(self.interval),
                limit=self.max_buffer_size,
            )
        except Exception as e:
            logger.error(f"Failed to seed klines via REST: {e}")
            return

        if response.get("retCode") != 0:
            logger.error(f"Failed to seed klines. API Response: {response}")
            return

        result = response.get("result", {})
        items = result.get("list", [])
        parsed: List[Kline] = []
        for item in items:
            kline = self._parse_rest_kline(item)
            if kline:
                parsed.append(kline)

        parsed.sort(key=lambda k: k.timestamp)
        if len(parsed) > self.max_buffer_size:
            parsed = parsed[-self.max_buffer_size:]
        self.kline_buffer = parsed
        logger.info(f"Seeded {len(self.kline_buffer)} klines via REST.")

    def _parse_rest_kline(self, item: Any) -> Optional[Kline]:
        try:
            if isinstance(item, (list, tuple)) and len(item) >= 6:
                timestamp = int(item[0])
                return Kline(
                    symbol=self.symbol,
                    interval=self.interval,
                    timestamp=timestamp,
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]),
                    is_closed=True,
                )
            if isinstance(item, dict):
                timestamp = item.get("start") or item.get("startTime")
                if timestamp is None:
                    return None
                return Kline(
                    symbol=self.symbol,
                    interval=self.interval,
                    timestamp=int(timestamp),
                    open=float(item.get("open")),
                    high=float(item.get("high")),
                    low=float(item.get("low")),
                    close=float(item.get("close")),
                    volume=float(item.get("volume")),
                    is_closed=True,
                )
        except Exception as e:
            logger.error(f"Error parsing REST kline: {e}")
        return None

    async def _poll_klines_loop(self):
        if not self._http:
            return
        poll_interval = self._get_poll_interval_seconds()
        while self._running:
            try:
                response = await asyncio.to_thread(
                    self._http.get_kline,
                    category=self.category,
                    symbol=self.symbol,
                    interval=str(self.interval),
                    limit=2,
                )
                if response.get("retCode") != 0:
                    logger.error(f"REST poll failed: {response}")
                else:
                    items = response.get("result", {}).get("list", [])
                    self.last_rest_poll_ts = asyncio.get_running_loop().time()

                    current_kline = self._pick_latest_rest_kline(items)
                    closed_kline = self._pick_latest_closed_rest_kline(items)
                    if closed_kline and closed_kline.timestamp != self._last_polled_ts:
                        self._last_polled_ts = closed_kline.timestamp
                        self.kline_buffer.append(closed_kline)
                        if len(self.kline_buffer) > self.max_buffer_size:
                            self.kline_buffer.pop(0)
                        self._dispatch_kline(closed_kline, source="REST")

                    if current_kline:
                        should_emit_live = (
                            self._last_live_ts != current_kline.timestamp
                            or self._last_live_price != current_kline.close
                        )
                        if should_emit_live:
                            self._last_live_ts = current_kline.timestamp
                            self._last_live_price = current_kline.close
                            self._dispatch_kline(current_kline, source="REST")
            except Exception as e:
                logger.error(f"REST poll error: {e}")

            await asyncio.sleep(poll_interval)

    def _pick_latest_rest_kline(self, items: Any) -> Optional[Kline]:
        if not items:
            return None
        candidate = items[0]
        kline = self._parse_rest_kline(candidate)
        if kline:
            kline.is_closed = False
        return kline

    def _pick_latest_closed_rest_kline(self, items: Any) -> Optional[Kline]:
        if not items:
            return None
        # Bybit REST returns latest first. Use the second item if available.
        candidate = items[1] if len(items) > 1 else items[0]
        return self._parse_rest_kline(candidate)

    def _get_poll_interval_seconds(self) -> int:
        if self.rest_poll_interval_seconds:
            return max(1, int(self.rest_poll_interval_seconds))
        try:
            minutes = int(self.interval)
            return max(2, minutes * 2)
        except (TypeError, ValueError):
            return 5

    def _dispatch_kline(self, kline: Kline, source: str):
        self.data_source = source
        self.last_update_ts = kline.timestamp
        now = time.time()
        if source == "WS":
            self.last_ws_message_ts = now
        else:
            self.last_rest_message_ts = now

        for callback in self.callbacks:
            try:
                if self._loop and source == "WS":
                    self._loop.call_soon_threadsafe(callback, kline)
                else:
                    callback(kline)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    def get_historical_buffer(self) -> List[Kline]:
        """Return a copy of the closed candles buffer."""
        return list(self.kline_buffer)
