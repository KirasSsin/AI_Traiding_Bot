"""ATR breakout long-only strategy (S40 production integration per ADR 0060 LOCKED).

LOCKED parameters per ADR 0060 — anti-snooping pre-registration (autoresearch BTCUSDT 240 iter1):
  - atr_period: 9 (Wilder ATR for breakout signal)
  - atr_breakout_mult: 2.5 (entry/exit multiplier vs ATR band)
  - atr_stop_period: 21 (Wilder ATR for trailing stop loss)
  - atr_stop_mult: 1.5 (stop loss = entry_close - atr_stop * this)
  - signal_side_mode: "long_only" (FSM invariant — NEVER emits SHORT)

Entry rule (LONG — bar i-1 signal, fill at open[i]):
  close[i-1] > close[i-2] + atr_breakout_mult * atr[i-2]
  AND current_side == FLAT

Exit rules (FLAT) — checked in priority order:
  IF current LONG:
    1. Reverse ATR breakout: close[i-1] < close[i-2] - atr_breakout_mult * atr[i-2]
       -> EXIT_FLAT_ATR_REVERSE
    2. ATR stop intrabar: bar.low <= entry_close - atr_stop_mult * atr_stop[-1]
       -> EXIT_FLAT_ATR_STOP_AB

Invariant: signal evaluated on closed bar(T) using data through bar(T-1)
(no look-ahead per execution-timing.md). Execution at open(T+1) per
existing FSM contract.

Thread-safety: NOT thread-safe — single-producer per symbol pattern
(per ADR 0023 single-writer invariant).

Reference implementation: scripts/autoresearch_endless.py::strat_atr_breakout
(BTCUSDT_240 autoresearch iter1 best).
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import numpy as np

from src.marketdata.models import Bar
from src.risk.reason_codes import ReasonCode
from src.signalgen.models import Signal, SignalSide

# ADR 0060 LOCKED — DO NOT modify without a new ADR amendment.
# Source: scripts/autoresearch_endless.py, BTCUSDT_240, autoresearch iter1 best.
ATR_BREAKOUT_LOCKED_PARAMS: dict[str, object] = {
    "atr_period": 9,
    "atr_breakout_mult": Decimal("2.5"),
    "atr_stop_period": 21,
    "atr_stop_mult": Decimal("1.5"),
    "signal_side_mode": "long_only",
}

_ZERO = Decimal("0")


class ATRBreakoutStrategy:
    """Stateful ATR breakout long-only strategy.

    Internal state: rolling deque of last (buffer_size) bars, current_side,
    and entry_close when LONG.

    warmup gate = max(atr_period, atr_stop_period) + 3  (mirrors research warmup)

    Signal contract: on_bar(bar) -> Signal | None
      - Returns None for unclosed bars, during warmup, or when no condition fires.
      - Never emits SignalSide.SHORT.
    """

    def __init__(self, *, symbol: str) -> None:
        self._symbol = symbol
        self._atr_period: int = int(ATR_BREAKOUT_LOCKED_PARAMS["atr_period"])  # type: ignore[call-overload]
        self._atr_breakout_mult: float = float(ATR_BREAKOUT_LOCKED_PARAMS["atr_breakout_mult"])  # type: ignore[arg-type]
        self._atr_stop_period: int = int(ATR_BREAKOUT_LOCKED_PARAMS["atr_stop_period"])  # type: ignore[call-overload]
        self._atr_stop_mult: float = float(ATR_BREAKOUT_LOCKED_PARAMS["atr_stop_mult"])  # type: ignore[arg-type]

        # warmup mirrors research: max(atr_period, atr_stop_period) + 3
        self._warmup: int = max(self._atr_period, self._atr_stop_period) + 3
        self._buffer_size: int = max(self._atr_period, self._atr_stop_period) + 10

        self._highs: deque[float] = deque(maxlen=self._buffer_size)
        self._lows: deque[float] = deque(maxlen=self._buffer_size)
        self._closes: deque[float] = deque(maxlen=self._buffer_size)

        self._current_side: SignalSide = SignalSide.FLAT
        # entry_close stored so ATR stop can be computed from it
        self._entry_close: float | None = None

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

        # Append OHLC to rolling buffers
        self._highs.append(float(bar.high))
        self._lows.append(float(bar.low))
        self._closes.append(float(bar.close))

        # Warmup gate
        if len(self._closes) < self._warmup:
            return None

        closes_arr = np.array(self._closes, dtype=np.float64)
        highs_arr = np.array(self._highs, dtype=np.float64)
        lows_arr = np.array(self._lows, dtype=np.float64)

        # ATR arrays (Wilder)
        atr_signal = self._wilder_atr(highs_arr, lows_arr, closes_arr, self._atr_period)
        atr_stop = (
            self._wilder_atr(highs_arr, lows_arr, closes_arr, self._atr_stop_period)
            if self._atr_stop_period != self._atr_period
            else atr_signal
        )

        # Need valid ATR at index [-2] (bar T-2) for signal computation
        if len(atr_signal) < 2 or np.isnan(atr_signal[-2]):
            return None

        prev_close = closes_arr[-2]  # bar(T-1) close
        prev_prev_close = closes_arr[-3] if len(closes_arr) >= 3 else float("nan")  # bar(T-2) close
        atr_at_prev_prev = atr_signal[-2]  # atr[i-2] in research notation

        if np.isnan(prev_prev_close) or np.isnan(atr_at_prev_prev):
            return None

        # ------------------------------------------------------------------
        # Entry logic — FLAT → LONG
        # ------------------------------------------------------------------
        if self._current_side == SignalSide.FLAT:
            # Entry: close[i-1] > close[i-2] + atr_breakout_mult * atr[i-2]
            if prev_close > prev_prev_close + self._atr_breakout_mult * atr_at_prev_prev:
                self._current_side = SignalSide.LONG
                self._entry_close = prev_close
                atr_val = float(atr_stop[-1]) if not np.isnan(atr_stop[-1]) else None
                return self._build_signal(
                    bar,
                    SignalSide.LONG,
                    atr_val=atr_val,
                    reason=ReasonCode.ENTRY_LONG_ATR_BREAKOUT,
                )
            return None

        # ------------------------------------------------------------------
        # Exit logic — LONG → FLAT
        # ------------------------------------------------------------------
        if self._current_side == SignalSide.LONG:
            atr_val = float(atr_stop[-1]) if not np.isnan(atr_stop[-1]) else None

            # Priority 1: reverse ATR breakdown
            # close[i-1] < close[i-2] - atr_breakout_mult * atr[i-2]
            if prev_close < prev_prev_close - self._atr_breakout_mult * atr_at_prev_prev:
                self._current_side = SignalSide.FLAT
                self._entry_close = None
                return self._build_signal(
                    bar,
                    SignalSide.FLAT,
                    atr_val=atr_val,
                    reason=ReasonCode.EXIT_FLAT_ATR_REVERSE,
                )

            # Priority 2: ATR stop intrabar
            # bar.low <= entry_close - atr_stop_mult * atr_stop[-1]
            if (
                self._entry_close is not None
                and atr_val is not None
                and float(bar.low) <= self._entry_close - self._atr_stop_mult * atr_val
            ):
                self._current_side = SignalSide.FLAT
                self._entry_close = None
                return self._build_signal(
                    bar,
                    SignalSide.FLAT,
                    atr_val=atr_val,
                    reason=ReasonCode.EXIT_FLAT_ATR_STOP_AB,
                )

        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wilder_atr(
        highs_arr: np.ndarray,
        lows_arr: np.ndarray,
        closes_arr: np.ndarray,
        period: int,
    ) -> np.ndarray:
        """Wilder ATR — exact port of scripts/autoresearch_endless.py::_atr().

        Uses prev_close[0] = close[0]. Wilder smoothing: SMA seed then EMA-like.
        Returns array same length as input; NaN for indices < period-1.
        """
        n = len(closes_arr)
        prev_close = np.concatenate([[closes_arr[0]], closes_arr[:-1]])
        tr: np.ndarray = np.maximum.reduce(
            [
                highs_arr - lows_arr,
                np.abs(highs_arr - prev_close),
                np.abs(lows_arr - prev_close),
            ]
        )
        atr_out = np.full(n, np.nan, dtype=np.float64)
        if n < period:
            return atr_out
        atr_out[period - 1] = tr[:period].mean()
        for i in range(period, n):
            atr_out[i] = (atr_out[i - 1] * (period - 1) + tr[i]) / period
        return atr_out

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
