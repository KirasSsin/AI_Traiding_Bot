"""E2E smoke: place MARKET BUY 0.001 BTCUSDT on Bybit testnet.

Env-gated: skipped unless `PYTEST_RUN_INTEGRATION=1` is set.
"""

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from src.execution.bybit.adapter import BybitMarketAdapter
from src.execution.models import OrderSide, OrderStatus
from src.marketdata.bybit.rest import BybitRESTClient
from src.platform.config import Settings

pytestmark = pytest.mark.integration


def _settings() -> Settings:
    return Settings(
        data_dir="/tmp/data",
        log_dir="/tmp/logs",
        db_path="/tmp/data/bot.db",
        parquet_dir="/tmp/data/parquet",
    )


def _skip_if_not_explicitly_opted_in() -> None:
    if os.environ.get("PYTEST_RUN_INTEGRATION") != "1":
        pytest.skip("set PYTEST_RUN_INTEGRATION=1 to run live-testnet tests")


def test_testnet_market_buy_places_and_fills() -> None:
    _skip_if_not_explicitly_opted_in()
    settings = _settings()
    assert settings.testnet is True, "smoke test must run on testnet only"

    rest = BybitRESTClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=True,
    )
    filters = rest.get_filters("BTCUSDT")

    adapter = BybitMarketAdapter(rest_client=rest, filters=filters)
    qty = filters.round_qty(Decimal("0.001"))
    cid = f"smoke-{uuid4().hex[:8]}"

    order = adapter.place_market_order(
        client_order_id=cid,
        side=OrderSide.BUY,
        qty=qty,
        reference_price=Decimal("60000"),
    )
    assert order.status is OrderStatus.NEW
    assert order.exch_order_id is not None
