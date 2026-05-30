"""Direct unit tests for the extracted Kronos dispatch module (S53 T5, C11).

Tests target ``src.dashboard._kronos_dispatch.run_kronos_dispatch`` directly,
independent of backtest_runner wiring.  Patch targets live in _kronos_dispatch
(not backtest_runner) for dispatch-level isolation.

Characterization coverage (mirrors plan T5 Step 4):
  - no manifest → "not built" honest structured result (no crash, no torch).
  - manifest + real-keyed cache → n_trades > 0 (cache-key parity).
  - unsupported combo → ValueError with "support" in the message.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_ohlcv_df(n: int = 50) -> pd.DataFrame:
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


def _make_req(
    symbol: str = "BTCUSDT",
    interval: str = "60",
    strategy_id: str = "kronos",
) -> object:
    """Build a minimal BacktestRequest-like object for dispatch tests."""
    from src.dashboard.backtest_runner import BacktestRequest

    return BacktestRequest(
        strategy_id=strategy_id,
        symbol=symbol,
        interval=interval,
        start="2023-01-01",
        end="2023-02-01",
    )


def _make_preset() -> dict:
    """Return a minimal 'kronos' preset dict for tests."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS

    # Ensure the test combo is in supported_combos (it always is for BTCUSDT/60).
    return dict(STRATEGY_PRESETS["kronos"])


def _make_run_id_and_cache_path(tmp_path: Path) -> tuple[str, Path]:
    """Return a dummy run_id and cache_path in tmp_path."""
    run_id = "a" * 16  # valid sha256[:16] shape
    cache_path = tmp_path / f"{run_id}.json"
    return run_id, cache_path


# Real key constants matching _write_manifest below.
_REAL_MODEL_ID = "NeoQuasar/Kronos-mini"
_REAL_WEIGHTS_HASH = "deadbeefcafe"
_REAL_PARAMS_HASH = "0011223344"
_REAL_DEVICE = "mps"


def _write_manifest(cache_dir: Path) -> None:
    """Write a _manifest.json matching the script's real key params."""
    import json

    manifest = {
        "schema_version": 1,
        "model_id": _REAL_MODEL_ID,
        "weights_hash": _REAL_WEIGHTS_HASH,
        "params_hash": _REAL_PARAMS_HASH,
        "device": _REAL_DEVICE,
        "combos": [{"symbol": "BTCUSDT", "timeframe": "1h", "n_entries": 1}],
    }
    (cache_dir / "_manifest.json").write_text(json.dumps(manifest, indent=2))


def _build_real_keyed_cache(cache_dir: Path, df: pd.DataFrame, *, fire_bar: int) -> None:
    """Populate PredictionCache with real keys so the dispatch gets HITS."""
    from datetime import timedelta
    from decimal import Decimal

    from src.ml.prediction_cache import CacheKey, PredictionCache

    cache = PredictionCache(cache_dir)
    open_time = pd.Timestamp(df["_ts"].iloc[fire_bar]).to_pydatetime()
    bar_close_ts = int((open_time + timedelta(hours=1)).timestamp())
    current_close = float(df["close"].iloc[fire_bar])

    key = CacheKey(
        model_id=_REAL_MODEL_ID,
        weights_hash=_REAL_WEIGHTS_HASH,
        symbol="BTCUSDT",
        timeframe="1h",
        bar_close_ts=bar_close_ts,
        params_hash=_REAL_PARAMS_HASH,
        device=_REAL_DEVICE,
    )
    # Predict well above current close → ENTRY_LONG_KRONOS at fire_bar.
    cache.put(key, [Decimal(str(current_close * 1.10))])


# ---------------------------------------------------------------------------
# Tests: no-manifest path ("not built")
# ---------------------------------------------------------------------------


def test_run_kronos_dispatch_no_manifest_no_crash(tmp_path: Path) -> None:
    """No manifest → honest 'not built' result, no exception, no torch import."""
    import sys
    from unittest.mock import patch

    from src.dashboard._kronos_dispatch import run_kronos_dispatch

    assert "torch" not in sys.modules

    empty_cache = tmp_path / "kr_cache"
    empty_cache.mkdir()
    run_id, cache_path = _make_run_id_and_cache_path(tmp_path)
    preset = _make_preset()
    req = _make_req()
    df = _make_ohlcv_df()

    with patch("src.dashboard._kronos_dispatch._load_kronos_df", return_value=df):
        result = run_kronos_dispatch(
            req,
            preset=preset,
            run_id=run_id,
            cache_path=cache_path,
            runs_dir=tmp_path / "runs",
            cache_dir=empty_cache,
        )

    assert result["verdict"] == "RAW_PRETRAIN_LEAKAGE_SUSPECTED"
    assert result["run_id"] == run_id
    # Honest "not built" message must reference the cache-build instruction.
    result_str = str(result).lower()
    assert "run_ml" in result_str or "not cached" in result_str or "cache" in result_str
    assert "torch" not in sys.modules


