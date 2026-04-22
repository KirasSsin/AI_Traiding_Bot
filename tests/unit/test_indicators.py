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


def test_ema_wilder_matches_manual_recurrence() -> None:
    """EMA(n) Wilder: α=1/n; seed = SMA первых n; recurrence на всех t >= n."""
    close = np.arange(1.0, 21.0)  # 1..20

    result = ema(close, period=5, mode="wilder")

    # Warm-up: первые 4 значения NaN
    assert np.all(np.isnan(result[:4]))

    # Wilder seed: SMA(1..5) = 3.0
    assert result[4] == pytest.approx(3.0, abs=1e-12)

    # α = 1/5 = 0.2
    # EMA[5] = 0.2·6 + 0.8·3 = 1.2 + 2.4 = 3.6
    assert result[5] == pytest.approx(3.6, abs=1e-12)
    # EMA[6] = 0.2·7 + 0.8·3.6 = 1.4 + 2.88 = 4.28
    assert result[6] == pytest.approx(4.28, abs=1e-12)


def test_ema_rejects_bad_inputs() -> None:
    close = np.arange(1.0, 11.0)
    with pytest.raises(ValueError, match="period must be >= 2"):
        ema(close, period=1)
    with pytest.raises(ValueError, match="1-D"):
        ema(close.reshape(2, 5), period=3)


def test_rsi_wilder_matches_talib() -> None:
    """RSI(14) Wilder: сверяем с прямым вызовом talib.RSI (который использует Wilder)."""
    import talib

    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.standard_normal(100))

    from src.signalgen.indicators import rsi

    result = rsi(close, period=14)
    expected = talib.RSI(close, timeperiod=14)

    # Warm-up: первые 14 NaN
    assert np.all(np.isnan(result[:14]))

    np.testing.assert_allclose(result[14:], expected[14:], rtol=1e-9)


def test_rsi_extremes() -> None:
    """RSI=100 при монотонном росте, RSI=0 при монотонном падении."""
    from src.signalgen.indicators import rsi

    up = np.arange(1.0, 30.0)
    result = rsi(up, period=14)
    assert result[-1] == pytest.approx(100.0, abs=1e-6)

    down = np.arange(30.0, 1.0, -1.0)
    result = rsi(down, period=14)
    assert result[-1] == pytest.approx(0.0, abs=1e-6)
