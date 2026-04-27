"""Entry-point: `python -m src <subcommand>` (ADR 0022 sub-decision 9).

Subcommands:
  run             — start RuntimeManager (blocking) — full wiring TODO (see T20 reference)
  backfill        — OHLCV backfill (delegated to existing scripts)
  reconcile-only  — bootstrap + reconcile, no trading loop — full wiring TODO (see T20 reference)
  kill            — write .kill_switch sentinel and exit (body in Task 19)

Note: `_cmd_run` and `_cmd_reconcile_only` bodies are placeholders — full dependency
wiring deferred to T20 integration test (which constructs RuntimeManager directly,
bypassing this CLI). Update these bodies once the T20 wiring pattern is validated.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import pandas as pd

from src.analytics.dsr import compute_dsr
from src.backtest.data_collector import load_market_data
from src.backtest.mc_permutation import sign_flip_p_value
from src.backtest.replay_engine import run_replay
from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.backtest.trade_extractor import extract_trade_records
from src.backtest.walk_forward import (
    WalkForwardRunner,
    WindowSplitter,
    evaluate_acceptance_gate,
)
from src.backtest.wfa_reporter import format_wfa_report
from src.execution.bybit.adapter import BybitMarketAdapter
from src.execution.bybit.ws_private import BybitPrivateWSConsumer
from src.execution.coordinator import Coordinator
from src.execution.reconciler import Reconciler
from src.execution.state_repo import ExecutionStateRepo
from src.marketdata.bybit.rest import BybitRESTClient
from src.marketdata.filters import BybitFilters
from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.fill_history import FillHistoryRepository
from src.risk.fill_recorder_adapter import FillRecorderAdapter
from src.risk.manager import RiskManager
from src.risk.trade_history import TradeHistoryRepository
from src.runtime.bar_source import BarSource
from src.runtime.manager import RuntimeManager
from src.signalgen.mean_reversion_strategy import MeanReversionRsiBBStrategy
from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy  # noqa: F401 — kept for backward-compat tests


def _cmd_run(args: argparse.Namespace) -> int:
    """Wire all dependencies and start RuntimeManager.

    DI graph (per ADR 0026 + pre-s11-backlog C1, closes S8a T20 STUB):
    Settings → REST client → BybitFilters (placeholders) → market adapter →
    DB connection → state repo → reconciler → coordinator → bar source →
    strategy → risk manager → WS consumer → RuntimeManager.run().

    Symbol is taken from `--symbol` CLI arg (default BTCUSDT). base_coin is
    derived from symbol suffix (BTCUSDT → BTC), mirroring the convention в
    `Reconciler._derive_base_coin`.

    BybitFilters constructed here с placeholder values; production wiring will
    load filters via `BybitRESTClient.get_filters(symbol)` (deferred S12+).
    FillRecorder = FillRecorderAdapter (S12 T1 — closes _NoopFillRecorder stub
    per ADR 0027 Q5; best-effort 2-layer pattern, см. fill_recorder_adapter docstring).

    Returns:
        0 — clean exit;
        130 — KeyboardInterrupt (SIGINT convention);
        1 — runtime crash (unexpected Exception).
    """
    from sqlite3 import Connection

    settings = Settings()
    symbol: str = args.symbol
    # Derive base_coin from symbol suffix (BTCUSDT → BTC, BTCUSDC → BTC)
    base_coin = symbol[:-4] if symbol.endswith(("USDT", "USDC")) else symbol

    # Database
    mig_dir = Path(__file__).resolve().parent.parent / "migrations"
    init_db(settings.db_path, mig_dir)
    conn: Connection = connect(settings.db_path)

    # REST client + filters (placeholders — production loads via get_filters S12+)
    rest = BybitRESTClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.testnet,
    )
    filters = BybitFilters(
        symbol=symbol,
        step_size=Decimal("0.000001"),
        tick_size=Decimal("0.01"),
        min_order_qty=Decimal("0.00001"),
        max_order_qty=Decimal("100"),
        min_order_amt=Decimal("1"),
    )
    adapter = BybitMarketAdapter(rest=rest, filters=filters)

    # State + reconciler + coordinator
    # S19 ADR 0034 Condition A2: derive heal_max_age_seconds from interval (1H для _cmd_run)
    bar_interval = "60"
    heal_age = _derive_heal_max_age_seconds(settings, bar_interval)
    repo = ExecutionStateRepo(conn)
    reconciler = Reconciler(
        query=adapter, base_coin=base_coin, symbol=symbol,
        heal_max_age_seconds=heal_age,
    )
    coordinator = Coordinator(
        adapter=adapter,
        repo=repo,
        reconciler=reconciler,
        symbol=symbol,
        base_coin=base_coin,
    )

    # Strategy + risk manager (S15 ADR 0030: mean-reversion replaces EmaCrossover)
    strategy = MeanReversionRsiBBStrategy(
        symbol=symbol,
        rsi_period=settings.strategy_rsi_period,
        rsi_oversold=settings.strategy_rsi_oversold,
        rsi_overbought=settings.strategy_rsi_overbought,
        atr_period=settings.strategy_atr_period,
        # bb_period=20, bb_k=2.0 — pre-registered defaults per ADR 0030 (no operator override)
    )
    # S15 T1: pass symbol so RiskManager._compute_p_b queries trade history per-symbol
    risk_manager = RiskManager(conn=conn, settings=settings, symbol=symbol)

    # Bar source + WS consumer (FillRecorder = production adapter, S12 T1)
    bar_source = BarSource(adapter=rest, symbol=symbol, interval=bar_interval)
    fill_history_repo = FillHistoryRepository(conn)
    trade_history_repo = TradeHistoryRepository(conn)
    fill_recorder = FillRecorderAdapter(
        repo=fill_history_repo,
        state_repo=repo,
        trade_history_repo=trade_history_repo,
    )

    endpoint = "demo.bybit.com" if settings.testnet else "stream.bybit.com"
    ws_consumer = BybitPrivateWSConsumer(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        endpoint=endpoint,
        coordinator=coordinator,
        reconciler=reconciler,
        fill_recorder=fill_recorder,
    )

    # RuntimeManager + run
    rm = RuntimeManager(
        coordinator=coordinator,
        reconciler=reconciler,
        ws_consumer=ws_consumer,
        bar_source=bar_source,
        strategy=strategy,
        risk_manager=risk_manager,
        settings=settings,
    )

    try:
        rm.run()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: runtime crash: {e}", file=sys.stderr)
        return 1


def _derive_heal_max_age_seconds(settings: Settings, interval: str) -> int:
    """S19 ADR 0034 Condition A2: derive heal_max_age_seconds from heal_max_bars + interval.

    Architecture-recommended pattern: Settings stays pure value store (no derived values),
    bootstrap (e.g. _cmd_run) computes derived value here + passes к Reconciler.

    If settings.heal_max_bars is None, legacy heal_max_age_seconds field used directly
    (backward-compat). Otherwise: heal_max_age_seconds = heal_max_bars * interval_seconds.

    Interval string per BarSource convention ("60" = 1H, "15" = 15M).
    """
    if settings.heal_max_bars is None:
        return settings.heal_max_age_seconds
    interval_seconds_map: dict[str, int] = {
        "5": 300,
        "15": 900,
        "30": 1800,
        "60": 3600,
        "120": 7200,
        "240": 14400,
        "D": 86400,
    }
    if interval not in interval_seconds_map:
        raise ValueError(
            f"Unsupported interval '{interval}' для heal_max_age derivation. "
            f"Supported: {sorted(interval_seconds_map.keys())}."
        )
    return settings.heal_max_bars * interval_seconds_map[interval]


def _resolve_symbols(args: argparse.Namespace) -> list[str]:
    """Resolve symbol list from --symbols (multi) OR --symbol (single, fallback).

    S15 ADR 0030: --symbols overrides --symbol. Returns uppercase list.
    """
    if getattr(args, "symbols", None):
        return [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    sym = getattr(args, "symbol", None) or "BTCUSDT"
    return [sym]


def _backfill_one_symbol(
    *,
    rest: BybitRESTClient,
    symbol: str,
    start_ms: int,
    end_ms: int,
    output_path: Path,
    label: str,
    interval: str = "60",
) -> int:
    """Backfill one symbol → Parquet. Returns 0 on success, 1 on empty response."""
    print(f"backfill: fetching {symbol} {interval}M {label} ...", flush=True)
    bars = rest.get_klines(symbol, interval, start_ms, end_ms, limit_per_call=1000)
    if not bars:
        print(
            f"backfill: WARNING — empty kline response for {symbol} {label}",
            flush=True,
        )
        return 1

    rows = [
        {
            "time": b.close_time.isoformat(),
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": float(b.volume),
        }
        for b in bars
    ]
    df = pd.DataFrame(rows)
    # ADR 0003 snappy + atomic tmp-rename (S13 T2 data-integrity)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    df.to_parquet(tmp_path, index=False, compression="snappy", engine="pyarrow")
    tmp_path.rename(output_path)
    print(f"backfill: wrote {len(df)} bars to {output_path}", flush=True)
    return 0


def _cmd_backfill(args: argparse.Namespace) -> int:
    """Backfill OHLCV via BybitRESTClient.get_klines + write Parquet.

    S15 ADR 0030: supports --symbols comma-separated for multi-symbol batch
    (BTCUSDT,ETHUSDT,SOLUSDT). Each symbol → own Parquet file.

    Returns:
        0 — all symbols written successfully (>0 bars each);
        1 — at least one symbol returned empty kline response.
    """
    from datetime import UTC, datetime

    settings = Settings()
    symbols = _resolve_symbols(args)
    label = f"{args.from_date} → {args.to_date}"

    start_dt = datetime.fromisoformat(args.from_date).replace(tzinfo=UTC)
    end_dt = datetime.fromisoformat(args.to_date).replace(tzinfo=UTC)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    rest = BybitRESTClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.testnet,
    )

    interval = getattr(args, "interval", "60")
    interval_label_map: dict[str, str] = {"5": "5m", "15": "15m", "30": "30m", "60": "1h", "120": "2h", "240": "4h", "D": "1d"}
    interval_label = interval_label_map[interval]

    overall_rc = 0
    for symbol in symbols:
        # --output ignored when multi-symbol (per arg help)
        if len(symbols) == 1 and args.output_path:
            output_path = Path(args.output_path)
        else:
            output_path = Path(f"data/{symbol}_{interval_label}.parquet")
        rc = _backfill_one_symbol(
            rest=rest,
            symbol=symbol,
            start_ms=start_ms,
            end_ms=end_ms,
            output_path=output_path,
            label=label,
            interval=interval,
        )
        if rc != 0:
            overall_rc = rc
    return overall_rc


def _cmd_reconcile_only(args: argparse.Namespace) -> int:
    """Run bootstrap + reconcile, no trading loop.

    Subset of _cmd_run DI graph — only Coordinator + Reconciler needed.
    Closes S8a T20 STUB per ADR 0026 (S11 P0).

    Returns:
        0 — bootstrap clean exit;
        1 — bootstrap failure (reconcile divergence или connectivity error).
    """
    from sqlite3 import Connection

    settings = Settings()
    symbol: str = args.symbol
    base_coin = symbol[:-4] if symbol.endswith(("USDT", "USDC")) else symbol

    # Database
    mig_dir = Path(__file__).resolve().parent.parent / "migrations"
    init_db(settings.db_path, mig_dir)
    conn: Connection = connect(settings.db_path)

    # REST + market adapter (placeholders — S12 will load filters via REST)
    rest = BybitRESTClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.testnet,
    )
    filters = BybitFilters(
        symbol=symbol,
        step_size=Decimal("0.000001"),
        tick_size=Decimal("0.01"),
        min_order_qty=Decimal("0.00001"),
        max_order_qty=Decimal("100"),
        min_order_amt=Decimal("1"),
    )
    adapter = BybitMarketAdapter(rest=rest, filters=filters)

    # State + reconciler + coordinator (no RuntimeManager, no Strategy, no RiskManager)
    # S19 ADR 0034 Condition A2: heal_max_age derived from interval (1H для _cmd_reconcile_only)
    heal_age = _derive_heal_max_age_seconds(settings, "60")
    repo = ExecutionStateRepo(conn)
    reconciler = Reconciler(
        query=adapter, base_coin=base_coin, symbol=symbol,
        heal_max_age_seconds=heal_age,
    )
    coordinator = Coordinator(
        adapter=adapter,
        repo=repo,
        reconciler=reconciler,
        symbol=symbol,
        base_coin=base_coin,
    )

    try:
        coordinator.bootstrap()
        print(f"reconcile-only: bootstrap complete для {symbol}")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: reconcile-only bootstrap failed: {e}", file=sys.stderr)
        return 1


def _cmd_kill(_args: argparse.Namespace) -> int:
    """Write sentinel-file at configured path, atomic. ADR 0022 sub-decision 5.

    Atomic via os.open (O_WRONLY|O_CREAT|O_TRUNC, 0o600) + os.fdopen + os.replace.
    Mirrors src/risk/override.py:82-95 minus os.fsync — sentinel is operator-typed
    signal, paper-trade scope; fsync overhead not justified.
    """
    from src.platform.config import Settings

    settings = Settings()
    sentinel = Path(settings.runtime_kill_switch_path)
    sentinel.parent.mkdir(parents=True, exist_ok=True)

    tmp = sentinel.with_suffix(sentinel.suffix + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(b"")
        os.replace(tmp, sentinel)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)

    print(f"kill switch written: {sentinel}")
    return 0


def _load_ohlcv(*, symbol: str, start: str, end: str, interval: str = "60") -> pd.DataFrame:
    """Load OHLCV from Parquet via data_collector.

    S12 T2: closes S11 stub. Reuses existing data_collector pipeline.
    Operator must run `python -m src backfill --symbol <X>` to populate Parquet first.

    S13 T4 (CC4): pre-flight NaN assertion — `df.dropna()` post-warmup must yield
    >=90% bars else WFA aborts with explicit error.

    S19 ADR 0034: interval param extends parquet path: 60 → _1h, 15 → _15m.
    """
    interval_label_map: dict[str, str] = {"5": "5m", "15": "15m", "30": "30m", "60": "1h", "120": "2h", "240": "4h", "D": "1d"}
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


def _run_wfa_single_symbol(
    *, symbol: str, df: pd.DataFrame, strategy_config: dict[str, object] | None = None,
    bars_per_year: int = 8760,
    train_bars: int = 2000,
    test_bars: int = 500,
    k_folds: int = 5,
    embargo_bars: int = 20,
) -> "tuple[list[object], list[float], dict[str, object], float]":
    """Run WFA for one symbol. Returns (trades, fold_oos_sharpes, runner_result, mc_p).

    S15 T5 — extracted from _cmd_wfa for multi-symbol aggregation.
    S25 ADR 0039: optional strategy_config override (для dashboard preset selection).
    None → defaults к _default_wfa_config (S17 mean-reversion).
    S27 T1: bars_per_year injected в config — fixes replay_engine annualization
    bug (sqrt(24*365) hardcoded). Default 8760 = 1H для backward compat.
    Note: trades typed as list[object] (forward-compat) — actual TradeRecord
    instances; cast at call site if needed.
    """
    from typing import Any, cast
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
            if "timestamp_open" in df_normalized.columns and "entry_ts" not in df_normalized.columns:
                df_normalized = df_normalized.rename(columns={
                    "timestamp_open": "entry_ts",
                    "timestamp_close": "exit_ts",
                })
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


def _cmd_wfa(args: argparse.Namespace) -> int:
    """Run Walk-Forward Analysis + report (S15 ADR 0030: multi-symbol aggregation).

    Subcommand:
      python -m src wfa --symbols BTCUSDT,ETHUSDT,SOLUSDT --start 2021-07-02 --end 2026-04-26

    S15 T0/T5: DSR computed с n_trials = (existing trial count + 1) using cross-trial
    sigma_SR from CrossTrialLog (closes S14 Q2 REVISE carry-over).

    Returns:
        0 — verdict PASS (T1-T6 all green AND DSR > 0);
        2 — verdict FAIL;
        1 — error (empty data for ALL symbols).
    """
    import json
    import math
    import statistics

    from src.analytics.cross_trial_log import CrossTrialLog
    from src.risk.trade_history import TradeRecord as _TradeRecord

    settings = Settings()  # noqa: F841 — reserved для future settings-driven WFA params
    symbols = _resolve_symbols(args)

    all_trades: list[_TradeRecord] = []
    all_fold_sharpes: list[float] = []
    per_symbol_summary: dict[str, dict[str, object]] = {}
    mc_p_values: list[float] = []

    interval_arg = getattr(args, "interval", "60")
    # S27 T1: bars_per_year derived from interval, passed к replay_engine
    bars_per_year_map: dict[str, int] = {
        "5": 105120, "15": 35040, "30": 17520, "60": 8760, "120": 4380, "240": 2190, "D": 365,
    }
    bars_per_year_cli = bars_per_year_map.get(interval_arg, 8760)
    for symbol in symbols:
        try:
            df = _load_ohlcv(symbol=symbol, start=args.start, end=args.end, interval=interval_arg)
        except FileNotFoundError as e:
            print(f"WARNING: skip {symbol} — {e}", flush=True)
            per_symbol_summary[symbol] = {"status": "missing_parquet", "trades": 0}
            continue
        if df.empty:
            print(f"WARNING: skip {symbol} — empty OHLCV", flush=True)
            per_symbol_summary[symbol] = {"status": "empty_ohlcv", "trades": 0}
            continue

        # S33 T4 (CC6 (b) consensus): WFA window from CLI args (default ADR 0014: train=2000/test=500)
        sym_trades, sym_fold_sharpes, sym_runner_result, sym_mc_p = _run_wfa_single_symbol(
            symbol=symbol, df=df, bars_per_year=bars_per_year_cli,
            train_bars=getattr(args, "wfa_train", 2000),
            test_bars=getattr(args, "wfa_test", 500),
            k_folds=getattr(args, "wfa_folds", 5),
            embargo_bars=getattr(args, "wfa_embargo", 20),
        )
        from typing import cast as _cast
        all_trades.extend(_cast(list[_TradeRecord], sym_trades))
        all_fold_sharpes.extend(sym_fold_sharpes)
        mc_p_values.append(sym_mc_p)
        per_symbol_summary[symbol] = {
            "status": "ok",
            "trades": len(sym_trades),
            "k_folds": len(sym_fold_sharpes),
            "mean_oos_is_sharpe": (
                float(sum(sym_fold_sharpes) / len(sym_fold_sharpes))
                if sym_fold_sharpes else None
            ),
            "mc_p_value": sym_mc_p,
        }

    # Bail-out only if NO symbol succeeded WFA at all (all empty/missing).
    # Empty trades с successful folds still compute metrics → FAIL verdict (T5 n_trades=0).
    if not all_fold_sharpes:
        print(json.dumps({
            "verdict": "ERROR",
            "reason": "no symbol completed WFA (all empty/missing parquet)",
            "per_symbol": per_symbol_summary,
        }, default=str, indent=2))
        return 1

    # Aggregate MC p-value: max (most conservative across symbols)
    mc_p = max(mc_p_values) if mc_p_values else 1.0

    # S15 T0: DSR cross-trial sigma_SR (closes S14 Q2 carry-over)
    trial_log_path = Path("data/cross_trial_sharpes.json")
    trial_log = CrossTrialLog(path=trial_log_path)
    pre_existing_sharpes = trial_log.get_oos_sharpes()

    # Aggregate OOS Sharpe для THIS sprint = mean of all fold sharpes across symbols
    aggregate_oos_sharpe = (
        float(sum(all_fold_sharpes) / len(all_fold_sharpes))
        if all_fold_sharpes else float("nan")
    )
    cross_trial_sharpes = pre_existing_sharpes + [aggregate_oos_sharpe]
    n_trials = len(cross_trial_sharpes)

    if n_trials >= 2 and not math.isnan(aggregate_oos_sharpe):
        sigma_sr_value = statistics.stdev(cross_trial_sharpes)
        dsr_value = compute_dsr(
            trades=all_trades, n_trials=n_trials, sigma_sr=sigma_sr_value
        )
    else:
        sigma_sr_value = None
        dsr_value = compute_dsr(trades=all_trades, n_trials=1)

    # T1-T6 metrics aggregated across symbols
    # S19 ADR 0034 Condition A3: pass bars_per_year derived from interval
    # S33 T1: rename `bars_per_year_map` → `bars_per_year_map_wfa` to fix mypy [no-redef] (line 564 has same name in different scope)
    interval = getattr(args, "interval", "60")
    bars_per_year_map_wfa: dict[str, int] = {"5": 105120, "15": 35040, "30": 17520, "60": 8760, "120": 4380, "240": 2190, "D": 365}
    bars_per_year = bars_per_year_map_wfa[interval]
    metrics = compute_t1_t6_metrics(
        trades=all_trades,
        fold_oos_is_sharpe=all_fold_sharpes,
        bars_per_year=bars_per_year,
    )

    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=all_fold_sharpes,
        mc_p_value=mc_p,
    )

    def _nan_or_value(v: object) -> object:
        return None if (isinstance(v, float) and math.isnan(v)) else v

    # Verdict per ADR 0028/0030: PASS/FAIL based on T1-T6 + DSR
    failed_criteria: list[str] = []
    if _nan_or_value(metrics["t1_sharpe_oos"]) is None or metrics["t1_sharpe_oos"] < 1.0:
        failed_criteria.append("t1")
    if _nan_or_value(metrics["t2_sortino_oos"]) is None or metrics["t2_sortino_oos"] < 1.5:
        failed_criteria.append("t2")
    if _nan_or_value(metrics["t3_max_drawdown"]) is None or metrics["t3_max_drawdown"] >= 0.25:
        failed_criteria.append("t3")
    win_rate = metrics["t4_win_rate"]
    avg_rr = metrics["t4_avg_rr"]
    t4_fail = (
        _nan_or_value(win_rate) is None
        or _nan_or_value(avg_rr) is None
        or (avg_rr >= 2.0 and win_rate < 0.35)
        or (1.5 <= avg_rr < 2.0 and win_rate < 0.45)
        or avg_rr < 1.5
    )
    if t4_fail:
        failed_criteria.append("t4")
    if (
        _nan_or_value(metrics["t5_mean_pnl_pct"]) is None
        or metrics["t5_mean_pnl_pct"] <= 0
        or _nan_or_value(metrics["t5_t_stat"]) is None
        or metrics["t5_t_stat"] < 2.0
        or metrics["t5_n_trades"] < 100
    ):
        failed_criteria.append("t5")
    if _nan_or_value(metrics["t6_oos_is_sharpe_ratio_mean"]) is None or metrics["t6_oos_is_sharpe_ratio_mean"] < 0.7:
        failed_criteria.append("t6")

    dsr_pass = _nan_or_value(dsr_value) is not None and dsr_value > 0
    verdict = "PASS" if len(failed_criteria) == 0 and dsr_pass else "FAIL"

    # S15 T0/T5: persist this trial AFTER measurement (для future DSR n_trials accumulation).
    # Guard: only persist when real trades exist (skip CLI smoke tests с mocked extractor returning [] trades).
    # S17 fix: sprint number now configurable via SPRINT_N env var (default 0 = unknown).
    if not math.isnan(aggregate_oos_sharpe) and len(all_trades) > 0:
        sprint_num = int(os.environ.get("SPRINT_N", "0"))
        trial_log.append_trial(sprint=sprint_num, oos_sharpe=aggregate_oos_sharpe)

    print(json.dumps({
        "symbols": symbols,
        "per_symbol": per_symbol_summary,
        "verdict": verdict,
        "failed_criteria": failed_criteria,
        "dsr": _nan_or_value(dsr_value),
        "dsr_pass": dsr_pass,
        "n_trials": n_trials,
        "sigma_sr_cross_trial": sigma_sr_value,
        "trial_log_state": {
            "pre_existing_sharpes": pre_existing_sharpes,
            "this_run_aggregate_sharpe": aggregate_oos_sharpe,
        },
        "metrics": {
            "t1_sharpe_oos": _nan_or_value(metrics["t1_sharpe_oos"]),
            "t2_sortino_oos": _nan_or_value(metrics["t2_sortino_oos"]),
            "t3_max_drawdown": _nan_or_value(metrics["t3_max_drawdown"]),
            "t4_win_rate": _nan_or_value(metrics["t4_win_rate"]),
            "t4_avg_rr": _nan_or_value(metrics["t4_avg_rr"]),
            "t5_mean_pnl_pct": _nan_or_value(metrics["t5_mean_pnl_pct"]),
            "t5_t_stat": _nan_or_value(metrics["t5_t_stat"]),
            "t5_n_trades": metrics["t5_n_trades"],
            "t6_oos_is_sharpe_ratio_mean": _nan_or_value(metrics["t6_oos_is_sharpe_ratio_mean"]),
        },
        "total_k_folds": len(all_fold_sharpes),
        "mc_p_value_aggregate": mc_p,
        "acceptance_gate": gate,
    }, default=str, indent=2))

    return 0 if verdict == "PASS" else 2


def _cmd_monitor(args: argparse.Namespace) -> int:
    """Read-only state snapshot: FSM state + halt + recent trades.

    Per S11 cross-cutting concern C2: STRICTLY read-only (no SQL writes —
    SQLite WAL contention с live bot).

    Subcommand: python -m src monitor --symbol BTCUSDT
    """
    from typing import Any as _Any

    settings = Settings()
    symbol: str = args.symbol or "BTCUSDT"

    # Read-only sqlite connection (no writes possible at SQLite level)
    db_uri = f"file:{settings.db_path}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    try:
        # Current state
        # NOTE: `last_event` is NOT a column in execution_state schema — it's a concept
        # passed via Coordinator to halt_log.context_json. Read it from latest halt_log entry
        # if needed. Bug fix post-S12 ship: original query referenced nonexistent column.
        state_row = conn.execute(
            "SELECT symbol, state, halt_reason, last_reconcile_at, updated_at "
            "FROM execution_state WHERE symbol = ?",
            (symbol,),
        ).fetchone()

        # Recent trades (last 10)
        trade_rows = conn.execute(
            "SELECT trade_id, exit_ts, pnl_pct, reason_code "
            "FROM trade_history WHERE symbol = ? ORDER BY exit_ts DESC LIMIT 10",
            (symbol,),
        ).fetchall()

        # Recent halts (last 5) — table may not exist в old DBs
        import contextlib

        halt_rows: list[tuple[_Any, ...]] = []
        with contextlib.suppress(sqlite3.OperationalError):
            halt_rows = conn.execute(
                "SELECT halt_ts, halt_reason, context FROM halt_log "
                "ORDER BY halt_ts DESC LIMIT 5"
            ).fetchall()

        import json

        snapshot = {
            "symbol": symbol,
            "state": {
                "current_state": state_row[1] if state_row else "MISSING",
                "halt_reason": state_row[2] if state_row else None,
                "last_reconcile_at": state_row[3] if state_row else None,
                "updated_at": state_row[4] if state_row else None,
            },
            "recent_trades": [
                {"trade_id": r[0], "exit_ts": r[1], "pnl_pct": r[2], "reason_code": r[3]}
                for r in trade_rows
            ],
            "recent_halts": [
                {"halt_ts": r[0], "halt_reason": r[1], "context": r[2]}
                for r in halt_rows
            ],
        }

        print(json.dumps(snapshot, default=str, indent=2))
        return 0
    finally:
        conn.close()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src", description="AI Trading Bot v0.1 — live runtime CLI (ADR 0022).")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Start RuntimeManager (blocking).")
    p_run.add_argument("--symbol", default="BTCUSDT")
    p_run.set_defaults(func=_cmd_run)

    p_bf = sub.add_parser("backfill", help="OHLCV backfill.")
    p_bf.add_argument("--symbol", default="BTCUSDT", help="Trading pair (single, default: BTCUSDT)")
    p_bf.add_argument(
        "--symbols", default=None,
        help="Comma-separated trading pairs for multi-symbol backfill (S15 ADR 0030). "
             "Overrides --symbol when set, e.g. --symbols BTCUSDT,ETHUSDT,SOLUSDT",
    )
    p_bf.add_argument(
        "--interval", default="60",
        choices=["5", "15", "30", "60", "120", "240", "D"],
        help="Bar interval (S19 ADR 0034): '60' = 1H (default), '15' = 15M.",
    )
    p_bf.add_argument("--from", dest="from_date", required=True, help="Start date YYYY-MM-DD")
    p_bf.add_argument("--to", dest="to_date", required=True, help="End date YYYY-MM-DD")
    p_bf.add_argument(
        "--output", dest="output_path", default=None,
        help="Output Parquet path (default: data/<symbol>_<interval>.parquet). Ignored when --symbols set."
    )
    p_bf.set_defaults(func=_cmd_backfill)

    p_rec = sub.add_parser("reconcile-only", help="Bootstrap + reconcile, no trading loop.")
    p_rec.add_argument("--symbol", default="BTCUSDT")
    p_rec.set_defaults(func=_cmd_reconcile_only)

    p_kill = sub.add_parser("kill", help="Write .kill_switch sentinel and exit.")
    p_kill.set_defaults(func=_cmd_kill)

    p_wfa = sub.add_parser("wfa", help="Run Walk-Forward Analysis + report.")
    p_wfa.add_argument("--symbol", default="BTCUSDT", help="Single symbol (default: BTCUSDT)")
    p_wfa.add_argument(
        "--symbols", default=None,
        help="Comma-separated symbols for multi-symbol aggregated WFA (S15 ADR 0030). "
             "Overrides --symbol when set, e.g. --symbols BTCUSDT,ETHUSDT,SOLUSDT",
    )
    p_wfa.add_argument(
        "--interval", default="60",
        choices=["5", "15", "30", "60", "120", "240", "D"],
        help="Bar interval (S19 ADR 0034): '60' = 1H (default, bars_per_year=8760), "
             "'15' = 15M (bars_per_year=35040). Annualization factor derived correctly "
             "к prevent 2× Sharpe understimate per Condition A3.",
    )
    p_wfa.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    p_wfa.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    # S33 T4 (CC6 (b) consensus per consilium): WFA window override для 4H multi-symbol.
    # Default ADR 0014: train=2000/test=500/k_folds=5/embargo=20.
    # CC6 (b): 4H requires train=1000/test=250 (~3.3y OOS, OOS/IS ratio preserved 0.25).
    p_wfa.add_argument("--wfa-train", type=int, default=2000, help="WFA train window bars (ADR 0014 default 2000)")
    p_wfa.add_argument("--wfa-test", type=int, default=500, help="WFA test window bars (ADR 0014 default 500)")
    p_wfa.add_argument("--wfa-folds", type=int, default=5, help="WFA K-folds (ADR 0014 default 5)")
    p_wfa.add_argument("--wfa-embargo", type=int, default=20, help="WFA embargo bars (ADR 0014 default 20)")
    p_wfa.set_defaults(func=_cmd_wfa)

    p_mon = sub.add_parser("monitor", help="Read-only state snapshot (FSM + trades + halts).")
    p_mon.add_argument("--symbol", default="BTCUSDT")
    p_mon.set_defaults(func=_cmd_monitor)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
