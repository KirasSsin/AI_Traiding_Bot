"""Bybit V5 private WebSocket consumer — order + wallet + execution topics.

ADR 0021 sub-decision 6. Execution topic added in S9 Q3 B1.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class _CoordinatorProto(Protocol):
    def on_order_event(self, evt: dict[str, Any]) -> None: ...
    def on_ws_reconnect(self) -> None: ...


class _ReconcilerProto(Protocol):
    def on_wallet_event(self, evt: dict[str, Any]) -> None: ...


class _FillRecorderProto(Protocol):
    def on_fill_event(self, evt: dict[str, Any]) -> None: ...


class BybitPrivateWSConsumer:
    """Subscribes to `order` + `wallet` + `execution` topics on Bybit V5 private stream.

    Execution topic added в S9 Q3 B1 — pure analytics ingestion (per-fill granularity).
    Production wiring of concrete FillRecorder still pending (`__main__.py::_cmd_run`
    is STUB since S8a — defer к operator-readiness sprint).
    """

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
        fill_recorder: _FillRecorderProto,  # NEW S9 Q3 B1
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._endpoint = endpoint
        self._coordinator = coordinator
        self._reconciler = reconciler
        self._fill_recorder = fill_recorder  # NEW
        self._ws: Any | None = None  # pybit WebSocket handle (lazy, untyped)

    def __repr__(self) -> str:
        """S39 T13 M4 — redact secrets from repr (security hardening)."""
        key_redacted = f"{self._api_key[:4]}***" if self._api_key else "none"
        return (
            f"BybitPrivateWSConsumer(api_key={key_redacted}, "
            f"endpoint={self._endpoint!r}, "
            f"ws_connected={self._ws is not None})"
        )

    def start(self) -> None:
        """Connect + subscribe (pybit handles async threading internally).

        ADR 0021 sub-decision 6 — wire on_disconnect via underlying
        websocket-client `WebSocketApp.on_close`. pybit does NOT expose a
        user-level disconnect callback, so we install ours after pybit has
        instantiated the inner WebSocketApp. If the install path fails (pybit
        layout change), the heartbeat watchdog (`check_alive`) is the backstop.
        """
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
        self._ws.execution_stream(callback=self._on_execution_raw)
        self._install_close_hook()

    def _install_close_hook(self) -> None:
        """Wrap underlying websocket-client `on_close` to fire on_disconnect.

        pybit WebSocket holds an inner `ws` (`WebSocketApp`) per channel.
        Walking the attribute is brittle — wrapped in try/except so a pybit
        upgrade can't crash startup; missing hook is logged + falls back to
        the periodic `check_alive` watchdog.
        """
        try:
            inner = getattr(self._ws, "ws", None)
            if inner is None:
                logger.warning(
                    "ws_private: pybit inner ws missing; relying on check_alive watchdog"
                )
                return
            prev = getattr(inner, "on_close", None)

            def wrapped(ws_app: Any, status_code: int, msg: str) -> None:
                try:
                    self.on_disconnect()
                finally:
                    if callable(prev):
                        prev(ws_app, status_code, msg)

            inner.on_close = wrapped
        except Exception:
            logger.exception("ws_private: failed to install close hook; check_alive only")

    def check_alive(self, *, max_silence_seconds: float = 30.0) -> bool:
        """Heartbeat watchdog — call periodically from a worker loop.

        Backstop for the close-hook path. Returns True if the WS is still
        receiving pings within `max_silence_seconds`; False (and triggers
        on_disconnect) otherwise. Caller decides cadence.
        """
        if self._ws is None:
            return False
        last = getattr(self._ws, "last_ping_time", None)
        if last is None:
            return True  # not yet established a baseline; assume alive
        import time

        if time.time() - float(last) > max_silence_seconds:
            self.on_disconnect(_from_check_alive=True)
            return False
        return True

    def stop(self) -> None:
        if self._ws is not None:
            self._ws.exit()
            self._ws = None

    def on_disconnect(self, *, _from_check_alive: bool = False) -> None:
        """Callback triggered by close-hook OR check_alive — routes reconcile.

        S39 T8 H2 — After triggering coordinator reconnect, re-probe via check_alive
        to verify WS subscription was successfully re-attached. Prevents silent
        dead-WS scenario where reconcile delivers AGREE on stale state.

        Args:
            _from_check_alive: Internal flag to prevent recursion when called
                from check_alive() watchdog. Re-probe only happens when called
                from close-hook (external disconnect event).
        """
        try:
            self._coordinator.on_ws_reconnect()
        except Exception:
            logger.exception("on_ws_reconnect hook failed")

        # S39 T8 H2 — verify subscription re-attached after reconnect
        # Only re-probe when disconnect came from close-hook (not from check_alive watchdog)
        # to avoid recursion: check_alive → on_disconnect → check_alive → ...
        if not _from_check_alive and not self.check_alive():
            logger.warning(
                "ws_private.reconnect.subscription_lost",
                extra={"ws_state": "dead_after_reconnect"},
            )

    def _on_order_raw(self, msg: dict[str, Any]) -> None:
        try:
            data = msg.get("data")
            # S47 T11 M3 — isinstance guard: pybit V3 may emit data as dict (single-event);
            # V5 emits list. Wrap dict → [dict] for uniform iteration. Drop None/other types.
            if data is None:
                return
            if isinstance(data, dict):
                events: list[Any] = [data]
            elif isinstance(data, list):
                events = data
            else:
                logger.warning(
                    "ws.order.shape_mismatch",
                    extra={
                        "expected": "list|dict",
                        "got": type(data).__name__,
                        "topic": msg.get("topic"),
                    },
                )
                return
            for item in events:
                evt = self._parse_order(item)
                if evt is None:
                    continue  # dropped (logged in parser)
                self._coordinator.on_order_event(evt)
        except Exception:
            logger.exception("order event dispatch failed; dropping msg=%r", msg)

    def _on_wallet_raw(self, msg: dict[str, Any]) -> None:
        try:
            data = msg.get("data")
            # S47 T11 M3 — isinstance guard: pybit V3 may emit data as dict (single-event).
            if data is None:
                return
            if isinstance(data, dict):
                events = [data]
            elif isinstance(data, list):
                events = data
            else:
                logger.warning(
                    "ws.wallet.shape_mismatch",
                    extra={
                        "expected": "list|dict",
                        "got": type(data).__name__,
                        "topic": msg.get("topic"),
                    },
                )
                return
            for item in events:
                for coin_row in item.get("coin", []):
                    evt = {"coin": coin_row["coin"], "walletBalance": coin_row["walletBalance"]}
                    self._reconciler.on_wallet_event(evt)
        except Exception:
            logger.exception("wallet event dispatch failed; dropping msg=%r", msg)

    def _on_execution_raw(self, msg: dict[str, Any]) -> None:
        """S9 Q3 B1 — dispatch each fill from Bybit V5 execution topic.

        Mirror of _on_order_raw / _on_wallet_raw exception-swallowing pattern.
        Raw fill dict passed verbatim to recorder; recorder owns parsing to FillRecord.
        """
        try:
            data = msg.get("data")
            # S47 T11 M3 — isinstance guard: pybit V3 may emit data as dict (single-event).
            if data is None:
                return
            if isinstance(data, dict):
                events = [data]
            elif isinstance(data, list):
                events = data
            else:
                logger.warning(
                    "ws.execution.shape_mismatch",
                    extra={
                        "expected": "list|dict",
                        "got": type(data).__name__,
                        "topic": msg.get("topic"),
                    },
                )
                return
            for item in events:
                self._fill_recorder.on_fill_event(item)
        except Exception:
            logger.exception("execution event dispatch failed; dropping msg=%r", msg)

    def _parse_order(self, item: dict[str, Any]) -> dict[str, Any] | None:
        status = item.get("orderStatus", "")
        if status in self._FILLED_STATUSES:
            missing = [f for f in self._REQUIRED_FEE_FIELDS if f not in item]
            if missing:
                logger.error(
                    "order event %s missing required fee fields %s; dropping item=%r",
                    status,
                    missing,
                    item,
                )
                return None
        return dict(item)
