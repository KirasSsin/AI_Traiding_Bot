"""autoresearch_donchian — autonomous search runner (100-trial budget).

Implements trader-expert ROUND consilium recommendations:
  Q1 composite metric: score = agg_sharpe * log1p(n_trades / 5.0); hard floor n_trades<10 → -999
  Q2 search order: lookback FIRST (7 values), then atr_mult, then exit_lookback, then atr_period
  Q4 stop: 30 consecutive non-improvements OR score >= 2.5
  Q5 safeguards: hard floor n_trades<10, 3/5 folds positive consistency check, no MC gate

Phase plan:
  Phase 1 (7 trials): lookback ∈ {5,10,15,20,30,40,55}, exit=lookback//2, atr_mult=2.0
  Phase 2 (8 trials): best lookback × atr_mult ∈ {1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0}
  Phase 3 (5 trials): best (lookback, atr) × exit ∈ {lookback*0.25, *0.4, *0.5, *0.7, *0.9}
  Phase 4 (5 trials): best (lookback, exit, atr) × atr_period ∈ {7, 10, 14, 21, 30}
  Phase 5 (75 trials): random exploration around top-3 (perturbation ±20%)

Total: 100 trials. Each ~1-2 sec. Total ~3-5 min wall clock.

Held-out verification deferred к POST-loop (via verify_heldout.py separate script).

Output: results.tsv appended + run.log final summary.
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path
from typing import Any

# Add bot project to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoresearch_donchian.prepare_donchian import evaluate_metric, load_split

random.seed(42)  # Reproducibility

RESULTS_PATH = Path(__file__).parent / "results.tsv"

# trader-expert recommendation: n_trades hard floor
N_TRADES_FLOOR = 10
# trader-expert recommendation: 3/5 folds positive (consistency)
MIN_POSITIVE_FOLDS = 3
# trader-expert recommendation: stop early
EARLY_STOP_NO_IMPROVE = 30
EARLY_STOP_SCORE_THRESHOLD = 2.5

# Total trial budget (operator-set)
TRIAL_BUDGET = 100


def composite_score(
    *,
    metric: float,  # aggregate Sharpe
    n_trades: int,
    fold_sharpes: list[float],
) -> float:
    """trader-expert Q1: composite_score = agg_sharpe * log1p(n_trades / 5.0).

    Safeguards (Q5):
    - Hard floor: n_trades < 10 → -999
    - Consistency: < 3/5 folds positive → -999
    """
    if n_trades < N_TRADES_FLOOR:
        return -999.0
    if math.isnan(metric):
        return -999.0
    positive_folds = sum(1 for s in fold_sharpes if s > 0)
    if len(fold_sharpes) >= 5 and positive_folds < MIN_POSITIVE_FOLDS:
        return -999.0
    return float(metric * math.log1p(n_trades / 5.0))


def run_trial(
    train_df: Any,
    params: dict[str, Any],
    trial_id: str,
) -> dict[str, Any]:
    """Single trial: backtest на train_df с params + return result dict."""
    t0 = time.time()
    try:
        result = evaluate_metric(df=train_df, params=params, use_wfa=True)
    except Exception as exc:  # noqa: BLE001 — autoresearch crash log
        return {
            "trial_id": trial_id,
            "params": params,
            "score": -999.0,
            "metric": float("nan"),
            "n_trades": 0,
            "mc_p": float("nan"),
            "fold_sharpes": [],
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
        "mc_p": result["mc_p"],
        "fold_sharpes": result["fold_sharpes"],
        "status": result["status"],
        "elapsed": time.time() - t0,
    }


def append_result(r: dict[str, Any], description: str) -> None:
    """Append к results.tsv per autoresearch convention."""
    with open(RESULTS_PATH, "a") as f:
        params_str = (
            f"L{r['params']['lookback_n']}E{r['params']['exit_lookback_n']}"
            f"A{r['params']['atr_stop_mult']}P{r['params']['atr_period']}"
        )
        f.write(
            f"{r['trial_id']}\t"
            f"{r['score']:.4f}\t"
            f"{r['metric']:.4f}\t"
            f"{r['n_trades']}\t"
            f"{r['mc_p']:.4f}\t"
            f"{r['status']}\t"
            f"{description} ({params_str})\n"
        )


def phase1_lookback_sweep(train_df: Any) -> list[dict[str, Any]]:
    """7 trials: lookback ∈ {5,10,15,20,30,40,55}, exit=lookback//2, atr_mult=2.0."""
    print("\n=== PHASE 1: lookback_n sweep (7 trials) ===")
    results = []
    for i, lb in enumerate([5, 10, 15, 20, 30, 40, 55], start=1):
        params = {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "atr_period": 14,
            "atr_stop_mult": 2.0,
        }
        trial_id = f"P1_{i}"
        r = run_trial(train_df, params, trial_id)
        results.append(r)
        print(
            f"  {trial_id} L={lb} E={params['exit_lookback_n']} → "
            f"score={r['score']:.3f} sharpe={r['metric']:.3f} n={r['n_trades']} ({r['elapsed']:.1f}s)"
        )
        append_result(r, "phase1 lookback sweep")
    return results


