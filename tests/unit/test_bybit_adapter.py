"""Tests for BybitMarketAdapter.place_order (ADR 0020 sub-decision 1)."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from src.execution.bybit.adapter import BybitAPIError, BybitMarketAdapter, OrderAck
from src.execution.bybit.errors import ReasonCode
from src.marketdata.filters import BybitFilters, FilterViolation

_FILTERS = BybitFilters(
    symbol="BTCUSDT",
    step_size=Decimal("0.000001"),
    tick_size=Decimal("0.01"),
    min_order_qty=Decimal("0.000048"),
    max_order_qty=Decimal("71.73956243"),
    min_order_amt=Decimal("1"),
)


def _rest_ok_place() -> MagicMock:
    r = MagicMock()
    r._http.place_order.return_value = {
        "retCode": 0,
        "result": {"orderId": "EX-12345", "orderLinkId": "CID-abc"},
    }
    return r


def test_place_order_buy_returns_ack() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    ack = adapter.place_order(
        symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"), order_link_id="CID-abc"
    )
    assert isinstance(ack, OrderAck)
    assert ack.order_id == "EX-12345"
    assert ack.order_link_id == "CID-abc"


def test_place_order_sell_passes_side_to_api() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    adapter.place_order(
        symbol="BTCUSDT", side="Sell", qty=Decimal("0.001"), order_link_id="CID-sell"
    )
    _, kwargs = rest._http.place_order.call_args
    assert kwargs["category"] == "spot"
    assert kwargs["symbol"] == "BTCUSDT"
    assert kwargs["side"] == "Sell"
    assert kwargs["orderType"] == "Market"
    assert kwargs["marketUnit"] == "baseCoin"
    assert isinstance(kwargs["qty"], str)


def test_filter_violation_rejected_before_api_call() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    with pytest.raises(FilterViolation, match="qty"):
        adapter.place_order(symbol="BTCUSDT", side="Buy", qty=Decimal("0.00001"))
    rest._http.place_order.assert_not_called()


def test_api_error_mapped_to_reason_code() -> None:
    rest = MagicMock()
    rest._http.place_order.return_value = {
        "retCode": 110007,
        "retMsg": "insufficient balance",
        "result": {},
    }
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    with pytest.raises(BybitAPIError) as exc:
        adapter.place_order(
            symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"), order_link_id="CID-poor"
        )
    assert exc.value.reason is ReasonCode.INSUFFICIENT_BALANCE
    assert exc.value.ret_code == 110007


# --- S55 BYBIT-03: unify BybitAPIError hierarchy + map rest-exhaustion .reason ---
#
# adapter.place_order delegates the REST call to _retry_with_backoff. On a sustained
# order-frequency rate-limit (170005/170222), _retry_with_backoff EXHAUSTS its retries
# and raises src.marketdata.bybit.rest.BybitAPIError — a SEPARATE class that has no
# `.reason`. coordinator.flatten catches the ADAPTER BybitAPIError, so the rest-class
# escaped uncaught → no .reason → 110072 short-circuit unreachable → generic Exception
# path → False → double-sell (BYBIT-02). Fix: adapter re-wraps every rest-exhaustion
# into adapter.BybitAPIError WITH a mapped .reason, and the adapter class subclasses
# the rest class so a single `except` covers both.

from src.marketdata.bybit.rest import BybitAPIError as RestBybitAPIError  # noqa: E402


def test_adapter_bybit_api_error_subclasses_rest_bybit_api_error() -> None:
    """Unified hierarchy: catching the rest base class also catches the adapter class."""
    assert issubclass(BybitAPIError, RestBybitAPIError)


def test_place_order_rest_exhaustion_rewrapped_with_reason() -> None:
    """Sustained 170222 → _retry_with_backoff exhausts → adapter re-raises its OWN
    BybitAPIError WITH .reason set (RATE_LIMIT_HIT), not the bare rest class."""
    rest = MagicMock()
    rest._http.place_order.return_value = {
        "retCode": 170222,
        "retMsg": "order count limit",
        "result": {},
    }
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    with pytest.raises(BybitAPIError) as exc:
        adapter.place_order(
            symbol="BTCUSDT", side="Sell", qty=Decimal("0.001"), order_link_id="CID-rl"
        )
    # Must be the ADAPTER class (has .reason), not the rest class.
    assert isinstance(exc.value, BybitAPIError)
    assert exc.value.reason is ReasonCode.RATE_LIMIT_HIT
    assert exc.value.ret_code == 170222


def test_place_order_rest_exhaustion_170005_rewrapped() -> None:
    """170005 (order frequency limit) exhaustion is likewise re-wrapped with .reason."""
    rest = MagicMock()
    rest._http.place_order.return_value = {
        "retCode": 170005,
        "retMsg": "order frequency limit",
        "result": {},
    }
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    with pytest.raises(BybitAPIError) as exc:
        adapter.place_order(
            symbol="BTCUSDT", side="Sell", qty=Decimal("0.001"), order_link_id="CID-rl2"
        )
    assert exc.value.reason is ReasonCode.RATE_LIMIT_HIT


def test_place_limit_order_rest_exhaustion_rewrapped() -> None:
    rest = MagicMock()
    rest._http.place_order.return_value = {
        "retCode": 170222,
        "retMsg": "order count limit",
        "result": {},
    }
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    with pytest.raises(BybitAPIError) as exc:
        adapter.place_limit_order(
            symbol="BTCUSDT",
            side="Sell",
            qty=Decimal("0.001"),
            price=Decimal("65000"),
            order_link_id="CID-tp",
        )
    assert exc.value.reason is ReasonCode.RATE_LIMIT_HIT


def test_place_stop_market_order_rest_exhaustion_rewrapped() -> None:
    rest = MagicMock()
    rest._http.place_order.return_value = {
        "retCode": 170222,
        "retMsg": "order count limit",
        "result": {},
    }
    adapter = BybitMarketAdapter(rest=rest, filters=_FILTERS)
    with pytest.raises(BybitAPIError) as exc:
        adapter.place_stop_market_order(
            symbol="BTCUSDT",
            side="Sell",
            qty=Decimal("0.001"),
            trigger_price=Decimal("64000"),
            order_link_id="CID-sl",
        )
    assert exc.value.reason is ReasonCode.RATE_LIMIT_HIT


# --- S55 ARCH-03: public step_size / min_order_qty accessors (no _filters leak) ---


def test_adapter_step_size_property_exposes_filter_step() -> None:
    """ARCH-03: Coordinator._qty_step must read a PUBLIC step_size property, not the
    private _adapter._filters.step_size attribute (encapsulation leak across modules)."""
    adapter = BybitMarketAdapter(rest=MagicMock(), filters=_FILTERS)
    assert adapter.step_size == _FILTERS.step_size
    assert adapter.step_size == Decimal("0.000001")


def test_adapter_min_order_qty_property_exposes_filter_min() -> None:
    """ARCH-03/BYBIT-05: residual-flatten dust detection needs the venue min_order_qty
    via a public accessor, not a private _filters attribute reach-in."""
    adapter = BybitMarketAdapter(rest=MagicMock(), filters=_FILTERS)
    assert adapter.min_order_qty == _FILTERS.min_order_qty
    assert adapter.min_order_qty == Decimal("0.000048")
