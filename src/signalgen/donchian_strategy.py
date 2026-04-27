"""Donchian breakout long-only strategy (S35 α track per ADR 0054 LOCKED).

LOCKED parameters per ADR 0054 — anti-snooping pre-registration:
  - lookback_n=20 (entry window)
  - exit_lookback_n=10 (exit window — Turtle Trading variant)
  - atr_period=14 (Wilder ATR)
  - atr_stop_mult=2.0 (volatility-adjusted trailing stop)
  - signal_side_mode="long_only" (FSM invariant — NEVER emits SHORT)

Entry rule (LONG): close(T) > max(high[T-lookback_n:T])  AND  current_side == FLAT
Exit rule (FLAT):  IF current LONG, exit if EITHER:
                   - close(T) < min(low[T-exit_lookback_n:T])  (Donchian channel exit)
                   - close(T) < entry_close - atr_stop_mult * ATR(T)  (ATR trailing stop)

Invariant: signal on close(T) → execution at open(T+1) (no look-ahead per execution-timing.md).
Thread-safety: NOT thread-safe — single-producer per symbol pattern.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import numpy as np

from src.marketdata.models import Bar
from src.signalgen.indicators import atr
from src.signalgen.models import Signal, SignalSide

# ADR 0054 LOCKED — DO NOT modify без new ADR.
DONCHIAN_LONG_ONLY_PARAMS: dict[str, object] = {
    "lookback_n": 20,
    "exit_lookback_n": 10,
    "atr_period": 14,
    "atr_stop_mult": Decimal("2.0"),
    "signal_side_mode": "long_only",
}


class DonchianBreakoutStrategy:
    """Stateful Donchian breakout strategy (long-only).

    Internal state: rolling buffer of last (lookback_n + atr_period + 5) bars,
    plus current_side and entry_close_when_long.
    """

    def __init__(
        self,
        *,
        symbol: str,
        lookback_n: int,
        exit_lookback_n: int,
        atr_period: int,
        atr_stop_mult: Decimal,
    ) -> None:
        if lookback_n <= 0 or exit_lookback_n <= 0 or atr_period <= 0:
            raise ValueError("lookback / exit_lookback / atr_period must be positive")
        if exit_lookback_n >= lookback_n:
            raise ValueError("exit_lookback_n must be < lookback_n")
        if atr_stop_mult <= Decimal("0"):
            raise ValueError("atr_stop_mult must be positive")

        self._symbol = symbol
        self._lookback_n = lookback_n
        self._exit_lookback_n = exit_lookback_n
        self._atr_n = atr_period
        self._atr_stop_mult = atr_stop_mult
        self._buffer_size = max(lookback_n, atr_period) + 5
        self._bars: list[Bar] = []
        self._current_side: SignalSide = SignalSide.FLAT
        self._entry_close: Decimal | None = None

    def _append_bar(self, bar: Bar) -> bool:
        if not bar.is_closed:
            return False
        if bar.symbol != self._symbol:
            return False
        if self._bars and bar.close_time <= self._bars[-1].close_time:
            return False
        self._bars.append(bar)
        if len(self._bars) > self._buffer_size:
            self._bars = self._bars[-self._buffer_size :]
        return True

    def warmup(self, bar: Bar) -> None:
        """Feed historical bar к buffer без signal emission."""
        self._append_bar(bar)

    def on_bar(self, bar: Bar) -> Signal | None:
        if not self._append_bar(bar):
            return None
        if len(self._bars) < self._lookback_n + 1:
            return None

        highs = np.array([float(b.high) for b in self._bars], dtype=np.float64)
        lows = np.array([float(b.low) for b in self._bars], dtype=np.float64)
        closes = np.array([float(b.close) for b in self._bars], dtype=np.float64)

        # Donchian channel: max(high[T-lookback_n:T]), excluding current bar.
        donchian_high = float(np.max(highs[-(self._lookback_n + 1) : -1]))
        donchian_low_exit = float(np.min(lows[-(self._exit_lookback_n + 1) : -1]))
        atr_arr = atr(highs, lows, closes, self._atr_n)
        atr_now = float(atr_arr[-1])
        if np.isnan(atr_now):
            return None

        close_now = float(bar.close)

        # Entry rule (LONG): close > donchian_high AND FLAT
        if self._current_side == SignalSide.FLAT and close_now > donchian_high:
            self._current_side = SignalSide.LONG
            self._entry_close = bar.close
            return self._build_signal(
                bar,
                SignalSide.LONG,
                atr_now=atr_now,
                reason="ENTRY_LONG_DONCHIAN_BREAKOUT",
            )

        # Exit rule (FLAT): from LONG, channel exit OR ATR stop hit
        if self._current_side == SignalSide.LONG and self._entry_close is not None:
            atr_stop_price = float(self._entry_close) - float(self._atr_stop_mult) * atr_now
            channel_exit = close_now < donchian_low_exit
            atr_stop_exit = close_now < atr_stop_price
            if channel_exit or atr_stop_exit:
                self._current_side = SignalSide.FLAT
                reason = "EXIT_FLAT_ATR_STOP" if atr_stop_exit else "EXIT_FLAT_CHANNEL"
                self._entry_close = None
                return self._build_signal(
                    bar,
                    SignalSide.FLAT,
                    atr_now=atr_now,
                    reason=reason,
                )

        return None

    def _build_signal(
        self,
        bar: Bar,
        side: SignalSide,
        *,
        atr_now: float,
        reason: str,
    ) -> Signal:
        # Donchian не computes EMA/ADX/DI/RSI — populate с zero placeholders
        # (Signal protocol shared с EMA strategy, mean-reversion same pattern per S15).
        zero = Decimal("0")
        return Signal(
            signal_id=uuid4(),
            symbol=self._symbol,
            side=side,
            bar_close_time=bar.close_time,
            generated_at=datetime.now(UTC),
            ema_fast=zero,
            ema_slow=zero,
            adx_14=zero,
            plus_di_14=zero,
            minus_di_14=zero,
            rsi_14=zero,
            atr_14=Decimal(str(atr_now)),
            reason=reason,
        )
