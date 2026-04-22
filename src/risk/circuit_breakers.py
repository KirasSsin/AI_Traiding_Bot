"""Circuit breaker detector — pure functions, no I/O, no state."""

from dataclasses import dataclass
from decimal import Decimal

from src.risk.models import HaltState


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Thresholds passed from Settings."""

    l1_dd: Decimal        # 0.15
    l2_dd: Decimal        # 0.22
    l3_dd: Decimal        # 0.30
    flash_abs: Decimal    # 0.08
    flash_atr_mult: Decimal  # 3.0


class CircuitBreakerDetector:
    """Pure functions — no I/O, no state. Stateless detector over inputs."""

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._cfg = config

    def check_drawdown(self, *, peak: Decimal, current: Decimal) -> HaltState:
        """DD% = (peak - current) / peak.

        Returns highest triggered level (L3 > L2 > L1 > L0).
        Returns L0 when current >= peak (no drawdown) or peak <= 0.
        """
        if peak <= 0:
            return HaltState.L0
        if current >= peak:
            return HaltState.L0
        dd = (peak - current) / peak
        if dd >= self._cfg.l3_dd:
            return HaltState.L3
        if dd >= self._cfg.l2_dd:
            return HaltState.L2
        if dd >= self._cfg.l1_dd:
            return HaltState.L1
        return HaltState.L0

    def check_flash(
        self, *, bar_close: Decimal, prev_close: Decimal, atr: Decimal
    ) -> bool:
        """True if |bar_close - prev_close| / prev_close > max(flash_abs, flash_atr_mult * atr / prev_close).

        prev_close <= 0 → False (defensive).
        """
        if prev_close <= 0:
            return False
        delta_pct = abs(bar_close - prev_close) / prev_close
        atr_pct = (self._cfg.flash_atr_mult * atr) / prev_close
        threshold = max(self._cfg.flash_abs, atr_pct)
        return delta_pct > threshold
