"""ENDLESS autoresearch loop — multi-symbol × timeframe × strategy.

Self-contained (NO external script deps). Mission: maximize PnL coverage across
ALL combinations. Run forever. User instruction overnight: don't stop.

Per combo: sweep all 5 strategy templates × parameter grid.
Filter: PASS = positive full PnL + Sharpe > 0.5 + ≥4/5 sub-period robust + n_trades ≥ 20.
Save: per-combo PASS results к results.jsonl + best to best_per_combo.json.

Outputs:
- data/autoresearch_endless/results.jsonl  — append-only PASS log
- data/autoresearch_endless/best_per_combo.json
- data/autoresearch_endless/iteration_log.jsonl
"""

from __future__ import annotations

import json
import time
import traceback
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

# ─── Output paths ───
OUT_DIR = Path("data/autoresearch_endless")
OUT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_JSONL = OUT_DIR / "results.jsonl"
BEST_JSON = OUT_DIR / "best_per_combo.json"
ITER_LOG = OUT_DIR / "iteration_log.jsonl"

# ─── Constants ───
COMMISSION_TAKER = 0.001
SLIPPAGE = 0.0005

# CC4 S50 (ADR 0067 Q4): held-out date range LOCKED for anti-champion-bias.
# Parameter sweep reads TRAIN only (ts < HELDOUT_START). Held-out evaluation runs
# ONCE on the per-combo winner via eval_heldout_once() — never inside the sweep loop.
HELDOUT_START = "2025-06-01"
HELDOUT_END = "2026-05-01"

BARS_PER_YEAR_BY_INTERVAL: dict[str, int] = {
    "5": int(365.25 * 24 * 12),
    "15": int(365.25 * 24 * 4),
    "60": int(365.25 * 24),
    "240": int(365.25 * 6),
    "D": int(365.25),
}

COMBOS = [
    ("BTCUSDT", "240", "data/BTCUSDT_4h_binance.parquet"),
    ("BTCUSDT", "60", "data/BTCUSDT_1h.parquet"),
    ("BTCUSDT", "15", "data/BTCUSDT_15m.parquet"),
    ("BTCUSDT", "D", "data/BTCUSDT_1d.parquet"),
    ("ETHUSDT", "240", "data/ETHUSDT_4h.parquet"),
    ("ETHUSDT", "60", "data/ETHUSDT_1h.parquet"),
    ("ETHUSDT", "15", "data/ETHUSDT_15m.parquet"),
    ("SOLUSDT", "240", "data/SOLUSDT_4h.parquet"),
    ("SOLUSDT", "60", "data/SOLUSDT_1h.parquet"),
    ("SOLUSDT", "15", "data/SOLUSDT_15m.parquet"),
    ("BTCUSDT", "5", "data/BTCUSDT_5m.parquet"),
]


# ─── Indicators ───
def _atr(df: pd.DataFrame, period: int) -> np.ndarray:
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([high - low, np.abs(high - prev_close), np.abs(low - prev_close)])
    atr = np.full_like(tr, np.nan)
    if len(tr) < period:
        return atr
    atr[period - 1] = tr[:period].mean()
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    ema = np.full_like(values, np.nan, dtype=np.float64)
    if len(values) < period:
        return ema
    alpha = 2.0 / (period + 1)
    ema[period - 1] = values[:period].mean()
    for i in range(period, len(values)):
        ema[i] = alpha * values[i] + (1 - alpha) * ema[i - 1]
    return ema


