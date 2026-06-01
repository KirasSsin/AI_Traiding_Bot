"""S53 T7 — Kronos (NeoQuasar) cache-build + exploratory backtest runner (11 combos).

Variant-driven: uses KronosVariant singletons (no hardcoded MODEL_ID/TOKENIZER_ID).
Selects variant via ``--variant {base,mini}`` CLI arg (or ``KRONOS_VARIANT`` env,
default ``base``).

OPERATOR INSTRUCTIONS (Mac M4 Pro, MPS):
  1. pip install -e ".[ml]"
  2. RUN_ML=1 .venv/bin/python scripts/run_kronos_s53.py --variant base

Without RUN_ML=1 this script prints these instructions and exits 0.
torch is never imported unless RUN_ML=1 is set.

CACHE ARTIFACTS → data/kronos_cache/  (gitignored — never committed).
RESULTS JSON    → data/kronos_s53_results/  (gitignored — never committed).

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

WARNING (CC4): changing variant/tokenizer changes weights_hash → old cache entries
  become MISS → full rebuild required.
"""

from __future__ import annotations

import argparse
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
from src.ml.kronos_variant import KronosVariant, variant_by_name
from src.ml.prediction_cache import CacheKey, PredictionCache, hash_params, median_ensemble

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
_log = logging.getLogger(__name__)

# ─── Guard ────────────────────────────────────────────────────────────────────
RUN_ML: bool = os.environ.get("RUN_ML") == "1"

# ─── Kronos config ────────────────────────────────────────────────────────────
DEVICE = "mps"
TEMPERATURE = 1.0
TOP_P = 0.9
SAMPLE_COUNT = 20
HORIZON = 1
SEED = 42

# SECURITY: model + tokenizer HF repos are pinned to verified commit SHAs in
# `KronosVariant` (src/ml/kronos_variant.py) — version-controlled, not env. Each
# repo has its own pin (model and tokenizer are SEPARATE repos with different
# SHAs). from_pretrained deserializes untrusted checkpoints (torch.load = ACE);
# the in-code pins are the ACE defense. weights_hash = post-download provenance.

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
RESULTS_DIR = Path("data/kronos_s53_results")

# FIX A (PHASE 6 R2) — manifest sidecar. Mirrors S51 D2 parquet-manifest pattern.
# Captures the cache-key-defining params (model_id, weights_hash, params_hash,
# device) so the dashboard can reconstruct CacheKeys matching this build → HITS.
MANIFEST_NAME = "_manifest.json"
MANIFEST_SCHEMA_VERSION = 1


# ─── Variant resolution ───────────────────────────────────────────────────────


def resolve_variant(name: str) -> KronosVariant:
    """Resolve a KronosVariant by name (``base`` | ``mini``).

    Delegates to ``variant_by_name`` from ``src.ml.kronos_variant``.
    Exposed at module level so smoke tests can verify singleton identity.
    """
    return variant_by_name(name)


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


