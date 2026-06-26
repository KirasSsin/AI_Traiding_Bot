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

ATR parity (D4, S51): BOTH Wilder ATRs (signal period + stop period) are
maintained INCREMENTALLY over full history via the canonical RMA recursion
(O(1) per bar, mirrors SupertrendStrategy._update_atr) — exactly matching
src.signalgen.indicators.wilder_atr and the backtest runner _atr. Previously
the ATRs were recomputed over a bounded sliding deque (maxlen = max_period +
10), which re-seeded the recursion every bar once saturated → live ATR
diverged up to ~39% rel from the full-history path the WFA (ADR 0064)
validated. The signal indexing (atr[-2] / closes[-2,-3]) and entry/exit
semantics are UNCHANGED — only the ATR *values* are corrected (no re-seed).
See ADR 0064 amendment + tests/unit/test_atr_breakout_parity.py.

Thread-safety: NOT thread-safe — single-producer per symbol pattern
(per ADR 0023 single-writer invariant).

Reference implementation: scripts/autoresearch_endless.py::strat_atr_breakout
(BTCUSDT_240 autoresearch iter1 best).
"""

from __future__ import annotations

import math
from collections import deque
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

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

# ADR 0061 LOCKED — per-combo params from autoresearch endless best_per_combo.json.
# Each combo's params locked independently (anti-snooping audit trail).
# DO NOT modify without a new ADR amendment.
# Source: data/autoresearch_endless/best_per_combo.json (endless autoresearch run).
ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO: dict[tuple[str, str], dict[str, object]] = {
    ("BTCUSDT", "240"): {
        "atr_period": 9,
        "atr_breakout_mult": Decimal("2.5"),
        "atr_stop_period": 21,
        "atr_stop_mult": Decimal("1.5"),
    },
    ("BTCUSDT", "60"): {
        "atr_period": 9,
        "atr_breakout_mult": Decimal("2.5"),
        "atr_stop_period": 21,
        "atr_stop_mult": Decimal("3.0"),
    },
    ("BTCUSDT", "15"): {
        "atr_period": 9,
        "atr_breakout_mult": Decimal("3.0"),
        "atr_stop_period": 14,
        "atr_stop_mult": Decimal("3.0"),
    },
    ("BTCUSDT", "D"): {
        "atr_period": 9,
        "atr_breakout_mult": Decimal("1.0"),
        "atr_stop_period": 9,
        "atr_stop_mult": Decimal("3.0"),
    },
    ("ETHUSDT", "240"): {
        "atr_period": 14,
        "atr_breakout_mult": Decimal("2.5"),
        "atr_stop_period": 14,
        "atr_stop_mult": Decimal("1.5"),
    },
    ("ETHUSDT", "60"): {
        "atr_period": 14,
        "atr_breakout_mult": Decimal("2.5"),
        "atr_stop_period": 21,
        "atr_stop_mult": Decimal("1.5"),
    },
    ("ETHUSDT", "15"): {
        "atr_period": 9,
        "atr_breakout_mult": Decimal("3.0"),
        "atr_stop_period": 14,
        "atr_stop_mult": Decimal("2.0"),
    },
    ("SOLUSDT", "240"): {
        "atr_period": 21,
        "atr_breakout_mult": Decimal("1.5"),
        "atr_stop_period": 9,
        "atr_stop_mult": Decimal("2.0"),
    },
    ("SOLUSDT", "60"): {
        "atr_period": 9,
        "atr_breakout_mult": Decimal("2.0"),
        "atr_stop_period": 21,
        "atr_stop_mult": Decimal("3.0"),
    },
    ("SOLUSDT", "15"): {
        "atr_period": 21,
        "atr_breakout_mult": Decimal("2.5"),
        "atr_stop_period": 9,
        "atr_stop_mult": Decimal("3.0"),
    },
}

_ZERO = Decimal("0")


class _WilderATR:
    """Incremental Wilder ATR over FULL history (O(1) per bar).

    Exact canonical RMA matching src.signalgen.indicators.wilder_atr /
    atr_breakout_runner._atr:
      - TR[0] = high[0] - low[0]   (prev_close[0] = close[0] convention).
      - TR[i] = max(high-low, |high-prev_close|, |low-prev_close|).
      - Seed at bar index ``period-1``: ATR = mean(TR[0..period-1]).
      - Recursion thereafter: ATR = (ATR*(period-1) + TR[i]) / period.

    Exposes ``current`` (ATR through the latest bar) and ``previous`` (ATR
    through the bar before it) — None until the respective bar is seeded. These
    reproduce the old windowed array's ``[-1]`` / ``[-2]`` reads WITHOUT the
    sliding-window re-seed (the D4 defect).
    """

    def __init__(self, period: int) -> None:
        self._period = period
        self._prev_atr: float | None = None
        self._prev_close: float | None = None  # close[i-1] for TR
        self._tr_seed: list[float] = []
        self.current: float | None = None
        self.previous: float | None = None

    def update(self, high: float, low: float, close: float) -> None:
        if self._prev_close is None:
            tr = high - low  # bar 0: prev_close == close[0] -> TR collapses to h-l
        else:
            prev_close = self._prev_close
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        self._prev_close = close

        if self._prev_atr is None:
            self._tr_seed.append(tr)
            if len(self._tr_seed) < self._period:
                new = None
            else:  # seed bar (index period-1): ATR = mean of first `period` TRs
                self._prev_atr = sum(self._tr_seed) / self._period
                self._tr_seed = []
                new = self._prev_atr
        else:
            self._prev_atr = (self._prev_atr * (self._period - 1) + tr) / self._period
            new = self._prev_atr

        self.previous = self.current
        self.current = new


class ATRBreakoutStrategy:
    """Stateful ATR breakout long-only strategy.

    Internal state: incremental full-history Wilder ATR carries (signal + stop),
    a small rolling close buffer (for the close[-2]/close[-3] references),
    current_side, and entry_close when LONG. The ATRs are full-history O(1)
    recursions — NOT windowed recomputes (D4, S51).

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

        # Small rolling close buffer — only the close[-2]/close[-3] references
        # are needed (no longer used for ATR; ATR is incremental full-history).
        self._closes: deque[float] = deque(maxlen=max(self._atr_period, self._atr_stop_period) + 10)

        # Incremental full-history Wilder ATR (signal + stop). When the two
        # periods coincide the stop ATR aliases the signal ATR (research parity).
        self._atr_signal = _WilderATR(self._atr_period)
        self._atr_stop_calc: _WilderATR | None = (
            None if self._atr_stop_period == self._atr_period else _WilderATR(self._atr_stop_period)
        )

        # Last ATR values the strategy holds for the just-processed bar (through
        # bar T). None during warmup. Exposed for parity testing / observability.
        self._last_atr_signal: float | None = None
        self._last_atr_stop: float | None = None

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

        high = float(bar.high)
        low = float(bar.low)
        close = float(bar.close)

        # Advance both incremental full-history ATRs (recursion sees full history).
        self._atr_signal.update(high, low, close)
        if self._atr_stop_calc is not None:
            self._atr_stop_calc.update(high, low, close)
        self._closes.append(close)

        # ATR through bar T (current) for the stop level + Signal.atr_14.
        atr_stop_curr = (
            self._atr_stop_calc.current
            if self._atr_stop_calc is not None
            else self._atr_signal.current
        )
        self._last_atr_signal = self._atr_signal.current
        self._last_atr_stop = atr_stop_curr

        # Warmup gate
        if len(self._closes) < self._warmup:
            return None

        # Signal ATR through bar T-1 (== old windowed atr_signal[-2], now full-history).
        atr_at_prev_prev = self._atr_signal.previous
        if atr_at_prev_prev is None:
            return None

        prev_close = self._closes[-2]  # bar(T-1) close
        prev_prev_close = self._closes[-3] if len(self._closes) >= 3 else float("nan")  # bar(T-2)

        if math.isnan(prev_prev_close):
            return None

        # ------------------------------------------------------------------
        # Entry logic — FLAT → LONG
        # ------------------------------------------------------------------
        if self._current_side == SignalSide.FLAT:
            # Entry: close[i-1] > close[i-2] + atr_breakout_mult * atr[i-2]
            if prev_close > prev_prev_close + self._atr_breakout_mult * atr_at_prev_prev:
                self._current_side = SignalSide.LONG
                self._entry_close = prev_close
                return self._build_signal(
                    bar,
                    SignalSide.LONG,
                    atr_val=atr_stop_curr,
                    reason=ReasonCode.ENTRY_LONG_ATR_BREAKOUT,
                )
            return None

        # ------------------------------------------------------------------
        # Exit logic — LONG → FLAT
        # ------------------------------------------------------------------
        if self._current_side == SignalSide.LONG:
            atr_val = atr_stop_curr

            # Priority 1: ATR stop intrabar (checked BEFORE reverse breakdown to
            # match the WFA-validated runner _backtest_single, which evaluates
            # `if low[i] <= stop_price` before `elif exit_[i]`). On a same-bar
            # double-exit live must book the stop, exactly like the backtest.
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

            # Priority 2: reverse ATR breakdown
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

        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
