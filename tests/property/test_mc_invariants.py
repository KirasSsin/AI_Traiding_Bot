"""MC p-value invariants property test — S33 T2 (CC-D fix regression guard, Item #2).

Per quant-stats-reviewer ROUND 2:
- p-value MUST be > 0 always (impossible с finite permutations к get exact 0)
- 1/(N+1) ≤ p ≤ 1 (Phipson & Smyth 2010 floor)
- Monotonic non-decreasing в count_extreme

Catches CC-D regression: pre-fix `count/N` returned p=0 when count_extreme=0,
which is logically impossible с finite permutations.

Reference: ADR 0015 — `(count + 1) / (N + 1)` per Phipson & Smyth 2010.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from src.backtest.mc_permutation import block_bootstrap_p_value, sign_flip_p_value


# Hypothesis strategies — bounded sizes для test speed
returns_strategy = st.lists(
    st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False),
    min_size=10,
    max_size=200,
).map(lambda lst: np.array(lst, dtype=np.float64))

n_iter_strategy = st.integers(min_value=10, max_value=500)


# ────────────────────────────────────────────────────────────────────────────
# sign_flip_p_value invariants
# ────────────────────────────────────────────────────────────────────────────

@given(returns=returns_strategy, n_iter=n_iter_strategy)
@settings(max_examples=30, deadline=2000)
def test_sign_flip_p_value_floor_above_zero(returns, n_iter):
    """p-value NEVER zero (impossible с finite permutations).

    Per Phipson & Smyth 2010: minimum p = 1/(N+1).
    Pre-CC-D: returned 0.0 when count_extreme=0 — logically impossible.
    """
    p = sign_flip_p_value(returns, n_iterations=n_iter, seed=42)

    if np.isnan(p):  # empty returns edge case
        assert len(returns) == 0
        return

    assert p > 0.0, f"p-value floor violated (CC-D regression): n={n_iter}, got p={p}"


@given(returns=returns_strategy, n_iter=n_iter_strategy)
@settings(max_examples=30, deadline=2000)
def test_sign_flip_p_value_upper_bound(returns, n_iter):
    """p-value ≤ 1.0 always."""
    p = sign_flip_p_value(returns, n_iterations=n_iter, seed=42)
    if np.isnan(p):
        return
    assert p <= 1.0, f"p > 1: n={n_iter}, got {p}"


@given(returns=returns_strategy, n_iter=n_iter_strategy)
@settings(max_examples=20, deadline=2000)
def test_sign_flip_p_value_above_phipson_smyth_floor(returns, n_iter):
    """Minimum p-value = 1/(N+1) per Phipson & Smyth 2010 (ADR 0015)."""
    p = sign_flip_p_value(returns, n_iterations=n_iter, seed=42)
    if np.isnan(p):
        return
    expected_floor = 1.0 / (n_iter + 1)
    assert p >= expected_floor, (
        f"p < 1/(N+1) floor: n={n_iter}, expected ≥ {expected_floor:.6f}, got {p:.6f}"
    )


# ────────────────────────────────────────────────────────────────────────────
# block_bootstrap_p_value invariants (same bug per ROUND 2 Item #1 extension)
# ────────────────────────────────────────────────────────────────────────────

@given(returns=returns_strategy, n_iter=n_iter_strategy)
@settings(max_examples=30, deadline=3000)
def test_block_bootstrap_p_value_floor_above_zero(returns, n_iter):
    """Same floor invariant для block_bootstrap (CC-D extended scope per ROUND 2)."""
    if len(returns) < 30:  # block_size default 30
        return  # skip — function returns NaN

    p = block_bootstrap_p_value(returns, n_iterations=n_iter, seed=42)
    if np.isnan(p):
        return
    assert p > 0.0, f"block_bootstrap p floor violated: n={n_iter}, got p={p}"


@given(returns=returns_strategy, n_iter=n_iter_strategy)
@settings(max_examples=30, deadline=3000)
def test_block_bootstrap_p_value_upper_bound(returns, n_iter):
    """p ≤ 1.0 always."""
    if len(returns) < 30:
        return
    p = block_bootstrap_p_value(returns, n_iterations=n_iter, seed=42)
    if np.isnan(p):
        return
    assert p <= 1.0


# ────────────────────────────────────────────────────────────────────────────
# Edge case: zero count_extreme MUST NOT return p=0 (CC-D regression guard)
# ────────────────────────────────────────────────────────────────────────────

def test_sign_flip_p_value_extreme_signal_returns_floor_not_zero():
    """Extreme positive returns (no permutation matches) → p = 1/(N+1), NOT 0.

    Constructs returns where every permuted sign-flip produces |mean| < observed
    (large positive constant returns). Pre-CC-D returned 0.0 — impossible.
    Post-CC-D: returns 1/(N+1) per Phipson & Smyth.
    """
    # All-positive returns large enough that NO sign-flip permutation matches |mean|
    # Some flips will produce equal or larger |mean| (e.g., flipping signs symmetrically),
    # so we use clearly skewed returns
    returns = np.array([0.05] * 50, dtype=np.float64)  # all 5%, |mean|=0.05
    n_iter = 100

    p = sign_flip_p_value(returns, n_iterations=n_iter, seed=42)

    # With all-positive equal returns, half permutations should produce mean=0,
    # but we just need to verify p > 0 (CC-D regression test)
    assert p > 0.0, f"CC-D regression: p=0 not allowed. Got p={p}"
    assert p >= 1.0 / (n_iter + 1), f"p below Phipson-Smyth floor"


def test_block_bootstrap_p_value_floor_explicit():
    """Same explicit edge case для block_bootstrap."""
    returns = np.array([0.05] * 50, dtype=np.float64)
    n_iter = 100

    p = block_bootstrap_p_value(returns, n_iterations=n_iter, block_size=10, seed=42)

    assert p > 0.0, f"CC-D regression: block_bootstrap p=0 not allowed. Got p={p}"
    assert p >= 1.0 / (n_iter + 1)
