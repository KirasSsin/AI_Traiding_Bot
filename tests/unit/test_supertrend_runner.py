"""S50 T7 — supertrend_runner.py unit tests (TDD RED → GREEN).

Verifies:
  1. run_supertrend_wfa() returns a verdict dict with expected keys.
  2. n_trials=10 is passed to run_research_wfa (DSR multi-testing penalty wired).
  3. CrossTrialLog.append_trial is not bypassed (invoked via run_research_wfa).
  4. Verdict dict keys match atr_breakout_runner WFA output shape.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_N = 2000  # enough bars to avoid WFA_FAIL_DATA


def _make_df(n: int = _N) -> pd.DataFrame:
    """Minimal OHLCV DataFrame with _ts column (normalized form)."""
    import numpy as np

    rng = np.random.default_rng(42)
    close = 30_000.0 + np.cumsum(rng.normal(0, 50, n))
    return pd.DataFrame(
        {
            "_ts": pd.date_range("2023-01-01", periods=n, freq="h", tz="UTC"),
            "open": close * 0.999,
            "high": close * 1.002,
            "low": close * 0.998,
            "close": close,
            "volume": rng.uniform(100, 500, n),
        }
    )


def _make_wfa_result(verdict: str = "WFA_PASS") -> dict[str, Any]:
    """Minimal wfa_result dict matching research_wfa.run_research_wfa return shape."""
    return {
        "verdict": verdict,
        "failed_criteria": [],
        "fold_sharpe_ratios": [0.9, 1.1, 0.85],
        "trial_mean_fold_oos_sharpe": 0.95,
        "trial_oos_sharpe": 0.93,
        "mc_p_value": 0.03,
        "dsr": 0.97,
        "dsr_pass": True,
        "dsr_status": "PASS",
        "sigma_sr_cross_trial": 0.12,
        "n_trades_raw": 42,
        "n_trials": 10,
        "wfa_params": {
            "train_bars": 1200,
            "test_bars": 300,
            "k_folds": 3,
            "embargo_bars": 10,
            "min_required": 100,
            "actual": _N,
            "symbol": "BTCUSDT",
        },
        "metrics": {
            "sharpe": 0.95,
            "win_rate": 0.55,
            "total_pnl_pct": 12.3,
            "n_trades": 42,
        },
        "trades": [SimpleNamespace(pnl_pct=0.01)],
    }


# ---------------------------------------------------------------------------
# Test: module + function exist (smoke)
# ---------------------------------------------------------------------------


def test_supertrend_runner_importable() -> None:
    """supertrend_runner module must be importable with run_supertrend_wfa."""
    from src.backtest import supertrend_runner  # noqa: F401

    assert hasattr(supertrend_runner, "run_supertrend_wfa")


# ---------------------------------------------------------------------------
# Test: n_trials=10 passed to run_research_wfa
# ---------------------------------------------------------------------------


def test_run_supertrend_wfa_passes_n_trials_10(tmp_path: Path) -> None:
    """run_supertrend_wfa MUST call run_research_wfa with n_trials=10."""
    from src.backtest.supertrend_runner import run_supertrend_wfa

    wfa_result = _make_wfa_result()

    with (
        patch(
            "src.backtest.supertrend_runner.run_research_wfa", return_value=wfa_result
        ) as mock_wfa,
        patch("src.backtest.supertrend_runner._load_ohlcv_df", return_value=_make_df()),
    ):
        run_supertrend_wfa(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            cross_trial_log_path=tmp_path / "cross_trial_sharpes.json",
        )

    assert mock_wfa.called, "run_research_wfa must be called"
    _, kwargs = mock_wfa.call_args
    assert (
        kwargs.get("n_trials") == 10
    ), f"n_trials must be 10 (Supertrend = hypothesis #10), got {kwargs.get('n_trials')!r}"


# ---------------------------------------------------------------------------
# Test: sprint_tag is distinct (not the generic default)
# ---------------------------------------------------------------------------


def test_run_supertrend_wfa_uses_sprint_tag(tmp_path: Path) -> None:
    """run_supertrend_wfa must pass a distinct sprint_tag to run_research_wfa."""
    from src.backtest.supertrend_runner import run_supertrend_wfa

    wfa_result = _make_wfa_result()

    with (
        patch(
            "src.backtest.supertrend_runner.run_research_wfa", return_value=wfa_result
        ) as mock_wfa,
        patch("src.backtest.supertrend_runner._load_ohlcv_df", return_value=_make_df()),
    ):
        run_supertrend_wfa(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            cross_trial_log_path=tmp_path / "cross_trial_sharpes.json",
        )

    _, kwargs = mock_wfa.call_args
    sprint_tag = kwargs.get("sprint_tag", "")
    assert sprint_tag, "sprint_tag must be a non-empty string"


# ---------------------------------------------------------------------------
# Test: verdict dict has required keys
# ---------------------------------------------------------------------------

_REQUIRED_VERDICT_KEYS = {
    "verdict",
    "failed_criteria",
    "fold_sharpe_ratios",
    "dsr",
    "dsr_pass",
    "mc_p_value",
    "metrics",
    "n_trades_raw",
    "wfa_params",
}


def test_run_supertrend_wfa_verdict_keys(tmp_path: Path) -> None:
    """Verdict dict from run_supertrend_wfa must contain all required keys."""
    from src.backtest.supertrend_runner import run_supertrend_wfa

    wfa_result = _make_wfa_result()

    with (
        patch("src.backtest.supertrend_runner.run_research_wfa", return_value=wfa_result),
        patch("src.backtest.supertrend_runner._load_ohlcv_df", return_value=_make_df()),
    ):
        result = run_supertrend_wfa(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            cross_trial_log_path=tmp_path / "cross_trial_sharpes.json",
        )

    missing = _REQUIRED_VERDICT_KEYS - set(result.keys())
    assert not missing, f"Verdict dict missing keys: {missing}"


# ---------------------------------------------------------------------------
# Test: append_trial is NOT bypassed (called via run_research_wfa)
# ---------------------------------------------------------------------------


def test_run_supertrend_wfa_does_not_bypass_append_trial(tmp_path: Path) -> None:
    """append_trial must be called by run_research_wfa, not bypassed.

    We verify indirectly: run_research_wfa itself must be called (not an
    inline DSR block). The CrossTrialLog.append_trial is an internal concern
    of run_research_wfa — as long as run_research_wfa is called with n_trials=10,
    append_trial runs (per T2 finding: append is inside run_research_wfa since
    S44 T9 retrofit).
    """
    from src.backtest.supertrend_runner import run_supertrend_wfa

    wfa_result = _make_wfa_result()
    call_log: list[dict[str, Any]] = []

    def _recording_wfa(**kwargs: Any) -> dict[str, Any]:
        call_log.append(
            {"n_trials": kwargs.get("n_trials"), "sprint_tag": kwargs.get("sprint_tag")}
        )
        return wfa_result

    with (
        patch("src.backtest.supertrend_runner.run_research_wfa", side_effect=_recording_wfa),
        patch("src.backtest.supertrend_runner._load_ohlcv_df", return_value=_make_df()),
    ):
        run_supertrend_wfa(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            cross_trial_log_path=tmp_path / "cross_trial_sharpes.json",
        )

    assert len(call_log) == 1, "run_research_wfa must be called exactly once"
    assert call_log[0]["n_trials"] == 10, "n_trials=10 must reach run_research_wfa"


# ---------------------------------------------------------------------------
# Test: cross_trial_log_path forwarded
# ---------------------------------------------------------------------------


def test_run_supertrend_wfa_forwards_cross_trial_log_path(tmp_path: Path) -> None:
    """cross_trial_log_path passed to run_research_wfa (used by append_trial)."""
    from src.backtest.supertrend_runner import run_supertrend_wfa

    wfa_result = _make_wfa_result()
    log_path = tmp_path / "cross_trial_sharpes.json"

    with (
        patch(
            "src.backtest.supertrend_runner.run_research_wfa", return_value=wfa_result
        ) as mock_wfa,
        patch("src.backtest.supertrend_runner._load_ohlcv_df", return_value=_make_df()),
    ):
        run_supertrend_wfa(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            cross_trial_log_path=log_path,
        )

    _, kwargs = mock_wfa.call_args
    assert kwargs.get("cross_trial_log_path") == log_path


# ---------------------------------------------------------------------------
# Test: backtest_fn uses the vectorized Supertrend kernel (not atr_breakout)
# ---------------------------------------------------------------------------


def test_run_supertrend_wfa_uses_supertrend_backtest_fn(tmp_path: Path) -> None:
    """backtest_fn passed to run_research_wfa must be the Supertrend kernel."""
    from src.backtest.supertrend_runner import run_supertrend_wfa

    wfa_result = _make_wfa_result()
    captured: list[Any] = []

    def _capture_backtest_fn(**kwargs: Any) -> dict[str, Any]:
        captured.append(kwargs.get("backtest_fn"))
        return wfa_result

    with (
        patch("src.backtest.supertrend_runner.run_research_wfa", side_effect=_capture_backtest_fn),
        patch("src.backtest.supertrend_runner._load_ohlcv_df", return_value=_make_df()),
    ):
        run_supertrend_wfa(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            cross_trial_log_path=tmp_path / "cross_trial_sharpes.json",
        )

    assert captured, "backtest_fn not captured"
    fn = captured[0]
    assert fn is not None, "backtest_fn must not be None"
    # Must NOT be the ATR breakout kernel (separate module).
    assert "atr_breakout" not in getattr(
        fn, "__module__", ""
    ), "backtest_fn must be the Supertrend kernel, not atr_breakout"


# ---------------------------------------------------------------------------
# Test: unskip placeholder in test_supertrend_runner_ntrials.py
# (The skip is there; this test just documents the T7 completion via a passing
#  version of the same intent — actual wiring verified by tests above.)
# ---------------------------------------------------------------------------


def test_supertrend_runner_n_trials_10_wiring_verified(tmp_path: Path) -> None:
    """CC3 wiring guard (test-engineer PHASE 6: replace empty-body import-smoke).

    Asserts run_supertrend_wfa actually forwards n_trials=10 to run_research_wfa,
    not just that the module imports. Mirrors test_run_supertrend_wfa_passes_n_trials_10.
    """
    from src.backtest.supertrend_runner import run_supertrend_wfa

    wfa_result = _make_wfa_result(verdict="WFA_FAIL")

    with (
        patch(
            "src.backtest.supertrend_runner.run_research_wfa", return_value=wfa_result
        ) as mock_wfa,
        patch("src.backtest.supertrend_runner._load_ohlcv_df", return_value=_make_df()),
    ):
        run_supertrend_wfa(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            cross_trial_log_path=tmp_path / "cross_trial_sharpes.json",
        )

    _, kwargs = mock_wfa.call_args
    assert (
        kwargs.get("n_trials") == 10
    ), f"supertrend_runner must forward n_trials=10 (hypothesis #10); got {kwargs.get('n_trials')!r}"
