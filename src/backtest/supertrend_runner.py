"""Supertrend WFA runner — S50 T7 (ADR 0067, hypothesis #10).

Mirrors atr_breakout_runner._run_atr_breakout_wfa pattern:
  - Vectorized _backtest_single for fold execution (Lazybear Supertrend)
  - run_research_wfa with n_trials=10 (Supertrend = hypothesis #10 per ADR 0067)
  - CrossTrialLog.append_trial wired via run_research_wfa (NOT direct — S44 T9 retrofit)

Execution semantics (Lazybear Supertrend):
  - The Lazybear trend is RECURSIVE: trend[i] depends on close[i] (active-band
    selection close[i] <= final_ub[i]). A flip whose deciding bar is i is only
    known after close[i], so the fill is the NEXT bar open: close(T) → open(T+1).
    Filling open[i] (the flip bar's own open) would be same-bar look-ahead.
  - Entry: BEAR→BULL flip decided at close[i] → fill at open[i+1] * (1 + SLIPPAGE)
  - Exit: BULL→BEAR flip decided at close[i] → fill at open[i+1] * (1 - SLIPPAGE)
  - A flip on the last bar has no next-bar open (entry skipped; open position
    closed at last bar mark-to-market)
  - Sequential additive PnL (per ADR 0064)

LOCKED params per ADR 0067 — DO NOT modify without new ADR:
  atr_period=10, multiplier=3.0, signal_side_mode="long_only"

Data: BTCUSDT 1H parquet per ADR 0067 (hypothesis #10 pre-registered on 1H).

n_trials=10 NOTE (T2 finding):
  The DSR multi-testing penalty only activates when data/cross_trial_sharpes.json
  holds >= 3 OOS Sharpe entries. With fewer entries run_research_wfa honestly falls
  back to compute_dsr_with_status(n_trials=1). This is EXPECTED, not a bug. Do NOT
  fabricate sigma_sr to force the penalty.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from math import isnan, sqrt
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.backtest.research_wfa import get_wfa_tier_params, run_research_wfa

_log = logging.getLogger(__name__)

_COMMISSION_TAKER = 0.001  # 0.1% taker — mirrors atr_breakout_runner
_SLIPPAGE = 0.0005  # 0.05% adverse

# BTCUSDT 1H: bars_per_year = 365.25 * 24 (mirrors atr_breakout_runner mapping)
_BARS_PER_YEAR_1H: int = int(365.25 * 24)  # 8766

# ADR 0067 LOCKED — DO NOT modify without a new ADR amendment.
SUPERTREND_LOCKED_PARAMS: dict[str, object] = {
    "atr_period": 10,
    "multiplier": 3.0,
    "signal_side_mode": "long_only",
}

# Parquet path per ADR 0067 (BTCUSDT 1H).
_PARQUET_PATH = "data/BTCUSDT_1h.parquet"


@dataclass
class _TradeRecord:
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    pnl_pct: float  # net after commission + slippage, fractional (not ×100)


def _wilder_atr_vectorized(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int
) -> np.ndarray:
    """Wilder ATR — mirrors atr_breakout_runner._atr() (exact port).

    Seed: SMA of first `period` TR values at index period-1.
    Recurrence: atr[i] = (atr[i-1]*(period-1) + tr[i]) / period
    """
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr: np.ndarray = np.maximum.reduce(
        [
            high - low,
            np.abs(high - prev_close),
            np.abs(low - prev_close),
        ]
    )
    atr_out = np.full_like(tr, np.nan, dtype=np.float64)
    n = len(tr)
    if n < period:
        return atr_out
    atr_out[period - 1] = tr[:period].mean()
    for i in range(period, n):
        atr_out[i] = (atr_out[i - 1] * (period - 1) + tr[i]) / period
    return atr_out


def _supertrend_vectorized(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    multiplier: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Lazybear Supertrend bands + trend direction (vectorized).

    Implements the carry/clamp (ratchet) from SupertrendStrategy.on_bar().

    Returns:
        (supertrend_line, trend) where trend[i] = 1 (BULL) / -1 (BEAR) / 0 (warmup).
    """
    n = len(close)
    hl2 = (high + low) / 2.0
    basic_ub = hl2 + multiplier * atr
    basic_lb = hl2 - multiplier * atr

    final_ub = np.full(n, np.nan)
    final_lb = np.full(n, np.nan)
    supertrend = np.full(n, np.nan)
    trend = np.zeros(n, dtype=np.int8)

    # Find first valid ATR bar (seed bar — no signal, no flip)
    seed_idx = -1
    for i in range(n):
        if not np.isnan(atr[i]):
            seed_idx = i
            break
    if seed_idx < 0:
        return supertrend, trend

    # Seed bar: conservative upper band (BEAR — no entry)
    final_ub[seed_idx] = basic_ub[seed_idx]
    final_lb[seed_idx] = basic_lb[seed_idx]
    supertrend[seed_idx] = basic_ub[seed_idx]  # upper band = BEAR seed
    trend[seed_idx] = -1  # BEAR

    for i in range(seed_idx + 1, n):
        if np.isnan(atr[i]):
            continue
        prev_close = close[i - 1]
        prev_final_ub = final_ub[i - 1]
        prev_final_lb = final_lb[i - 1]
        if np.isnan(prev_final_ub) or np.isnan(prev_final_lb):
            continue
        prev_supertrend = supertrend[i - 1]

        # Lazybear clamp / ratchet
        final_ub[i] = (
            basic_ub[i]
            if (basic_ub[i] < prev_final_ub or prev_close > prev_final_ub)
            else prev_final_ub
        )
        final_lb[i] = (
            basic_lb[i]
            if (basic_lb[i] > prev_final_lb or prev_close < prev_final_lb)
            else prev_final_lb
        )

        # Supertrend line selection
        if prev_supertrend == prev_final_ub:
            supertrend[i] = final_ub[i] if close[i] <= final_ub[i] else final_lb[i]
        else:
            supertrend[i] = final_lb[i] if close[i] >= final_lb[i] else final_ub[i]

        trend[i] = 1 if supertrend[i] == final_lb[i] else -1

    return supertrend, trend


