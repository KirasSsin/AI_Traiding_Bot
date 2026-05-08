"""research search v3 — multi-paradigm sweep (iter 3+ autoresearch).

Operator directive: 100 iterations. Trader-expert ROUND 1 BLOCKED Donchian
extension (anti-snooping per ADR 0054). Solution: sweep ACROSS paradigms,
each strategy class = fresh N_trials family per Bailey 2014.

Per strategy: ~10 trial grid search + held-out verify. 10 strategies × 10 = ~100.

Composite score = agg_sharpe * log1p(n_trades / 5.0). Hard floor n<10 → -999.
Held-out PASS threshold: held-out Sharpe >= 0.5 × train Sharpe AND held-out > 0.

Output: results.tsv appended (P*v3_<strategy>_<i>) + per-strategy verdict.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.prepare import load_split
from research.strategies import (  # noqa: E402
    STRATEGY_REGISTRY,
    evaluate_heldout,
    evaluate_wfa,
)

RESULTS_PATH = Path(__file__).parent / "results.tsv"

N_TRADES_FLOOR = 10
MIN_POSITIVE_FOLDS = 3
HELDOUT_PASS_RATIO = 0.5

# Per-strategy hyperparameter grid (compact ~10 trials each).
# 5M scaling: lookbacks ~ 4H × 12-48 (since 5M = 4H/48). Holds longer = lower commission impact.
GRIDS: dict[str, list[dict[str, Any]]] = {
    "donchian_raw": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "atr_period": 50,
            "atr_stop_mult": am,
        }
        for lb in [100, 200, 400]
        for am in [2.0, 3.0, 4.0]
    ],
    "rsi_mean_reversion": [
        {"rsi_period": p, "rsi_low": low, "rsi_high": high, "atr_period": 50, "atr_stop_mult": 2.5}
        for p in [50, 100]
        for low in [20, 25]
        for high in [55, 65]
    ][:10],
    "bollinger_breakout": [
        {"bb_period": p, "bb_k": k, "atr_period": 50, "atr_stop_mult": 2.5}
        for p in [100, 200, 300]
        for k in [2.0, 2.5, 3.0]
    ],
    "bollinger_mr": [
        {"bb_period": p, "bb_k": k, "atr_period": 50, "atr_stop_mult": 2.5}
        for p in [100, 200, 300]
        for k in [2.0, 2.5, 3.0]
    ],
    "macd_momentum": [
        {"macd_fast": f, "macd_slow": s, "macd_signal": 60, "atr_period": 50, "atr_stop_mult": 2.5}
        for f, s in [(60, 130), (90, 200), (45, 110), (120, 260)]
    ]
    + [
        {
            "macd_fast": 60,
            "macd_slow": 130,
            "macd_signal": sig,
            "atr_period": 50,
            "atr_stop_mult": am,
        }
        for sig in [45, 90]
        for am in [2.0, 3.0, 4.0]
    ][:10],
    "atr_squeeze_breakout": [
        {
            "lookback_n": lb,
            "squeeze_window": 500,
            "squeeze_pct": pct,
            "atr_period": 50,
            "atr_stop_mult": 2.5,
        }
        for lb in [100, 200, 300]
        for pct in [20, 30, 40]
    ],
    "momentum_n_consec": [
        {"n_consec": n, "exit_n_reverse": 3, "atr_period": 50, "atr_stop_mult": am}
        for n in [4, 6, 8, 10]
        for am in [2.0, 3.0, 4.0]
    ][:10],
    "volume_breakout": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "vol_window": 100,
            "vol_mult": vm,
            "atr_period": 50,
            "atr_stop_mult": 2.5,
        }
        for lb in [100, 200, 300]
        for vm in [1.5, 2.0, 3.0]
    ],
    "ema_crossover": [
        {"ema_fast": f, "ema_slow": s, "atr_period": 50, "atr_stop_mult": 2.5}
        for f, s in [(20, 100), (50, 200), (60, 240), (100, 400), (30, 150)]
    ]
    + [
        {"ema_fast": 50, "ema_slow": 200, "atr_period": 50, "atr_stop_mult": am}
        for am in [1.5, 2.0, 3.0, 4.0]
    ][:10],
    "price_channel_with_atr": [
        {
            "lookback_n": lb,
            "exit_lookback_n": max(2, lb // 2),
            "atr_pct_min": pmin,
            "atr_pct_max": 0.02,
            "atr_period": 50,
            "atr_stop_mult": 2.5,
        }
        for lb in [100, 200, 300]
        for pmin in [0.001, 0.002, 0.004]
    ],
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


def search_strategy(name: str, train_df: Any, held_df: Any) -> dict[str, Any]:
    print(f"\n=== STRATEGY: {name} ===")
    grid = GRIDS.get(name, [])
    if not grid:
        return {"strategy": name, "best": None, "verdict": "no_grid"}
    trials = []
    for i, params in enumerate(grid, start=1):
        t0 = time.time()
        try:
            r = evaluate_wfa(train_df, name, params)
        except Exception as exc:  # noqa: BLE001
            r = {
                "metric": float("nan"),
                "n_trades": 0,
                "fold_sharpes": [],
                "status": f"crash:{exc}",
            }
        score = composite(r["metric"], r["n_trades"], r["fold_sharpes"])
        elapsed = time.time() - t0
        trials.append({"params": params, "result": r, "score": score, "trial": i})
        trial_id = f"P3v3_{name}_{i}"
        desc = f"v3 {name} trial #{i} ({_params_str(params)})"
        append_tsv(
            trial_id,
            score,
            r["metric"],
            r["n_trades"],
            r.get("total_pnl_pct", 0.0),
            r["status"],
            desc,
        )
        print(
            f"  #{i} score={score:+.3f} sharpe={r['metric']:+.3f} "
            f"pnl={r.get('total_pnl_pct', 0):+6.1f}% n={r['n_trades']:3d} "
            f"win={r.get('win_rate', 0):.2f} ({elapsed:.2f}s)"
        )

    best = max(trials, key=lambda t: t["score"])
    train_sharpe = best["result"]["metric"]
    print(
        f"  → BEST: score={best['score']:.3f} train Sharpe={train_sharpe:+.3f} {_params_str(best['params'])}"
    )

    # Skip held-out если train sharpe negative или score == -999
    if best["score"] == -999.0 or train_sharpe <= 0:
        print(f"  → SKIP held-out (train FAIL): score={best['score']} train Sharpe={train_sharpe}")
        verdict = f"train_fail score={best['score']:.2f} sharpe={train_sharpe:.2f}"
        append_tsv(
            f"P3v3_{name}_HELDOUT_SKIP",
            0.0,
            0.0,
            0,
            0.0,
            "skipped_train_fail",
            f"v3 {name} held-out skipped — train FAIL",
        )
        return {"strategy": name, "best": best, "held_out": None, "verdict": verdict}

    # Held-out verify
    print("  → Running held-out verify...")
    h = evaluate_heldout(held_df, name, best["params"])
    held_sharpe = h["metric"]
    pass_threshold = train_sharpe * HELDOUT_PASS_RATIO
    if math.isnan(held_sharpe) or h["n_trades"] < 5:
        verdict = f"held-out FAIL: insufficient (n={h['n_trades']}, sharpe={held_sharpe})"
    elif held_sharpe < 0:
        verdict = (
            f"held-out FAIL: sign-flip (train +{train_sharpe:.2f} → held-out {held_sharpe:.2f})"
        )
    elif held_sharpe < pass_threshold:
        verdict = f"held-out FAIL: degradation (held-out {held_sharpe:.2f} < {pass_threshold:.2f} threshold)"
    else:
        verdict = f"PASS candidate: held-out {held_sharpe:.2f} >= {pass_threshold:.2f} threshold"

    append_tsv(
        f"P3v3_{name}_HELDOUT",
        h["metric"],
        h["metric"],
        h["n_trades"],
        h.get("total_pnl_pct", 0.0),
        h["status"],
        f"v3 {name} HELDOUT — {verdict} ({_params_str(best['params'])})",
    )
    print(
        f"  → HELDOUT: sharpe={h['metric']:+.3f} pnl={h.get('total_pnl_pct', 0):+.1f}% "
        f"n={h['n_trades']} win={h.get('win_rate', 0):.2f}"
    )
    print(f"  → VERDICT: {verdict}")
    return {"strategy": name, "best": best, "held_out": h, "verdict": verdict}


def main() -> int:
    t0 = time.time()
    print("=== research search v3 — multi-paradigm sweep ===")
    print(f"Strategies: {list(STRATEGY_REGISTRY.keys())}")
    total_trials = sum(len(g) for g in GRIDS.values())
    print(f"Total trials: {total_trials}")
    print("PASS threshold: held-out Sharpe >= 0.5 * train Sharpe AND held-out > 0")
    print()

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
    print(f"\n\n=== FINAL SUMMARY ({elapsed:.1f}s, {total_trials} total trials) ===\n")
    print(f"{'Strategy':<28s} | {'Train Sharpe':>13s} | {'Held-out':>10s} | Verdict")
    print("-" * 100)
    for s in summaries:
        if s["best"] is None:
            print(f"{s['strategy']:<28s} | {'n/a':>13s} | {'n/a':>10s} | {s['verdict']}")
            continue
        train_s = s["best"]["result"]["metric"]
        held_s = s["held_out"]["metric"] if s["held_out"] else float("nan")
        print(f"{s['strategy']:<28s} | {train_s:>+13.3f} | {held_s:>+10.3f} | {s['verdict']}")

    pass_candidates = [s for s in summaries if s["held_out"] and "PASS" in s["verdict"]]
    print(f"\nPASS candidates: {len(pass_candidates)}")
    for s in pass_candidates:
        print(
            f"  {s['strategy']}: train={s['best']['result']['metric']:.2f} held-out={s['held_out']['metric']:.2f}"
        )

    # Append final summary к results.tsv
    append_tsv(
        "P3v3_FINAL_SUMMARY",
        0.0,
        0.0,
        total_trials,
        0.0,
        "summary",
        f"v3 multi-paradigm sweep complete — {len(pass_candidates)} PASS candidates",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
