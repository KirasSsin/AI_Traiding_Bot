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
from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy


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
    repo = ExecutionStateRepo(conn)
    reconciler = Reconciler(query=adapter, base_coin=base_coin, symbol=symbol)
    coordinator = Coordinator(
        adapter=adapter,
        repo=repo,
        reconciler=reconciler,
        symbol=symbol,
        base_coin=base_coin,
    )

    # Strategy + risk manager
    strategy = EmaCrossoverAdxRsiStrategy(
        symbol=symbol,
        ema_fast=settings.strategy_ema_fast,
        ema_slow=settings.strategy_ema_slow,
        adx_period=settings.strategy_adx_period,
        adx_threshold=settings.strategy_adx_threshold,
        rsi_period=settings.strategy_rsi_period,
        rsi_oversold=settings.strategy_rsi_oversold,
        rsi_overbought=settings.strategy_rsi_overbought,
        atr_period=settings.strategy_atr_period,
    )
    risk_manager = RiskManager(conn=conn, settings=settings)

    # Bar source + WS consumer (FillRecorder = production adapter, S12 T1)
    bar_source = BarSource(adapter=rest, symbol=symbol, interval="60")
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


def _cmd_backfill(args: argparse.Namespace) -> int:
    """Backfill OHLCV via BybitRESTClient.get_klines + write Parquet.

    S13 T2 per ADR 0028 Q3 (Bybit Spot only, no Binance fallback per ADR 0016).
    Closes S8a T20 STUB delegate placeholder.

    Args:
        args.symbol: trading pair (e.g. "BTCUSDT")
        args.from_date: ISO date "YYYY-MM-DD"
        args.to_date: ISO date "YYYY-MM-DD"
        args.output_path: Parquet output (default: data/<symbol>_1h.parquet)

    Returns:
        0 — Parquet written with >0 bars;
        1 — empty kline response (data not available for requested range).
    """
    from datetime import UTC, datetime

    settings = Settings()
    symbol: str = args.symbol or "BTCUSDT"
    output_path = Path(args.output_path) if args.output_path else Path(f"data/{symbol}_1h.parquet")

    start_dt = datetime.fromisoformat(args.from_date).replace(tzinfo=UTC)
    end_dt = datetime.fromisoformat(args.to_date).replace(tzinfo=UTC)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    rest = BybitRESTClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.testnet,
    )

    print(f"backfill: fetching {symbol} 1H {args.from_date} → {args.to_date} ...", flush=True)
    bars = rest.get_klines(symbol, "60", start_ms, end_ms, limit_per_call=1000)

    if not bars:
        print(
            f"backfill: WARNING — empty kline response for {symbol} "
            f"{args.from_date} → {args.to_date}",
            flush=True,
        )
        return 1

    # Convert list[Bar] → DataFrame (schema compatible with data_collector.load_market_data)
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

    # S13 T2 data-integrity fix: explicit snappy + atomic tmp-rename
    # (a) ADR 0003 mandates snappy — explicit args defend against pyarrow→fastparquet engine switch
    # (b) Atomic write: tmp + Path.rename() — prevents partial file on crash during ~5min backfill
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    df.to_parquet(tmp_path, index=False, compression="snappy", engine="pyarrow")
    tmp_path.rename(output_path)

    print(f"backfill: wrote {len(df)} bars to {output_path}", flush=True)
    return 0


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
    repo = ExecutionStateRepo(conn)
    reconciler = Reconciler(query=adapter, base_coin=base_coin, symbol=symbol)
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


def _load_ohlcv(*, symbol: str, start: str, end: str) -> pd.DataFrame:
    """Load OHLCV from Parquet via data_collector.

    S12 T2: closes S11 stub. Reuses existing data_collector pipeline.
    Operator must run `python -m src backfill --symbol <X>` to populate Parquet first.

    S13 T4 (CC4): pre-flight NaN assertion — `df.dropna()` post-warmup must yield
    >=90% bars else WFA aborts with explicit error.
    """
    parquet_path = f"data/{symbol}_1h.parquet"
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


