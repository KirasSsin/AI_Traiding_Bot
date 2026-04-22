"""Unit tests for signalgen.indicators — goldens vs TA-Lib + manual formulas."""

import numpy as np
import pytest
from src.signalgen.indicators import ema  # noqa: E402


def test_ema_classical_matches_talib_formula() -> None:
    """EMA(n) classical: α = 2/(n+1); seed via SMA первых n баров."""
    close = np.array(
        [
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
            6.0,
            7.0,
            8.0,
            9.0,
            10.0,
            11.0,
            12.0,
            13.0,
            14.0,
            15.0,
            16.0,
            17.0,
            18.0,
            19.0,
            20.0,
        ]
    )
    result = ema(close, period=5, mode="classical")

    # Первые 4 значения — NaN (warm-up)
    assert np.all(np.isnan(result[:4]))

    # EMA[4] = SMA(close[0..4]) = 3.0
    assert result[4] == pytest.approx(3.0, abs=1e-12)

    # α = 2/(5+1) = 1/3; EMA[5] = α·close[5] + (1-α)·EMA[4]
    #                         = (1/3)·6 + (2/3)·3 = 4.0
    assert result[5] == pytest.approx(4.0, abs=1e-12)

    # EMA[6] = (1/3)·7 + (2/3)·4 = 5.0
    assert result[6] == pytest.approx(5.0, abs=1e-12)
