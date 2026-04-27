"""Donchian backtest driver — S35 T4 backtest run (anti-snooping per ADR 0054).

Loads BTCUSDT_4h.parquet, runs WFA K=5 folds via WalkForwardRunner using
DONCHIAN_LONG_ONLY_PARAMS LOCKED parameters, evaluates against amended
acceptance gates (ADR 0052 + ADR 0054), writes verdict к
data/donchian_backtest_results.json.

Strategy dispatch reuses src.backtest.indicators `donchian` strategy_type +
src.backtest.replay_engine SL/TP handler with sl_atr_mult=2.0 (matching
DONCHIAN_LONG_ONLY_PARAMS["atr_stop_mult"]) и tp_atr_mult=1e9 (effectively
disabled — Donchian uses ATR trailing stop OR channel exit, not fixed TP).

CLI:
    .venv/bin/python -m src.backtest.donchian_runner

Per ADR 0054: single pre-registered run, NO parameter sweep, NO peek-and-iterate.
N_trials counter = 5 (S13/S15/S17/S22/S35 cumulative deflation).
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from src.analytics.cross_trial_log import CrossTrialLog
from src.analytics.dsr import compute_dsr_with_status
from src.backtest.data_collector import load_market_data
from src.backtest.mc_permutation import sign_flip_p_value
from src.backtest.replay_engine import run_replay
from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.backtest.trade_extractor import extract_trade_records
from src.backtest.walk_forward import (
    WalkForwardRunner,
    WindowSplitter,
    evaluate_acceptance_gate,
)
from src.risk.trade_history import TradeRecord
from src.signalgen.donchian_strategy import DONCHIAN_LONG_ONLY_PARAMS

# ADR 0054 amended gates (consilium binding).
SHARPE_THRESHOLD = 0.7
P_THRESHOLD = 0.05
N_EFF_THRESHOLD = 50
T5_FLOOR = 50
DSR_THRESHOLD = 0.95
N_TRIALS_LOCKED = 5  # S13/S15/S17/S22/S35 cumulative per ADR 0054


def _build_strategy_config() -> dict[str, Any]:
    """Build replay_engine config с donchian strategy_type per ADR 0054 LOCKED."""
    atr_stop_mult = float(cast(Decimal, DONCHIAN_LONG_ONLY_PARAMS["atr_stop_mult"]))
    return {
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
                    "lookback_n": int(cast(int, DONCHIAN_LONG_ONLY_PARAMS["lookback_n"])),
                    "exit_lookback_n": int(cast(int, DONCHIAN_LONG_ONLY_PARAMS["exit_lookback_n"])),
                },
                "atr": {
                    "period": int(cast(int, DONCHIAN_LONG_ONLY_PARAMS["atr_period"])),
                    "sl_atr_mult": atr_stop_mult,
                    # TP effectively disabled (Donchian uses ATR trailing stop, not fixed TP).
                    "tp_atr_mult": 1.0e9,
                },
            },
        },
    }


def _run_donchian_wfa(
    *,
    parquet_path: Path,
    symbol: str,
    start: str,
    end: str,
    interval_label: str,
    bars_per_year: int,
    train_bars: int,
    test_bars: int,
    k_folds: int,
    embargo_bars: int,
) -> dict[str, Any]:
    """Run WFA single-symbol для Donchian + return verdict dict."""
    config = _build_strategy_config()
    config["bars_per_year"] = bars_per_year

    # Load OHLCV.
    df = load_market_data(
        {
            "data": {
                "source": "parquet",
                "parquet_path": str(parquet_path),
                "start_date": start,
                "end_date": end,
            }
        }
    )
    if df.empty:
        raise ValueError(f"empty OHLCV after filter [{start}, {end}] from {parquet_path}")
    print(f"Loaded {len(df)} bars from {parquet_path}", flush=True)

    splitter = WindowSplitter(
        train_bars=train_bars,
        test_bars=test_bars,
        embargo_bars=embargo_bars,
        k_folds=k_folds,
    )
    runner = WalkForwardRunner(splitter=splitter, replay_fn=run_replay)
    runner_result = runner.run(df=df, config=config, symbol=symbol)

    # MC sign-flip p-value on aggregated OOS returns.
    oos_trades_df = runner_result["aggregate"]["oos_trades_df"]
    if oos_trades_df.empty:
        mc_p = 1.0
    else:
        import numpy as np

        raw = oos_trades_df["net_pnl"].astype(float).to_numpy()
        returns_arr = np.asarray(raw, dtype=float) / 10000.0
        mc_p = sign_flip_p_value(returns_arr, n_iterations=2000, seed=42)

    # Per-fold trade extraction.
    from datetime import UTC as _UTC

    import pandas as pd

    trades: list[TradeRecord] = []
    fold_sharpes: list[float] = []
    for fold_data in runner_result["folds"]:
        fold_sharpes.append(float(fold_data["oos_is_sharpe_ratio"]))
        fold_trades_df = fold_data.get("oos_trades_df")
        if fold_trades_df is not None and not fold_trades_df.empty:
            df_norm = fold_trades_df.copy()
            if "timestamp_open" in df_norm.columns and "entry_ts" not in df_norm.columns:
                df_norm = df_norm.rename(
                    columns={
                        "timestamp_open": "entry_ts",
                        "timestamp_close": "exit_ts",
                    }
                )
            for _col in ("entry_ts", "exit_ts"):
                if _col in df_norm.columns:
                    s = pd.to_datetime(df_norm[_col])
                    if s.dt.tz is None:
                        s = s.dt.tz_localize(_UTC)
                    df_norm[_col] = s
            if "fees_paid" not in df_norm.columns:
                entry_fee = df_norm.get("entry_fee", 0)
                exit_fee = df_norm.get("exit_fee", 0)
                df_norm["fees_paid"] = entry_fee + exit_fee
            trades.extend(extract_trade_records(df_norm, symbol=symbol))

    n_trades_raw = len(trades)

    # Trial-level mean of fold OOS Sharpes для cross-trial pooling per ADR 0056
    # (clarifies arithmetic mean of fold OOS Sharpes vs pooled trade-level OOS Sharpe).
    trial_mean_fold_oos_sharpe = (
        float(sum(fold_sharpes) / len(fold_sharpes)) if fold_sharpes else float("nan")
    )

    # T1-T6 metrics (informational).
    metrics = compute_t1_t6_metrics(
        trades=trades,
        fold_oos_is_sharpe=fold_sharpes,
        bars_per_year=bars_per_year,
    )

    # DSR per ADR 0054: N_trials = 5 LOCKED (S13/S15/S17/S22/S35 cumulative).
    # ADR 0056 sigma_SR sourcing hierarchy:
    #   - N >= 3 cross-trial entries: stdev(cross_trial_sharpes) [PREFERRED]
    #   - 1-2 entries:                NaN [DEGENERATE — df<2 inadmissible]
    #   - 0 entries:                  None [EMPTY]
    # REMOVED (S36 T6): per-fold Sharpe stdev as sigma_SR proxy — confounds within-trial
    # noise с cross-trial selection variability per Bailey 2014 eq.12.
    trial_log = CrossTrialLog(path=Path("data/cross_trial_sharpes.json"))
    pre_existing = trial_log.get_oos_sharpes()
    cross_trial_sharpes = pre_existing + [trial_mean_fold_oos_sharpe]
    if len(cross_trial_sharpes) >= 3 and not math.isnan(trial_mean_fold_oos_sharpe):
        sigma_sr: float | None = statistics.stdev(cross_trial_sharpes)
    elif len(cross_trial_sharpes) >= 1:
        # DEGENERATE: 1-2 entries → NaN sigma; caller falls back к n_trials=1 path.
        sigma_sr = float("nan")
    else:
        sigma_sr = None

    # Compute DSR с status flag per ADR 0056 n_trades thresholds.
    if (
        sigma_sr is not None
        and not math.isnan(sigma_sr)
        and not math.isnan(trial_mean_fold_oos_sharpe)
    ):
        dsr_info = compute_dsr_with_status(
            trades=trades, n_trials=N_TRIALS_LOCKED, sigma_sr=sigma_sr
        )
    else:
        # DEGENERATE OR EMPTY log path: n_trials=1, no multi-testing penalty.
        # Honest reporting: gate likely FAIL, recorded в failed_criteria.
        dsr_info = compute_dsr_with_status(trades=trades, n_trials=1)
    dsr_value = dsr_info["dsr"]

    # Acceptance gate (ADR 0052 amended thresholds).
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes,
        mc_p_value=mc_p,
        sharpe_threshold=SHARPE_THRESHOLD,
        p_threshold=P_THRESHOLD,
        n_trades_raw=n_trades_raw,
        n_trades_n_eff=n_trades_raw,  # single-symbol — n_eff ≈ n_raw (no correlation deflation)
        n_eff_threshold=N_EFF_THRESHOLD,
        t5_floor=T5_FLOOR,
    )

    # Verdict — ADR 0054 conjoint AND of 6 gates.
    failed_criteria: list[str] = list(gate["failed_criteria"])
    dsr_pass = (
        dsr_value is not None
        and not (isinstance(dsr_value, float) and math.isnan(dsr_value))
        and dsr_value >= DSR_THRESHOLD
    )
    if not dsr_pass:
        failed_criteria.append("dsr_threshold")

    verdict = "PASS" if not failed_criteria else "FAIL"

    return {
        "strategy": "DonchianBreakoutStrategy",
        "params": {
            k: (str(v) if isinstance(v, Decimal) else v)
            for k, v in DONCHIAN_LONG_ONLY_PARAMS.items()
        },
        "symbol": symbol,
        "timeframe": interval_label,
        "period": {"start": start, "end": end, "n_bars": len(df)},
        "wfa": {
            "train_bars": train_bars,
            "test_bars": test_bars,
            "embargo_bars": embargo_bars,
            "k_folds": k_folds,
        },
        "n_trades_raw": n_trades_raw,
        "n_trades_n_eff": n_trades_raw,
        "fold_oos_is_sharpe_ratios": fold_sharpes,
        "trial_mean_fold_oos_sharpe": trial_mean_fold_oos_sharpe,
        "mc_p_value": mc_p,
        "dsr": dsr_value,
        "dsr_status": dsr_info["status"],
        "sigma_sr_cross_trial": sigma_sr,
        "n_trials_counter": N_TRIALS_LOCKED,
        "metrics": {
            "t1_sharpe_oos": metrics.get("t1_sharpe_oos"),
            "t2_sortino_oos": metrics.get("t2_sortino_oos"),
            "t3_max_drawdown": metrics.get("t3_max_drawdown"),
            "t4_win_rate": metrics.get("t4_win_rate"),
            "t4_avg_rr": metrics.get("t4_avg_rr"),
            "t5_n_trades": metrics.get("t5_n_trades"),
            "t5_mean_pnl_pct": metrics.get("t5_mean_pnl_pct"),
            "t5_t_stat": metrics.get("t5_t_stat"),
            "t6_oos_is_sharpe_ratio_mean": metrics.get("t6_oos_is_sharpe_ratio_mean"),
        },
        "acceptance_gate": gate,
        "thresholds": {
            "sharpe_per_fold": SHARPE_THRESHOLD,
            "mc_p_value": P_THRESHOLD,
            "n_eff": N_EFF_THRESHOLD,
            "t5_floor": T5_FLOOR,
            "dsr": DSR_THRESHOLD,
        },
        "verdict": verdict,
        "failed_criteria": failed_criteria,
        "ran_at": datetime.now(UTC).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.backtest.donchian_runner")
    parser.add_argument("--input", type=Path, default=Path("data/BTCUSDT_4h.parquet"))
    parser.add_argument("--output", type=Path, default=Path("data/donchian_backtest_results.json"))
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2026-04-26")
    parser.add_argument("--interval-label", default="4h")
    # 4H bars: 6 per day → 6 * 365 = 2190.
    parser.add_argument("--bars-per-year", type=int, default=2190)
    # Per S33 T4 CC6 (b) — 4H WFA window: train=1000/test=250.
    parser.add_argument("--wfa-train", type=int, default=1000)
    parser.add_argument("--wfa-test", type=int, default=250)
    parser.add_argument("--wfa-folds", type=int, default=5)
    parser.add_argument("--wfa-embargo", type=int, default=20)
    args = parser.parse_args(argv)

    result = _run_donchian_wfa(
        parquet_path=args.input,
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        interval_label=args.interval_label,
        bars_per_year=args.bars_per_year,
        train_bars=args.wfa_train,
        test_bars=args.wfa_test,
        k_folds=args.wfa_folds,
        embargo_bars=args.wfa_embargo,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=str))

    print(json.dumps(result, indent=2, default=str), flush=True)
    print(f"\nVerdict: {result['verdict']}", flush=True)
    print(f"Failed criteria: {result['failed_criteria']}", flush=True)
    print(f"Output written к {args.output}", flush=True)

    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
