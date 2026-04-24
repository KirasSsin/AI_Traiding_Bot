"""REST kline bar source — dedup + stall counter.

ADR 0022 sub-decisions 2 + 3.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.marketdata.models import Bar

logger = logging.getLogger(__name__)


class BarSource:
    """Poll latest closed bar via REST kline; dedup by close_time."""

    _INTERVAL_MS = {"60": 3_600_000}

    def __init__(self, *, adapter: Any, symbol: str, interval: str = "60") -> None:
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
                extra={"err": str(e), "consecutive_failures": self.consecutive_failures},
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
