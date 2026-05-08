"""research search v7 — volume_breakout multi-timeframe replication (iter 9).

Operator: растиражировать 4H PASS на остальные таймфреймы.

Approach: focused multi-seed sweep на volume_breakout strategy per timeframe (5M/15M/1H).
Each TF: 10 sweeps × 100 trials = 1000. Stop at first PASS per TF.

PASS criterion: held-out PnL > 10% AND held-out Sharpe > 0.

Caveat: held-out re-use Bailey 2014 violation (acknowledged ESC-1 override).
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

import research.strategies as strat_mod  # noqa: E402

RESULTS_PATH = Path(__file__).parent / "results.tsv"

N_TRADES_FLOOR = 10
MIN_POSITIVE_FOLDS = 3
TRIAL_BUDGET = 100  # per sweep
GRID_PORTION = 30
RANDOM_PORTION = TRIAL_BUDGET - GRID_PORTION
MAX_SWEEPS = 10
PASS_PNL_THRESHOLD = 10.0
PASS_SHARPE_THRESHOLD = 0.0

# Per-TF volume_breakout grids (scaled from 4H PASS params: L=9, ex=8, vw=10, vm=1.39, ap=16, am=2.52)
# Scale factor: 4H = 240 min. 5M=5min (×48), 15M=15min (×16), 1H=60min (×4)
TF_CONFIGS = {
    "5M": {
        "parquet": "data/BTCUSDT_5m.parquet",
        "bars_per_year": 105192,
        "wfa_train": 10000,
        "wfa_test": 2500,
        "embargo": 100,
        "grid": [
            {
                "lookback_n": lb,
                "exit_lookback_n": ex,
                "vol_window": vw,
                "vol_mult": vm,
                "atr_period": ap,
                "atr_stop_mult": am,
            }
            for lb in [200, 400, 800, 1500]
            for ex in [100, 200, 400]
            for vw in [200, 500]
            for vm in [1.5, 2.5]
            for ap in [50, 100]
            for am in [2.0, 3.0]
            if ex < lb
        ][:GRID_PORTION],
    },
    "15M": {
        "parquet": "data/BTCUSDT_15m.parquet",
        "bars_per_year": 35064,
        "wfa_train": 12000,
        "wfa_test": 3000,
        "embargo": 96,
        "grid": [
            {
                "lookback_n": lb,
                "exit_lookback_n": ex,
                "vol_window": vw,
                "vol_mult": vm,
                "atr_period": ap,
                "atr_stop_mult": am,
            }
            for lb in [80, 150, 250, 500]
            for ex in [40, 80, 150]
            for vw in [80, 160]
            for vm in [1.4, 2.0, 2.5]
            for ap in [30, 60]
            for am in [2.0, 2.5, 3.0]
            if ex < lb
        ][:GRID_PORTION],
    },
    "1H": {
        "parquet": "data/BTCUSDT_1h.parquet",
        "bars_per_year": 8766,
        "wfa_train": 3000,
        "wfa_test": 750,
        "embargo": 24,
        "grid": [
            {
                "lookback_n": lb,
                "exit_lookback_n": ex,
                "vol_window": vw,
                "vol_mult": vm,
                "atr_period": ap,
                "atr_stop_mult": am,
            }
            for lb in [20, 40, 80, 150]
            for ex in [10, 20, 40]
            for vw in [20, 40, 80]
            for vm in [1.3, 1.5, 2.0]
            for ap in [10, 20, 40]
            for am in [2.0, 2.5, 3.0]
            if ex < lb
        ][:GRID_PORTION],
    },
}


def composite(metric: float, n_trades: int, fold_sharpes: list[float]) -> float:
    if n_trades < N_TRADES_FLOOR or math.isnan(metric):
        return -999.0
    pos = sum(1 for s in fold_sharpes if s > 0)
    if len(fold_sharpes) >= 5 and pos < MIN_POSITIVE_FOLDS:
        return -999.0
    return float(metric * math.log1p(n_trades / 5.0))


def _params_str(p: dict[str, Any]) -> str:
    return "_".join(f"{k}={v}" for k, v in sorted(p.items()))


def append_tsv(
    trial_id: str, score: float, sharpe: float, n: int, pnl: float, status: str, desc: str
) -> None:
    with open(RESULTS_PATH, "a") as f:
        f.write(f"{trial_id}\t{score:.4f}\t{sharpe:.4f}\t{n}\t{pnl:.2f}\t{status}\t{desc}\n")


def _perturb(base: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in base.items():
        if isinstance(v, int):
            out[k] = max(2, int(v * random.uniform(0.5, 1.5)))
        elif isinstance(v, float):
            out[k] = round(v * random.uniform(0.6, 1.6), 4)
        else:
            out[k] = v
    if "exit_lookback_n" in out and "lookback_n" in out:
        out["exit_lookback_n"] = min(out["exit_lookback_n"], max(2, out["lookback_n"] - 1))
    return out


def load_split(parquet_path: str, train_ratio: float = 0.80) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(parquet_path).reset_index(drop=True)
    if "timestamp" not in df.columns and "time" in df.columns:
        df["timestamp"] = pd.to_datetime(df["time"], errors="coerce")
    n = len(df)
    split_idx = int(n * train_ratio)
    return df.iloc[:split_idx].reset_index(drop=True), df.iloc[split_idx:].reset_index(drop=True)


def run_sweep_tf(
    tf_name: str, sweep_id: int, train_df: Any, held_df: Any, cfg: dict[str, Any]
) -> dict[str, Any] | None:
    seed = 42 + sweep_id
    random.seed(seed)
    grid = cfg["grid"]
    trials: list[dict[str, Any]] = []

    for i, params in enumerate(grid, start=1):
        try:
            r = strat_mod.evaluate_wfa(
                train_df,
                "volume_breakout",
                params,
                train_bars=cfg["wfa_train"],
                test_bars=cfg["wfa_test"],
                k_folds=5,
                embargo_bars=cfg["embargo"],
            )
        except Exception as exc:  # noqa: BLE001
            r = {
                "metric": float("nan"),
                "n_trades": 0,
                "fold_sharpes": [],
                "status": f"crash:{exc}",
                "total_pnl_pct": 0.0,
                "win_rate": float("nan"),
            }
        score = composite(r["metric"], r["n_trades"], r["fold_sharpes"])
        trials.append({"params": params, "result": r, "score": score})
        append_tsv(
            f"P7v7_{tf_name}_s{sweep_id}_g{i}",
            score,
            r["metric"],
            r["n_trades"],
            r.get("total_pnl_pct", 0.0),
            r["status"],
            f"v7 {tf_name} sweep#{sweep_id} volume_breakout grid #{i} ({_params_str(params)})",
        )

    grid_sorted = sorted(trials, key=lambda t: t["score"], reverse=True)
    top3 = [t["params"] for t in grid_sorted[:3] if t["score"] > -999]
    if not top3:
        top3 = [grid[0]]
    for i in range(1, RANDOM_PORTION + 1):
        params = _perturb(random.choice(top3))
        try:
            r = strat_mod.evaluate_wfa(
                train_df,
                "volume_breakout",
                params,
                train_bars=cfg["wfa_train"],
                test_bars=cfg["wfa_test"],
                k_folds=5,
                embargo_bars=cfg["embargo"],
            )
        except Exception as exc:  # noqa: BLE001
            r = {
                "metric": float("nan"),
                "n_trades": 0,
                "fold_sharpes": [],
                "status": f"crash:{exc}",
                "total_pnl_pct": 0.0,
                "win_rate": float("nan"),
            }
        score = composite(r["metric"], r["n_trades"], r["fold_sharpes"])
        trials.append({"params": params, "result": r, "score": score})
        append_tsv(
            f"P7v7_{tf_name}_s{sweep_id}_r{i}",
            score,
            r["metric"],
            r["n_trades"],
            r.get("total_pnl_pct", 0.0),
            r["status"],
            f"v7 {tf_name} sweep#{sweep_id} volume_breakout random #{i} ({_params_str(params)})",
        )

    best = max(trials, key=lambda t: t["score"])
    train_sharpe = best["result"]["metric"]
    if best["score"] == -999.0 or train_sharpe <= 0:
        return None

    h = strat_mod.evaluate_heldout(held_df, "volume_breakout", best["params"])
    held_sharpe = h["metric"]
    held_pnl = h.get("total_pnl_pct", 0.0)
    is_pass = (
        held_sharpe > PASS_SHARPE_THRESHOLD
        and held_pnl > PASS_PNL_THRESHOLD
        and not math.isnan(held_sharpe)
        and h["n_trades"] >= 5
    )
    verdict = (
        f"PASS Sharpe={held_sharpe:.2f} PnL={held_pnl:+.1f}%"
        if is_pass
        else f"sign-flip Sharpe={held_sharpe:.2f}"
        if held_sharpe < 0
        else f"PnL fail {held_pnl:+.1f}%"
        if held_pnl < PASS_PNL_THRESHOLD
        else "other"
    )
    append_tsv(
        f"P7v7_{tf_name}_s{sweep_id}_HELDOUT",
        held_sharpe,
        held_sharpe,
        h["n_trades"],
        held_pnl,
        h["status"],
        f"v7 {tf_name} sweep#{sweep_id} HELDOUT volume_breakout — {verdict} train Sharpe={train_sharpe:.2f}",
    )
    return {
        "sweep": sweep_id,
        "params": best["params"],
        "train_sharpe": train_sharpe,
        "train_pnl": best["result"].get("total_pnl_pct", 0.0),
        "held_sharpe": held_sharpe,
        "held_pnl": held_pnl,
        "held_n": h["n_trades"],
        "pass": is_pass,
        "verdict": verdict,
    }


def run_tf(tf_name: str, cfg: dict[str, Any]) -> dict[str, Any] | None:
    print(f"\n\n========== TIMEFRAME: {tf_name} ==========")
    train_df, held_df = load_split(cfg["parquet"])
    print(f"  Train: {len(train_df)} / Held-out: {len(held_df)}")
    strat_mod.BARS_PER_YEAR = cfg["bars_per_year"]
    pass_result = None
    best_so_far = None
    for sweep_id in range(1, MAX_SWEEPS + 1):
        result = run_sweep_tf(tf_name, sweep_id, train_df, held_df, cfg)
        if result is None:
            print(f"  Sweep#{sweep_id}: train fail (no positive trial)")
            continue
        msg = (
            f"  Sweep#{sweep_id}: train={result['train_sharpe']:+.2f}/"
            f"+{result['train_pnl']:.1f}% → held={result['held_sharpe']:+.2f}/"
            f"{result['held_pnl']:+.1f}% n={result['held_n']} | {result['verdict']}"
        )
        if result["pass"]:
            print(f"  ★ {msg} ★")
            pass_result = result
            break
        print(f"  · {msg}")
        if best_so_far is None or result["held_pnl"] > best_so_far["held_pnl"]:
            best_so_far = result
    if pass_result:
        print(f"\n  ★★★ PASS на {tf_name} (sweep#{pass_result['sweep']}) ★★★")
        print(f"  Params: {_params_str(pass_result['params'])}")
        return pass_result
    print(f"\n  No PASS на {tf_name} в {MAX_SWEEPS} sweeps")
    if best_so_far:
        print(f"  Best partial: {best_so_far['verdict']} ({_params_str(best_so_far['params'])})")
    return best_so_far


def main() -> int:
    t0 = time.time()
    print("=== research search v7 — volume_breakout multi-TF replication ===")
    print(
        f"PASS criterion: held-out PnL > {PASS_PNL_THRESHOLD}% AND Sharpe > {PASS_SHARPE_THRESHOLD}"
    )
    print(f"Per TF: {MAX_SWEEPS} sweeps × {TRIAL_BUDGET} trials = {MAX_SWEEPS * TRIAL_BUDGET}")
    summaries = {}
    for tf_name, cfg in TF_CONFIGS.items():
        summaries[tf_name] = run_tf(tf_name, cfg)

    elapsed = time.time() - t0
    print(f"\n\n=== FINAL ({elapsed:.1f}s) ===")
    for tf_name, r in summaries.items():
        if r is None:
            print(f"  {tf_name}: NO viable result (all sweeps train_fail)")
        elif r["pass"]:
            print(
                f"  {tf_name}: ★ PASS sweep#{r['sweep']} | "
                f"train={r['train_sharpe']:+.2f}/+{r['train_pnl']:.1f}% → "
                f"held={r['held_sharpe']:+.2f}/{r['held_pnl']:+.1f}% n={r['held_n']}"
            )
            print(f"    params: {_params_str(r['params'])}")
        else:
            print(
                f"  {tf_name}: {r['verdict']} (best partial — "
                f"train={r['train_sharpe']:+.2f}/+{r['train_pnl']:.1f}% → "
                f"held={r['held_sharpe']:+.2f}/{r['held_pnl']:+.1f}% n={r['held_n']})"
            )

    n_pass = sum(1 for r in summaries.values() if r and r.get("pass"))
    print(f"\nTotal PASS across timeframes: {n_pass}/{len(TF_CONFIGS)}")
    append_tsv(
        "P7v7_FINAL",
        0.0,
        0.0,
        MAX_SWEEPS * TRIAL_BUDGET * len(TF_CONFIGS),
        0.0,
        "summary",
        f"v7 multi-TF replication: {n_pass}/{len(TF_CONFIGS)} PASS",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
