"""REST kline bar source — dedup + stall counter.

ADR 0022 sub-decisions 2 + 3.
"""
from __future__ import annotations

import time
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

    def __init__(self, *, adapter: Any, symbol: str, interval: str = "60") -> None:
        if interval not in self._INTERVAL_MS:
            raise ValueError(
                f"BarSource: unsupported interval={interval!r}; "
                f"valid={list(self._INTERVAL_MS)}"
            )
        self._adapter = adapter
        self._symbol = symbol
        self._interval = interval
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
        latest = bars[-1]
        close_ms = int(latest.close_time.timestamp() * 1000)
        if self._last_close_ts is not None and close_ms <= self._last_close_ts:
            return None
        self._last_close_ts = close_ms
        return latest

    def should_halt(self, *, threshold: int) -> bool:
        """True if consecutive_failures hit threshold — caller emits HALT_BAR_POLL_STALL."""
        return self.consecutive_failures >= threshold

    def _fetch(self) -> list[Bar]:
        step_ms = self._INTERVAL_MS[self._interval]
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - step_ms * 2  # last 2 bars window
        return self._adapter.get_klines(  # type: ignore[no-any-return]
            symbol=self._symbol,
            interval=self._interval,
            start_ms=start_ms,
            end_ms=end_ms,
        )