def _rsi(values: np.ndarray, period: int) -> np.ndarray:
    rsi = np.full_like(values, np.nan, dtype=np.float64)
    if len(values) <= period:
        return rsi
    deltas = np.diff(values)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()
    rsi[period] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period + 1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        rsi[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return rsi


def _adx(df: pd.DataFrame, period: int) -> np.ndarray:
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    n = len(df)
    adx = np.full(n, np.nan, dtype=np.float64)
    if n < 2 * period:
        return adx
    up_move = np.diff(high)
    down_move = -np.diff(low)
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([high - low, np.abs(high - prev_close), np.abs(low - prev_close)])
    atr_s = np.full(n, np.nan)
    plus_di = np.full(n, np.nan)
    minus_di = np.full(n, np.nan)
    atr_s[period] = tr[1 : period + 1].sum()
    plus_dm_s = plus_dm[:period].sum()
    minus_dm_s = minus_dm[:period].sum()
    plus_di[period] = 100.0 * plus_dm_s / atr_s[period] if atr_s[period] > 0 else 0
    minus_di[period] = 100.0 * minus_dm_s / atr_s[period] if atr_s[period] > 0 else 0
    for i in range(period + 1, n):
        atr_s[i] = atr_s[i - 1] - atr_s[i - 1] / period + tr[i]
        plus_dm_s = plus_dm_s - plus_dm_s / period + plus_dm[i - 1]
        minus_dm_s = minus_dm_s - minus_dm_s / period + minus_dm[i - 1]
        plus_di[i] = 100.0 * plus_dm_s / atr_s[i] if atr_s[i] > 0 else 0
        minus_di[i] = 100.0 * minus_dm_s / atr_s[i] if atr_s[i] > 0 else 0
    dx = 100.0 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-12)
    adx[2 * period] = np.nanmean(dx[period + 1 : 2 * period + 1])
    for i in range(2 * period + 1, n):
        adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period
    return adx


