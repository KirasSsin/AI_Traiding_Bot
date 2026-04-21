"""Tests for find_gaps."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.marketdata.gaps import find_gaps
from src.marketdata.models import Bar, DataQuality
from src.marketdata.storage import ParquetBarWriter

INTERVAL_MS = 3_600_000


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


def test_no_gaps_returns_empty(tmp_path: Path) -> None:
    w = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    w.append([_bar(i) for i in range(5)])
    assert find_gaps(tmp_path, interval_ms=INTERVAL_MS) == []


def test_single_gap_detected(tmp_path: Path) -> None:
    w = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    w.append([_bar(i) for i in [0, 1, 2]])
    w.append([_bar(i) for i in [5, 6]])  # missing 3 and 4
    gaps = find_gaps(tmp_path, interval_ms=INTERVAL_MS)
    assert len(gaps) == 1
    gap_start, gap_end = gaps[0]
    expected_start = datetime(2026, 4, 20, 3, tzinfo=UTC)  # close_time of bar 2
    expected_end = datetime(2026, 4, 20, 5, tzinfo=UTC)  # open_time of bar 5
    assert gap_start == expected_start
    assert gap_end == expected_end


def test_empty_dir_returns_empty(tmp_path: Path) -> None:
    assert find_gaps(tmp_path, interval_ms=INTERVAL_MS) == []
