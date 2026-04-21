"""Venue-agnostic kline → Bar aggregator with dedup/order/gap invariants."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from src.marketdata.models import Bar, DataQuality


class OutOfOrderError(RuntimeError):
    """WS kline arrived out-of-order or duplicated after confirm=True."""


_INTERVAL_LITERAL: dict[int, Literal["1m", "5m", "15m", "1h", "4h", "1d"]] = {
    60_000: "1m",
    300_000: "5m",
    900_000: "15m",
    3_600_000: "1h",
    14_400_000: "4h",
    86_400_000: "1d",
}


class BarBuilder:
    """Accepts WS kline dicts; emits Bar only on `confirm=true`."""

    def __init__(self, symbol: str, interval_ms: int) -> None:
        self._symbol = symbol
        self._interval_ms = interval_ms
        self._interval_literal = _INTERVAL_LITERAL[interval_ms]
        self._last_confirmed_open_ms: int | None = None

    def process(self, msg: dict[str, object]) -> Bar | None:
        """Process a single WS message. Returns Bar if closed, else None."""
        open_ms = int(msg["start"])  # type: ignore[call-overload]
        confirm = bool(msg["confirm"])

        self._check_order(open_ms)

        if not confirm:
            return None

        bar = self._build_bar(msg, data_quality=DataQuality.OK)
        self._last_confirmed_open_ms = open_ms
        return bar

    def process_with_gap_fill(self, msg: dict[str, object]) -> tuple[Bar | None, Bar | None]:
        """Process msg; if gap detected since last confirmed, emit synthetic
        GAP bar + the real bar. Returns (first_gap_bar, real_bar).
        """
        open_ms = int(msg["start"])  # type: ignore[call-overload]
        gap_bar: Bar | None = None
        if (
            self._last_confirmed_open_ms is not None
            and open_ms > self._last_confirmed_open_ms + self._interval_ms
        ):
            gap_open_ms = self._last_confirmed_open_ms + self._interval_ms
            gap_bar = self._synth_gap_bar(gap_open_ms)
        real_bar = self.process(msg)
        return gap_bar, real_bar

    def _check_order(self, open_ms: int) -> None:
        if self._last_confirmed_open_ms is None:
            return
        if open_ms == self._last_confirmed_open_ms:
            raise OutOfOrderError(f"duplicate open_ms={open_ms} after confirm")
        if open_ms < self._last_confirmed_open_ms:
            raise OutOfOrderError(
                f"out-of-order: {open_ms} < last confirmed {self._last_confirmed_open_ms}"
            )

    def _build_bar(self, msg: dict[str, object], data_quality: DataQuality) -> Bar:
        open_ms = int(msg["start"])  # type: ignore[call-overload]
        open_time = datetime.fromtimestamp(open_ms / 1000, tz=UTC)
        close_time = open_time + timedelta(milliseconds=self._interval_ms)
        return Bar(
            symbol=self._symbol,
            interval=self._interval_literal,
            open_time=open_time,
            close_time=close_time,
            open=Decimal(str(msg["open"])),
            high=Decimal(str(msg["high"])),
            low=Decimal(str(msg["low"])),
            close=Decimal(str(msg["close"])),
            volume=Decimal(str(msg["volume"])),
            trade_count=0,
            is_closed=True,
            data_quality=data_quality,
        )

    def _synth_gap_bar(self, open_ms: int) -> Bar:
        """Synthetic GAP bar — per edge-cases.md #1, NO forward-fill OHLC."""
        assert self._last_confirmed_open_ms is not None
        open_time = datetime.fromtimestamp(open_ms / 1000, tz=UTC)
        close_time = open_time + timedelta(milliseconds=self._interval_ms)
        return Bar(
            symbol=self._symbol,
            interval=self._interval_literal,
            open_time=open_time,
            close_time=close_time,
            open=Decimal("0"),
            high=Decimal("0"),
            low=Decimal("0"),
            close=Decimal("0"),
            volume=Decimal("0"),
            trade_count=0,
            is_closed=True,
            data_quality=DataQuality.GAP,
        )
