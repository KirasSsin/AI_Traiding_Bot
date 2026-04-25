"""Bollinger Bands indicator (Bollinger 1980s).

Middle = SMA(close, period)
Upper  = middle + k * stdev_pop(close, period)
Lower  = middle - k * stdev_pop(close, period)

Population standard deviation (ddof=0) per Bollinger original spec.
S15 — NEW indicator for MeanReversionRsiBBStrategy (ADR 0030).
"""
from __future__ import annotations

import numpy as np


def bollinger_bands(
    close: np.ndarray, *, period: int = 20, k: float = 2.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute Bollinger Bands (upper, middle, lower).

    Args:
        close: 1-D float array of close prices.
        period: rolling window size (default 20 per Bollinger).
        k: standard-deviation multiplier (default 2.0 per Bollinger).

    Returns:
        Tuple `(upper, middle, lower)` of three 1-D numpy arrays, same length
        as `close`. First (period - 1) values = NaN (warm-up).

    Raises:
        ValueError: period < 2 OR k <= 0 OR close not 1-D.
    """
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    if k <= 0:
        raise ValueError(f"k must be > 0, got {k}")
    if close.ndim != 1:
        raise ValueError("close must be 1-D")

    n = len(close)
    middle = np.full(n, np.nan, dtype=np.float64)
    upper = np.full(n, np.nan, dtype=np.float64)
    lower = np.full(n, np.nan, dtype=np.float64)

    if n < period:
        return upper, middle, lower

    for i in range(period - 1, n):
        window = close[i - period + 1 : i + 1]
        m = float(np.mean(window))
        s = float(np.std(window, ddof=0))  # population stdev per Bollinger
        middle[i] = m
        upper[i] = m + k * s
        lower[i] = m - k * s

    return upper, middle, lower
