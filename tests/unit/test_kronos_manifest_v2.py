"""S54 T1 — manifest v2 + _build_cache_for_combo ts-return + backfill tests.

Targets scripts/run_kronos_s53.py:
  - MANIFEST_SCHEMA_VERSION == 2.
  - _build_cache_for_combo returns {written, first_bar_ts, last_bar_ts} with
    correct min/max bar_close_ts over the built window.
  - _write_manifest writes self-describing per-combo entries; merge by
    (symbol, timeframe) preserves each combo's OWN params (mixed sample_count).
  - rebuild_manifest_v2 upgrades a v1 manifest in-place using parquet windows.

torch-free: uses a MockKronosAdapter (no real inference).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import scripts.run_kronos_s53 as rk
from src.ml.prediction_cache import PredictionCache

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


class MockKronosAdapter:
    """Minimal adapter returning a fixed Decimal prediction (no torch)."""

    def predict(self, context_df: Any, *, lookback: int, horizon: int) -> list[Decimal]:  # noqa: ARG002
        return [Decimal("100.0")]


def _make_df(n: int = 10, freq: str = "1h") -> pd.DataFrame:
    """Normalized OHLCV frame with a UTC ``_ts`` column (mirrors _normalize_df out)."""
    rng = pd.date_range("2023-06-01", periods=n, freq=freq, tz="UTC")
    prices = [20000.0 + i * 10.0 for i in range(n)]
    return pd.DataFrame(
        {
            "_ts": rng,
            "open": prices,
            "high": [p + 5 for p in prices],
            "low": [p - 5 for p in prices],
            "close": [p + 1 for p in prices],
            "volume": [1.0] * n,
        }
    )


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------


def test_manifest_schema_version_is_2() -> None:
    assert rk.MANIFEST_SCHEMA_VERSION == 2


# ---------------------------------------------------------------------------
# _build_cache_for_combo ts-return
# ---------------------------------------------------------------------------


def test_build_cache_for_combo_returns_first_last_ts(tmp_path: Path) -> None:
    """The built window's first/last bar_close_ts match the expected formula."""
    df = _make_df(n=5, freq="1h")
    cache = PredictionCache(tmp_path)

    stats = rk._build_cache_for_combo(
        symbol="BTCUSDT",
        timeframe="1h",
        df=df,
        adapter=MockKronosAdapter(),
        cache=cache,
        model_id="NeoQuasar/Kronos-base",
        weights_hash="abc",
        params_hash="def",
        max_context=512,
        max_bars=None,
        n_draws=1,
    )

    td = timedelta(hours=1)
    expected_first = int((pd.Timestamp(df["_ts"].iloc[0]).to_pydatetime() + td).timestamp())
    expected_last = int((pd.Timestamp(df["_ts"].iloc[-1]).to_pydatetime() + td).timestamp())

    assert stats["written"] == 5
    assert stats["first_bar_ts"] == expected_first
    assert stats["last_bar_ts"] == expected_last
    assert stats["first_bar_ts"] < stats["last_bar_ts"]


def test_build_cache_for_combo_max_bars_windows_ts(tmp_path: Path) -> None:
    """max_bars restricts the window → first_bar_ts is the last-N window start."""
    df = _make_df(n=10, freq="1h")
    cache = PredictionCache(tmp_path)

    stats = rk._build_cache_for_combo(
        symbol="BTCUSDT",
        timeframe="1h",
        df=df,
        adapter=MockKronosAdapter(),
        cache=cache,
        model_id="m",
        weights_hash="w",
        params_hash="p",
        max_context=512,
        max_bars=3,
        n_draws=1,
    )

    td = timedelta(hours=1)
    # Last 3 bars: indices 7,8,9.
    expected_first = int((pd.Timestamp(df["_ts"].iloc[7]).to_pydatetime() + td).timestamp())
    expected_last = int((pd.Timestamp(df["_ts"].iloc[9]).to_pydatetime() + td).timestamp())
    assert stats["written"] == 3
    assert stats["first_bar_ts"] == expected_first
    assert stats["last_bar_ts"] == expected_last


# ---------------------------------------------------------------------------
# _write_manifest v2 shape + per-combo param preservation
# ---------------------------------------------------------------------------


def test_write_manifest_v2_shape(tmp_path: Path) -> None:
    """Manifest carries schema_version 2 + self-describing combo entries."""
    rk._write_manifest(
        cache_dir=tmp_path,
        model_id="NeoQuasar/Kronos-base",
        weights_hash="topw",
        params_hash="topp",
        combos_coverage=[
            {
                "symbol": "BTCUSDT",
                "timeframe": "5m",
                "model_id": "NeoQuasar/Kronos-base",
                "weights_hash": "w5",
                "params_hash": "p5",
                "device": "mps",
                "first_bar_ts": 1000,
                "last_bar_ts": 2000,
                "n_entries": 100,
            }
        ],
    )
    manifest = json.loads((tmp_path / rk.MANIFEST_NAME).read_text())
    assert manifest["schema_version"] == 2
    # v1 back-compat top-level fields retained.
    assert manifest["model_id"] == "NeoQuasar/Kronos-base"
    combo = manifest["combos"][0]
    for field in (
        "symbol",
        "timeframe",
        "model_id",
        "weights_hash",
        "params_hash",
        "device",
        "first_bar_ts",
        "last_bar_ts",
        "n_entries",
    ):
        assert field in combo, f"missing per-combo field: {field}"
    assert combo["first_bar_ts"] == 1000
    assert combo["last_bar_ts"] == 2000


