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

    Signal encoding (replay_engine consumer):
      1 -> long entry candidate
      0 -> no signal
      -1 -> short entry candidate (only ema_crossover may emit; mean-reversion never)
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
            rsi_period, oversold, bb_period, bb_k, int(signal.sum()),
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
            fast, slow, rsi_period, atr_period, int(signal.sum()),
        )

    return out
