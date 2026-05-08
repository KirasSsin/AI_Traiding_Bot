"""autoresearch_donchian — single experiment runner.

Адаптировано из karpathy/autoresearch train.py paradigm.

Agent EDITS THIS FILE. Each experiment = one git commit с modified params.

Per program_donchian.md: tune `PARAMS` dict + run → check metric → keep/discard.

Output format mirrors karpathy spec:
    ---
    metric (sharpe):  X.XX
    n_trades:         N
    mc_p:             X.XXX
    fold_sharpes:     [...]
    status:           ok|insufficient_data|crash
    seconds_total:    X.X
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add bot project к sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoresearch_donchian.prepare_donchian import evaluate_metric, load_split

# ============================================================
# AGENT EDITS THIS BLOCK
# ============================================================
# Baseline = ADR 0054 LOCKED Donchian S35 (lookback=20, exit=10, atr_mult=2.0)
# Per autoresearch loop: tune values, commit, run, log result, keep/discard.

PARAMS: dict[str, float | int] = {
    "lookback_n": 20,  # Donchian channel lookback (entry breakout window)
    "exit_lookback_n": 10,  # Donchian channel exit window (Turtle Trading variant)
    "atr_period": 14,  # ATR smoothing period (Wilder)
    "atr_stop_mult": 2.0,  # ATR multiplier для stop loss
}

# ============================================================
# DO NOT MODIFY BELOW (per program_donchian.md anti-snooping)
# ============================================================


def main() -> int:
    t0 = time.time()
    split = load_split()
    train_df = split.train_df

    print("autoresearch_donchian experiment START")
    print(f"  PARAMS: {PARAMS}")
    print(f"  train data: {len(train_df)} bars ({split.train_start} → {split.train_end})")
    print(f"  held-out: {len(split.heldout_df)} bars (NOT touched in search)")
    print()

    try:
        result = evaluate_metric(df=train_df, params=PARAMS, use_wfa=True)
    except Exception as exc:  # noqa: BLE001 — autoresearch crash log
        elapsed = time.time() - t0
        print("---")
        print("metric (sharpe):  nan")
        print("n_trades:         0")
        print("mc_p:             nan")
        print("fold_sharpes:     []")
        print("status:           crash")
        print(f"error:            {type(exc).__name__}: {exc}")
        print(f"seconds_total:    {elapsed:.1f}")
        return 1

    elapsed = time.time() - t0
    print("---")
    print(f"metric (sharpe):  {result['metric']:.4f}")
    print(f"n_trades:         {result['n_trades']}")
    print(f"mc_p:             {result['mc_p']:.4f}")
    print(f"fold_sharpes:     {[round(s, 3) for s in result['fold_sharpes']]}")
    print(f"status:           {result['status']}")
    print(f"seconds_total:    {elapsed:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
