"""research search v2 — autonomous 100-trial loop с EMA filter dimension (iter 2).

Differences vs search.py (iter 1):
  - Uses research.backtest_v2.evaluate_wfa (self-contained, EMA filter aware)
  - 5-dim search space: lookback_n, exit_lookback_n, atr_period, atr_stop_mult, ema_filter_period
  - Phase 6 added: ema_filter_period sweep ∈ {0, 50, 100, 150, 200, 250, 300}
  - Phase 5 random also perturbs ema_filter_period

Composite scoring identical: score = agg_sharpe * log1p(n_trades / 5.0)
Safeguards: n_trades < 10 → -999. <3/5 folds positive → -999.

Output: results.tsv appended (iter 2 trials prefixed P*v2_).
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.backtest_v2 import evaluate_wfa
from research.prepare import load_split

random.seed(42)

RESULTS_PATH = Path(__file__).parent / "results.tsv"

N_TRADES_FLOOR = 10
MIN_POSITIVE_FOLDS = 3
EARLY_STOP_NO_IMPROVE = 30
EARLY_STOP_SCORE_THRESHOLD = 2.5
TRIAL_BUDGET = 100


def composite_score(*, metric: float, n_trades: int, fold_sharpes: list[float]) -> float:
    if n_trades < N_TRADES_FLOOR:
        return -999.0
    if math.isnan(metric):
        return -999.0
    positive_folds = sum(1 for s in fold_sharpes if s > 0)
    if len(fold_sharpes) >= 5 and positive_folds < MIN_POSITIVE_FOLDS:
        return -999.0
    return float(metric * math.log1p(n_trades / 5.0))


def run_trial(train_df: Any, params: dict[str, Any], trial_id: str) -> dict[str, Any]:
    t0 = time.time()
    try:
        result = evaluate_wfa(train_df, params)
    except Exception as exc:  # noqa: BLE001
        return {
            "trial_id": trial_id,
            "params": params,
            "score": -999.0,
            "metric": float("nan"),
            "n_trades": 0,
            "total_pnl_pct": 0.0,
            "win_rate": float("nan"),
            "fold_sharpes": [],
            "fold_pnls": [],
            "status": "crash",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed": time.time() - t0,
        }
    score = composite_score(
        metric=result["metric"],
        n_trades=result["n_trades"],
        fold_sharpes=result["fold_sharpes"],
    )
    return {
        "trial_id": trial_id,
        "params": params,
        "score": score,
        "metric": result["metric"],
        "n_trades": result["n_trades"],
        "total_pnl_pct": result.get("total_pnl_pct", 0.0),
        "win_rate": result.get("win_rate", float("nan")),
        "fold_sharpes": result["fold_sharpes"],
        "fold_pnls": result.get("fold_pnls", []),
        "status": result["status"],
        "elapsed": time.time() - t0,
    }


def append_result(r: dict[str, Any], description: str) -> None:
    with open(RESULTS_PATH, "a") as f:
        p = r["params"]
        params_str = (
            f"L{p['lookback_n']}E{p['exit_lookback_n']}"
            f"A{p['atr_stop_mult']}P{p['atr_period']}"
            f"EMA{p.get('ema_filter_period', 0)}"
        )
        f.write(
            f"{r['trial_id']}\t"
            f"{r['score']:.4f}\t"
            f"{r['metric']:.4f}\t"
            f"{r['n_trades']}\t"
            f"{r.get('total_pnl_pct', 0.0):.2f}\t"
            f"{r['status']}\t"
            f"{description} ({params_str})\n"
        )


def fmt(r: dict[str, Any]) -> str:
    return (
        f"score={r['score']:+.3f} sharpe={r['metric']:+.3f} "
        f"pnl={r.get('total_pnl_pct', 0):+6.1f}% n={r['n_trades']:3d} "
        f"win={r.get('win_rate', 0):.2f}"
    )


def phase1_lookback_sweep(train_df: Any) -> list[dict[str, Any]]:
    print("\n=== PHASE 1: lookback_n sweep (7 trials, ema=0 baseline) ===")
    results = []
    for i, lb in enumerate([5, 10, 15, 20, 30, 40, 55], start=1):
        params = {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "atr_period": 14,
            "atr_stop_mult": 2.0,
            "ema_filter_period": 0,
        }
        r = run_trial(train_df, params, f"P1v2_{i}")
        results.append(r)
        print(f"  P1v2_{i} L={lb} → {fmt(r)}")
        append_result(r, "p1v2 lookback sweep")
    return results


def phase2_atr_sweep(train_df: Any, best_lb: int) -> list[dict[str, Any]]:
    print(f"\n=== PHASE 2: atr_mult sweep on L={best_lb} (8 trials) ===")
    results = []
    for i, am in enumerate([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0], start=1):
        params = {
            "lookback_n": best_lb,
            "exit_lookback_n": max(2, best_lb // 2),
            "atr_period": 14,
            "atr_stop_mult": am,
            "ema_filter_period": 0,
        }
        r = run_trial(train_df, params, f"P2v2_{i}")
        results.append(r)
        print(f"  P2v2_{i} ATR×{am} → {fmt(r)}")
        append_result(r, "p2v2 atr sweep")
    return results


def phase3_exit_sweep(train_df: Any, best_lb: int, best_am: float) -> list[dict[str, Any]]:
    print(f"\n=== PHASE 3: exit_lb sweep on L={best_lb} ATR×{best_am} (5 trials) ===")
    results = []
    for i, ratio in enumerate([0.25, 0.4, 0.5, 0.7, 0.9], start=1):
        ex = max(2, int(best_lb * ratio))
        if ex >= best_lb:
            ex = best_lb - 1
        params = {
            "lookback_n": best_lb,
            "exit_lookback_n": ex,
            "atr_period": 14,
            "atr_stop_mult": best_am,
            "ema_filter_period": 0,
        }
        r = run_trial(train_df, params, f"P3v2_{i}")
        results.append(r)
        print(f"  P3v2_{i} E={ex} → {fmt(r)}")
        append_result(r, f"p3v2 exit ratio {ratio}")
    return results


def phase4_atr_period_sweep(
    train_df: Any, best_lb: int, best_ex: int, best_am: float
) -> list[dict[str, Any]]:
    print("\n=== PHASE 4: atr_period sweep (5 trials) ===")
    results = []
    for i, ap in enumerate([7, 10, 14, 21, 30], start=1):
        params = {
            "lookback_n": best_lb,
            "exit_lookback_n": best_ex,
            "atr_period": ap,
            "atr_stop_mult": best_am,
            "ema_filter_period": 0,
        }
        r = run_trial(train_df, params, f"P4v2_{i}")
        results.append(r)
        print(f"  P4v2_{i} P={ap} → {fmt(r)}")
        append_result(r, f"p4v2 atr_period {ap}")
    return results


def phase6_ema_sweep(
    train_df: Any, best_lb: int, best_ex: int, best_ap: int, best_am: float
) -> list[dict[str, Any]]:
    """NEW iter 2: EMA filter dimension sweep on best 4D base."""
    print(
        f"\n=== PHASE 6: EMA filter sweep on L={best_lb} E={best_ex} P={best_ap} ATR×{best_am} (7 trials) ==="
    )
    results = []
    for i, ema in enumerate([0, 50, 100, 150, 200, 250, 300], start=1):
        params = {
            "lookback_n": best_lb,
            "exit_lookback_n": best_ex,
            "atr_period": best_ap,
            "atr_stop_mult": best_am,
            "ema_filter_period": ema,
        }
        r = run_trial(train_df, params, f"P6v2_{i}")
        results.append(r)
        print(f"  P6v2_{i} EMA={ema} → {fmt(r)}")
        append_result(r, f"p6v2 ema {ema}")
    return results


def phase5_random(
    train_df: Any, best_params: dict[str, Any], n_trials: int
) -> list[dict[str, Any]]:
    """Random perturbation around best 5-dim params (±20-50%)."""
    print(f"\n=== PHASE 5: random exploration around best ({n_trials} trials) ===")
    results = []
    no_improve = 0
    best_score_so_far = -999.0
    base_ema = best_params.get("ema_filter_period", 0)
    for i in range(1, n_trials + 1):
        lb = max(3, int(best_params["lookback_n"] * random.uniform(0.6, 1.5)))
        ex = max(2, int(lb * random.uniform(0.3, 0.7)))
        if ex >= lb:
            ex = lb - 1
        ap = max(5, int(best_params["atr_period"] * random.uniform(0.6, 1.5)))
        am = max(0.5, best_params["atr_stop_mult"] * random.uniform(0.6, 1.6))
        # EMA: 30% chance off, otherwise jitter ±50%
        if random.random() < 0.3:
            ema = 0
        else:
            base = base_ema if base_ema > 0 else 200
            ema = max(20, int(base * random.uniform(0.5, 1.7)))
        params = {
            "lookback_n": lb,
            "exit_lookback_n": ex,
            "atr_period": ap,
            "atr_stop_mult": round(am, 2),
            "ema_filter_period": ema,
        }
        r = run_trial(train_df, params, f"P5v2_{i}")
        results.append(r)
        improved = "↑" if r["score"] > best_score_so_far else " "
        print(
            f"  P5v2_{i} L={lb} E={ex} P={ap} ATR×{params['atr_stop_mult']} EMA={ema} → {fmt(r)} {improved}"
        )
        append_result(r, f"p5v2 random #{i}")

        if r["score"] > best_score_so_far:
            best_score_so_far = r["score"]
            no_improve = 0
            if r["score"] >= EARLY_STOP_SCORE_THRESHOLD:
                print(f"  → Early stop: score {r['score']:.3f} >= {EARLY_STOP_SCORE_THRESHOLD}")
                break
        else:
            no_improve += 1
            if no_improve >= EARLY_STOP_NO_IMPROVE:
                print(f"  → Early stop: {EARLY_STOP_NO_IMPROVE} trials no improve")
                break
    return results


def main() -> int:
    t0 = time.time()
    print("=== research search v2 (iter 2 — EMA filter dimension) ===")
    print(f"Trial budget: {TRIAL_BUDGET}")
    print(f"Hard floor: n_trades < {N_TRADES_FLOOR} → -999")
    print(f"Consistency: <{MIN_POSITIVE_FOLDS}/5 folds positive → -999")

    split = load_split()
    train_df = split.train_df
    print(f"Train: {len(train_df)} bars / Held-out: {len(split.heldout_df)} bars (locked)")

    all_results: list[dict[str, Any]] = []

    p1 = phase1_lookback_sweep(train_df)
    all_results.extend(p1)
    best_lb = max(p1, key=lambda r: r["score"])["params"]["lookback_n"]
    print(f"  → best lookback: {best_lb}")

    p2 = phase2_atr_sweep(train_df, best_lb)
    all_results.extend(p2)
    best_am = max(p2, key=lambda r: r["score"])["params"]["atr_stop_mult"]
    print(f"  → best atr_mult: {best_am}")

    p3 = phase3_exit_sweep(train_df, best_lb, best_am)
    all_results.extend(p3)
    best_ex = max(p3, key=lambda r: r["score"])["params"]["exit_lookback_n"]
    print(f"  → best exit: {best_ex}")

    p4 = phase4_atr_period_sweep(train_df, best_lb, best_ex, best_am)
    all_results.extend(p4)
    best_ap = max(p4, key=lambda r: r["score"])["params"]["atr_period"]
    print(f"  → best atr_period: {best_ap}")

    p6 = phase6_ema_sweep(train_df, best_lb, best_ex, best_ap, best_am)
    all_results.extend(p6)
    best_ema_pick = max(p6, key=lambda r: r["score"])
    print(f"  → best ema: {best_ema_pick['params']['ema_filter_period']}")

    deterministic_best = max(all_results, key=lambda r: r["score"])
    print(f"\nDeterministic best: {deterministic_best['params']}")
    print(
        f"  score={deterministic_best['score']:.3f} sharpe={deterministic_best['metric']:.3f} n={deterministic_best['n_trades']}"
    )

    used = len(all_results)
    remaining = TRIAL_BUDGET - used
    p5 = phase5_random(train_df, deterministic_best["params"], remaining)
    all_results.extend(p5)

    final_best = max(all_results, key=lambda r: r["score"])
    elapsed = time.time() - t0
    print("\n=== FINAL ITER 2 SEARCH RESULT ===")
    print(f"Trials run: {len(all_results)} / {TRIAL_BUDGET}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"BEST PARAMS: {final_best['params']}")
    print(f"  trial_id: {final_best['trial_id']}")
    print(f"  composite score: {final_best['score']:.4f}")
    print(f"  aggregate Sharpe: {final_best['metric']:.4f}")
    print(f"  total_pnl_pct: {final_best.get('total_pnl_pct', 0):.2f}")
    print(f"  win_rate: {final_best.get('win_rate', float('nan')):.4f}")
    print(f"  n_trades: {final_best['n_trades']}")
    print(f"  fold_sharpes: {final_best['fold_sharpes']}")
    print(f"  fold_pnls: {final_best.get('fold_pnls', [])}")
    print("\nNext: held-out verification on best params (verify_heldout.py update)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
