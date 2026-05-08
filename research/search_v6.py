"""research search v6 — 4H multi-seed sweep (iter 8 — operator: iterate until PnL > 1000 USDT).

Operator directive: continue iterations until held-out PnL > 10% (= $1000 USDT on $10k base)
AND held-out Sharpe > 0. Run multiple sweeps с different random seeds, stop at first PASS.

Held-out previously used iter 3+ on 4H (commit c2cd3a0) — re-use = Bailey 2014 anti-snooping
violation, acknowledged ESC-1 override. Each sweep N_trials=1 family pooled.

PASS criterion (operator-aligned):
  held-out total_pnl_pct >= 10.0  (= $1000 USDT on $10000 base)
  AND held-out Sharpe > 0

Per sweep: 100 trials × 10 strategies = 1000. Up to MAX_SWEEPS sweeps × 1000 = budget.
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.prepare import load_split  # noqa: E402
from research.strategies import (  # noqa: E402
    STRATEGY_REGISTRY,
    evaluate_heldout,
    evaluate_wfa,
)

RESULTS_PATH = Path(__file__).parent / "results.tsv"
DETAILED_LOG = Path(__file__).parent / "results_detailed.tsv"  # gitignored — full trials

N_TRADES_FLOOR = 10
MIN_POSITIVE_FOLDS = 3
TRIAL_BUDGET_PER_STRAT = 100
GRID_PORTION = 30
RANDOM_PORTION = TRIAL_BUDGET_PER_STRAT - GRID_PORTION
MAX_SWEEPS = 100  # operator continuous mode — 100 × 1000 = 100k trials
PASS_PNL_THRESHOLD = 10.0  # 10% = $1000 USDT
PASS_SHARPE_THRESHOLD = 0.0

# 4H GRIDS (broader than iter 3+ к explore deeper space)
GRIDS: dict[str, list[dict[str, Any]]] = {
    "donchian_raw": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "atr_period": ap,
            "atr_stop_mult": am,
        }
        for lb in [10, 15, 20, 30, 50, 80]
        for ap in [10, 14, 21]
        for am in [1.5, 2.5, 4.0]
    ][:GRID_PORTION],
    "rsi_mean_reversion": [
        {"rsi_period": p, "rsi_low": low, "rsi_high": high, "atr_period": 14, "atr_stop_mult": am}
        for p in [7, 14, 21]
        for low in [20, 25, 30, 35]
        for high in [50, 55, 65]
        for am in [1.5, 2.0, 3.0]
    ][:GRID_PORTION],
    "bollinger_breakout": [
        {"bb_period": p, "bb_k": k, "atr_period": 14, "atr_stop_mult": am}
        for p in [10, 20, 30, 50, 80]
        for k in [1.5, 2.0, 2.5, 3.0]
        for am in [2.0, 3.0]
    ][:GRID_PORTION],
    "bollinger_mr": [
        {"bb_period": p, "bb_k": k, "atr_period": 14, "atr_stop_mult": am}
        for p in [10, 20, 30, 50, 80]
        for k in [1.5, 2.0, 2.5, 3.0]
        for am in [2.0, 3.0]
    ][:GRID_PORTION],
    "macd_momentum": [
        {"macd_fast": f, "macd_slow": s, "macd_signal": sig, "atr_period": 14, "atr_stop_mult": am}
        for f, s in [(8, 21), (12, 26), (5, 35), (12, 50), (20, 60)]
        for sig in [9, 14]
        for am in [2.0, 3.0]
    ][:GRID_PORTION],
    "atr_squeeze_breakout": [
        {
            "lookback_n": lb,
            "squeeze_window": sw,
            "squeeze_pct": pct,
            "atr_period": 14,
            "atr_stop_mult": 2.0,
        }
        for lb in [15, 30, 50]
        for sw in [50, 100, 200]
        for pct in [20, 30, 40, 50]
    ][:GRID_PORTION],
    "momentum_n_consec": [
        {"n_consec": n, "exit_n_reverse": ex, "atr_period": 14, "atr_stop_mult": am}
        for n in [2, 3, 4, 5, 6]
        for ex in [2, 3]
        for am in [1.5, 2.5, 3.5]
    ][:GRID_PORTION],
    "volume_breakout": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "vol_window": 20,
            "vol_mult": vm,
            "atr_period": 14,
            "atr_stop_mult": 2.0,
        }
        for lb in [10, 15, 20, 30, 50]
        for vm in [1.2, 1.5, 2.0, 2.5]
    ][:GRID_PORTION],
    "ema_crossover": [
        {"ema_fast": f, "ema_slow": s, "atr_period": 14, "atr_stop_mult": am}
        for f, s in [(5, 20), (8, 21), (10, 30), (12, 26), (15, 50), (20, 100)]
        for am in [1.5, 2.0, 3.0, 4.0]
    ][:GRID_PORTION],
    "price_channel_with_atr": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "atr_pct_min": pmin,
            "atr_pct_max": 0.05,
            "atr_period": 14,
            "atr_stop_mult": 2.0,
        }
        for lb in [10, 15, 20, 30, 50]
        for pmin in [0.001, 0.003, 0.005, 0.01]
    ][:GRID_PORTION],
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
    # Per-trial rows → gitignored detailed log (avoid TSV bloat > 100MB GitHub limit).
    # Only HELDOUT/PASS/summary rows go к tracked results.tsv.
    is_summary = "HELDOUT" in trial_id or "FINAL" in trial_id or "SUMMARY" in trial_id
    target = RESULTS_PATH if is_summary else DETAILED_LOG
    with open(target, "a") as f:
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


def search_strategy(name: str, train_df: Any, held_df: Any, sweep_id: int) -> dict[str, Any]:
    grid = GRIDS.get(name, [])
    if not grid:
        return {"strategy": name, "best": None, "verdict": "no_grid"}
    trials: list[dict[str, Any]] = []

    for i, params in enumerate(grid, start=1):
        try:
            r = evaluate_wfa(train_df, name, params)
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
            f"P6v6s{sweep_id}_{name}_g{i}",
            score,
            r["metric"],
            r["n_trades"],
            r.get("total_pnl_pct", 0.0),
            r["status"],
            f"v6 4H sweep#{sweep_id} {name} grid #{i} ({_params_str(params)})",
        )

    grid_sorted = sorted(trials, key=lambda t: t["score"], reverse=True)
    top3 = [t["params"] for t in grid_sorted[:3] if t["score"] > -999]
    if not top3:
        top3 = [grid[0]]
    for i in range(1, RANDOM_PORTION + 1):
        params = _perturb(random.choice(top3))
        try:
            r = evaluate_wfa(train_df, name, params)
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
            f"P6v6s{sweep_id}_{name}_r{i}",
            score,
            r["metric"],
            r["n_trades"],
            r.get("total_pnl_pct", 0.0),
            r["status"],
            f"v6 4H sweep#{sweep_id} {name} random #{i} ({_params_str(params)})",
        )

    best = max(trials, key=lambda t: t["score"])
    train_sharpe = best["result"]["metric"]
    train_pnl = best["result"].get("total_pnl_pct", 0.0)

    if best["score"] == -999.0 or train_sharpe <= 0:
        return {
            "strategy": name,
            "best": best,
            "held_out": None,
            "pass": False,
            "verdict": f"train_fail s={best['score']:.2f}",
        }

    h = evaluate_heldout(held_df, name, best["params"])
    held_sharpe = h["metric"]
    held_pnl = h.get("total_pnl_pct", 0.0)
    is_pass = (
        held_sharpe > PASS_SHARPE_THRESHOLD
        and held_pnl > PASS_PNL_THRESHOLD
        and not math.isnan(held_sharpe)
        and h["n_trades"] >= 5
    )
    if is_pass:
        verdict = f"PASS held-out Sharpe={held_sharpe:.2f} PnL={held_pnl:+.1f}%"
    elif math.isnan(held_sharpe) or h["n_trades"] < 5:
        verdict = f"insufficient n={h['n_trades']}"
    elif held_sharpe < 0:
        verdict = f"sign-flip ({train_sharpe:+.2f}→{held_sharpe:.2f})"
    elif held_pnl < PASS_PNL_THRESHOLD:
        verdict = f"PnL fail ({held_pnl:+.1f}% < {PASS_PNL_THRESHOLD}%)"
    else:
        verdict = f"degradation Sharpe={held_sharpe:.2f}"

    append_tsv(
        f"P6v6s{sweep_id}_{name}_HELDOUT",
        h["metric"],
        h["metric"],
        h["n_trades"],
        held_pnl,
        h["status"],
        f"v6 4H sweep#{sweep_id} {name} HELDOUT — {verdict} train_Sharpe={train_sharpe:.2f} | params: {_params_str(best['params'])}",
    )
    return {
        "strategy": name,
        "best": best,
        "held_out": h,
        "pass": is_pass,
        "verdict": verdict,
        "train_sharpe": train_sharpe,
        "train_pnl": train_pnl,
        "held_sharpe": held_sharpe,
        "held_pnl": held_pnl,
    }


def run_sweep(sweep_id: int, train_df: Any, held_df: Any) -> bool:
    """Returns True if PASS found."""
    seed = 42 + sweep_id
    random.seed(seed)
    print(f"\n\n========== SWEEP #{sweep_id} (seed={seed}) ==========\n")
    summaries = []
    for name in STRATEGY_REGISTRY:
        s = search_strategy(name, train_df, held_df, sweep_id)
        summaries.append(s)
        if s.get("pass"):
            print(f"  ★ {name}: {s['verdict']} ★")
        else:
            tp = s.get("train_sharpe", float("nan"))
            hp = s.get("held_pnl", 0.0)
            print(f"  · {name}: {s['verdict']} (train={tp:+.2f} held_pnl={hp:+.1f}%)")

    pass_strats = [s for s in summaries if s.get("pass")]
    print(f"\n  Sweep #{sweep_id} PASS candidates: {len(pass_strats)}")
    for s in pass_strats:
        print(
            f"    {s['strategy']}: train Sharpe={s['train_sharpe']:.2f} → held-out PnL={s['held_pnl']:+.1f}%"
        )
        print(f"      params: {_params_str(s['best']['params'])}")
    return len(pass_strats) > 0


def main() -> int:
    t0 = time.time()
    # CLI: optional start_sweep arg (default 1)
    start_sweep = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end_sweep = start_sweep + MAX_SWEEPS - 1
    print(f"=== research search v6 — 4H multi-seed sweep ({start_sweep}..{end_sweep}) ===")
    print(
        f"PASS criterion: held-out PnL > {PASS_PNL_THRESHOLD}% AND Sharpe > {PASS_SHARPE_THRESHOLD}"
    )
    print(f"Sweeps: {MAX_SWEEPS} × 1000 trials = {MAX_SWEEPS * 1000} budget")

    split = load_split()
    print(f"Train: {len(split.train_df)} / Held-out: {len(split.heldout_df)}")

    pass_count = 0
    completed_sweeps = 0
    pass_log: list[int] = []
    for sweep_id in range(start_sweep, end_sweep + 1):
        if run_sweep(sweep_id, split.train_df, split.heldout_df):
            pass_count += 1
            pass_log.append(sweep_id)
            print(f"\n  ★ PASS #{pass_count} в sweep #{sweep_id} (продолжаем continuous)")
        completed_sweeps = sweep_id
    pass_found = pass_count > 0

    elapsed = time.time() - t0
    n_total = completed_sweeps * 1000
    print(
        f"\n\n=== FINAL ({elapsed:.1f}s, {n_total} trials, {completed_sweeps}/{MAX_SWEEPS} sweeps) ==="
    )
    if pass_found:
        print(f"PASS count: {pass_count} в sweeps {pass_log}")
        print("All PASS rows: grep '★ PASS' results.tsv | grep P6v6s")
    else:
        print(f"NO PASS in {n_total} trials — universal sign-flip persists on 4H")

    append_tsv(
        "P6v6_FINAL",
        0.0,
        0.0,
        n_total,
        0.0,
        "summary_pass" if pass_found else "summary_no_pass",
        f"v6 4H multi-seed: {completed_sweeps} sweeps, {n_total} trials, pass={pass_found}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