def _backtest_single(
    df: pd.DataFrame, params: dict[str, Any], bars_per_year: int
) -> dict[str, Any]:
    """Vectorized Supertrend backtest for a single contiguous DataFrame slice.

    BacktestFn-compatible signature: (df, params, bars_per_year) -> dict.

    Entry: BEAR->BULL flip decided at close[i] → fill at open[i+1] * (1 + SLIPPAGE)
    Exit:  BULL->BEAR flip decided at close[i] → fill at open[i+1] * (1 - SLIPPAGE)
    The Lazybear trend is recursive (trend[i] uses close[i]), so the flip is only
    known after close[i]; the earliest executable price is the next bar open
    (close(T) -> open(T+1)). Filling open[i] would be same-bar look-ahead.
    ATR stop: not implemented (Supertrend relies on trend-flip exit only, consistent
    with ADR 0067 exit = flip + downstream FSM ATR bracket SL; research path uses
    flip-only for OOS PnL estimation).
    Mark-to-market: open position closed on last bar.

    Returns dict with n_trades, sharpe, total_pnl_pct, win_rate, trades.
    """
    atr_period = int(params.get("atr_period", int(SUPERTREND_LOCKED_PARAMS["atr_period"])))  # type: ignore[arg-type,call-overload]
    multiplier = float(params.get("multiplier", float(SUPERTREND_LOCKED_PARAMS["multiplier"])))  # type: ignore[arg-type]

    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    open_ = df["open"].to_numpy(dtype=np.float64)
    n = len(df)

    atr_arr = _wilder_atr_vectorized(high, low, close, atr_period)
    _, trend = _supertrend_vectorized(high, low, close, atr_arr, multiplier)

    trades: list[_TradeRecord] = []
    in_pos = False
    entry_idx = -1
    entry_price = 0.0

    # Fill mapping (S50 PHASE 6 BLOCKER): the Lazybear trend is RECURSIVE — trend[i]
    # depends on close[i] (active-band selection close[i] <= final_ub[i]). A flip
    # whose deciding bar is i is therefore only KNOWN at close[i], so the earliest
    # executable price is the NEXT bar open, open[i+1] (close(T) -> open(T+1)). This
    # matches the streaming SupertrendStrategy contract (signal on closed bar T, FSM
    # fills T+1). Filling open[i] would be same-bar look-ahead. A flip on the last bar
    # (i == n-1) has no next-bar open: an entry is skipped; an open position is closed
    # at the last-bar mark-to-market below.
    for i in range(1, n):
        prev_trend = trend[i - 1]
        curr_trend = trend[i]
        if prev_trend == 0 or curr_trend == 0:
            continue

        if not in_pos:
            # Entry: BEAR(-1) -> BULL(+1) flip decided at close[i] -> fill at open[i+1].
            if prev_trend == -1 and curr_trend == 1 and i + 1 < n:
                entry_price = open_[i + 1] * (1.0 + _SLIPPAGE)
                entry_idx = i + 1
                in_pos = True
        else:
            # Exit: BULL(+1) -> BEAR(-1) flip decided at close[i] -> fill at open[i+1].
            if prev_trend == 1 and curr_trend == -1 and i + 1 < n:
                exit_price = open_[i + 1] * (1.0 - _SLIPPAGE)
                pnl_gross = (exit_price - entry_price) / entry_price
                pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER
                trades.append(_TradeRecord(entry_idx, i + 1, entry_price, exit_price, pnl_net))
                in_pos = False

    # Close open position on last bar mark-to-market
    if in_pos:
        exit_price = close[-1] * (1.0 - _SLIPPAGE)
        pnl_gross = (exit_price - entry_price) / entry_price
        pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER
        trades.append(_TradeRecord(entry_idx, n - 1, entry_price, exit_price, pnl_net))

    n_trades = len(trades)
    if n_trades == 0:
        return {
            "n_trades": 0,
            "sharpe": float("nan"),
            "total_pnl_pct": 0.0,
            "win_rate": float("nan"),
            "trades": [],
        }

    pnls = np.array([t.pnl_pct for t in trades])
    mean_holding = float(np.mean([t.exit_idx - t.entry_idx for t in trades]))
    pnl_std = float(pnls.std(ddof=1))

    if pnl_std > 0 and mean_holding > 0:
        trades_per_year = bars_per_year / mean_holding
        sharpe = float((pnls.mean() / pnl_std) * sqrt(trades_per_year))
    else:
        sharpe = float("nan") if pnl_std == 0 else 0.0

    return {
        "n_trades": n_trades,
        "sharpe": sharpe,
        "total_pnl_pct": float(pnls.sum() * 100.0),
        "win_rate": float((pnls > 0).mean()),
        "trades": trades,
    }


