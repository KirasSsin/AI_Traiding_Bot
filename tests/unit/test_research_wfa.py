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


def test_get_wfa_tier_params_low_freq_4h() -> None:
    """S45 — 4H interval returns low-freq tier params."""
    from src.backtest.research_wfa import get_wfa_tier_params

    p = get_wfa_tier_params("240")
    assert p["train_bars"] == 1500
    assert p["test_bars"] == 250
    assert p["k_folds"] == 5
    assert p["embargo_bars"] == 20


def test_get_wfa_tier_params_low_freq_d() -> None:
    """S45 — D interval returns low-freq tier params."""
    from src.backtest.research_wfa import get_wfa_tier_params

    p = get_wfa_tier_params("D")
    assert p["test_bars"] == 250


def test_get_wfa_tier_params_high_freq_15m() -> None:
    """S45 — 15M returns high-freq default tier."""
    from src.backtest.research_wfa import get_wfa_tier_params

    p = get_wfa_tier_params("15")
    assert p["train_bars"] == 2000
    assert p["test_bars"] == 500


def test_get_wfa_tier_params_high_freq_1h() -> None:
    """S45 — 1H returns high-freq default tier."""
    from src.backtest.research_wfa import get_wfa_tier_params

    p = get_wfa_tier_params("60")
    assert p["test_bars"] == 500


# ---------------------------------------------------------------------------
# S51 D5 — two-level pool scoping (strategy_class threading + fallback status)
# ---------------------------------------------------------------------------

_AB_PARAMS = {
    "atr_period": 9,
    "atr_breakout_mult": 2.5,
    "atr_stop_period": 21,
    "atr_stop_mult": 1.5,
}


def _run_d5(
    tmp_path,
    *,
    strategy_class: str,
    n_trials: int,
    log_name: str = "cross_trial.json",
) -> dict[str, Any]:
    """Run the shared harness with the deterministic fake backtest (5000 bars)."""
    return run_research_wfa(
        df=_fake_df(5000),
        params=_AB_PARAMS,
        backtest_fn=_fake_backtest_fn,
        bars_per_year=8766,
        symbol="BTCUSDT",
        train_bars=2000,
        test_bars=500,
        k_folds=5,
        embargo_bars=20,
        n_trials=n_trials,
        cross_trial_log_path=tmp_path / log_name,
        sprint_tag="S51",
        strategy_class=strategy_class,
    )


def test_d5_default_strategy_class_is_unknown() -> None:
    """S51 D5 — default strategy_class='unknown' (legacy callers, fail-safe)."""
    import inspect

    sig = inspect.signature(run_research_wfa)
    assert sig.parameters["strategy_class"].default == "unknown"


def test_d5_strategy_class_threaded_to_log(tmp_path) -> None:
    """S51 D5 — run_research_wfa tags the appended entry with strategy_class."""
    from src.analytics.cross_trial_log import CrossTrialLog

    log_path = tmp_path / "cross_trial.json"
    _run_d5(tmp_path, strategy_class="supertrend", n_trials=10)
    log = CrossTrialLog(path=log_path)
    entries = log.get_entries()
    assert entries, "trial should have been appended"
    assert all(e["strategy_class"] == "supertrend" for e in entries)


def test_d5_single_trial_status_when_n_trials_1(tmp_path) -> None:
    """S51 D5 — n_trials=1 caller (volume_breakout) → SINGLE_TRIAL, no penalty."""
    result = _run_d5(tmp_path, strategy_class="volume_breakout", n_trials=1)
    assert result["sigma_scope_status"] == "SINGLE_TRIAL"


def test_d5_insufficient_class_history_no_crash(tmp_path) -> None:
    """S51 D5 verdict (e) — global N>1 but <3 within-class entries → no crash.

    Pre-seed the pool with 9 wild atr_breakout entries (incl. −89). A supertrend
    run with n_trials=10 must NOT raise (pre-D5: NaN sigma + n_trials>1 raised
    ValueError) and must NOT be poisoned. Within-class supertrend count after
    append = 1 (<3) → INSUFFICIENT_CLASS_HISTORY, DSR computed honestly.
    """
    from src.analytics.cross_trial_log import CrossTrialLog

    log_path = tmp_path / "cross_trial.json"
    seed = CrossTrialLog(path=log_path)
    for i in range(9):
        seed.append_trial(
            sprint=44,
            symbol=f"X_{i}",
            strategy_class="atr_breakout",
            oos_sharpe=-89.0 + i,
        )
    result = _run_d5(tmp_path, strategy_class="supertrend", n_trials=10)
    assert result["sigma_scope_status"] == "INSUFFICIENT_CLASS_HISTORY"
    # global breadth still reported for transparency / anti-snooping
    assert result["n_trials"] == 10


def test_d5_class_scoped_ignores_cross_family_contamination(tmp_path) -> None:
    """S51 D5 — >=3 within-class entries → CLASS_SCOPED; sigma_SR NOT poisoned.

    Pre-seed 2 tight supertrend entries + 1 wild atr_breakout (−89). The run adds
    the 3rd supertrend entry → within-class sigma over the supertrend subset only
    (finite, small), NOT contaminated by the −89 atr_breakout entry.
    """
    import math

    from src.analytics.cross_trial_log import CrossTrialLog

    log_path = tmp_path / "cross_trial.json"
    seed = CrossTrialLog(path=log_path)
    seed.append_trial(sprint=49, symbol="BTC_a", strategy_class="supertrend", oos_sharpe=1.0)
    seed.append_trial(sprint=49, symbol="BTC_b", strategy_class="supertrend", oos_sharpe=2.0)
    seed.append_trial(sprint=44, symbol="ETH_wild", strategy_class="atr_breakout", oos_sharpe=-89.0)
    result = _run_d5(tmp_path, strategy_class="supertrend", n_trials=10)
    assert result["sigma_scope_status"] == "CLASS_SCOPED"
    sigma = result["sigma_sr_cross_trial"]
    assert sigma is not None and not math.isnan(sigma)
    # within-class sigma over [1.0, 2.0, trial_mean] — bounded, NOT ~the −89 spread
    assert sigma < 50.0


def test_d5_within_class_sigma_uncontaminated_vs_global(tmp_path) -> None:
    """S51 D5 — the appended-pool within-class sigma differs from the global sigma
    when other classes are present (proves scoping actually filters)."""
    from src.analytics.cross_trial_log import CrossTrialLog

    log_path = tmp_path / "cross_trial.json"
    seed = CrossTrialLog(path=log_path)
    seed.append_trial(sprint=49, symbol="BTC_a", strategy_class="supertrend", oos_sharpe=1.0)
    seed.append_trial(sprint=49, symbol="BTC_b", strategy_class="supertrend", oos_sharpe=2.0)
    seed.append_trial(sprint=44, symbol="ETH_wild", strategy_class="atr_breakout", oos_sharpe=-89.0)
    _run_d5(tmp_path, strategy_class="supertrend", n_trials=10)
    log = CrossTrialLog(path=log_path)
    class_sigma = log.sigma_sr(strategy_class="supertrend")
    global_sigma = log.sigma_sr()
    assert class_sigma is not None and global_sigma is not None
    # global pool includes the −89 contaminant → much larger spread than class-only
    assert global_sigma > class_sigma * 5
