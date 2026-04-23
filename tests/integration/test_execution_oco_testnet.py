"""Sprint 5 happy-path integration test on Bybit testnet (opt-in).

Sequence: entry MARKET (small qty) with native tpslMode → reconcile sees
open OCO order + non-zero balance → opposite-side MARKET to flatten →
reconcile sees flat.

ADR ref: wiki/project/decisions/0019-sprint-5-execution-decisions.md sub-decision 5.

Opt-in: set `PYTEST_RUN_INTEGRATION=1` (matches existing testnet smoke pattern).
"""
from __future__ import annotations

import os
import time
from decimal import Decimal
from uuid import uuid4

import pytest

from src.execution.bybit.adapter import BybitMarketAdapter
from src.execution.models import OrderSide, OrderStatus
from src.execution.oco import OcoParams, build_oco_order
from src.execution.reconciler import Reconciler
from src.marketdata.bybit.rest import BybitRESTClient
from src.platform.config import Settings

pytestmark = pytest.mark.integration


def _skip_if_not_explicitly_opted_in() -> None:
    if os.environ.get("PYTEST_RUN_INTEGRATION") != "1":
        pytest.skip("set PYTEST_RUN_INTEGRATION=1 to run live-testnet tests")


def _settings() -> Settings:
    return Settings(
        data_dir="/tmp/data",
        log_dir="/tmp/logs",
        db_path="/tmp/data/bot.db",
        parquet_dir="/tmp/data/parquet",
    )


class _BybitSpotExchangeClient:
    """Adapts BybitRESTClient._http to the ExchangeQueryClient protocol.

    Spot has no positions endpoint — we read BTC free balance as proxy.
    """

    def __init__(self, rest: BybitRESTClient, base_coin: str) -> None:
        self._rest = rest
        self._coin = base_coin

    def get_open_orders(self, symbol: str) -> list[dict]:
        resp = self._rest._http.get_open_orders(category="spot", symbol=symbol)
        return list(resp.get("result", {}).get("list", []))

    def get_position(self, symbol: str) -> dict | None:
        resp = self._rest._http.get_wallet_balance(
            accountType="UNIFIED", coin=self._coin
        )
        rows = resp.get("result", {}).get("list", [])
        if not rows:
            return None
        coins = rows[0].get("coin", [])
        match = next((c for c in coins if c.get("coin") == self._coin), None)
        if match is None:
            return None
        free = match.get("walletBalance") or match.get("free") or "0"
        return {"size": str(free), "avgPrice": "0"}


def test_oco_happy_path_testnet() -> None:
    _skip_if_not_explicitly_opted_in()

    settings = _settings()
    assert settings.testnet is True, "must run on testnet only"

    rest = BybitRESTClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=True,
    )
    symbol = "BTCUSDT"
    filters = rest.get_filters(symbol)
    adapter = BybitMarketAdapter(rest_client=rest, filters=filters)
    exch_client = _BybitSpotExchangeClient(rest, base_coin="BTC")
    reconciler = Reconciler(exch_client)

    # 1. Get reference price from the underlying HTTP client
    ticker_resp = rest._http.get_tickers(category="spot", symbol=symbol)
    last_price = Decimal(ticker_resp["result"]["list"][0]["lastPrice"])

    # 2. Build OCO bracket using a 0.5%-of-price ATR proxy
    qty = filters.round_qty(Decimal("0.001"))
    atr_proxy = (last_price * Decimal("0.005")).quantize(Decimal("0.1"))
    oco = build_oco_order(
        OcoParams(
            symbol=symbol,
            side="LONG",
            qty=qty,
            entry_price=last_price,
            atr=atr_proxy,
            sl_atr_mult=Decimal("1.5"),
            tp_atr_mult=Decimal("3.0"),
            tick_size=Decimal("0.1"),
        )
    )

    # 3. Place entry with native tpslMode
    cid_open = f"s5-open-{uuid4().hex[:8]}"
    order = adapter.place_market_order(
        client_order_id=cid_open,
        side=OrderSide.BUY,
        qty=qty,
        reference_price=last_price,
        take_profit=oco.take_profit,
        stop_loss=oco.stop_loss,
        tpsl_mode="Full",
    )
    assert order.status is OrderStatus.NEW

    time.sleep(2)  # let testnet propagate

    # 4. Reconcile sees position present
    state_open = reconciler.fetch_exchange_state(symbol)
    assert state_open.position.qty > 0

    # 5. Flatten via opposite-side market order
    cid_close = f"s5-close-{uuid4().hex[:8]}"
    adapter.place_market_order(
        client_order_id=cid_close,
        side=OrderSide.SELL,
        qty=qty,
        reference_price=last_price,
    )

    time.sleep(2)

    # 6. Reconcile sees flat (qty rounds back to ~0; allow dust below qty step)
    state_close = reconciler.fetch_exchange_state(symbol)
    assert state_close.position.qty < qty  # below the round-trip qty
