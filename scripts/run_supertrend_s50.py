"""S50 T8 — Supertrend BTCUSDT 1H train sweep + single held-out eval.

Anti-snooping discipline (ADR 0067 Q4):
- Param sweep runs on TRAIN slice ONLY (ts < 2025-06-01).
- Winner picked by TRAIN Sharpe with n_trades sanity >= MIN_TRADES_WINNER.
- eval_heldout_once() called EXACTLY ONCE on winner. No re-pick after seeing held-out.

Outputs (data/ is gitignored — results embedded in backlog doc by commit step):
- data/supertrend_s50_sweep.json  — full 35-combo sweep table
- data/supertrend_s50_heldout.json — winner + held-out verdict

Verdict threshold (ADR 0067):
  PROCEED to T9 WFA: held-out Sharpe > 0 AND held-out n_trades >= 15
  else: honest FAIL
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

# Re-use production implementations from autoresearch_endless.py
from scripts.autoresearch_endless import (
    BARS_PER_YEAR_BY_INTERVAL,
    _backtest,
    _normalize_df,
    eval_heldout_once,
    split_train_heldout,
    strat_supertrend,
)

# ─── Config ───
DATA_PATH = "data/BTCUSDT_1h.parquet"
INTERVAL = "60"
OUT_DIR = Path("data")
SWEEP_JSON = OUT_DIR / "supertrend_s50_sweep.json"
HELDOUT_JSON = OUT_DIR / "supertrend_s50_heldout.json"

# Anti-snooping: minimum trades for winner eligibility.
# A param combo with < MIN_TRADES_WINNER train trades could be a 2-trade fluke;
# exclude from winner selection even if Sharpe is numerically highest.
MIN_TRADES_WINNER = 10

# Held-out verdict threshold (ADR 0067)
HELDOUT_SHARPE_THRESHOLD = 0.0
HELDOUT_NTRADES_THRESHOLD = 15

# Param grid: 7 ATR periods × 5 multipliers = 35 combos
ATR_PERIODS = [7, 9, 10, 12, 14, 16, 21]
MULTIPLIERS = [2.0, 2.5, 3.0, 3.5, 4.0]
# ATR stop multiplier (single value — for T8 empirical sweep we fix to 2.0 which is
# the midpoint of autoresearch base_atr_stop [1.5,2.0,2.5,3.0]; keeps sweep at 35
# combos, not 35×4=140, which is the mandate "35 combos" from brief)
ATR_STOP_MULT = 2.0


def run_sweep(train_df: pd.DataFrame, bpy: int) -> list[dict]:
    """Sweep all 35 supertrend combos on TRAIN. Return sorted results (best first)."""
    results = []
    for atr_period in ATR_PERIODS:
        for mult in MULTIPLIERS:
            params = {"atr_period": atr_period, "mult": mult}
            try:
                entry, exit_, warmup, atr_arr = strat_supertrend(train_df, **params)
                metrics = _backtest(train_df, entry, exit_, atr_arr, ATR_STOP_MULT, warmup, bpy)
            except Exception as exc:
                results.append(
                    {
                        "atr_period": atr_period,
                        "mult": mult,
                        "error": str(exc),
                        "n_trades": 0,
                        "sharpe": float("nan"),
                        "pnl_pct": 0.0,
                        "win_rate": float("nan"),
                        "winner_eligible": False,
                    }
                )
                continue

            sharpe = metrics["sharpe"]
            n_trades = metrics["n_trades"]
            eligible = n_trades >= MIN_TRADES_WINNER and not (np.isnan(sharpe))
            results.append(
                {
                    "atr_period": atr_period,
                    "mult": mult,
                    "n_trades": n_trades,
                    "pnl_pct": round(metrics["pnl_pct"], 4),
                    "sharpe": round(float(sharpe), 4) if not np.isnan(sharpe) else float("nan"),
                    "win_rate": round(float(metrics["win_rate"]), 4)
                    if not np.isnan(metrics.get("win_rate", float("nan")))
                    else float("nan"),
                    "winner_eligible": eligible,
                }
            )

    return results


def pick_winner(results: list[dict]) -> dict | None:
    """Pick combo with highest TRAIN Sharpe among eligible (n_trades >= MIN_TRADES_WINNER)."""
    eligible = [
        r
        for r in results
        if r.get("winner_eligible") and not np.isnan(r.get("sharpe", float("nan")))
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda r: r["sharpe"])


def main() -> int:
    print("=" * 60)
    print("S50 T8 — Supertrend BTCUSDT 1H sweep + held-out eval")
    print("=" * 60)

    bpy = BARS_PER_YEAR_BY_INTERVAL[INTERVAL]
    print(
        f"bars_per_year={bpy} | atr_stop_mult={ATR_STOP_MULT} | min_trades_winner={MIN_TRADES_WINNER}"
    )

    # ── Load + split ──
    print(f"\nLoading {DATA_PATH} ...", flush=True)
    full_df = _normalize_df(DATA_PATH)
    print(
        f"Full data: {len(full_df):,} bars  {full_df['ts'].iloc[0].date()} → {full_df['ts'].iloc[-1].date()}"
    )

    train_df, heldout_df = split_train_heldout(full_df)
    print(
        f"TRAIN : {len(train_df):,} bars  {train_df['ts'].iloc[0].date()} → {train_df['ts'].iloc[-1].date()}"
    )
    print(
        f"HELDOUT: {len(heldout_df):,} bars  {heldout_df['ts'].iloc[0].date()} → {heldout_df['ts'].iloc[-1].date()}"
    )

    if len(train_df) < 500:
        print("BLOCKED — train slice too small (< 500 bars)")
        return 1
    if len(heldout_df) < 100:
        print("WARNING — held-out slice small (< 100 bars); eval may be noisy")

    # ── Step 2: sweep TRAIN ──
    print(f"\nSweeping {len(ATR_PERIODS) * len(MULTIPLIERS)} combos on TRAIN ONLY ...", flush=True)
    sweep_results = run_sweep(train_df, bpy)

    # Print sweep table
    print(f"\n{'atr':>5} {'mult':>5} {'n_trades':>9} {'sharpe':>8} {'pnl%':>8} {'eligible':>9}")
    print("-" * 55)
    for r in sweep_results:
        print(
            f"{r['atr_period']:>5} {r['mult']:>5.1f} {r['n_trades']:>9} "
            f"{r['sharpe']:>8.3f} {r['pnl_pct']:>8.2f} {'Y' if r['winner_eligible'] else 'N':>9}"
        )

    # Save sweep JSON
    OUT_DIR.mkdir(exist_ok=True)
    SWEEP_JSON.write_text(
        json.dumps(
            {
                "description": "S50 T8 supertrend BTCUSDT 1H train sweep (35 combos)",
                "data_path": DATA_PATH,
                "train_bars": len(train_df),
                "train_start": str(train_df["ts"].iloc[0].date()),
                "train_end": str(train_df["ts"].iloc[-1].date()),
                "heldout_bars": len(heldout_df),
                "heldout_start": str(heldout_df["ts"].iloc[0].date()),
                "heldout_end": str(heldout_df["ts"].iloc[-1].date()),
                "atr_stop_mult": ATR_STOP_MULT,
                "min_trades_winner": MIN_TRADES_WINNER,
                "combos": sweep_results,
            },
            indent=2,
            default=str,
        )
    )
    print(f"\nSweep saved to {SWEEP_JSON}")

    # ── Step 3: pick winner (TRAIN Sharpe) ──
    winner = pick_winner(sweep_results)
    if winner is None:
        print("\nNo eligible winner (all combos below MIN_TRADES_WINNER or all-NaN Sharpe).")
        verdict = "FAIL"
        heldout_result = {
            "winner": None,
            "verdict": verdict,
            "reason": "no_eligible_winner",
        }
        HELDOUT_JSON.write_text(json.dumps(heldout_result, indent=2))
        print(f"Held-out result saved to {HELDOUT_JSON}")
        print(f"\nVERDICT: {verdict}")
        return 0

    print("\nWINNER (highest train Sharpe among eligible):")
    print(f"  atr_period={winner['atr_period']}  mult={winner['mult']}")
    print(
        f"  train_sharpe={winner['sharpe']:.4f}  n_trades={winner['n_trades']}  pnl%={winner['pnl_pct']:.2f}"
    )

    # ── Step 3: single held-out eval ──
    print("\nRunning single held-out eval (ONCE, anti-snooping)...", flush=True)
    winner_combo = {
        "strategy": "supertrend",
        "params": {"atr_period": winner["atr_period"], "mult": winner["mult"]},
        "atr_stop_mult": ATR_STOP_MULT,
        "bars_per_year": bpy,
    }
    heldout_metrics = eval_heldout_once(winner_combo, heldout_df)
    print(f"  held-out Sharpe : {heldout_metrics['heldout_sharpe']:.4f}")
    print(f"  held-out n_trades: {heldout_metrics['heldout_n_trades']}")
    print(f"  held-out pnl%   : {heldout_metrics['heldout_pnl_pct']:.2f}")
    print(
        f"  held-out win_rate: {heldout_metrics['heldout_win_rate']:.3f}"
        if heldout_metrics.get("heldout_win_rate")
        else ""
    )

    # ── Step 4: verdict ──
    ho_sharpe = heldout_metrics["heldout_sharpe"]
    ho_n = heldout_metrics["heldout_n_trades"]
    proceed = (
        not np.isnan(ho_sharpe)
        and ho_sharpe > HELDOUT_SHARPE_THRESHOLD
        and ho_n >= HELDOUT_NTRADES_THRESHOLD
    )
    verdict = "PROCEED_T9" if proceed else "FAIL"

    reason_parts = []
    if np.isnan(ho_sharpe):
        reason_parts.append("sharpe=NaN")
    elif ho_sharpe <= HELDOUT_SHARPE_THRESHOLD:
        reason_parts.append(f"sharpe={ho_sharpe:.4f} <= threshold {HELDOUT_SHARPE_THRESHOLD}")
    if ho_n < HELDOUT_NTRADES_THRESHOLD:
        reason_parts.append(f"n_trades={ho_n} < threshold {HELDOUT_NTRADES_THRESHOLD}")
    reason = "; ".join(reason_parts) if reason_parts else "all thresholds met"

    heldout_result = {
        "description": "S50 T8 held-out eval — single evaluation, anti-snooping",
        "winner_params": {"atr_period": winner["atr_period"], "mult": winner["mult"]},
        "train_sharpe": winner["sharpe"],
        "train_n_trades": winner["n_trades"],
        "train_pnl_pct": winner["pnl_pct"],
        "heldout_sharpe": heldout_metrics["heldout_sharpe"],
        "heldout_n_trades": heldout_metrics["heldout_n_trades"],
        "heldout_pnl_pct": heldout_metrics["heldout_pnl_pct"],
        "heldout_win_rate": heldout_metrics.get("heldout_win_rate"),
        "verdict": verdict,
        "verdict_reason": reason,
        "thresholds": {
            "sharpe_gt": HELDOUT_SHARPE_THRESHOLD,
            "n_trades_gte": HELDOUT_NTRADES_THRESHOLD,
        },
    }
    HELDOUT_JSON.write_text(json.dumps(heldout_result, indent=2, default=str))
    print(f"Held-out result saved to {HELDOUT_JSON}")

    print("\n" + "=" * 60)
    print(f"VERDICT: {verdict}")
    if not proceed:
        print(f"Reason : {reason}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
