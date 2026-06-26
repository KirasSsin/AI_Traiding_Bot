"""S55 QS-3 (ADR 0071 follow-up) — donchian_runner DSR units fix.

`_run_donchian_wfa` reads sigma_SR from the class-scoped cross-trial pool
(`trial_log.sigma_sr(strategy_class="donchian")`). Those stored OOS Sharpes are
ANNUALIZED bar-returns Sharpes (replay_engine × sqrt(bars_per_year)), but
`compute_dsr`'s internal candidate Sharpe is per-trade (un-annualized). Bailey &
López de Prado 2014 eq.12/13 require SR, SR* and sigma_SR at ONE frequency.

Defect: the CLASS_SCOPED call (`compute_dsr_with_status` line 204) passed NO
`annualization_factor` → sigma_SR ~sqrt(bars_per_year) too large → sharpe_star
inflated → DSR depressed → potential FALSE NEGATIVE on the donchian money/gate.

This mirrors the S55 QS-1 fix for research_wfa/wfa_reporter and QS-2 (ADR 0071)
for _cmd_wfa. donchian_runner was the last un-fixed call site.

RED before fix: captured kwargs lack `annualization_factor` (None).
GREEN after fix: `annualization_factor == sqrt(bars_per_year)` (wfa_reporter
parity — donchian fold Sharpes share replay_engine bar-returns provenance).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _seed_donchian_pool(data_dir: Path) -> None:
    """Write >=3 within-class 'donchian' entries → admissible sigma_SR (ADR 0056 N>=3)."""
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "cross_trial_sharpes.json").write_text(
        json.dumps(
            {
                "trials": [
                    {
                        "sprint": 35,
                        "symbol": "BTCUSDT_20_10",
                        "strategy_class": "donchian",
                        "oos_sharpe": -44.0,
                    },
                    {
                        "sprint": 36,
                        "symbol": "BTCUSDT_20_10",
                        "strategy_class": "donchian",
                        "oos_sharpe": 0.4,
                    },
                    {
                        "sprint": 37,
                        "symbol": "BTCUSDT_20_10",
                        "strategy_class": "donchian",
                        "oos_sharpe": -10.0,
                    },
                ]
            }
        )
    )


def test_donchian_dsr_class_scoped_call_passes_annualization_factor(tmp_path, monkeypatch):
    """CLASS_SCOPED branch must de-annualize sigma_SR via annualization_factor=sqrt(bars_per_year).

    RED: line 204 calls compute_dsr_with_status WITHOUT annualization_factor.
    """
    from src.backtest import donchian_runner as dr

    monkeypatch.chdir(tmp_path)
    _seed_donchian_pool(tmp_path / "data")

    bars_per_year = 2190  # arbitrary 4h fixture value (test passes it explicitly; CLI default is 2191 per S55 QS-2)

    captured: dict = {}

    def _capture(**kwargs):
        captured.update(kwargs)
        return {"dsr": 0.99, "status": "GATE_ELIGIBLE", "n_trades": 100}

    # Non-empty OHLCV; mock runner returns one fold (→ finite trial_mean_fold_oos_sharpe).
    mock_df = MagicMock()
    mock_df.empty = False

    empty_oos = MagicMock()
    empty_oos.empty = True  # → mc_p = 1.0, skips numpy sign-flip path

    mock_runner = MagicMock()
    mock_runner.run.return_value = {
        "folds": [{"oos_is_sharpe_ratio": 0.8, "oos_trades_df": None}],
        "aggregate": {"oos_trades_df": empty_oos},
    }

    with (
        patch("src.backtest.donchian_runner.load_market_data", return_value=mock_df),
        patch("src.backtest.donchian_runner.WindowSplitter"),
        patch("src.backtest.donchian_runner.WalkForwardRunner", return_value=mock_runner),
        patch("src.backtest.donchian_runner.run_replay"),
        patch("src.backtest.donchian_runner.sign_flip_p_value", return_value=1.0),
        patch("src.backtest.donchian_runner.compute_t1_t6_metrics", return_value={}),
        patch(
            "src.backtest.donchian_runner.evaluate_acceptance_gate",
            return_value={"failed_criteria": []},
        ),
        patch(
            "src.backtest.donchian_runner.compute_dsr_with_status",
            side_effect=_capture,
        ),
    ):
        dr._run_donchian_wfa(
            parquet_path=Path("data/BTCUSDT_4h.parquet"),
            symbol="BTCUSDT",
            start="2023-01-01",
            end="2026-04-26",
            interval_label="4h",
            bars_per_year=bars_per_year,
            train_bars=1000,
            test_bars=250,
            k_folds=5,
            embargo_bars=20,
        )

    # CLASS_SCOPED branch fired (finite class sigma → n_trials=5 global breadth).
    assert captured.get("n_trials") == 5
    assert captured.get("sigma_sr") is not None
    # Units fix: de-annualization factor present and == sqrt(bars_per_year).
    assert captured.get("annualization_factor") == pytest.approx(math.sqrt(bars_per_year))
