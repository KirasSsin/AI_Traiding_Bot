"""Tests for MC block bootstrap (autocorrelation-preserving secondary).

Sprint 10 Q3 (ADR 0015 secondary method, block 20-50 bars).
"""
from __future__ import annotations

import math

import numpy as np
from src.backtest.mc_permutation import block_bootstrap_p_value


def test_returns_valid_p_value_in_range() -> None:
    """block_bootstrap_p_value returns float in [0, 1] for valid input."""
    returns = np.array([0.01] * 100)
    p = block_bootstrap_p_value(returns, n_iterations=200, block_size=20, seed=42)
    assert isinstance(p, float)
    assert 0.0 <= p <= 1.0


def test_block_size_affects_resampling() -> None:
    """Different block sizes produce different p-values на autocorrelated data."""
    rng = np.random.default_rng(42)
    n = 200
    returns = np.zeros(n)
    for t in range(1, n):
        returns[t] = 0.5 * returns[t - 1] + rng.normal(0.001, 0.01)

    p_block20 = block_bootstrap_p_value(returns, n_iterations=2000, block_size=20, seed=42)
    p_block50 = block_bootstrap_p_value(returns, n_iterations=2000, block_size=50, seed=42)
    assert p_block20 != p_block50


def test_seed_reproducibility() -> None:
    """Same seed → identical p (reproducibility)."""
    returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015, 0.008, -0.003, 0.012])
    p1 = block_bootstrap_p_value(returns, n_iterations=2000, block_size=3, seed=42)
    p2 = block_bootstrap_p_value(returns, n_iterations=2000, block_size=3, seed=42)
    assert p1 == p2


def test_empty_returns_returns_nan() -> None:
    """Empty returns array → NaN p (defensive)."""
    p = block_bootstrap_p_value(np.array([]), n_iterations=2000, block_size=20, seed=42)
    assert math.isnan(p)
