"""BybitPrivateWSConsumer tests (ADR 0021 sub-decision 6)."""
from unittest.mock import MagicMock

import pytest

from src.execution.bybit.ws_private import BybitPrivateWSConsumer


def test_consumer_initializes_with_pybit_handle():
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord,
        reconciler=reco,
    )
    assert c._coordinator is coord
    assert c._reconciler is reco


def test_consumer_on_disconnect_triggers_reconnect_event():
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord, reconciler=reco,
    )
    c.on_disconnect()
    # Reconnect path eventually calls coordinator.on_ws_reconnect
    coord.on_ws_reconnect.assert_called_once()
