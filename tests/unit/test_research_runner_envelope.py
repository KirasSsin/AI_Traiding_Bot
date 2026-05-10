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
