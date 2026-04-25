"""Tests for Bollinger Bands indicator (S15 T2).

Verifies BB(period, k) formula: middle=SMA, upper=middle+k*stdev_pop, lower=middle-k*stdev_pop.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.signalgen.bollinger_bands import bollinger_bands


def test_bb_constant_series_zero_width() -> None:
    """Constant prices → upper == middle == lower (stdev = 0)."""
    close = np.full(30, 100.0)
    upper, middle, lower = bollinger_bands(close, period=20, k=2.0)
    assert np.isclose(upper[-1], 100.0)
    assert np.isclose(middle[-1], 100.0)
    assert np.isclose(lower[-1], 100.0)


def test_bb_warmup_nan() -> None:
    """First (period-1) values are NaN, period-th index = first valid."""
    close = np.array([100.0 + i for i in range(25)])
    upper, middle, lower = bollinger_bands(close, period=20, k=2.0)
    assert np.isnan(upper[0])
    assert np.isnan(upper[18])  # period - 2
    assert not np.isnan(upper[19])  # first valid (period - 1)
    assert not np.isnan(middle[19])
    assert not np.isnan(lower[19])


def test_bb_known_values_linear_ramp() -> None:
    """Linear ramp 1..20, period=20, k=2: middle=10.5, upper/lower symmetric."""
    close = np.arange(1.0, 21.0)  # [1, 2, ..., 20]
    upper, middle, lower = bollinger_bands(close, period=20, k=2.0)
    assert np.isclose(middle[-1], 10.5)
    expected_std = float(np.std(close, ddof=0))
    assert np.isclose(upper[-1], 10.5 + 2.0 * expected_std)
    assert np.isclose(lower[-1], 10.5 - 2.0 * expected_std)


def test_bb_invalid_period_raises() -> None:
    with pytest.raises(ValueError, match="period must be >= 2"):
        bollinger_bands(np.array([1.0, 2.0]), period=1, k=2.0)


def test_bb_invalid_k_raises() -> None:
    with pytest.raises(ValueError, match="k must be > 0"):
        bollinger_bands(np.array([1.0, 2.0]), period=20, k=0.0)
    with pytest.raises(ValueError, match="k must be > 0"):
        bollinger_bands(np.array([1.0, 2.0]), period=20, k=-1.0)


def test_bb_2d_input_rejected() -> None:
    with pytest.raises(ValueError, match="close must be 1-D"):
        bollinger_bands(np.array([[1.0, 2.0], [3.0, 4.0]]), period=2, k=2.0)


def test_bb_short_series_returns_all_nan() -> None:
    """len(close) < period → all NaN, no error."""
    close = np.array([1.0, 2.0, 3.0])
    upper, middle, lower = bollinger_bands(close, period=20, k=2.0)
    assert np.all(np.isnan(upper))
    assert np.all(np.isnan(middle))
    assert np.all(np.isnan(lower))


def test_bb_default_params() -> None:
    """Default period=20, k=2.0."""
    close = np.arange(1.0, 25.0)
    u1, m1, l1 = bollinger_bands(close)
    u2, m2, l2 = bollinger_bands(close, period=20, k=2.0)
    assert np.allclose(u1[~np.isnan(u1)], u2[~np.isnan(u2)])
    assert np.allclose(m1[~np.isnan(m1)], m2[~np.isnan(m2)])
    assert np.allclose(l1[~np.isnan(l1)], l2[~np.isnan(l2)])


def test_bb_upper_always_above_lower() -> None:
    """For any non-constant series, upper > middle > lower (when valid)."""
    np.random.seed(42)
    close = np.cumsum(np.random.randn(100)) + 100.0
    upper, middle, lower = bollinger_bands(close, period=20, k=2.0)
    valid = ~np.isnan(upper)
    assert np.all(upper[valid] >= middle[valid])
    assert np.all(middle[valid] >= lower[valid])
