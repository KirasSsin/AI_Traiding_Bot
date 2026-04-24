"""BarSource — REST kline poller с dedup + stall counter.

ADR 0022 sub-decisions 2 + 3.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from src.marketdata.models import Bar, DataQuality
from src.runtime.bar_source import BarSource


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


def test_bar_source_calls_adapter_with_recent_window(monkeypatch):
    """_fetch must call adapter.get_klines with last 2 bars worth of window (start/end_ms)."""
    from src.runtime.bar_source import BarSource

    captured: dict = {}

    class FakeAdapter:
        def get_klines(self, *, symbol, interval, start_ms, end_ms, limit_per_call=1000):  # noqa: ARG002
            captured["symbol"] = symbol
            captured["interval"] = interval
            captured["start_ms"] = start_ms
            captured["end_ms"] = end_ms
            return []

    src = BarSource(adapter=FakeAdapter(), symbol="BTCUSDT", interval="60")
    # Freeze "now" via monkeypatch on time.time used inside _fetch
    monkeypatch.setattr("src.runtime.bar_source.time.time", lambda: 1_700_010_000.0)
    src.poll()

    assert captured["symbol"] == "BTCUSDT"
    assert captured["interval"] == "60"
    # Window = at least last 2 bars (interval=60 → 7_200_000 ms)
    assert captured["end_ms"] - captured["start_ms"] >= 7_200_000
    # end_ms ≈ now (1_700_010_000_000 ± 1s)
    assert abs(captured["end_ms"] - 1_700_010_000_000) < 1_000


def test_bar_source_failure_increments_counter():
    from src.runtime.bar_source import BarSource

    class BadAdapter:
        def get_klines(self, **_):
            raise RuntimeError("network down")

    src = BarSource(adapter=BadAdapter(), symbol="BTCUSDT", interval="60")
    assert src.poll() is None
    assert src.consecutive_failures == 1
    assert src.poll() is None
    assert src.consecutive_failures == 2


def test_bar_source_should_halt_at_threshold():
    from src.runtime.bar_source import BarSource

    class BadAdapter:
        def get_klines(self, **_):
            raise RuntimeError("X")

    src = BarSource(adapter=BadAdapter(), symbol="BTCUSDT", interval="60")
    # 23 failures — below threshold
    for _ in range(23):
        src.poll()
    assert src.should_halt(threshold=24) is False
    # 24th — at threshold
    src.poll()
    assert src.should_halt(threshold=24) is True


def test_bar_source_recovery_resets_counter():
    from src.runtime.bar_source import BarSource

    bar = _bar(1_700_000_000_000, 1_700_003_600_000)
    states = [RuntimeError("X"), RuntimeError("X"), [bar]]

    class FlapAdapter:
        def __init__(self):
            self._i = 0

        def get_klines(self, **_):
            v = states[self._i]
            self._i += 1
            if isinstance(v, BaseException):
                raise v
            return v

    src = BarSource(adapter=FlapAdapter(), symbol="BTCUSDT", interval="60")
    src.poll()
    src.poll()
    assert src.consecutive_failures == 2
    src.poll()  # recovery
    assert src.consecutive_failures == 0
    assert src.should_halt(threshold=24) is False


@pytest.mark.parametrize(
    "interval",
    ["1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"],
)
def test_bar_source_init_accepts_all_bybit_intervals(interval):
    """All 13 Bybit V5 kline interval strings accepted at init."""
    src = BarSource(adapter=object(), symbol="BTCUSDT", interval=interval)
    assert src._interval == interval


def test_bar_source_init_rejects_unknown_interval():
    """Unknown interval fails fast at init, not at first poll."""
    with pytest.raises(ValueError, match="unsupported interval"):
        BarSource(adapter=object(), symbol="BTCUSDT", interval="99")


def test_bar_source_init_rejects_empty_interval():
    """Empty string interval also fails."""
    with pytest.raises(ValueError, match="unsupported interval"):
        BarSource(adapter=object(), symbol="BTCUSDT", interval="")
