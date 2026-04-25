"""Tests for WalkForwardRunner — orchestrator с dual-Sharpe routing.

Sprint 10 Q4 (per pre-s10-backlog.md verdict + cross-cutting concern #1).
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
from src.backtest.walk_forward import WalkForwardRunner, WindowSplitter


def _synthetic_df(n_bars: int = 5000) -> pd.DataFrame:
    """Synthetic 1H OHLCV — enough bars для 5-fold K=5 (need >= 4520)."""
    rng = np.random.default_rng(42)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.01, n_bars)))
    timestamps = pd.date_range("2024-01-01", periods=n_bars, freq="1h")
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": closes * 0.999,
        "high": closes * 1.001,
        "low": closes * 0.998,
        "close": closes,
        "volume": np.ones(n_bars),
    })


def test_runner_invokes_replay_per_fold() -> None:
    """Per ADR 0014 K=5: runner calls run_replay 10 times (IS + OOS per fold = 2 × K)."""
    df = _synthetic_df(n_bars=5000)
    splitter = WindowSplitter()
    config: dict[str, Any] = {"trading": {"initial_balance": 10000.0, "long_only": True}}

    mock_replay = MagicMock(return_value={
        "equity_df": pd.DataFrame({"timestamp": [pd.Timestamp("2024-01-01")], "balance": [10100.0]}),
        "trades_df": pd.DataFrame({"net_pnl": [100.0], "timestamp_open": [pd.Timestamp("2024-01-01")]}),
        "metrics": {"Sharpe Ratio": 1.2, "Total Return (%)": 1.0},
    })

    runner = WalkForwardRunner(splitter=splitter, replay_fn=mock_replay)
    runner.run(df=df, config=config)

    assert mock_replay.call_count == 10  # 5 folds × 2 replays (IS + OOS)


def test_runner_collects_per_fold_results() -> None:
    """Result dict has 'folds' list с per-fold metrics + trades."""
    df = _synthetic_df(n_bars=5000)
    splitter = WindowSplitter()
    config: dict[str, Any] = {"trading": {"initial_balance": 10000.0}}

    mock_replay = MagicMock(return_value={
        "equity_df": pd.DataFrame({"timestamp": [pd.Timestamp("2024-01-01")], "balance": [10100.0]}),
        "trades_df": pd.DataFrame({"net_pnl": [100.0]}),
        "metrics": {"Sharpe Ratio": 1.2},
    })

    runner = WalkForwardRunner(splitter=splitter, replay_fn=mock_replay)
    result = runner.run(df=df, config=config)

    assert "folds" in result
    assert len(result["folds"]) == 5
    for fold in result["folds"]:
        assert "fold_idx" in fold
        assert "train_window" in fold
        assert "test_window" in fold
        assert "is_metrics" in fold
        assert "oos_metrics" in fold
        assert "oos_trades_df" in fold
        assert "oos_is_sharpe_ratio" in fold


def test_runner_aggregates_oos_trades() -> None:
    """Aggregate OOS trades = K folds × oos trades concatenated."""
    df = _synthetic_df(n_bars=5000)
    splitter = WindowSplitter()
    config: dict[str, Any] = {"trading": {"initial_balance": 10000.0}}

    mock_replay = MagicMock(return_value={
        "equity_df": pd.DataFrame({"balance": [10100.0]}),
        "trades_df": pd.DataFrame({"net_pnl": [50.0]}),
        "metrics": {"Sharpe Ratio": 1.0},
    })

    runner = WalkForwardRunner(splitter=splitter, replay_fn=mock_replay)
    result = runner.run(df=df, config=config)

    aggregate = result["aggregate"]
    assert "oos_trades_df" in aggregate
    assert len(aggregate["oos_trades_df"]) == 5  # 5 folds × 1 trade each
    assert aggregate["k_folds"] == 5
    assert "fold_oos_sharpes" in aggregate
    assert len(aggregate["fold_oos_sharpes"]) == 5


def test_runner_oos_is_sharpe_ratio_computed_per_fold() -> None:
    """Each fold's oos_is_sharpe_ratio = oos_sharpe / is_sharpe."""
    df = _synthetic_df(n_bars=5000)
    splitter = WindowSplitter()
    config: dict[str, Any] = {"trading": {"initial_balance": 10000.0}}

    # IS sharpe = 1.5, OOS sharpe = 1.2 → ratio = 0.8
    mock_replay = MagicMock(return_value={
        "equity_df": pd.DataFrame({"balance": [10100.0]}),
        "trades_df": pd.DataFrame({"net_pnl": [50.0]}),
        "metrics": {"Sharpe Ratio": 1.5},
    })

    runner = WalkForwardRunner(splitter=splitter, replay_fn=mock_replay)
    result = runner.run(df=df, config=config)

    for fold in result["folds"]:
        # IS == OOS in mock → ratio = 1.0
        assert fold["oos_is_sharpe_ratio"] == 1.0


def test_insufficient_data_raises() -> None:
    """If df shorter than min required, raise."""
    df = _synthetic_df(n_bars=1000)
    splitter = WindowSplitter()
    config: dict[str, Any] = {}

    runner = WalkForwardRunner(splitter=splitter, replay_fn=MagicMock())
    with pytest.raises(ValueError, match="insufficient data"):
        runner.run(df=df, config=config)
