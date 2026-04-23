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
    Compute EMA/RSI/ATR and long-only signal for replay.

    Signal encoding:
      1 -> long entry candidate (EMA cross up + RSI filter)
      0 -> no signal
    """
    if cfg is None:
        cfg = load_config()

    out = df.copy()
    strategy_cfg = cfg.get("strategy", {}).get("indicators", {})
    ema_cfg = strategy_cfg.get("ema", {})
    rsi_cfg = strategy_cfg.get("rsi", {})
    atr_cfg = strategy_cfg.get("atr", {})

    fast = int(ema_cfg.get("fast_period", 20))
    slow = int(ema_cfg.get("slow_period", 50))
    rsi_period = int(rsi_cfg.get("period", 14))
    atr_period = int(atr_cfg.get("period", 14))

    out["ema_fast"] = out["close"].ewm(span=fast, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=slow, adjust=False).mean()

    delta = out["close"].diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1 / rsi_period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1 / rsi_period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi"] = (100 - (100 / (1 + rs))).fillna(50.0)

    high_low = out["high"] - out["low"]
    high_close = (out["high"] - out["close"].shift(1)).abs()
    low_close = (out["low"] - out["close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    out["atr"] = true_range.ewm(alpha=1 / atr_period, adjust=False).mean()

    cross_up = (out["ema_fast"].shift(1) <= out["ema_slow"].shift(1)) & (
        out["ema_fast"] > out["ema_slow"]
    )
    overbought = float(rsi_cfg.get("overbought", 68))

    signal = np.zeros(len(out), dtype=np.int8)
    signal[np.where(cross_up & (out["rsi"] < overbought))[0]] = 1
    out["signal"] = signal

    logger.info(
        "Indicators ready: EMA %s/%s, RSI %s, ATR %s, long signals=%s",
        fast,
        slow,
        rsi_period,
        atr_period,
        int(signal.sum()),
    )
    return out
