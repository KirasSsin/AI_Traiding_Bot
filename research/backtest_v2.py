"""research backtest_v2 — self-contained vectorized Donchian + EMA200 trend filter + ATR stop.

Adapted из autoresearch paradigm "model architecture fair game" rule.
Pure pandas/numpy. NO dependency on src/backtest/ — keeps research/ folder isolated per
program.md anti-snooping discipline (только prepare.py.load_split shared).

Iter 2 hypothesis (trader-expert prior + iter 1 evidence): EMA200 trend filter rejects
counter-trend Donchian breakouts → reduces whipsaw losses в bear/range periods.

Long-only (per ADR 0054 LOCKED Donchian S35).

Strategy logic per bar i (i >= warmup):
    entry_signal = close[i-1] > rolling_max(high, lookback_n)[i-2]  # breakout prev bar
                   AND (ema_filter_period == 0 OR close[i-1] > ema(close, ema_filter_period)[i-1])
    exit_signal  = close[i-1] < rolling_min(low, exit_lookback_n)[i-2]  # exit channel
                   OR  low[i] <= entry_price - atr[entry_bar] * atr_stop_mult  (intrabar stop)

Execution: market open next bar (close[i-1] signal → fill at open[i]).
Commission: 0.1% taker round trip (entry + exit). Slippage: 0.05% adverse.

Sharpe: per-trade returns, annualized × sqrt(BARS_PER_YEAR / mean_holding_bars).
WFA: K folds на train portion, aggregate Sharpe = mean(fold_sharpes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# Constants mirror prepare.py defaults
BARS_PER_YEAR = 2190  # 4H
COMMISSION_TAKER = 0.001  # 0.1%
SLIPPAGE = 0.0005  # 0.05% adverse
INITIAL_BALANCE = 10000.0
POSITION_SIZE_PCT = 10.0  # 10% per trade


@dataclass
class TradeRecord:
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    pnl_pct: float  # net (after commission + slippage)


def _atr(df: pd.DataFrame, period: int) -> np.ndarray:
    """Wilder ATR. Returns array same length as df, NaN for < period."""
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce(
        [
            high - low,
            np.abs(high - prev_close),
            np.abs(low - prev_close),
        ]
    )
    atr = np.full_like(tr, np.nan)
    if len(tr) < period:
        return atr
    # Wilder smoothing: first ATR = SMA of first `period` TRs, then EMA-like
    atr[period - 1] = tr[:period].mean()
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    """EMA with standard alpha = 2 / (period + 1). Returns same length, NaN for < period."""
    ema = np.full_like(values, np.nan, dtype=np.float64)
    if len(values) < period:
        return ema
    alpha = 2.0 / (period + 1)
    ema[period - 1] = values[:period].mean()
    for i in range(period, len(values)):
        ema[i] = alpha * values[i] + (1 - alpha) * ema[i - 1]
    return ema


def _backtest_single(df: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
    """Single contiguous backtest. Returns trades + metrics."""
    lookback_n = int(params["lookback_n"])
    exit_lookback_n = int(params["exit_lookback_n"])
    atr_period = int(params.get("atr_period", 14))
    atr_stop_mult = float(params["atr_stop_mult"])
    ema_filter_period = int(params.get("ema_filter_period", 0))  # 0 = disabled

    close = df["close"].to_numpy(dtype=np.float64)
    open_ = df["open"].to_numpy(dtype=np.float64)
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    n = len(df)

    # Indicators
    roll_high = pd.Series(high).rolling(lookback_n, min_periods=lookback_n).max().to_numpy()
    roll_low = pd.Series(low).rolling(exit_lookback_n, min_periods=exit_lookback_n).min().to_numpy()
    atr = _atr(df, atr_period)
    ema = _ema(close, ema_filter_period) if ema_filter_period > 0 else None

    warmup = max(lookback_n, exit_lookback_n, atr_period, ema_filter_period) + 1

    trades: list[TradeRecord] = []
    in_pos = False
    entry_idx = -1
    entry_price = 0.0
    entry_atr = 0.0

    for i in range(warmup, n):
        if not in_pos:
            # Entry signal: prev close breakout vs prev rolling high (excluding current bar)
            # Use shift(1) semantics: roll_high[i-2] (window ended at i-2), checked against close[i-1]
            if i < 2:
                continue
            ref_high = roll_high[i - 2]
            if np.isnan(ref_high):
                continue
            breakout = close[i - 1] > ref_high
            trend_ok = True
            if ema is not None:
                trend_ok = (not np.isnan(ema[i - 1])) and close[i - 1] > ema[i - 1]
            if breakout and trend_ok:
                # Fill at open[i] + slippage adverse
                entry_price = open_[i] * (1 + SLIPPAGE)
                entry_idx = i
                entry_atr = atr[i - 1]
                if np.isnan(entry_atr):
                    continue  # skip invalid
                in_pos = True
        else:
            # Exit conditions
            stop_price = entry_price - entry_atr * atr_stop_mult
            ref_low = roll_low[i - 2] if i >= 2 else np.nan
            channel_exit = (not np.isnan(ref_low)) and close[i - 1] < ref_low

            if low[i] <= stop_price:
                # Intrabar stop: fill at stop_price (worst case, no slippage further — already adverse)
                exit_price = stop_price * (1 - SLIPPAGE)
                pnl_gross = (exit_price - entry_price) / entry_price
                pnl_net = pnl_gross - 2 * COMMISSION_TAKER
                trades.append(TradeRecord(entry_idx, i, entry_price, exit_price, pnl_net))
                in_pos = False
            elif channel_exit:
                exit_price = open_[i] * (1 - SLIPPAGE)
                pnl_gross = (exit_price - entry_price) / entry_price
                pnl_net = pnl_gross - 2 * COMMISSION_TAKER
                trades.append(TradeRecord(entry_idx, i, entry_price, exit_price, pnl_net))
                in_pos = False

    # Close open position на last bar (mark to market)
    if in_pos:
        exit_price = close[-1] * (1 - SLIPPAGE)
        pnl_gross = (exit_price - entry_price) / entry_price
        pnl_net = pnl_gross - 2 * COMMISSION_TAKER
        trades.append(TradeRecord(entry_idx, n - 1, entry_price, exit_price, pnl_net))

    # Metrics
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
    mean_holding = np.mean([t.exit_idx - t.entry_idx for t in trades])
    if pnls.std(ddof=1) > 0 and mean_holding > 0:
        # Annualize: scale per-trade returns к annual basis
        trades_per_year = BARS_PER_YEAR / mean_holding
        sharpe = (pnls.mean() / pnls.std(ddof=1)) * np.sqrt(trades_per_year)
    else:
        sharpe = float("nan") if pnls.std(ddof=1) == 0 else 0.0

    return {
        "n_trades": n_trades,
        "sharpe": float(sharpe),
        "total_pnl_pct": float(pnls.sum() * 100.0),
        "win_rate": float((pnls > 0).mean()),
        "trades": trades,
    }


def evaluate_wfa(
    df: pd.DataFrame,
    params: dict[str, Any],
    *,
    train_bars: int = 2000,
    test_bars: int = 500,
    k_folds: int = 5,
    embargo_bars: int = 20,
) -> dict[str, Any]:
    """Walk-Forward Analysis на train portion. Returns aggregate metrics."""
    min_required = train_bars + embargo_bars + k_folds * test_bars
    if len(df) < min_required:
        return {
            "metric": float("nan"),
            "n_trades": 0,
            "fold_sharpes": [],
            "fold_pnls": [],
            "win_rate": float("nan"),
            "status": "insufficient_data",
        }

    fold_sharpes: list[float] = []
    fold_pnls: list[float] = []
    n_trades_total = 0
    pnl_total: list[float] = []

    for k in range(k_folds):
        # Sliding window: train [k*test_bars : k*test_bars + train_bars], test follows
        train_start = k * test_bars
        train_end = train_start + train_bars
        test_start = train_end + embargo_bars
        test_end = test_start + test_bars
        if test_end > len(df):
            break
        # WFA: in pure form мы tune on train, eval on test. Здесь params фиксированные (search loop tunes globally),
        # так что просто eval на test fold.
        test_df = df.iloc[test_start:test_end].reset_index(drop=True)
        result = _backtest_single(test_df, params)
        if result["n_trades"] > 0 and not np.isnan(result["sharpe"]):
            fold_sharpes.append(result["sharpe"])
            fold_pnls.append(result["total_pnl_pct"])
            pnl_total.extend([t.pnl_pct for t in result["trades"]])
            n_trades_total += result["n_trades"]
        else:
            fold_sharpes.append(0.0)
            fold_pnls.append(0.0)

    agg_sharpe = float(np.mean(fold_sharpes)) if fold_sharpes else float("nan")
    win_rate = float(np.mean([p > 0 for p in pnl_total])) if pnl_total else float("nan")
    return {
        "metric": agg_sharpe,
        "n_trades": n_trades_total,
        "fold_sharpes": [round(s, 4) for s in fold_sharpes],
        "fold_pnls": [round(p, 2) for p in fold_pnls],
        "win_rate": win_rate,
        "total_pnl_pct": float(sum(fold_pnls)),
        "status": "ok",
    }


def evaluate_heldout(df: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
    """Single contiguous backtest на held-out portion."""
    result = _backtest_single(df, params)
    return {
        "metric": result["sharpe"],
        "n_trades": result["n_trades"],
        "total_pnl_pct": result["total_pnl_pct"],
        "win_rate": result["win_rate"],
        "fold_sharpes": [],
        "status": "heldout_single",
    }
