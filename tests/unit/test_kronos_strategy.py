"""Unit tests for KronosStrategy (S52 T4, ADR 0068, V3 signal rule + C7 cache-consumer).

The strategy is a normal ``on_bar`` consumer of the prediction CACHE built in T3
(``src.ml.prediction_cache``). It performs a cache LOOKUP only — NO torch import.

V3 signal rule (LOCKED, horizon = 1):
  - pred_close > current_close * (1 + threshold)  -> ENTRY_LONG_KRONOS
  - pred_close < current_close                    -> EXIT_FLAT_KRONOS
  - otherwise                                     -> None
  threshold default = Decimal("0.006") (= 2x round-trip cost:
    commission 0.10%/side + slippage 0.05%/side = 0.30% round-trip → 0.60%).

Cache MISS -> None (graceful degradation, no crash). Look-ahead-safe: only acts
on closed bars; the cache key is built from THIS bar's close timestamp.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from src.marketdata.models import Bar
from src.ml.prediction_cache import CacheKey, PredictionCache
from src.risk.reason_codes import ReasonCode
from src.signalgen.kronos_strategy import KronosStrategy
from src.signalgen.models import SignalSide

# --- shared identifying fields for the cache key (strategy config) ---
MODEL_ID = "kronos-mini"
WEIGHTS_HASH = "abc123"
SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"
PARAMS_HASH = "def456"
DEVICE = "cpu"


@pytest.fixture
def base_time() -> datetime:
    return datetime(2024, 1, 1, tzinfo=UTC)


def _make_bar(
    *,
    close_time: datetime,
    close: float,
    is_closed: bool = True,
    symbol: str = SYMBOL,
    high: float | None = None,
    low: float | None = None,
) -> Bar:
    high_v = close if high is None else high
    low_v = close if low is None else low
    return Bar(
        open_time=close_time - timedelta(hours=1),
        close_time=close_time,
        symbol=symbol,
        interval="1h",
        open=Decimal(str(close)),
        high=Decimal(str(high_v)),
        low=Decimal(str(low_v)),
        close=Decimal(str(close)),
        volume=Decimal("100"),
        trade_count=100,
        is_closed=is_closed,
    )


def _make_strategy(cache: PredictionCache) -> KronosStrategy:
    return KronosStrategy(
        symbol=SYMBOL,
        cache=cache,
        model_id=MODEL_ID,
        weights_hash=WEIGHTS_HASH,
        timeframe=TIMEFRAME,
        params_hash=PARAMS_HASH,
        device=DEVICE,
    )


def _put_prediction(cache: PredictionCache, bar: Bar, pred_close: Decimal) -> None:
    """Persist a horizon=1 prediction keyed to THIS bar's close timestamp."""
    key = CacheKey(
        model_id=MODEL_ID,
        weights_hash=WEIGHTS_HASH,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        bar_close_ts=int(bar.close_time.timestamp()),
        params_hash=PARAMS_HASH,
        device=DEVICE,
    )
    cache.put(key, [pred_close])


# ---------------------------------------------------------------------------
# reason code count + membership
# ---------------------------------------------------------------------------


def test_reason_code_count_is_67() -> None:
    assert len(list(ReasonCode)) == 67


def test_kronos_reason_codes_exist() -> None:
    assert ReasonCode.ENTRY_LONG_KRONOS.value == "ENTRY_LONG_KRONOS"
    assert ReasonCode.EXIT_FLAT_KRONOS.value == "EXIT_FLAT_KRONOS"


# ---------------------------------------------------------------------------
# signal rule (V3)
# ---------------------------------------------------------------------------


def test_entry_long_when_pred_above_threshold(base_time: datetime, tmp_path) -> None:
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    # Warm up the ATR first — ENTRY is blocked until atr_14 can size the bracket.
    last = _feed_closed_bars_with_range(strat, base_time, count=14, close=100.0)
    bar = _make_bar(close_time=last + timedelta(hours=1), close=100.0, high=101.0, low=99.0)
    # pred_close > 100 * (1 + 0.006) = 100.60 -> ENTRY_LONG
    _put_prediction(cache, bar, Decimal("101.00"))
    sig = strat.on_bar(bar)
    assert sig is not None
    assert sig.side == SignalSide.LONG
    assert sig.reason == ReasonCode.ENTRY_LONG_KRONOS.value


