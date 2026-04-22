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
    if not (high.shape == low.shape == close.shape) or high.ndim != 1:
        raise ValueError("high, low, close must be 1-D and same shape")
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    return talib.ATR(high, low, close, timeperiod=period)
