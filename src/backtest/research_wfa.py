"""S44 T1 — Shared WFA helper for research-mode runners (atr_breakout, volume_breakout).

Replaces RAW envelope with full acceptance discipline (T1-T6 + DSR + MC + N_trials).

PnL accounting: sequential-additive preserved (per ADR 0064 + S42 trader-expert
verdict). Per-fold OOS trades aggregated, DSR computed via cross_trial_sharpes pool.

Pattern source: src/backtest/donchian_runner.py::_run_donchian_wfa (canonical).
Differs: backtest_fn is research kernel (_backtest_single signature), not run_replay
(replay_engine architecturally blocked для research presets per atr_breakout_runner.py
docstring header).

WindowSplitter API: split(total_bars=N) yields (train_start, train_end, test_start,
test_end) integer index 4-tuples — caller slices df itself per fold.
"""

from __future__ import annotations

import math
import statistics
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Protocol

import numpy as np
import pandas as pd

from src.analytics.cross_trial_log import CrossTrialLog
from src.analytics.dsr import compute_dsr_with_status
from src.backtest.mc_permutation import sign_flip_p_value
from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.backtest.walk_forward import WindowSplitter, evaluate_acceptance_gate

# ADR 0052 LOCKED thresholds
DSR_THRESHOLD = 0.95
SHARPE_THRESHOLD = 0.7
P_THRESHOLD = 0.05
N_EFF_THRESHOLD = 50
T5_FLOOR = 50


class _PnlPctTrade(Protocol):
    pnl_pct: float


BacktestFn = Callable[[pd.DataFrame, dict[str, Any], int], dict[str, Any]]


def _min_required_bars(*, train_bars: int, test_bars: int, k_folds: int, embargo_bars: int) -> int:
    """ADR 0014 default: train + embargo + k * test = 2000 + 20 + 5*500 = 4520."""
    return train_bars + embargo_bars + k_folds * test_bars


def _adapt_trades_for_metrics(trades: list[Any]) -> list[Any]:
    """Adapt research _TradeRecord (pnl_pct only) → SimpleNamespace with pnl_quote.

    `compute_t1_t6_metrics` reads `t.pnl_pct` and `t.pnl_quote` (T3 drawdown computation).
    Research trades carry only `pnl_pct` (sequential-additive accounting per ADR 0064 —
    notional implicit). Synthesize pnl_quote = pnl_pct (unit notional) so T3 drawdown
    is computed on equity curve in pnl_pct units.
    """
    return [SimpleNamespace(pnl_pct=float(t.pnl_pct), pnl_quote=float(t.pnl_pct)) for t in trades]