# ─── Generic backtest engine ───
def _backtest(
    df: pd.DataFrame,
    entry: np.ndarray,
    exit_: np.ndarray,
    atr: np.ndarray,
    atr_stop_mult: float,
    warmup: int,
    bars_per_year: int,
) -> dict:
    open_ = df["open"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    n = len(df)
    trades = []
    in_pos = False
    entry_idx = -1
    entry_price = 0.0
    entry_atr = 0.0
    for i in range(warmup, n):
        if not in_pos:
            if entry[i]:
                a = atr[i - 1] if i >= 1 else np.nan
                if np.isnan(a):
                    continue
                entry_price = open_[i] * (1 + SLIPPAGE)
                entry_idx = i
                entry_atr = a
                in_pos = True
        else:
            stop_price = entry_price - entry_atr * atr_stop_mult
            if low[i] <= stop_price:
                exit_price = stop_price * (1 - SLIPPAGE)
                pnl_net = (exit_price - entry_price) / entry_price - 2 * COMMISSION_TAKER
                trades.append((entry_idx, i, pnl_net))
                in_pos = False
            elif exit_[i]:
                exit_price = open_[i] * (1 - SLIPPAGE)
                pnl_net = (exit_price - entry_price) / entry_price - 2 * COMMISSION_TAKER
                trades.append((entry_idx, i, pnl_net))
                in_pos = False
    if in_pos:
        exit_price = close[-1] * (1 - SLIPPAGE)
        pnl_net = (exit_price - entry_price) / entry_price - 2 * COMMISSION_TAKER
        trades.append((entry_idx, n - 1, pnl_net))
    n_trades = len(trades)
    if n_trades == 0:
        return {"n_trades": 0, "pnl_pct": 0.0, "sharpe": float("nan"), "win_rate": float("nan")}
    pnls = np.array([t[2] for t in trades])
    holding = np.mean([t[1] - t[0] for t in trades])
    sharpe = (
        (pnls.mean() / pnls.std(ddof=1)) * np.sqrt(bars_per_year / holding)
        if pnls.std(ddof=1) > 0 and holding > 0
        else 0.0
    )
    return {
        "n_trades": n_trades,
        "pnl_pct": float(pnls.sum() * 100.0),
        "sharpe": float(sharpe),
        "win_rate": float((pnls > 0).mean()),
    }


# ─── Strategy generators ───
def strat_ema_crossover(df: pd.DataFrame, fast: int, slow: int, atr_period: int):
    close = df["close"].to_numpy(dtype=np.float64)
    fast_ema = _ema(close, fast)
    slow_ema = _ema(close, slow)
    n = len(df)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(slow + 2, n):
        if (fast_ema[i - 1] > slow_ema[i - 1]) and (fast_ema[i - 2] <= slow_ema[i - 2]):
            entry[i] = True
        if (fast_ema[i - 1] < slow_ema[i - 1]) and (fast_ema[i - 2] >= slow_ema[i - 2]):
            exit_[i] = True
    return entry, exit_, max(slow, atr_period) + 2, _atr(df, atr_period)


def strat_rsi_mr(
    df: pd.DataFrame, rsi_period: int, oversold: int, overbought: int, atr_period: int
):
    close = df["close"].to_numpy(dtype=np.float64)
    rsi_arr = _rsi(close, rsi_period)
    n = len(df)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    for i in range(rsi_period + 2, n):
        if not np.isnan(rsi_arr[i - 1]):
            if rsi_arr[i - 1] < oversold:
                entry[i] = True
            if rsi_arr[i - 1] > overbought:
                exit_[i] = True
    return entry, exit_, max(rsi_period, atr_period) + 2, _atr(df, atr_period)


def strat_adx_donchian(
    df: pd.DataFrame,
    lookback_n: int,
    exit_n: int,
    adx_period: int,
    adx_thresh: float,
    atr_period: int,
):
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    n = len(df)
    roll_high = pd.Series(high).rolling(lookback_n, min_periods=lookback_n).max().to_numpy()
    roll_low = pd.Series(low).rolling(exit_n, min_periods=exit_n).min().to_numpy()
    adx_arr = _adx(df, adx_period)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    warmup = max(lookback_n, exit_n, 2 * adx_period, atr_period) + 2
    for i in range(warmup, n):
        rh = roll_high[i - 2]
        rl = roll_low[i - 2]
        if (
            not np.isnan(rh)
            and not np.isnan(adx_arr[i - 1])
            and close[i - 1] > rh
            and adx_arr[i - 1] > adx_thresh
        ):
            entry[i] = True
        if not np.isnan(rl) and close[i - 1] < rl:
            exit_[i] = True
    return entry, exit_, warmup, _atr(df, atr_period)


def strat_atr_breakout(
    df: pd.DataFrame, atr_period: int, atr_breakout_mult: float, atr_stop_period: int
):
    close = df["close"].to_numpy(dtype=np.float64)
    atr_arr = _atr(df, atr_period)
    atr_stop = _atr(df, atr_stop_period) if atr_stop_period != atr_period else atr_arr
    n = len(df)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    warmup = max(atr_period, atr_stop_period) + 3
    for i in range(warmup, n):
        if not np.isnan(atr_arr[i - 2]):
            if close[i - 1] > close[i - 2] + atr_breakout_mult * atr_arr[i - 2]:
                entry[i] = True
            if close[i - 1] < close[i - 2] - atr_breakout_mult * atr_arr[i - 2]:
                exit_[i] = True
    return entry, exit_, warmup, atr_stop


def strat_triple_confirm(
    df: pd.DataFrame,
    ema_period: int,
    rsi_period: int,
    rsi_thresh: int,
    adx_period: int,
    adx_thresh: float,
    atr_period: int,
):
    close = df["close"].to_numpy(dtype=np.float64)
    ema_arr = _ema(close, ema_period)
    rsi_arr = _rsi(close, rsi_period)
    adx_arr = _adx(df, adx_period)
    n = len(df)
    entry = np.zeros(n, dtype=bool)
    exit_ = np.zeros(n, dtype=bool)
    warmup = max(ema_period, rsi_period, 2 * adx_period, atr_period) + 2
    for i in range(warmup, n):
        if (
            not np.isnan(ema_arr[i - 1])
            and not np.isnan(rsi_arr[i - 1])
            and not np.isnan(adx_arr[i - 1])
        ):
            if (
                close[i - 1] > ema_arr[i - 1]
                and rsi_arr[i - 1] < rsi_thresh
                and adx_arr[i - 1] > adx_thresh
            ):
                entry[i] = True
            if close[i - 1] < ema_arr[i - 1] or rsi_arr[i - 1] > 75:
                exit_[i] = True
    return entry, exit_, warmup, _atr(df, atr_period)


# ─── Helpers ───
def _normalize_df(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "ts" in df.columns:
        ts_col = "ts"
    elif "time" in df.columns:
        ts_col = "time"
    elif "timestamp" in df.columns:
        ts_col = "timestamp"
    else:
        df = df.reset_index()
        ts_col = "ts" if "ts" in df.columns else "time"
    df["ts"] = pd.to_datetime(df[ts_col], utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    return df[["ts", "open", "high", "low", "close", "volume"]]


def split_train_heldout(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Physical train/held-out split on the `ts` column (ADR 0067 Q4, CC4 S50).

    Prevents champion-bias (Bailey 2014): the parameter sweep must only ever see
    TRAIN data, otherwise sweeping a grid and picking the per-combo winner overfits
    to the full sample. train = rows with ts < HELDOUT_START; heldout = rows with
    ts ∈ [HELDOUT_START, HELDOUT_END]. Both slices get a fresh 0..n-1 index for the
    positional logic in `_backtest`.

    Args:
        df: normalized OHLCV frame with a tz-aware UTC `ts` column (see _normalize_df).

    Returns:
        (train, heldout) — disjoint frames; heldout may be empty if data predates
        HELDOUT_START.
    """
    start = pd.Timestamp(HELDOUT_START, tz="UTC")
    end = pd.Timestamp(HELDOUT_END, tz="UTC")
    train = df[df["ts"] < start].reset_index(drop=True)
    heldout = df[(df["ts"] >= start) & (df["ts"] <= end)].reset_index(drop=True)
    return train, heldout


def eval_heldout_once(combo: dict, df: pd.DataFrame) -> dict:
    """Evaluate a single chosen combo on the held-out slice — ONE call, not a sweep.

    Called on the per-combo winner (T8) after the train-only sweep selects it, to
    report out-of-sample performance honestly. NEVER call inside the sweep loop —
    doing so would reintroduce the champion-bias this split exists to remove.

    Args:
        combo: dict with "strategy", "params", "atr_stop_mult", and "bars_per_year".
        df: the held-out OHLCV slice from split_train_heldout (tz-aware `ts` column).

    Returns:
        Metrics dict prefixed with "heldout_" (pnl_pct, sharpe, n_trades, win_rate).
    """
    strat_fn, _grid, _stops = _build_grid(combo["strategy"])
    entry, exit_, warmup, atr_arr = strat_fn(df, **combo["params"])
    metrics = _backtest(
        df, entry, exit_, atr_arr, combo["atr_stop_mult"], warmup, combo["bars_per_year"]
    )
    return {
        "heldout_pnl_pct": metrics["pnl_pct"],
        "heldout_sharpe": metrics["sharpe"],
        "heldout_n_trades": metrics["n_trades"],
        "heldout_win_rate": metrics["win_rate"],
    }


def _build_periods(df: pd.DataFrame, n_chunks: int = 5) -> list[tuple[date, date]]:
    start = df["ts"].dt.date.iloc[0]
    end = df["ts"].dt.date.iloc[-1]
    total_days = (end - start).days
    chunk_days = total_days // n_chunks
    periods = []
    for i in range(n_chunks):
        s = start + timedelta(days=i * chunk_days)
        e = start + timedelta(days=(i + 1) * chunk_days) if i < n_chunks - 1 else end
        periods.append((s, e))
    return periods


def _eval_robustness(
    df: pd.DataFrame,
    strat_fn: Callable,
    params: dict,
    atr_stop_mult: float,
    periods: list[tuple[date, date]],
    bars_per_year: int,
) -> dict:
    entry, exit_, warmup, atr_arr = strat_fn(df, **params)
    full = _backtest(df, entry, exit_, atr_arr, atr_stop_mult, warmup, bars_per_year)
    sub_results = []
    for start, end in periods:
        sub = df[(df["ts"].dt.date >= start) & (df["ts"].dt.date <= end)].reset_index(drop=True)
        if len(sub) < 100:
            continue
        s_entry, s_exit, s_warm, s_atr = strat_fn(sub, **params)
        sub_results.append(
            _backtest(sub, s_entry, s_exit, s_atr, atr_stop_mult, s_warm, bars_per_year)
        )
    n_pos = sum(1 for r in sub_results if r["pnl_pct"] > 0)
    return {
        "params": params,
        "atr_stop_mult": atr_stop_mult,
        "full_pnl_pct": full["pnl_pct"],
        "full_sharpe": full["sharpe"],
        "full_n_trades": full["n_trades"],
        "full_win_rate": full["win_rate"],
        "subperiod_pos": n_pos,
        "subperiod_total": len(sub_results),
        "subperiod_pnls": [round(r["pnl_pct"], 2) for r in sub_results],
    }


def _build_grid(strategy: str) -> tuple[Callable, list[dict], list[float]]:
    base_atr_stop = [1.5, 2.0, 2.5, 3.0]
    if strategy == "ema_cross":
        return (
            strat_ema_crossover,
            [
                {"fast": f, "slow": s, "atr_period": ap}
                for f, s, ap in product([5, 8, 12, 20], [21, 50, 100, 200], [9, 14, 21])
                if f < s
            ],
            base_atr_stop,
        )
    if strategy == "rsi_mr":
        return (
            strat_rsi_mr,
            [
                {"rsi_period": rp, "oversold": o, "overbought": ob, "atr_period": ap}
                for rp, o, ob, ap in product([7, 14, 21], [25, 30, 35], [65, 70, 75], [9, 14])
            ],
            base_atr_stop,
        )
    if strategy == "adx_donch":
        return (
            strat_adx_donchian,
            [
                {
                    "lookback_n": lb,
                    "exit_n": ex,
                    "adx_period": 14,
                    "adx_thresh": at,
                    "atr_period": ap,
                }
                for lb, ex, at, ap in product([10, 15, 20, 30], [8, 10, 15], [20, 25, 30], [9, 14])
            ],
            base_atr_stop,
        )
    if strategy == "atr_break":
        return (
            strat_atr_breakout,
            [
                {"atr_period": ap, "atr_breakout_mult": abm, "atr_stop_period": asp}
                for ap, abm, asp in product([9, 14, 21], [1.0, 1.5, 2.0, 2.5, 3.0], [9, 14, 21])
            ],
            base_atr_stop,
        )
    if strategy == "triple":
        return (
            strat_triple_confirm,
            [
                {
                    "ema_period": ep,
                    "rsi_period": 14,
                    "rsi_thresh": rt,
                    "adx_period": 14,
                    "adx_thresh": at,
                    "atr_period": 14,
                }
                for ep, rt, at in product([50, 100, 200], [50, 60, 70], [20, 25, 30])
            ],
            base_atr_stop,
        )
    raise ValueError(f"Unknown: {strategy}")


def _log_iter(event: dict) -> None:
    event["timestamp"] = datetime.now(UTC).isoformat()
    with ITER_LOG.open("a") as f:
        f.write(json.dumps(event) + "\n")


def _save_pass(result: dict) -> None:
    with RESULTS_JSONL.open("a") as f:
        f.write(json.dumps(result, default=str) + "\n")


def _load_best() -> dict:
    if BEST_JSON.exists():
        return json.loads(BEST_JSON.read_text())
    return {}


def _save_best(best: dict) -> None:
    BEST_JSON.write_text(json.dumps(best, indent=2, default=str))


def run_combo(symbol: str, interval: str, path: str, strategies: list[str], iteration: int) -> dict:
    bpy = BARS_PER_YEAR_BY_INTERVAL.get(interval, 2190)
    print(f"\n[{symbol} {interval}] iter={iteration} bpy={bpy} loading {path}", flush=True)
    t0 = time.time()
    try:
        df = _normalize_df(path)
    except Exception as e:
        print(f"  LOAD ERROR: {e}", flush=True)
        _log_iter({"event": "load_error", "combo": f"{symbol}_{interval}", "error": str(e)})
        return {"error": str(e)}

    print(
        f"  loaded {len(df):,} bars  {df['ts'].iloc[0].date()} → {df['ts'].iloc[-1].date()}",
        flush=True,
    )
    if len(df) < 500:
        print("  SKIP — too few bars", flush=True)
        return {"skipped": True}

    # CC4 S50: sweep train-only (anti-champion-bias ADR 0067 Q4). The held-out slice
    # (ts >= HELDOUT_START) is reserved for a single eval_heldout_once() on the winner.
    df, _heldout = split_train_heldout(df)
    print(
        f"  train slice: {len(df):,} bars  (held-out {len(_heldout):,} bars reserved)",
        flush=True,
    )
    if len(df) < 500:
        print("  SKIP — too few train bars after held-out split", flush=True)
        return {"skipped": True}

    periods = _build_periods(df, n_chunks=5)
    combo_pass: list[dict] = []
    for strat_name in strategies:
        try:
            strat_fn, param_grid, stop_mults = _build_grid(strat_name)
        except Exception as e:
            print(f"  {strat_name} grid error: {e}", flush=True)
            continue
        n_evals = 0
        n_pass_strat = 0
        for params in param_grid:
            for asm in stop_mults:
                try:
                    r = _eval_robustness(df, strat_fn, params, asm, periods, bpy)
                except Exception:
                    continue
                n_evals += 1
                if (
                    r["full_pnl_pct"] > 0
                    and r["full_sharpe"] > 0.5
                    and r["subperiod_pos"] >= 4
                    and r["full_n_trades"] >= 20
                ):
                    r["strategy"] = strat_name
                    r["symbol"] = symbol
                    r["interval"] = interval
                    r["iteration"] = iteration
                    r["bars_per_year"] = bpy
                    r["score"] = (
                        r["full_pnl_pct"]
                        * r["subperiod_pos"]
                        * r["full_sharpe"]
                        * np.log1p(r["full_n_trades"])
                    )
                    combo_pass.append(r)
                    n_pass_strat += 1
                    _save_pass(r)
        print(f"  {strat_name}: {n_evals} evals → {n_pass_strat} PASS", flush=True)

    elapsed = time.time() - t0
    best = _load_best()
    combo_key = f"{symbol}_{interval}"
    if combo_pass:
        combo_pass.sort(key=lambda x: x["score"], reverse=True)
        new_best = combo_pass[0]
        existing = best.get(combo_key)
        if existing is None or new_best["score"] > existing.get("score", -1):
            best[combo_key] = {
                "strategy": new_best["strategy"],
                "params": new_best["params"],
                "atr_stop_mult": new_best["atr_stop_mult"],
                "full_pnl_pct": new_best["full_pnl_pct"],
                "full_sharpe": new_best["full_sharpe"],
                "full_n_trades": new_best["full_n_trades"],
                "subperiod_pnls": new_best["subperiod_pnls"],
                "score": new_best["score"],
                "iteration_found": iteration,
                "ts_found": datetime.now(UTC).isoformat(),
            }
            _save_best(best)
            print(
                f"  ★ NEW BEST {combo_key}: {new_best['strategy']} pnl={new_best['full_pnl_pct']:.2f}% trades={new_best['full_n_trades']}",
                flush=True,
            )

    summary = {
        "event": "combo_done",
        "combo": combo_key,
        "iteration": iteration,
        "n_pass": len(combo_pass),
        "elapsed_s": round(elapsed, 1),
    }
    _log_iter(summary)
    print(f"  [{symbol} {interval}] done: {len(combo_pass)} PASS  {elapsed:.1f}s", flush=True)
    return summary


def main() -> int:
    print(f"=== ENDLESS AUTORESEARCH starting {datetime.now(UTC).isoformat()} ===", flush=True)
    print(f"Combos: {len(COMBOS)}", flush=True)
    print(f"Output: {OUT_DIR}", flush=True)
    _log_iter({"event": "loop_start", "combos": len(COMBOS)})

    iteration = 0
    while True:
        iteration += 1
        print(f"\n========== ITERATION {iteration} ==========", flush=True)
        iter_start = time.time()
        for symbol, interval, path in COMBOS:
            try:
                run_combo(
                    symbol,
                    interval,
                    path,
                    ["ema_cross", "rsi_mr", "adx_donch", "atr_break", "triple"],
                    iteration,
                )
            except Exception:
                tb = traceback.format_exc()
                print(f"COMBO ERROR {symbol} {interval}:\n{tb}", flush=True)
                _log_iter({"event": "combo_error", "combo": f"{symbol}_{interval}", "trace": tb})
        iter_elapsed = time.time() - iter_start
        print(f"\n=== ITERATION {iteration} done в {iter_elapsed/60:.1f}min ===", flush=True)
        _log_iter(
            {
                "event": "iteration_done",
                "iteration": iteration,
                "elapsed_min": round(iter_elapsed / 60, 1),
            }
        )
        time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
