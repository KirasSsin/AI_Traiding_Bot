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
    raise NotImplementedError(f"mode={mode} implemented in Task 3")
