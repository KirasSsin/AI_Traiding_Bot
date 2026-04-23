"""Bybit V5 private WebSocket consumer — order + wallet topics.

ADR 0021 sub-decision 6. Execution topic deferred to S8.
"""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class _CoordinatorProto(Protocol):
    def on_order_event(self, evt: dict) -> None: ...
    def on_ws_reconnect(self) -> None: ...


class _ReconcilerProto(Protocol):
    def on_wallet_event(self, evt: dict) -> None: ...


class BybitPrivateWSConsumer:
    """Subscribes to `order` + `wallet` topics on Bybit V5 private stream."""

    _FILLED_STATUSES = ("Filled", "PartiallyFilled")
    _REQUIRED_FEE_FIELDS = ("cumExecFee", "feeCurrency")

    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        endpoint: str,
        coordinator: _CoordinatorProto,
        reconciler: _ReconcilerProto,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._endpoint = endpoint
        self._coordinator = coordinator
        self._reconciler = reconciler
        self._ws = None  # pybit WebSocket handle (lazy)

    def start(self) -> None:
        """Connect + subscribe (pybit handles async threading internally)."""
        from pybit.unified_trading import WebSocket  # deferred import
        self._ws = WebSocket(
            testnet="testnet" in self._endpoint,
            demo="demo" in self._endpoint,
            channel_type="private",
            api_key=self._api_key,
            api_secret=self._api_secret,
        )
        self._ws.order_stream(callback=self._on_order_raw)
        self._ws.wallet_stream(callback=self._on_wallet_raw)

    def stop(self) -> None:
        if self._ws is not None:
            self._ws.exit()
            self._ws = None

    def on_disconnect(self) -> None:
        """Callback triggered by pybit on disconnect — routes reconcile."""
        try:
            self._coordinator.on_ws_reconnect()
        except Exception:
            logger.exception("on_ws_reconnect hook failed")

    def _on_order_raw(self, msg: dict) -> None:
        try:
            for item in msg.get("data", []):
                evt = self._parse_order(item)
                if evt is None:
                    continue  # dropped (logged in parser)
                self._coordinator.on_order_event(evt)
        except Exception:
            logger.exception("order event dispatch failed; dropping msg=%r", msg)

    def _on_wallet_raw(self, msg: dict) -> None:
        try:
            for item in msg.get("data", []):
                for coin_row in item.get("coin", []):
                    evt = {"coin": coin_row["coin"], "walletBalance": coin_row["walletBalance"]}
                    self._reconciler.on_wallet_event(evt)
        except Exception:
            logger.exception("wallet event dispatch failed; dropping msg=%r", msg)

    def _parse_order(self, item: dict) -> dict | None:
        status = item.get("orderStatus", "")
        if status in self._FILLED_STATUSES:
            missing = [f for f in self._REQUIRED_FEE_FIELDS if f not in item]
            if missing:
                logger.error(
                    "order event %s missing required fee fields %s; dropping item=%r",
                    status, missing, item,
                )
                return None
        return dict(item)
