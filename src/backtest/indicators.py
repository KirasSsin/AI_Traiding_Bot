from typing import Any, Dict, Optional

import logging
import numpy as np
import pandas as pd
import yaml


logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def calculate_indicators(df: pd.DataFrame, cfg: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Compute indicators + signal column for replay.

    Strategy dispatch via cfg["strategy"]["type"]:
      "ema_crossover" (default) — EMA cross up + RSI<overbought filter
      "mean_reversion"          — RSI<oversold AND close<lower_BB (S15 ADR 0030)
      "donchian"                — Donchian channel breakout (S35 ADR 0054)
      "volume_breakout"         — Volume-confirmed Donchian breakout (S39 T4)

    Signal encoding (replay_engine consumer):
      1 -> long entry candidate
      0 -> no signal
      -1 -> short/channel exit candidate (volume_breakout emits; others may not)
    """
    if cfg is None:
        cfg = load_config()

    out = df.copy()
    strategy_cfg = cfg.get("strategy", {}).get("indicators", {})
    strategy_type = str(cfg.get("strategy", {}).get("type", "ema_crossover")).lower()
    ema_cfg = strategy_cfg.get("ema", {})
    rsi_cfg = strategy_cfg.get("rsi", {})
    atr_cfg = strategy_cfg.get("atr", {})
    bb_cfg = strategy_cfg.get("bb", {})

    fast = int(ema_cfg.get("fast_period", 20))
    slow = int(ema_cfg.get("slow_period", 50))
    rsi_period = int(rsi_cfg.get("period", 14))
    atr_period = int(atr_cfg.get("period", 14))

    out["ema_fast"] = out["close"].ewm(span=fast, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=slow, adjust=False).mean()

    # S27 T3: RSI warm-up gating. Pre-fix used .fillna(50.0) which masked NaN
    # warm-up — RSI[0..rsi_period-1] would equal 50.0 (or seeded value) instead
    # of NaN. talib.RSI standard returns NaN for first `period` bars.
    # Mean_reversion strategy immune (BB gates with min_periods=20). Ema_crossover
    # affected: RSI<overbought filter could admit invalid entries в warm-up.
    delta = out["close"].diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1 / rsi_period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1 / rsi_period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # Mask first `rsi_period` bars NaN (warm-up not complete)
    rsi.iloc[:rsi_period] = np.nan
    out["rsi"] = rsi

    # S27 T3: ATR warm-up gating consistency
    high_low = out["high"] - out["low"]
    high_close = (out["high"] - out["close"].shift(1)).abs()
    low_close = (out["low"] - out["close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1 / atr_period, adjust=False).mean()
    atr.iloc[:atr_period] = np.nan
    out["atr"] = atr

    if strategy_type == "mean_reversion":
        # S15 ADR 0030: RSI extreme + Bollinger Bands AND-gated trigger
        bb_period = int(bb_cfg.get("period", 20))
        bb_k = float(bb_cfg.get("k", 2.0))
        oversold = float(rsi_cfg.get("oversold", 30))
        rolling_mean = out["close"].rolling(window=bb_period, min_periods=bb_period).mean()
        rolling_std = out["close"].rolling(window=bb_period, min_periods=bb_period).std(ddof=0)
        out["bb_middle"] = rolling_mean
        out["bb_upper"] = rolling_mean + bb_k * rolling_std
        out["bb_lower"] = rolling_mean - bb_k * rolling_std
        signal = np.zeros(len(out), dtype=np.int8)
        long_mask = (out["rsi"] < oversold) & (out["close"] < out["bb_lower"])
        signal[np.where(long_mask)[0]] = 1
        out["signal"] = signal
        logger.info(
            "Indicators ready (mean_reversion): RSI(%s)<%.0f AND close<lower_BB(%s, %.1fσ), long signals=%s",
            rsi_period,
            oversold,
            bb_period,
            bb_k,
            int(signal.sum()),
        )
    elif strategy_type == "donchian":
        # S35 ADR 0054 LOCKED: Donchian breakout long-only (lookback_n=20).
        # Entry: close(T) > max(high[T-lookback_n:T]) excluding current bar AND FLAT.
        # Exit emitted via SL=ATR×atr_stop_mult (replay_engine SL handler) — TP disabled
        # by setting tp_atr_mult astronomically high in donchian_runner config.
        donchian_cfg = strategy_cfg.get("donchian", {})
        lookback_n = int(donchian_cfg.get("lookback_n", 20))
        prior_high = out["high"].shift(1).rolling(window=lookback_n, min_periods=lookback_n).max()
        out["donchian_high"] = prior_high
        signal = np.zeros(len(out), dtype=np.int8)
        long_mask = out["close"] > prior_high
        signal[np.where(long_mask.fillna(False))[0]] = 1
        out["signal"] = signal
        logger.info(
            "Indicators ready (donchian): lookback_n=%s, ATR(%s) stop, long signals=%s",
            lookback_n,
            atr_period,
            int(signal.sum()),
        )
    elif strategy_type == "volume_breakout":
        # S39 T4: Volume breakout long-only (autoresearch sweep#1644 LOCKED per ADR 0059).
        # Entry: close > rolling_high AND volume > vol_mean * vol_mult (AND FLAT).
        # Exit: channel (close < rolling_low) OR ATR intrabar stop (replay_engine SL handler).
        vb_cfg = strategy_cfg.get("volume_breakout", {})
        lookback_n = int(vb_cfg.get("lookback_n", 9))
        exit_lookback_n = int(vb_cfg.get("exit_lookback_n", 8))
        vol_window = int(vb_cfg.get("vol_window", 10))
        vol_mult = float(vb_cfg.get("vol_mult", 1.4563))
        signal = compute_volume_breakout_signals(
            out,
            lookback_n=lookback_n,
            exit_lookback_n=exit_lookback_n,
            vol_window=vol_window,
            vol_mult=vol_mult,
            atr_period=atr_period,
        )
        out["signal"] = signal
        logger.info(
            "Indicators ready (volume_breakout): lookback_n=%s, exit_lookback_n=%s, "
            "vol_window=%s, vol_mult=%.4f, ATR(%s) stop, long signals=%s",
            lookback_n,
            exit_lookback_n,
            vol_window,
            vol_mult,
            atr_period,
            int(signal.sum()),
        )
    else:
        # ema_crossover (legacy default)
        cross_up = (out["ema_fast"].shift(1) <= out["ema_slow"].shift(1)) & (
            out["ema_fast"] > out["ema_slow"]
        )
        overbought = float(rsi_cfg.get("overbought", 68))
        signal = np.zeros(len(out), dtype=np.int8)
        signal[np.where(cross_up & (out["rsi"] < overbought))[0]] = 1
        out["signal"] = signal
        logger.info(
            "Indicators ready (ema_crossover): EMA %s/%s, RSI %s, ATR %s, long signals=%s",
            fast,
            slow,
            rsi_period,
            atr_period,
            int(signal.sum()),
        )

    return out


def compute_volume_breakout_signals(
    df: pd.DataFrame,
    *,
    lookback_n: int,
    exit_lookback_n: int,
    vol_window: int,
    vol_mult: float,
    atr_period: int,
) -> np.ndarray:
    """Vectorized volume_breakout signal generator (long-only entry/channel-exit).

    Returns int8 array of length len(df):
      - 0 = no action (FLAT or HOLD)
      - 1 = entry signal (close[i-1] > rolling_high AND volume[i-1] > vol_mean * vol_mult)
      - -1 = channel exit signal (close[i-1] < rolling_low)

    NOTE: ATR intrabar stop signal is NOT computed here — strategy class (T3)
    handles ATR stop using its own state (entry_price + ATR value).

    Convention: signal on bar i derived from data through bar i-1 (no look-ahead).
    Reference windows EXCLUDE current bar (use [i-2] index per research toy).

    Source: research/strategies.py::strat_volume_breakout (autoresearch sweep#1644
    LOCKED per ADR 0059, branch autoresearch/donchian-may8 commit fff54ee).

    Args:
        df: DataFrame with columns open/high/low/close/volume.
        lookback_n: Donchian channel entry lookback (LOCKED=9).
        exit_lookback_n: Donchian channel exit lookback (LOCKED=8).
        vol_window: Volume rolling mean window (LOCKED=10).
        vol_mult: Volume must exceed mean * this (LOCKED=1.4563).
        atr_period: Wilder ATR period (LOCKED=9) — used only for warmup gating.

    Returns:
        np.ndarray[int8] of length len(df).
    """
    n = len(df)
    if "volume" not in df.columns:
        return np.zeros(n, dtype=np.int8)
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    volume = df["volume"].to_numpy(dtype=np.float64)

    roll_high = pd.Series(high).rolling(lookback_n, min_periods=lookback_n).max().to_numpy()
    roll_low = pd.Series(low).rolling(exit_lookback_n, min_periods=exit_lookback_n).min().to_numpy()
    vol_mean = pd.Series(volume).rolling(vol_window, min_periods=vol_window).mean().to_numpy()

    signals = np.zeros(n, dtype=np.int8)
    warmup = max(lookback_n, exit_lookback_n, atr_period, vol_window) + 2
    for i in range(warmup, n):
        ref_h = roll_high[i - 2]
        ref_l = roll_low[i - 2]
        if (
            not np.isnan(ref_h)
            and not np.isnan(vol_mean[i - 1])
            and close[i - 1] > ref_h
            and volume[i - 1] > vol_mean[i - 1] * vol_mult
        ):
            signals[i] = 1
        elif not np.isnan(ref_l) and close[i - 1] < ref_l:
            signals[i] = -1
    return signals
