"""S36 T7 — live trade reporter ADR 0055 SD-6 methodology tests."""

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from src.analytics.live_trade_reporter import (
    DELTA_N_TRIALS_LOCKED,
    compute_calibration_ratio,
    compute_live_sharpe,
    compute_mc_with_gating,
    generate_live_report,
)
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_records(n: int, *, mean_pnl: float = 10.0, var_factor: float = 1.0) -> list[TradeRecord]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    records = []
    for i in range(n):
        # alternate sign with magnitude variation для non-zero stdev
        pnl = Decimal(str(mean_pnl + var_factor * (-1) ** i * (i % 5 + 1)))
        records.append(
            TradeRecord(
                symbol="BTCUSDT",
                entry_signal_id=uuid4(),
                entry_ts=base + timedelta(hours=i),
                exit_ts=base + timedelta(hours=i, minutes=30),
                qty=Decimal("0.1"),
                entry_price=Decimal("50000"),
                exit_price=Decimal("50000") + pnl,
                pnl_quote=pnl,
                pnl_pct=pnl / Decimal("50000"),
                fees_paid=Decimal("0.1"),
                reason_code=ReasonCode.EXIT_SL_HIT,
                kelly_phase=1,
                recorded_at=base + timedelta(hours=i, minutes=30),
            )
        )
    return records


def test_live_sharpe_gate_eligible_when_n_above_30() -> None:
    """ADR 0055 SD-6: n >= 30 → status GATE_ELIGIBLE + finite sharpe."""
    result = compute_live_sharpe(_make_records(35), bars_per_year=2190, avg_bars_per_trade=12.0)
    assert result["status"] == "GATE_ELIGIBLE"
    assert math.isfinite(result["sharpe"])
    assert result["n"] == 35


def test_live_sharpe_underpowered_when_10_to_30() -> None:
    result = compute_live_sharpe(_make_records(15))
    assert result["status"] == "UNDERPOWERED"
    assert math.isfinite(result["sharpe"])


def test_live_sharpe_insufficient_when_below_10() -> None:
    result = compute_live_sharpe(_make_records(5))
    assert result["status"] == "INSUFFICIENT_TRADES"
    assert math.isnan(result["sharpe"])


def test_calibration_ratio_pass_when_above_0_7() -> None:
    """Calibration ratio = live / S22_synthetic. >= 0.7 = PASS."""
    ratio = compute_calibration_ratio(live_sharpe=4.5, synthetic_s22_sharpe=6.17)
    assert ratio == pytest.approx(4.5 / 6.17, abs=1e-6)
    assert ratio > 0.7  # PASS


def test_calibration_ratio_fail_when_below_0_7() -> None:
    ratio = compute_calibration_ratio(live_sharpe=2.0, synthetic_s22_sharpe=6.17)
    assert ratio < 0.7  # FAIL


def test_calibration_ratio_nan_when_synthetic_zero() -> None:
    """Defensive: zero benchmark → NaN (avoid ZeroDivisionError)."""
    assert math.isnan(compute_calibration_ratio(live_sharpe=1.0, synthetic_s22_sharpe=0.0))


def test_calibration_ratio_nan_when_live_nan() -> None:
    """NaN propagation."""
    assert math.isnan(compute_calibration_ratio(live_sharpe=float("nan")))


def test_mc_gating_sign_flip_blocked_below_n_20() -> None:
    """ADR 0055 SD-6: sign-flip MC requires n >= 20 trades."""
    result = compute_mc_with_gating([1.0] * 15)
    assert result["sign_flip"] is None
    assert result["block_bootstrap"] is None
    assert result["status"] == "MC_INSUFFICIENT_N"


def test_mc_gating_sign_flip_only_when_20_to_40() -> None:
    """20 <= n < 40 → sign-flip computed, block-bootstrap None (degenerate)."""
    # need NON-zero variance returns
    returns = [(-1.0) ** i * (1.0 + i * 0.1) for i in range(25)]
    result = compute_mc_with_gating(returns)
    assert result["sign_flip"] is not None
    assert result["block_bootstrap"] is None
    assert result["status"] == "OK"


def test_mc_gating_both_when_n_above_40() -> None:
    """n >= 40 → both sign-flip + block-bootstrap computed."""
    returns = [(-1.0) ** i * (1.0 + i * 0.1) for i in range(45)]
    result = compute_mc_with_gating(returns)
    assert result["sign_flip"] is not None
    assert result["block_bootstrap"] is not None


def test_generate_live_report_full_metrics() -> None:
    """Single entry-point produces all required ADR 0055 SD-6 metrics."""
    records = _make_records(35, mean_pnl=20.0, var_factor=2.0)
    report = generate_live_report(records)
    assert report["n_trades"] == 35
    assert "live_sharpe" in report
    assert "calibration_ratio_to_s22" in report
    assert "mc" in report
    assert "dsr" in report
    assert report["n_trials_counter"] == DELTA_N_TRIALS_LOCKED
    assert report["n_trials_counter"] == 7  # S13/S15/S17/S20/S22/S33/S35
    assert report["methodology"] == "ADR_0055_SD6_LIVE_ADAPTED"
