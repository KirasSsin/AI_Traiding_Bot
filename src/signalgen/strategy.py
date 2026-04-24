"""EMA-crossover + ADX/RSI/ATR trading strategy (v0.1).

Reference: wiki/trading/strategies/ema-crossover-adx-rsi.md.
ADR: wiki/project/decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover.md.
Invariant: signal on close(T) → execution at open(T+1)
  (wiki/project/architecture/execution-timing.md).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import numpy as np

from src.marketdata.models import Bar
from src.signalgen.indicators import adx, atr, ema, minus_di, plus_di, rsi
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

    def _append_bar(self, bar: Bar) -> bool:
        """Filter + dedup + append + buffer truncate. Returns True if bar landed in buffer."""
        if not bar.is_closed:
            return False
        if bar.symbol != self._symbol:
            return False
        # Dedup + out-of-order guard: monotonic close_time only.
        if self._bars and bar.close_time <= self._bars[-1].close_time:
            return False
        self._bars.append(bar)
        if len(self._bars) > self._buffer_size:
            self._bars = self._bars[-self._buffer_size :]
        return True

    def warmup(self, bar: Bar) -> None:
        """Feed historical bar to rolling buffer WITHOUT signal emission.

        ADR 0022 sub-decision 2 — catch-up на startup защищает от look-ahead
        trade events на bars из прошлого. Buffer seeds identically to on_bar,
        only the signal-eval branch is skipped. Returns None always.
        """
        self._append_bar(bar)

    def on_bar(self, bar: Bar) -> Signal | None:
        """Main entry point. Called once per closed bar by MarketData pipeline."""
        if not self._append_bar(bar):
            return None

        # Warm-up: need >= max(ema_slow, 2·adx_period) + 1 closed bars
        # (ADX needs 2·adx_period for double-smoothing seeding).
        min_required = max(self._ema_slow_n, 2 * self._adx_n) + 1
        if len(self._bars) < min_required:
            return None

        # Compute indicators on full buffer (simple — recompute each call).
        closes = np.array([float(b.close) for b in self._bars], dtype=np.float64)
        highs = np.array([float(b.high) for b in self._bars], dtype=np.float64)
        lows = np.array([float(b.low) for b in self._bars], dtype=np.float64)

        ema_fast_arr = ema(closes, self._ema_fast_n, mode="classical")
        ema_slow_arr = ema(closes, self._ema_slow_n, mode="classical")
        adx_arr = adx(highs, lows, closes, self._adx_n)
        pdi_arr = plus_di(highs, lows, closes, self._adx_n)
        mdi_arr = minus_di(highs, lows, closes, self._adx_n)
        rsi_arr = rsi(closes, self._rsi_n)
        atr_arr = atr(highs, lows, closes, self._atr_n)

        snapshot = {
            "ema_fast": ema_fast_arr[-1],
            "ema_slow": ema_slow_arr[-1],
            "adx": adx_arr[-1],
            "plus_di": pdi_arr[-1],
            "minus_di": mdi_arr[-1],
            "rsi": rsi_arr[-1],
            "atr": atr_arr[-1],
        }
        # Any NaN in latest → indicators not yet warm.
        if any(np.isnan(v) for v in snapshot.values()):
            return None

        # Entry rule (LONG): cross up EMA_fast×EMA_slow at T-1→T, ADX>threshold,
        # +DI>-DI, RSI<overbought. Cross = fast[T] > slow[T] AND fast[T-1] <= slow[T-1].
        cross_up = bool(
            ema_fast_arr[-1] > ema_slow_arr[-1] and ema_fast_arr[-2] <= ema_slow_arr[-2]
        )
        trend_strong = Decimal(str(snapshot["adx"])) > self._adx_threshold
        bullish_dir = snapshot["plus_di"] > snapshot["minus_di"]
        not_overbought = Decimal(str(snapshot["rsi"])) < self._rsi_overbought

        if (
            cross_up
            and trend_strong
            and bullish_dir
            and not_overbought
            and self._current_side == SignalSide.FLAT
        ):
            self._current_side = SignalSide.LONG
            return self._build_signal(
                bar,
                SignalSide.LONG,
                snapshot,
                reason="ENTRY_LONG_EMA_CROSS_UP",
            )

        # Exit rule (FLAT): если current LONG, и EMA flips down + -DI доминирует → FLAT.
        if self._current_side == SignalSide.LONG:
            flip_down = ema_fast_arr[-1] < ema_slow_arr[-1]
            bearish_dir = snapshot["minus_di"] > snapshot["plus_di"]
            if flip_down and bearish_dir:
                self._current_side = SignalSide.FLAT
                return self._build_signal(
                    bar,
                    SignalSide.FLAT,
                    snapshot,
                    reason="EXIT_FLAT_SIGNAL_FLIP",
                )

        return None

    def _build_signal(
        self,
        bar: Bar,
        side: SignalSide,
        snapshot: dict[str, float],
        reason: str,
    ) -> Signal:
        return Signal(
            signal_id=uuid4(),
            symbol=self._symbol,
            side=side,
            bar_close_time=bar.close_time,
            generated_at=datetime.now(UTC),
            ema_fast=Decimal(str(snapshot["ema_fast"])),
            ema_slow=Decimal(str(snapshot["ema_slow"])),
            adx_14=Decimal(str(snapshot["adx"])),
            plus_di_14=Decimal(str(snapshot["plus_di"])),
            minus_di_14=Decimal(str(snapshot["minus_di"])),
            rsi_14=Decimal(str(snapshot["rsi"])),
            atr_14=Decimal(str(snapshot["atr"])),
            reason=reason,
        )
