"""S42 T1 — research runner envelope contract tests."""

from __future__ import annotations

from src.backtest.research_runner_envelope import build_research_runner_envelope


def test_envelope_contains_all_dashboard_required_keys() -> None:
    """Dashboard JS reads bars_per_year, failed_criteria, verdict, warnings, etc.
    Envelope MUST provide all to prevent toLocaleString-style crashes.
    """
    payload = build_research_runner_envelope(
        runner_name="atr_breakout_runner",
        symbol="BTCUSDT",
        interval="240",
        n_trades=69,
        sharpe=1.11,
        win_rate=0.46,
        total_pnl_pct=819.81,
        bars_per_year=2191,
        equity_curve=[0.0, 100.0, 200.0, 300.0, 400.0, 819.81],
        runner_label="ATR breakout (LOCKED)",
    )
    for key in (
        "bars_per_year",
        "warnings",
        "failed_criteria",
        "verdict",
        "acceptance_gate",
        "dsr",
        "dsr_pass",
        "mc_p_value",
        "metrics",
        "trade_stats",
        "wfa_params",
        "wfa_total_bars",
        "fold_sharpe_ratios",
        "failed_folds",
        "trades_dump",
    ):
        assert key in payload, f"Missing required dashboard key: {key}"


def test_envelope_warnings_includes_raw_full_period_high() -> None:
    """Honest disclosure — operator sees high warning that acceptance gate skipped."""
    payload = build_research_runner_envelope(
        runner_name="atr_breakout_runner",
        symbol="BTCUSDT",
        interval="240",
        n_trades=10,
        sharpe=1.0,
        win_rate=0.5,
        total_pnl_pct=100.0,
        bars_per_year=2191,
        equity_curve=[0.0, 50.0, 100.0],
        runner_label="x",
    )
    high = [
        w for w in payload["warnings"] if w["level"] == "high" and w["code"] == "raw_full_period"
    ]
    assert len(high) == 1
    assert "WFA retrofit pending S43" in high[0]["message"]


def test_envelope_subperiod_robustness_5_of_5_emits_ok_chip() -> None:
    """5/5 sub-period positives = info-level chip in warnings array."""
    payload = build_research_runner_envelope(
        runner_name="x",
        symbol="BTCUSDT",
        interval="240",
        n_trades=10,
        sharpe=1.0,
        win_rate=0.5,
        total_pnl_pct=500.0,
        bars_per_year=2191,
        equity_curve=[0.0, 100.0, 200.0, 300.0, 400.0, 500.0],
        runner_label="x",
    )
    chips = [w for w in payload["warnings"] if w["code"] == "subperiod_robustness"]
    assert len(chips) == 1
    assert chips[0]["level"] == "info"
    assert "5/5" in chips[0]["message"]


def test_envelope_subperiod_robustness_3_of_5_emits_warn_chip() -> None:
    """3/5 sub-period positives = warn-level chip."""
    payload = build_research_runner_envelope(
        runner_name="x",
        symbol="BTCUSDT",
        interval="240",
        n_trades=10,
        sharpe=1.0,
        win_rate=0.5,
        total_pnl_pct=75.0,
        bars_per_year=2191,
        # deltas chunked: [+50, -20, +40, -10, +15] = 3/5 positive
        equity_curve=[0.0, 50.0, 30.0, 70.0, 60.0, 75.0],
        runner_label="x",
    )
    chips = [w for w in payload["warnings"] if w["code"] == "subperiod_robustness"]
    assert chips[0]["level"] == "warn"
    assert "3/5" in chips[0]["message"]


def test_envelope_request_dict_carries_label_symbol_interval() -> None:
    """request dict mirrors dashboard payload echo."""
    payload = build_research_runner_envelope(
        runner_name="x",
        symbol="ETHUSDT",
        interval="60",
        n_trades=109,
        sharpe=1.5,
        win_rate=0.4,
        total_pnl_pct=181.74,
        bars_per_year=8766,
        equity_curve=[0.0, 100.0, 181.74],
        runner_label="ATR breakout 1H ETHUSDT",
        start="2023-01-01",
        end="2026-04-26",
    )
    assert payload["request"]["symbol"] == "ETHUSDT"
    assert payload["request"]["interval"] == "60"
    assert payload["request"]["start"] == "2023-01-01"
    assert payload["request"]["end"] == "2026-04-26"
    assert payload["request"]["strategy_label"] == "ATR breakout 1H ETHUSDT"


def test_envelope_failed_criteria_is_empty_list_not_none() -> None:
    """JS does r.failed_criteria.length — must be array, not null."""
    payload = build_research_runner_envelope(
        runner_name="x",
        symbol="BTCUSDT",
        interval="240",
        n_trades=10,
        sharpe=1.0,
        win_rate=0.5,
        total_pnl_pct=100.0,
        bars_per_year=2191,
        equity_curve=[0.0, 100.0],
        runner_label="x",
    )
    assert payload["failed_criteria"] == []
    assert payload["fold_sharpe_ratios"] == []
    assert payload["trades_dump"] == []


def test_envelope_equity_curve_parallel_arrays_format() -> None:
    """S43 T3 — envelope returns equity_curve как parallel arrays для uPlot native API.
    Format: {timestamps: [unix_int...], equity_pct: [float...]}.
    Both arrays MUST be same length.
    """
    payload = build_research_runner_envelope(
        runner_name="atr_breakout_runner",
        symbol="BTCUSDT",
        interval="240",
        n_trades=3,
        sharpe=1.0,
        win_rate=0.5,
        total_pnl_pct=15.0,
        bars_per_year=2191,
        equity_curve=[0.0, 5.0, 10.0, 15.0],
        equity_timestamps=[1672531200, 1672617600, 1672704000, 1672790400],
        runner_label="x",
    )
    ec = payload["equity_curve"]
    assert isinstance(ec, dict)
    assert "timestamps" in ec
    assert "equity_pct" in ec
    assert ec["timestamps"] == [1672531200, 1672617600, 1672704000, 1672790400]
    assert ec["equity_pct"] == [0.0, 5.0, 10.0, 15.0]
    assert all(isinstance(t, int) for t in ec["timestamps"])
    assert all(isinstance(v, float) for v in ec["equity_pct"])


