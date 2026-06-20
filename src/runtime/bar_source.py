"""REST kline bar source — dedup + stall counter.

ADR 0022 sub-decisions 2 + 3.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from src.platform.logging import get_logger

if TYPE_CHECKING:
    from src.marketdata.models import Bar

logger = get_logger(__name__)


class BarSource:
    """Poll latest closed bar via REST kline; dedup by close_time."""

    # Bybit V5 kline intervals: https://bybit-exchange.github.io/docs/v5/market/kline
    # M (month) = 30d nominal, used only for start_ms window sizing.
    _INTERVAL_MS: ClassVar[dict[str, int]] = {
        "1": 60_000,
        "3": 180_000,
        "5": 300_000,
        "15": 900_000,
        "30": 1_800_000,
        "60": 3_600_000,
        "120": 7_200_000,
        "240": 14_400_000,
        "360": 21_600_000,
        "720": 43_200_000,
        "D": 86_400_000,
        "W": 604_800_000,
        "M": 2_592_000_000,
    }

    def __init__(
        self,
        *,
        adapter: Any,
        symbol: str,
        interval: str = "60",
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        if interval not in self._INTERVAL_MS:
            raise ValueError(
                f"BarSource: unsupported interval={interval!r}; valid={list(self._INTERVAL_MS)}"
            )
        self._adapter = adapter
        self._symbol = symbol
        self._interval = interval
        self._now_fn = now_fn  # injectable clock (seconds epoch); None → module time.time
        self._last_close_ts: int | None = None  # ms epoch
        self.consecutive_failures: int = 0

    def poll(self) -> Bar | None:
        """Return latest closed bar if new, else None. Increments failure counter on error."""
        try:
            bars = self._fetch()
        except Exception as e:  # noqa: BLE001 — caller decides halt vs continue
            self.consecutive_failures += 1
            logger.warning(
                "bar_source.poll_failed",
                err=str(e),
                consecutive_failures=self.consecutive_failures,
            )
            return None

        self.consecutive_failures = 0
        if not bars:
            return None
        # DI-02 look-ahead guard: Bybit V5 kline includes the currently-forming
        # (not yet closed) candle as the last element, and rest.py hardcodes
        # is_closed=True. Drop any bar whose close_time is in the future — a bar
        # is settled only once now >= its close_time. Acting on a forming bar =
        # look-ahead (partial-bar data that will still change).
        now_ms = self._now_ms()
        latest = None
        for bar in bars:
            if int(bar.close_time.timestamp() * 1000) <= now_ms:
                latest = bar  # newest settled bar so far (bars are oldest-first)
        if latest is None:
            return None
        close_ms = int(latest.close_time.timestamp() * 1000)
        if self._last_close_ts is not None and close_ms <= self._last_close_ts:
            return None
        self._last_close_ts = close_ms
        return latest

    def should_halt(self, *, threshold: int) -> bool:
        """True if consecutive_failures hit threshold — caller emits HALT_BAR_POLL_STALL."""
        return self.consecutive_failures >= threshold

    def _now_ms(self) -> int:
        """Current epoch in ms. Uses injected clock if provided, else module time.time
        (looked up at call time so tests can monkeypatch bar_source.time.time)."""
        now_s = self._now_fn() if self._now_fn is not None else time.time()
        return int(now_s * 1000)

    def _fetch(self) -> list[Bar]:
        step_ms = self._INTERVAL_MS[self._interval]
        end_ms = self._now_ms()
        start_ms = end_ms - step_ms * 2  # last 2 bars window
        return self._adapter.get_klines(  # type: ignore[no-any-return]
            symbol=self._symbol,
            interval=self._interval,
            start_ms=start_ms,
            end_ms=end_ms,
        )
