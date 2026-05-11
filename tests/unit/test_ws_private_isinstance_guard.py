"""S47 T11 — WS private consumer isinstance guard (M3).

pybit V3 WebSocket may emit `data` as dict (single-event) OR list (multi-event).
Without guard, dict iteration yields keys → silent event-drop.
Guards in _on_order_raw / _on_wallet_raw / _on_execution_raw wrap dict → [dict].
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from src.execution.bybit.ws_private import BybitPrivateWSConsumer


@pytest.fixture
def consumer() -> BybitPrivateWSConsumer:
    """Minimal consumer with mocked dependencies."""
    return BybitPrivateWSConsumer(
        api_key="test",
        api_secret="test",
        endpoint="wss://stream-testnet.bybit.com/v5/private",
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        fill_recorder=MagicMock(),
    )


# --- _on_order_raw ---


def test_on_order_raw_data_as_list(consumer: BybitPrivateWSConsumer) -> None:
    """V5 normal path: list of events dispatches each."""
    consumer._coordinator.on_order_event = MagicMock()
    msg: dict[str, Any] = {
        "data": [{"orderId": "1", "orderStatus": "New"}, {"orderId": "2", "orderStatus": "New"}]
    }
    consumer._on_order_raw(msg)
    assert consumer._coordinator.on_order_event.call_count == 2


def test_on_order_raw_data_as_dict_wrapped(consumer: BybitPrivateWSConsumer) -> None:
    """V3 quirk: single event emitted as dict — must be processed (not dropped)."""
    consumer._coordinator.on_order_event = MagicMock()
    msg: dict[str, Any] = {"data": {"orderId": "single", "orderStatus": "New"}}
    consumer._on_order_raw(msg)
    consumer._coordinator.on_order_event.assert_called_once()
    evt = consumer._coordinator.on_order_event.call_args.args[0]
    assert evt["orderId"] == "single"


def test_on_order_raw_data_missing_no_op(consumer: BybitPrivateWSConsumer) -> None:
    """Missing data key → no dispatch."""
    consumer._coordinator.on_order_event = MagicMock()
    consumer._on_order_raw({})
    consumer._coordinator.on_order_event.assert_not_called()


def test_on_order_raw_data_unexpected_type_skipped(consumer: BybitPrivateWSConsumer) -> None:
    """Unexpected data type (int) → warn + skip, no dispatch."""
    consumer._coordinator.on_order_event = MagicMock()
    consumer._on_order_raw({"data": 42})
    consumer._coordinator.on_order_event.assert_not_called()


# --- _on_execution_raw ---


def test_on_execution_raw_data_as_dict_wrapped(consumer: BybitPrivateWSConsumer) -> None:
    """V3 quirk: single fill emitted as dict — must reach fill_recorder."""
    consumer._fill_recorder.on_fill_event = MagicMock()
    msg: dict[str, Any] = {"topic": "execution", "data": {"execId": "e1", "execQty": "0.5"}}
    consumer._on_execution_raw(msg)
    consumer._fill_recorder.on_fill_event.assert_called_once_with(
        {"execId": "e1", "execQty": "0.5"}
    )


def test_on_execution_raw_data_as_list(consumer: BybitPrivateWSConsumer) -> None:
    """V5 normal path: list of fills dispatches each."""
    consumer._fill_recorder.on_fill_event = MagicMock()
    msg: dict[str, Any] = {"data": [{"execId": "e1"}, {"execId": "e2"}]}
    consumer._on_execution_raw(msg)
    assert consumer._fill_recorder.on_fill_event.call_count == 2


def test_on_execution_raw_data_missing_no_op(consumer: BybitPrivateWSConsumer) -> None:
    consumer._fill_recorder.on_fill_event = MagicMock()
    consumer._on_execution_raw({})
    consumer._fill_recorder.on_fill_event.assert_not_called()


def test_on_execution_raw_data_unexpected_type_skipped(consumer: BybitPrivateWSConsumer) -> None:
    consumer._fill_recorder.on_fill_event = MagicMock()
    consumer._on_execution_raw({"data": "bad"})
    consumer._fill_recorder.on_fill_event.assert_not_called()


# --- _on_wallet_raw ---


def test_on_wallet_raw_data_as_dict_wrapped(consumer: BybitPrivateWSConsumer) -> None:
    """V3 quirk: wallet update emitted as dict — coin rows dispatched."""
    consumer._reconciler.on_wallet_event = MagicMock()
    msg: dict[str, Any] = {
        "data": {"accountType": "UNIFIED", "coin": [{"coin": "BTC", "walletBalance": "0.01"}]}
    }
    consumer._on_wallet_raw(msg)
    consumer._reconciler.on_wallet_event.assert_called_once_with(
        {"coin": "BTC", "walletBalance": "0.01"}
    )


def test_on_wallet_raw_data_missing_no_op(consumer: BybitPrivateWSConsumer) -> None:
    consumer._reconciler.on_wallet_event = MagicMock()
    consumer._on_wallet_raw({})
    consumer._reconciler.on_wallet_event.assert_not_called()
