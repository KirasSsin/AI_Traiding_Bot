"""Tests for MarketDataPipeline orchestrator."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from src.marketdata.bar_builder import BarBuilder
from src.marketdata.models import Bar, DataQuality
from src.marketdata.pipeline import MarketDataPipeline

INTERVAL_MS = 3_600_000


def _msg(open_ms: int, confirm: bool = True) -> dict[str, object]:
    return {
        "start": open_ms,
        "end": open_ms + INTERVAL_MS,
        "interval": "60",
        "open": "60000",
        "close": "60050",
        "high": "60100",
        "low": "59900",
        "volume": "1.0",
        "confirm": confirm,
    }


def _bar(hour: int) -> Bar:
    base = datetime(2026, 4, 20, 0, tzinfo=UTC)
    return Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=base + timedelta(hours=hour),
        close_time=base + timedelta(hours=hour + 1),
        open=Decimal("60000"),
        high=Decimal("60100"),
        low=Decimal("59900"),
        close=Decimal("60050"),
        volume=Decimal("1"),
        trade_count=0,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


async def _ws_stream(msgs: list[dict[str, object]]) -> AsyncIterator[dict[str, object]]:
    for m in msgs:
        yield m


@pytest.mark.asyncio
async def test_pipeline_persists_confirmed_bars(tmp_path: Path) -> None:
    rest = MagicMock()
    rest.get_klines.return_value = []  # no seed gap to fill

    ws = MagicMock()
    ws.start = MagicMock()
    msg_open_ms = int(datetime(2026, 4, 20, 0, tzinfo=UTC).timestamp() * 1000)
    ws.stream = lambda: _ws_stream([_msg(msg_open_ms, confirm=True)])

    parquet_writer = MagicMock()
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)

    pipeline = MarketDataPipeline(
        rest=rest,
        ws=ws,
        bar_builder=builder,
        parquet_writer=parquet_writer,
        parquet_dir=tmp_path,
        interval_ms=INTERVAL_MS,
    )
    # Run for one message then stop
    await asyncio.wait_for(pipeline.run(max_bars=1), timeout=2.0)

    ws.start.assert_called_once()
    parquet_writer.append.assert_called_once()
    ((bars,), _) = parquet_writer.append.call_args
    assert len(bars) == 1
    assert bars[0].is_closed is True


@pytest.mark.asyncio
async def test_pipeline_emits_gap_bar_on_ws_gap(tmp_path: Path) -> None:
    # WS stream with a missing interval between two confirmed bars → synthetic
    # GAP bar must be appended (DataQuality.GAP) so downstream series has no hidden hole.
    rest = MagicMock()
    rest.get_klines.return_value = []  # no seed gap

    open0 = int(datetime(2026, 4, 20, 0, tzinfo=UTC).timestamp() * 1000)
    open2 = open0 + 2 * INTERVAL_MS  # skip interval 1 → gap
    ws = MagicMock()
    ws.start = MagicMock()
    ws.stream = lambda: _ws_stream([_msg(open0, confirm=True), _msg(open2, confirm=True)])

    parquet_writer = MagicMock()
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)

    pipeline = MarketDataPipeline(
        rest=rest,
        ws=ws,
        bar_builder=builder,
        parquet_writer=parquet_writer,
        parquet_dir=tmp_path,
        interval_ms=INTERVAL_MS,
    )
    await asyncio.wait_for(pipeline.run(max_bars=2), timeout=2.0)

    appended = [b for (args, _) in parquet_writer.append.call_args_list for b in args[0]]
    gap_bars = [b for b in appended if b.data_quality is DataQuality.GAP]
    assert len(gap_bars) == 1
    assert gap_bars[0].open_time == datetime.fromtimestamp((open0 + INTERVAL_MS) / 1000, tz=UTC)
    # both real confirmed bars also persisted
    ok_bars = [b for b in appended if b.data_quality is DataQuality.OK]
    assert len(ok_bars) == 2


@pytest.mark.asyncio
async def test_pipeline_contiguous_stream_no_gap_bars(tmp_path: Path) -> None:
    # Contiguous confirmed bars → no spurious GAP bars emitted.
    rest = MagicMock()
    rest.get_klines.return_value = []

    open0 = int(datetime(2026, 4, 20, 0, tzinfo=UTC).timestamp() * 1000)
    open1 = open0 + INTERVAL_MS
    ws = MagicMock()
    ws.start = MagicMock()
    ws.stream = lambda: _ws_stream([_msg(open0, confirm=True), _msg(open1, confirm=True)])

    parquet_writer = MagicMock()
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)

    pipeline = MarketDataPipeline(
        rest=rest,
        ws=ws,
        bar_builder=builder,
        parquet_writer=parquet_writer,
        parquet_dir=tmp_path,
        interval_ms=INTERVAL_MS,
    )
    await asyncio.wait_for(pipeline.run(max_bars=2), timeout=2.0)

    appended = [b for (args, _) in parquet_writer.append.call_args_list for b in args[0]]
    gap_bars = [b for b in appended if b.data_quality is DataQuality.GAP]
    assert len(gap_bars) == 0
    assert len(appended) == 2


@pytest.mark.asyncio
async def test_pipeline_seeds_gap_via_rest(tmp_path: Path) -> None:
    # Parquet already has bars 0..2; gap at 3,4; pipeline should REST-fill 3,4 on start
    from src.marketdata.storage import ParquetBarWriter

    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    writer.append([_bar(i) for i in range(3)])
    writer.append([_bar(5)])  # gap: 3 and 4 missing

    rest = MagicMock()
    rest.get_klines.return_value = [_bar(3), _bar(4)]

    ws = MagicMock()
    ws.start = MagicMock()
    ws.stream = lambda: _ws_stream([])

    parquet_writer_mock = MagicMock()
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)

    pipeline = MarketDataPipeline(
        rest=rest,
        ws=ws,
        bar_builder=builder,
        parquet_writer=parquet_writer_mock,
        parquet_dir=tmp_path,
        interval_ms=INTERVAL_MS,
    )
    await asyncio.wait_for(pipeline.run(max_bars=0), timeout=2.0)

    rest.get_klines.assert_called_once()
    parquet_writer_mock.append.assert_called_once()
    ((bars,), _) = parquet_writer_mock.append.call_args
    assert len(bars) == 2
