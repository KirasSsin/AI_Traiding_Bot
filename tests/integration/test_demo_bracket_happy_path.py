"""ADR 0020 G14: Demo-as-proxy for Bybit V5 mainnet behavior.

Opt-in: set RUN_DEMO=1 + provide .env.demo with Bybit Demo API keys.
Default: SKIPPED (pytest_collection_modifyitems in tests/conftest.py).

Scenario: entry MARKET Buy (~$10 notional) → LONG_OPEN → arm OCO with far-from-market
TP/SL (won't fill) → OCO_ARMED → cancel both legs → flatten residual → FLAT.

API drift notes vs plan draft (2026-04-23):
- ExecutionStateRepo.__init__ takes conn: sqlite3.Connection, NOT db_path=str.
  We create the sqlite3 connection explicitly here.
- Settings has no bybit_demo_mode field; we skip if it can't be loaded cleanly.
- BybitFilters requires tick_size (plan draft omitted); provided here.
- Entry order_id not stored on ExecutionStateRow; reconstructed via make_order_link_id.
"""
from __future__ import annotations

import sqlite3
import time
from decimal import Decimal

import pytest

pytestmark = pytest.mark.demo

_SYMBOL = "BTCUSDT"
_BASE_COIN = "BTC"


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
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
            last_attempt_num INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


@pytest.fixture(scope="module")
def demo_coordinator(tmp_path_factory):
    # Imports inside fixture so collection never fails on missing demo deps.
    from src.execution.bybit.adapter import BybitMarketAdapter
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.execution.state_repo import ExecutionStateRepo
    from src.marketdata.filters import BybitFilters

    # Load settings from .env.demo; skip cleanly if file absent or creds missing.
    try:
        from src.platform.config import Settings
        settings = Settings(_env_file=".env.demo")
    except Exception as exc:
        pytest.skip(f"Cannot load .env.demo: {exc}")

    # Guard: Settings has no bybit_demo_mode field; require explicit opt-in via env file
    # by checking a plain env var so we never accidentally hit mainnet.
    import os
    if os.getenv("BYBIT_DEMO_MODE", "").lower() not in ("1", "true"):
        pytest.skip(
            "Refusing to run: set BYBIT_DEMO_MODE=1 in .env.demo or environment "
            "to confirm this is a Demo (not mainnet) session."
        )

    try:
        from pybit.unified_trading import HTTP
    except ImportError:
        pytest.skip("pybit not installed; cannot run demo test")

    http = HTTP(
        testnet=False,
        demo=True,
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
    )

    # BybitMarketAdapter expects rest._http to be the pybit HTTP client.
    class _RestShim:
        def __init__(self, h):
            self._http = h

    rest = _RestShim(http)

    filters = BybitFilters(
        symbol=_SYMBOL,
        step_size=Decimal("0.000001"),
        tick_size=Decimal("0.01"),
        min_order_qty=Decimal("0.000048"),
        max_order_qty=Decimal("71.7"),
        min_order_amt=Decimal("5"),
    )
    adapter = BybitMarketAdapter(rest=rest, filters=filters)

    db_dir = tmp_path_factory.mktemp("demo")
    conn = sqlite3.connect(str(db_dir / "execution.db"))
    _create_schema(conn)

    repo = ExecutionStateRepo(conn=conn)
    reconciler = Reconciler(
        query=adapter,
        base_coin=_BASE_COIN,
        symbol=_SYMBOL,
    )
    coord = Coordinator(
        adapter=adapter,
        repo=repo,
        reconciler=reconciler,
        symbol=_SYMBOL,
        base_coin=_BASE_COIN,
    )
    yield coord, repo, adapter
    conn.close()


def test_demo_happy_path_entry_arm_cancel_flatten(demo_coordinator):
    """E2E: entry → LONG_OPEN → arm OCO → OCO_ARMED → cancel → flatten → FLAT."""
    from src.execution.bracket import compute_oco_qty, make_order_link_id
    from src.execution.state_machine import ExecutionState
    from src.risk.reason_codes import ReasonCode

    coord, repo, adapter = demo_coordinator

    bracket_id = coord.start_bracket(
        entry_qty=Decimal("0.0002"),
        entry_side="Buy",
        tp_price=Decimal("100000.00"),
        sl_trigger_price=Decimal("30000.00"),
    )

    # Poll for LONG_OPEN (entry filled on exchange).
    for _ in range(20):
        time.sleep(0.5)
        row = repo.get(_SYMBOL)
        if row is not None and row.state == ExecutionState.LONG_OPEN:
            break

    row = repo.get(_SYMBOL)
    assert row is not None and row.state == ExecutionState.LONG_OPEN, (
        f"expected LONG_OPEN, got {row.state if row else 'None'}"
    )

    # Reconstruct entry orderLinkId from bracket_id (attempt=1, role=entry).
    # ExecutionStateRow does not store entry_order_id directly.
    entry_link_id = make_order_link_id(bracket_id=bracket_id, role="entry", attempt=1)

    # Fetch fill details via adapter.get_order (by orderLinkId not orderId).
    # Bybit V5 get_order by orderId is what the adapter exposes; we need the orderId.
    # The coordinator's place_order returns the orderId — it's not stored on the row,
    # so we fall back to get_open_orders / order history to resolve the orderId.
    open_orders = adapter.get_open_orders(symbol=_SYMBOL)
    history = adapter.get_order_history(symbol=_SYMBOL, limit=50)
    all_orders = open_orders + history
    entry_order_id = next(
        (o["orderId"] for o in all_orders if o.get("orderLinkId") == entry_link_id),
        None,
    )
    assert entry_order_id, (
        f"Entry order with orderLinkId={entry_link_id!r} not found in open/history"
    )

    fill = adapter.get_order(symbol=_SYMBOL, order_id=entry_order_id)

    oco_qty = compute_oco_qty(
        cum_exec_qty=fill.cum_exec_qty,
        cum_exec_fee=fill.cum_exec_fee,
        fee_currency=fill.fee_currency,
        base_coin=_BASE_COIN,
        qty_step=Decimal("0.000001"),
    )
    coord.arm_oco(
        tp_price=Decimal("100000.00"),
        sl_trigger_price=Decimal("30000.00"),
        oco_qty=oco_qty,
    )
    assert repo.get(_SYMBOL).state == ExecutionState.OCO_ARMED

    # Cancel OCO legs then flatten residual position.
    coord.flatten(reason=ReasonCode.HALT_RECONCILE_DIVERGENCE)

    for _ in range(20):
        time.sleep(0.5)
        row = repo.get(_SYMBOL)
        if row is not None and row.state == ExecutionState.FLAT:
            break

    assert repo.get(_SYMBOL).state == ExecutionState.FLAT
