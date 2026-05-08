"""research search v5 — 1000-trial sweep на 15M (iter 7 — ESC-1 OPERATOR OVERRIDE).

Trader gate previously FAILED (median 0.243% < 0.25%, commit 497a4ab).
ESC-1 override invoked per operator: 3-point acknowledgement logged в prepare.py header.

GRIDS rescaled ×4 from 1H baseline (15M = 1H/4 bars).
Per strategy: ~30 grid + ~70 random perturbation = 100 each. ×10 strategies = 1000.
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
TRIAL_BUDGET_PER_STRAT = 100
GRID_PORTION = 30
RANDOM_PORTION = TRIAL_BUDGET_PER_STRAT - GRID_PORTION

# 15M GRIDS = 1H baseline × 4 scale
GRIDS: dict[str, list[dict[str, Any]]] = {
    "donchian_raw": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "atr_period": ap,
            "atr_stop_mult": am,
        }
        for lb in [80, 160, 240, 400, 600]
        for ap in [56, 120]
        for am in [1.5, 2.5, 4.0]
    ][:GRID_PORTION],
    "rsi_mean_reversion": [
        {"rsi_period": p, "rsi_low": low, "rsi_high": high, "atr_period": 120, "atr_stop_mult": am}
        for p in [56, 84, 120]
        for low in [20, 25, 30]
        for high in [50, 60, 70]
        for am in [2.0]
    ][:GRID_PORTION],
    "bollinger_breakout": [
        {"bb_period": p, "bb_k": k, "atr_period": 120, "atr_stop_mult": am}
        for p in [80, 160, 240, 400]
        for k in [1.5, 2.0, 2.5, 3.0]
        for am in [2.0, 3.0]
    ][:GRID_PORTION],
    "bollinger_mr": [
        {"bb_period": p, "bb_k": k, "atr_period": 120, "atr_stop_mult": am}
        for p in [80, 160, 240, 400]
        for k in [1.5, 2.0, 2.5, 3.0]
        for am in [2.0, 3.0]
    ][:GRID_PORTION],
    "macd_momentum": [
        {"macd_fast": f, "macd_slow": s, "macd_signal": sig, "atr_period": 120, "atr_stop_mult": am}
        for f, s in [(48, 104), (32, 84), (20, 140), (48, 200), (80, 240)]
        for sig in [36, 56]
        for am in [2.0, 3.0]
    ][:GRID_PORTION],
    "atr_squeeze_breakout": [
        {
            "lookback_n": lb,
            "squeeze_window": sw,
            "squeeze_pct": pct,
            "atr_period": 120,
            "atr_stop_mult": 2.0,
        }
        for lb in [80, 160, 240]
        for sw in [400, 800]
        for pct in [20, 30, 40, 50]
    ][:GRID_PORTION],
    "momentum_n_consec": [
        {"n_consec": n, "exit_n_reverse": ex, "atr_period": 120, "atr_stop_mult": am}
        for n in [3, 4, 5, 6, 8]
        for ex in [2, 3]
        for am in [2.0, 3.0, 4.0]
    ][:GRID_PORTION],
    "volume_breakout": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "vol_window": 120,
            "vol_mult": vm,
            "atr_period": 120,
            "atr_stop_mult": 2.0,
        }
        for lb in [80, 160, 240, 400]
        for vm in [1.2, 1.5, 2.0, 2.5]
    ][:GRID_PORTION],
    "ema_crossover": [
        {"ema_fast": f, "ema_slow": s, "atr_period": 120, "atr_stop_mult": am}
        for f, s in [(32, 84), (48, 104), (80, 200), (40, 160), (60, 240), (80, 400), (120, 400)]
        for am in [1.5, 2.0, 3.0, 4.0]
    ][:GRID_PORTION],
    "price_channel_with_atr": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "atr_pct_min": pmin,
            "atr_pct_max": 0.05,
            "atr_period": 120,
            "atr_stop_mult": 2.0,
        }
        for lb in [80, 160, 240, 400]
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


def search_strategy(name: str, train_df: Any, held_df: Any) -> dict[str, Any]:
    print(f"\n=== STRATEGY: {name} ===")
    grid = GRIDS.get(name, [])
    if not grid:
        return {"strategy": name, "best": None, "verdict": "no_grid"}
    trials: list[dict[str, Any]] = []
    print(f"  Phase A: grid {len(grid)}")
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
        trials.append({"params": params, "result": r, "score": score, "phase": "grid", "trial": i})
        append_tsv(
            f"P5v5_{name}_g{i}",
            score,
            r["metric"],
            r["n_trades"],
            r.get("total_pnl_pct", 0.0),
            r["status"],
            f"v5 15M {name} grid #{i} ({_params_str(params)})",
        )

    grid_sorted = sorted(trials, key=lambda t: t["score"], reverse=True)
    top3 = [t["params"] for t in grid_sorted[:3] if t["score"] > -999]
    if not top3:
        top3 = [grid[0]]
    print(f"  Phase B: random {RANDOM_PORTION} around top-{len(top3)}")
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
        trials.append(
            {
                "params": params,
                "result": r,
                "score": score,
                "phase": "random",
                "trial": GRID_PORTION + i,
            }
        )
        append_tsv(
            f"P5v5_{name}_r{i}",
            score,
            r["metric"],
            r["n_trades"],
            r.get("total_pnl_pct", 0.0),
            r["status"],
            f"v5 15M {name} random #{i} ({_params_str(params)})",
        )

    best = max(trials, key=lambda t: t["score"])
    train_sharpe = best["result"]["metric"]
    train_pnl = best["result"].get("total_pnl_pct", 0.0)
    print(
        f"  → BEST {best['phase']} #{best['trial']}: "
        f"score={best['score']:.3f} sharpe={train_sharpe:+.3f} pnl={train_pnl:+.1f}% "
        f"n={best['result']['n_trades']}"
    )

    if best["score"] == -999.0 or train_sharpe <= 0:
        verdict = f"train_fail score={best['score']:.2f} sharpe={train_sharpe:.2f}"
        append_tsv(
            f"P5v5_{name}_HELDOUT_SKIP",
            0.0,
            0.0,
            0,
            0.0,
            "skipped_train_fail",
            f"v5 15M {name} held-out skipped",
        )
        return {"strategy": name, "best": best, "held_out": None, "verdict": verdict}

    h = evaluate_heldout(held_df, name, best["params"])
    held_sharpe = h["metric"]
    held_pnl = h.get("total_pnl_pct", 0.0)
    threshold = train_sharpe * HELDOUT_PASS_RATIO
    if math.isnan(held_sharpe) or h["n_trades"] < 5:
        verdict = f"held-out FAIL: insufficient (n={h['n_trades']})"
    elif held_sharpe < 0:
        verdict = f"held-out FAIL: sign-flip (train +{train_sharpe:.2f} → {held_sharpe:.2f})"
    elif held_pnl < 0:
        verdict = f"held-out FAIL: PnL negative ({held_pnl:.1f}%)"
    elif held_sharpe < threshold:
        verdict = f"held-out FAIL: degradation ({held_sharpe:.2f} < {threshold:.2f})"
    else:
        verdict = f"PASS: held-out Sharpe {held_sharpe:.2f} PnL {held_pnl:+.1f}%"

    append_tsv(
        f"P5v5_{name}_HELDOUT",
        h["metric"],
        h["metric"],
        h["n_trades"],
        h.get("total_pnl_pct", 0.0),
        h["status"],
        f"v5 15M {name} HELDOUT — {verdict} ({_params_str(best['params'])})",
    )
    print(f"  → HELDOUT: sharpe={held_sharpe:+.3f} pnl={held_pnl:+.1f}% n={h['n_trades']}")
    print(f"  → VERDICT: {verdict}")
    return {"strategy": name, "best": best, "held_out": h, "verdict": verdict}


def main() -> int:
    t0 = time.time()
    print("=== research search v5 — 1000 trials на 15M (ESC-1 override) ===")
    print("3-point acknowledgement logged: gate bypassed / N_trials=1 iter7 / held-out used")
    split = load_split()
    print(f"Train: {len(split.train_df)} / Held-out: {len(split.heldout_df)}")
    summaries = []
    for name in STRATEGY_REGISTRY:
        s = search_strategy(name, split.train_df, split.heldout_df)
        summaries.append(s)

    elapsed = time.time() - t0
    n_total = TRIAL_BUDGET_PER_STRAT * len(STRATEGY_REGISTRY)
    print(f"\n\n=== FINAL SUMMARY ({elapsed:.1f}s, {n_total} trials) ===\n")
    print(
        f"{'Strategy':<28s} | {'Train Sharpe':>13s} | {'Train PnL':>10s} | {'Held-out':>10s} | {'Held PnL':>10s} | Verdict"
    )
    print("-" * 130)
    for s in summaries:
        if s["best"] is None:
            print(f"{s['strategy']:<28s} | n/a | n/a | n/a | n/a | {s['verdict']}")
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
            f"  {s['strategy']}: train={train_s:.2f} → held-out={held_s:.2f} | {_params_str(s['best']['params'])}"
        )
    append_tsv(
        "P5v5_FINAL_SUMMARY",
        0.0,
        0.0,
        n_total,
        0.0,
        "summary",
        f"v5 15M 1000-trial sweep — {len(pass_candidates)} PASS",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
