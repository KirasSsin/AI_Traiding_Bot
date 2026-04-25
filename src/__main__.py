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
import sys
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

from src.execution.bybit.adapter import BybitMarketAdapter
from src.execution.bybit.ws_private import BybitPrivateWSConsumer
from src.execution.coordinator import Coordinator
from src.execution.reconciler import Reconciler
from src.execution.state_repo import ExecutionStateRepo
from src.marketdata.bybit.rest import BybitRESTClient
from src.marketdata.filters import BybitFilters
from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.manager import RiskManager
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
    FillRecorder = MagicMock-equivalent stub (production wiring deferred S12+).

    Returns:
        0 — clean exit;
        130 — KeyboardInterrupt (SIGINT convention);
        1 — runtime crash (unexpected Exception).
    """
    from sqlite3 import Connection
    from typing import Any as _Any

    class _NoopFillRecorder:
        """No-op FillRecorder stub satisfying _FillRecorderProto.

        S11 placeholder — production wiring deferred к S12 (per architecture-reviewer
        T2 concern C2: replace MagicMock anti-pattern с simple class).
        Conforms structurally к src.execution.bybit.ws_private._FillRecorderProto.
        """

        def on_fill_event(self, evt: dict[str, _Any]) -> None:  # noqa: ARG002
            return None

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

    # Bar source + WS consumer (FillRecorder stub — production wiring S12+)
    bar_source = BarSource(adapter=rest, symbol=symbol, interval="60")
    fill_recorder_stub = _NoopFillRecorder()

    endpoint = "demo.bybit.com" if settings.testnet else "stream.bybit.com"
    ws_consumer = BybitPrivateWSConsumer(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        endpoint=endpoint,
        coordinator=coordinator,
        reconciler=reconciler,
        fill_recorder=fill_recorder_stub,
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
    """Delegate to existing backfill script."""
    print(f"backfill --from {args.from_date} --to {args.to_date} (delegate to scripts/backfill.py)")
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


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src", description="AI Trading Bot v0.1 — live runtime CLI (ADR 0022).")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Start RuntimeManager (blocking).")
    p_run.add_argument("--symbol", default="BTCUSDT")
    p_run.set_defaults(func=_cmd_run)

    p_bf = sub.add_parser("backfill", help="OHLCV backfill.")
    p_bf.add_argument("--from", dest="from_date", required=True)
    p_bf.add_argument("--to", dest="to_date", required=True)
    p_bf.set_defaults(func=_cmd_backfill)

    p_rec = sub.add_parser("reconcile-only", help="Bootstrap + reconcile, no trading loop.")
    p_rec.add_argument("--symbol", default="BTCUSDT")
    p_rec.set_defaults(func=_cmd_reconcile_only)

    p_kill = sub.add_parser("kill", help="Write .kill_switch sentinel and exit.")
    p_kill.set_defaults(func=_cmd_kill)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
