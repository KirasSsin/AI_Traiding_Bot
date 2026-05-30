"""Unit tests for src.signalgen.indicators.wilder_atr (manual Wilder RMA recursion).

Distinct from talib-based indicators.atr() — uses prev_close[0]=close[0] seed and
SMA-seed at index period-1, mirroring scripts/autoresearch_endless.py::_atr().
"""

import numpy as np
from src.signalgen.indicators import wilder_atr


def test_wilder_atr_matches_recursion() -> None:
    high = np.array([10.0, 11.0, 12.0, 11.0, 13.0, 12.0, 14.0], dtype=np.float64)
    low = np.array([9.0, 9.5, 10.0, 10.0, 11.0, 11.0, 12.0], dtype=np.float64)
    close = np.array([9.5, 10.5, 11.0, 10.5, 12.0, 11.5, 13.0], dtype=np.float64)
    period = 3
    atr = wilder_atr(high, low, close, period)
    assert np.isnan(atr[: period - 1]).all()
    prev_c = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([high - low, np.abs(high - prev_c), np.abs(low - prev_c)])
    assert abs(atr[period - 1] - tr[:period].mean()) < 1e-12
    assert abs(atr[period] - (atr[period - 1] * (period - 1) + tr[period]) / period) < 1e-12


def test_wilder_atr_all_nan_when_short() -> None:
    result = wilder_atr(
        np.array([1.0, 2.0]),
        np.array([0.5, 1.0]),
        np.array([1.0, 1.5]),
        5,
    )
    assert np.isnan(result).all()


def test_wilder_atr_matches_atr_breakout_method() -> None:
    """Parity: extracted fn == original ATRBreakoutStrategy._wilder_atr output."""
    from src.signalgen.atr_breakout_strategy import ATRBreakoutStrategy

    rng = np.random.default_rng(42)
    n = 50
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + np.abs(rng.normal(0, 0.5, n))
    low = close - np.abs(rng.normal(0, 0.5, n))
    period = 14

    extracted = wilder_atr(high, low, close, period)
    original = ATRBreakoutStrategy._wilder_atr(high, low, close, period)

    np.testing.assert_array_equal(np.isnan(extracted), np.isnan(original))
    valid = ~np.isnan(extracted)
    np.testing.assert_allclose(extracted[valid], original[valid], rtol=0, atol=0)
    assert not np.isnan(extracted[period:]).any()
    assert np.isnan(extracted[: period - 1]).all()
