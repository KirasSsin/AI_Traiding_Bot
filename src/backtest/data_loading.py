"""Backtest OHLCV loading + single-symbol WFA helpers.

S55 LOW ARCH-05: relocated VERBATIM from src.__main__ (the CLI composition root) to
fix a layering inversion — lower layers (src.backtest, src.dashboard) were importing
private functions from the top-of-stack entry module. The OHLCV-loading + single-symbol
WFA logic belongs in src/backtest/, not the CLI module.

Behavior is byte-identical to the prior __main__ bodies; only the def names changed
(leading underscore dropped for the two public entrypoints). __main__ re-exports the
old private aliases (`_load_ohlcv`, `_run_wfa_single_symbol`) so existing test
patch-paths (`patch("src.__main__._load_ohlcv")`) survive unchanged.
"""

from __future__ import annotations

import re

import pandas as pd

from src.backtest.data_collector import load_market_data
from src.backtest.mc_permutation import sign_flip_p_value
from src.backtest.replay_engine import run_replay
from src.backtest.trade_extractor import extract_trade_records
from src.backtest.walk_forward import (
    WalkForwardRunner,
    WindowSplitter,
)

# SEC-S55-01 — anchored symbol allowlist (mirrors backtest_runner._RUN_ID_RE S49 H1).
# `symbol` is f-string-interpolated into the parquet read path in load_ohlcv below;
# load_ohlcv is reachable both from the unauthenticated /api/backtest endpoint and
# from the CLI, so the gate lives here as defense-in-depth (the dashboard
# BacktestPayload.symbol validator is the boundary 422). ANCHORED (\A...\Z + fullmatch)
# is mandatory — a substring `^...$` match would let 'BTCUSDT\n/evil' through.
_SYMBOL_RE = re.compile(r"\A[A-Z0-9]{1,20}\Z")


def load_ohlcv(*, symbol: str, start: str, end: str, interval: str = "60") -> pd.DataFrame:
    """Load OHLCV from Parquet via data_collector.

    S12 T2: closes S11 stub. Reuses existing data_collector pipeline.
    Operator must run `python -m src backfill --symbol <X>` to populate Parquet first.

    S13 T4 (CC4): pre-flight NaN assertion — `df.dropna()` post-warmup must yield
    >=90% bars else WFA aborts with explicit error.

    S19 ADR 0034: interval param extends parquet path: 60 → _1h, 15 → _15m.

    SEC-S55-01: `symbol` is f-string-interpolated into the parquet path below and is
    attacker-controlled via /api/backtest, so it is validated against an anchored
    allowlist FIRST — path traversal (e.g. '../../etc/passwd') raises ValueError
    before any filesystem access.
    """
    if not _SYMBOL_RE.fullmatch(symbol):
        raise ValueError(
            f"Invalid symbol '{symbol}': expected 1-20 uppercase alphanumeric chars (e.g. BTCUSDT)"
        )
    interval_label_map: dict[str, str] = {
        "5": "5m",
        "15": "15m",
        "30": "30m",
        "60": "1h",
        "120": "2h",
        "240": "4h",
        "D": "1d",
    }
    interval_label = interval_label_map.get(interval, "1h")
    parquet_path = f"data/{symbol}_{interval_label}.parquet"
    config = {
        "data": {
            "source": "parquet",
            "parquet_path": parquet_path,
            "start_date": start,
            "end_date": end,
        }
    }
    try:
        df = load_market_data(config)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"OHLCV Parquet missing at {parquet_path}. "
            f"Run 'python -m src backfill --symbol {symbol} --from {start} --to {end}' first. "
            f"Original error: {e}"
        ) from e

    # CC4: pre-flight NaN assertion (>=90% bars retained after dropna)
    if not df.empty:
        retained_pct = len(df.dropna()) / len(df)
        if retained_pct < 0.90:
            raise ValueError(
                f"NaN pre-flight failed for {symbol}: only {retained_pct:.1%} bars retained "
                f"after dropna (threshold >=90%). Likely data quality issue; investigate Parquet."
            )

    return df


