"""BarSource — REST kline poller с dedup + stall counter.

ADR 0022 sub-decisions 2 + 3.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from src.marketdata.models import Bar, DataQuality


def _bar(open_ms: int, close_ms: int) -> Bar:
    return Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=datetime.fromtimestamp(open_ms / 1000, tz=UTC),
        close_time=datetime.fromtimestamp(close_ms / 1000, tz=UTC),
        open=Decimal("60000"),
        high=Decimal("60100"),
        low=Decimal("59900"),
        close=Decimal("60050"),
        volume=Decimal("10"),
        trade_count=0,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def test_bar_source_dedup_same_close_ts() -> None:
    """Two polls with same closed bar → emit once, then None."""
    from src.runtime.bar_source import BarSource

    adapter = MagicMock()
    bar = _bar(1_700_000_000_000, 1_700_003_600_000)
    adapter.get_klines.return_value = [bar]

    src = BarSource(adapter=adapter, symbol="BTCUSDT", interval="60")
    first = src.poll()
    second = src.poll()
    assert first == bar
    assert second is None
    assert src.consecutive_failures == 0


def test_bar_source_emits_new_bar_on_close() -> None:
    from src.runtime.bar_source import BarSource

    adapter = MagicMock()
    bar1 = _bar(1_700_000_000_000, 1_700_003_600_000)
    bar2 = _bar(1_700_003_600_000, 1_700_007_200_000)
    adapter.get_klines.side_effect = [[bar1], [bar2]]

    src = BarSource(adapter=adapter, symbol="BTCUSDT", interval="60")
    assert src.poll() == bar1
    assert src.poll() == bar2
