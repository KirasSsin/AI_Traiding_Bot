"""Unit tests for compute_volume_breakout_signals helper (S39 T2)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _synthetic_df(n: int = 100, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0, 2, n)
    low = close - rng.uniform(0, 2, n)
    open_ = close + rng.normal(0, 0.5, n)
    volume = rng.uniform(1000, 5000, n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})


def test_volume_breakout_signals_no_lookahead() -> None:
    """Entry signal on bar i must use ONLY data through bar i-1 (no look-ahead)."""
    from src.backtest.indicators import compute_volume_breakout_signals

    df = _synthetic_df(50)
    signals = compute_volume_breakout_signals(
        df,
        lookback_n=9,
        exit_lookback_n=8,
        vol_window=10,
        vol_mult=1.4563,
        atr_period=9,
    )
    df2 = df.copy()
    df2.iloc[-1, df2.columns.get_loc("close")] = 999999.0
    signals2 = compute_volume_breakout_signals(
        df2,
        lookback_n=9,
        exit_lookback_n=8,
        vol_window=10,
        vol_mult=1.4563,
        atr_period=9,
    )
    np.testing.assert_array_equal(signals[:-1], signals2[:-1])


def test_volume_breakout_warmup_zeros() -> None:
    """First max(lookback_n, exit_lookback_n, atr_period, vol_window) + 2 bars = no signals."""
    from src.backtest.indicators import compute_volume_breakout_signals

    df = _synthetic_df(50)
    signals = compute_volume_breakout_signals(
        df,
        lookback_n=9,
        exit_lookback_n=8,
        vol_window=10,
        vol_mult=1.4563,
        atr_period=9,
    )
    warmup = max(9, 8, 9, 10) + 2
    assert (signals[:warmup] == 0).all()


def test_volume_breakout_entry_requires_volume_confirm() -> None:
    """Entry needs BOTH price > rolling_high AND volume > vol_mean * vol_mult."""
    from src.backtest.indicators import compute_volume_breakout_signals

    n = 30
    df = pd.DataFrame(
        {
            "open": np.full(n, 100.0),
            "high": np.full(n, 100.0),
            "low": np.full(n, 100.0),
            "close": np.full(n, 100.0),
            "volume": np.full(n, 1000.0),
        }
    )
    df.loc[20, "close"] = 200.0
    df.loc[20, "high"] = 200.0
    signals = compute_volume_breakout_signals(
        df,
        lookback_n=9,
        exit_lookback_n=8,
        vol_window=10,
        vol_mult=1.4563,
        atr_period=9,
    )
    assert signals[21] != 1


def test_volume_breakout_entry_with_volume_confirm() -> None:
    """Entry triggers when BOTH conditions met."""
    from src.backtest.indicators import compute_volume_breakout_signals

    n = 30
    df = pd.DataFrame(
        {
            "open": np.full(n, 100.0),
            "high": np.full(n, 100.0),
            "low": np.full(n, 100.0),
            "close": np.full(n, 100.0),
            "volume": np.full(n, 1000.0),
        }
    )
    df.loc[20, "close"] = 200.0
    df.loc[20, "high"] = 200.0
    df.loc[20, "volume"] = 5000.0
    signals = compute_volume_breakout_signals(
        df,
        lookback_n=9,
        exit_lookback_n=8,
        vol_window=10,
        vol_mult=1.4563,
        atr_period=9,
    )
    assert signals[21] == 1


def test_volume_breakout_channel_exit() -> None:
    """Channel exit triggers when close < rolling_low(exit_lookback_n)."""
    from src.backtest.indicators import compute_volume_breakout_signals

    n = 30
    df = pd.DataFrame(
        {
            "open": np.full(n, 100.0),
            "high": np.full(n, 100.0),
            "low": np.full(n, 100.0),
            "close": np.full(n, 100.0),
            "volume": np.full(n, 1000.0),
        }
    )
    df.loc[20, "close"] = 50.0
    df.loc[20, "low"] = 50.0
    signals = compute_volume_breakout_signals(
        df,
        lookback_n=9,
        exit_lookback_n=8,
        vol_window=10,
        vol_mult=1.4563,
        atr_period=9,
    )
    assert signals[21] == -1
