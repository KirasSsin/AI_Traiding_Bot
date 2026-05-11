"""S48 T7 — RunRecord shape verification для HistoryTab Bug H.

Two tests:
1. Existing on-disk run records — inspect win_rate presence; report pre-T7 gaps.
2. Post-T7 source check — both paths (replay + research) must emit
   initial_balance_quote + final_balance_quote.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from src.backtest.research_runner_envelope import build_research_runner_envelope


def test_existing_runs_have_win_rate_field() -> None:
    """trade_stats.win_rate was present pre-T7 via research path (verified S47).

    Replay path (backtest_runner.py) adds it post-T7.
    At minimum, run records saved after S47 research path should include it.
    Older replay-only records may not — we report without asserting (backwards compat).
    """
    runs_dir = Path("data/runs")
    if not runs_dir.exists():
        pytest.skip("no runs/ directory — fresh checkout")

    sample_files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[
        :5
    ]
    if not sample_files:
        pytest.skip("no run records yet")

    for path in sample_files:
        data = json.loads(path.read_text())
        ts = data.get("trade_stats", {})
        # Report shape gaps without hard-failing pre-T7 records (backwards compat)
        if "win_rate" not in ts:
            print(f"PRE-T7 RUN (no win_rate): {path.name}")
        if "initial_balance_quote" not in ts:
            print(f"PRE-T7 RUN (no initial_balance_quote): {path.name}")
        if "final_balance_quote" not in ts:
            print(f"PRE-T7 RUN (no final_balance_quote): {path.name}")


def test_replay_path_source_emits_balance_fields() -> None:
    """After T7 — backtest_runner.py trade_stats must reference balance fields."""
    import src.dashboard.backtest_runner as br_module

    source = inspect.getsource(br_module)
    assert (
        "initial_balance_quote" in source
    ), "backtest_runner.py must emit initial_balance_quote in trade_stats (S48 T7)"
    assert (
        "final_balance_quote" in source
    ), "backtest_runner.py must emit final_balance_quote in trade_stats (S48 T7)"
    assert (
        '"win_rate": t4_win' in source
    ), "backtest_runner.py must emit win_rate in trade_stats (S48 T7)"


def test_research_path_envelope_emits_balance_fields() -> None:
    """build_research_runner_envelope must return initial_balance_quote + final_balance_quote."""
    result = build_research_runner_envelope(
        runner_name="test_runner",
        symbol="BTCUSDT",
        interval="60",
        n_trades=50,
        sharpe=1.2,
        win_rate=0.55,
        total_pnl_pct=15.0,
        bars_per_year=8760,
        equity_curve=[0.0, 5.0, 10.0, 15.0],
        runner_label="Test Runner",
        initial_balance=10000.0,
    )
    ts = result["trade_stats"]
    assert "initial_balance_quote" in ts, "research envelope must emit initial_balance_quote"
    assert "final_balance_quote" in ts, "research envelope must emit final_balance_quote"
    assert ts["initial_balance_quote"] == 10000.0
    assert (
        abs(ts["final_balance_quote"] - 11500.0) < 0.01
    ), f"expected 11500.0 (10000 * 1.15), got {ts['final_balance_quote']}"


def test_research_path_envelope_default_initial_balance() -> None:
    """Default initial_balance=10000 when not provided (backwards-compat callers)."""
    result = build_research_runner_envelope(
        runner_name="test_runner",
        symbol="ETHUSDT",
        interval="240",
        n_trades=20,
        sharpe=0.8,
        win_rate=0.4,
        total_pnl_pct=-5.0,
        bars_per_year=2190,
        equity_curve=[0.0, -5.0],
        runner_label="Test Runner",
        # initial_balance omitted — should default to 10000.0
    )
    ts = result["trade_stats"]
    assert ts["initial_balance_quote"] == 10000.0
    assert (
        abs(ts["final_balance_quote"] - 9500.0) < 0.01
    ), f"expected 9500.0 (10000 * 0.95), got {ts['final_balance_quote']}"


def test_research_path_win_rate_in_trade_stats() -> None:
    """win_rate must be present in trade_stats (was present pre-T7, verify no regression)."""
    result = build_research_runner_envelope(
        runner_name="test_runner",
        symbol="BTCUSDT",
        interval="60",
        n_trades=30,
        sharpe=1.0,
        win_rate=0.6,
        total_pnl_pct=10.0,
        bars_per_year=8760,
        equity_curve=[0.0, 10.0],
        runner_label="Test Runner",
    )
    ts = result["trade_stats"]
    assert "win_rate" in ts
    assert ts["win_rate"] == pytest.approx(0.6)
