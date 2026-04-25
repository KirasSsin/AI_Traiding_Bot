"""Tests for MC sign-flip permutation test.

Sprint 10 Q3 (per pre-s10-backlog.md verdict — flip per-trade pnl_pct sign).
ADR 0015: N=2000 default, p ≤ 0.05 acceptance gate.
"""
from __future__ import annotations

import math

import numpy as np
from src.backtest.mc_permutation import sign_flip_p_value


def test_strong_positive_returns_yield_low_p() -> None:
    """Consistent +1% returns → very low p-value (significant edge)."""
    returns = np.array([0.01] * 100)
    p = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    assert p < 0.05


def test_zero_mean_returns_yield_high_p() -> None:
    """Symmetric returns (mean ≈ 0) → high p-value (no edge)."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0, 0.01, 100)
    p = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    assert p > 0.05


def test_p_value_in_unit_interval() -> None:
    """p-value always в [0, 1]."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.01, 50)
    p = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    assert 0.0 <= p <= 1.0


def test_seed_reproducibility() -> None:
    """Same seed → identical p-value (reproducibility)."""
    returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015])
    p1 = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    p2 = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    assert p1 == p2


def test_empty_returns_returns_nan() -> None:
    """Empty returns array → NaN p-value (defensive)."""
    p = sign_flip_p_value(np.array([]), n_iterations=2000, seed=42)
    assert math.isnan(p)
