"""Integration: real bootstrap with Bybit Demo after simulated crash.

Opt-in: only runs with RUN_DEMO=1 + BYBIT_DEMO_API_KEY / BYBIT_DEMO_API_SECRET set.

Manual procedure:
1. Set environment: RUN_DEMO=1 BYBIT_DEMO_API_KEY=<key> BYBIT_DEMO_API_SECRET=<secret>
2. Run: pytest tests/integration/test_bootstrap_demo.py -v -m integration
3. The test places a real MARKET Buy on Bybit Demo (BTC/USDT, ~$6 notional).
4. It writes ENTRY_PENDING to DB (simulating a crash mid-execution).
5. Coordinator.bootstrap() reconciles the position via HEAL_ENTRY_FILLED.
6. Asserts FSM reaches LONG_OPEN (no halt).
7. Cleanup: coordinator.flatten() to close the position.

API drift notes vs plan draft (2026-04-24):
- BybitMarketAdapter.__init__ takes rest= and filters=, NOT api_key/api_secret/endpoint.
  Use pybit.unified_trading.HTTP + _RestShim pattern from test_demo_bracket_happy_path.py.
- ExecutionStateRepo.__init__ takes conn: sqlite3.Connection, NOT db_path.
  Use init_db + connect (or raw sqlite3.connect + manual schema) pattern.
- Reconciler does NOT accept settings= kwarg; use heal_max_age_seconds= directly.
- Coordinator does NOT accept settings= kwarg.
- repo.upsert_initial / repo.update do not exist; use repo.upsert(ExecutionStateRow(...)).
"""
from __future__ import annotations

import os
from decimal import Decimal

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DEMO") != "1",
        reason="Demo integration test opt-in via RUN_DEMO=1",
    ),
    pytest.mark.skipif(
        not os.getenv("BYBIT_DEMO_API_KEY") or not os.getenv("BYBIT_DEMO_API_SECRET"),
        reason="BYBIT_DEMO_API_KEY / BYBIT_DEMO_API_SECRET required",
    ),
]

_SYMBOL = "BTCUSDT"
_BASE_COIN = "BTC"
# Small qty: ~$6 notional at BTC ~$60k; above min_order_amt=$5
_ENTRY_QTY = Decimal("0.0001")


def test_bootstrap_heal_after_simulated_crash(tmp_path):
    """Flow:
    1. Build real Bybit Demo adapter + Reconciler + Coordinator.
    2. Place entry MARKET Buy on Demo for small qty (0.0001 BTC).
    3. Simulate crash: write ENTRY_PENDING row to DB (adapter placed order, FSM not updated).
    4. Coordinator.bootstrap() → reconciler detects Filled entry → HEAL_ENTRY_FILLED.
    5. FSM moves to LONG_OPEN.
    6. Assert no halt.
    7. Cleanup: flatten position.
    """
    import sqlite3
    from datetime import UTC, datetime

    # All imports inside test body so collection never fails when libs absent.
    try:
        from pybit.unified_trading import HTTP
    except ImportError:
        pytest.skip("pybit not installed; cannot run demo test")

    from src.execution.bybit.adapter import BybitMarketAdapter
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.execution.state_machine import ExecutionState
    from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
    from src.marketdata.filters import BybitFilters

    api_key = os.environ["BYBIT_DEMO_API_KEY"]
    api_secret = os.environ["BYBIT_DEMO_API_SECRET"]

    # Step 1 — build adapter (Bybit Demo endpoint, NOT testnet)
    http = HTTP(
        testnet=False,
        demo=True,
        api_key=api_key,
        api_secret=api_secret,
    )

    class _RestShim:
        def __init__(self, h):
            self._http = h

    rest = _RestShim(http)
    # TODO: fetch live filters via http.get_instruments_info if tick_size changes
    filters = BybitFilters(
        symbol=_SYMBOL,
        step_size=Decimal("0.000001"),
        tick_size=Decimal("0.01"),
        min_order_qty=Decimal("0.000048"),
        max_order_qty=Decimal("71.7"),
        min_order_amt=Decimal("5"),
    )
    adapter = BybitMarketAdapter(rest=rest, filters=filters)

    # Step 2 — repo via raw sqlite3 (avoid init_db migration dep in opt-in test)
    conn = sqlite3.connect(str(tmp_path / "demo.db"))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_state (
            symbol TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            position_qty TEXT NOT NULL,
            entry_price TEXT,
            oco_main_order_id TEXT,
            bracket_id TEXT,
            oco_tp_order_id TEXT,
            oco_sl_order_id TEXT,
            expected_oco_qty TEXT,
            arming_started_at TEXT,
            last_attempt_num INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            halt_reason TEXT,
            last_exit_reason TEXT,
            last_reconcile_at TEXT,
            bootstrap_at TEXT
        )
    """)
    conn.commit()
    repo = ExecutionStateRepo(conn=conn)

    reconciler = Reconciler(
        adapter=adapter,
        base_coin=_BASE_COIN,
        symbol=_SYMBOL,
        heal_max_age_seconds=3600,
    )
    coord = Coordinator(
        adapter=adapter,
        repo=repo,
        reconciler=reconciler,
        symbol=_SYMBOL,
        base_coin=_BASE_COIN,
    )

    # Step 3 — place real entry order on Demo
    # TODO: adapter.place_order returns OrderAck; adapt if method name differs
    ack = adapter.place_order(
        symbol=_SYMBOL,
        side="Buy",
        qty=_ENTRY_QTY,
        order_link_id=f"bootstrap-demo-test-{int(datetime.now(tz=UTC).timestamp())}",
    )
    entry_order_id = ack.order_id

    # Step 4 — simulate crash: write ENTRY_PENDING to DB (as if crash after place but before fill)
    now_iso = datetime.now(tz=UTC).isoformat()
    repo.upsert(ExecutionStateRow(
        symbol=_SYMBOL,
        state=ExecutionState.ENTRY_PENDING,
        position_qty=Decimal("0"),
        entry_price=None,
        oco_main_order_id=entry_order_id,
        bracket_id="testbrac",
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=_ENTRY_QTY,
        arming_started_at=None,
        last_attempt_num=0,
        updated_at=now_iso,
    ))

    # Step 5 — bootstrap (reconcile path: HEAL_ENTRY_FILLED expected)
    coord.bootstrap()

    # Step 6 — assert FSM reached LONG_OPEN (no halt)
    row = repo.get(_SYMBOL)
    assert row is not None
    assert row.halt_reason is None, f"unexpected halt: {row.halt_reason}"
    assert row.state == ExecutionState.LONG_OPEN, (
        f"expected LONG_OPEN after HEAL_ENTRY_FILLED, got {row.state!r}"
    )

    # Step 7 — cleanup: flatten position
    # TODO: verify flatten() method signature in Coordinator for v0.1 scope
    try:
        coord.flatten(reason="EXIT_TEST_CLEANUP")
    except Exception as exc:
        pytest.fail(f"cleanup flatten failed: {exc}")

    conn.close()
