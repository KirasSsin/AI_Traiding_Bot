"""Deflated Sharpe Ratio (Bailey & López de Prado, 2014).

Sprint 9 Q3 B2.

DSR adjusts vanilla Sharpe ratio для:
- Sample length (small N inflates variance estimate)
- Skewness + kurtosis of returns (non-normality penalty)
- Multiple testing bias (если N strategies tested — supplied as `n_trials`)

Formula reference:
- Bailey, D.H., López de Prado, M. (2014) "The Deflated Sharpe Ratio: Correcting
  for Selection Bias, Backtest Overfitting and Non-Normality"
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551

This module operates on `TradeRecord` array (closed trades с exit_ts).
No look-ahead: each TradeRecord's pnl_pct is realized at exit_ts.

quant-stats-reviewer mandatory before merge — verify formula correctness +
annualization factor + log-vs-simple return choice + look-ahead invariant.
"""
from __future__ import annotations

import math

from scipy import stats

from src.risk.trade_history import TradeRecord


def compute_returns(trades: list[TradeRecord], *, use_log: bool = True) -> list[float]:
    """Extract per-trade returns from TradeRecord list.

    Default = log returns (additive across trades, suitable для compounding).
    Set use_log=False для simple returns (pnl_pct directly).

    Edge case: pnl_pct == -1.0 (total loss) → log return = -inf.
    """
    out: list[float] = []
    for t in trades:
        pct = float(t.pnl_pct)
        if use_log:
            # log(1 + r) — defined for r > -1; total loss → -inf
            if pct <= -1.0:
                out.append(-math.inf)
                continue
            out.append(math.log(1.0 + pct))
        else:
            out.append(pct)
    return out


def compute_dsr(
    trades: list[TradeRecord],
    *,
    benchmark_sharpe: float = 0.0,
    n_trials: int = 1,
    use_log: bool = True,
) -> float:
    """Compute Deflated Sharpe Ratio.

    Returns NaN if:
    - N=0 (no trades)
    - N=1 (variance undefined)
    - All returns identical (variance=0)
    - denom_inner ≤ 0 (skew × sharpe combo creates undefined sqrt arg)

    Args:
        trades: closed TradeRecord list (exit_ts populated).
        benchmark_sharpe: prior Sharpe target (default 0).
        n_trials: number of strategies tested (multiple-testing penalty).
        use_log: log returns если True (default), simple if False.

    Returns:
        DSR scalar в (0, 1) interpreted as Φ-CDF probability that
        observed Sharpe exceeds benchmark after adjusting для selection bias.
    """
    returns = compute_returns(trades, use_log=use_log)
    n = len(returns)
    if n < 2:
        return math.nan

    # Filter -inf if total-loss trade present (would corrupt mean/var)
    finite_returns = [r for r in returns if math.isfinite(r)]
    if len(finite_returns) < 2:
        return math.nan

    mean = sum(finite_returns) / len(finite_returns)
    var = sum((r - mean) ** 2 for r in finite_returns) / (len(finite_returns) - 1)
    if var <= 0:
        return math.nan
    std = math.sqrt(var)
    sharpe = mean / std

    # Skewness + kurtosis of returns (Fisher = excess kurtosis, bias-corrected)
    skew = float(stats.skew(finite_returns, bias=False))
    kurt = float(stats.kurtosis(finite_returns, bias=False, fisher=True))

    # Expected max Sharpe across n_trials (Bailey & López de Prado 2014, eq. 12)
    # E[max SR_n] ≈ benchmark + ((1 - γ) * Φ⁻¹(1 - 1/n) + γ * Φ⁻¹(1 - 1/(n × e)))
    # γ = Euler-Mascheroni constant ≈ 0.5772
    if n_trials <= 1:
        sharpe_star = benchmark_sharpe
    else:
        gamma = 0.5772156649
        z1 = float(stats.norm.ppf(1.0 - 1.0 / n_trials))
        z2 = float(stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e)))
        sharpe_star = benchmark_sharpe + (1.0 - gamma) * z1 + gamma * z2

    # DSR formula (Bailey & López de Prado 2014, eq. 13):
    # DSR = Φ((SR - SR*) × √(n - 1) / √(1 - skew × SR + (kurt - 1)/4 × SR²))
    denom_inner = 1.0 - skew * sharpe + (kurt - 1.0) / 4.0 * sharpe**2
    if denom_inner <= 0:
        return math.nan
    denom = math.sqrt(denom_inner)
    z_dsr = (sharpe - sharpe_star) * math.sqrt(len(finite_returns) - 1) / denom
    return float(stats.norm.cdf(z_dsr))
