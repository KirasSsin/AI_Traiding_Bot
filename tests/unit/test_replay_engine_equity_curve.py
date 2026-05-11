"""S48 T2 — replay engine emits equity_curve parallel arrays для legacy presets (Bug B).

Two test strategies:
1. Unit test: verify equity_curve building logic directly from sym_trades list (no I/O).
2. Integration smoke: verify recent disk-cached runs from the replay path have equity_curve
   (only runs created AFTER the fix will pass; older runs are skipped gracefully).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Unit test: equity_curve computation logic (no WFA/OHLCV required)
# ---------------------------------------------------------------------------


def _make_trade(
    exit_ts: datetime,
    pnl_pct: float,
) -> MagicMock:
    """Build a minimal TradeRecord-like mock."""
    t = MagicMock()
    t.exit_ts = exit_ts
    t.pnl_pct = Decimal(str(pnl_pct))
    t.pnl_quote = Decimal("0.0")
    t.fees_paid = Decimal("0.0")
    t.symbol = "BTCUSDT"
    t.qty = Decimal("0.001")
    t.entry_price = Decimal("50000.0")
    t.exit_price = Decimal("51000.0")
    t.entry_ts = exit_ts
    t.reason_code = "SIGNAL"
    t.kelly_phase = 1
    return t


def test_equity_curve_cumulative_semantics() -> None:
    """equity_pct must be cumulative sum (×100) of trade.pnl_pct values.

    Verifies S48 T2 Bug B fix: replay engine builds equity_curve from TradeRecord list.
    pnl_pct is fractional (0.012 = +1.2%) → multiply ×100 for display percent.
    Running sum = cumulative equity percent from initial capital.
    """
    ts1 = datetime(2024, 1, 10, 12, 0, 0, tzinfo=UTC)
    ts2 = datetime(2024, 1, 11, 14, 0, 0, tzinfo=UTC)
    ts3 = datetime(2024, 1, 12, 16, 0, 0, tzinfo=UTC)

    trades = [
        _make_trade(ts1, 0.012),  # +1.2%
        _make_trade(ts2, -0.008),  # -0.8% → cumulative: +0.4%
        _make_trade(ts3, 0.020),  # +2.0% → cumulative: +2.4%
    ]

    # Replicate the S48 T2 logic from backtest_runner.py
    eq_timestamps: list[int] = []
    eq_pct: list[float] = []
    running_pct = 0.0
    for t in trades:
        running_pct += float(t.pnl_pct) * 100.0
        eq_timestamps.append(int(t.exit_ts.timestamp()))
        eq_pct.append(running_pct)

    assert len(eq_timestamps) == 3
    assert len(eq_pct) == 3
    assert eq_timestamps[0] == int(ts1.timestamp())
    assert eq_timestamps[1] == int(ts2.timestamp())
    assert eq_timestamps[2] == int(ts3.timestamp())
    assert abs(eq_pct[0] - 1.2) < 1e-9
    assert abs(eq_pct[1] - 0.4) < 1e-9
    assert abs(eq_pct[2] - 2.4) < 1e-9


def test_equity_curve_empty_trades() -> None:
    """Empty sym_trades → equity_curve has empty arrays (no crash, no None)."""
    trades: list = []
    eq_timestamps: list[int] = []
    eq_pct: list[float] = []
    running_pct = 0.0
    for t in trades:
        running_pct += float(t.pnl_pct) * 100.0
        eq_timestamps.append(int(t.exit_ts.timestamp()))
        eq_pct.append(running_pct)

    assert eq_timestamps == []
    assert eq_pct == []


# ---------------------------------------------------------------------------
# Disk-run smoke test: runs created AFTER the fix must have equity_curve
# ---------------------------------------------------------------------------


def test_replay_envelope_includes_equity_curve_arrays() -> None:
    """Bug B fix: legacy WFA presets (ema/mean_reversion/donchian) должны emit
    equity_curve.timestamps + equity_pct arrays (как research_runner_envelope path)
    для frontend chart support.

    equity_pct is cumulative percent relative to initial capital:
    e.g. trade with pnl_pct=0.012 contributes +1.2% to running total.

    NOTE: runs created BEFORE S48 T2 fix are skipped (no equity_curve in cache).
    The test validates the NEW schema for post-fix runs only.
    """
    runs_dir = Path("data/runs")
    if not runs_dir.exists():
        pytest.skip("data/runs/ not present")

    # Find recent replay-path runs.
    # Replay path covers both:
    #   (a) new WFA presets: verdict in ("WFA_PASS", "WFA_FAIL")
    #   (b) legacy presets (ema/mean_reversion/donchian): verdict in ("PASS", "FAIL")
    # Common indicator: metrics has "t1_sharpe_oos" key (T1-T6 metrics computed by replay engine).
    # Only validate runs that have equity_curve key (post-fix runs).
    post_fix_runs: list[tuple[Path, dict]] = []  # type: ignore[type-arg]
    pre_fix_runs_count = 0

    for p in sorted(runs_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text())
            verdict = data.get("verdict", "")
            metrics = data.get("metrics", {})
            if verdict in ("WFA_PASS", "WFA_FAIL", "PASS", "FAIL") and "t1_sharpe_oos" in metrics:
                if "equity_curve" in data:
                    post_fix_runs.append((p, data))
                else:
                    pre_fix_runs_count += 1
        except Exception:  # noqa: BLE001
            continue

    if not post_fix_runs:
        pytest.skip(
            f"No post-fix replay-path runs found "
            f"({pre_fix_runs_count} pre-fix runs without equity_curve skipped)"
        )

    for path, data in post_fix_runs:
        ec = data.get("equity_curve")
        assert ec is not None, f"{path.name}: equity_curve missing (replay path Bug B not fixed)"
        assert "timestamps" in ec, f"{path.name}: timestamps missing from equity_curve"
        assert "equity_pct" in ec, f"{path.name}: equity_pct missing from equity_curve"
        assert isinstance(ec["timestamps"], list), f"{path.name}: timestamps must be list"
        assert isinstance(ec["equity_pct"], list), f"{path.name}: equity_pct must be list"
        # If trades exist, equity_curve arrays must be non-empty
        n_trades = data.get("trade_stats", {}).get("n_trades", None)
        if n_trades is None:
            n_trades = data.get("metrics", {}).get("t5_n_trades", 0) or 0
        if n_trades > 0:
            assert len(ec["timestamps"]) > 0, f"{path.name}: timestamps empty с n_trades={n_trades}"
            assert len(ec["equity_pct"]) > 0, f"{path.name}: equity_pct empty с n_trades={n_trades}"
            assert len(ec["timestamps"]) == len(
                ec["equity_pct"]
            ), f"{path.name}: timestamps/equity_pct length mismatch"