def phase2_atr_sweep(train_df: Any, best_lookback: int) -> list[dict[str, Any]]:
    """8 trials: best_lookback × atr_mult ∈ {1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0}."""
    print(f"\n=== PHASE 2: atr_mult sweep on lookback={best_lookback} (8 trials) ===")
    results = []
    for i, am in enumerate([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0], start=1):
        params = {
            "lookback_n": best_lookback,
            "exit_lookback_n": max(2, best_lookback // 2),
            "atr_period": 14,
            "atr_stop_mult": am,
        }
        trial_id = f"P2_{i}"
        r = run_trial(train_df, params, trial_id)
        results.append(r)
        print(
            f"  {trial_id} L={best_lookback} ATR×{am} → "
            f"score={r['score']:.3f} sharpe={r['metric']:.3f} n={r['n_trades']}"
        )
        append_result(r, "phase2 atr_mult sweep")
    return results


def phase3_exit_sweep(
    train_df: Any, best_lookback: int, best_atr_mult: float
) -> list[dict[str, Any]]:
    """5 trials: best (lookback, atr) × exit ∈ {0.25, 0.4, 0.5, 0.7, 0.9} × lookback."""
    print(
        f"\n=== PHASE 3: exit_lookback sweep on L={best_lookback} ATR×{best_atr_mult} (5 trials) ==="
    )
    results = []
    for i, ratio in enumerate([0.25, 0.4, 0.5, 0.7, 0.9], start=1):
        exit_lb = max(2, int(best_lookback * ratio))
        if exit_lb >= best_lookback:
            exit_lb = best_lookback - 1
        params = {
            "lookback_n": best_lookback,
            "exit_lookback_n": exit_lb,
            "atr_period": 14,
            "atr_stop_mult": best_atr_mult,
        }
        trial_id = f"P3_{i}"
        r = run_trial(train_df, params, trial_id)
        results.append(r)
        print(
            f"  {trial_id} L={best_lookback} E={exit_lb} ATR×{best_atr_mult} → "
            f"score={r['score']:.3f} n={r['n_trades']}"
        )
        append_result(r, f"phase3 exit ratio {ratio}")
    return results


def phase4_atr_period_sweep(
    train_df: Any,
    best_lookback: int,
    best_exit: int,
    best_atr_mult: float,
) -> list[dict[str, Any]]:
    """5 trials: best (lookback, exit, atr_mult) × atr_period ∈ {7, 10, 14, 21, 30}."""
    print("\n=== PHASE 4: atr_period sweep (5 trials) ===")
    results = []
    for i, ap in enumerate([7, 10, 14, 21, 30], start=1):
        params = {
            "lookback_n": best_lookback,
            "exit_lookback_n": best_exit,
            "atr_period": ap,
            "atr_stop_mult": best_atr_mult,
        }
        trial_id = f"P4_{i}"
        r = run_trial(train_df, params, trial_id)
        results.append(r)
        print(f"  {trial_id} ATR_period={ap} → " f"score={r['score']:.3f} n={r['n_trades']}")
        append_result(r, f"phase4 atr_period {ap}")
    return results


def phase5_random(
    train_df: Any,
    best_params: dict[str, Any],
    n_trials: int,
) -> list[dict[str, Any]]:
    """Random perturbation around best_params (±20%)."""
    print(f"\n=== PHASE 5: random exploration around best ({n_trials} trials) ===")
    results = []
    no_improve = 0
    best_score_so_far = -999.0
    for i in range(1, n_trials + 1):
        # Perturb each param ±20%
        lb = max(3, int(best_params["lookback_n"] * random.uniform(0.6, 1.5)))
        exit_lb = max(2, int(lb * random.uniform(0.3, 0.7)))
        if exit_lb >= lb:
            exit_lb = lb - 1
        ap = max(5, int(best_params["atr_period"] * random.uniform(0.6, 1.5)))
        am = max(0.5, best_params["atr_stop_mult"] * random.uniform(0.6, 1.6))
        params = {
            "lookback_n": lb,
            "exit_lookback_n": exit_lb,
            "atr_period": ap,
            "atr_stop_mult": round(am, 2),
        }
        trial_id = f"P5_{i}"
        r = run_trial(train_df, params, trial_id)
        results.append(r)
        improved = "↑" if r["score"] > best_score_so_far else " "
        print(
            f"  {trial_id} L={lb} E={exit_lb} P={ap} ATR×{params['atr_stop_mult']} → "
            f"score={r['score']:.3f} n={r['n_trades']} {improved}"
        )
        append_result(r, f"phase5 random perturbation #{i}")

        if r["score"] > best_score_so_far:
            best_score_so_far = r["score"]
            no_improve = 0
            if r["score"] >= EARLY_STOP_SCORE_THRESHOLD:
                print(
                    f"  → Early stop: score {r['score']:.3f} >= threshold {EARLY_STOP_SCORE_THRESHOLD}"
                )
                break
        else:
            no_improve += 1
            if no_improve >= EARLY_STOP_NO_IMPROVE:
                print(f"  → Early stop: {EARLY_STOP_NO_IMPROVE} trials without improvement")
                break
    return results


def main() -> int:
    t0 = time.time()
    print("=== autoresearch_donchian autonomous search ===")
    print(f"Trial budget: {TRIAL_BUDGET}")
    print("Composite metric: agg_sharpe * log1p(n_trades / 5.0)")
    print(f"Hard floor: n_trades < {N_TRADES_FLOOR} → score=-999")
    print(f"Consistency: <{MIN_POSITIVE_FOLDS}/5 folds positive → score=-999")
    print()

    split = load_split()
    train_df = split.train_df
    print(f"Train data: {len(train_df)} bars ({split.train_start} → {split.train_end})")
    print(f"Held-out: {len(split.heldout_df)} bars (NEVER touched in search)")

    all_results: list[dict[str, Any]] = []

    # Phase 1: lookback sweep
    p1 = phase1_lookback_sweep(train_df)
    all_results.extend(p1)
    best_p1 = max(p1, key=lambda r: r["score"])
    best_lookback = best_p1["params"]["lookback_n"]
    print(f"  → Best lookback: {best_lookback} (score={best_p1['score']:.3f})")

    # Phase 2: atr_mult sweep
    p2 = phase2_atr_sweep(train_df, best_lookback)
    all_results.extend(p2)
    best_p2 = max(p2, key=lambda r: r["score"])
    best_atr_mult = best_p2["params"]["atr_stop_mult"]
    print(f"  → Best atr_mult: {best_atr_mult} (score={best_p2['score']:.3f})")

    # Phase 3: exit sweep
    p3 = phase3_exit_sweep(train_df, best_lookback, best_atr_mult)
    all_results.extend(p3)
    best_p3 = max(p3, key=lambda r: r["score"])
    best_exit = best_p3["params"]["exit_lookback_n"]
    print(f"  → Best exit: {best_exit} (score={best_p3['score']:.3f})")

    # Phase 4: atr_period sweep
    p4 = phase4_atr_period_sweep(train_df, best_lookback, best_exit, best_atr_mult)
    all_results.extend(p4)
    best_p4 = max(p4, key=lambda r: r["score"])
    best_period = best_p4["params"]["atr_period"]
    print(f"  → Best atr_period: {best_period} (score={best_p4['score']:.3f})")

    # Best so far
    deterministic_best = max(all_results, key=lambda r: r["score"])
    print("\n=== Phases 1-4 deterministic best ===")
    print(f"  PARAMS: {deterministic_best['params']}")
    print(f"  score: {deterministic_best['score']:.4f}")
    print(f"  metric (sharpe): {deterministic_best['metric']:.4f}")
    print(f"  n_trades: {deterministic_best['n_trades']}")

    # Phase 5: random exploration
    used = len(all_results)
    remaining = TRIAL_BUDGET - used
    p5 = phase5_random(train_df, deterministic_best["params"], remaining)
    all_results.extend(p5)

    # Final summary
    final_best = max(all_results, key=lambda r: r["score"])
    elapsed = time.time() - t0
    print("\n=== FINAL TRAIN-PORTION SEARCH RESULT ===")
    print(f"Trials run: {len(all_results)} / {TRIAL_BUDGET}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"BEST PARAMS: {final_best['params']}")
    print(f"  trial_id: {final_best['trial_id']}")
    print(f"  composite score: {final_best['score']:.4f}")
    print(f"  aggregate Sharpe: {final_best['metric']:.4f}")
    print(f"  n_trades: {final_best['n_trades']}")
    print(f"  mc_p: {final_best['mc_p']:.4f}")
    print(f"  fold_sharpes: {[round(s, 2) for s in final_best['fold_sharpes']]}")
    print("\nNext step: held-out verification on best params (separate script)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
