import logging
import os
from typing import Any, Dict

import pandas as pd


REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]
logger = logging.getLogger(__name__)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {c: c.strip().lower() for c in df.columns}
    df = df.rename(columns=mapping)
    if "time" in df.columns and "timestamp" not in df.columns:
        df["timestamp"] = pd.to_datetime(df["time"], errors="coerce")
    elif "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    else:
        # Fallback to first column if file has no named time column
        df["timestamp"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Market data missing required column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _resolve_path(path: str) -> str:
    return os.path.abspath(path) if not os.path.isabs(path) else path


def _postprocess_df(df: pd.DataFrame, data_cfg: Dict[str, Any]) -> pd.DataFrame:
    if df.empty:
        return df

    df = _normalize_columns(df)
    df = df.dropna(subset=["timestamp"] + REQUIRED_COLUMNS)
    df = df.sort_values("timestamp").reset_index(drop=True)

    start_date = data_cfg.get("start_date")
    end_date = data_cfg.get("end_date")
    # tz alignment: when df timestamps are tz-aware (parquet from backfill writes ISO+UTC),
    # filter dates must be tz-aware too — else comparison raises TypeError.
    ts_tz = df["timestamp"].dt.tz if pd.api.types.is_datetime64_any_dtype(df["timestamp"]) else None
    if start_date:
        sd = pd.to_datetime(start_date)
        if ts_tz is not None and sd.tzinfo is None:
            sd = sd.tz_localize(ts_tz)
        df = df[df["timestamp"] >= sd]
    if end_date:
        ed = pd.to_datetime(end_date)
        if ts_tz is not None and ed.tzinfo is None:
            ed = ed.tz_localize(ts_tz)
        df = df[df["timestamp"] <= ed]

    return df.reset_index(drop=True)


def _read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV file not found: {path}")
    return pd.read_csv(path)


def _read_parquet(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Parquet file not found: {path}")
    return pd.read_parquet(path)


def load_market_data(config: Dict[str, Any]) -> pd.DataFrame:
    data_cfg = config.get("data", {})
    source = str(data_cfg.get("source", "csv")).lower()

    csv_path = _resolve_path(str(data_cfg.get("csv_path", "data/BTCUSDT_1h.csv")))
    parquet_path = _resolve_path(
        str(data_cfg.get("parquet_path", "data/BTCUSDT_1h.parquet"))
    )

    if source == "csv":
        df = _read_csv(csv_path)
        return _postprocess_df(df, data_cfg)

    if source == "parquet":
        try:
            df = _read_parquet(parquet_path)
            return _postprocess_df(df, data_cfg)
        except Exception as parquet_exc:
            logger.warning(
                "Parquet load failed (%s). Falling back to CSV source: %s",
                parquet_exc,
                csv_path,
            )
            df = _read_csv(csv_path)
            return _postprocess_df(df, data_cfg)

    raise ValueError("Unsupported data.source. Use 'csv' or 'parquet'.")


def load_data(config: Dict[str, Any]) -> pd.DataFrame:
    """Alias for `load_market_data` (older docs and external callers)."""
    return load_market_data(config)
