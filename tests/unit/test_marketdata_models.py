from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from src.marketdata.models import Bar, DataQuality


def _ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=UTC)


def test_bar_valid():
    bar = Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=_ts("2026-04-20T00:00:00"),
        close_time=_ts("2026-04-20T01:00:00"),
        open=Decimal("60000"),
        high=Decimal("60500"),
        low=Decimal("59800"),
        close=Decimal("60200"),
        volume=Decimal("125.5"),
        trade_count=3421,
        is_closed=True,
        data_quality=DataQuality.OK,
    )
    assert bar.symbol == "BTCUSDT"
    assert bar.is_closed is True


def test_bar_high_must_be_max():
    with pytest.raises(ValidationError, match="high"):
        Bar(
            symbol="BTCUSDT",
            interval="1h",
            open_time=_ts("2026-04-20T00:00:00"),
            close_time=_ts("2026-04-20T01:00:00"),
            open=Decimal("60000"),
            high=Decimal("59900"),
            low=Decimal("59800"),
            close=Decimal("60200"),
            volume=Decimal("1"),
            trade_count=1,
            is_closed=True,
            data_quality=DataQuality.OK,
        )


def test_bar_low_must_be_min():
    with pytest.raises(ValidationError, match="low"):
        Bar(
            symbol="BTCUSDT",
            interval="1h",
            open_time=_ts("2026-04-20T00:00:00"),
            close_time=_ts("2026-04-20T01:00:00"),
            open=Decimal("60000"),
            high=Decimal("60500"),
            low=Decimal("60100"),
            close=Decimal("60200"),
            volume=Decimal("1"),
            trade_count=1,
            is_closed=True,
            data_quality=DataQuality.OK,
        )


def test_bar_volume_non_negative():
    with pytest.raises(ValidationError):
        Bar(
            symbol="BTCUSDT",
            interval="1h",
            open_time=_ts("2026-04-20T00:00:00"),
            close_time=_ts("2026-04-20T01:00:00"),
            open=Decimal("60000"),
            high=Decimal("60500"),
            low=Decimal("59800"),
            close=Decimal("60200"),
            volume=Decimal("-1"),
            trade_count=1,
            is_closed=True,
            data_quality=DataQuality.OK,
        )


def test_bar_close_time_after_open_time():
    with pytest.raises(ValidationError, match="close_time"):
        Bar(
            symbol="BTCUSDT",
            interval="1h",
            open_time=_ts("2026-04-20T01:00:00"),
            close_time=_ts("2026-04-20T00:00:00"),
            open=Decimal("60000"),
            high=Decimal("60500"),
            low=Decimal("59800"),
            close=Decimal("60200"),
            volume=Decimal("1"),
            trade_count=1,
            is_closed=True,
            data_quality=DataQuality.OK,
        )