def test_write_manifest_merge_preserves_per_combo_params(tmp_path: Path) -> None:
    """Two combos built with different params_hash coexist (merge by sym,tf)."""
    rk._write_manifest(
        cache_dir=tmp_path,
        model_id="m",
        weights_hash="w",
        params_hash="p_5m",
        combos_coverage=[
            {
                "symbol": "BTCUSDT",
                "timeframe": "5m",
                "model_id": "m",
                "weights_hash": "w",
                "params_hash": "p_5m",
                "device": "mps",
                "first_bar_ts": 1,
                "last_bar_ts": 2,
                "n_entries": 10,
            }
        ],
    )
    # Second build: 1h combo with a DIFFERENT params_hash (e.g. sample_count change).
    rk._write_manifest(
        cache_dir=tmp_path,
        model_id="m",
        weights_hash="w",
        params_hash="p_1h",
        combos_coverage=[
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "model_id": "m",
                "weights_hash": "w",
                "params_hash": "p_1h",
                "device": "mps",
                "first_bar_ts": 3,
                "last_bar_ts": 4,
                "n_entries": 20,
            }
        ],
    )
    manifest = json.loads((tmp_path / rk.MANIFEST_NAME).read_text())
    by_tf = {c["timeframe"]: c for c in manifest["combos"]}
    assert by_tf["5m"]["params_hash"] == "p_5m"
    assert by_tf["1h"]["params_hash"] == "p_1h"


# ---------------------------------------------------------------------------
# rebuild_manifest_v2 backfill
# ---------------------------------------------------------------------------


def test_rebuild_manifest_v2_backfills_ts_from_parquet(tmp_path: Path, monkeypatch: Any) -> None:
    """v1 manifest (no ts) → v2 with first/last_bar_ts computed from parquet window."""
    # Write a synthetic 5m parquet (with a `time` column, like the live data).
    n = 20
    rng = pd.date_range("2023-06-01", periods=n, freq="5min", tz="UTC")
    parquet = tmp_path / "BTCUSDT_5m.parquet"
    pd.DataFrame(
        {
            "time": rng,
            "open": [1.0] * n,
            "high": [1.0] * n,
            "low": [1.0] * n,
            "close": [1.0] * n,
            "volume": [1.0] * n,
        }
    ).to_parquet(parquet)

    # Point COMBOS for (BTCUSDT, 5m) at our synthetic parquet.
    monkeypatch.setattr(
        rk,
        "COMBOS",
        [("BTCUSDT", "5m", str(parquet))],
    )

    # Write a v1 manifest: top-level params, combo with legacy n_entries_written.
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    v1 = {
        "schema_version": 1,
        "model_id": "NeoQuasar/Kronos-base",
        "weights_hash": "topw",
        "params_hash": "topp",
        "device": "mps",
        "combos": [{"symbol": "BTCUSDT", "timeframe": "5m", "n_entries_written": 5}],
    }
    (cache_dir / rk.MANIFEST_NAME).write_text(json.dumps(v1))

    manifest = rk.rebuild_manifest_v2(cache_dir)

    assert manifest["schema_version"] == 2
    combo = manifest["combos"][0]
    # n_entries=5 → window = last 5 bars (indices 15..19).
    td = timedelta(minutes=5)
    window = rng[-5:]
    expected_first = int((window[0].to_pydatetime() + td).timestamp())
    expected_last = int((window[-1].to_pydatetime() + td).timestamp())
    assert combo["n_entries"] == 5
    assert combo["first_bar_ts"] == expected_first
    assert combo["last_bar_ts"] == expected_last
    # Per-combo params backfilled from top-level.
    assert combo["model_id"] == "NeoQuasar/Kronos-base"
    assert combo["params_hash"] == "topp"
    assert combo["device"] == "mps"


def test_rebuild_manifest_v2_idempotent(tmp_path: Path, monkeypatch: Any) -> None:
    """Running rebuild on an already-v2 manifest leaves the ts fields untouched."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(rk, "COMBOS", [])  # no parquet needed — ts already present
    v2 = {
        "schema_version": 2,
        "model_id": "m",
        "weights_hash": "w",
        "params_hash": "p",
        "device": "mps",
        "combos": [
            {
                "symbol": "BTCUSDT",
                "timeframe": "5m",
                "model_id": "m",
                "weights_hash": "w",
                "params_hash": "p",
                "device": "mps",
                "first_bar_ts": 111,
                "last_bar_ts": 222,
                "n_entries": 5,
            }
        ],
    }
    (cache_dir / rk.MANIFEST_NAME).write_text(json.dumps(v2))

    manifest = rk.rebuild_manifest_v2(cache_dir)
    combo = manifest["combos"][0]
    assert combo["first_bar_ts"] == 111
    assert combo["last_bar_ts"] == 222


def test_rebuild_manifest_v2_missing_raises(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(FileNotFoundError):
        rk.rebuild_manifest_v2(tmp_path / "nonexistent")


# Sanity: confirm UTC date conversion expectation used by coverage helper.
def test_ts_iso_roundtrip() -> None:
    ts = int(datetime(2024, 3, 15, 12, 0, tzinfo=UTC).timestamp())
    assert datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%d") == "2024-03-15"