def run_research_wfa(
    *,
    df: pd.DataFrame,
    params: dict[str, Any],
    backtest_fn: BacktestFn,
    bars_per_year: int,
    symbol: str,
    train_bars: int,
    test_bars: int,
    k_folds: int,
    embargo_bars: int,
    n_trials: int = 1,  # S45 C1 — fail-safe default. Multi-hypothesis callers must explicit pass.
    cross_trial_log_path: Path | None = None,
    sprint_tag: str = "S44",
) -> dict[str, Any]:
    """Run WFA для research-mode runner. Returns verdict dict ready для envelope.

    Args:
        df: OHLCV DataFrame с columns [_ts, open, high, low, close, volume].
        params: strategy params dict passed verbatim в backtest_fn.
        backtest_fn: research kernel signature (df_slice, params, bars_per_year) → dict
                     с keys n_trades, sharpe, total_pnl_pct, win_rate, trades.
        bars_per_year: annualization constant (e.g. 8766 for 1H, 2190 for 4H).
        symbol: trading symbol (для error messages).
        train_bars/test_bars/k_folds/embargo_bars: WindowSplitter params (ADR 0014).
        n_trials: для DSR multiple-testing penalty (default 1 = fail-safe; explicit callers must pass).

    NOTE on train slice (S45 B2 documentation gap fix):
    For LOCKED-params research strategies (atr_breakout, volume_breakout), the
    training slice from WindowSplitter is intentionally NOT passed к backtest_fn.
    Reason: parameters are pre-registered (LOCKED), so no in-sample fitting occurs
    per fold — train slice is vestigial для parameter-frozen strategies.

    The `wfa_params["train_bars"]` returned reflects WHERE test windows are positioned
    (offset from data start), не actual IS isolation. For autoresearch strategies
    that DO fit per fold (future), wrap backtest_fn that uses train_slice.
        cross_trial_log_path: cross-trial Sharpe log path (для DSR sigma_SR).
        sprint_tag: tag для potential CrossTrialLog append (currently unused).

    Returns:
        dict с keys: verdict (WFA_PASS/WFA_FAIL/WFA_FAIL_DATA), failed_criteria,
        fold_sharpe_ratios, trial_mean_fold_oos_sharpe, trial_oos_sharpe, mc_p_value,
        dsr, dsr_pass, n_trades_raw, wfa_params, metrics, trades.
    """
    min_required = _min_required_bars(
        train_bars=train_bars,
        test_bars=test_bars,
        k_folds=k_folds,
        embargo_bars=embargo_bars,
    )

    # Data audit — fail-closed if insufficient bars.
    if len(df) < min_required:
        return {
            "verdict": "WFA_FAIL_DATA",
            "failed_criteria": ["data_volume"],
            "fold_sharpe_ratios": [],
            "trial_mean_fold_oos_sharpe": float("nan"),
            "trial_oos_sharpe": float("nan"),
            "mc_p_value": float("nan"),
            "dsr": float("nan"),
            "dsr_pass": False,
            "n_trades_raw": 0,
            "wfa_params": {
                "train_bars": train_bars,
                "test_bars": test_bars,
                "k_folds": k_folds,
                "embargo_bars": embargo_bars,
                "min_required": min_required,
                "actual": len(df),
                "symbol": symbol,
            },
            "metrics": {},
            "trades": [],
        }

    # Run WFA folds.
    splitter = WindowSplitter(
        train_bars=train_bars,
        test_bars=test_bars,
        embargo_bars=embargo_bars,
        k_folds=k_folds,
    )

    fold_sharpes: list[float] = []
    all_oos_trades: list[Any] = []
    all_pnls: list[float] = []

    # S45 B2 — train slice (tr_start:tr_end) intentionally NOT passed к backtest_fn для
    # LOCKED-params strategies (no per-fold fitting). See docstring NOTE above for rationale.
    for fold_idx, (tr_start, tr_end, te_start, te_end) in enumerate(
        splitter.split(total_bars=len(df))
    ):
        test_slice = df.iloc[te_start:te_end].reset_index(drop=True)
        if test_slice.empty:
            continue
        fold_result = backtest_fn(test_slice, params, bars_per_year)
        fold_trades = fold_result.get("trades", [])
        if not fold_trades:
            fold_sharpes.append(0.0)
            continue
        fold_sharpe_raw = fold_result.get("sharpe", 0.0)
        fold_sharpe = float(fold_sharpe_raw) if fold_sharpe_raw is not None else 0.0
        if math.isnan(fold_sharpe):
            fold_sharpe = 0.0
        fold_sharpes.append(fold_sharpe)
        all_oos_trades.extend(fold_trades)
        all_pnls.extend([float(t.pnl_pct) for t in fold_trades])

    n_trades_raw = len(all_oos_trades)

    # MC sign-flip p-value on aggregated OOS pnls.
    if n_trades_raw == 0:
        mc_p = 1.0
    else:
        returns_arr = np.asarray(all_pnls, dtype=float)
        mc_p = sign_flip_p_value(returns_arr, n_iterations=2000, seed=42)

    # Trial-level mean of fold OOS Sharpes (для cross-trial pooling per ADR 0056).
    trial_mean_fold_oos_sharpe = (
        float(sum(fold_sharpes) / len(fold_sharpes)) if fold_sharpes else float("nan")
    )

    # Trial OOS Sharpe = pooled OOS trades Sharpe (separate metric per ADR 0056).
    if n_trades_raw >= 2:
        pnls_arr = np.asarray(all_pnls, dtype=float)
        std_p = float(pnls_arr.std(ddof=1))
        if std_p > 0:
            # Approximate annualization via bars_per_year / mean_holding (~100 bars
            # default). Used as informational metric, не gate input.
            trial_oos_sharpe = float(pnls_arr.mean() / std_p) * math.sqrt(bars_per_year / 100.0)
        else:
            trial_oos_sharpe = 0.0
    else:
        trial_oos_sharpe = float("nan")

    # T1-T6 metrics (informational). Adapt research trades с pnl_quote synth.
    adapted_trades = _adapt_trades_for_metrics(all_oos_trades)
    metrics = compute_t1_t6_metrics(
        trades=adapted_trades,
        fold_oos_is_sharpe=fold_sharpes,
        bars_per_year=bars_per_year,
    )

    # DSR per ADR 0056 sigma_SR sourcing hierarchy.
    if cross_trial_log_path is None:
        cross_trial_log_path = Path("data/cross_trial_sharpes.json")
    trial_log = CrossTrialLog(path=cross_trial_log_path)
    pre_existing = trial_log.get_oos_sharpes()

    # S44 T9 — append к cross-trial log (skip if no valid sharpe)
    if not math.isnan(trial_mean_fold_oos_sharpe):
        try:
            sprint_int = int("".join(filter(str.isdigit, sprint_tag)) or "0")
            trial_log.append_trial(
                sprint=sprint_int,
                symbol=f"{symbol}_{params.get('atr_period', '?')}_{params.get('atr_breakout_mult', '?')}",
                oos_sharpe=trial_mean_fold_oos_sharpe,
            )
        except Exception:
            # Don't break dashboard if log write fails
            pass
    cross_trial_sharpes = pre_existing + [trial_mean_fold_oos_sharpe]
    if len(cross_trial_sharpes) >= 3 and not math.isnan(trial_mean_fold_oos_sharpe):
        sigma_sr: float | None = statistics.stdev(cross_trial_sharpes)
    elif len(cross_trial_sharpes) >= 1:
        sigma_sr = float("nan")
    else:
        sigma_sr = None

    if (
        sigma_sr is not None
        and not math.isnan(sigma_sr)
        and not math.isnan(trial_mean_fold_oos_sharpe)
    ):
        dsr_info = compute_dsr_with_status(
            trades=adapted_trades, n_trials=n_trials, sigma_sr=sigma_sr
        )
    else:
        # DEGENERATE OR EMPTY log path: n_trials=1, no multi-testing penalty.
        dsr_info = compute_dsr_with_status(trades=adapted_trades, n_trials=1)
    dsr_value = dsr_info["dsr"]

    # Acceptance gate (ADR 0052 thresholds).
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes,
        mc_p_value=mc_p,
        sharpe_threshold=SHARPE_THRESHOLD,
        p_threshold=P_THRESHOLD,
        n_trades_raw=n_trades_raw,
        n_trades_n_eff=n_trades_raw,
        n_eff_threshold=N_EFF_THRESHOLD,
        t5_floor=T5_FLOOR,
    )
    failed_criteria: list[str] = list(gate["failed_criteria"])
    dsr_pass = (
        dsr_value is not None
        and not (isinstance(dsr_value, float) and math.isnan(dsr_value))
        and dsr_value >= DSR_THRESHOLD
    )
    if not dsr_pass:
        failed_criteria.append("dsr_threshold")

    verdict = "WFA_PASS" if not failed_criteria else "WFA_FAIL"

    return {
        "verdict": verdict,
        "failed_criteria": failed_criteria,
        "fold_sharpe_ratios": fold_sharpes,
        "trial_mean_fold_oos_sharpe": trial_mean_fold_oos_sharpe,
        "trial_oos_sharpe": trial_oos_sharpe,
        "mc_p_value": mc_p,
        "dsr": dsr_value,
        "dsr_pass": dsr_pass,
        "dsr_status": dsr_info["status"],
        "sigma_sr_cross_trial": sigma_sr,
        "n_trades_raw": n_trades_raw,
        "n_trials": n_trials,
        "wfa_params": {
            "train_bars": train_bars,
            "test_bars": test_bars,
            "k_folds": k_folds,
            "embargo_bars": embargo_bars,
            "min_required": min_required,
            "actual": len(df),
            "symbol": symbol,
        },
        "metrics": metrics,
        "trades": all_oos_trades,
    }