def _default_wfa_config() -> dict[str, object]:
    """S17 ADR 0032 default config (mean-reversion RSI 35/65 + BB 1.5σ).

    S25 ADR 0039: extracted к standalone function для dashboard к override.
    Pre-registered binding parameters per ADR — CLI uses this as default,
    но dashboard может pass alternative strategy config (EMA crossover, S15 strict).
    """
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
            "type": "mean_reversion",
            "indicators": {
                "atr": {"sl_atr_mult": 1.5, "tp_atr_mult": 3.0},
                "rsi": {"period": 14, "oversold": 35, "overbought": 65},
                "bb": {"period": 20, "k": 1.5},
            },
        },
    }


def run_wfa_single_symbol(
    *,
    symbol: str,
    df: pd.DataFrame,
    strategy_config: dict[str, object] | None = None,
    bars_per_year: int = 8760,
    train_bars: int = 2000,
    test_bars: int = 500,
    k_folds: int = 5,
    embargo_bars: int = 20,
) -> tuple[list[object], list[float], dict[str, object], float]:
    """Run WFA for one symbol. Returns (trades, fold_oos_sharpes, runner_result, mc_p).

    S15 T5 — extracted from _cmd_wfa for multi-symbol aggregation.
    S25 ADR 0039: optional strategy_config override (для dashboard preset selection).
    None → defaults к _default_wfa_config (S17 mean-reversion).
    S27 T1: bars_per_year injected в config — fixes replay_engine annualization
    bug (sqrt(24*365) hardcoded). Default 8760 = 1H для backward compat.
    Note: trades typed as list[object] (forward-compat) — actual TradeRecord
    instances; cast at call site if needed.
    """
    from typing import cast

    # S33 T4 (Item #10): WFA window customizable per-call (CC6 (b) consensus train=1000/test=250 для 4H)
    splitter = WindowSplitter(
        train_bars=train_bars, test_bars=test_bars, k_folds=k_folds, embargo_bars=embargo_bars
    )
    runner = WalkForwardRunner(splitter=splitter, replay_fn=run_replay)
    config = strategy_config if strategy_config is not None else _default_wfa_config()
    # S27 T1: ensure bars_per_year present (override если уже в strategy_config)
    if "bars_per_year" not in config:
        config = dict(config)
        config["bars_per_year"] = bars_per_year
    # S33 T4 (Item #10): pass symbol для error context
    runner_result = runner.run(df=df, config=config, symbol=symbol)

    # MC sign-flip on aggregated OOS returns
    oos_trades_df = runner_result["aggregate"]["oos_trades_df"]
    if oos_trades_df.empty:
        mc_p = 1.0
    else:
        import numpy as np

        raw = oos_trades_df["net_pnl"].astype(float).to_numpy()
        returns_arr = np.asarray(raw, dtype=float) / 10000.0
        mc_p = sign_flip_p_value(returns_arr, n_iterations=2000, seed=42)

    # Per-fold trade extraction (S13 T5)
    from src.risk.trade_history import TradeRecord as _TradeRecord

    trades: list[_TradeRecord] = []
    fold_sharpes: list[float] = []
    for fold_data in runner_result["folds"]:
        fold_sharpes.append(fold_data["oos_is_sharpe_ratio"])
        fold_trades_df = fold_data.get("oos_trades_df")
        if fold_trades_df is not None and not fold_trades_df.empty:
            df_normalized = fold_trades_df.copy()
            if (
                "timestamp_open" in df_normalized.columns
                and "entry_ts" not in df_normalized.columns
            ):
                df_normalized = df_normalized.rename(
                    columns={
                        "timestamp_open": "entry_ts",
                        "timestamp_close": "exit_ts",
                    }
                )
            from datetime import UTC as _UTC

            for _col in ("entry_ts", "exit_ts"):
                if _col in df_normalized.columns:
                    col_series = pd.to_datetime(df_normalized[_col])
                    if col_series.dt.tz is None:
                        col_series = col_series.dt.tz_localize(_UTC)
                    df_normalized[_col] = col_series
            if "fees_paid" not in df_normalized.columns:
                entry_fee = df_normalized.get("entry_fee", 0)
                exit_fee = df_normalized.get("exit_fee", 0)
                df_normalized["fees_paid"] = entry_fee + exit_fee
            trades.extend(extract_trade_records(df_normalized, symbol=symbol))
    return cast(list[object], trades), fold_sharpes, cast(dict[str, object], runner_result), mc_p
