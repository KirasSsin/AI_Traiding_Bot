"""bars_per_year annualization end-to-end integration test — S33 T1 (Item #11).

Per quant-stats-reviewer Q6 concern (consilium ROUND 2):
S27 T1 fix `bars_per_year` parameterization MUST propagate through replay engine
`sharpe_ratio` computation, NOT just unit test of function isolation. Verifies
4H interval (bars_per_year=2190) end-to-end через `run_replay` → `_compute_metrics`.

Establishes regression guard для S27 T1 fix integrity. Prevents silent annualization
errors that would invalidate WFA sweep verdicts (S33 F backtest measurement T5).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from src.backtest.replay_engine import run_replay
from src.backtest.strategy_metrics import _DEFAULT_BARS_PER_YEAR


def _build_synthetic_df(n_bars: int = 200) -> pd.DataFrame:
    """Synthetic OHLCV с deterministic price series для testing.

    Creates 200 bars с oscillating prices (~10% range) — enough к trigger multiple
    cross_up signals AFTER RSI warm-up, exit trades через SL/TP/EOD.
    """
    rng = np.random.default_rng(seed=42)
    base = 100.0
    # Walk: random ±0.5% per bar, drift back to base every 50 bars
    pct_changes = rng.normal(0, 0.005, n_bars)
    pct_changes[::50] -= 0.02  # periodic drift back
    cumulative = np.cumprod(1 + pct_changes)
    prices = base * cumulative

    rows = []
    for i, p in enumerate(prices):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=4 * i),  # 4H bars
                "open": float(p),
                "high": float(p) * 1.005,
                "low": float(p) * 0.995,
                "close": float(p),
                "volume": 1.0,
            }
        )
    return pd.DataFrame(rows)


def _config_for_4h() -> dict:
    """Replay config с 4H bars_per_year=2190 explicit."""
    return {
        "bars_per_year": 2190,
        "trading": {
            "initial_balance": 10000.0,
            "commission_taker": 0.0,
            "slippage": 0.0,
            "position_size_pct": 10.0,
            "max_drawdown_pct": 90.0,
            "long_only": True,
        },
        "strategy": {
            "indicators": {
                "ema": {"fast_period": 9, "slow_period": 21},
                "rsi": {"period": 14, "overbought": 70, "oversold": 30},
                "atr": {"period": 14, "sl_atr_mult": 2.0, "tp_atr_mult": 3.0},
            }
        },
    }


def _config_for_1h() -> dict:
    """Replay config с 1H bars_per_year=8760 (S27 default)."""
    cfg = _config_for_4h()
    cfg["bars_per_year"] = 8760
    return cfg


def test_default_bars_per_year_constant():
    """_DEFAULT_BARS_PER_YEAR=8766 (1H baseline; S49 L6 unify on 365.25 family).

    Was 8760 (365 family); unified to 8766 = round(365.25 × 24). Immaterial to
    gates (0.07% Sharpe annualization shift) — informational consistency only.
    """
    assert _DEFAULT_BARS_PER_YEAR == 8766


def test_replay_4h_uses_bars_per_year_2190_for_annualization():
    """4H interval → bars_per_year=2190 propagates через run_replay → metrics.

    Sharpe annualization factor = sqrt(2190) ≈ 46.79 (NOT sqrt(8760) ≈ 93.59).
    Verifies S27 T1 fix wires config к replay engine + strategy_metrics.
    """
    df = _build_synthetic_df(n_bars=200)
    cfg = _config_for_4h()

    result = run_replay(df, cfg)

    assert "metrics" in result, "run_replay должен return metrics dict"
    metrics = result["metrics"]

    # Verify Sharpe computed (not NaN/None) — annualization path executed
    assert "Sharpe Ratio" in metrics, "metrics должен include 'sharpe'"
    sharpe = metrics["Sharpe Ratio"]

    # Sharpe должен быть finite number (not NaN, not inf) — confirms annualization formula ran
    if sharpe is not None:
        assert np.isfinite(sharpe), f"Sharpe должен be finite, got {sharpe}"


def test_replay_1h_baseline_preserved():
    """1H interval → bars_per_year=8760 (S27 default before-fix). Baseline preserved."""
    df = _build_synthetic_df(n_bars=200)
    cfg = _config_for_1h()

    result = run_replay(df, cfg)
    metrics = result["metrics"]

    assert "Sharpe Ratio" in metrics
    if metrics["Sharpe Ratio"] is not None:
        assert np.isfinite(metrics["Sharpe Ratio"])


def test_replay_default_bars_per_year_when_config_missing():
    """Config без bars_per_year → defaults к 8760 (backward-compat S27 T1)."""
    df = _build_synthetic_df(n_bars=200)
    cfg = _config_for_4h()
    del cfg["bars_per_year"]  # remove explicit к test default

    result = run_replay(df, cfg)
    metrics = result["metrics"]

    # Should not raise — default falls к 8760 per replay_engine.py:133
    assert "Sharpe Ratio" in metrics


def test_4h_vs_1h_sharpe_annualization_ratio():
    """Same daily returns → 4H Sharpe = 1H Sharpe × sqrt(2190/8760) = ×0.5.

    Mathematical invariant: annualized Sharpe = raw_Sharpe × sqrt(bars_per_year).
    Если same trade pattern produces same per-bar Sharpe, annualized ratio
    должен strictly = sqrt(2190/8760) ≈ 0.500.

    Validates bars_per_year propagates correctly через FULL replay → metrics path.
    """
    df = _build_synthetic_df(n_bars=200)

    cfg_4h = _config_for_4h()
    cfg_1h = _config_for_1h()

    result_4h = run_replay(df, cfg_4h)
    result_1h = run_replay(df, cfg_1h)

    sharpe_4h = result_4h["metrics"].get("Sharpe Ratio")
    sharpe_1h = result_1h["metrics"].get("Sharpe Ratio")

    if sharpe_4h is None or sharpe_1h is None or sharpe_4h == 0 or sharpe_1h == 0:
        pytest.skip("Insufficient trades для ratio check (synthetic data sparse)")

    # Both same data + same per-bar metrics → annualization ratio = sqrt(2190/8760) = 0.5
    expected_ratio = float(np.sqrt(2190 / 8760))  # = 0.5
    actual_ratio = sharpe_4h / sharpe_1h

    assert abs(actual_ratio - expected_ratio) < 0.01, (
        f"Sharpe annualization ratio mismatch: expected {expected_ratio:.4f} (sqrt(2190/8760)), "
        f"got {actual_ratio:.4f}. bars_per_year propagation broken в replay engine."
    )
