"""Market-data pipeline: gap-seed via REST → stream WS → persist Parquet."""

from pathlib import Path
from typing import Any, Protocol

from src.marketdata.bar_builder import BarBuilder
from src.marketdata.gaps import find_gaps
from src.marketdata.models import Bar
from src.marketdata.storage import ParquetBarWriter


class _RESTClient(Protocol):
    def get_klines(self, symbol: str, interval: str, start_ms: int, end_ms: int) -> list[Bar]: ...


class _WSConsumer(Protocol):
    def start(self) -> None: ...
    def stream(self) -> Any: ...  # AsyncIterator[dict[str, Any]]


class MarketDataPipeline:
    """Orchestrates seed → stream → persist flow."""

    def __init__(
        self,
        rest: _RESTClient,
        ws: _WSConsumer,
        bar_builder: BarBuilder,
        parquet_writer: ParquetBarWriter,
        parquet_dir: Path,
        interval_ms: int,
        symbol: str = "BTCUSDT",
        ws_interval: str = "60",
    ) -> None:
        self._rest = rest
        self._ws = ws
        self._builder = bar_builder
        self._writer = parquet_writer
        self._parquet_dir = parquet_dir
        self._interval_ms = interval_ms
        self._symbol = symbol
        self._ws_interval = ws_interval

    async def run(self, max_bars: int | None = None) -> None:
        """Gap-seed then consume WS until `max_bars` confirmed bars appended
        (None = forever). `max_bars=0` skips streaming (useful for seed-only tests).
        """
        await self._seed_gaps()
        if max_bars == 0:
            return
        self._ws.start()
        count = 0
        async for msg in self._ws.stream():
            bar = self._builder.process(msg)
            if bar is not None:
                self._writer.append([bar])
                count += 1
                if max_bars is not None and count >= max_bars:
                    return

    async def _seed_gaps(self) -> None:
        gaps = find_gaps(self._parquet_dir, interval_ms=self._interval_ms)
        for gap_start, gap_end in gaps:
            start_ms = int(gap_start.timestamp() * 1000)
            end_ms = int(gap_end.timestamp() * 1000)
            bars = self._rest.get_klines(
                symbol=self._symbol,
                interval=self._ws_interval,
                start_ms=start_ms,
                end_ms=end_ms,
            )
            if bars:
                self._writer.append(bars)
