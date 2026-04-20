from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from src.marketdata.models import Bar, DataQuality
from src.marketdata.storage import ParquetBarWriter


def _bar(i: int) -> Bar:
    base = datetime(2026, 4, 20, 0, tzinfo=timezone.utc)
    return Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=base + timedelta(hours=i),
        close_time=base + timedelta(hours=i + 1),
        open=Decimal("60000"),
        high=Decimal("60500"),
        low=Decimal("59800"),
        close=Decimal("60200"),
        volume=Decimal("1.5"),
        trade_count=100,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def test_writer_creates_file_and_persists_bars(tmp_path: Path) -> None:
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    bars = [_bar(i) for i in range(3)]

    writer.append(bars)

    files = list(tmp_path.glob("*.parquet"))
    assert len(files) == 1
    table = pq.read_table(files[0])
    assert table.num_rows == 3
    assert set(table.schema.names) >= {
        "open_time", "close_time", "open", "high", "low", "close",
        "volume", "trade_count", "data_quality",
    }


def test_writer_append_is_additive(tmp_path: Path) -> None:
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    writer.append([_bar(i) for i in range(2)])
    writer.append([_bar(i) for i in range(2, 5)])

    files = sorted(tmp_path.glob("*.parquet"))
    total = sum(pq.read_table(f).num_rows for f in files)
    assert total == 5
