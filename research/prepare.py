"""research — data preparation + runtime utilities.

Адаптировано из karpathy/autoresearch prepare.py paradigm.

DO NOT MODIFY. Per program_donchian.md — fixed evaluation harness.

Loads BTC 4H OHLCV (2023-01-01 → 2026-04-26 = 7273 bars).
Splits 80/20: train (~5818 bars 2023-01 → 2025-09) / held-out (~1455 bars 2025-09 → 2026-04).

Held-out test set NEVER visible during search loop. Final verdict only on held-out.

Bot project precedent: ADR 0014 WFA defaults (train=2000/test=500/k=5/embargo=20).
В autoresearch loop: train portion = full WFA, held-out = unseen final test.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

# Constants — 5M timeframe (per operator directive iter 4: more trades + better PnL)
# Original 4H constants preserved в git history (commit 4231a17 + earlier).
DATA_PATH = Path(__file__).parent.parent / "data" / "BTCUSDT_5m.parquet"
TRAIN_RATIO = 0.80  # 80% search / 20% held-out
BARS_PER_YEAR = 105192  # 5M = 365.25 * 24 * 60 / 5 = 105192
SYMBOL = "BTCUSDT"
INTERVAL = "5"

# Search-time WFA defaults (5M scale: ~28 days train / ~8.7 days test windows)
WFA_TRAIN_BARS = 10000  # ~34.7 days @ 5M
WFA_TEST_BARS = 2500  # ~8.7 days @ 5M
WFA_K_FOLDS = 5
WFA_EMBARGO_BARS = 100  # ~8.3h gap (overnight regime change buffer)

# Held-out evaluation — NO WFA, single contiguous backtest
HELDOUT_MIN_BARS = 5000  # ~17 days safety check (5M scale)


@dataclass(frozen=True)
class DataSplit:
    """Train/held-out OHLCV split. Held-out NEVER touched during search."""

    train_df: pd.DataFrame  # ~5818 bars
    heldout_df: pd.DataFrame  # ~1455 bars
    train_start: str
    train_end: str
    heldout_start: str
    heldout_end: str


def load_split() -> DataSplit:
    """Load BTC 4H + split 80/20. Raises if data missing OR insufficient."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"BTC 4H parquet missing: {DATA_PATH}\n"
            "Run backfill first: ./scripts/start-bot.sh --backfill --symbol BTCUSDT --interval 240 --start 2023-01-01 --end 2026-04-26"
        )
    df = pd.read_parquet(DATA_PATH).reset_index(drop=True)
    # Normalize per src/backtest/data_collector.py:16 — replay_engine expects timestamp column
    if "timestamp" not in df.columns and "time" in df.columns:
        df["timestamp"] = pd.to_datetime(df["time"], errors="coerce")
    n_total = len(df)
    if n_total < 1000:
        raise ValueError(f"Insufficient data: {n_total} bars. Need >= 1000.")

    split_idx = int(n_total * TRAIN_RATIO)
    train_df = df.iloc[:split_idx].reset_index(drop=True)
    heldout_df = df.iloc[split_idx:].reset_index(drop=True)

    if len(heldout_df) < HELDOUT_MIN_BARS:
        raise ValueError(f"Held-out too small: {len(heldout_df)} bars (min {HELDOUT_MIN_BARS})")

    return DataSplit(
        train_df=train_df,
        heldout_df=heldout_df,
        train_start=str(train_df["time"].iloc[0]),
        train_end=str(train_df["time"].iloc[-1]),
        heldout_start=str(heldout_df["time"].iloc[0]),
        heldout_end=str(heldout_df["time"].iloc[-1]),
    )


def evaluate_metric(
    *,
    df: pd.DataFrame,
    params: dict[str, Any],
    use_wfa: bool = True,
) -> dict[str, Any]:
    """Run backtest на df с params. Returns metrics dict.

    Args:
        df: OHLCV (train portion для search, heldout для final)
        params: {lookback_n, exit_lookback_n, atr_period, atr_stop_mult}
        use_wfa: True для search (WFA on train), False для held-out (single backtest)

    Metric: aggregate_oos_sharpe (higher = better). Trader can also weight DSR.
    """
    from src.__main__ import _run_wfa_single_symbol
    from src.backtest.replay_engine import run_replay

    strategy_config: dict[str, Any] = {
        "trading": {
            "initial_balance": 10000.0,
            "commission_taker": 0.001,
            "slippage": 0.0005,
            "position_size_pct": 10.0,
            "max_drawdown_pct": 50.0,
            "long_only": True,
        },
        "strategy": {
            "type": "donchian",
            "indicators": {
                "donchian": {
                    "lookback_n": int(params["lookback_n"]),
                    "exit_lookback_n": int(params["exit_lookback_n"]),
                },
                "atr": {
                    "period": int(params.get("atr_period", 14)),
                    "sl_atr_mult": float(params["atr_stop_mult"]),
                    "tp_atr_mult": 1_000_000.0,  # disable fixed TP — Donchian uses ATR stop
                },
            },
        },
        "bars_per_year": BARS_PER_YEAR,
    }

    if use_wfa:
        # Search: WFA на train portion
        if len(df) < WFA_TRAIN_BARS + WFA_EMBARGO_BARS + WFA_K_FOLDS * WFA_TEST_BARS:
            return {
                "metric": float("nan"),
                "n_trades": 0,
                "fold_sharpes": [],
                "mc_p": float("nan"),
                "status": "insufficient_data",
            }
        trades, fold_sharpes, runner_result, mc_p = _run_wfa_single_symbol(
            symbol=SYMBOL,
            df=df,
            strategy_config=strategy_config,
            train_bars=WFA_TRAIN_BARS,
            test_bars=WFA_TEST_BARS,
            k_folds=WFA_K_FOLDS,
            embargo_bars=WFA_EMBARGO_BARS,
        )
        n_trades = len(trades)
        agg_sharpe = sum(fold_sharpes) / len(fold_sharpes) if fold_sharpes else float("nan")
        return {
            "metric": agg_sharpe,
            "n_trades": n_trades,
            "fold_sharpes": fold_sharpes,
            "mc_p": mc_p,
            "status": "ok",
        }

    # Held-out: single contiguous backtest
    result = run_replay(df, strategy_config)
    metrics = result.get("metrics", {})
    sharpe = float(metrics.get("Sharpe Ratio", float("nan")))
    trades_df = result.get("trades_df")
    n_trades = len(trades_df) if trades_df is not None else 0
    return {
        "metric": sharpe,
        "n_trades": n_trades,
        "fold_sharpes": [],
        "mc_p": float("nan"),
        "status": "heldout_single",
    }


def summary() -> dict[str, Any]:
    """Print data split summary. Used at setup confirmation."""
    split = load_split()
    return {
        "data_path": str(DATA_PATH),
        "total_bars": len(split.train_df) + len(split.heldout_df),
        "train_bars": len(split.train_df),
        "heldout_bars": len(split.heldout_df),
        "train_range": f"{split.train_start} → {split.train_end}",
        "heldout_range": f"{split.heldout_start} → {split.heldout_end}",
        "wfa_min_required": WFA_TRAIN_BARS + WFA_EMBARGO_BARS + WFA_K_FOLDS * WFA_TEST_BARS,
    }


if __name__ == "__main__":
    s = summary()
    print("research — data split summary:")
    for k, v in s.items():
        print(f"  {k}: {v}")