def test_envelope_equity_curve_empty_when_no_trades() -> None:
    """Zero trades → empty arrays (not None) — frontend safely calls .length."""
    payload = build_research_runner_envelope(
        runner_name="x",
        symbol="BTCUSDT",
        interval="240",
        n_trades=0,
        sharpe=0.0,
        win_rate=0.0,
        total_pnl_pct=0.0,
        bars_per_year=2191,
        equity_curve=[],
        equity_timestamps=[],
        runner_label="x",
    )
    assert payload["equity_curve"] == {"timestamps": [], "equity_pct": []}


def test_envelope_equity_timestamps_optional_keyword() -> None:
    """equity_timestamps default = empty list (backward-compat для callers еще не updated)."""
    payload = build_research_runner_envelope(
        runner_name="x",
        symbol="BTCUSDT",
        interval="240",
        n_trades=2,
        sharpe=1.0,
        win_rate=0.5,
        total_pnl_pct=10.0,
        bars_per_year=2191,
        equity_curve=[0.0, 5.0, 10.0],
        runner_label="x",
        # equity_timestamps not passed
    )
    assert payload["equity_curve"]["equity_pct"] == [0.0, 5.0, 10.0]
    assert payload["equity_curve"]["timestamps"] == []


def test_envelope_with_wfa_result_populates_fields() -> None:
    """S44 T4 — when wfa_result passed, envelope uses WFA values, not null sentinels."""
    wfa = {
        "verdict": "WFA_PASS",
        "failed_criteria": [],
        "fold_sharpe_ratios": [1.2, 1.5, 0.9, 1.1, 1.4],
        "trial_mean_fold_oos_sharpe": 1.22,
        "mc_p_value": 0.02,
        "dsr": 0.97,
        "dsr_pass": True,
        "n_trades_raw": 80,
        "wfa_params": {
            "train_bars": 2000,
            "test_bars": 500,
            "k_folds": 5,
            "embargo_bars": 20,
            "min_required": 4520,
            "actual": 5000,
        },
        "metrics": {"t1_sharpe_oos": 1.22, "t5_n_trades": 80},
        "trades": [],
    }
    payload = build_research_runner_envelope(
        runner_name="x",
        symbol="BTCUSDT",
        interval="240",
        n_trades=80,
        sharpe=1.22,
        win_rate=0.55,
        total_pnl_pct=200.0,
        bars_per_year=2191,
        equity_curve=[0.0, 200.0],
        runner_label="x",
        wfa_result=wfa,
    )
    assert payload["verdict"] == "WFA_PASS"
    assert payload["dsr"] == 0.97
    assert payload["dsr_pass"] is True
    assert payload["mc_p_value"] == 0.02
    assert payload["fold_sharpe_ratios"] == [1.2, 1.5, 0.9, 1.1, 1.4]
    assert payload["wfa_params"]["k_folds"] == 5
    assert payload["wfa_total_bars"] == 5000
    assert payload["acceptance_gate"] == "WFA_PASS"
    assert payload["failed_criteria"] == []


def test_envelope_without_wfa_result_returns_raw_sentinels() -> None:
    """Backward compat: when wfa_result=None, envelope returns RAW sentinels (S42 behavior)."""
    payload = build_research_runner_envelope(
        runner_name="x",
        symbol="BTCUSDT",
        interval="240",
        n_trades=10,
        sharpe=1.0,
        win_rate=0.5,
        total_pnl_pct=100.0,
        bars_per_year=2191,
        equity_curve=[0.0, 100.0],
        runner_label="x",
    )
    assert payload["verdict"] == "RAW"
    assert payload["dsr"] is None
    assert payload["acceptance_gate"] is None
    # raw_full_period warning still present (no WFA was run)
    assert any(w["code"] == "raw_full_period" for w in payload["warnings"])


def test_envelope_with_wfa_result_strips_raw_full_period_warning() -> None:
    """When WFA was actually run, raw_full_period warning is dropped (acceptance discipline applied)."""
    wfa = {
        "verdict": "WFA_FAIL",
        "failed_criteria": ["t5_floor"],
        "fold_sharpe_ratios": [0.0, 0.5],
        "trial_mean_fold_oos_sharpe": 0.25,
        "mc_p_value": 0.5,
        "dsr": 0.0,
        "dsr_pass": False,
        "n_trades_raw": 5,
        "wfa_params": {
            "train_bars": 2000,
            "test_bars": 500,
            "k_folds": 5,
            "embargo_bars": 20,
            "min_required": 4520,
            "actual": 5000,
        },
        "metrics": {},
        "trades": [],
    }
    payload = build_research_runner_envelope(
        runner_name="x",
        symbol="BTCUSDT",
        interval="240",
        n_trades=5,
        sharpe=0.5,
        win_rate=0.4,
        total_pnl_pct=10.0,
        bars_per_year=2191,
        equity_curve=[0.0, 10.0],
        runner_label="x",
        wfa_result=wfa,
    )
    # raw_full_period warning dropped — WFA discipline applied
    assert not any(w["code"] == "raw_full_period" for w in payload["warnings"])
