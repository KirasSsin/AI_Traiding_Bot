"""WFA reporter — 3-series Sharpe routing + DSR aggregate informational.

Sprint 10 Q4 + Q6 + Q7 (per pre-s10-backlog.md verdicts + cross-cutting concerns).

3 distinct Sharpe series MUST NOT conflate (cross-cutting concern #1):
1. Bar-returns Sharpe (sqrt(8760) annualized) — used для ADR 0014 OOS/IS gate
2. Per-trade Sharpe (DSR internal, NOT annualized) — produced by DSR module
3. Display Sharpe (sqrt(8760) annualized per-trade) — informational only

DSR aggregate uses sigma_sr = std(per-fold Sharpe) per Q7 (Bailey eq. 12).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.analytics.dsr import compute_dsr, compute_returns
from src.risk.trade_history import TradeRecord


# Annualization factor: sqrt(365 * 24) для 24/7 crypto 1H bars.
# Per Q6 verdict — fixed constant, NOT derived from trade frequency (circular).
_ANNUALIZATION_FACTOR = float(np.sqrt(8760))


def format_wfa_report(
    *,
    runner_result: dict[str, Any],
    trades_for_dsr: list[TradeRecord],
    mc_p_value: float,
    gate_result: dict[str, Any],
) -> dict[str, Any]:
    """Format structured WFA report.

    Routes 3 distinct Sharpe series correctly + computes DSR aggregate.

    Args:
        runner_result: dict from WalkForwardRunner.run() с 'folds' + 'aggregate'.
        trades_for_dsr: aggregated TradeRecord list from all folds для DSR.
        mc_p_value: MC permutation p-value.
        gate_result: dict from evaluate_acceptance_gate().

    Returns:
        Structured report dict с per-series Sharpe + DSR + gate details.
    """
    folds = runner_result.get("folds", [])
    aggregate = runner_result.get("aggregate", {})

    # Series 1: bar-returns Sharpe per fold
    bar_returns_sharpe_per_fold = [
        f.get("oos_metrics", {}).get("Sharpe Ratio", 0.0) for f in folds
    ]

    # Series 2: per-trade Sharpe (DSR internal)
    per_trade_sharpe: float = math.nan
    if trades_for_dsr:
        returns = compute_returns(trades_for_dsr, use_log=True)
        finite_returns = [r for r in returns if math.isfinite(r)]
        if len(finite_returns) >= 2:
            mean = sum(finite_returns) / len(finite_returns)
            var = sum((r - mean) ** 2 for r in finite_returns) / (len(finite_returns) - 1)
            if var > 0:
                per_trade_sharpe = mean / math.sqrt(var)

    # Series 3: display Sharpe (per-trade × sqrt(8760))
    display_sharpe = (
        per_trade_sharpe * _ANNUALIZATION_FACTOR
        if math.isfinite(per_trade_sharpe)
        else math.nan
    )

    # DSR aggregate (n_trials=K, sigma_sr from per-fold Sharpes per Q7)
    dsr_aggregate: float = math.nan
    dsr_per_fold: list[float] = []
    fold_oos_sharpes = aggregate.get("fold_oos_sharpes", [])
    if trades_for_dsr and len(fold_oos_sharpes) >= 2:
        sigma_sr = float(np.std(fold_oos_sharpes, ddof=1))
        dsr_aggregate = compute_dsr(
            trades_for_dsr,
            n_trials=len(fold_oos_sharpes),
            sigma_sr=sigma_sr,
        )

    # Per-fold DSR (placeholder — DataFrame→TradeRecord conversion deferred)
    for _ in folds:
        dsr_per_fold.append(math.nan)

    return {
        "bar_returns_sharpe_per_fold": bar_returns_sharpe_per_fold,
        "per_trade_sharpe": per_trade_sharpe,
        "display_sharpe": display_sharpe,
        "display_sharpe_annualization_factor": _ANNUALIZATION_FACTOR,
        "dsr_aggregate": dsr_aggregate,
        "dsr_per_fold": dsr_per_fold,
        "mc_p_value": mc_p_value,
        "acceptance_gate": gate_result,
        "k_folds": aggregate.get("k_folds", 0),
    }
