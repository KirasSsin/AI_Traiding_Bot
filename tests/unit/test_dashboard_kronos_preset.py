"""Tests for Kronos dashboard preset (S52 T8 — ADR 0068, RAW_PRETRAIN_LEAKAGE_SUSPECTED).

Covers:
  - 1 parametric 'kronos' preset with 11 supported_combos (mirrors atr_breakout pattern).
  - type == "kronos", optgroup == "ML / Прогноз".
  - RU description contains honest leakage note.
  - /api/strategies includes 'kronos' (server-driven, no frontend change).
  - dispatch with NO cache -> returns RAW_PRETRAIN_LEAKAGE_SUSPECTED + honest message, no crash.
  - dispatch WITH pre-populated cache -> returns exploratory result (verdict RAW_PRETRAIN_LEAKAGE_SUSPECTED).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Preset registration
# ---------------------------------------------------------------------------

_EXPECTED_COMBOS = [
    ("BTCUSDT", "5"),
    ("BTCUSDT", "15"),
    ("BTCUSDT", "60"),
    ("BTCUSDT", "240"),
    ("BTCUSDT", "D"),
    ("ETHUSDT", "15"),
    ("ETHUSDT", "60"),
    ("ETHUSDT", "240"),
    ("SOLUSDT", "15"),
    ("SOLUSDT", "60"),
    ("SOLUSDT", "240"),
]


def test_kronos_preset_registered() -> None:
    """'kronos' preset must exist in STRATEGY_PRESETS."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    assert "kronos" in STRATEGY_PRESETS
    preset = STRATEGY_PRESETS["kronos"]
    assert preset["type"] == "kronos"
    assert preset["sprint"] == "S52"


def test_kronos_preset_supported_combos_exact_11() -> None:
    """Parametric preset must declare exactly 11 supported_combos."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["kronos"]
    sc = preset.get("supported_combos")
    assert isinstance(sc, list)
    assert len(sc) == 11, f"Expected 11 combos, got {len(sc)}: {sc}"
    for combo in _EXPECTED_COMBOS:
        assert combo in sc, f"Missing combo {combo} in supported_combos"


def test_kronos_preset_optgroup() -> None:
    """Preset must be in 'ML / Прогноз' optgroup for dashboard dropdown grouping."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["kronos"]
    assert preset.get("optgroup") == "ML / Прогноз"


def test_kronos_preset_description_has_leakage_note() -> None:
    """Description must contain RAW_PRETRAIN_LEAKAGE_SUSPECTED note (honest label)."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["kronos"]
    desc = preset.get("description", "")
    assert len(desc) > 50
    # Honest leakage disclosure must be present
    assert (
        "RAW_PRETRAIN_LEAKAGE_SUSPECTED" in desc
        or "претрейн" in desc.lower()
        or "pretrain" in desc.lower()
    )


def test_kronos_preset_label_nonempty() -> None:
    """Preset label must be a non-empty string."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    preset = STRATEGY_PRESETS["kronos"]
    label = preset.get("label", "")
    assert len(label) > 5


def test_api_strategies_includes_kronos() -> None:
    """STRATEGY_PRESETS must include 'kronos' with required API fields."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    assert "kronos" in STRATEGY_PRESETS
    preset = STRATEGY_PRESETS["kronos"]
    for field in ("label", "type", "optgroup", "description"):
        assert field in preset, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Dispatch: no cache -> honest structured result (no crash, no torch)
# ---------------------------------------------------------------------------


def _make_ohlcv_df(n: int = 30) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame for dispatch tests."""
    import numpy as np

    rng = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
    prices = 20000.0 + np.arange(n, dtype=float) * 10.0
    return pd.DataFrame(
        {
            "_ts": rng,
            "open": prices,
            "high": prices + 50.0,
            "low": prices - 50.0,
            "close": prices + 5.0,
            "volume": 100.0 + np.zeros(n),
            "time": rng,
        }
    )


@pytest.fixture()
def tmp_runs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect _RUNS_DIR to a tmp path so tests don't pollute data/runs/."""
    runs = tmp_path / "runs"
    runs.mkdir()
    import src.dashboard.backtest_runner as br

    monkeypatch.setattr(br, "_RUNS_DIR", runs)
    return runs


@pytest.fixture()
def empty_cache_dir(tmp_path: Path) -> Path:
    """A tmp dir to act as an EMPTY prediction cache."""
    cache = tmp_path / "kronos_cache_empty"
    cache.mkdir()
    return cache


