"""Monte Carlo permutation tests для strategy significance.

Sprint 10 Q3 (per pre-s10-backlog.md verdict + ADR 0015).

sign_flip_p_value: per-trade pnl_pct sign-flip null hypothesis test.
- Test statistic: mean(returns) — proxy для Sharpe sign
- p-value: fraction of permuted statistics ≥ observed
- N=2000 default per ADR 0015

block_bootstrap_p_value: secondary method preserves autocorrelation (T6).
"""
from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt


def sign_flip_p_value(
    returns: npt.NDArray[np.float64],
    *,
    n_iterations: int = 2000,
    seed: int | None = None,
) -> float:
    """Sign-flip permutation test.

    Null: returns symmetric around 0 (no directional edge).
    Test stat: mean(returns).
    p = fraction of N permutations с |mean(perm)| >= |mean(observed)| (two-sided).

    Args:
        returns: per-trade returns array (np.float64).
        n_iterations: permutation count (ADR 0015 default 2000).
        seed: RNG seed для reproducibility.

    Returns:
        p-value в [0, 1], NaN if returns empty.
    """
    if len(returns) == 0:
        return math.nan

    observed = float(np.abs(np.mean(returns)))
    rng = np.random.default_rng(seed)

    count_extreme = 0
    for _ in range(n_iterations):
        signs = rng.choice([-1.0, 1.0], size=len(returns))
        permuted = returns * signs
        if abs(float(np.mean(permuted))) >= observed:
            count_extreme += 1

    return float(count_extreme / n_iterations)