def _load_ohlcv_df(
    parquet_path: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Load and normalize OHLCV DataFrame from parquet, filtered to [start_date, end_date].

    Handles 'ts' (Binance) and 'time' (Bybit) column schemas — mirrors
    atr_breakout_runner._load_parquet_df normalization.

    Raises:
        FileNotFoundError: if parquet file does not exist.
        ValueError: if data is empty for given date range.
    """
    raw = pd.read_parquet(parquet_path)

    if "ts" in raw.columns:
        raw["_ts"] = pd.to_datetime(raw["ts"], utc=True)
    elif "time" in raw.columns:
        raw["_ts"] = pd.to_datetime(raw["time"], utc=True)
    else:
        raw = raw.reset_index()
        raw["_ts"] = pd.to_datetime(raw.iloc[:, 0], utc=True)

    raw = raw.sort_values("_ts").reset_index(drop=True)
    mask = raw["_ts"].dt.date >= start_date
    mask &= raw["_ts"].dt.date <= end_date
    df = raw[mask].copy().reset_index(drop=True)
    return df


def run_supertrend_wfa(
    *,
    start_date: date,
    end_date: date,
    train_bars: int | None = None,
    test_bars: int | None = None,
    k_folds: int | None = None,
    embargo_bars: int | None = None,
    params: dict[str, Any] | None = None,
    cross_trial_log_path: Path | None = None,
    sprint_tag: str = "S50",
) -> dict[str, Any]:
    """Run Supertrend WFA for BTCUSDT 1H with n_trials=10 (hypothesis #10).

    Mirrors atr_breakout_runner._run_atr_breakout_wfa pattern exactly:
      1. Resolve tier params via get_wfa_tier_params("60") (1H = high-freq).
      2. Load OHLCV from data/BTCUSDT_1h.parquet.
      3. Call run_research_wfa with n_trials=10 + cross_trial_log_path wired.
         CrossTrialLog.append_trial runs INSIDE run_research_wfa (S44 T9 retrofit).

    Args:
        start_date: inclusive start date.
        end_date: inclusive end date.
        train_bars/test_bars/k_folds/embargo_bars: optional WFA overrides (defaults
            from get_wfa_tier_params("60") = high-freq tier).
        params: explicit strategy params override. If None, uses SUPERTREND_LOCKED_PARAMS.
        cross_trial_log_path: path to cross-trial Sharpe log (defaults to
            data/cross_trial_sharpes.json via run_research_wfa).
        sprint_tag: tag for CrossTrialLog append key (default "S50").

    Returns:
        dict from run_research_wfa: verdict, failed_criteria, fold_sharpe_ratios,
        trial_mean_fold_oos_sharpe, trial_oos_sharpe, mc_p_value, dsr, dsr_pass,
        n_trades_raw, wfa_params, metrics, trades.

    Raises:
        ValueError: if no OHLCV data for given date range.
    """
    tier = get_wfa_tier_params("60")  # 1H = high-freq tier
    resolved_train = train_bars if train_bars is not None else tier["train_bars"]
    resolved_test = test_bars if test_bars is not None else tier["test_bars"]
    resolved_k = k_folds if k_folds is not None else tier["k_folds"]
    resolved_embargo = embargo_bars if embargo_bars is not None else tier["embargo_bars"]

    resolved_params: dict[str, Any] = {
        "atr_period": int(SUPERTREND_LOCKED_PARAMS["atr_period"]),  # type: ignore[call-overload]
        "multiplier": float(SUPERTREND_LOCKED_PARAMS["multiplier"]),  # type: ignore[arg-type]
    }
    if params is not None:
        resolved_params.update(params)

    df = _load_ohlcv_df(_PARQUET_PATH, start_date, end_date)
    if df.empty:
        raise ValueError(f"No OHLCV data for BTCUSDT 1H in [{start_date}, {end_date}]")

    return run_research_wfa(
        df=df,
        params=resolved_params,
        backtest_fn=_backtest_single,
        bars_per_year=_BARS_PER_YEAR_1H,
        symbol="BTCUSDT",
        train_bars=resolved_train,
        test_bars=resolved_test,
        k_folds=resolved_k,
        embargo_bars=resolved_embargo,
        n_trials=10,  # S50 T7 — Supertrend = hypothesis #10 (ADR 0067 CC3 wiring)
        cross_trial_log_path=cross_trial_log_path,
        sprint_tag=sprint_tag,
        strategy_class="supertrend",  # S51 D5 — within-class sigma_SR scoping
    )
