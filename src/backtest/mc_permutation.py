"""Monte Carlo permutation tests для strategy significance.

Sprint 10 Q3 (per pre-s10-backlog.md verdict + ADR 0015).

sign_flip_p_value: per-trade pnl_pct sign-flip null hypothesis test.
- Test statistic: mean(returns) — proxy для Sharpe sign
- p-value: fraction of permuted statistics ≥ observed
- N=2000 default per ADR 0015

block_bootstrap_p_value: secondary method preserves autocorrelation (T6).

S39 T11 F8 — single source of truth for block_size: MC_BLOCK_SIZE = 20.
ADR 0015 range 20-50; live_trade_reporter chose 20 (smaller blocks → more
permutations → tighter p-value resolution для small n).
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

# S39 T11 F8 — canonical MC block size (ADR 0015 range 20-50)
MC_BLOCK_SIZE: int = 20


def sign_flip_p_value(
    returns: npt.NDArray[np.float64],
    *,
    n_iterations: int = 2000,
    seed: int | None = 42,
) -> float:
    """Sign-flip permutation test.

    Null: returns symmetric around 0 (no directional edge).
    Test stat: mean(returns).
    p = fraction of N permutations с |mean(perm)| >= |mean(observed)| (two-sided).

    Args:
        returns: per-trade returns array (np.float64).
        n_iterations: permutation count (ADR 0015 default 2000).
        seed: RNG seed для reproducibility. S27 T5: default 42 (was None pre-fix).
            Non-deterministic default produced inconsistent audit p-values
            across runs of formulas_audit_v1.json. Pass `seed=None` explicitly
            если требуется non-deterministic randomness.

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

    # S33 T2 (CC-D fix): (count + 1) / (N + 1) per Phipson & Smyth 2010 / ADR 0015.
    # Avoids p=0 (logically impossible с finite permutations).
    # Minimum p = 1/(N+1), не 0.
    return float((count_extreme + 1) / (n_iterations + 1))


def block_bootstrap_p_value(
    returns: npt.NDArray[np.float64],
    *,
    n_iterations: int = 2000,
    block_size: int = MC_BLOCK_SIZE,
    seed: int | None = 42,
) -> float:
    """Block bootstrap permutation test (preserves autocorrelation).

    Per ADR 0015 secondary method. Resamples blocks of `block_size` bars,
    тех concatenates к length(returns) sequence. Tests if observed mean
    significantly differs from bootstrap distribution.

    M4 (S49) WARNING — METHOD CAVEAT: this resample-with-replacement from the
    OBSERVED returns measures the SAMPLING VARIABILITY of the observed mean, NOT
    directional-edge significance versus a no-edge null. A correct edge null
    requires block SIGN-FLIP (see SignFlipTest / sign_flip_p_value, the gate).
    This metric is secondary/informational only. DO NOT promote it to a verdict
    gate without switching to the sign-flip (edge-null) method.

    Args:
        returns: per-trade returns array.
        n_iterations: bootstrap iterations (ADR 0015 default 2000).
        block_size: block length в bars (ADR 0015 range 20-50, default MC_BLOCK_SIZE=20).
        seed: RNG seed.

    Returns:
        p-value в [0, 1], NaN if returns empty или block_size > len(returns).
    """
    if len(returns) == 0 or block_size > len(returns):
        return math.nan

    n = len(returns)
    n_blocks = (n + block_size - 1) // block_size  # ceil
    observed = float(np.abs(np.mean(returns)))
    rng = np.random.default_rng(seed)

    count_extreme = 0
    for _ in range(n_iterations):
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        sampled = np.concatenate([returns[s : s + block_size] for s in starts])[:n]
        if abs(float(np.mean(sampled))) >= observed:
            count_extreme += 1

    # S33 T2 (CC-D fix extended scope ROUND 2 Item #1): (count+1)/(N+1) per Phipson & Smyth 2010.
    # Same fix as sign_flip_p_value — avoids p=0 (impossible с finite permutations).
    return float((count_extreme + 1) / (n_iterations + 1))
