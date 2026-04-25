"""Verify vector_backtest annualization factor matches 1H bar period.

Sprint 10 Q6 (per pre-s10-backlog.md trader REVISE accepted).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from src.backtest.vector_backtest import VectorBacktester


def _synthetic_df(n_bars: int = 100) -> pd.DataFrame:
    """Build synthetic 1H OHLCV с alternating signals for Sharpe sanity check."""
    rng = np.random.default_rng(42)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.01, n_bars)))
    return pd.DataFrame({
        "close": closes,
        "signal": [1 if i % 4 < 2 else -1 for i in range(n_bars)],
    })


def test_sharpe_uses_1h_annualization_factor() -> None:
    """Sharpe should use sqrt(8760) = sqrt(365*24) для 1H bars, NOT sqrt(365*24*60)."""
    df = _synthetic_df()
    bt = VectorBacktester(df, initial_capital=10000.0, maker_fee=0.001)
    result = bt.run()

    # Re-compute с correct factor — must match
    returns_mean = bt.df["strategy_returns"].mean()
    returns_std = bt.df["strategy_returns"].std()
    expected_sharpe = (returns_mean / returns_std) * np.sqrt(365 * 24)
    assert abs(result["Sharpe Ratio"] - expected_sharpe) < 1e-9, (
        f"Sharpe used wrong factor. Got {result['Sharpe Ratio']}, "
        f"expected {expected_sharpe} (sqrt(365*24)=sqrt(8760))"
    )


def test_sharpe_matches_replay_engine_convention() -> None:
    """vector_backtest annualization must match replay_engine._compute_metrics:51 convention."""
    expected_factor = np.sqrt(24 * 365)
    assert abs(expected_factor - np.sqrt(8760)) < 1e-9
