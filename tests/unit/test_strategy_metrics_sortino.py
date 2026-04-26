"""S27 T2 — canonical Sortino downside deviation.

Bug pre-fix: src/backtest/strategy_metrics.py:80-85 used `losers.std(ddof=1)`
(std of losing trades only, mean-centered). Canonical Sortino uses downside
deviation = sqrt(mean(min(r, target)**2)) over ALL n trades, target=0.

Per Sortino & Price (1994), Bailey & López de Prado (2018) — downside
deviation must include all observations, treating non-negative as 0.

Pre-fix produces ~3.6x inflated Sortino. Currently masked by anomaly guard
(n<100 AND |sortino|>50 → display N/A) so не affects current verdicts. But
если strategy reaches n≥100 near T2 threshold (≥1.5), false-positive risk.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import numpy as np
import pytest

from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(pnl_pct: float, hours_offset: int = 0) -> TradeRecord:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    qty = Decimal("0.001")
    entry = Decimal("50000")
    notional = qty * entry
    pnl_quote = Decimal(str(pnl_pct)) * notional
    exit_price = entry + (pnl_quote / qty)
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=base + timedelta(hours=hours_offset),
        exit_ts=base + timedelta(hours=hours_offset + 1),
        qty=qty,
        entry_price=entry,
        exit_price=exit_price,
        pnl_quote=pnl_quote,
        pnl_pct=Decimal(str(pnl_pct)),
        fees_paid=Decimal("0.0"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=base,
    )


def test_sortino_canonical_downside_deviation() -> None:
    """Sortino = mean(returns) / sqrt(mean(min(r,0)^2)) × annualization.

    NOT std of losers subset.
    """
    # 4 winners (+0.02) + 2 losers (-0.01) — known returns
    trades = [_make_trade(0.02, i) for i in range(4)]
    trades += [_make_trade(-0.01, i + 4) for i in range(2)]

    metrics = compute_t1_t6_metrics(
        trades=trades, fold_oos_is_sharpe=[1.0], bars_per_year=8760,
    )

    # Manual canonical Sortino calc
    pnl_pcts = np.array([0.02, 0.02, 0.02, 0.02, -0.01, -0.01])
    mean_r = float(pnl_pcts.mean())
    downside = np.minimum(pnl_pcts, 0.0)  # zeros for non-losing trades
    downside_dev = float(np.sqrt(np.mean(downside ** 2)))
    expected_sortino_per_trade = mean_r / downside_dev
    expected_sortino_annualized = expected_sortino_per_trade * float(np.sqrt(8760))

    assert metrics["t2_sortino_oos"] == pytest.approx(expected_sortino_annualized, rel=1e-6)


def test_sortino_with_only_losers_uses_canonical_formula() -> None:
    """Verify denom = rms(losses) over all n trades, not std(losers, ddof=1)."""
    trades = [_make_trade(-0.01, i) for i in range(5)]

    metrics = compute_t1_t6_metrics(
        trades=trades, fold_oos_is_sharpe=[1.0], bars_per_year=8760,
    )

    pnl_pcts = np.array([-0.01] * 5)
    mean_r = float(pnl_pcts.mean())
    downside = np.minimum(pnl_pcts, 0.0)
    downside_dev = float(np.sqrt(np.mean(downside ** 2)))  # = 0.01
    expected = (mean_r / downside_dev) * float(np.sqrt(8760))

    assert metrics["t2_sortino_oos"] == pytest.approx(expected, rel=1e-6)


def test_sortino_zero_downside_returns_nan() -> None:
    """Edge case: all winners → downside_dev=0 → NaN (not crash)."""
    trades = [_make_trade(0.01, i) for i in range(10)]

    metrics = compute_t1_t6_metrics(
        trades=trades, fold_oos_is_sharpe=[1.0], bars_per_year=8760,
    )

    assert np.isnan(metrics["t2_sortino_oos"])


def test_sortino_pre_fix_buggy_formula_now_rejected() -> None:
    """Verify current Sortino does NOT match pre-fix std(losers, ddof=1) formula.

    Sanity: ensure test catches if someone reverts к buggy implementation.
    """
    trades = [_make_trade(0.02, i) for i in range(4)]
    trades += [_make_trade(-0.01, i + 4) for i in range(2)]

    metrics = compute_t1_t6_metrics(
        trades=trades, fold_oos_is_sharpe=[1.0], bars_per_year=8760,
    )

    pnl_pcts = np.array([0.02, 0.02, 0.02, 0.02, -0.01, -0.01])
    losers_only = pnl_pcts[pnl_pcts < 0]
    # Pre-fix formula (buggy): std(losers, ddof=1) — only 2 losers, std on subset
    if len(losers_only) > 1 and float(losers_only.std(ddof=1)) > 0:
        buggy_sortino_per_trade = float(pnl_pcts.mean() / losers_only.std(ddof=1))
        buggy_sortino_annualized = buggy_sortino_per_trade * float(np.sqrt(8760))
        # Verify NEW formula not equal к buggy formula (when both denominators nonzero)
        # If equal — fix didn't take effect
        assert abs(metrics["t2_sortino_oos"] - buggy_sortino_annualized) > 1e-3, (
            f"Sortino still uses buggy formula: got {metrics['t2_sortino_oos']:.6f}, "
            f"buggy = {buggy_sortino_annualized:.6f}"
        )
    else:
        # Buggy formula would crash; canonical handles fine
        assert not np.isnan(metrics["t2_sortino_oos"])
