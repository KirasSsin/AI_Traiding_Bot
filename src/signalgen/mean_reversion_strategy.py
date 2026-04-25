"""Mean-reversion strategy: RSI extreme + Bollinger Bands breach (Sprint 15).

ADR 0030 — pre-registered AND-gated trigger:
    LONG entry: RSI(14) < oversold AND close < lower_BB(20, 2σ)
    EXIT:       RSI(14) > overbought OR close > upper_BB(20, 2σ)

Reuses Signal protocol from EmaCrossoverAdxRsiStrategy для drop-in replacement.
Unused EMA/ADX/DI fields в Signal populated с zero placeholders (mean-reversion
не computes those indicators).

Invariant: signal on close(T) → execution at open(T+1) — no look-ahead
  (per wiki/project/architecture/execution-timing.md).

Thread-safety: NOT thread-safe. One instance — one producer thread per symbol
(per ADR 0022 single-writer; ADR 0030 multi-symbol uses one instance per symbol).
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import numpy as np

from src.marketdata.models import Bar
from src.signalgen.bollinger_bands import bollinger_bands
from src.signalgen.indicators import atr, rsi
from src.signalgen.models import Signal, SignalSide


class MeanReversionRsiBBStrategy:
    """Stateful mean-reversion strategy. Drop-in replacement for EmaCrossover."""

    def __init__(
        self,
        *,
        symbol: str,
        rsi_period: int = 14,
        bb_period: int = 20,
        bb_k: float = 2.0,
        rsi_oversold: Decimal = Decimal("30"),
        rsi_overbought: Decimal = Decimal("70"),
        atr_period: int = 14,
    ) -> None:
        if rsi_period < 2:
            raise ValueError(f"rsi_period must be >= 2, got {rsi_period}")
        if bb_period < 2:
            raise ValueError(f"bb_period must be >= 2, got {bb_period}")
        if bb_k <= 0:
            raise ValueError(f"bb_k must be > 0, got {bb_k}")
        if not (Decimal("0") <= rsi_oversold < rsi_overbought <= Decimal("100")):
            raise ValueError(
                f"require 0 <= rsi_oversold ({rsi_oversold}) < "
                f"rsi_overbought ({rsi_overbought}) <= 100"
            )

        self._symbol = symbol
        self._rsi_n = rsi_period
        self._bb_n = bb_period
        self._bb_k = bb_k
        self._rsi_oversold = rsi_oversold
        self._rsi_overbought = rsi_overbought
        self._atr_n = atr_period

        # Buffer >= max(rsi, bb, atr) + 5 для warm-up + lookback safety
        self._buffer_size = max(rsi_period, bb_period, atr_period) + 5
        self._bars: list[Bar] = []
        self._current_side: SignalSide = SignalSide.FLAT

    def _append_bar(self, bar: Bar) -> bool:
        """Filter + dedup + append + buffer truncate. True if bar landed."""
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
        """Feed historical bar к buffer без signal emission (ADR 0022 sub-decision 2)."""
        self._append_bar(bar)

    def on_bar(self, bar: Bar) -> Signal | None:
        """Main entry. Called once per closed bar."""
        if not self._append_bar(bar):
            return None

        min_required = max(self._rsi_n, self._bb_n) + 1
        if len(self._bars) < min_required:
            return None

        closes = np.array([float(b.close) for b in self._bars], dtype=np.float64)
        highs = np.array([float(b.high) for b in self._bars], dtype=np.float64)
        lows = np.array([float(b.low) for b in self._bars], dtype=np.float64)

        rsi_arr = rsi(closes, self._rsi_n)
        upper_bb, middle_bb, lower_bb = bollinger_bands(
            closes, period=self._bb_n, k=self._bb_k
        )
        atr_arr = atr(highs, lows, closes, self._atr_n)

        snapshot = {
            "rsi": rsi_arr[-1],
            "bb_upper": upper_bb[-1],
            "bb_middle": middle_bb[-1],
            "bb_lower": lower_bb[-1],
            "atr": atr_arr[-1],
            "close": float(bar.close),
        }
        if any(np.isnan(v) for v in snapshot.values()):
            return None

        rsi_val = Decimal(str(snapshot["rsi"]))
        close_val = snapshot["close"]

        # LONG entry: RSI < oversold AND close < lower_BB AND currently FLAT
        if (
            self._current_side == SignalSide.FLAT
            and rsi_val < self._rsi_oversold
            and close_val < snapshot["bb_lower"]
        ):
            self._current_side = SignalSide.LONG
            return self._build_signal(
                bar, SignalSide.LONG, snapshot, reason="ENTRY_LONG_MEANREV_RSI_BB"
            )

        # EXIT: in LONG, RSI > overbought OR close > upper_BB
        if self._current_side == SignalSide.LONG:
            if rsi_val > self._rsi_overbought or close_val > snapshot["bb_upper"]:
                self._current_side = SignalSide.FLAT
                return self._build_signal(
                    bar, SignalSide.FLAT, snapshot, reason="EXIT_FLAT_MEANREV_REVERT"
                )

        return None

    def _build_signal(
        self,
        bar: Bar,
        side: SignalSide,
        snapshot: dict[str, float],
        reason: str,
    ) -> Signal:
        # Signal model carries EMA/ADX/DI fields from EmaCrossover lineage —
        # pass zero placeholders since mean-reversion does not compute those.
        return Signal(
            signal_id=uuid4(),
            symbol=self._symbol,
            side=side,
            bar_close_time=bar.close_time,
            generated_at=datetime.now(UTC),
            ema_fast=Decimal("0"),
            ema_slow=Decimal("0"),
            adx_14=Decimal("0"),
            plus_di_14=Decimal("0"),
            minus_di_14=Decimal("0"),
            rsi_14=Decimal(str(snapshot["rsi"])),
            atr_14=Decimal(str(snapshot["atr"])),
            reason=reason,
        )