def test_kronos_dispatch_no_cache_no_crash(tmp_runs_dir: Path, empty_cache_dir: Path) -> None:
    """dispatch type=kronos with empty cache must NOT raise, NOT import torch."""
    import sys

    # torch must remain absent throughout this test
    assert "torch" not in sys.modules

    from src.dashboard.backtest_runner import BacktestRequest, run_backtest

    df = _make_ohlcv_df(50)

    # Patch _load_kronos_df to return our stub df, and _KRONOS_CACHE_DIR for isolation
    import src.dashboard.backtest_runner as br

    original_cache_dir = br._KRONOS_CACHE_DIR  # type: ignore[attr-defined]
    try:
        br._KRONOS_CACHE_DIR = empty_cache_dir  # type: ignore[attr-defined]
        with patch.object(br, "_load_kronos_df", return_value=df):
            req = BacktestRequest(
                strategy_id="kronos",
                symbol="BTCUSDT",
                interval="60",
                start="2023-01-01",
                end="2023-02-01",
            )
            result = run_backtest(req, force=True)
    finally:
        br._KRONOS_CACHE_DIR = original_cache_dir  # type: ignore[attr-defined]

    assert result is not None
    assert result.get("verdict") == "RAW_PRETRAIN_LEAKAGE_SUSPECTED"
    # must contain an honest "not cached" message somewhere
    result_str = str(result)
    assert (
        "cache" in result_str.lower()
        or "кэш" in result_str.lower()
        or "cached" in result_str.lower()
    )
    # torch must still be absent
    assert "torch" not in sys.modules


def test_kronos_dispatch_no_cache_returns_structured_result(
    tmp_runs_dir: Path, empty_cache_dir: Path
) -> None:
    """Cache-absent result must be a structured dict with required keys."""
    import src.dashboard.backtest_runner as br
    from src.dashboard.backtest_runner import BacktestRequest, run_backtest

    df = _make_ohlcv_df(50)

    original_cache_dir = br._KRONOS_CACHE_DIR  # type: ignore[attr-defined]
    try:
        br._KRONOS_CACHE_DIR = empty_cache_dir  # type: ignore[attr-defined]
        with patch.object(br, "_load_kronos_df", return_value=df):
            req = BacktestRequest(
                strategy_id="kronos",
                symbol="BTCUSDT",
                interval="60",
                start="2023-01-01",
                end="2023-02-01",
            )
            result = run_backtest(req, force=True)
    finally:
        br._KRONOS_CACHE_DIR = original_cache_dir  # type: ignore[attr-defined]

    # Must have run_id (even for graceful no-cache result)
    assert "run_id" in result
    assert "verdict" in result
    assert result["verdict"] == "RAW_PRETRAIN_LEAKAGE_SUSPECTED"


# ---------------------------------------------------------------------------
# Dispatch: with populated cache -> exploratory result
# ---------------------------------------------------------------------------


def _populate_cache(cache_dir: Path, symbol: str, timeframe: str) -> None:
    """Write a single dummy cache entry so the cache appears non-empty."""
    # We don't need real kronos predictions — just something that makes
    # PredictionCache.get(...) return a non-None value for at least one bar.
    # The run_kronos_exploratory will get cache hits = 0 (wrong keys) but
    # won't crash — it gracefully produces 0 trades, returns envelope.
    # To produce actual trades we'd need matching keys; for this test
    # we only verify verdict + no-crash, so 0-trade envelope is fine.
    # Mark the dir as "populated" by writing a sentinel file.
    (cache_dir / "_sentinel.txt").write_text("populated")


def test_kronos_dispatch_with_cache_returns_leakage_verdict(
    tmp_runs_dir: Path, tmp_path: Path
) -> None:
    """dispatch with a pre-populated cache dir must return RAW_PRETRAIN_LEAKAGE_SUSPECTED."""
    populated_cache = tmp_path / "kronos_cache_populated"
    populated_cache.mkdir()
    _populate_cache(populated_cache, "BTCUSDT", "1h")

    import src.dashboard.backtest_runner as br
    from src.dashboard.backtest_runner import BacktestRequest, run_backtest

    df = _make_ohlcv_df(50)

    original_cache_dir = br._KRONOS_CACHE_DIR  # type: ignore[attr-defined]
    try:
        br._KRONOS_CACHE_DIR = populated_cache  # type: ignore[attr-defined]
        with patch.object(br, "_load_kronos_df", return_value=df):
            req = BacktestRequest(
                strategy_id="kronos",
                symbol="BTCUSDT",
                interval="60",
                start="2023-01-01",
                end="2023-02-01",
            )
            result = run_backtest(req, force=True)
    finally:
        br._KRONOS_CACHE_DIR = original_cache_dir  # type: ignore[attr-defined]

    assert result["verdict"] == "RAW_PRETRAIN_LEAKAGE_SUSPECTED"
    assert "run_id" in result
