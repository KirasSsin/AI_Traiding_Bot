"""Unit tests for strat_supertrend in autoresearch_endless.py (S50 T6).

TDD RED: these tests must fail before implementation, GREEN after.

Tests:
1. strat_supertrend is registered in _build_grid + callable.
2. On a known trend-flip series: entry at BEAR->BULL bar, exit at BULL->BEAR bar.
3. Parity with streaming SupertrendStrategy: vectorized and streaming produce
   entry/exit at the same bar indices on identical data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from src.marketdata.models import Bar, DataQuality
from src.signalgen.supertrend_strategy import SupertrendStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_df(
    closes: list[float], highs: list[float] | None = None, lows: list[float] | None = None
) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame for strat functions."""
    n = len(closes)
    closes_arr = np.array(closes, dtype=np.float64)
    highs_arr = np.array(highs, dtype=np.float64) if highs is not None else closes_arr + 0.5
    lows_arr = np.array(lows, dtype=np.float64) if lows is not None else closes_arr - 0.5
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    ts = [t0 + timedelta(hours=i) for i in range(n)]
    return pd.DataFrame(
        {
            "ts": ts,
            "open": closes_arr,
            "high": highs_arr,
            "low": lows_arr,
            "close": closes_arr,
            "volume": np.ones(n),
        }
    )


