"""research search v4 — 1000-trial multi-paradigm sweep на 1H (operator iter 6 directive).

Per strategy: ~30 systematic grid + ~70 random perturbation around top-3 grid winners.
Total budget: ~100/strategy × 10 strategies = ~1000 trials.

Composite score = agg_sharpe * log1p(n_trades / 5.0). Hard floor n<10 → -999.
PASS threshold: held-out Sharpe >= 0.5 × train Sharpe AND held-out > 0 AND held-out PnL > 0.

Output: results.tsv appended (P4v4_<strategy>_<i>) + per-strategy verdict + final ranking.

1H pre-check PASSED: median bar range 0.514% > 0.25% trader gate (commit 497a4ab).
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

random.seed(42)

RESULTS_PATH = Path(__file__).parent / "results.tsv"

N_TRADES_FLOOR = 10
MIN_POSITIVE_FOLDS = 3
HELDOUT_PASS_RATIO = 0.5
TRIAL_BUDGET_PER_STRAT = 100  # × 10 strategies = ~1000 total
GRID_PORTION = 30  # systematic grid trials
RANDOM_PORTION = TRIAL_BUDGET_PER_STRAT - GRID_PORTION  # 70 random perturbation


# ---------- Per-strategy GRIDS (systematic, ~30 trials each) ----------
# 1H scale: lookbacks compromise между 5M (×60) и 4H (×4).
# Donchian classical periods 20-100, EMA 12-200, RSI 14-50, etc.


def _expand(*combos: list[Any]) -> list[dict[str, Any]]:
    return [dict(c) for c in combos]


GRIDS: dict[str, list[dict[str, Any]]] = {
    "donchian_raw": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "atr_period": ap,
            "atr_stop_mult": am,
        }
        for lb in [20, 40, 60, 100, 150]
        for ap in [14, 30]
        for am in [1.5, 2.5, 4.0]
    ][:GRID_PORTION],
    "rsi_mean_reversion": [
        {"rsi_period": p, "rsi_low": low, "rsi_high": high, "atr_period": 30, "atr_stop_mult": am}
        for p in [14, 21, 30]
        for low in [20, 25, 30]
        for high in [50, 60, 70]
        for am in [2.0]
    ][:GRID_PORTION],
    "bollinger_breakout": [
        {"bb_period": p, "bb_k": k, "atr_period": 30, "atr_stop_mult": am}
        for p in [20, 40, 60, 100]
        for k in [1.5, 2.0, 2.5, 3.0]
        for am in [2.0, 3.0]
    ][:GRID_PORTION],
    "bollinger_mr": [
        {"bb_period": p, "bb_k": k, "atr_period": 30, "atr_stop_mult": am}
        for p in [20, 40, 60, 100]
        for k in [1.5, 2.0, 2.5, 3.0]
        for am in [2.0, 3.0]
    ][:GRID_PORTION],
    "macd_momentum": [
        {"macd_fast": f, "macd_slow": s, "macd_signal": sig, "atr_period": 30, "atr_stop_mult": am}
        for f, s in [(12, 26), (8, 21), (5, 35), (12, 50), (20, 60)]
        for sig in [9, 14]
        for am in [2.0, 3.0]
    ][:GRID_PORTION],
    "atr_squeeze_breakout": [
        {
            "lookback_n": lb,
            "squeeze_window": sw,
            "squeeze_pct": pct,
            "atr_period": 30,
            "atr_stop_mult": 2.0,
        }
        for lb in [20, 40, 60]
        for sw in [100, 200]
        for pct in [20, 30, 40, 50]
    ][:GRID_PORTION],
    "momentum_n_consec": [
        {"n_consec": n, "exit_n_reverse": ex, "atr_period": 30, "atr_stop_mult": am}
        for n in [3, 4, 5, 6, 8]
        for ex in [2, 3]
        for am in [2.0, 3.0, 4.0]
    ][:GRID_PORTION],
    "volume_breakout": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "vol_window": 30,
            "vol_mult": vm,
            "atr_period": 30,
            "atr_stop_mult": 2.0,
        }
        for lb in [20, 40, 60, 100]
        for vm in [1.2, 1.5, 2.0, 2.5]
    ][:GRID_PORTION],
    "ema_crossover": [
        {"ema_fast": f, "ema_slow": s, "atr_period": 30, "atr_stop_mult": am}
        for f, s in [(8, 21), (12, 26), (20, 50), (10, 40), (15, 60), (20, 100), (30, 100)]
        for am in [1.5, 2.0, 3.0, 4.0]
    ][:GRID_PORTION],
    "price_channel_with_atr": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "atr_pct_min": pmin,
            "atr_pct_max": 0.05,
            "atr_period": 30,
            "atr_stop_mult": 2.0,
        }
        for lb in [20, 40, 60, 100]
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
    with open(RESULTS_PATH, "a") as f:
        f.write(f"{trial_id}\t{score:.4f}\t{sharpe:.4f}\t{n}\t{pnl:.2f}\t{status}\t{desc}\n")


def _perturb(base: dict[str, Any]) -> dict[str, Any]:
    """Random perturbation ±30-50% for numeric params; preserve ints as ints."""
    out: dict[str, Any] = {}
    for k, v in base.items():
        if isinstance(v, int):
            jitter = random.uniform(0.5, 1.5)
            out[k] = max(2, int(v * jitter))
        elif isinstance(v, float):
            jitter = random.uniform(0.6, 1.6)
            out[k] = round(v * jitter, 4)
        else:
            out[k] = v
    # Sanity: exit_lookback_n < lookback_n
    if "exit_lookback_n" in out and "lookback_n" in out:
        out["exit_lookback_n"] = min(out["exit_lookback_n"], max(2, out["lookback_n"] - 1))
    return out


def search_strategy(name: str, train_df: Any, held_df: Any) -> dict[str, Any]:
    print(f"\n=== STRATEGY: {name} ===")
    grid = GRIDS.get(name, [])
    if not grid:
        return {"strategy": name, "best": None, "verdict": "no_grid"}
    trials: list[dict[str, Any]] = []

    # Phase A: systematic grid
    print(f"  Phase A: grid scan {len(grid)} trials")
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
        trials.append({"params": params, "result": r, "score": score, "trial": i, "phase": "grid"})
        append_tsv(
            f"P4v4_{name}_g{i}",
            score,
            r["metric"],
            r["n_trades"],
            r.get("total_pnl_pct", 0.0),
            r["status"],
            f"v4 {name} grid #{i} ({_params_str(params)})",
        )

    # Phase B: random perturbation around top-3 grid winners
    grid_sorted = sorted(trials, key=lambda t: t["score"], reverse=True)
    top3 = [t["params"] for t in grid_sorted[:3] if t["score"] > -999]
    if not top3:
        # Fallback: use first grid entry as base
        top3 = [grid[0]]
    print(
        f"  Phase B: random perturbation {RANDOM_PORTION} trials around top-{len(top3)} grid winners"
    )
    for i in range(1, RANDOM_PORTION + 1):
        base = random.choice(top3)
        params = _perturb(base)
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
        trials.append(
            {
                "params": params,
                "result": r,
                "score": score,
                "trial": GRID_PORTION + i,
                "phase": "random",
            }
        )
        append_tsv(
            f"P4v4_{name}_r{i}",
            score,
            r["metric"],
            r["n_trades"],
            r.get("total_pnl_pct", 0.0),
            r["status"],
            f"v4 {name} random #{i} ({_params_str(params)})",
        )

    best = max(trials, key=lambda t: t["score"])
    train_sharpe = best["result"]["metric"]
    train_pnl = best["result"].get("total_pnl_pct", 0.0)
    print(
        f"  → BEST {best['phase']} #{best['trial']}: "
        f"score={best['score']:.3f} sharpe={train_sharpe:+.3f} pnl={train_pnl:+.1f}% "
        f"n={best['result']['n_trades']} | {_params_str(best['params'])}"
    )

    if best["score"] == -999.0 or train_sharpe <= 0:
        verdict = f"train_fail score={best['score']:.2f} sharpe={train_sharpe:.2f}"
        append_tsv(
            f"P4v4_{name}_HELDOUT_SKIP",
            0.0,
            0.0,
            0,
            0.0,
            "skipped_train_fail",
            f"v4 {name} held-out skipped — train FAIL",
        )
        return {"strategy": name, "best": best, "held_out": None, "verdict": verdict}

    # Held-out verify
    h = evaluate_heldout(held_df, name, best["params"])
    held_sharpe = h["metric"]
    held_pnl = h.get("total_pnl_pct", 0.0)
    pass_threshold = train_sharpe * HELDOUT_PASS_RATIO
    if math.isnan(held_sharpe) or h["n_trades"] < 5:
        verdict = f"held-out FAIL: insufficient (n={h['n_trades']})"
    elif held_sharpe < 0:
        verdict = (
            f"held-out FAIL: sign-flip (train +{train_sharpe:.2f} → held-out {held_sharpe:.2f})"
        )
    elif held_pnl < 0:
        verdict = f"held-out FAIL: PnL negative ({held_pnl:.1f}%)"
    elif held_sharpe < pass_threshold:
        verdict = f"held-out FAIL: degradation ({held_sharpe:.2f} < {pass_threshold:.2f})"
    else:
        verdict = f"PASS: held-out Sharpe {held_sharpe:.2f} PnL {held_pnl:+.1f}%"

    append_tsv(
        f"P4v4_{name}_HELDOUT",
        h["metric"],
        h["metric"],
        h["n_trades"],
        h.get("total_pnl_pct", 0.0),
        h["status"],
        f"v4 {name} HELDOUT — {verdict} ({_params_str(best['params'])})",
    )
    print(
        f"  → HELDOUT: sharpe={held_sharpe:+.3f} pnl={held_pnl:+.1f}% "
        f"n={h['n_trades']} win={h.get('win_rate', 0):.2f}"
    )
    print(f"  → VERDICT: {verdict}")
    return {"strategy": name, "best": best, "held_out": h, "verdict": verdict}


def main() -> int:
    t0 = time.time()
    print(
        f"=== research search v4 — 1000-trial sweep на 1H ({TRIAL_BUDGET_PER_STRAT} per strategy) ==="
    )
    print(f"Phase A grid: {GRID_PORTION} | Phase B random: {RANDOM_PORTION}")
    print(f"Total: ~{TRIAL_BUDGET_PER_STRAT * len(STRATEGY_REGISTRY)} trials")

    split = load_split()
    train_df = split.train_df
    held_df = split.heldout_df
    print(f"Train: {len(train_df)} bars / Held-out: {len(held_df)} bars")

    summaries = []
    for name in STRATEGY_REGISTRY:
        s = search_strategy(name, train_df, held_df)
        summaries.append(s)

    # Final ranking
    elapsed = time.time() - t0
    n_total = TRIAL_BUDGET_PER_STRAT * len(STRATEGY_REGISTRY)
    print(f"\n\n=== FINAL SUMMARY ({elapsed:.1f}s, {n_total} total trials) ===\n")
    print(
        f"{'Strategy':<28s} | {'Train Sharpe':>13s} | {'Train PnL':>10s} | {'Held-out':>10s} | {'Held PnL':>10s} | Verdict"
    )
    print("-" * 130)
    for s in summaries:
        if s["best"] is None:
            print(
                f"{s['strategy']:<28s} | {'n/a':>13s} | {'n/a':>10s} | {'n/a':>10s} | {'n/a':>10s} | {s['verdict']}"
            )
            continue
        train_s = s["best"]["result"]["metric"]
        train_p = s["best"]["result"].get("total_pnl_pct", 0.0)
        held_s = s["held_out"]["metric"] if s["held_out"] else float("nan")
        held_p = s["held_out"].get("total_pnl_pct", 0.0) if s["held_out"] else 0.0
        print(
            f"{s['strategy']:<28s} | {train_s:>+13.3f} | {train_p:>+9.1f}% | "
            f"{held_s:>+10.3f} | {held_p:>+9.1f}% | {s['verdict']}"
        )

    pass_candidates = [s for s in summaries if "PASS" in s["verdict"]]
    print(f"\nPASS candidates: {len(pass_candidates)}")
    for s in pass_candidates:
        train_s = s["best"]["result"]["metric"]
        held_s = s["held_out"]["metric"]
        print(
            f"  {s['strategy']}: train Sharpe={train_s:.2f} → held-out Sharpe={held_s:.2f} | "
            f"params: {_params_str(s['best']['params'])}"
        )

    append_tsv(
        "P4v4_FINAL_SUMMARY",
        0.0,
        0.0,
        n_total,
        0.0,
        "summary",
        f"v4 1H 1000-trial sweep complete — {len(pass_candidates)} PASS candidates",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
