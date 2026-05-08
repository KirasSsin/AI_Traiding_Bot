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

from research.prepare import evaluate_metric, load_split

# BEST PARAMS from search loop (P5_5, train score=2.5766 Sharpe=1.27 n=33)
BEST_PARAMS: dict[str, Any] = {
    "lookback_n": 11,
    "exit_lookback_n": 5,
    "atr_period": 13,
    "atr_stop_mult": 0.61,
}

TRAIN_SHARPE = 1.2704  # from search output
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
    result = evaluate_metric(df=split.heldout_df, params=BEST_PARAMS, use_wfa=False)
    print("=== HELD-OUT RESULT ===")
    print(f"Sharpe (held-out): {result['metric']:.4f}")
    print(f"n_trades: {result['n_trades']}")
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
