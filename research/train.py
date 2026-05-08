"""research — single experiment runner (iter 2: EMA200 trend filter dimension).

Адаптировано из karpathy/autoresearch train.py paradigm.

Agent EDITS THIS FILE. Each experiment = one git commit с modified params.

Per program.md: tune `PARAMS` dict + run → check metric → keep/discard.

Iter 1 (closed FAIL): pure Donchian S35 hyperparameter tuning. Held-out -3.23.
Iter 2 (active): + EMA200 trend filter dimension (per trader-expert prior).

Output:
    ---
    metric (sharpe):  X.XX
    n_trades:         N
    total_pnl_pct:    X.XX
    win_rate:         X.XXX
    fold_sharpes:     [...]
    fold_pnls:        [...]
    status:           ok|insufficient_data|crash
    seconds_total:    X.X
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add bot project к sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from research.backtest_v2 import evaluate_wfa
from research.prepare import load_split

# ============================================================
# AGENT EDITS THIS BLOCK
# ============================================================
# Iter 2 baseline = ADR 0054 LOCKED Donchian + EMA200 filter (new dimension).
# ema_filter_period=0 disables filter (= iter 1 baseline). Set к 200 для standard EMA200 filter.

PARAMS: dict[str, float | int] = {
    "lookback_n": 20,  # Donchian channel lookback (entry breakout window)
    "exit_lookback_n": 10,  # Donchian channel exit window (Turtle Trading variant)
    "atr_period": 14,  # ATR smoothing period (Wilder)
    "atr_stop_mult": 2.0,  # ATR multiplier для stop loss
    "ema_filter_period": 200,  # EMA trend filter (0 = disabled, 200 = standard EMA200)
}

# ============================================================
# DO NOT MODIFY BELOW (per program.md anti-snooping)
# ============================================================


def main() -> int:
    t0 = time.time()
    split = load_split()
    train_df = split.train_df

    print("research experiment START (iter 2 — EMA filter dimension)")
    print(f"  PARAMS: {PARAMS}")
    print(f"  train data: {len(train_df)} bars ({split.train_start} → {split.train_end})")
    print(f"  held-out: {len(split.heldout_df)} bars (NOT touched in search)")
    print()

    try:
        result = evaluate_wfa(train_df, PARAMS)
    except Exception as exc:  # noqa: BLE001 — autoresearch crash log
        elapsed = time.time() - t0
        print("---")
        print("metric (sharpe):  nan")
        print("n_trades:         0")
        print("total_pnl_pct:    nan")
        print("win_rate:         nan")
        print("fold_sharpes:     []")
        print("fold_pnls:        []")
        print("status:           crash")
        print(f"error:            {type(exc).__name__}: {exc}")
        print(f"seconds_total:    {elapsed:.1f}")
        return 1

    elapsed = time.time() - t0
    print("---")
    print(f"metric (sharpe):  {result['metric']:.4f}")
    print(f"n_trades:         {result['n_trades']}")
    print(f"total_pnl_pct:    {result.get('total_pnl_pct', 0.0):.2f}")
    print(f"win_rate:         {result.get('win_rate', float('nan')):.4f}")
    print(f"fold_sharpes:     {result['fold_sharpes']}")
    print(f"fold_pnls:        {result.get('fold_pnls', [])}")
    print(f"status:           {result['status']}")
    print(f"seconds_total:    {elapsed:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
