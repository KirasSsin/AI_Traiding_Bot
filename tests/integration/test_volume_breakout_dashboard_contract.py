"""S42 T3 — volume_breakout dashboard envelope contract."""

from __future__ import annotations

from datetime import date

import pytest
from src.backtest.volume_breakout_runner import run_volume_breakout_backtest

REQUIRED_DASHBOARD_KEYS = (
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
    "request",
    "n_trades",
    "sharpe",
    "win_rate",
    "total_pnl_pct",
    "runner",
)


@pytest.mark.integration
def test_volume_breakout_returns_envelope_keys() -> None:
    r = run_volume_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
    )
    for key in REQUIRED_DASHBOARD_KEYS:
        assert key in r, f"S42 contract missing key: {key}"


@pytest.mark.integration
def test_volume_breakout_envelope_verdict_is_raw() -> None:
    r = run_volume_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
    )
    assert r["verdict"] == "RAW"
    assert r["failed_criteria"] == []


@pytest.mark.integration
def test_volume_breakout_envelope_warnings_includes_raw_full_period() -> None:
    r = run_volume_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
    )
    high = [w for w in r["warnings"] if w["level"] == "high" and w["code"] == "raw_full_period"]
    assert len(high) == 1


@pytest.mark.integration
def test_volume_breakout_envelope_request_carries_symbol_interval() -> None:
    r = run_volume_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
    )
    assert r["request"]["symbol"] == "BTCUSDT"
    assert r["request"]["interval"] == "240"
    assert r["request"]["start"] == "2023-01-01"
    assert r["request"]["end"] == "2026-04-26"
    assert r["bars_per_year"] == 2191