def test_exit_flat_when_pred_below_current(base_time: datetime, tmp_path) -> None:
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    bar = _make_bar(close_time=base_time, close=100.0)
    _put_prediction(cache, bar, Decimal("99.0"))
    sig = strat.on_bar(bar)
    assert sig is not None
    assert sig.side == SignalSide.FLAT
    assert sig.reason == ReasonCode.EXIT_FLAT_KRONOS.value


def test_no_signal_within_band(base_time: datetime, tmp_path) -> None:
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    bar = _make_bar(close_time=base_time, close=100.0)
    # 100 <= pred <= 100.60 -> no signal (within threshold band at 0.60%)
    _put_prediction(cache, bar, Decimal("100.30"))
    assert strat.on_bar(bar) is None


def test_no_signal_at_exact_threshold(base_time: datetime, tmp_path) -> None:
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    bar = _make_bar(close_time=base_time, close=100.0)
    # pred == 100.60 exactly -> not strictly greater -> no signal
    _put_prediction(cache, bar, Decimal("100.60"))
    assert strat.on_bar(bar) is None


def test_no_signal_at_exact_current(base_time: datetime, tmp_path) -> None:
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    bar = _make_bar(close_time=base_time, close=100.0)
    # pred == current exactly -> not strictly less -> no exit signal
    _put_prediction(cache, bar, Decimal("100.0"))
    assert strat.on_bar(bar) is None


# ---------------------------------------------------------------------------
# cache MISS -> graceful None
# ---------------------------------------------------------------------------


def test_cache_miss_returns_none_no_exception(base_time: datetime, tmp_path) -> None:
    cache = PredictionCache(tmp_path)  # empty cache
    strat = _make_strategy(cache)
    bar = _make_bar(close_time=base_time, close=100.0)
    assert strat.on_bar(bar) is None


# ---------------------------------------------------------------------------
# look-ahead / live-bar guard
# ---------------------------------------------------------------------------


def test_unclosed_bar_returns_none(base_time: datetime, tmp_path) -> None:
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    bar = _make_bar(close_time=base_time, close=100.0, is_closed=False)
    # even with a cached entry-prediction present, an unclosed bar -> None
    _put_prediction(cache, bar, Decimal("100.50"))
    assert strat.on_bar(bar) is None


def test_foreign_symbol_bar_returns_none(base_time: datetime, tmp_path) -> None:
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    bar = _make_bar(close_time=base_time, close=100.0, symbol="ETHUSDT")
    assert strat.on_bar(bar) is None


def test_key_uses_current_bar_close_ts(base_time: datetime, tmp_path) -> None:
    """A prediction keyed to a FUTURE bar must NOT be read for the current bar."""
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    current = _make_bar(close_time=base_time, close=100.0)
    future = _make_bar(close_time=base_time + timedelta(hours=1), close=100.0)
    # Only the FUTURE bar has a (would-be entry) prediction cached.
    _put_prediction(cache, future, Decimal("100.50"))
    # Current bar lookup uses its OWN close ts -> MISS -> None (no look-ahead).
    assert strat.on_bar(current) is None


# ---------------------------------------------------------------------------
# configurable threshold (locked default, but read from config)
# ---------------------------------------------------------------------------


def test_threshold_default_is_locked_value(tmp_path) -> None:
    """DEFAULT_THRESHOLD must equal 0.006 (2× round-trip cost, PHASE 6 corrected)."""
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    assert strat._threshold == Decimal("0.006")


