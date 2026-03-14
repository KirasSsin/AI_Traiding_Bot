import numpy as np
import pytest
from src.core.math_engine import MathEngine

def test_hurst_random_walk():
    # A random walk should have a Hurst exponent near 0.5
    np.random.seed(42)
    random_changes = np.random.randn(1000)
    random_walk = np.cumsum(random_changes)
    h = MathEngine.hurst_exponent(random_walk, max_lag=20)
    print(f"Random Walk Hurst: {h}")
    # It might not be exactly 0.5 due to small sample size, but should be around it
    assert 0.4 < h < 0.6, "Hurst for random walk should be ~0.5"

def test_hurst_mean_reverting():
    # A mean reverting series (e.g. sine wave with noise)
    np.random.seed(42)
    t = np.linspace(0, 1000, 1000) # Increased frequency to oscillate quickly
    mean_reverting = np.sin(t) + np.random.randn(1000) * 0.1
    h = MathEngine.hurst_exponent(mean_reverting, max_lag=20)
    print(f"Mean Reverting Hurst: {h}")
    assert h < 0.5, "Hurst for mean-reverting should be < 0.5"

def test_cvar():
    # Simple normal distribution
    np.random.seed(42)
    returns = np.random.normal(0, 1, 10000)
    # Expected shortfall for standard normal at 95% is ~2.06
    cvar = MathEngine.calc_cvar(returns, 0.95)
    print(f"CVaR 95%: {cvar}")
    assert cvar < -1.5, "CVaR should represent the tail loss mean"

def test_fractional_kelly():
    win_rate = 0.55
    win_loss_ratio = 1.2
    # Kelly = 0.55 - (0.45 / 1.2) = 0.55 - 0.375 = 0.175
    # Half Kelly = 0.175 * 0.5 = 0.0875
    k = MathEngine.fractional_kelly(win_rate, win_loss_ratio, 0.5)
    assert abs(k - 0.0875) < 0.001