def _make_bar(
    close_time: datetime,
    close: float,
    high: float | None = None,
    low: float | None = None,
    symbol: str = "BTCUSDT",
) -> Bar:
    h = high if high is not None else close + 0.5
    lo = low if low is not None else close - 0.5
    return Bar(
        symbol=symbol,
        interval="1h",
        open_time=close_time - timedelta(hours=1),
        close_time=close_time,
        open=Decimal(str(close)),
        high=Decimal(str(h)),
        low=Decimal(str(lo)),
        close=Decimal(str(close)),
        volume=Decimal("100.0"),
        trade_count=100,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def _build_trend_flip_series(
    flat_price: float = 100.0,
    flat_count: int = 30,
    bull_prices: list[float] | None = None,
    bear_prices: list[float] | None = None,
) -> tuple[list[float], list[float], list[float]]:
    """Build a price series with clear BEAR->BULL->BEAR flips.

    Returns (closes, highs, lows).
    """
    if bull_prices is None:
        bull_prices = [110, 130, 160, 200, 240, 280, 300, 310, 315, 320]
    if bear_prices is None:
        bear_prices = [270, 220, 180, 150, 120, 100, 90]

    closes: list[float] = []
    highs: list[float] = []
    lows: list[float] = []

    # Flat warmup
    for _ in range(flat_count):
        closes.append(flat_price)
        highs.append(flat_price + 0.5)
        lows.append(flat_price - 0.5)

    # Bull run
    for p in bull_prices:
        closes.append(p)
        highs.append(p + 1.0)
        lows.append(p - 1.0)

    # Bear crash
    for p in bear_prices:
        closes.append(p)
        highs.append(p + 1.0)
        lows.append(p - 1.0)

    return closes, highs, lows


# ---------------------------------------------------------------------------
# Test 1: registration + callable
# ---------------------------------------------------------------------------


def test_strat_supertrend_registered_in_build_grid() -> None:
    """_build_grid('supertrend') must return (callable, non-empty list, non-empty list)."""
    from scripts.autoresearch_endless import _build_grid

    strat_fn, param_grid, stop_mults = _build_grid("supertrend")
    assert callable(strat_fn)
    assert len(param_grid) > 0
    assert len(stop_mults) > 0


def test_strat_supertrend_function_callable() -> None:
    """strat_supertrend must be importable and callable with (df, atr_period, mult)."""
    from scripts.autoresearch_endless import strat_supertrend

    closes, highs, lows = _build_trend_flip_series()
    df = _make_df(closes, highs, lows)
    result = strat_supertrend(df, atr_period=10, mult=3.0)
    assert len(result) == 4  # entry, exit_, warmup, atr_arr
    entry, exit_, warmup, atr_arr = result
    assert isinstance(entry, np.ndarray)
    assert isinstance(exit_, np.ndarray)
    assert len(entry) == len(df)
    assert len(exit_) == len(df)
    assert isinstance(warmup, int)
    assert isinstance(atr_arr, np.ndarray)


# ---------------------------------------------------------------------------
# Test 2: signals on a known trend-flip series
# ---------------------------------------------------------------------------


def test_strat_supertrend_produces_entry_on_bull_flip() -> None:
    """strat_supertrend must produce at least one entry signal (BEAR->BULL flip)."""
    from scripts.autoresearch_endless import strat_supertrend

    closes, highs, lows = _build_trend_flip_series()
    df = _make_df(closes, highs, lows)
    entry, exit_, warmup, _ = strat_supertrend(df, atr_period=10, mult=3.0)
    assert entry[warmup:].any(), "Expected at least one entry (BEAR->BULL flip) after warmup"


def test_strat_supertrend_produces_exit_on_bear_flip() -> None:
    """strat_supertrend must produce at least one exit signal (BULL->BEAR flip)."""
    from scripts.autoresearch_endless import strat_supertrend

    closes, highs, lows = _build_trend_flip_series()
    df = _make_df(closes, highs, lows)
    entry, exit_, warmup, _ = strat_supertrend(df, atr_period=10, mult=3.0)
    assert exit_[warmup:].any(), "Expected at least one exit (BULL->BEAR flip) after warmup"


def test_strat_supertrend_entry_before_exit() -> None:
    """First entry index must precede first exit index on a bull-then-bear series."""
    from scripts.autoresearch_endless import strat_supertrend

    closes, highs, lows = _build_trend_flip_series()
    df = _make_df(closes, highs, lows)
    entry, exit_, warmup, _ = strat_supertrend(df, atr_period=10, mult=3.0)
    entry_indices = np.where(entry)[0]
    exit_indices = np.where(exit_)[0]
    assert len(entry_indices) > 0
    assert len(exit_indices) > 0
    assert (
        entry_indices[0] < exit_indices[0]
    ), f"First entry bar {entry_indices[0]} must be before first exit bar {exit_indices[0]}"


# ---------------------------------------------------------------------------
# Test 3: parity with streaming SupertrendStrategy
# ---------------------------------------------------------------------------


def _run_streaming(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    atr_period: int = 10,
    mult: float = 3.0,
) -> tuple[list[int], list[int]]:
    """Run streaming SupertrendStrategy on the same series; return (entry_bars, exit_bars)."""
    strat = SupertrendStrategy(symbol="BTCUSDT", atr_period=atr_period, multiplier=mult)
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    entry_bars: list[int] = []
    exit_bars: list[int] = []
    for i, (c, h, lo) in enumerate(zip(closes, highs, lows, strict=False)):
        ct = t0 + timedelta(hours=i + 1)
        sig = strat.on_bar(_make_bar(ct, c, h, lo))
        if sig is not None:
            from src.signalgen.models import SignalSide

            if sig.side == SignalSide.LONG:
                entry_bars.append(i)
            elif sig.side == SignalSide.FLAT:
                exit_bars.append(i)
    return entry_bars, exit_bars


def test_strat_supertrend_parity_with_streaming() -> None:
    """Vectorized strat_supertrend signals must match streaming SupertrendStrategy bar indices.

    The streaming strategy emits a signal ON bar T (closed bar T evaluated, fill T+1).
    The vectorized strat sets entry[T] = True / exit_[T] = True at the same bar T.
    Bar indices must match exactly.
    """
    from scripts.autoresearch_endless import strat_supertrend

    closes, highs, lows = _build_trend_flip_series()
    df = _make_df(closes, highs, lows)

    # Vectorized signals
    entry, exit_, warmup, _ = strat_supertrend(df, atr_period=10, mult=3.0)
    vec_entry_bars = list(np.where(entry)[0])
    vec_exit_bars = list(np.where(exit_)[0])

    # Streaming signals (bar index = position in the series, 0-based)
    stream_entry_bars, stream_exit_bars = _run_streaming(
        closes, highs, lows, atr_period=10, mult=3.0
    )

    assert (
        vec_entry_bars == stream_entry_bars
    ), f"Entry bar mismatch:\n  vectorized: {vec_entry_bars}\n  streaming:  {stream_entry_bars}"
    assert (
        vec_exit_bars == stream_exit_bars
    ), f"Exit bar mismatch:\n  vectorized: {vec_exit_bars}\n  streaming:  {stream_exit_bars}"


# ---------------------------------------------------------------------------
# Test 4: COMBOS sweep range sanity
# ---------------------------------------------------------------------------


def test_supertrend_combo_grid_includes_center_params() -> None:
    """COMBOS grid for supertrend must include center params atr_period=10, mult=3.0 (ADR 0067)."""
    from scripts.autoresearch_endless import _build_grid

    _, param_grid, _ = _build_grid("supertrend")
    center = {"atr_period": 10, "mult": 3.0}
    assert (
        center in param_grid
    ), f"Center params {center} not found in supertrend grid (ADR 0067 requires atr_period=10, mult=3.0)"


def test_supertrend_combo_grid_covers_sweep_range() -> None:
    """Grid must cover atr_period ∈ [7..21] and mult ∈ [2.0..4.0]."""
    from scripts.autoresearch_endless import _build_grid

    _, param_grid, _ = _build_grid("supertrend")
    periods = {p["atr_period"] for p in param_grid}
    mults = {p["mult"] for p in param_grid}
    assert min(periods) <= 7
    assert max(periods) >= 21
    assert min(mults) <= 2.0
    assert max(mults) >= 4.0
