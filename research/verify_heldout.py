"""research — held-out verification (final unbiased verdict).

Runs best PARAMS на held-out set (1455 bars 2025-08-26 → 2026-04-26)
which was NEVER visible during search loop.

Per Bailey & López de Prado 2014 anti-snooping: this is the ONLY admissible
final metric. Train Sharpe = potentially overfit. Held-out Sharpe = honest.

trader-expert recommendation Q6: PASS threshold = held-out Sharpe ≥ 0.5 × train Sharpe.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.backtest_v2 import evaluate_heldout
from research.prepare import load_split

# Iter 2 BEST PARAMS from search_v2 loop (P4v2_1, train score=5.70 Sharpe=2.50 n=44 PnL+63%)
# EMA filter EMPIRICALLY FALSIFIED — best ema_filter_period=0 (disabled).
BEST_PARAMS: dict[str, Any] = {
    "lookback_n": 15,
    "exit_lookback_n": 6,
    "atr_period": 7,
    "atr_stop_mult": 2.5,
    "ema_filter_period": 0,
}

TRAIN_SHARPE = 2.4985  # from search_v2 output
PASS_THRESHOLD_RATIO = 0.5  # trader-expert Q6


def main() -> int:
    split = load_split()
    print("=== HELD-OUT VERIFICATION ===")
    print(f"Best PARAMS from search: {BEST_PARAMS}")
    print(f"Train Sharpe (search): {TRAIN_SHARPE}")
    print(f"Held-out range: {split.heldout_start} → {split.heldout_end}")
    print(f"Held-out bars: {len(split.heldout_df)}")
    print()

    # Held-out: single contiguous backtest (NO WFA — too short for K=5)
    result = evaluate_heldout(split.heldout_df, BEST_PARAMS)
    print("=== HELD-OUT RESULT ===")
    print(f"Sharpe (held-out): {result['metric']:.4f}")
    print(f"n_trades: {result['n_trades']}")
    print(f"total_pnl_pct: {result.get('total_pnl_pct', 0):.2f}")
    print(f"win_rate: {result.get('win_rate', float('nan')):.4f}")
    print(f"status: {result['status']}")
    print()

    # Verdict per trader-expert Q6 threshold
    pass_threshold = TRAIN_SHARPE * PASS_THRESHOLD_RATIO
    heldout_sharpe = result["metric"]

    print("=== HONEST VERDICT ===")
    print(f"Pass threshold: held-out Sharpe ≥ {pass_threshold:.3f} (= 0.5 × train {TRAIN_SHARPE})")

    import math

    if math.isnan(heldout_sharpe):
        verdict = "FAIL: held-out Sharpe is NaN (no trades OR insufficient data)"
    elif result["n_trades"] < 5:
        verdict = f"FAIL: held-out n_trades={result['n_trades']} < 5 (insufficient sample)"
    elif heldout_sharpe < 0:
        verdict = f"FAIL: held-out Sharpe {heldout_sharpe:.3f} < 0 (negative — overfit confirmed)"
    elif heldout_sharpe < pass_threshold:
        ratio = heldout_sharpe / TRAIN_SHARPE if TRAIN_SHARPE > 0 else float("nan")
        verdict = (
            f"FAIL: held-out Sharpe {heldout_sharpe:.3f} < threshold {pass_threshold:.3f} "
            f"({ratio*100:.1f}% of train — degradation > 50% indicates overfit)"
        )
    else:
        ratio = heldout_sharpe / TRAIN_SHARPE
        verdict = (
            f"PASS candidate: held-out Sharpe {heldout_sharpe:.3f} ≥ threshold {pass_threshold:.3f} "
            f"({ratio*100:.1f}% of train preserved) — feed к formal kit cycle ROUND 7 brainstorm"
        )

    print(f"VERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
