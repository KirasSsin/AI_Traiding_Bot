"""S42 T2 — atr_breakout dashboard envelope contract."""

from __future__ import annotations

from datetime import date

import pytest
from src.backtest.atr_breakout_runner import run_atr_breakout_backtest

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
def test_atr_breakout_returns_envelope_keys() -> None:
    """Every key dashboard.js reads MUST be present."""
    r = run_atr_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2017, 8, 17),
        end_date=date(2026, 4, 30),
    )
    for key in REQUIRED_DASHBOARD_KEYS:
        assert key in r, f"S42 contract missing key: {key}"


@pytest.mark.integration
def test_atr_breakout_envelope_verdict_is_raw() -> None:
    """RAW verdict — acceptance discipline skipped до S43."""
    r = run_atr_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2017, 8, 17),
        end_date=date(2026, 4, 30),
    )
    assert r["verdict"] == "RAW"
    assert r["failed_criteria"] == []


@pytest.mark.integration
def test_atr_breakout_envelope_warnings_includes_raw_full_period() -> None:
    """High-level honest disclosure chip present."""
    r = run_atr_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2017, 8, 17),
        end_date=date(2026, 4, 30),
    )
    high = [w for w in r["warnings"] if w["level"] == "high" and w["code"] == "raw_full_period"]
    assert len(high) == 1


@pytest.mark.integration
def test_atr_breakout_envelope_request_carries_symbol_interval() -> None:
    r = run_atr_breakout_backtest(
        symbol="ETHUSDT",
        interval="60",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
    )
    assert r["request"]["symbol"] == "ETHUSDT"
    assert r["request"]["interval"] == "60"
    assert r["request"]["start"] == "2023-01-01"
    assert r["request"]["end"] == "2026-04-26"


@pytest.mark.integration
def test_atr_breakout_envelope_preserves_pnl_replication_btc_4h() -> None:
    """REGRESSION: envelope wrap must NOT change PnL math.
    BTCUSDT 4H expected 819.81 ± 2.0 from S40 baseline.
    """
    r = run_atr_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2017, 8, 17),
        end_date=date(2026, 4, 30),
    )
    assert abs(r["total_pnl_pct"] - 819.81) < 2.0
    assert r["n_trades"] == 69
