"""REST-vs-REST consecutive bar price quality detector.

Sprint 9 Q1 (per pre-s9-backlog.md verdict).

Detector compares current REST closed bar price vs previously observed
REST closed bar price (held in-memory). Designed for use by RuntimeManager
after BarSource.poll() returns a new closed bar.

Why REST-vs-REST (not WS+REST):
- WS kline subscription does not exist (ws_private only subscribes to
  order + wallet topics).
- Wiring WS kline contradicts S8a ADR 0022 async/sync deferral к S9+.
- WS partial-bar updates create false-positive risk при per-bar comparison.

Threshold rationale (0.5% relative on 1H BTCUSDT @ ~$100k):
- ~$500 instantaneous move bar-to-bar is unusual для 1H granularity.
- Catches stuck/corrupted feed без new infrastructure.
- Single tunable knob (no per-symbol overrides for v0.1).
"""
from __future__ import annotations

from decimal import Decimal

from src.platform.logging import get_logger

logger = get_logger(__name__)


class BarPriceQualityDetector:
    """Stateless detector — caller owns persistence of last_close baseline.

    Usage:
        det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
        for bar in bar_source.poll_iter():
            if det.check(current_close=bar.close):
                coordinator.request_halt(reason=ReasonCode.HALT_DATA_QUALITY)
    """

    def __init__(self, *, threshold_pct: Decimal) -> None:
        if threshold_pct <= 0:
            raise ValueError(
                f"BarPriceQualityDetector: threshold_pct must be > 0, got {threshold_pct}"
            )
        self._threshold_pct = threshold_pct
        self._last_close: Decimal | None = None

    def check(self, *, current_close: Decimal) -> bool:
        """Return True if deviation > threshold (halt-worthy).

        First call establishes baseline → returns False.
        Subsequent calls compare against last_close, then update baseline.
        Defensive: prior_close ≤ 0 → False (cannot compute relative deviation).
        """
        prior = self._last_close
        self._last_close = current_close

        if prior is None:
            return False  # No baseline yet
        if prior <= 0:
            return False  # Defensive: avoid division by zero or negative anchor
        deviation_pct = abs(current_close - prior) / prior
        if deviation_pct > self._threshold_pct:
            logger.warning(
                "data_quality.deviation_exceeds_threshold",
                prior_close=str(prior),
                current_close=str(current_close),
                deviation_pct=str(deviation_pct),
                threshold_pct=str(self._threshold_pct),
            )
            return True
        return False
