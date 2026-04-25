"""Pre-flight NaN assertion: data integrity check before WFA (CC4 per ADR 0028)."""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest


def test_load_ohlcv_passes_when_dropna_yields_above_90pct() -> None:
    """Healthy OHLCV (no NaN) passes pre-flight."""
    from src import __main__ as cli

    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=100, freq="1h"),
        "open": [50000.0 + i for i in range(100)],
        "high": [50010.0 + i for i in range(100)],
        "low": [49990.0 + i for i in range(100)],
        "close": [50005.0 + i for i in range(100)],
        "volume": [1.0] * 100,
    })

    with patch("src.__main__.load_market_data", return_value=df):
        result = cli._load_ohlcv(symbol="BTCUSDT", start="2024-01-01", end="2024-01-05")

    assert len(result) == 100


def test_load_ohlcv_aborts_when_dropna_yields_below_90pct() -> None:
    """>=10% NaN bars after dropna -> abort with explicit error (CC4)."""
    from src import __main__ as cli

    rows = []
    for i in range(100):
        rows.append({
            "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
            "open": 50000.0 + i,
            "high": 50010.0 + i,
            "low": 49990.0 + i,
            "close": 50005.0 + i if i % 2 == 0 else None,  # 50% NaN
            "volume": 1.0,
        })
    df = pd.DataFrame(rows)

    with patch("src.__main__.load_market_data", return_value=df), pytest.raises(ValueError, match="NaN.*pre-flight.*90%"):
        cli._load_ohlcv(symbol="BTCUSDT", start="2024-01-01", end="2024-01-05")


def test_load_ohlcv_passes_at_exactly_90pct_threshold() -> None:
    """Boundary: exactly 90% retained after dropna -> PASS (>=, not >)."""
    from src import __main__ as cli

    rows = []
    for i in range(100):
        rows.append({
            "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
            "open": 50000.0 + i,
            "high": 50010.0 + i,
            "low": 49990.0 + i,
            "close": 50005.0 + i if i >= 10 else None,  # first 10 NaN
            "volume": 1.0,
        })
    df = pd.DataFrame(rows)

    with patch("src.__main__.load_market_data", return_value=df):
        result = cli._load_ohlcv(symbol="BTCUSDT", start="2024-01-01", end="2024-01-05")

    assert len(result) == 100
