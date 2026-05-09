"""Volume breakout long-only strategy (S39 production integration per ADR 0059 LOCKED).

LOCKED parameters per ADR 0059 — anti-snooping pre-registration (autoresearch sweep#1644):
  - lookback_n=9 (Donchian channel entry lookback ~1.5 days @ 4H)
  - exit_lookback_n=8 (Donchian channel exit lookback)
  - vol_window=10 (volume rolling mean window)
  - vol_mult=1.4563 (volume must exceed mean * this multiplier)
  - atr_period=9 (Wilder ATR period)
  - atr_stop_mult=2.9663 (stop loss = entry_price - ATR * this)
  - signal_side_mode="long_only" (FSM invariant — NEVER emits SHORT)

Entry rule (LONG):
  close[-2] > max(high[-(lookback_n+1):-1]) AND
  volume[-2] > mean(volume[-(vol_window+1):-1]) * vol_mult AND
  current_side == FLAT

Exit rule (FLAT) — checked in priority order:
  IF current LONG:
    1. Channel exit: close[-2] < min(low[-(exit_lookback_n+1):-1])
       -> EXIT_FLAT_VOLUME_CHANNEL
    2. ATR stop intrabar: bar.low <= entry_price - atr_stop_mult * ATR
       -> EXIT_FLAT_ATR_STOP_VB

Invariant: signal evaluated on closed bar(T) using data through bar(T-1)
(no look-ahead per execution-timing.md). Execution at open(T+1) per
existing FSM contract.

Thread-safety: NOT thread-safe — single-producer per symbol pattern
(per ADR 0023 single-writer invariant).

Reference implementation: research/strategies.py::strat_volume_breakout
(branch autoresearch/donchian-may8 commit fff54ee).
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import numpy as np

from src.marketdata.models import Bar
from src.risk.reason_codes import ReasonCode
from src.signalgen.indicators import atr
from src.signalgen.models import Signal, SignalSide

# ADR 0059 LOCKED — DO NOT modify without a new ADR amendment.
# Source: autoresearch sweep#1644, branch autoresearch/donchian-may8 commit fff54ee.
VOLUME_BREAKOUT_LOCKED_PARAMS: dict[str, object] = {
    "lookback_n": 9,
    "exit_lookback_n": 8,
    "vol_window": 10,
    "vol_mult": Decimal("1.4563"),
    "atr_period": 9,
    "atr_stop_mult": Decimal("2.9663"),
    "signal_side_mode": "long_only",
}

_ZERO = Decimal("0")


class VolumeBreakoutStrategy:
    """Stateful volume breakout long-only strategy.

    Internal state: rolling deque of last (buffer_size) bars, current_side,
    and entry_price when LONG.

    buffer_size = max(lookback_n, exit_lookback_n, atr_period, vol_window) + 5
    warmup gate = max(lookback_n, exit_lookback_n, atr_period, vol_window) + 2

    Signal contract: on_bar(bar) -> Signal | None
      - Returns None for unclosed bars, during warmup, or when no condition fires.
      - Never emits SignalSide.SHORT.
    """

    def __init__(self, *, symbol: str) -> None:
        self._symbol = symbol
        self._lookback_n: int = int(VOLUME_BREAKOUT_LOCKED_PARAMS["lookback_n"])  # type: ignore[call-overload]
        self._exit_lookback_n: int = int(VOLUME_BREAKOUT_LOCKED_PARAMS["exit_lookback_n"])  # type: ignore[call-overload]
        self._vol_window: int = int(VOLUME_BREAKOUT_LOCKED_PARAMS["vol_window"])  # type: ignore[call-overload]
        self._vol_mult: float = float(VOLUME_BREAKOUT_LOCKED_PARAMS["vol_mult"])  # type: ignore[arg-type]
        self._atr_period: int = int(VOLUME_BREAKOUT_LOCKED_PARAMS["atr_period"])  # type: ignore[call-overload]
        self._atr_stop_mult: float = float(VOLUME_BREAKOUT_LOCKED_PARAMS["atr_stop_mult"])  # type: ignore[arg-type]

        self._warmup: int = (
            max(self._lookback_n, self._exit_lookback_n, self._atr_period, self._vol_window) + 2
        )
        self._buffer_size: int = (
            max(self._lookback_n, self._exit_lookback_n, self._atr_period, self._vol_window) + 5
        )

        self._highs: deque[float] = deque(maxlen=self._buffer_size)
        self._lows: deque[float] = deque(maxlen=self._buffer_size)
        self._closes: deque[float] = deque(maxlen=self._buffer_size)
        self._volumes: deque[float] = deque(maxlen=self._buffer_size)

        self._current_side: SignalSide = SignalSide.FLAT
        self._entry_price: float | None = None

    # ------------------------------------------------------------------
    # Public contract
    # ------------------------------------------------------------------

    def on_bar(self, bar: Bar) -> Signal | None:
        """Evaluate strategy on a closed bar. Returns Signal or None.

        Invariants enforced:
        - bar.is_closed must be True (live bar guard).
        - Warmup gate: min buffer depth before any signal.
        - Long-only: NEVER returns a SHORT signal.
        """
        if not bar.is_closed:
            return None

        # Append OHLCV to rolling buffers
        self._highs.append(float(bar.high))
        self._lows.append(float(bar.low))
        self._closes.append(float(bar.close))
        self._volumes.append(float(bar.volume))

        # Warmup gate
        if len(self._closes) < self._warmup:
            return None

        # Slice arrays for look-ahead-safe computations.
        # Index [-1] = bar(T) just appended; [-2] = bar(T-1).
        # Signal conditions use data through bar(T-1) exclusively.
        highs_arr = np.array(self._highs, dtype=np.float64)
        lows_arr = np.array(self._lows, dtype=np.float64)
        closes_arr = np.array(self._closes, dtype=np.float64)
        volumes_arr = np.array(self._volumes, dtype=np.float64)

        prev_close = closes_arr[-2]
        prev_vol = volumes_arr[-2]

        # Reference windows exclude current bar (T) — use [-(N+1):-1]
        ref_high_window = highs_arr[-(self._lookback_n + 1) : -1]
        ref_low_window = lows_arr[-(self._exit_lookback_n + 1) : -1]
        vol_mean_window = volumes_arr[-(self._vol_window + 1) : -1]

        if len(ref_high_window) < self._lookback_n or len(ref_low_window) < self._exit_lookback_n:
            return None

        ref_high = float(np.max(ref_high_window))
        ref_low = float(np.min(ref_low_window))
        vol_mean = float(np.mean(vol_mean_window)) if len(vol_mean_window) > 0 else 0.0

        atr_val = self._compute_wilder_atr(highs_arr, lows_arr, closes_arr)

        # ------------------------------------------------------------------
        # Entry logic — FLAT → LONG
        # ------------------------------------------------------------------
        if self._current_side == SignalSide.FLAT:
            volume_confirm = prev_vol > vol_mean * self._vol_mult
            breakout = prev_close > ref_high
            if breakout and volume_confirm:
                self._current_side = SignalSide.LONG
                self._entry_price = prev_close
                return self._build_signal(
                    bar,
                    SignalSide.LONG,
                    atr_val=atr_val,
                    reason=ReasonCode.ENTRY_LONG_VOLUME_BREAKOUT,
                )
            return None

        # ------------------------------------------------------------------
        # Exit logic — LONG → FLAT
        # ------------------------------------------------------------------
        if self._current_side == SignalSide.LONG:
            # Priority 1: channel exit (close[-2] < channel low)
            if prev_close < ref_low:
                self._current_side = SignalSide.FLAT
                self._entry_price = None
                return self._build_signal(
                    bar,
                    SignalSide.FLAT,
                    atr_val=atr_val,
                    reason=ReasonCode.EXIT_FLAT_VOLUME_CHANNEL,
                )
            # Priority 2: ATR stop intrabar (current bar low breaches stop level)
            if (
                self._entry_price is not None
                and atr_val is not None
                and float(bar.low) <= self._entry_price - self._atr_stop_mult * atr_val
            ):
                self._current_side = SignalSide.FLAT
                self._entry_price = None
                return self._build_signal(
                    bar,
                    SignalSide.FLAT,
                    atr_val=atr_val,
                    reason=ReasonCode.EXIT_FLAT_ATR_STOP_VB,
                )

        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_wilder_atr(
        self,
        highs_arr: np.ndarray,
        lows_arr: np.ndarray,
        closes_arr: np.ndarray,
    ) -> float | None:
        """Wilder ATR computed on current rolling buffer slices."""
        if len(closes_arr) < self._atr_period + 1:
            return None
        atr_arr: np.ndarray = atr(highs_arr, lows_arr, closes_arr, self._atr_period)
        if len(atr_arr) == 0 or np.isnan(atr_arr[-1]):
            return None
        return float(atr_arr[-1])

    def _build_signal(
        self,
        bar: Bar,
        side: SignalSide,
        *,
        atr_val: float | None,
        reason: ReasonCode,
    ) -> Signal:
        """Construct Signal with zero-placeholder fields for indicators not computed."""
        atr_decimal = Decimal(str(atr_val)) if atr_val is not None else _ZERO
        return Signal(
            signal_id=uuid4(),
            symbol=self._symbol,
            side=side,
            bar_close_time=bar.close_time,
            generated_at=datetime.now(UTC),
            ema_fast=_ZERO,
            ema_slow=_ZERO,
            adx_14=_ZERO,
            plus_di_14=_ZERO,
            minus_di_14=_ZERO,
            rsi_14=_ZERO,
            atr_14=atr_decimal,
            reason=reason.value,
        )
