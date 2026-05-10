"""S44 T1 — research WFA helper tests."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from src.backtest.atr_breakout_runner import _TradeRecord
from src.backtest.research_wfa import run_research_wfa


def _fake_backtest_fn(
    df: pd.DataFrame, _params: dict[str, Any], _bars_per_year: int
) -> dict[str, Any]:
    """Mock backtest. Returns trades with deterministic per-trade pnl_pct."""
    n_trades = len(df) // 100
    if n_trades == 0:
        return {
            "n_trades": 0,
            "sharpe": float("nan"),
            "total_pnl_pct": 0.0,
            "win_rate": float("nan"),
            "trades": [],
        }
    pnls = [0.01 if i % 5 < 3 else -0.005 for i in range(n_trades)]
    trades = [
        _TradeRecord(
            entry_idx=i * 100,
            exit_idx=i * 100 + 50,
            entry_price=100.0,
            exit_price=100.0 + p * 100,
            pnl_pct=p,
        )
        for i, p in enumerate(pnls)
    ]
    return {
        "n_trades": n_trades,
        "sharpe": 1.5,
        "total_pnl_pct": sum(pnls) * 100,
        "win_rate": 0.6,
        "trades": trades,
    }


def _fake_df(n_bars: int) -> pd.DataFrame:
    ts = pd.date_range(start="2023-01-01", periods=n_bars, freq="1h", tz="UTC")
    return pd.DataFrame(
        {
            "_ts": ts,
            "open": np.linspace(100, 200, n_bars),
            "high": np.linspace(101, 201, n_bars),
            "low": np.linspace(99, 199, n_bars),
            "close": np.linspace(100, 200, n_bars),
            "volume": np.full(n_bars, 1000.0),
        }
    )


def test_run_research_wfa_returns_required_keys(tmp_path) -> None:
    df = _fake_df(5000)
    result = run_research_wfa(
        df=df,
        params={
            "atr_period": 9,
            "atr_breakout_mult": 2.5,
            "atr_stop_period": 21,
            "atr_stop_mult": 1.5,
        },
        backtest_fn=_fake_backtest_fn,
        bars_per_year=8766,
        symbol="BTCUSDT",
        train_bars=2000,
        test_bars=500,
        k_folds=5,
        embargo_bars=20,
        cross_trial_log_path=tmp_path / "cross_trial.json",
    )
    for key in (
        "verdict",
        "fold_sharpe_ratios",
        "trial_mean_fold_oos_sharpe",
        "mc_p_value",
        "dsr",
        "dsr_pass",
        "n_trades_raw",
        "failed_criteria",
        "wfa_params",
        "metrics",
        "trades",
        "trial_oos_sharpe",
    ):
        assert key in result, f"Missing key: {key}"


def test_run_research_wfa_data_limited_returns_wfa_fail_data(tmp_path) -> None:
    """If df too small for default params → verdict=WFA_FAIL_DATA, no throw."""
    df = _fake_df(1000)  # < 4520 min_required
    result = run_research_wfa(
        df=df,
        params={
            "atr_period": 9,
            "atr_breakout_mult": 2.5,
            "atr_stop_period": 21,
            "atr_stop_mult": 1.5,
        },
        backtest_fn=_fake_backtest_fn,
        bars_per_year=8766,
        symbol="BTCUSDT",
        train_bars=2000,
        test_bars=500,
        k_folds=5,
        embargo_bars=20,
        cross_trial_log_path=tmp_path / "cross_trial.json",
    )
    assert result["verdict"] == "WFA_FAIL_DATA"
    assert "data_volume" in result["failed_criteria"]


def test_run_research_wfa_fold_count_matches_k_folds(tmp_path) -> None:
    df = _fake_df(5000)
    result = run_research_wfa(
        df=df,
        params={
            "atr_period": 9,
            "atr_breakout_mult": 2.5,
            "atr_stop_period": 21,
            "atr_stop_mult": 1.5,
        },
        backtest_fn=_fake_backtest_fn,
        bars_per_year=8766,
        symbol="BTCUSDT",
        train_bars=2000,
        test_bars=500,
        k_folds=5,
        embargo_bars=20,
        cross_trial_log_path=tmp_path / "cross_trial.json",
    )
    assert len(result["fold_sharpe_ratios"]) == 5


def test_run_research_wfa_aggregated_trades_preserve_pnls(tmp_path) -> None:
    df = _fake_df(5000)
    result = run_research_wfa(
        df=df,
        params={
            "atr_period": 9,
            "atr_breakout_mult": 2.5,
            "atr_stop_period": 21,
            "atr_stop_mult": 1.5,
        },
        backtest_fn=_fake_backtest_fn,
        bars_per_year=8766,
        symbol="BTCUSDT",
        train_bars=2000,
        test_bars=500,
        k_folds=5,
        embargo_bars=20,
        cross_trial_log_path=tmp_path / "cross_trial.json",
    )
    # 5 folds × 500 test_bars = 2500 OOS bars / 100 bars per trade = 25 trades total
    assert result["n_trades_raw"] >= 20  # tolerance for fold boundaries


def test_run_research_wfa_default_n_trials_is_1() -> None:
    """S45 C1 — default n_trials=1 (fail-safe). Multi-hypothesis callers must explicit."""
    import inspect

    from src.backtest.research_wfa import run_research_wfa

    sig = inspect.signature(run_research_wfa)
    assert (
        sig.parameters["n_trials"].default == 1
    ), f"Default n_trials must be 1 (fail-safe), got {sig.parameters['n_trials'].default}"