def _compute_weights_hash(variant: KronosVariant) -> str:
    """Compute SHA-256 over HuggingFace cached weight files for the variant's repos.

    Searches the HF cache under the default ``~/.cache/huggingface/`` tree for
    files matching variant.model_id AND variant.tokenizer_id
    (pytorch_model.bin / model.safetensors / model.ckpt). Both repos are
    separate downloads for Kronos (unlike Chronos where they are the same).
    All found weight files are sorted and hashed together for a combined
    provenance digest (C4).

    Falls back to SHA-256 of ``"model_id|tokenizer_id"`` when no files are
    found (e.g. models not yet downloaded).

    WARNING (CC4): changing variant/tokenizer changes weights_hash -> old cache
    entries become MISS -> full rebuild required.
    """
    model_id = variant.model_id
    tokenizer_id = variant.tokenizer_id
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    weight_extensions = {".bin", ".safetensors", ".ckpt", ".pt"}

    weight_files: list[Path] = []
    for repo_id in (model_id, tokenizer_id):
        # Repo id "org/name" -> directory prefix "models--org--name"
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
    model_id: str,
    weights_hash: str,
    params_hash: str,
    max_context: int,
    max_bars: int | None = None,
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
    4. Reduce via median_ensemble -> single Decimal vector.
    5. Write to cache (put).

    Returns:
        Number of newly written cache entries.
    """
    td = _TF_TO_TD.get(timeframe, timedelta(hours=1))
    written = 0
    # Only build cache for the last ``max_bars`` bars (earlier bars still serve
    # as model context via df.iloc[:i+1]). Full-history build is intractable.
    start_idx = 0 if max_bars is None else max(0, len(df) - max_bars)

    for i, row in df.iterrows():
        if int(i) < start_idx:
            continue
        open_time = pd.Timestamp(row["_ts"]).to_pydatetime()
        bar_close_ts = int((open_time + td).timestamp())

        key = CacheKey(
            model_id=model_id,
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
            pred = adapter.predict(context_df, lookback=max_context, horizon=HORIZON)
            samples.append(pred)

        prediction = median_ensemble(samples)
        cache.put(key, prediction)
        written += 1

    return written


def _write_manifest(
    *,
    cache_dir: Path,
    model_id: str,
    weights_hash: str,
    params_hash: str,
    combos_coverage: list[dict[str, Any]],
) -> None:
    """Write/merge ``<cache_dir>/_manifest.json`` (FIX A, PHASE 6 R2).

    Captures the 4 non-(symbol, timeframe, bar_close_ts) cache-key fields the
    dashboard needs to reconstruct matching :class:`CacheKey`s: ``model_id``,
    ``weights_hash``, ``params_hash``, ``device``. Includes a schema version and
    the per-combo coverage list. If a manifest already exists, the key params are
    overwritten (consistent build) and the combo coverage is merged by
    (symbol, timeframe) so a partial re-run does not drop prior combos.
    """
    manifest_path = cache_dir / MANIFEST_NAME

    merged_combos: dict[tuple[str, str], dict[str, Any]] = {}
    if manifest_path.exists():
        try:
            prior: dict[str, Any] = json.loads(manifest_path.read_text())
            for entry in prior.get("combos", []):
                merged_combos[(entry["symbol"], entry["timeframe"])] = entry
        except (json.JSONDecodeError, OSError, KeyError):
            merged_combos = {}

    for entry in combos_coverage:
        merged_combos[(entry["symbol"], entry["timeframe"])] = entry

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "model_id": model_id,
        "weights_hash": weights_hash,
        "params_hash": params_hash,
        "device": DEVICE,
        "combos": sorted(merged_combos.values(), key=lambda e: (e["symbol"], e["timeframe"])),
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    combos_list: list[Any] = manifest["combos"]  # type: ignore[assignment]
    _log.info("Wrote manifest -> %s (%d combos)", manifest_path, len(combos_list))


# ─── Main ─────────────────────────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments (or ``argv`` for testing)."""
    parser = argparse.ArgumentParser(
        description="Kronos S53 cache-build + exploratory runner (11 combos)"
    )
    parser.add_argument(
        "--variant",
        choices=["base", "mini"],
        default=os.environ.get("KRONOS_VARIANT", "base"),
        help="Kronos variant to use (default: base or KRONOS_VARIANT env).",
    )
    parser.add_argument(
        "--max-bars",
        type=int,
        default=None,
        help=(
            "Build cache only for the LAST N bars per combo (earlier bars still "
            "serve as model context). Full-history per-bar build is intractable "
            "(BTC 1h = 29k bars × sample_count). Recommended for exploratory runs, "
            "e.g. --max-bars 500. Default None = all bars (very slow)."
        ),
    )
    parser.add_argument(
        "--symbols",
        default=None,
        help=(
            "Comma-separated symbols to build (e.g. 'BTCUSDT' or 'BTCUSDT,ETHUSDT'). "
            "Default None = all. Use to run a single combo fast — the script "
            "otherwise iterates all 11 (symbol,timeframe) combos."
        ),
    )
    parser.add_argument(
        "--timeframes",
        default=None,
        help=(
            "Comma-separated timeframes to build (e.g. '1h' or '1h,4h'). "
            "Default None = all. Combine with --symbols to pin one combo."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point. ``argv`` overrides sys.argv for testing."""
    args = _parse_args(argv)
    variant = resolve_variant(args.variant)

    if not RUN_ML:
        print("=" * 60)
        print("Kronos S53 cache-build + exploratory runner")
        print("=" * 60)
        print()
        print("RUN_ML is not set — skipping real model inference.")
        print()
        print(f"variant       = {variant.name}  ({variant.model_id})")
        print(f"tokenizer_id  = {variant.tokenizer_id}")
        print(f"max_context   = {variant.max_context}")
        print()
        print("WARNING: changing variant/tokenizer changes weights_hash ->")
        print("         old cache entries become MISS -> full rebuild required.")
        print()
        print("To run on operator M4 Pro (MPS):")
        print('  1. pip install -e ".[ml]"')
        print(f"  2. RUN_ML=1 .venv/bin/python scripts/run_kronos_s53.py --variant {variant.name}")
        print()
        print("Cache artifacts  -> data/kronos_cache/  (gitignored)")
        print("Results JSON     -> data/kronos_s53_results/  (gitignored)")
        print()
        print("HONEST DISCLAIMER: BTC/USDT confirmed in Kronos pretrain corpus.")
        print("Results carry VERDICT_RAW_PRETRAIN_LEAKAGE_SUSPECTED — EXPLORATORY ONLY.")
        return 0

    # ── torch/Kronos imports — ONLY inside RUN_ML branch ──────────────────────
    import torch  # type: ignore[import-not-found]  # noqa: PLC0415 — guarded import
    from src.ml.kronos_adapter import KronosModelAdapter  # noqa: PLC0415

    print("=" * 60)
    print("S53 T7 — Kronos (NeoQuasar) cache-build + exploratory backtest (11 combos)")
    print("=" * 60)
    print(f"variant       = {variant.name}")
    print(f"model_id      = {variant.model_id}")
    print(f"tokenizer_id  = {variant.tokenizer_id}")
    print(f"max_context   = {variant.max_context}")
    print(f"device        = {DEVICE}")
    print(f"sample_count  = {SAMPLE_COUNT}")
    print(f"horizon       = {HORIZON}")
    print(f"seed          = {SEED}")
    print()
    print("WARNING: changing variant/tokenizer changes weights_hash ->")
    print("         old cache entries become MISS -> full rebuild required.")

    # Fix torch seed for reproducibility (V4 determinism).
    torch.manual_seed(SEED)

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

    # Instantiate adapter FIRST (downloads model + tokenizer weights to HF cache).
    # weights_hash is computed AFTER instantiation so weight files are guaranteed
    # on disk — avoids fallback hash on first-run (FIX 4, PHASE 6 R1).
    print("\nLoading Kronos adapter ...")
    print(f"model_rev     = {variant.model_revision}")
    print(f"tokenizer_rev = {variant.tokenizer_revision}")
    adapter = KronosModelAdapter(
        variant=variant,
        device=DEVICE,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        sample_count=SAMPLE_COUNT,
    )

    # Compute weights hash (C4 provenance — covers model + tokenizer repos).
    # Must run AFTER adapter init so weight files are present.
    print("\nComputing weights hash ...")
    weights_hash = _compute_weights_hash(variant)
    print(f"weights_hash  = {weights_hash}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cache = PredictionCache(CACHE_DIR)

    all_results: list[dict[str, Any]] = []
    combos_coverage: list[dict[str, Any]] = []

    # Optional combo filter — run a single (symbol, timeframe) fast instead of all 11.
    sym_filter = {s.strip() for s in args.symbols.split(",")} if args.symbols else None
    tf_filter = {t.strip() for t in args.timeframes.split(",")} if args.timeframes else None
    combos = [
        c
        for c in COMBOS
        if (sym_filter is None or c[0] in sym_filter) and (tf_filter is None or c[1] in tf_filter)
    ]
    if not combos:
        print(f"No combos match --symbols={args.symbols} --timeframes={args.timeframes}")
        return 1
    print(f"Building {len(combos)} of {len(COMBOS)} combos.")

    for symbol, timeframe, parquet_path in combos:
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
            f"{df['_ts'].iloc[0].date()} -> {df['_ts'].iloc[-1].date()}"
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
        n_build = len(df) if args.max_bars is None else min(len(df), args.max_bars)
        print(f"  Building cache for {n_build:,} bars (of {len(df):,}) ...", flush=True)
        written = _build_cache_for_combo(
            symbol=symbol,
            timeframe=timeframe,
            df=df,
            adapter=adapter,
            cache=cache,
            model_id=variant.model_id,
            weights_hash=weights_hash,
            params_hash=params_hash,
            max_context=variant.max_context,
            max_bars=args.max_bars,
        )
        print(f"  Cache entries written: {written:,} (total in cache may be larger)")

        # Track per-combo coverage for the manifest sidecar (FIX A).
        combos_coverage.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "n_bars": int(len(df)),
                "n_entries_written": int(written),
            }
        )

        # ── Run exploratory backtest ────────────────────────────────────────────
        run_params: dict[str, Any] = {
            "model_id": variant.model_id,
            "weights_hash": weights_hash,
            "params_hash": params_hash,
            "device": DEVICE,
            "threshold": "0.006",
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
                "model_id": variant.model_id,
                "weights_hash": weights_hash,
                "params_hash": params_hash,
                "device": DEVICE,
                "n_bars": len(df),
                "cache_entries_written": written,
            }
        )
        all_results.append(serializable)

        result_path = RESULTS_DIR / f"kronos_s53_{symbol}_{timeframe}.json"
        result_path.write_text(json.dumps(serializable, indent=2, default=str))
        print(f"  Saved -> {result_path}")

    # ── Write manifest sidecar (FIX A) so the dashboard reconstructs matching keys ──
    _write_manifest(
        cache_dir=CACHE_DIR,
        model_id=variant.model_id,
        weights_hash=weights_hash,
        params_hash=params_hash,
        combos_coverage=combos_coverage,
    )

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

    summary_path = RESULTS_DIR / "kronos_s53_summary.json"
    summary_path.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\nSummary saved -> {summary_path}")
    print("\nDISCLAIMER: EXPLORATORY ONLY — RAW_PRETRAIN_LEAKAGE_SUSPECTED.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
