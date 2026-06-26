"""S55 Batch 2 HIGH QS-1 — DSR single-scale units fix.

THE DEFECT (pre-fix): compute_dsr's internal candidate Sharpe (dsr.py:103,
`sharpe = mean/std` over per-trade log returns) is UN-ANNUALIZED, but the
`sigma_sr` callers feed (research_wfa.py / wfa_reporter.py) is the stdev of
ANNUALIZED fold/trial Sharpes (× sqrt(bars_per_year/mean_holding) ≈ ~9×).

Bailey & López de Prado 2014 eq.12 (`sharpe_star = benchmark + sigma_sr·(...)`)
and eq.13 assume a SINGLE observation frequency throughout. Feeding an annualized
sigma_sr against a per-trade candidate Sharpe inflates `sharpe_star` ~9× → forces
`(sharpe - sharpe_star)` deeply negative → DSR≈0 false-negative gate. ACTIVE for
atr_breakout (genuine-edge strategies wrongly FAIL the DSR criterion).

THE FIX (quant-stats-reviewer verdict, option B): de-annualize sigma_sr to the
per-trade scale inside compute_dsr via `annualization_factor`, leaving eq.13
fully per-trade (Lo 2002 variance-of-SR denom is frequency-sensitive — scaling SR
up into it would be mathematically invalid). New param default None = no-op for
the n_trials=1 path (sigma_sr unused there) → fully backward-compatible.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.analytics.dsr import compute_dsr
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(*, pnl_pct: float, hours: int) -> TradeRecord:
    base = datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC)
    pct = Decimal(str(round(pnl_pct, 8)))
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=base + timedelta(hours=hours),
        exit_ts=base + timedelta(hours=hours + 1),
        qty=Decimal("0.5"),
        entry_price=Decimal("100000"),
        exit_price=Decimal("100000") * (Decimal("1") + pct),
        pnl_quote=Decimal("100"),
        pnl_pct=pct,
        fees_paid=Decimal("0.05"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=base,
    )


def _genuine_edge_trades() -> list[TradeRecord]:
    """A profitable, modest-edge track record (real but not extreme Sharpe).

    60 trades: 0.008 win two of three trades, -0.006 loss every third. Tuned so
    the UN-aligned (annualized-sigma) DSR is crushed to a false-negative while the
    single-scale DSR clears the 0.95 gate — i.e. it isolates the units bug rather
    than a track record so strong it passes either way.
    """
    trades: list[TradeRecord] = []
    for i in range(60):
        pnl = 0.008 if i % 3 != 0 else -0.006
        trades.append(_make_trade(pnl_pct=pnl, hours=i))
    return trades


# Realistic ANNUALIZED sigma_sr as callers actually pass it (stdev of fold
# Sharpes that were each × sqrt(bars_per_year/mean_holding); ~unit-ish stdev on
# the annualized scale). The annualization factor for 1H crypto, mean holding
# ~100 bars: sqrt(8760/100) ≈ 9.36.
_ANNUALIZED_SIGMA_SR = 0.6
_ANNUALIZATION_FACTOR = math.sqrt(8760.0 / 100.0)


def test_annualized_sigma_without_factor_suppresses_dsr() -> None:
    """REPRO the defect: annualized sigma_sr + no annualization_factor → DSR≈0.

    This is the current (buggy) call shape — SR per-trade vs sigma_sr annualized.
    The inflated sharpe_star crushes a genuine edge to a near-zero DSR.
    """
    trades = _genuine_edge_trades()
    dsr_mismatched = compute_dsr(trades, n_trials=8, sigma_sr=_ANNUALIZED_SIGMA_SR)
    assert math.isfinite(dsr_mismatched)
    # Mismatched scales force a false-negative — well below the 0.95 gate.
    assert dsr_mismatched < 0.5


def test_single_scale_allows_genuine_edge_to_pass_gate() -> None:
    """With annualization_factor matching the sigma_sr scale, a genuine edge
    CAN clear the 0.95 DSR gate (impossible under the mismatch).
    """
    trades = _genuine_edge_trades()
    dsr_aligned = compute_dsr(
        trades,
        n_trials=8,
        sigma_sr=_ANNUALIZED_SIGMA_SR,
        annualization_factor=_ANNUALIZATION_FACTOR,
    )
    assert math.isfinite(dsr_aligned)
    assert dsr_aligned > 0.95, (
        f"genuine-edge DSR={dsr_aligned} must clear 0.95 once SR and sigma_sr "
        "share one frequency (Bailey eq.12/13 single-scale assumption)"
    )


def test_annualization_factor_de_annualizes_sigma_sr() -> None:
    """annualization_factor=f is exactly equivalent to passing sigma_sr/f.

    Confirms the fix de-annualizes sigma_sr (option B) rather than touching the
    candidate Sharpe or the eq.13 denom.
    """
    trades = _genuine_edge_trades()
    via_factor = compute_dsr(
        trades,
        n_trials=8,
        sigma_sr=_ANNUALIZED_SIGMA_SR,
        annualization_factor=_ANNUALIZATION_FACTOR,
    )
    via_manual = compute_dsr(
        trades,
        n_trials=8,
        sigma_sr=_ANNUALIZED_SIGMA_SR / _ANNUALIZATION_FACTOR,
    )
    assert via_factor == via_manual


def test_annualization_factor_none_is_backward_compatible() -> None:
    """Default annualization_factor=None changes nothing (no scaling applied)."""
    trades = _genuine_edge_trades()
    default = compute_dsr(trades, n_trials=8, sigma_sr=_ANNUALIZED_SIGMA_SR)
    explicit_none = compute_dsr(
        trades, n_trials=8, sigma_sr=_ANNUALIZED_SIGMA_SR, annualization_factor=None
    )
    assert default == explicit_none


def test_annualization_factor_ignored_for_n_trials_1() -> None:
    """n_trials=1 path never uses sigma_sr → annualization_factor is a no-op."""
    trades = _genuine_edge_trades()
    base = compute_dsr(trades, n_trials=1)
    with_factor = compute_dsr(trades, n_trials=1, annualization_factor=_ANNUALIZATION_FACTOR)
    assert base == with_factor
