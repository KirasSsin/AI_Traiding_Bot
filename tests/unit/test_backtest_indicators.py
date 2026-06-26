"""S55 PY-3 — shared Wilder ATR (`src.backtest.indicators._wilder_atr`) parity tests.

The Wilder ATR (SMA-seed + recursion, prev_close[0]=close[0] convention) was
duplicated byte-for-byte in volume_breakout_runner.py and atr_breakout_runner.py.
PY-3 extracted ONE implementation into src/backtest/indicators.py and imports it
into both runners aliased as `_atr`.

These tests pin the math against a hand-computed fixture and assert both runners
share the exact same callable, so the two call sites can never silently diverge.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from src.backtest.indicators import _wilder_atr


def _make_df(highs: list[float], lows: list[float], closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"high": highs, "low": lows, "close": closes})


def test_wilder_atr_matches_hand_computed_fixture() -> None:
    """Hand-compute Wilder ATR(period=3) and assert the shared fn reproduces it.

    Convention: prev_close[0] = close[0] → TR[0] = high[0] - low[0].
    TR[i>0] = max(h-l, |h - prev_close|, |l - prev_close|).
    Seed: ATR[period-1] = mean(TR[0:period]). Recursion:
    ATR[i] = (ATR[i-1] * (period-1) + TR[i]) / period.
    """
    high = [10.0, 11.0, 12.0, 11.5, 13.0]
    low = [9.0, 9.5, 10.5, 10.0, 11.0]
    close = [9.5, 10.5, 11.0, 10.5, 12.5]
    df = _make_df(high, low, close)

    period = 3
    h = np.array(high)
    lo = np.array(low)
    c = np.array(close)
    prev_close = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum.reduce([h - lo, np.abs(h - prev_close), np.abs(lo - prev_close)])
    expected = np.full_like(tr, np.nan)
    expected[period - 1] = tr[:period].mean()
    for i in range(period, len(tr)):
        expected[i] = (expected[i - 1] * (period - 1) + tr[i]) / period

    out = _wilder_atr(df, period)

    # NaN warm-up region (indices < period-1).
    assert np.isnan(out[: period - 1]).all()
    np.testing.assert_allclose(out[period - 1 :], expected[period - 1 :], rtol=1e-12)


def test_wilder_atr_returns_all_nan_when_shorter_than_period() -> None:
    df = _make_df([1.0, 2.0], [0.5, 1.0], [0.8, 1.5])
    out = _wilder_atr(df, period=5)
    assert out.shape == (2,)
    assert np.isnan(out).all()


def test_tr_zero_index_uses_close_as_prev_close() -> None:
    """TR[0] must equal high[0]-low[0] (prev_close[0]=close[0] convention)."""
    df = _make_df([10.0, 10.0, 10.0], [8.0, 8.0, 8.0], [9.0, 9.0, 9.0])
    out = _wilder_atr(df, period=2)
    # All TR = 2.0 (h-l constant, no gaps) → ATR seed = 2.0, stays 2.0.
    assert out[1] == 2.0
    assert out[2] == 2.0


def test_both_runners_share_the_exact_same_atr_callable() -> None:
    """volume_breakout_runner._atr and atr_breakout_runner._atr are the shared fn.

    Guards against future re-divergence: both must be the identical object
    imported from src.backtest.indicators._wilder_atr.
    """
    from src.backtest import atr_breakout_runner, volume_breakout_runner

    assert volume_breakout_runner._atr is _wilder_atr
    assert atr_breakout_runner._atr is _wilder_atr
    assert volume_breakout_runner._atr is atr_breakout_runner._atr
