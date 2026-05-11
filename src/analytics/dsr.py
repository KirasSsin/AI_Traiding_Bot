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
look-ahead invariant + sigma_sr usage (S10 Q7).
"""

from __future__ import annotations

import math
from typing import Any

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
    sigma_sr: float | None = None,
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
        sigma_sr: cross-trial Sharpe std deviation (REQUIRED if n_trials > 1).
                  Caller computes sigma_sr = std([fold_sharpe_1, ..., fold_sharpe_K]).
                  S10 closes S9 NotImplementedError per ADR 0025 + pre-s10-backlog Q7.
        use_log: log returns если True (default), simple if False.

    Returns:
        DSR scalar в (0, 1) interpreted as Φ-CDF probability that
        observed Sharpe exceeds benchmark after adjusting для selection bias.

    Raises:
        ValueError: n_trials < 1 (invalid) or n_trials > 1 без sigma_sr.
    """
    if n_trials < 1:
        raise ValueError(f"n_trials must be >= 1, got {n_trials}")
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

    # Skewness + kurtosis of returns. PEARSON kurtosis (fisher=False) per
    # Bailey & López de Prado 2014 eq. 13 (gamma_4 = total kurtosis, NOT excess).
    # For Normal distribution Pearson=3 → (3-1)/4 = 0.5 recovers Lo (2002)
    # Sharpe variance (1 + SR²/2)/(T-1). Using fisher=True (excess) would give
    # (0-1)/4 = -0.25 — systematically wrong.
    skew = float(stats.skew(finite_returns, bias=False))
    kurt = float(stats.kurtosis(finite_returns, bias=False, fisher=False))

    # Bailey & López de Prado 2014 eq. 12: E[max SR_n] для n_trials > 1.
    # Closes S9 NotImplementedError per ADR 0025 + pre-s10-backlog.md Q7.
    # E[max SR] = mu_SR + sigma_SR × ((1-γ)*Φ⁻¹(1-1/N) + γ*Φ⁻¹(1-1/(N×e)))
    if n_trials > 1:
        if sigma_sr is None:
            raise ValueError(
                "compute_dsr: sigma_sr REQUIRED when n_trials > 1. "
                "Caller must supply std of Sharpes across trials. See ADR 0025."
            )
        if math.isnan(sigma_sr):
            # S36 T6 quant-stats-reviewer C1 hardening: NaN<0 evaluates False в Python,
            # so без explicit isnan check NaN sigma_sr would silently propagate через
            # sharpe_star → produce silent NaN DSR без exception/log. Defense-in-depth
            # для future direct callers (donchian_runner already guards at call-site).
            raise ValueError(
                "compute_dsr: sigma_sr cannot be NaN when n_trials > 1. "
                "ADR 0056: cross_trial < 3 entries → use n_trials=1 OR mark UNDERPOWERED."
            )
        if sigma_sr < 0:
            # std deviation is non-negative by definition. Negative value would
            # produce sharpe_star < benchmark (DSR inflated rather than penalized).
            # Per quant-stats-reviewer T4 concern.
            raise ValueError(f"compute_dsr: sigma_sr must be >= 0, got {sigma_sr}")
        gamma = 0.5772156649  # Euler-Mascheroni
        z1 = float(stats.norm.ppf(1.0 - 1.0 / n_trials))
        z2 = float(stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e)))
        sharpe_star = benchmark_sharpe + sigma_sr * ((1.0 - gamma) * z1 + gamma * z2)
    else:
        sharpe_star = benchmark_sharpe

    # DSR formula (Bailey & López de Prado 2014, eq. 13):
    # DSR = Φ((SR - SR*) × √(n - 1) / √(1 - skew × SR + (kurt - 1)/4 × SR²))
    # where kurt = Pearson (total) kurtosis, NOT excess (S9 BLOCKER fix preserved).
    denom_inner = 1.0 - skew * sharpe + (kurt - 1.0) / 4.0 * sharpe**2
    if denom_inner <= 0:
        return math.nan
    denom = math.sqrt(denom_inner)
    z_dsr = (sharpe - sharpe_star) * math.sqrt(len(finite_returns) - 1) / denom
    return float(stats.norm.cdf(z_dsr))


def compute_dsr_with_status(
    *,
    trades: list[TradeRecord],
    n_trials: int = 1,
    sigma_sr: float | None = None,
    benchmark_sharpe: float = 0.0,
    use_log: bool = True,
) -> dict[str, Any]:
    """ADR 0056 — DSR с n_trades-threshold status flag.

    Returns dict с keys:
      - dsr (float): NaN если n_trades < 10
      - status (str): "INSUFFICIENT_TRADES" | "UNDERPOWERED" | "GATE_ELIGIBLE"
      - n_trades (int): closed trade count

    Per ADR 0056 thresholds:
      - n_trades < 10:   DSR=NaN, status=INSUFFICIENT_TRADES
      - 10 <= n < 30:    DSR computed, status=UNDERPOWERED
      - n >= 30:         DSR computed, status=GATE_ELIGIBLE

    Args same semantics as `compute_dsr` (delegates для DSR computation).
    """
    n = len(trades)
    if n < 10:
        return {"dsr": float("nan"), "status": "INSUFFICIENT_TRADES", "n_trades": n}
    dsr = compute_dsr(
        trades,
        benchmark_sharpe=benchmark_sharpe,
        n_trials=n_trials,
        sigma_sr=sigma_sr,
        use_log=use_log,
    )
    status = "UNDERPOWERED" if n < 30 else "GATE_ELIGIBLE"
    return {"dsr": dsr, "status": status, "n_trades": n}