def _cmd_wfa(args: argparse.Namespace) -> int:
    """Run Walk-Forward Analysis + report.

    Subcommand: python -m src wfa --symbol BTCUSDT --start 2024-01-01 --end 2024-04-01

    Wires S10 WFA orchestrator (WindowSplitter + WalkForwardRunner + sign_flip_p_value
    + evaluate_acceptance_gate + format_wfa_report) с stub OHLCV loader (S12 integrates
    real data path).

    Returns:
        0 — gate passed (Sharpe AND MC <= thresholds);
        2 — gate failed;
        1 — error (empty data, etc.).
    """
    settings = Settings()  # noqa: F841 — reserved для future settings-driven WFA params
    symbol: str = args.symbol or "BTCUSDT"

    df = _load_ohlcv(symbol=symbol, start=args.start, end=args.end)
    if df.empty:
        print("WARNING: OHLCV loader returned empty (S12 integrates real data path)", flush=True)
        return 1

    splitter = WindowSplitter()  # ADR 0014 defaults
    runner = WalkForwardRunner(splitter=splitter, replay_fn=run_replay)
    config = {
        "trading": {
            "initial_balance": 10000.0,
            "commission_taker": 0.001,
            "slippage": 0.0005,
            "position_size_pct": 10.0,
            "max_drawdown_pct": 50.0,
            "long_only": True,
        },
        "strategy": {"indicators": {"atr": {"sl_atr_mult": 1.5, "tp_atr_mult": 3.0}}},
    }
    runner_result = runner.run(df=df, config=config)

    # MC sign-flip on aggregated OOS returns
    oos_trades = runner_result["aggregate"]["oos_trades_df"]
    if oos_trades.empty:
        mc_p = 1.0
    else:
        import numpy as np
        raw = oos_trades["net_pnl"].astype(float).to_numpy()
        returns_arr = np.asarray(raw, dtype=float) / 10000.0
        mc_p = sign_flip_p_value(returns_arr, n_iterations=2000, seed=42)

    # S13 T5: Per-fold trade extraction (closes S10/S12 carry-over)
    # replay_engine emits timestamp_open/timestamp_close — normalize to extractor contract.
    from src.risk.trade_history import TradeRecord as _TradeRecord
    all_trades: list[_TradeRecord] = []
    fold_oos_is_sharpe_ratios: list[float] = []
    for fold_data in runner_result["folds"]:
        fold_oos_is_sharpe_ratios.append(fold_data["oos_is_sharpe_ratio"])
        fold_trades_df = fold_data.get("oos_trades_df")
        if fold_trades_df is not None and not fold_trades_df.empty:
            # Normalize replay_engine column names → extract_trade_records contract
            df_normalized = fold_trades_df.copy()
            if "timestamp_open" in df_normalized.columns and "entry_ts" not in df_normalized.columns:
                df_normalized = df_normalized.rename(columns={
                    "timestamp_open": "entry_ts",
                    "timestamp_close": "exit_ts",
                })
            # replay_engine timestamps are tz-naive; TradeRecord requires tz-aware (UTC)
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
            all_trades.extend(extract_trade_records(df_normalized, symbol=symbol))

    # S13 Q5 + CC1: DSR active S13 (N_trials=1, formula-invariant)
    dsr_value = compute_dsr(trades=all_trades, n_trials=1)

    # S13 T6: T1-T6 metrics
    metrics = compute_t1_t6_metrics(
        trades=all_trades,
        fold_oos_is_sharpe=fold_oos_is_sharpe_ratios,
    )

    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_oos_is_sharpe_ratios,
        mc_p_value=mc_p,
    )

    format_wfa_report(
        runner_result=runner_result,
        trades_for_dsr=all_trades,
        mc_p_value=mc_p,
        gate_result=gate,
    )

    import json
    import math

    def _nan_or_value(v: object) -> object:
        return None if (isinstance(v, float) and math.isnan(v)) else v

    # S13 T7: Verdict report (per Q7 ESC-1=c defer pattern — PASS/FAIL only, no pre-commit)
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

    # Q7 ESC-1=c defer pattern: report only, operator decides at S15
    verdict = "PASS" if len(failed_criteria) == 0 and dsr_pass else "FAIL"

    print(json.dumps({
        "symbol": symbol,
        "verdict": verdict,
        "failed_criteria": failed_criteria,
        "dsr": _nan_or_value(dsr_value),
        "dsr_pass": dsr_pass,
        "n_trials": 1,
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
        "k_folds": len(fold_oos_is_sharpe_ratios),
        "mc_p_value": mc_p,
        "acceptance_gate": gate,
    }, default=str, indent=2))

    # Exit codes per ADR 0028 Q7 defer pattern: 0 = PASS, 2 = FAIL
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
    p_bf.add_argument("--symbol", default="BTCUSDT", help="Trading pair (default: BTCUSDT)")
    p_bf.add_argument("--from", dest="from_date", required=True, help="Start date YYYY-MM-DD")
    p_bf.add_argument("--to", dest="to_date", required=True, help="End date YYYY-MM-DD")
    p_bf.add_argument(
        "--output", dest="output_path", default=None,
        help="Output Parquet path (default: data/<symbol>_1h.parquet)"
    )
    p_bf.set_defaults(func=_cmd_backfill)

    p_rec = sub.add_parser("reconcile-only", help="Bootstrap + reconcile, no trading loop.")
    p_rec.add_argument("--symbol", default="BTCUSDT")
    p_rec.set_defaults(func=_cmd_reconcile_only)

    p_kill = sub.add_parser("kill", help="Write .kill_switch sentinel and exit.")
    p_kill.set_defaults(func=_cmd_kill)

    p_wfa = sub.add_parser("wfa", help="Run Walk-Forward Analysis + report.")
    p_wfa.add_argument("--symbol", default="BTCUSDT")
    p_wfa.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    p_wfa.add_argument("--end", required=True, help="End date YYYY-MM-DD")
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