def test_run_kronos_dispatch_no_manifest_returns_structured_result(tmp_path: Path) -> None:
    """No-manifest result must contain all required envelope keys."""
    from unittest.mock import patch

    from src.dashboard._kronos_dispatch import run_kronos_dispatch

    empty_cache = tmp_path / "kr_cache"
    empty_cache.mkdir()
    run_id, cache_path = _make_run_id_and_cache_path(tmp_path)
    preset = _make_preset()
    req = _make_req()
    df = _make_ohlcv_df()

    with patch("src.dashboard._kronos_dispatch._load_kronos_df", return_value=df):
        result = run_kronos_dispatch(
            req,
            preset=preset,
            run_id=run_id,
            cache_path=cache_path,
            runs_dir=tmp_path / "runs",
            cache_dir=empty_cache,
        )

    assert "run_id" in result
    assert "verdict" in result
    assert result["verdict"] == "RAW_PRETRAIN_LEAKAGE_SUSPECTED"
    assert "warnings" in result
    assert len(result["warnings"]) > 0


# ---------------------------------------------------------------------------
# Tests: manifest + real-keyed cache → hits
# ---------------------------------------------------------------------------


def test_run_kronos_dispatch_manifest_keyed_cache_produces_hits(tmp_path: Path) -> None:
    """Manifest + real-keyed cache → n_trades > 0 (cache-key parity preserved)."""
    from unittest.mock import patch

    from src.dashboard._kronos_dispatch import run_kronos_dispatch

    real_cache = tmp_path / "kr_cache_real"
    real_cache.mkdir()
    df = _make_ohlcv_df(50)
    _build_real_keyed_cache(real_cache, df, fire_bar=20)
    _write_manifest(real_cache)

    run_id, cache_path = _make_run_id_and_cache_path(tmp_path)
    preset = _make_preset()
    # T6: manifest uses _REAL_MODEL_ID=Kronos-mini → request must specify variant="mini"
    from src.dashboard.backtest_runner import BacktestRequest

    req = BacktestRequest(
        strategy_id="kronos",
        symbol="BTCUSDT",
        interval="60",
        start="2023-01-01",
        end="2023-02-01",
        variant="mini",
    )

    with patch("src.dashboard._kronos_dispatch._load_kronos_df", return_value=df):
        result = run_kronos_dispatch(
            req,
            preset=preset,
            run_id=run_id,
            cache_path=cache_path,
            runs_dir=tmp_path / "runs",
            cache_dir=real_cache,
        )

    assert result["verdict"] == "RAW_PRETRAIN_LEAKAGE_SUSPECTED"
    assert (
        result["n_trades"] > 0
    ), "manifest-keyed cache produced 0 trades — cache-key parity broken in _kronos_dispatch"


# ---------------------------------------------------------------------------
# Tests: unsupported combo → ValueError
# ---------------------------------------------------------------------------


def test_run_kronos_dispatch_unsupported_combo_raises_value_error(tmp_path: Path) -> None:
    """(symbol, interval) not in supported_combos must raise ValueError."""
    from src.dashboard._kronos_dispatch import run_kronos_dispatch

    empty_cache = tmp_path / "kr_cache"
    empty_cache.mkdir()
    run_id, cache_path = _make_run_id_and_cache_path(tmp_path)
    preset = _make_preset()
    # ETHUSDT/5 is NOT in supported_combos.
    req = _make_req(symbol="ETHUSDT", interval="5")

    with pytest.raises(ValueError, match="(?i)support"):
        run_kronos_dispatch(
            req,
            preset=preset,
            run_id=run_id,
            cache_path=cache_path,
            runs_dir=tmp_path / "runs",
            cache_dir=empty_cache,
        )


# ---------------------------------------------------------------------------
# T6: variant dispatch — "mini" against base-only manifest → honest miss message
# ---------------------------------------------------------------------------


