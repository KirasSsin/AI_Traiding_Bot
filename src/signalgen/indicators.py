"""TA-Lib indicator wrappers — stateless, numpy in/out.

ADR 0011: Wilder smoothing for ADX/RSI/ATR; Classical EMA for crossovers.
"""

from typing import Literal

import numpy as np
import talib

EmaMode = Literal["classical", "wilder"]


def ema(close: np.ndarray, period: int, mode: EmaMode = "classical") -> np.ndarray:
    """Exponential Moving Average.

    Args:
        close: 1-D float array of close prices.
        period: smoothing period (n >= 2).
        mode: "classical" → α=2/(n+1); "wilder" → α=1/n.

    Returns:
        1-D float array same length as `close`; первые (period-1) значений = NaN.

    Notes:
        TA-Lib `EMA` использует classical formula с SMA-seed (per ADR 0011).
        Wilder режим — собственная реализация (seed + recurrence α=1/n); follow-up в Task 3.
    """
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    if close.ndim != 1:
        raise ValueError("close must be 1-D")
    if mode == "classical":
        return talib.EMA(close, timeperiod=period)
    # Wilder: α = 1/period; seed = SMA(close[0..period-1]); recurrence на t >= period.
    result = np.full_like(close, np.nan, dtype=np.float64)
    if len(close) < period:
        return result
    seed = np.mean(close[:period])
    result[period - 1] = seed
    alpha = 1.0 / period
    for t in range(period, len(close)):
        result[t] = alpha * close[t] + (1.0 - alpha) * result[t - 1]
    return result


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index (Wilder 1978).

    TA-Lib `RSI` использует Wilder smoothing по умолчанию (α=1/n) per ADR 0011.

    Args:
        close: 1-D float array of close prices.
        period: period (default 14 per Wilder).

    Returns:
        Array same length as `close`, первые `period` значений — NaN.
        Диапазон [0, 100].
    """
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    if close.ndim != 1:
        raise ValueError("close must be 1-D")
    return talib.RSI(close, timeperiod=period)


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range (Wilder 1978).

    TR = max(high-low, |high-prev_close|, |low-prev_close|).
    ATR[t] = Wilder-smooth(TR, period) per ADR 0011.

    Args:
        high, low, close: 1-D arrays same length.
        period: period (default 14).

    Returns:
        Array same length as inputs, первые `period` значений = NaN. Всегда >= 0.
    """
    _validate_hlc(high, low, close, period)
    return talib.ATR(high, low, close, timeperiod=period)


def wilder_atr(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int,
) -> np.ndarray:
    """Wilder ATR via manual RMA recursion — distinct from talib-based ``atr()``.

    Exact port of scripts/autoresearch_endless.py::_atr(). Uses
    ``prev_close[0] = close[0]`` for the first true-range bar, seeds the recursion
    with an SMA of the first ``period`` TR values at index ``period-1``, then
    applies Wilder smoothing ``atr[i] = (atr[i-1]*(period-1) + tr[i]) / period``.

    NOTE: numerically distinct from :func:`atr` (talib seed = period, ~1.4%
    divergence). Shared by ATR breakout and Supertrend; ``volume_breakout`` keeps
    talib ``atr()`` (ADR 0059 anti-snooping LOCKED).

    Args:
        high, low, close: 1-D float arrays, same length.
        period: smoothing period.

    Returns:
        Array same length as input; NaN for indices < ``period-1``. All-NaN when
        ``len(close) < period``.
    """
    n = len(close)
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr: np.ndarray = np.maximum.reduce(
        [
            high - low,
            np.abs(high - prev_close),
            np.abs(low - prev_close),
        ]
    )
    atr_out = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return atr_out
    atr_out[period - 1] = tr[:period].mean()
    for i in range(period, n):
        atr_out[i] = (atr_out[i - 1] * (period - 1) + tr[i]) / period
    return atr_out


def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average Directional Index (Wilder 1978).

    ADX = Wilder-smooth(DX, period); DX = 100 · |+DI - -DI| / (+DI + -DI).
    Range [0, 100]; >25 → trending.

    Returns:
        1-D array; warm-up ≈ 2·period - 1 баров NaN (double-smoothing).
    """
    _validate_hlc(high, low, close, period)
    return talib.ADX(high, low, close, timeperiod=period)


def plus_di(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """+DI per Wilder 1978. Range [0, 100]."""
    _validate_hlc(high, low, close, period)
    return talib.PLUS_DI(high, low, close, timeperiod=period)


def minus_di(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """-DI per Wilder 1978. Range [0, 100]."""
    _validate_hlc(high, low, close, period)
    return talib.MINUS_DI(high, low, close, timeperiod=period)


def _validate_hlc(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> None:
    if not (high.shape == low.shape == close.shape) or high.ndim != 1:
        raise ValueError("high, low, close must be 1-D and same shape")
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