def test_strategy_on_bar_with_cached_empty_list_returns_none(
    base_time: datetime, tmp_path: Path
) -> None:
    """A cached [] for the current bar → on_bar returns None (falsy guard treats [] as miss).

    PredictionCache.get returns [] (not None) when put([]) was called.
    KronosStrategy.on_bar has ``if not prediction: return None`` which treats an
    empty list as a cache miss — no signal, no IndexError on prediction[0].
    """
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    bar = _make_bar(close_time=base_time, close=100.0)

    # Build the exact key the strategy will look up.
    key = CacheKey(
        model_id=MODEL_ID,
        weights_hash=WEIGHTS_HASH,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        bar_close_ts=int(bar.close_time.timestamp()),
        params_hash=PARAMS_HASH,
        device=DEVICE,
    )
    cache.put(key, [])  # persist empty prediction

    # Sanity: cache.get returns [] (not None).
    got = cache.get(key)
    assert got == [], f"expected cache.get to return [] but got {got!r}"

    # Strategy must return None — empty list is falsy, treated as cache miss.
    assert strat.on_bar(bar) is None


def test_threshold_configurable(base_time: datetime, tmp_path) -> None:
    cache = PredictionCache(tmp_path)
    strat = KronosStrategy(
        symbol=SYMBOL,
        cache=cache,
        model_id=MODEL_ID,
        weights_hash=WEIGHTS_HASH,
        timeframe=TIMEFRAME,
        params_hash=PARAMS_HASH,
        device=DEVICE,
        threshold=Decimal("0.05"),
    )
    bar = _make_bar(close_time=base_time, close=100.0)
    # pred 100.50 > 100.25 but < 105 (5% threshold) -> no signal under wide band
    _put_prediction(cache, bar, Decimal("100.50"))
    assert strat.on_bar(bar) is None


# ---------------------------------------------------------------------------
# real Wilder ATR fill (S53 T4, BLOCKER CC2) — atr_14 > 0 for bracket sizing
# ---------------------------------------------------------------------------


def _feed_closed_bars_with_range(
    strat: KronosStrategy, base_time: datetime, *, count: int, close: float = 100.0
) -> datetime:
    """Feed ``count`` closed bars with a non-trivial high/low range (no cached pred).

    Each bar has TR ~= 2 (high = close+1, low = close-1) so Wilder ATR warms up to
    a strictly positive value. Returns the close_time of the LAST bar fed so the
    caller can place the next (entry) bar one hour later.
    """
    last = base_time
    for i in range(count):
        ct = base_time + timedelta(hours=i)
        bar = _make_bar(close_time=ct, close=close, high=close + 1.0, low=close - 1.0)
        strat.on_bar(bar)  # no cached prediction -> None, but ATR advances
        last = ct
    return last


def test_signal_carries_real_atr_not_zero(base_time: datetime, tmp_path: Path) -> None:
    """ENTRY signals must carry atr_14 > 0 after warm-up (bracket sizing, was _ZERO)."""
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    # Warm up the ATR: feed 14 closed bars with a real range (period=14 default).
    last = _feed_closed_bars_with_range(strat, base_time, count=14, close=100.0)
    # Entry bar: one hour after the last warm-up bar.
    entry_ct = last + timedelta(hours=1)
    entry_bar = _make_bar(close_time=entry_ct, close=100.0, high=101.0, low=99.0)
    _put_prediction(cache, entry_bar, Decimal("101.00"))  # > 100.60 -> ENTRY_LONG
    sig = strat.on_bar(entry_bar)
    assert sig is not None
    assert sig.reason == ReasonCode.ENTRY_LONG_KRONOS.value
    assert sig.atr_14 > Decimal("0")  # NOT the old _ZERO stub


def test_entry_blocked_until_atr_warmed(base_time: datetime, tmp_path: Path) -> None:
    """ENTRY condition met but ATR not warmed (< period bars) -> on_bar returns None.

    No valid SL can be sized without an ATR, so the strategy must refuse the trade.
    """
    cache = PredictionCache(tmp_path)
    strat = _make_strategy(cache)
    bar = _make_bar(close_time=base_time, close=100.0, high=101.0, low=99.0)
    _put_prediction(cache, bar, Decimal("101.00"))  # would-be ENTRY_LONG
    # First bar -> ATR still in warm-up (None) -> no trade despite entry condition.
    assert strat.on_bar(bar) is None
