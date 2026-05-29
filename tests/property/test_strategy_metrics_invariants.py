"""Hypothesis property invariants for compute_t1_t6_metrics (S49 M8d).

`src/backtest/strategy_metrics.py::compute_t1_t6_metrics` is a formula module of the
S27 bug class (subtle NaN / division / sign errors that pass example-based tests but
break on adversarial inputs). These properties assert structural invariants that must
hold for *any* synthetic OOS trade series:

  - t3_max_drawdown ∈ [0, 1]              (a fraction, never negative, never > 100%)
  - t4_win_rate     ∈ [0, 1]
  - t1_sharpe / t2_sortino / t5_t_stat / t6 are finite-or-NaN, never ±inf
  - t5_n_trades == len(trades)

NaN is an allowed sentinel ("insufficient data"); ±inf is not — an infinite Sharpe
would silently flip an acceptance criterion.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(pnl_pct: float, pnl_quote: float) -> TradeRecord:
    """Minimal TradeRecord carrying only the pnl fields the metrics read."""
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=datetime(2025, 1, 1, tzinfo=UTC),
        exit_ts=datetime(2025, 1, 1, 1, tzinfo=UTC),
        qty=Decimal("0.1"),
        entry_price=Decimal("50000"),
        exit_price=Decimal("50500"),
        pnl_quote=Decimal(str(round(pnl_quote, 6))),
        pnl_pct=Decimal(str(round(pnl_pct, 6))),
        fees_paid=Decimal("0"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=datetime(2025, 1, 1, 1, tzinfo=UTC),
    )


def _finite_or_nan(x: float) -> bool:
    return math.isnan(x) or math.isfinite(x)


# pnl_pct kept within a realistic per-trade band; pnl_quote derived so drawdown
# never blows equity below zero against the 10_000 default initial_capital.
_pnl_pct = st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)
_pnl_quote = st.floats(min_value=-500.0, max_value=500.0, allow_nan=False, allow_infinity=False)
_trade_strategy = st.builds(_make_trade, pnl_pct=_pnl_pct, pnl_quote=_pnl_quote)
_fold_sharpes = st.lists(
    st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    max_size=10,
)


@pytest.mark.property
@settings(max_examples=200, deadline=None)
@given(
    trades=st.lists(_trade_strategy, min_size=1, max_size=60),
    fold_oos_is_sharpe=_fold_sharpes,
)
def test_metrics_invariants_hold_for_any_series(
    trades: list[TradeRecord], fold_oos_is_sharpe: list[float]
) -> None:
    m = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=fold_oos_is_sharpe)

    # Bounded fractions.
    dd = m["t3_max_drawdown"]
    assert math.isnan(dd) or (0.0 <= dd <= 1.0), f"max_drawdown out of [0,1]: {dd}"
    wr = m["t4_win_rate"]
    assert math.isnan(wr) or (0.0 <= wr <= 1.0), f"win_rate out of [0,1]: {wr}"

    # Finite-or-NaN (never ±inf) for every ratio metric.
    for key in (
        "t1_sharpe_oos",
        "t2_sortino_oos",
        "t4_avg_rr",
        "t5_mean_pnl_pct",
        "t5_t_stat",
        "t6_oos_is_sharpe_ratio_mean",
    ):
        assert _finite_or_nan(m[key]), f"{key} is non-finite (inf): {m[key]}"

    # Bookkeeping.
    assert m["t5_n_trades"] == len(trades)


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(fold_oos_is_sharpe=_fold_sharpes)
def test_empty_trades_returns_nan_sentinels(fold_oos_is_sharpe: list[float]) -> None:
    """n == 0 branch: numeric fields are NaN, n_trades == 0, no exception."""
    m = compute_t1_t6_metrics(trades=[], fold_oos_is_sharpe=fold_oos_is_sharpe)
    assert m["t5_n_trades"] == 0
    assert math.isnan(m["t3_max_drawdown"])
    assert math.isnan(m["t4_win_rate"])
    assert _finite_or_nan(m["t6_oos_is_sharpe_ratio_mean"])


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(
    win_pcts=st.lists(
        st.floats(min_value=0.001, max_value=0.5, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=40,
    )
)
def test_all_winners_win_rate_one_and_drawdown_zero(win_pcts: list[float]) -> None:
    """Monotone-up equity (all winners): win_rate == 1, drawdown == 0, Sortino NaN."""
    trades = [_make_trade(p, p * 1000) for p in win_pcts]
    m = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[])
    assert m["t4_win_rate"] == 1.0
    assert m["t3_max_drawdown"] == 0.0
    # No losers → downside deviation 0 → Sortino undefined (NaN, not inf).
    assert math.isnan(m["t2_sortino_oos"])
