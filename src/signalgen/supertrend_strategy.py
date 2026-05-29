"""Supertrend long-only strategy (S50, hypothesis #10, ADR 0067 LOCKED, Lazybear variant).

LOCKED parameters per ADR 0067 — anti-snooping pre-registration:
  - atr_period: 10 (Wilder ATR for Supertrend bands)
  - multiplier: 3.0 (band offset = multiplier * ATR)
  - signal_side_mode: "long_only" (FSM invariant — NEVER emits SHORT)

Lazybear Supertrend (the trend-dependent variant freqtrade uses) computed on
each closed bar T from data through bar T:
  hl2       = (high[T] + low[T]) / 2
  atr       = wilder_atr(...)[-1]              # ATR at bar T
  basic_ub  = hl2 + multiplier * atr
  basic_lb  = hl2 - multiplier * atr
  # final bands carry forward with the Lazybear clamp (ratchet):
  final_ub  = basic_ub if (basic_ub < prev_final_ub or prev_close > prev_final_ub)
              else prev_final_ub
  final_lb  = basic_lb if (basic_lb > prev_final_lb or prev_close < prev_final_lb)
              else prev_final_lb
  # supertrend line selection (carry of prev line decides which band is active):
  if prev_supertrend == prev_final_ub:
      supertrend = final_ub if close <= final_ub else final_lb
  else:                       # prev_supertrend tracked the lower band
      supertrend = final_lb if close >= final_lb else final_ub
  trend = BULL if supertrend == final_lb else BEAR

Entry rule (LONG — evaluated on closed bar T, fill at open T+1):
  trend flips BEAR -> BULL  ->  ENTRY_LONG_SUPERTREND
Exit rule (FLAT):
  trend flips BULL -> BEAR  ->  EXIT_FLAT_SUPERTREND_FLIP
Mid-trend (no flip) -> None.

ATR bracket stop loss (no take-profit) is enforced downstream by the FSM/risk
layer using atr_14 carried in the Signal; this strategy emits the trend-flip
signals only (per ADR 0067 exit = flip + ATR bracket SL, no TP).

Invariant: signal evaluated on closed bar(T) using data through bar(T)
(no look-ahead — wilder_atr[i] depends only on TR[0..i], bands use bar T close).
Execution at open(T+1) per existing FSM contract.

Thread-safety: NOT thread-safe — single-producer per symbol pattern
(per ADR 0023 single-writer invariant).

Cross-validation: T5 validates this streaming output against a vectorized
Lazybear reference — the carry/clamp must match exactly.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

import numpy as np

from src.marketdata.models import Bar
from src.risk.reason_codes import ReasonCode
from src.signalgen.indicators import wilder_atr
from src.signalgen.models import Signal, SignalSide

# ADR 0067 LOCKED — DO NOT modify without a new ADR amendment.
SUPERTREND_LOCKED_PARAMS: dict[str, object] = {
    "atr_period": 10,
    "multiplier": Decimal("3.0"),
    "signal_side_mode": "long_only",
}

_ZERO = Decimal("0")


class SupertrendStrategy:
    """Stateful Supertrend long-only strategy (Lazybear variant).

    Internal state: rolling deque of last (buffer_size) bars, current side,
    Lazybear band/line carry (prev_final_ub/lb, prev_supertrend, prev_close),
    and last processed close_time (dedup/OOO guard).

    warmup gate = atr_period (bars before ATR is valid produce no signal)

    Signal contract: on_bar(bar) -> Signal | None
      - Returns None for unclosed bars, during warmup, the seed bar, or when
        the trend does not flip.
      - Never emits SignalSide.SHORT.
    """

    def __init__(
        self,
        *,
        symbol: str,
        atr_period: int | None = None,
        multiplier: float | None = None,
        long_only: bool = True,
    ) -> None:
        self._symbol = symbol
        self._atr_period: int = (
            atr_period if atr_period is not None else int(SUPERTREND_LOCKED_PARAMS["atr_period"])  # type: ignore[call-overload]
        )
        self._multiplier: float = (
            multiplier if multiplier is not None else float(SUPERTREND_LOCKED_PARAMS["multiplier"])  # type: ignore[arg-type]
        )
        self._long_only = long_only

        self._buffer_size: int = self._atr_period + 10

        self._highs: deque[float] = deque(maxlen=self._buffer_size)
        self._lows: deque[float] = deque(maxlen=self._buffer_size)
        self._closes: deque[float] = deque(maxlen=self._buffer_size)

        self._current_side: SignalSide = SignalSide.FLAT
        self._last_close_time: datetime | None = None

        # Lazybear carry state (None until the seed bar with valid ATR).
        self._supertrend_line: float | None = None
        self._trend_direction: Literal["BULL", "BEAR"] | None = None
        self._prev_final_ub: float | None = None
        self._prev_final_lb: float | None = None
        self._prev_close: float | None = None

    # ------------------------------------------------------------------
    # Public contract
    # ------------------------------------------------------------------

    def on_bar(self, bar: Bar) -> Signal | None:
        """Evaluate strategy on a closed bar. Returns Signal or None.

        Invariants enforced:
        - bar.is_closed must be True (live-bar guard).
        - OOO/dedup: bar.close_time must be strictly after last processed.
        - Warmup/seed gate before any signal.
        - Long-only: NEVER returns SHORT.
        """
        if not bar.is_closed:
            return None

        # OOO/dedup guard: reject bars not strictly newer than last processed.
        if self._last_close_time is not None and bar.close_time <= self._last_close_time:
            return None
        self._last_close_time = bar.close_time

        high = float(bar.high)
        low = float(bar.low)
        close = float(bar.close)

        self._highs.append(high)
        self._lows.append(low)
        self._closes.append(close)

        # Warmup: ATR invalid until atr_period bars are buffered.
        if len(self._closes) < self._atr_period:
            return None

        atr_arr = wilder_atr(
            np.array(self._highs, dtype=np.float64),
            np.array(self._lows, dtype=np.float64),
            np.array(self._closes, dtype=np.float64),
            self._atr_period,
        )
        atr = float(atr_arr[-1])
        if np.isnan(atr):
            return None

        hl2 = (high + low) / 2.0
        basic_ub = hl2 + self._multiplier * atr
        basic_lb = hl2 - self._multiplier * atr

        # Seed bar: first bar with a valid ATR. No prior carry -> no flip, no signal.
        if (
            self._prev_final_ub is None
            or self._prev_final_lb is None
            or self._prev_close is None
            or self._supertrend_line is None
            or self._trend_direction is None
        ):
            self._prev_final_ub = basic_ub
            self._prev_final_lb = basic_lb
            self._supertrend_line = basic_ub  # conservative seed on the upper band
            self._trend_direction = "BEAR"  # no entry on the seed bar
            self._prev_close = close
            return None

        prev_final_ub = self._prev_final_ub
        prev_final_lb = self._prev_final_lb
        prev_close = self._prev_close
        prev_supertrend = self._supertrend_line
        prev_trend = self._trend_direction

        # Final bands with the Lazybear carry/clamp (ratchet).
        final_ub = (
            basic_ub if (basic_ub < prev_final_ub or prev_close > prev_final_ub) else prev_final_ub
        )
        final_lb = (
            basic_lb if (basic_lb > prev_final_lb or prev_close < prev_final_lb) else prev_final_lb
        )

        # Supertrend line: which band is active is decided by the previous line.
        if prev_supertrend == prev_final_ub:
            supertrend = final_ub if close <= final_ub else final_lb
        else:
            supertrend = final_lb if close >= final_lb else final_ub

        trend: Literal["BULL", "BEAR"] = "BULL" if supertrend == final_lb else "BEAR"

        # Persist carry for the next bar.
        self._prev_final_ub = final_ub
        self._prev_final_lb = final_lb
        self._supertrend_line = supertrend
        self._trend_direction = trend
        self._prev_close = close

        return self._evaluate_flip(bar, prev_trend, trend, atr)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evaluate_flip(
        self,
        bar: Bar,
        prev_trend: Literal["BULL", "BEAR"],
        trend: Literal["BULL", "BEAR"],
        atr: float,
    ) -> Signal | None:
        """Map a trend transition to an entry/exit Signal (or None mid-trend)."""
        # Entry: BEAR -> BULL flip while FLAT.
        if prev_trend == "BEAR" and trend == "BULL" and self._current_side == SignalSide.FLAT:
            self._current_side = SignalSide.LONG
            return self._build_signal(
                bar, SignalSide.LONG, atr_val=atr, reason=ReasonCode.ENTRY_LONG_SUPERTREND
            )

        # Exit: BULL -> BEAR flip while LONG.
        if prev_trend == "BULL" and trend == "BEAR" and self._current_side == SignalSide.LONG:
            self._current_side = SignalSide.FLAT
            return self._build_signal(
                bar,
                SignalSide.FLAT,
                atr_val=atr,
                reason=ReasonCode.EXIT_FLAT_SUPERTREND_FLIP,
            )

        return None

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
