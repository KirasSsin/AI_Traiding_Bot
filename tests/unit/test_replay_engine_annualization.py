"""S27 T1 — replay_engine._compute_metrics annualization parameterization.

Bug pre-fix: `np.sqrt(24 * 365)` hardcoded для всех timeframes.
For 4H data: IS Sharpe overstated 2x. For 15M/5M: understated.
Affects 27/30 experiments в S27 audit (formulas_audit_v1.json).

Fix: accept `bars_per_year` parameter, replace hardcoded constant.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest.replay_engine import _compute_metrics


def _synthetic_equity_trades(
    n_bars: int = 200, daily_return: float = 0.001, vol: float = 0.01,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build synthetic equity curve + trades_df with deterministic returns."""
    rng = np.random.default_rng(42)
    returns = rng.normal(daily_return, vol, n_bars)
    balance = 10000.0 * np.exp(np.cumsum(returns))
    equity_df = pd.DataFrame({"balance": balance})
    trades_df = pd.DataFrame({
        "net_pnl": [10.0, -5.0, 8.0],
        "entry_fee": [1.0, 1.0, 1.0],
        "exit_fee": [1.0, 1.0, 1.0],
    })
    return equity_df, trades_df


def test_sharpe_uses_1h_annualization_when_bars_per_year_8760() -> None:
    """Default 1H: Sharpe = mean/std × sqrt(8760)."""
    eq, tr = _synthetic_equity_trades()
    metrics = _compute_metrics(eq, tr, initial_balance=10000.0, bars_per_year=8760)

    returns = eq["balance"].pct_change().dropna()
    expected = float((returns.mean() / returns.std()) * np.sqrt(8760))
    assert abs(metrics["Sharpe Ratio"] - expected) < 1e-9


def test_sharpe_uses_4h_annualization_when_bars_per_year_2190() -> None:
    """4H: Sharpe = mean/std × sqrt(2190). Bug pre-fix used sqrt(8760) → 2x overstated."""
    eq, tr = _synthetic_equity_trades()
    metrics = _compute_metrics(eq, tr, initial_balance=10000.0, bars_per_year=2190)

    returns = eq["balance"].pct_change().dropna()
    expected = float((returns.mean() / returns.std()) * np.sqrt(2190))
    assert abs(metrics["Sharpe Ratio"] - expected) < 1e-9
    # Sanity check: 4H sharpe = 1H sharpe / 2 (since sqrt(8760/2190) = 2)
    metrics_1h = _compute_metrics(eq, tr, initial_balance=10000.0, bars_per_year=8760)
    assert abs(metrics["Sharpe Ratio"] - metrics_1h["Sharpe Ratio"] / 2) < 1e-9


def test_sharpe_uses_15m_annualization_when_bars_per_year_35040() -> None:
    """15M: Sharpe = mean/std × sqrt(35040). Bug pre-fix used sqrt(8760) → 2x understated."""
    eq, tr = _synthetic_equity_trades()
    metrics = _compute_metrics(eq, tr, initial_balance=10000.0, bars_per_year=35040)

    returns = eq["balance"].pct_change().dropna()
    expected = float((returns.mean() / returns.std()) * np.sqrt(35040))
    assert abs(metrics["Sharpe Ratio"] - expected) < 1e-9


def test_sortino_uses_same_annualization_as_sharpe() -> None:
    """Sortino same fix: sqrt(bars_per_year), not hardcoded sqrt(24*365)."""
    eq, tr = _synthetic_equity_trades()
    metrics = _compute_metrics(eq, tr, initial_balance=10000.0, bars_per_year=2190)

    returns = eq["balance"].pct_change().dropna()
    downside = returns[returns < 0]
    if len(downside) > 0 and downside.std() > 0:
        expected_sortino = float((returns.mean() / downside.std()) * np.sqrt(2190))
        assert abs(metrics["Sortino Ratio"] - expected_sortino) < 1e-9


def test_default_bars_per_year_backward_compatible() -> None:
    """When bars_per_year not passed, default = 8760 (1H) preserves old behavior."""
    eq, tr = _synthetic_equity_trades()
    metrics_explicit = _compute_metrics(eq, tr, initial_balance=10000.0, bars_per_year=8760)
    metrics_default = _compute_metrics(eq, tr, initial_balance=10000.0)
    assert abs(metrics_explicit["Sharpe Ratio"] - metrics_default["Sharpe Ratio"]) < 1e-12
