"""Kronos ML dispatch — extracted from backtest_runner (S53 T5, C11).

Handles the ``type == "kronos"`` branch: manifest-keyed cache-replay via
:func:`~src.backtest.kronos_runner.run_kronos_exploratory`, with an honest
"cache not built" structured result when the manifest sidecar is absent.

No torch import in this module — inference is cache-replay only.
Real inference (RUN_ML=1) is performed separately by scripts/run_kronos_s53.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants — Kronos cache dir and per-combo parquet paths (11 combos).
# Cache dir is gitignored; operator must run scripts/run_kronos_s53.py first.
# ---------------------------------------------------------------------------

_KRONOS_CACHE_DIR: Path = Path("data/kronos_cache")

_KRONOS_PARQUET_BY_COMBO: dict[tuple[str, str], str] = {
    ("BTCUSDT", "5"): "data/BTCUSDT_5m.parquet",
    ("BTCUSDT", "15"): "data/BTCUSDT_15m.parquet",
    ("BTCUSDT", "60"): "data/BTCUSDT_1h.parquet",
    ("BTCUSDT", "240"): "data/BTCUSDT_4h.parquet",
    ("BTCUSDT", "D"): "data/BTCUSDT_1d.parquet",
    ("ETHUSDT", "15"): "data/ETHUSDT_15m.parquet",
    ("ETHUSDT", "60"): "data/ETHUSDT_1h.parquet",
    ("ETHUSDT", "240"): "data/ETHUSDT_4h.parquet",
    ("SOLUSDT", "15"): "data/SOLUSDT_15m.parquet",
    ("SOLUSDT", "60"): "data/SOLUSDT_1h.parquet",
    ("SOLUSDT", "240"): "data/SOLUSDT_4h.parquet",
}

# S52 FIX A (PHASE 6 R2) — manifest sidecar written by scripts/run_kronos_s52.py.
# Schema v1: captures model_id, weights_hash, params_hash, device so the dashboard
# can reconstruct CacheKeys matching the operator-built cache.
_KRONOS_MANIFEST_NAME = "_manifest.json"
_KRONOS_MANIFEST_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_kronos_manifest(cache_dir: Path) -> dict[str, Any] | None:
    """Read ``<cache_dir>/_manifest.json`` and return its parsed dict, else ``None``.

    The manifest carries the 4 non-(symbol, timeframe, bar_close_ts) cache-key
    fields the strategy needs to reconstruct matching :class:`~src.ml.prediction_cache.CacheKey`\\s:
    ``model_id``, ``weights_hash``, ``params_hash``, ``device`` (+ schema version
    and per-combo coverage). Absent manifest = cache not built (honest "not built"
    path); present manifest = built (per-bar misses are legitimate, not "not built").

    Returns:
        Parsed manifest dict, or ``None`` on missing / unparsable manifest.
    """
    manifest_path = cache_dir / _KRONOS_MANIFEST_NAME
    if not manifest_path.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return data


def _load_kronos_df(
    symbol: str,
    interval: str,
    start: str,
    end: str,
) -> Any:
    """Load and normalize OHLCV DataFrame from parquet for a Kronos (symbol, interval) combo.

    Handles 'ts' (Binance) and 'time' (Bybit) column schemas — mirrors
    atr_breakout_runner._load_parquet_df normalization.

    Args:
        symbol: Trading symbol (e.g. "BTCUSDT").
        interval: Dashboard interval code (e.g. "60", "240", "D").
        start: ISO date string start inclusive (e.g. "2022-01-01").
        end: ISO date string end inclusive (e.g. "2023-12-31").

    Returns:
        Normalized DataFrame with ``_ts`` column.

    Raises:
        FileNotFoundError: if combo not registered or parquet file missing.
        ValueError: if DataFrame is empty after date filtering.
    """
    from datetime import date as _date

    import pandas as pd

    data_path_str = _KRONOS_PARQUET_BY_COMBO.get((symbol, interval))
    if data_path_str is None:
        raise FileNotFoundError(
            f"No parquet data path registered for Kronos ({symbol}, {interval}). "
            f"Supported combos: {sorted(_KRONOS_PARQUET_BY_COMBO.keys())}"
        )
    data_path = Path(data_path_str)
    if not data_path.exists():
        raise FileNotFoundError(
            f"Kronos parquet file missing: {data_path}. " f"Run market data download first."
        )

    raw = pd.read_parquet(data_path)

    if "ts" in raw.columns:
        raw["_ts"] = pd.to_datetime(raw["ts"], utc=True)
    elif "time" in raw.columns:
        raw["_ts"] = pd.to_datetime(raw["time"], utc=True)
    else:
        raw = raw.reset_index()
        raw["_ts"] = pd.to_datetime(raw.iloc[:, 0], utc=True)

    raw = raw.sort_values("_ts").reset_index(drop=True)
    start_date = _date.fromisoformat(start)
    end_date = _date.fromisoformat(end)
    mask = raw["_ts"].dt.date >= start_date
    mask &= raw["_ts"].dt.date <= end_date
    return raw[mask].copy().reset_index(drop=True)


# ---------------------------------------------------------------------------
# Public dispatch entry point
# ---------------------------------------------------------------------------

# Dashboard interval code → Kronos timeframe string (mirrors INTERVAL_FILE_LABEL).
_INTERVAL_TO_TIMEFRAME: dict[str, str] = {
    "5": "5m",
    "15": "15m",
    "60": "1h",
    "240": "4h",
    "D": "1d",
}

# Dashboard interval code → human-readable label (mirrors INTERVAL_LABELS).
_INTERVAL_LABELS: dict[str, str] = {
    "5": "5 minutes",
    "15": "15 minutes",
    "60": "1 hour",
    "240": "4 hours",
    "D": "1 day",
}


def run_kronos_dispatch(
    req: Any,
    *,
    preset: dict[str, Any],
    run_id: str,
    cache_path: Path,
    runs_dir: Path,
    cache_dir: Path = _KRONOS_CACHE_DIR,
) -> dict[str, Any]:
    """Execute the Kronos ML backtest dispatch (cache-replay, no torch).

    Implements the ``type == "kronos"`` branch: reads the manifest sidecar to
    reconstruct real cache keys, then replays predictions via
    :func:`~src.backtest.kronos_runner.run_kronos_exploratory`.  If the manifest
    is absent the cache has not been built yet and an honest structured result is
    returned without raising.

    Verdict is hard-pinned to ``RAW_PRETRAIN_LEAKAGE_SUSPECTED`` per ADR 0068.
    No torch import occurs in this path.

    Args:
        req: :class:`~src.dashboard.backtest_runner.BacktestRequest` instance.
        preset: The ``STRATEGY_PRESETS["kronos"]`` dict (caller-resolved).
        run_id: SHA-256[:16] run identifier (pre-computed by caller).
        cache_path: Path to the on-disk result cache file for this run.
        runs_dir: Directory where run JSON files are stored.
        cache_dir: Kronos prediction cache directory; defaults to
            :data:`_KRONOS_CACHE_DIR`.

    Returns:
        Result dict with ``run_id``, ``verdict``, ``n_trades``, ``request``,
        and associated fields matching the standard backtest envelope shape.

    Raises:
        ValueError: if ``(req.symbol, req.interval)`` is not in
            ``preset["supported_combos"]``.
    """
    from src.backtest.research_runner_envelope import VERDICT_RAW_PRETRAIN_LEAKAGE
    from src.ml.prediction_cache import PredictionCache

    # FIX B (PHASE 6 R2) — validate (symbol, interval) against supported_combos
    # BEFORE any dispatch (mirrors how server-side dispatch should reject invalid combos).
    supported_combos_kr = preset.get("supported_combos", [])
    if (req.symbol, req.interval) not in supported_combos_kr:
        raise ValueError(
            f"Kronos does not support combo ({req.symbol}, {req.interval}). "
            f"Supported combos: {sorted(supported_combos_kr)}"
        )

    # Map dashboard interval code → kronos timeframe string (e.g. "60" → "1h")
    timeframe_kr = _INTERVAL_TO_TIMEFRAME.get(req.interval, req.interval)

    # FIX A (PHASE 6 R2 / B2) — reconstruct the REAL cache-key params from the
    # manifest sidecar written by scripts/run_kronos_s52.py. Without this the
    # dashboard hardcodes placeholder keys (model_id="kronos", weights_hash="unknown",
    # device="cpu") that NEVER match the operator-built cache (real model_id /
    # weights_hash / params_hash / device="mps") → 100% MISS. The manifest also
    # makes "not built" (no manifest) distinguishable from "built but bar-level miss".
    manifest_kr = _read_kronos_manifest(cache_dir)
    if manifest_kr is not None:
        params_kr: dict[str, Any] = {
            "model_id": str(manifest_kr.get("model_id", "kronos")),
            "weights_hash": str(manifest_kr.get("weights_hash", "unknown")),
            "params_hash": str(manifest_kr.get("params_hash", "unknown")),
            "device": str(manifest_kr.get("device", "cpu")),
        }
    else:
        # No manifest → cache not built. Placeholder params (only used on the
        # graceful no-cache path below; never reaches a real lookup).
        params_kr = {
            "model_id": "kronos",
            "weights_hash": "unknown",
            "params_hash": "unknown",
            "device": "cpu",
        }

    cache_kr = PredictionCache(cache_dir)

    # "Not built" iff the manifest is absent. A manifest with no per-bar entries
    # for the queried range is a legitimate per-bar miss (0 trades), NOT "not built".
    if manifest_kr is None:
        # Cache absent — return honest structured result, no crash
        result_kr_nocache: dict[str, Any] = {
            "run_id": run_id,
            "cached": False,
            "verdict": VERDICT_RAW_PRETRAIN_LEAKAGE,
            "failed_criteria": [],
            "warnings": [
                {
                    "level": "info",
                    "code": "kronos_cache_absent",
                    "message": (
                        "Kronos predictions not cached yet — run "
                        "`RUN_ML=1 scripts/run_kronos_s52.py` on M4 first. "
                        "Cache artifacts → data/kronos_cache/ (gitignored)."
                    ),
                }
            ],
            "metrics": {},
            "request": {
                "strategy_id": req.strategy_id,
                "strategy_label": preset["label"],
                "strategy_config": preset,
                "symbol": req.symbol,
                "interval": req.interval,
                "interval_label": _INTERVAL_LABELS.get(req.interval, req.interval),
                "start": req.start,
                "end": req.end,
            },
            "message": (
                "Kronos predictions not cached yet — "
                "run `RUN_ML=1 scripts/run_kronos_s52.py` on M4 first."
            ),
        }
        runs_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(result_kr_nocache, default=str, indent=2))
        return result_kr_nocache

    # Cache present — load parquet and replay
    from src.backtest.kronos_runner import run_kronos_exploratory

    df_kr = _load_kronos_df(
        symbol=req.symbol,
        interval=req.interval,
        start=req.start,
        end=req.end,
    )

    kr_envelope = run_kronos_exploratory(
        df=df_kr,
        symbol=req.symbol,
        timeframe=timeframe_kr,
        params=params_kr,
        cache=cache_kr,
    )

    runs_dir.mkdir(parents=True, exist_ok=True)

    result_kr: dict[str, Any] = dict(kr_envelope)
    result_kr["run_id"] = run_id
    result_kr["cached"] = False
    result_kr["request"] = {
        "strategy_id": req.strategy_id,
        "strategy_label": preset["label"],
        "strategy_config": preset,
        "symbol": req.symbol,
        "interval": req.interval,
        "interval_label": _INTERVAL_LABELS.get(req.interval, req.interval),
        "start": req.start,
        "end": req.end,
    }
    cache_path.write_text(json.dumps(result_kr, default=str, indent=2))
    return result_kr
