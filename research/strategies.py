"""research strategies registry — multi-paradigm backtest для iter 3+ autoresearch.

Operator directive: 100 iterations across DIFFERENT strategy paradigms (per
trader-expert ROUND 1 verdict — Donchian paradigm closed, expand search space).

Each strategy = function `(df, params) -> list[TradeRecord]`. Common shell handles
WFA + held-out + Sharpe metric.

Long-only — research toy bypasses formal long_only invariant constraints
(ADR 0009 applies к main src only).

Strategy registry:
    1. donchian_raw — Donchian channel breakout (iter 1 baseline reference)
    2. rsi_mean_reversion — RSI<thr entry, RSI>50 exit
    3. bollinger_breakout — close > BB_upper
    4. bollinger_mean_reversion — close < BB_lower then bounce
    5. macd_momentum — MACD line cross + hist positive
    6. atr_squeeze_breakout — ATR percentile low → breakout entry
    7. momentum_n_consecutive — N consecutive green bars → enter
    8. volume_breakout — Donchian + volume > rolling mean
    9. ema_crossover — fast EMA crosses slow EMA (S13 baseline reference)
    10. price_channel — close > rolling_max(N) AND ATR > threshold

Common exit logic (all strategies): ATR stop OR strategy-specific exit.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from research.prepare import BARS_PER_YEAR  # noqa: E402  — derive from prepare.py

COMMISSION_TAKER = 0.001
SLIPPAGE = 0.0005


@dataclass
class TradeRecord:
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    pnl_pct: float


# ---------- Indicators ----------


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([high - low, np.abs(high - prev_close), np.abs(low - prev_close)])
    atr = np.full_like(tr, np.nan)
    if len(tr) < period:
        return atr
    atr[period - 1] = tr[:period].mean()
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def _ema(x: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=np.float64)
    if len(x) < period:
        return out
    alpha = 2.0 / (period + 1)
    out[period - 1] = x[:period].mean()
    for i in range(period, len(x)):
        out[i] = alpha * x[i] + (1 - alpha) * out[i - 1]
    return out


def _rsi(close: np.ndarray, period: int) -> np.ndarray:
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.full_like(close, np.nan, dtype=np.float64)
    avg_loss = np.full_like(close, np.nan, dtype=np.float64)
    if len(close) < period + 1:
        return avg_gain
    avg_gain[period] = gain[1 : period + 1].mean()
    avg_loss[period] = loss[1 : period + 1].mean()
    for i in range(period + 1, len(close)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i]) / period
    rs = avg_gain / np.where(avg_loss == 0, 1e-10, avg_loss)
    return 100.0 - 100.0 / (1.0 + rs)


# ---------- Common backtest shell ----------


def _execute_with_atr_stop(
    df: pd.DataFrame,
    entry_signals: np.ndarray,  # boolean array, True at bar where signal fires (use close[i-1])
    exit_signals: np.ndarray,  # boolean array, True at bar where exit fires
    atr_arr: np.ndarray,
    atr_stop_mult: float,
    warmup: int,
) -> list[TradeRecord]:
    """Generic execution: long entry на open[i] + slippage; exit on signal OR ATR stop.

    entry_signals[i] = True означает signal fired AT close[i-1] (or some prior bar),
    fill at open[i].
    exit_signals[i] same convention.
    """
    open_ = df["open"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    n = len(df)

    trades: list[TradeRecord] = []
    in_pos = False
    entry_idx = -1
    entry_price = 0.0
    entry_atr = 0.0

    for i in range(warmup, n):
        if not in_pos:
            if entry_signals[i]:
                if np.isnan(atr_arr[i - 1]):
                    continue
                entry_price = open_[i] * (1 + SLIPPAGE)
                entry_idx = i
                entry_atr = atr_arr[i - 1]
                in_pos = True
        else:
            stop_price = entry_price - entry_atr * atr_stop_mult
            if low[i] <= stop_price:
                exit_price = stop_price * (1 - SLIPPAGE)
                pnl = (exit_price - entry_price) / entry_price - 2 * COMMISSION_TAKER
                trades.append(TradeRecord(entry_idx, i, entry_price, exit_price, pnl))
                in_pos = False
            elif exit_signals[i]:
                exit_price = open_[i] * (1 - SLIPPAGE)
                pnl = (exit_price - entry_price) / entry_price - 2 * COMMISSION_TAKER
                trades.append(TradeRecord(entry_idx, i, entry_price, exit_price, pnl))
                in_pos = False

    if in_pos:
        exit_price = close[-1] * (1 - SLIPPAGE)
        pnl = (exit_price - entry_price) / entry_price - 2 * COMMISSION_TAKER
        trades.append(TradeRecord(entry_idx, n - 1, entry_price, exit_price, pnl))

    return trades


# ---------- Strategy implementations ----------


def strat_donchian_raw(df: pd.DataFrame, params: dict[str, Any]) -> list[TradeRecord]:
    lb = int(params.get("lookback_n", 20))
    ex_lb = int(params.get("exit_lookback_n", 10))
    ap = int(params.get("atr_period", 14))
    am = float(params.get("atr_stop_mult", 2.0))
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    n = len(df)
    roll_high = pd.Series(high).rolling(lb, min_periods=lb).max().to_numpy()
    roll_low = pd.Series(low).rolling(ex_lb, min_periods=ex_lb).min().to_numpy()
    atr = _atr(high, low, close, ap)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(2, n):
        ref_h = roll_high[i - 2]
        ref_l = roll_low[i - 2]
        if not np.isnan(ref_h) and close[i - 1] > ref_h:
            entry[i] = True
        if not np.isnan(ref_l) and close[i - 1] < ref_l:
            exit_[i] = True
    warmup = max(lb, ex_lb, ap) + 1
    return _execute_with_atr_stop(df, entry, exit_, atr, am, warmup)


def strat_rsi_mean_reversion(df: pd.DataFrame, params: dict[str, Any]) -> list[TradeRecord]:
    rsi_p = int(params.get("rsi_period", 14))
    rsi_low = float(params.get("rsi_low", 30.0))
    rsi_high = float(params.get("rsi_high", 50.0))
    ap = int(params.get("atr_period", 14))
    am = float(params.get("atr_stop_mult", 2.0))
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    n = len(df)
    rsi = _rsi(close, rsi_p)
    atr = _atr(high, low, close, ap)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(2, n):
        if not np.isnan(rsi[i - 1]):
            if rsi[i - 1] < rsi_low:
                entry[i] = True
            if rsi[i - 1] > rsi_high:
                exit_[i] = True
    warmup = max(rsi_p, ap) + 2
    return _execute_with_atr_stop(df, entry, exit_, atr, am, warmup)


def strat_bollinger_breakout(df: pd.DataFrame, params: dict[str, Any]) -> list[TradeRecord]:
    bb_p = int(params.get("bb_period", 20))
    bb_k = float(params.get("bb_k", 2.0))
    ap = int(params.get("atr_period", 14))
    am = float(params.get("atr_stop_mult", 2.0))
    close = df["close"].to_numpy(dtype=np.float64)
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    n = len(df)
    sma = pd.Series(close).rolling(bb_p, min_periods=bb_p).mean().to_numpy()
    std = pd.Series(close).rolling(bb_p, min_periods=bb_p).std(ddof=0).to_numpy()
    upper = sma + bb_k * std
    lower = sma - bb_k * std
    atr = _atr(high, low, close, ap)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(2, n):
        if not np.isnan(upper[i - 1]) and close[i - 1] > upper[i - 1]:
            entry[i] = True
        if not np.isnan(lower[i - 1]) and close[i - 1] < lower[i - 1]:
            exit_[i] = True
    warmup = max(bb_p, ap) + 2
    return _execute_with_atr_stop(df, entry, exit_, atr, am, warmup)


def strat_bollinger_mr(df: pd.DataFrame, params: dict[str, Any]) -> list[TradeRecord]:
    """Mean-reversion: close < lower then bounce → enter; close > sma → exit."""
    bb_p = int(params.get("bb_period", 20))
    bb_k = float(params.get("bb_k", 2.0))
    ap = int(params.get("atr_period", 14))
    am = float(params.get("atr_stop_mult", 2.0))
    close = df["close"].to_numpy(dtype=np.float64)
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    n = len(df)
    sma = pd.Series(close).rolling(bb_p, min_periods=bb_p).mean().to_numpy()
    std = pd.Series(close).rolling(bb_p, min_periods=bb_p).std(ddof=0).to_numpy()
    lower = sma - bb_k * std
    atr = _atr(high, low, close, ap)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(3, n):
        # Bounce: close[i-2] < lower AND close[i-1] > close[i-2] (bullish bounce)
        if (
            not np.isnan(lower[i - 2])
            and close[i - 2] < lower[i - 2]
            and close[i - 1] > close[i - 2]
        ):
            entry[i] = True
        if not np.isnan(sma[i - 1]) and close[i - 1] > sma[i - 1]:
            exit_[i] = True
    warmup = max(bb_p, ap) + 3
    return _execute_with_atr_stop(df, entry, exit_, atr, am, warmup)


def strat_macd_momentum(df: pd.DataFrame, params: dict[str, Any]) -> list[TradeRecord]:
    fast = int(params.get("macd_fast", 12))
    slow = int(params.get("macd_slow", 26))
    sig = int(params.get("macd_signal", 9))
    ap = int(params.get("atr_period", 14))
    am = float(params.get("atr_stop_mult", 2.0))
    close = df["close"].to_numpy(dtype=np.float64)
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    n = len(df)
    ema_f = _ema(close, fast)
    ema_s = _ema(close, slow)
    macd_line = ema_f - ema_s
    signal_line = _ema(macd_line, sig)
    hist = macd_line - signal_line
    atr = _atr(high, low, close, ap)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(2, n):
        if not (np.isnan(macd_line[i - 1]) or np.isnan(signal_line[i - 1])):
            # Bull cross: macd crosses above signal AND hist positive
            if (
                macd_line[i - 2] <= signal_line[i - 2]
                and macd_line[i - 1] > signal_line[i - 1]
                and hist[i - 1] > 0
            ):
                entry[i] = True
            # Bear cross: macd crosses below signal
            if macd_line[i - 2] >= signal_line[i - 2] and macd_line[i - 1] < signal_line[i - 1]:
                exit_[i] = True
    warmup = slow + sig + 2
    return _execute_with_atr_stop(df, entry, exit_, atr, am, warmup)


def strat_atr_squeeze_breakout(df: pd.DataFrame, params: dict[str, Any]) -> list[TradeRecord]:
    """ATR percentile low (squeeze) → enter on Donchian breakout."""
    lb = int(params.get("lookback_n", 20))
    squeeze_window = int(params.get("squeeze_window", 100))
    squeeze_pct = float(params.get("squeeze_pct", 30.0))
    ap = int(params.get("atr_period", 14))
    am = float(params.get("atr_stop_mult", 2.0))
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    n = len(df)
    roll_high = pd.Series(high).rolling(lb, min_periods=lb).max().to_numpy()
    atr = _atr(high, low, close, ap)
    atr_pct = (
        pd.Series(atr)
        .rolling(squeeze_window, min_periods=20)
        .quantile(squeeze_pct / 100.0)
        .to_numpy()
    )
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(2, n):
        ref_h = roll_high[i - 2]
        # Squeeze: ATR below percentile threshold → ready to expand
        if (
            not np.isnan(ref_h)
            and not np.isnan(atr_pct[i - 1])
            and atr[i - 1] < atr_pct[i - 1]
            and close[i - 1] > ref_h
        ):
            entry[i] = True
        # Exit: ATR expanded sharply (regime change OR profit-taking)
        if not np.isnan(atr_pct[i - 1]) and atr[i - 1] > 2 * atr_pct[i - 1]:
            exit_[i] = True
    warmup = max(lb, ap, squeeze_window) + 2
    return _execute_with_atr_stop(df, entry, exit_, atr, am, warmup)


def strat_momentum_n_consec(df: pd.DataFrame, params: dict[str, Any]) -> list[TradeRecord]:
    """N consecutive green bars (close > open) → enter."""
    n_consec = int(params.get("n_consec", 3))
    ap = int(params.get("atr_period", 14))
    am = float(params.get("atr_stop_mult", 2.0))
    exit_reverse = int(params.get("exit_n_reverse", 2))
    open_ = df["open"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    n = len(df)
    green = (close > open_).astype(np.int32)
    atr = _atr(high, low, close, ap)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(n_consec + 1, n):
        if green[i - n_consec : i].sum() == n_consec:
            entry[i] = True
        # Exit on N consecutive red bars
        if i >= exit_reverse + 1 and green[i - exit_reverse : i].sum() == 0:
            exit_[i] = True
    warmup = max(n_consec, ap) + 2
    return _execute_with_atr_stop(df, entry, exit_, atr, am, warmup)


def strat_volume_breakout(df: pd.DataFrame, params: dict[str, Any]) -> list[TradeRecord]:
    """Donchian breakout + volume > rolling mean × multiplier."""
    lb = int(params.get("lookback_n", 20))
    ex_lb = int(params.get("exit_lookback_n", 10))
    vol_window = int(params.get("vol_window", 20))
    vol_mult = float(params.get("vol_mult", 1.5))
    ap = int(params.get("atr_period", 14))
    am = float(params.get("atr_stop_mult", 2.0))
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    if "volume" not in df.columns:
        return []
    volume = df["volume"].to_numpy(dtype=np.float64)
    n = len(df)
    roll_high = pd.Series(high).rolling(lb, min_periods=lb).max().to_numpy()
    roll_low = pd.Series(low).rolling(ex_lb, min_periods=ex_lb).min().to_numpy()
    vol_mean = pd.Series(volume).rolling(vol_window, min_periods=vol_window).mean().to_numpy()
    atr = _atr(high, low, close, ap)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(2, n):
        ref_h = roll_high[i - 2]
        ref_l = roll_low[i - 2]
        if (
            not np.isnan(ref_h)
            and not np.isnan(vol_mean[i - 1])
            and close[i - 1] > ref_h
            and volume[i - 1] > vol_mean[i - 1] * vol_mult
        ):
            entry[i] = True
        if not np.isnan(ref_l) and close[i - 1] < ref_l:
            exit_[i] = True
    warmup = max(lb, ex_lb, ap, vol_window) + 2
    return _execute_with_atr_stop(df, entry, exit_, atr, am, warmup)


def strat_ema_crossover(df: pd.DataFrame, params: dict[str, Any]) -> list[TradeRecord]:
    fast = int(params.get("ema_fast", 12))
    slow = int(params.get("ema_slow", 26))
    ap = int(params.get("atr_period", 14))
    am = float(params.get("atr_stop_mult", 2.0))
    close = df["close"].to_numpy(dtype=np.float64)
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    n = len(df)
    ema_f = _ema(close, fast)
    ema_s = _ema(close, slow)
    atr = _atr(high, low, close, ap)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(2, n):
        if not (
            np.isnan(ema_f[i - 1])
            or np.isnan(ema_s[i - 1])
            or np.isnan(ema_f[i - 2])
            or np.isnan(ema_s[i - 2])
        ):
            if ema_f[i - 2] <= ema_s[i - 2] and ema_f[i - 1] > ema_s[i - 1]:
                entry[i] = True
            if ema_f[i - 2] >= ema_s[i - 2] and ema_f[i - 1] < ema_s[i - 1]:
                exit_[i] = True
    warmup = slow + 2
    return _execute_with_atr_stop(df, entry, exit_, atr, am, warmup)


def strat_price_channel_with_atr(df: pd.DataFrame, params: dict[str, Any]) -> list[TradeRecord]:
    """Donchian + ATR/price ratio threshold (only enter when volatility favorable)."""
    lb = int(params.get("lookback_n", 20))
    ex_lb = int(params.get("exit_lookback_n", 10))
    atr_pct_min = float(params.get("atr_pct_min", 0.005))  # ATR/price >= 0.5%
    atr_pct_max = float(params.get("atr_pct_max", 0.05))  # <= 5%
    ap = int(params.get("atr_period", 14))
    am = float(params.get("atr_stop_mult", 2.0))
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    n = len(df)
    roll_high = pd.Series(high).rolling(lb, min_periods=lb).max().to_numpy()
    roll_low = pd.Series(low).rolling(ex_lb, min_periods=ex_lb).min().to_numpy()
    atr = _atr(high, low, close, ap)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(2, n):
        ref_h = roll_high[i - 2]
        ref_l = roll_low[i - 2]
        if not np.isnan(ref_h) and not np.isnan(atr[i - 1]):
            atr_pct = atr[i - 1] / close[i - 1]
            if close[i - 1] > ref_h and atr_pct_min <= atr_pct <= atr_pct_max:
                entry[i] = True
        if not np.isnan(ref_l) and close[i - 1] < ref_l:
            exit_[i] = True
    warmup = max(lb, ex_lb, ap) + 2
    return _execute_with_atr_stop(df, entry, exit_, atr, am, warmup)


# ---------- Strategy registry ----------

STRATEGY_REGISTRY: dict[str, Callable[[pd.DataFrame, dict[str, Any]], list[TradeRecord]]] = {
    "donchian_raw": strat_donchian_raw,
    "rsi_mean_reversion": strat_rsi_mean_reversion,
    "bollinger_breakout": strat_bollinger_breakout,
    "bollinger_mr": strat_bollinger_mr,
    "macd_momentum": strat_macd_momentum,
    "atr_squeeze_breakout": strat_atr_squeeze_breakout,
    "momentum_n_consec": strat_momentum_n_consec,
    "volume_breakout": strat_volume_breakout,
    "ema_crossover": strat_ema_crossover,
    "price_channel_with_atr": strat_price_channel_with_atr,
}


# ---------- WFA + held-out shells ----------


def _metrics_from_trades(trades: list[TradeRecord], n_bars: int | None = None) -> dict[str, Any]:
    """Bar-based Sharpe annualization (cross-timeframe consistent).

    Old formula (trade-frequency based) blew up на 5M (sqrt(21000)=145× scale).
    New formula: per-bar return series, annualize sqrt(BARS_PER_YEAR).
    """
    n = len(trades)
    if n == 0:
        return {
            "n_trades": 0,
            "sharpe": float("nan"),
            "total_pnl_pct": 0.0,
            "win_rate": float("nan"),
        }
    pnls = np.array([t.pnl_pct for t in trades])
    total_pnl_pct = float(pnls.sum() * 100.0)
    win_rate = float((pnls > 0).mean())

    if n_bars is None:
        n_bars = max(t.exit_idx for t in trades) + 1
    per_bar = np.zeros(n_bars, dtype=np.float64)
    for t in trades:
        hold = t.exit_idx - t.entry_idx
        if hold > 0:
            per_bar[t.entry_idx : t.exit_idx] = t.pnl_pct / hold

    if per_bar.std(ddof=1) > 0:
        sharpe = (per_bar.mean() / per_bar.std(ddof=1)) * np.sqrt(BARS_PER_YEAR)
    else:
        sharpe = 0.0
    return {
        "n_trades": n,
        "sharpe": float(sharpe),
        "total_pnl_pct": total_pnl_pct,
        "win_rate": win_rate,
    }


def evaluate_wfa(
    df: pd.DataFrame,
    strategy_name: str,
    params: dict[str, Any],
    *,
    train_bars: int = 2000,
    test_bars: int = 500,
    k_folds: int = 5,
    embargo_bars: int = 20,
) -> dict[str, Any]:
    if strategy_name not in STRATEGY_REGISTRY:
        return {
            "metric": float("nan"),
            "n_trades": 0,
            "fold_sharpes": [],
            "status": "unknown_strategy",
        }
    fn = STRATEGY_REGISTRY[strategy_name]
    min_required = train_bars + embargo_bars + k_folds * test_bars
    if len(df) < min_required:
        return {
            "metric": float("nan"),
            "n_trades": 0,
            "fold_sharpes": [],
            "status": "insufficient_data",
        }
    fold_sharpes: list[float] = []
    fold_pnls: list[float] = []
    pnl_total: list[float] = []
    n_total = 0
    for k in range(k_folds):
        train_start = k * test_bars
        test_start = train_start + train_bars + embargo_bars
        test_end = test_start + test_bars
        if test_end > len(df):
            break
        test_df = df.iloc[test_start:test_end].reset_index(drop=True)
        trades = fn(test_df, params)
        m = _metrics_from_trades(trades, n_bars=len(test_df))
        if m["n_trades"] > 0 and not np.isnan(m["sharpe"]):
            fold_sharpes.append(m["sharpe"])
            fold_pnls.append(m["total_pnl_pct"])
            pnl_total.extend([t.pnl_pct for t in trades])
            n_total += m["n_trades"]
        else:
            fold_sharpes.append(0.0)
            fold_pnls.append(0.0)
    agg = float(np.mean(fold_sharpes)) if fold_sharpes else float("nan")
    win = float(np.mean([p > 0 for p in pnl_total])) if pnl_total else float("nan")
    return {
        "metric": agg,
        "n_trades": n_total,
        "fold_sharpes": [round(s, 3) for s in fold_sharpes],
        "fold_pnls": [round(p, 2) for p in fold_pnls],
        "win_rate": win,
        "total_pnl_pct": float(sum(fold_pnls)),
        "status": "ok",
    }


def evaluate_heldout(
    df: pd.DataFrame, strategy_name: str, params: dict[str, Any]
) -> dict[str, Any]:
    if strategy_name not in STRATEGY_REGISTRY:
        return {"metric": float("nan"), "n_trades": 0, "status": "unknown_strategy"}
    trades = STRATEGY_REGISTRY[strategy_name](df, params)
    m = _metrics_from_trades(trades, n_bars=len(df))
    return {
        "metric": m["sharpe"],
        "n_trades": m["n_trades"],
        "total_pnl_pct": m["total_pnl_pct"],
        "win_rate": m["win_rate"],
        "fold_sharpes": [],
        "status": "heldout_single",
    }
