from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from src.marketdata.models import Bar, DataQuality
from src.marketdata.storage import ParquetBarWriter


def _bar(i: int) -> Bar:
    base = datetime(2026, 4, 20, 0, tzinfo=UTC)
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
        "open_time",
        "close_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trade_count",
        "data_quality",
    }


def test_writer_leaves_no_tmp_file_on_success(tmp_path: Path) -> None:
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    path = writer.append([_bar(0)])

    assert path.exists()
    # final file written, no leftover temp artifact
    assert list(tmp_path.glob("*.tmp")) == []
    assert list(tmp_path.glob("*.parquet")) == [path]


def test_writer_atomic_no_partial_final_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate a crash during the rename step → final path must not exist
    # (write went to .tmp), and the tmp artifact must be cleaned up.
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")

    import src.marketdata.storage as storage_mod

    def _boom(_src: str, _dst: str) -> None:
        raise OSError("simulated crash during rename")

    monkeypatch.setattr(storage_mod.os, "replace", _boom)

    with pytest.raises(OSError, match="simulated crash"):
        writer.append([_bar(0)])

    # no corrupt/partial final partition left behind
    assert list(tmp_path.glob("*.parquet")) == []
    # tmp cleaned up on failure
    assert list(tmp_path.glob("*.tmp")) == []


def test_writer_append_is_additive(tmp_path: Path) -> None:
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    writer.append([_bar(i) for i in range(2)])
    writer.append([_bar(i) for i in range(2, 5)])

    files = sorted(tmp_path.glob("*.parquet"))
    total = sum(pq.read_table(f).num_rows for f in files)
    assert total == 5
