"""Kronos forecasting strategy — prediction-cache consumer (S52, ADR 0068, V3 + C7).

This strategy is a normal ``on_bar`` consumer of the prediction CACHE built in T3
(:mod:`src.ml.prediction_cache`). It performs a cache LOOKUP only and therefore
NEVER imports torch (nor the torch path of ``kronos_adapter``): Kronos runs
OFFLINE at cache-build time, and the strategy merely replays already-deterministic
``Decimal`` predictions. This keeps ``src/signalgen/`` torch-free per the C1
isolation invariant (guarded by ``tests/unit/test_ml_optional_dep.py`` Test B).

V3 signal rule (LOCKED, horizon = 1). Let ``pred_close`` be the cached predicted
close for the next bar and ``current_close`` this bar's close:
  - ``pred_close > current_close * (1 + threshold)`` -> ENTRY_LONG_KRONOS
  - ``pred_close < current_close``                   -> EXIT_FLAT_KRONOS (flatten)
  - otherwise                                        -> None (no signal)
``threshold`` defaults to ``Decimal("0.006")`` (= 2x round-trip cost:
commission 0.10%/side + slippage 0.05%/side = 0.30% round-trip → 0.60%) and is
configurable. Long-only — the strategy NEVER emits SHORT.

Cache MISS (no prediction stored for this bar's key) -> ``None``: no trade, no
block, no crash. The strategy degrades gracefully when a prediction is missing.

Look-ahead safety (S50/S51 lesson, CRITICAL): the strategy acts ONLY on CLOSED
bars (``is_closed`` gate) and the cache key is built from THIS bar's close
timestamp (``bar_close_ts = int(bar.close_time.timestamp())``). A prediction
keyed to a future timestamp is therefore never read for the current bar
(append-before-compute discipline).

Thread-safety: NOT thread-safe — single-producer per symbol pattern
(per ADR 0023 single-writer invariant).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from src.marketdata.models import Bar
from src.ml.prediction_cache import CacheKey, PredictionCache
from src.risk.reason_codes import ReasonCode
from src.signalgen.atr_breakout_strategy import _WilderATR
from src.signalgen.models import Signal, SignalSide

# ADR 0068 / V3 LOCKED — threshold default = 2x round-trip cost
# (commission 0.10%/side + slippage 0.05%/side = 0.30% round-trip → 0.60%).
DEFAULT_THRESHOLD = Decimal("0.006")

_ZERO = Decimal("0")


class KronosStrategy:
    """Stateful long-only Kronos forecasting strategy (cache LOOKUP consumer).

    The strategy holds the identifying cache fields (``model_id``,
    ``weights_hash``, ``timeframe``, ``params_hash``, ``device``) needed to
    reconstruct the :class:`~src.ml.prediction_cache.CacheKey` for each bar. The
    ``bar_close_ts`` field is derived from the current bar's close timestamp so
    no future prediction can be read.

    Signal contract: ``on_bar(bar) -> Signal | None``
      - Returns ``None`` for unclosed bars, foreign-symbol bars, and cache
        misses, and when the prediction lies within the no-trade band.
      - Never emits :attr:`SignalSide.SHORT`.
    """

    def __init__(
        self,
        *,
        symbol: str,
        cache: PredictionCache,
        model_id: str,
        weights_hash: str,
        timeframe: str,
        params_hash: str,
        device: str,
        threshold: Decimal = DEFAULT_THRESHOLD,
        atr_period: int = 14,
    ) -> None:
        """Initialise the strategy with its cache and key-identifying config.

        Args:
            symbol: Trading symbol this strategy is bound to (e.g. ``"BTCUSDT"``).
            cache: The deterministic prediction cache to look predictions up in.
            model_id: Kronos model identifier (cache key field).
            weights_hash: Hash of the model weights (cache key field).
            timeframe: Bar timeframe string (cache key field, e.g. ``"1h"``).
            params_hash: Hash of the sampling params (cache key field).
            device: Device the predictions were produced on (cache key field).
            threshold: Minimum relative upside for an entry (LOCKED default
                ``Decimal("0.006")`` = 2× round-trip cost, configurable).
            atr_period: Wilder ATR period used to fill ``Signal.atr_14`` for
                bracket sizing (default 14). The ATR is computed incrementally
                from closed bars only (look-ahead-safe).
        """
        self._symbol = symbol
        self._cache = cache
        self._model_id = model_id
        self._weights_hash = weights_hash
        self._timeframe = timeframe
        self._params_hash = params_hash
        self._device = device
        self._threshold = threshold
        # Incremental full-history Wilder ATR (reused from ATRBreakoutStrategy,
        # DRY). Kronos does NOT compute EMA/RSI/ADX — only ATR for SL/TP sizing.
        self._atr = _WilderATR(period=atr_period)
        self._last_atr: Decimal | None = None
        # Self-consistent signal contract (TL-06): mirror the sibling strategies
        # (donchian/atr_breakout/...) — only emit ENTRY when FLAT, only emit
        # EXIT when LONG. Long-only FSM: state ∈ {FLAT, LONG} (never SHORT).
        self._current_side: SignalSide = SignalSide.FLAT

    def on_bar(self, bar: Bar) -> Signal | None:
        """Evaluate the V3 rule on a closed bar via a cache lookup.

        Returns a :class:`Signal` on an entry/exit decision, or ``None`` for an
        unclosed/foreign bar, a cache miss, or a prediction inside the no-trade
        band. Decimal arithmetic throughout (no float).
        """
        # Live-bar guard: never act on an unclosed bar (look-ahead safety).
        if not bar.is_closed:
            return None
        if bar.symbol != self._symbol:
            return None

        # Advance the incremental Wilder ATR on EVERY closed bar (regardless of
        # whether a signal fires) — look-ahead-safe (only closed bars up to and
        # including this one feed the recursion). Store the latest warmed value.
        self._atr.update(float(bar.high), float(bar.low), float(bar.close))
        if self._atr.current is not None:
            self._last_atr = Decimal(str(self._atr.current))

        # Build the key from THIS bar's close timestamp — never a future bar's.
        key = CacheKey(
            model_id=self._model_id,
            weights_hash=self._weights_hash,
            symbol=self._symbol,
            timeframe=self._timeframe,
            bar_close_ts=int(bar.close_time.timestamp()),
            params_hash=self._params_hash,
            device=self._device,
        )
        prediction = self._cache.get(key)
        # Cache MISS -> graceful None (no trade, no crash).
        if not prediction:
            return None

        pred_close = prediction[0]  # horizon = 1 -> single predicted close
        current_close = bar.close

        # Entry rule (LONG): only when currently FLAT (no double-entry — TL-06).
        if self._current_side == SignalSide.FLAT and pred_close > current_close * (
            Decimal(1) + self._threshold
        ):
            # Risk-safe: no ENTRY without a warmed ATR — the bracket SL/TP cannot
            # be sized from atr_14 == 0 (SL == entry or div-by-zero). Refuse.
            if self._last_atr is None or self._last_atr <= 0:
                return None
            self._current_side = SignalSide.LONG
            return self._build_signal(bar, SignalSide.LONG, ReasonCode.ENTRY_LONG_KRONOS)
        # Exit rule (FLAT): only when currently LONG (no phantom exit — TL-06).
        if self._current_side == SignalSide.LONG and pred_close < current_close:
            # EXIT_FLAT only flattens an existing position — no SL sizing needed,
            # so it may fire even before the ATR has warmed up.
            self._current_side = SignalSide.FLAT
            return self._build_signal(bar, SignalSide.FLAT, ReasonCode.EXIT_FLAT_KRONOS)
        return None

    def _build_signal(self, bar: Bar, side: SignalSide, reason: ReasonCode) -> Signal:
        """Construct a Signal with zero placeholders for indicators not computed."""
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
            atr_14=self._last_atr if self._last_atr is not None else _ZERO,
            reason=reason.value,
        )
