"""S54 T2 — kronos_coverage helper, per-combo dispatch hits, /api/kronos/coverage.

  - kronos_coverage() converts v2 manifest first/last_bar_ts → ISO date ranges.
  - dispatch reconstructs CacheKeys from the per-combo v2 entry params → hits.
  - GET /api/kronos/coverage returns {"coverage": [...]} with the expected shape.

torch-free.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from src.dashboard._kronos_dispatch import kronos_coverage, run_kronos_dispatch
from src.dashboard.app import create_app

# ---------------------------------------------------------------------------
# kronos_coverage helper
# ---------------------------------------------------------------------------


def test_kronos_coverage_no_manifest_returns_empty(tmp_path: Path) -> None:
    assert kronos_coverage(tmp_path) == []


def test_kronos_coverage_converts_ts_to_iso(tmp_path: Path) -> None:
    first_ts = int(datetime(2023, 1, 1, 0, 5, tzinfo=UTC).timestamp())
    last_ts = int(datetime(2026, 4, 26, 0, 0, tzinfo=UTC).timestamp())
    manifest = {
        "schema_version": 2,
        "model_id": "NeoQuasar/Kronos-base",
        "weights_hash": "w",
        "params_hash": "p",
        "device": "mps",
        "combos": [
            {
                "symbol": "BTCUSDT",
                "timeframe": "5m",
                "model_id": "NeoQuasar/Kronos-base",
                "weights_hash": "w",
                "params_hash": "p",
                "device": "mps",
                "first_bar_ts": first_ts,
                "last_bar_ts": last_ts,
                "n_entries": 33467,
            }
        ],
    }
    (tmp_path / "_manifest.json").write_text(json.dumps(manifest))

    cov = kronos_coverage(tmp_path)
    assert len(cov) == 1
    entry = cov[0]
    assert entry == {
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "start_iso": "2023-01-01",
        "end_iso": "2026-04-26",
        "n_entries": 33467,
    }


def test_kronos_coverage_v1_entry_yields_empty_dates(tmp_path: Path) -> None:
    """A legacy combo lacking ts fields → empty ISO strings (UI treats as 'not built')."""
    manifest = {
        "schema_version": 1,
        "model_id": "m",
        "weights_hash": "w",
        "params_hash": "p",
        "device": "mps",
        "combos": [{"symbol": "BTCUSDT", "timeframe": "5m", "n_entries_written": 5}],
    }
    (tmp_path / "_manifest.json").write_text(json.dumps(manifest))
    cov = kronos_coverage(tmp_path)
    assert cov[0]["start_iso"] == ""
    assert cov[0]["end_iso"] == ""
    assert cov[0]["n_entries"] == 5


# ---------------------------------------------------------------------------
# Dispatch hits via per-combo v2 params
# ---------------------------------------------------------------------------


def _make_ohlcv_df(n: int = 50) -> pd.DataFrame:
    rng = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
    prices = [20000.0 + i * 10.0 for i in range(n)]
    return pd.DataFrame(
        {
            "_ts": rng,
            "open": prices,
            "high": [p + 50 for p in prices],
            "low": [p - 50 for p in prices],
            "close": [p + 5 for p in prices],
            "volume": [100.0] * n,
            "time": rng,
        }
    )


def test_dispatch_hits_via_per_combo_params(tmp_path: Path) -> None:
    """A v2 manifest whose per-combo params DIFFER from top-level → keys built from
    the combo entry produce cache hits (mixed sample_count correctness)."""
    from unittest.mock import patch

    from src.dashboard.backtest_runner import STRATEGY_PRESETS, BacktestRequest
    from src.ml.kronos_variant import KRONOS_BASE
    from src.ml.prediction_cache import CacheKey, PredictionCache

    cache_dir = tmp_path / "kr_cache"
    cache_dir.mkdir()

    combo_weights = "combo_w_1h"
    combo_params = "combo_p_1h"
    combo_device = "mps"

    # Top-level params are DELIBERATELY WRONG; only the per-combo entry is correct.
    manifest = {
        "schema_version": 2,
        "model_id": KRONOS_BASE.model_id,
        "weights_hash": "WRONG_TOP",
        "params_hash": "WRONG_TOP",
        "device": "cpu",
        "combos": [
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "model_id": KRONOS_BASE.model_id,
                "weights_hash": combo_weights,
                "params_hash": combo_params,
                "device": combo_device,
                "first_bar_ts": 1,
                "last_bar_ts": 2,
                "n_entries": 50,
            }
        ],
    }
    (cache_dir / "_manifest.json").write_text(json.dumps(manifest))

    df = _make_ohlcv_df(50)
    fire_bar = 20
    cache = PredictionCache(cache_dir)
    open_time = pd.Timestamp(df["_ts"].iloc[fire_bar]).to_pydatetime()
    bar_close_ts = int((open_time + timedelta(hours=1)).timestamp())
    key = CacheKey(
        model_id=KRONOS_BASE.model_id,
        weights_hash=combo_weights,
        symbol="BTCUSDT",
        timeframe="1h",
        bar_close_ts=bar_close_ts,
        params_hash=combo_params,
        device=combo_device,
    )
    cache.put(key, [Decimal(str(float(df["close"].iloc[fire_bar]) * 1.10))])

    req = BacktestRequest(
        strategy_id="kronos",
        symbol="BTCUSDT",
        interval="60",
        start="2023-01-01",
        end="2023-02-01",
        variant="base",
    )
    run_id = "a" * 16
    cache_path = tmp_path / f"{run_id}.json"

    with patch("src.dashboard._kronos_dispatch._load_kronos_df", return_value=df):
        result = run_kronos_dispatch(
            req,
            preset=dict(STRATEGY_PRESETS["kronos"]),
            run_id=run_id,
            cache_path=cache_path,
            runs_dir=tmp_path / "runs",
            cache_dir=cache_dir,
        )

    assert result["verdict"] == "RAW_PRETRAIN_LEAKAGE_SUSPECTED"
    assert (
        result["n_trades"] > 0
    ), "per-combo params not used — dispatch fell back to (wrong) top-level keys"


# ---------------------------------------------------------------------------
# Endpoint shape
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_kronos_coverage_endpoint_shape(client: TestClient) -> None:
    r = client.get("/api/kronos/coverage")
    assert r.status_code == 200
    data = r.json()
    assert "coverage" in data
    assert isinstance(data["coverage"], list)
    # Each entry (if any) must carry the documented fields.
    for entry in data["coverage"]:
        assert set(entry.keys()) == {
            "symbol",
            "timeframe",
            "start_iso",
            "end_iso",
            "n_entries",
        }
