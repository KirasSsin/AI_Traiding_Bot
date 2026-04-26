"""S27 T3 — RSI/ATR warm-up gating в backtest indicators.

Bug pre-fix: src/backtest/indicators.py:50-53 used `pandas.ewm` без NaN warm-up.
RSI[0]≈50 (fillna), RSI[14]≈46.7 (talib) — diverge substantially first 14 bars.

Per trading-logic-reviewer S27 audit:
- mean_reversion: BB gates (min_periods=20) → first 19 bars produce NaN bb_lower
  → no spurious signals. Immune.
- ema_crossover: RSI<overbought filter может admit RSI-invalid-gated entries
  в first 14 bars каждого fold.

Fix: mask first `rsi_period` bars RSI = NaN.
ATR similarly: mask first `atr_period` bars (less critical, SL/TP affected).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest.indicators import calculate_indicators


def _synthetic_ohlcv(n_bars: int = 100, seed: int = 42) -> pd.DataFrame:
    """Random walk OHLCV для indicator warm-up tests."""
    rng = np.random.default_rng(seed)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.01, n_bars)))
    highs = closes * (1.0 + np.abs(rng.normal(0, 0.005, n_bars)))
    lows = closes * (1.0 - np.abs(rng.normal(0, 0.005, n_bars)))
    opens = closes + rng.normal(0, 0.5, n_bars)
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n_bars, freq="1h"),
        "open": opens, "high": highs, "low": lows, "close": closes,
        "volume": rng.uniform(100, 1000, n_bars),
    })


def test_rsi_first_period_bars_are_nan_ema_crossover() -> None:
    """RSI period=14 → RSI[0..13] must be NaN (warm-up not complete)."""
    df = _synthetic_ohlcv(n_bars=50)
    cfg = {
        "strategy": {
            "type": "ema_crossover",
            "indicators": {
                "rsi": {"period": 14, "overbought": 68},
                "ema": {"fast_period": 12, "slow_period": 26},
                "atr": {"period": 14},
            },
        },
    }
    out = calculate_indicators(df, cfg)

    rsi = out["rsi"].to_numpy()
    # First 14 bars (period=14) MUST be NaN — pre-fix returned fillna(50.0)
    assert np.all(np.isnan(rsi[:14])), (
        f"RSI warm-up not masked. First 14 values: {rsi[:14]}"
    )
    # After warm-up, RSI must be valid finite values in [0, 100]
    assert np.all(~np.isnan(rsi[14:]))
    assert np.all((rsi[14:] >= 0) & (rsi[14:] <= 100))


def test_rsi_signal_does_not_fire_during_warmup_ema_crossover() -> None:
    """ema_crossover entry: RSI<overbought filter must not gate on warm-up RSI."""
    df = _synthetic_ohlcv(n_bars=50)
    cfg = {
        "strategy": {
            "type": "ema_crossover",
            "indicators": {
                "rsi": {"period": 14, "overbought": 68},
                "ema": {"fast_period": 12, "slow_period": 26},
                "atr": {"period": 14},
            },
        },
    }
    out = calculate_indicators(df, cfg)

    # Signals в first 14 bars must be 0 (RSI=NaN → boolean comparison False)
    assert (out["signal"].iloc[:14] == 0).all()


def test_rsi_warmup_does_not_break_mean_reversion() -> None:
    """mean_reversion: BB gates (min_periods=20) handle warm-up. No regression."""
    df = _synthetic_ohlcv(n_bars=100)
    cfg = {
        "strategy": {
            "type": "mean_reversion",
            "indicators": {
                "rsi": {"period": 14, "oversold": 30},
                "bb": {"period": 20, "k": 2.0},
                "atr": {"period": 14},
            },
        },
    }
    out = calculate_indicators(df, cfg)

    # Signal column populated, no crash
    assert "signal" in out.columns
    assert len(out) == 100
    # First 19 bars: bb_lower = NaN → comparison False → signal=0
    assert (out["signal"].iloc[:19] == 0).all()


def test_atr_first_period_bars_nan() -> None:
    """ATR warm-up: first `atr_period` bars NaN (consistency с RSI)."""
    df = _synthetic_ohlcv(n_bars=50)
    cfg = {
        "strategy": {
            "type": "ema_crossover",
            "indicators": {
                "rsi": {"period": 14, "overbought": 68},
                "ema": {"fast_period": 12, "slow_period": 26},
                "atr": {"period": 14},
            },
        },
    }
    out = calculate_indicators(df, cfg)

    atr = out["atr"].to_numpy()
    # First `period` bars NaN — under-initialized
    assert np.all(np.isnan(atr[:14]))
    # After warm-up, finite positive
    assert np.all(~np.isnan(atr[14:]))
    assert np.all(atr[14:] > 0)
