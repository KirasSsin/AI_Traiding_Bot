"""T1-T6 strategy metrics extraction (S13 T6 per acceptance-criteria.md)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(*, pnl_quote: Decimal, hours_offset: int = 0,
                qty_decimal: Decimal = Decimal("0.001"),
                entry_price_decimal: Decimal = Decimal("50000")) -> TradeRecord:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    notional = qty_decimal * entry_price_decimal
    exit_price = entry_price_decimal + (pnl_quote / qty_decimal)
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=base + timedelta(hours=hours_offset),
        exit_ts=base + timedelta(hours=hours_offset + 1),
        qty=qty_decimal,
        entry_price=entry_price_decimal,
        exit_price=exit_price,
        pnl_quote=pnl_quote,
        pnl_pct=pnl_quote / notional,
        fees_paid=Decimal("0.05"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=base,
    )


def test_compute_metrics_returns_all_t1_t6_fields() -> None:
    trades = [_make_trade(pnl_quote=Decimal("1.0"), hours_offset=i) for i in range(120)]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[0.8, 0.9, 0.75, 0.85, 0.95])
    assert set(metrics.keys()) >= {
        "t1_sharpe_oos", "t2_sortino_oos", "t3_max_drawdown",
        "t4_win_rate", "t4_avg_rr",
        "t5_mean_pnl_pct", "t5_t_stat", "t5_n_trades",
        "t6_oos_is_sharpe_ratio_mean",
    }


def test_compute_metrics_t1_sharpe_winners_positive() -> None:
    trades = [_make_trade(pnl_quote=Decimal("1.0"), hours_offset=i) for i in range(100)]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    assert metrics["t1_sharpe_oos"] > 0


def test_compute_metrics_t3_max_drawdown_zero_for_monotonic() -> None:
    trades = [_make_trade(pnl_quote=Decimal("1.0"), hours_offset=i) for i in range(50)]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    assert metrics["t3_max_drawdown"] == pytest.approx(0.0, abs=0.001)


def test_compute_metrics_t3_max_drawdown_with_dip() -> None:
    """30 winners $10 + 30 losers -$5 + 30 winners $5 -> dips -> MaxDD > 0."""
    trades = (
        [_make_trade(pnl_quote=Decimal("10"), hours_offset=i) for i in range(30)]
        + [_make_trade(pnl_quote=Decimal("-5"), hours_offset=30 + i) for i in range(30)]
        + [_make_trade(pnl_quote=Decimal("5"), hours_offset=60 + i) for i in range(30)]
    )
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    assert metrics["t3_max_drawdown"] > 0


def test_compute_metrics_t4_win_rate() -> None:
    trades = (
        [_make_trade(pnl_quote=Decimal("1.0"), hours_offset=i) for i in range(50)]
        + [_make_trade(pnl_quote=Decimal("-1.0"), hours_offset=50 + i) for i in range(50)]
    )
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    assert metrics["t4_win_rate"] == pytest.approx(0.5, abs=0.01)


def test_compute_metrics_t5_n_trades() -> None:
    trades = [_make_trade(pnl_quote=Decimal("0.5"), hours_offset=i) for i in range(123)]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    assert metrics["t5_n_trades"] == 123


def test_compute_metrics_t6_oos_is_sharpe_ratio_mean() -> None:
    trades = [_make_trade(pnl_quote=Decimal("1.0"), hours_offset=i) for i in range(100)]
    fold_oos_is = [0.7, 0.8, 0.9]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=fold_oos_is)
    assert metrics["t6_oos_is_sharpe_ratio_mean"] == pytest.approx(0.8, abs=0.01)


def test_compute_metrics_empty_trades_returns_nan() -> None:
    metrics = compute_t1_t6_metrics(trades=[], fold_oos_is_sharpe=[])
    assert metrics["t5_n_trades"] == 0
    import math
    assert math.isnan(metrics["t1_sharpe_oos"])


def test_compute_metrics_t3_initial_capital_parameterizable() -> None:
    """initial_capital sourced as parameter (not hardcoded)."""
    trades = [_make_trade(pnl_quote=Decimal("100"), hours_offset=i) for i in range(10)]
    metrics_default = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0])
    metrics_50k = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0], initial_capital=50000.0)
    assert metrics_default["t3_max_drawdown"] == pytest.approx(0.0, abs=0.001)
    assert metrics_50k["t3_max_drawdown"] == pytest.approx(0.0, abs=0.001)


def test_compute_metrics_t3_total_blowout_returns_one() -> None:
    """T3 MaxDD = 100% (NOT NaN) on equity hits 0."""
    blowout = _make_trade(
        pnl_quote=Decimal("-10000"),
        qty_decimal=Decimal("1.0"),
        entry_price_decimal=Decimal("50000"),
        hours_offset=0,
    )
    metrics = compute_t1_t6_metrics(trades=[blowout], fold_oos_is_sharpe=[1.0])
    assert metrics["t3_max_drawdown"] == pytest.approx(1.0, abs=0.001)


def test_compute_metrics_t3_first_loss_drawdown_from_initial_capital() -> None:
    """T3 MaxDD: first trade is loss → drawdown measured from initial_capital,
    NOT post-loss equity (quant-stats reviewer T6 BLOCKER fix)."""
    trades = [_make_trade(pnl_quote=Decimal("-500"), hours_offset=0,
                          qty_decimal=Decimal("0.1"), entry_price_decimal=Decimal("50000"))]
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0],
                                     initial_capital=10000.0)
    # Initial $10000 → after -$500 loss = $9500 → drawdown = $500/$10000 = 5%
    assert metrics["t3_max_drawdown"] == pytest.approx(0.05, abs=0.001)


def test_compute_metrics_t3_first_loss_then_recovery() -> None:
    """T3 MaxDD: drawdown from initial peak preserved через recovery."""
    trades = [
        _make_trade(pnl_quote=Decimal("-500"), hours_offset=0,
                    qty_decimal=Decimal("0.1"), entry_price_decimal=Decimal("50000")),
        _make_trade(pnl_quote=Decimal("1000"), hours_offset=1,
                    qty_decimal=Decimal("0.1"), entry_price_decimal=Decimal("50000")),
    ]
    # Equity: $10000 → $9500 → $10500. Peak=$10000 (initial), trough=$9500.
    # MaxDD = ($10000 - $9500) / $10000 = 5%
    metrics = compute_t1_t6_metrics(trades=trades, fold_oos_is_sharpe=[1.0],
                                     initial_capital=10000.0)
    assert metrics["t3_max_drawdown"] == pytest.approx(0.05, abs=0.001)
