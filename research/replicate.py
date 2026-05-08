"""research replicate — apply 4H PASS volume_breakout params на other timeframes.

Operator directive: растиражировать success на остальные таймфреймы.

Step 1: exact 4H PASS params on 5M/15M/1H — sanity check.
Step 2: targeted multi-seed sweep on volume_breakout per timeframe (search_v7 separate).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.strategies import evaluate_heldout, evaluate_wfa  # noqa: E402

# 4H PASS params from sweep#10 seed=52
PASS_PARAMS_4H: dict[str, Any] = {
    "lookback_n": 9,
    "exit_lookback_n": 8,
    "vol_window": 10,
    "vol_mult": 1.39,
    "atr_period": 16,
    "atr_stop_mult": 2.52,
}

TIMEFRAMES = [
    ("5M", "data/BTCUSDT_5m.parquet", 105192, 10000, 2500, 100),
    ("15M", "data/BTCUSDT_15m.parquet", 35064, 12000, 3000, 96),
    ("1H", "data/BTCUSDT_1h.parquet", 8766, 3000, 750, 24),
    ("4H", "data/BTCUSDT_4h.parquet", 2190, 2000, 500, 20),
]


def load_split(parquet_path: str, train_ratio: float = 0.80) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(parquet_path).reset_index(drop=True)
    if "timestamp" not in df.columns and "time" in df.columns:
        df["timestamp"] = pd.to_datetime(df["time"], errors="coerce")
    n = len(df)
    split_idx = int(n * train_ratio)
    return df.iloc[:split_idx].reset_index(drop=True), df.iloc[split_idx:].reset_index(drop=True)


def main() -> None:
    print("=== Replicate 4H PASS params на other timeframes (exact params, no rescale) ===")
    print("Source: 4H sweep#10 seed=52 volume_breakout")
    print(f"Params: {PASS_PARAMS_4H}\n")

    print(
        f"{'TF':>4s} | {'BARS_PER_YR':>11s} | {'Train n':>10s} | {'Train Sharpe':>13s} | {'Train PnL':>10s} | {'Held Sharpe':>12s} | {'Held PnL':>10s} | {'Held n':>7s}"
    )
    print("-" * 120)

    # Patch BARS_PER_YEAR per TF (used in metrics)
    import research.strategies as strat_mod

    for tf_name, parquet, bars_y, train_b, test_b, embargo in TIMEFRAMES:
        train_df, held_df = load_split(parquet)
        # Monkey-patch BARS_PER_YEAR в strategies module
        strat_mod.BARS_PER_YEAR = bars_y

        # WFA
        wfa = evaluate_wfa(
            train_df,
            "volume_breakout",
            PASS_PARAMS_4H,
            train_bars=train_b,
            test_bars=test_b,
            k_folds=5,
            embargo_bars=embargo,
        )
        # Held-out
        held = evaluate_heldout(held_df, "volume_breakout", PASS_PARAMS_4H)

        train_s = wfa["metric"]
        train_p = wfa.get("total_pnl_pct", 0.0)
        held_s = held["metric"]
        held_p = held.get("total_pnl_pct", 0.0)
        held_n = held.get("n_trades", 0)

        verdict = ""
        if held_s > 0 and held_p >= 10:
            verdict = " ★ PASS"
        elif held_s > 0:
            verdict = " (positive direction)"
        else:
            verdict = " sign-flip"

        print(
            f"{tf_name:>4s} | {bars_y:>11d} | {wfa['n_trades']:>10d} | "
            f"{train_s:>+13.3f} | {train_p:>+9.1f}% | "
            f"{held_s:>+12.3f} | {held_p:>+9.1f}% | {held_n:>7d}{verdict}"
        )


if __name__ == "__main__":
    main()
