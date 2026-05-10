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


@pytest.mark.integration
@pytest.mark.parametrize(
    "symbol,interval,expected_pnl,start,end",
    [
        ("BTCUSDT", "240", 819.81, "2017-08-17", "2026-04-30"),
        ("SOLUSDT", "240", 264.29, "2023-01-01", "2026-04-26"),
        ("ETHUSDT", "60", 181.74, "2023-01-01", "2026-04-26"),
        ("BTCUSDT", "15", 107.35, "2023-01-01", "2026-04-26"),
        ("BTCUSDT", "60", 146.36, "2023-01-01", "2026-04-26"),
        ("SOLUSDT", "60", 214.08, "2023-01-01", "2026-04-26"),
        ("ETHUSDT", "240", 152.30, "2023-01-01", "2026-04-26"),
        ("SOLUSDT", "15", 150.51, "2023-01-01", "2026-04-26"),
        ("BTCUSDT", "D", 167.54, "2023-01-02", "2026-04-26"),
        ("ETHUSDT", "15", 35.53, "2023-01-01", "2026-04-26"),
    ],
)
def test_consolidated_atr_breakout_replicates_per_combo(
    symbol: str,
    interval: str,
    expected_pnl: float,
    start: str,
    end: str,
) -> None:
    """S42 T4 — single 'atr_breakout' preset returns correct PnL per supported combo."""
    from src.dashboard.backtest_runner import BacktestRequest, run_backtest

    req = BacktestRequest(
        strategy_id="atr_breakout",
        symbol=symbol,
        interval=interval,
        start=start,
        end=end,
    )
    r = run_backtest(req, force=True)
    delta = abs(r["total_pnl_pct"] - expected_pnl)
    assert (
        delta < 2.0
    ), f"PnL drift {symbol}_{interval}: expected {expected_pnl} got {r['total_pnl_pct']} delta {delta}"


@pytest.mark.integration
def test_old_atr_breakout_preset_ids_removed() -> None:
    """Backward compat (Q4 verdict CONFIRM (a)) — 10 old preset_ids removed."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    old_ids = [
        "atr_breakout_iter_endless",
        "atr_breakout_sol_4h_s41",
        "atr_breakout_eth_1h_s41",
        "atr_breakout_btc_15m_s41",
        "atr_breakout_btc_1h_s41",
        "atr_breakout_sol_1h_s41",
        "atr_breakout_eth_4h_s41",
        "atr_breakout_sol_15m_s41",
        "atr_breakout_btc_1d_s41",
        "atr_breakout_eth_15m_s41",
    ]
    for old in old_ids:
        assert old not in STRATEGY_PRESETS, f"Old preset {old} should be removed"
    assert "atr_breakout" in STRATEGY_PRESETS, "Unified preset missing"


@pytest.mark.integration
def test_atr_breakout_preset_has_supported_combos_field() -> None:
    """Q2 — supported_combos field for frontend gates."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    p = STRATEGY_PRESETS["atr_breakout"]
    assert "supported_combos" in p
    sc = p["supported_combos"]
    assert isinstance(sc, list)
    assert ("BTCUSDT", "240") in sc
    assert len(sc) == 10  # all autoresearch PASS combos


@pytest.mark.integration
def test_atr_breakout_dispatch_preserves_envelope_keys() -> None:
    """T4 critical fix — dispatch must merge envelope, not throw it away."""
    from src.dashboard.backtest_runner import BacktestRequest, run_backtest

    req = BacktestRequest(
        strategy_id="atr_breakout",
        symbol="BTCUSDT",
        interval="240",
        start="2017-08-17",
        end="2026-04-30",
    )
    r = run_backtest(req, force=True)
    for key in (
        "bars_per_year",
        "warnings",
        "failed_criteria",
        "verdict",
        "acceptance_gate",
        "dsr",
        "dsr_pass",
        "mc_p_value",
    ):
        assert key in r, f"Dispatch must merge envelope key: {key}"
    assert r["verdict"] == "RAW"
    assert isinstance(r["failed_criteria"], list)
    assert isinstance(r["warnings"], list)
    high = [w for w in r["warnings"] if w["code"] == "raw_full_period"]
    assert len(high) == 1


@pytest.mark.integration
def test_atr_breakout_envelope_includes_equity_curve_timestamps() -> None:
    """S43 T4 — atr_breakout runner passes df timestamps к envelope."""
    from datetime import date

    from src.backtest.atr_breakout_runner import run_atr_breakout_backtest

    r = run_atr_breakout_backtest(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2017, 8, 17),
        end_date=date(2026, 4, 30),
    )
    ec = r["equity_curve"]
    assert isinstance(ec, dict)
    assert len(ec["timestamps"]) == len(ec["equity_pct"])
    assert len(ec["timestamps"]) >= 70  # 69 trades + 1 starting zero
    assert ec["timestamps"][0] >= 1502928000  # 2017-08-17 unix
    assert all(isinstance(t, int) for t in ec["timestamps"])
    assert ec["equity_pct"][0] == 0.0
    assert abs(ec["equity_pct"][-1] - 819.81) < 2.0


@pytest.mark.integration
def test_volume_breakout_dispatch_preserves_envelope_keys() -> None:
    """T4 — same dispatch fix для volume_breakout."""
    from src.dashboard.backtest_runner import BacktestRequest, run_backtest

    req = BacktestRequest(
        strategy_id="volume_breakout_iter10",
        symbol="BTCUSDT",
        interval="240",
        start="2023-01-01",
        end="2026-04-26",
    )
    r = run_backtest(req, force=True)
    for key in ("bars_per_year", "warnings", "failed_criteria", "verdict"):
        assert key in r, f"volume_breakout dispatch must merge envelope key: {key}"
    assert r["verdict"] == "RAW"