def _write_base_manifest(cache_dir: Path) -> None:
    """Write a manifest with model_id = base (NeoQuasar/Kronos-base)."""
    import json

    from src.ml.kronos_variant import KRONOS_BASE

    manifest = {
        "schema_version": 1,
        "model_id": KRONOS_BASE.model_id,
        "weights_hash": "aabbcc",
        "params_hash": "001122",
        "device": "cpu",
        "combos": [{"symbol": "BTCUSDT", "timeframe": "1h", "n_entries": 1}],
    }
    (cache_dir / "_manifest.json").write_text(json.dumps(manifest, indent=2))


def _make_req_with_variant(variant: str, symbol: str = "BTCUSDT", interval: str = "60") -> object:
    """Build BacktestRequest with explicit variant field."""
    from src.dashboard.backtest_runner import BacktestRequest

    return BacktestRequest(
        strategy_id="kronos",
        symbol=symbol,
        interval=interval,
        start="2023-01-01",
        end="2023-02-01",
        variant=variant,
    )


def test_run_kronos_dispatch_mini_against_base_manifest_returns_honest_miss(tmp_path: Path) -> None:
    """Requesting variant='mini' against base-only manifest → honest 'not cached for mini' result."""
    from unittest.mock import patch

    from src.dashboard._kronos_dispatch import run_kronos_dispatch

    base_cache = tmp_path / "kr_cache_base"
    base_cache.mkdir()
    _write_base_manifest(base_cache)

    run_id, cache_path = _make_run_id_and_cache_path(tmp_path)
    preset = _make_preset()
    req = _make_req_with_variant("mini")
    df = _make_ohlcv_df()

    with patch("src.dashboard._kronos_dispatch._load_kronos_df", return_value=df):
        result = run_kronos_dispatch(
            req,
            preset=preset,
            run_id=run_id,
            cache_path=cache_path,
            runs_dir=tmp_path / "runs",
            cache_dir=base_cache,
        )

    # Must NOT crash and must return the leakage verdict
    assert result["verdict"] == "RAW_PRETRAIN_LEAKAGE_SUSPECTED"
    assert result["run_id"] == run_id
    # Must indicate mini is not cached
    result_str = str(result).lower()
    assert "mini" in result_str or "variant" in result_str or "cache" in result_str


def test_run_kronos_dispatch_matching_variant_hits(tmp_path: Path) -> None:
    """Requesting variant='mini' against mini manifest + mini-keyed cache → hits."""
    import json
    from datetime import timedelta
    from decimal import Decimal
    from unittest.mock import patch

    from src.dashboard._kronos_dispatch import run_kronos_dispatch
    from src.ml.kronos_variant import KRONOS_MINI
    from src.ml.prediction_cache import CacheKey, PredictionCache

    mini_cache = tmp_path / "kr_cache_mini"
    mini_cache.mkdir()

    # Write manifest with mini model_id
    manifest = {
        "schema_version": 1,
        "model_id": KRONOS_MINI.model_id,
        "weights_hash": "deadbeefcafe",
        "params_hash": "0011223344",
        "device": "mps",
        "combos": [{"symbol": "BTCUSDT", "timeframe": "1h", "n_entries": 1}],
    }
    (mini_cache / "_manifest.json").write_text(json.dumps(manifest, indent=2))

    df = _make_ohlcv_df(50)
    fire_bar = 20
    cache = PredictionCache(mini_cache)
    open_time = pd.Timestamp(df["_ts"].iloc[fire_bar]).to_pydatetime()
    bar_close_ts = int((open_time + timedelta(hours=1)).timestamp())
    current_close = float(df["close"].iloc[fire_bar])
    key = CacheKey(
        model_id=KRONOS_MINI.model_id,
        weights_hash="deadbeefcafe",
        symbol="BTCUSDT",
        timeframe="1h",
        bar_close_ts=bar_close_ts,
        params_hash="0011223344",
        device="mps",
    )
    cache.put(key, [Decimal(str(current_close * 1.10))])

    run_id, cache_path = _make_run_id_and_cache_path(tmp_path)
    preset = _make_preset()
    req = _make_req_with_variant("mini")

    with patch("src.dashboard._kronos_dispatch._load_kronos_df", return_value=df):
        result = run_kronos_dispatch(
            req,
            preset=preset,
            run_id=run_id,
            cache_path=cache_path,
            runs_dir=tmp_path / "runs",
            cache_dir=mini_cache,
        )

    assert result["verdict"] == "RAW_PRETRAIN_LEAKAGE_SUSPECTED"
    assert result["n_trades"] > 0, "mini-keyed cache + mini variant request → should produce hits"
