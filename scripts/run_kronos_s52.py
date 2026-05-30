"""S52 T7 — Kronos (NeoQuasar) cache-build + exploratory backtest runner (11 combos).

OPERATOR INSTRUCTIONS (Mac M4 Pro, MPS):
  1. pip install -e ".[ml]"
  2. RUN_ML=1 .venv/bin/python scripts/run_kronos_s52.py

Without RUN_ML=1 this script prints these instructions and exits 0.
torch is never imported unless RUN_ML=1 is set.

CACHE ARTIFACTS → data/kronos_cache/  (gitignored — never committed).
RESULTS JSON    → data/kronos_s52_results/  (gitignored — never committed).

HONEST DISCLAIMER (ADR 0068, GATE 0):
  BTC/USDT confirmed in Kronos pretraining corpus. Backtest results carry
  verdict VERDICT_RAW_PRETRAIN_LEAKAGE_SUSPECTED and are EXPLORATORY ONLY.
  No formal WFA path. Forward paper-trade is the only clean evaluation.

DESIGN (ADR 0068, C4 provenance-bound keys):
  - weights_hash = SHA-256 of actual HuggingFace weights file on operator machine.
  - CacheKey fields exactly match what KronosStrategy.on_bar() reads:
      model_id, weights_hash, symbol, timeframe, bar_close_ts, params_hash, device
  - bar_close_ts = int((open_time + timeframe_delta).timestamp()) — derived from
    the same formula as _build_bar_from_row in kronos_runner.py.
  - params_hash = hash_params({"T": temperature, "top_p": top_p,
      "sample_count": sample_count, "horizon": horizon, "seed": seed}).
  - median_ensemble() reduces sample_count draws → single Decimal vector per bar.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

# Allow running from repo root without install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.backtest.kronos_runner import run_kronos_exploratory
from src.ml.prediction_cache import CacheKey, PredictionCache, hash_params, median_ensemble

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
_log = logging.getLogger(__name__)

# ─── Guard ────────────────────────────────────────────────────────────────────
RUN_ML: bool = os.environ.get("RUN_ML") == "1"

# ─── Kronos model config ──────────────────────────────────────────────────────
MODEL_ID = "NeoQuasar/Kronos-mini"
TOKENIZER_ID = "NeoQuasar/Kronos-Tokenizer-base"
DEVICE = "mps"
MAX_CONTEXT = 2048
TEMPERATURE = 1.0
TOP_P = 0.9
SAMPLE_COUNT = 20
HORIZON = 1
SEED = 42

# ─── 11 combos (ADR 0068 scope) ───────────────────────────────────────────────
#   (symbol, timeframe_str, parquet_path)
#   timeframe_str matches the KronosStrategy / CacheKey convention ("5m", "1h", etc.)
COMBOS: list[tuple[str, str, str]] = [
    ("BTCUSDT", "5m", "data/BTCUSDT_5m.parquet"),
    ("BTCUSDT", "15m", "data/BTCUSDT_15m.parquet"),
    ("BTCUSDT", "1h", "data/BTCUSDT_1h.parquet"),
    ("BTCUSDT", "4h", "data/BTCUSDT_4h.parquet"),
    ("BTCUSDT", "1d", "data/BTCUSDT_1d.parquet"),
    ("ETHUSDT", "15m", "data/ETHUSDT_15m.parquet"),
    ("ETHUSDT", "1h", "data/ETHUSDT_1h.parquet"),
    ("ETHUSDT", "4h", "data/ETHUSDT_4h.parquet"),
    ("SOLUSDT", "15m", "data/SOLUSDT_15m.parquet"),
    ("SOLUSDT", "1h", "data/SOLUSDT_1h.parquet"),
    ("SOLUSDT", "4h", "data/SOLUSDT_4h.parquet"),
]

# Timeframe string → timedelta (mirrors _build_bar_from_row in kronos_runner.py).
_TF_TO_TD: dict[str, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
}

# Output directories.
CACHE_DIR = Path("data/kronos_cache")
RESULTS_DIR = Path("data/kronos_s52_results")


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _normalize_df(path: str) -> pd.DataFrame:
    """Load parquet + normalize to unified OHLCV frame with UTC ``_ts`` column.

    Mirrors autoresearch_endless._normalize_df but renames the timestamp column
    to ``_ts`` (the column name expected by kronos_runner._build_bar_from_row).
    """
    df = pd.read_parquet(path)
    if "ts" in df.columns:
        ts_col = "ts"
    elif "time" in df.columns:
        ts_col = "time"
    elif "timestamp" in df.columns:
        ts_col = "timestamp"
    else:
        df = df.reset_index()
        ts_col = "ts" if "ts" in df.columns else "time"
    df["_ts"] = pd.to_datetime(df[ts_col], utc=True)
    df = df.sort_values("_ts").reset_index(drop=True)
    return df[["_ts", "open", "high", "low", "close", "volume"]]


def _compute_weights_hash(model_id: str, tokenizer_id: str) -> str:
    """Compute SHA-256 over HuggingFace cached weight files for both repos.

    Searches the HF cache under the default ``~/.cache/huggingface/`` tree for
    files matching the model repository AND the tokenizer repository
    (pytorch_model.bin / model.safetensors / model.ckpt). Both repos are
    separate downloads for Kronos (unlike Chronos where they are the same).
    All found weight files are sorted and hashed together for a combined
    provenance digest (C4).

    Falls back to SHA-256 of ``"model_id|tokenizer_id"`` when no files are
    found (e.g. models not yet downloaded).
    """
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    weight_extensions = {".bin", ".safetensors", ".ckpt", ".pt"}

    weight_files: list[Path] = []
    for repo_id in (model_id, tokenizer_id):
        # Repo id "org/name" → directory prefix "models--org--name"
        repo_dir_name = "models--" + repo_id.replace("/", "--")
        repo_dir = hf_cache / repo_dir_name
        if repo_dir.exists():
            for candidate in repo_dir.rglob("*"):
                if candidate.is_file() and candidate.suffix in weight_extensions:
                    weight_files.append(candidate)

    if not weight_files:
        fallback_seed = f"{model_id}|{tokenizer_id}"
        _log.warning(
            "No weight files found for %s / %s under %s; using ids as hash seed.",
            model_id,
            tokenizer_id,
            hf_cache,
        )
        return hashlib.sha256(fallback_seed.encode("utf-8")).hexdigest()

    weight_files.sort()
    h = hashlib.sha256()
    for wf in weight_files:
        _log.info("  hashing weights file: %s", wf)
        with wf.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    digest = h.hexdigest()
    _log.info("weights_hash (%d files, model+tokenizer): %s", len(weight_files), digest)
    return digest


def _build_cache_for_combo(
    *,
    symbol: str,
    timeframe: str,
    df: pd.DataFrame,
    adapter: Any,
    cache: PredictionCache,
    weights_hash: str,
    params_hash: str,
) -> int:
    """Build cache entries for every bar in ``df`` for one (symbol, timeframe) combo.

    For each bar we:
    1. Build the CacheKey with ``bar_close_ts = int((open_time + td).timestamp())``.
       This EXACTLY mirrors _build_bar_from_row + KronosStrategy.on_bar():
         open_time = row["_ts"] (tz-aware UTC datetime)
         close_time = open_time + td
         bar_close_ts = int(bar.close_time.timestamp())
    2. Skip if key already cached (idempotent rebuild).
    3. Predict using the real adapter (SAMPLE_COUNT draws).
    4. Reduce via median_ensemble → single Decimal vector.
    5. Write to cache (put).

    Returns:
        Number of newly written cache entries.
    """
    td = _TF_TO_TD.get(timeframe, timedelta(hours=1))
    written = 0

    for i, row in df.iterrows():
        open_time = pd.Timestamp(row["_ts"]).to_pydatetime()
        bar_close_ts = int((open_time + td).timestamp())

        key = CacheKey(
            model_id=MODEL_ID,
            weights_hash=weights_hash,
            symbol=symbol,
            timeframe=timeframe,
            bar_close_ts=bar_close_ts,
            params_hash=params_hash,
            device=DEVICE,
        )

        # Skip already-cached entries (idempotent).
        if cache.get(key) is not None:
            continue

        # Feed the adapter up to this bar (all rows up to and including i).
        context_df: pd.DataFrame = (
            df.iloc[: int(i) + 1].rename(columns={"_ts": "ts"}).set_index("ts")
        )

        # Draw SAMPLE_COUNT samples.
        samples: list[list[Decimal]] = []
        for _ in range(SAMPLE_COUNT):
            pred = adapter.predict(context_df, lookback=MAX_CONTEXT, horizon=HORIZON)
            samples.append(pred)

        prediction = median_ensemble(samples)
        cache.put(key, prediction)
        written += 1

    return written


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    if not RUN_ML:
        print("=" * 60)
        print("Kronos S52 cache-build + exploratory runner")
        print("=" * 60)
        print()
        print("RUN_ML is not set — skipping real model inference.")
        print()
        print("To run on operator M4 Pro (MPS):")
        print('  1. pip install -e ".[ml]"')
        print("  2. RUN_ML=1 .venv/bin/python scripts/run_kronos_s52.py")
        print()
        print("Cache artifacts  → data/kronos_cache/  (gitignored)")
        print("Results JSON     → data/kronos_s52_results/  (gitignored)")
        print()
        print("HONEST DISCLAIMER: BTC/USDT confirmed in Kronos pretrain corpus.")
        print("Results carry VERDICT_RAW_PRETRAIN_LEAKAGE_SUSPECTED — EXPLORATORY ONLY.")
        return 0

    # ── torch/Kronos imports — ONLY inside RUN_ML branch ──────────────────────
    import torch  # type: ignore[import-not-found]  # noqa: PLC0415 — guarded import
    from src.ml.kronos_adapter import KronosModelAdapter  # noqa: PLC0415

    print("=" * 60)
    print("S52 T7 — Kronos (NeoQuasar) cache-build + exploratory backtest (11 combos)")
    print("=" * 60)
    print(f"model_id      = {MODEL_ID}")
    print(f"tokenizer_id  = {TOKENIZER_ID}")
    print(f"device        = {DEVICE}")
    print(f"max_context   = {MAX_CONTEXT}")
    print(f"sample_count  = {SAMPLE_COUNT}")
    print(f"horizon       = {HORIZON}")
    print(f"seed          = {SEED}")

    # Fix torch seed for reproducibility (V4 determinism).
    torch.manual_seed(SEED)

    # Compute weights hash (C4 provenance — covers model + tokenizer repos).
    print("\nComputing weights hash ...")
    weights_hash = _compute_weights_hash(MODEL_ID, TOKENIZER_ID)
    print(f"weights_hash  = {weights_hash}")

    # Compute params hash (C4).
    sampling_params: dict[str, Any] = {
        "T": TEMPERATURE,
        "top_p": TOP_P,
        "sample_count": SAMPLE_COUNT,
        "horizon": HORIZON,
        "seed": SEED,
    }
    params_hash = hash_params(sampling_params)
    print(f"params_hash   = {params_hash}")

    # Instantiate adapter (loads model + tokenizer from HF).
    print("\nLoading Kronos adapter ...")
    adapter = KronosModelAdapter(
        model_id=MODEL_ID,
        tokenizer_id=TOKENIZER_ID,
        device=DEVICE,
        max_context=MAX_CONTEXT,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        sample_count=SAMPLE_COUNT,
    )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cache = PredictionCache(CACHE_DIR)

    all_results: list[dict[str, Any]] = []

    for symbol, timeframe, parquet_path in COMBOS:
        print(f"\n{'─' * 60}")
        print(f"Combo: {symbol} {timeframe}  ({parquet_path})")

        try:
            df = _normalize_df(parquet_path)
        except FileNotFoundError:
            _log.warning("SKIP — parquet not found: %s", parquet_path)
            all_results.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "status": "skipped_data_missing",
                }
            )
            continue

        print(
            f"  loaded {len(df):,} bars  "
            f"{df['_ts'].iloc[0].date()} → {df['_ts'].iloc[-1].date()}"
        )

        if len(df) < 50:
            _log.warning("SKIP — too few bars (%d)", len(df))
            all_results.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "status": "skipped_too_few_bars",
                    "n_bars": len(df),
                }
            )
            continue

        # ── Build cache ────────────────────────────────────────────────────────
        print(f"  Building cache for {len(df):,} bars ...", flush=True)
        written = _build_cache_for_combo(
            symbol=symbol,
            timeframe=timeframe,
            df=df,
            adapter=adapter,
            cache=cache,
            weights_hash=weights_hash,
            params_hash=params_hash,
        )
        print(f"  Cache entries written: {written:,} (total in cache may be larger)")

        # ── Run exploratory backtest ────────────────────────────────────────────
        run_params: dict[str, Any] = {
            "model_id": MODEL_ID,
            "weights_hash": weights_hash,
            "params_hash": params_hash,
            "device": DEVICE,
            "threshold": "0.0025",
        }
        print("  Running exploratory backtest ...", flush=True)
        result = run_kronos_exploratory(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            params=run_params,
            cache=cache,
        )

        n_trades = result.get("n_trades", 0)
        sharpe = result.get("sharpe", float("nan"))
        total_pnl_pct = result.get("total_pnl_pct", 0.0)
        verdict = result.get("verdict", "UNKNOWN")

        print(
            f"  n_trades={n_trades}  sharpe={sharpe:.4f}  pnl%={total_pnl_pct:.2f}"
            f"  verdict={verdict}"
        )

        # Strip non-serializable trades list before JSON write.
        serializable = {k: v for k, v in result.items() if k != "trades"}
        serializable.update(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "model_id": MODEL_ID,
                "weights_hash": weights_hash,
                "params_hash": params_hash,
                "device": DEVICE,
                "n_bars": len(df),
                "cache_entries_written": written,
            }
        )
        all_results.append(serializable)

        result_path = RESULTS_DIR / f"kronos_s52_{symbol}_{timeframe}.json"
        result_path.write_text(json.dumps(serializable, indent=2, default=str))
        print(f"  Saved → {result_path}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("SUMMARY (11 combos, VERDICT_RAW_PRETRAIN_LEAKAGE_SUSPECTED)")
    print(f"{'=' * 60}")
    for r in all_results:
        sym = r.get("symbol", "?")
        tf = r.get("timeframe", "?")
        status = r.get("status", "ok")
        if status != "ok":
            print(f"  {sym:10} {tf:5}  SKIPPED ({status})")
        else:
            nt = r.get("n_trades", 0)
            sh = r.get("sharpe", float("nan"))
            pnl = r.get("total_pnl_pct", 0.0)
            print(f"  {sym:10} {tf:5}  n_trades={nt:4d}  sharpe={sh:7.4f}  pnl%={pnl:7.2f}")

    summary_path = RESULTS_DIR / "kronos_s52_summary.json"
    summary_path.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\nSummary saved → {summary_path}")
    print("\nDISCLAIMER: EXPLORATORY ONLY — RAW_PRETRAIN_LEAKAGE_SUSPECTED.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
