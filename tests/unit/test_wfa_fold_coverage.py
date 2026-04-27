"""WFA fold coverage pre-run validation — S33 T4 (Item #10).

Per trading-logic-reviewer ROUND 2:
SOL Bybit listing date may give fewer 4H bars чем BTC. Silent fold-skip risk
если total_bars < required. Pre-run validation raises ValueError с symbol context.

Per consilium ROUND 2 Item #10: prevents misleading N < 5 result для SOL.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtest.walk_forward import WindowSplitter, WalkForwardRunner


def _dummy_replay(df: pd.DataFrame, config: dict) -> dict:
    """Stub replay function для WFA testing — returns minimal valid result."""
    return {
        "metrics": {"Sharpe Ratio": 0.0},
        "trades_df": pd.DataFrame(),
        "equity_df": pd.DataFrame(),
    }


def test_wfa_raises_on_insufficient_bars_with_symbol_context():
    """Per Item #10: error message includes symbol context (defaults к 'unknown' если не passed)."""
    splitter = WindowSplitter(train_bars=1000, test_bars=250, k_folds=5, embargo_bars=20)
    runner = WalkForwardRunner(splitter=splitter, replay_fn=_dummy_replay)

    # Required: 1000 + 20 + 5*250 = 2270 bars
    short_df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=2000, freq="4h"),
        "open": [100.0] * 2000,
        "high": [101.0] * 2000,
        "low": [99.0] * 2000,
        "close": [100.0] * 2000,
        "volume": [1.0] * 2000,
    })

    with pytest.raises(ValueError, match="insufficient data"):
        runner.run(df=short_df, config={"strategy": {"indicators": {"ema": {"fast_period": 9, "slow_period": 21}, "rsi": {"period": 14, "overbought": 70, "oversold": 30}, "atr": {"period": 14, "sl_atr_mult": 2.0, "tp_atr_mult": 3.0}}}}, symbol="SOLUSDT")


def test_wfa_error_message_contains_symbol_when_provided():
    """Symbol param included в error message для operator visibility (per Item #10)."""
    splitter = WindowSplitter(train_bars=1000, test_bars=250, k_folds=5, embargo_bars=20)
    runner = WalkForwardRunner(splitter=splitter, replay_fn=_dummy_replay)

    short_df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=500, freq="4h"),
        "open": [100.0] * 500, "high": [101.0] * 500, "low": [99.0] * 500,
        "close": [100.0] * 500, "volume": [1.0] * 500,
    })

    with pytest.raises(ValueError) as exc_info:
        runner.run(df=short_df, config={}, symbol="SOLUSDT")

    assert "SOLUSDT" in str(exc_info.value), f"Symbol must appear in error: {exc_info.value}"


def test_wfa_window_splitter_4h_window_train_1000_test_250():
    """Per CC6 (b) consensus: WFA 4H window train=1000/test=250 K=5 = ~3.3y OOS coverage."""
    splitter = WindowSplitter(train_bars=1000, test_bars=250, k_folds=5, embargo_bars=20)
    # Min required: 1000 + 20 + 5*250 = 2270 bars
    # 4H bars: 2270 / 6 ≈ 378 days ≈ 1y minimum
    # Full Bybit BTC 4H ~10500 bars (4.81y) — easily fits

    valid_df_lengths = [2270, 5000, 10500]
    for n in valid_df_lengths:
        df_lengths = list(splitter.split(total_bars=n))
        assert len(df_lengths) == 5, f"K=5 folds expected для {n} bars, got {len(df_lengths)}"
