"""Tests for BarBuilder — venue-agnostic kline aggregator."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from src.marketdata.bar_builder import BarBuilder, OutOfOrderError
from src.marketdata.models import Bar, DataQuality

INTERVAL_MS = 3_600_000  # 1H


def _msg(
    open_ms: int,
    confirm: bool = True,
    o: str = "60000",
    h: str = "60100",
    lo: str = "59900",
    c: str = "60050",
    v: str = "1.0",
) -> dict[str, object]:
    """Bybit V5 WS kline payload shape."""
    return {
        "start": open_ms,
        "end": open_ms + INTERVAL_MS,
        "interval": "60",
        "open": o,
        "close": c,
        "high": h,
        "low": lo,
        "volume": v,
        "confirm": confirm,
    }


def test_emits_bar_on_confirm() -> None:
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    result = builder.process(_msg(1745193600000, confirm=True))
    assert result is not None
    assert isinstance(result, Bar)
    assert result.is_closed is True
    assert result.data_quality is DataQuality.OK
    assert result.open == Decimal("60000")


def test_returns_none_on_non_confirm() -> None:
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    result = builder.process(_msg(1745193600000, confirm=False))
    assert result is None


def test_duplicate_non_confirmed_is_ignored() -> None:
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    builder.process(_msg(1745193600000, confirm=False))
    result = builder.process(_msg(1745193600000, confirm=False, c="60100"))
    assert result is None


def test_duplicate_after_confirmed_is_rejected() -> None:
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    builder.process(_msg(1745193600000, confirm=True))
    with pytest.raises(OutOfOrderError, match="duplicate"):
        builder.process(_msg(1745193600000, confirm=True))


def test_out_of_order_is_rejected() -> None:
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    builder.process(_msg(1745193600000, confirm=True))
    with pytest.raises(OutOfOrderError, match="out-of-order"):
        builder.process(_msg(1745193600000 - INTERVAL_MS, confirm=True))


def test_gap_emits_synthetic_gap_bar() -> None:
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    builder.process(_msg(1745193600000, confirm=True))
    gap_bar, real_bar = builder.process_with_gap_fill(
        _msg(1745193600000 + 2 * INTERVAL_MS, confirm=True)
    )
    assert gap_bar is not None
    assert gap_bar.data_quality is DataQuality.GAP
    assert gap_bar.open_time == datetime.fromtimestamp((1745193600000 + INTERVAL_MS) / 1000, tz=UTC)
    assert real_bar is not None
    assert real_bar.data_quality is DataQuality.OK
