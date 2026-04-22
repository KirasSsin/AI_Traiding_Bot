"""EMA-crossover + ADX/RSI/ATR trading strategy (v0.1).

Reference: wiki/trading/strategies/ema-crossover-adx-rsi.md.
ADR: wiki/project/decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover.md.
Invariant: signal on close(T) → execution at open(T+1)
  (wiki/project/architecture/execution-timing.md).
"""

from datetime import datetime
from decimal import Decimal

from src.marketdata.models import Bar
from src.signalgen.models import Signal, SignalSide


class EmaCrossoverAdxRsiStrategy:
    """Stateful strategy: feed closed bars one-by-one, get Signal | None.

    Internal state: rolling buffer of last N bars (N = max indicator warm-up + 5).
    Emission rule: emit signal **only** on bar with is_closed=True when all gates pass.

    Thread-safety: **not thread-safe.** One instance — one producer thread
    (MarketData pipeline).
    """

    def __init__(
        self,
        *,
        symbol: str,
        ema_fast: int,
        ema_slow: int,
        adx_period: int,
        adx_threshold: Decimal,
        rsi_period: int,
        rsi_oversold: Decimal,
        rsi_overbought: Decimal,
        atr_period: int,
    ) -> None:
        if ema_fast >= ema_slow:
            raise ValueError("ema_fast must be < ema_slow")
        self._symbol = symbol
        self._ema_fast_n = ema_fast
        self._ema_slow_n = ema_slow
        self._adx_n = adx_period
        self._adx_threshold = adx_threshold
        self._rsi_n = rsi_period
        self._rsi_oversold = rsi_oversold
        self._rsi_overbought = rsi_overbought
        self._atr_n = atr_period

        # Buffer: need >= slow + 2·adx_period for ADX double-smoothing warm-up.
        self._buffer_size = max(ema_slow, 2 * adx_period, atr_period, rsi_period) + 5
        self._bars: list[Bar] = []
        self._last_signal_close_time: datetime | None = None
        self._current_side: SignalSide = SignalSide.FLAT

    def on_bar(self, bar: Bar) -> Signal | None:
        """Main entry point. Called once per closed bar by MarketData pipeline."""
        if not bar.is_closed:
            return None
        if bar.symbol != self._symbol:
            return None

        self._bars.append(bar)
        if len(self._bars) > self._buffer_size:
            self._bars = self._bars[-self._buffer_size :]

        # Warm-up: need >= max(ema_slow, 2·adx_period) + 1 closed bars
        # (ADX needs 2·adx_period for double-smoothing seeding).
        min_required = max(self._ema_slow_n, 2 * self._adx_n) + 1
        if len(self._bars) < min_required:
            return None

        # Signal emission logic — Tasks 9-12.
        return None
