"""FillRecorderAdapter — bridges Bybit V5 WS execution events → FillHistoryRepository.

S12 Q5 REVISE-additive (per ADR 0027). Best-effort 2-layer pattern:

1. **Always-on:** structlog audit log (``fill_event_received``).
2. **Best-effort DB insert:** Attempt lookup chain WS orderId → execution_state.bracket_id
   → trade_history.entry_signal_id → trade_id. Skip + warn если ANY step unresolved.

CURRENT SCHEMA REALITY (S12 implementation):
``execution_state`` table has NO ``entry_signal_id`` column (verified migrations
0003 + 0004 + 0005). Coordinator only persists ``bracket_id``. Therefore the chain
breaks at the bracket_id↔trade_id gap — full lossless DB persistence with proper
schema link is deferred к S13+ (needs migration; Q7 hard constraint blocks for S12).

Adapter still calls ``find_by_order_id`` so the gap surfaces в logs (operator
post-mortem readable) AND so adapter is drop-in compatible с the S13+ schema fix
(only the "skip — bracket_id↔trade_id link missing" branch needs replacing).

Race condition note: WS execution events MAY arrive before trade_history.insert_closed_trade
(trade still open, exit_ts not yet set). Adapter handles via skip+warn — operator
post-mortem reads structlog audit для unresolved fills.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from src.risk.fill_history import FillHistoryRepository, FillRecord

logger = logging.getLogger(__name__)


class _StateRepoProto(Protocol):
    """Subset of ExecutionStateRepo used by adapter."""

    def find_by_order_id(self, order_id: str) -> Any | None: ...


class _TradeHistoryRepoProto(Protocol):
    """Subset of TradeHistoryRepository used by adapter."""

    def find_trade_id_by_signal(self, entry_signal_id: Any) -> int | None: ...


class FillRecorderAdapter:
    """Adapter implementing _FillRecorderProto (src/execution/bybit/ws_private.py).

    See module docstring для design rationale. Key invariant: NEVER crash on
    malformed WS event. Always log; insert only when fully resolved.
    """

    def __init__(
        self,
        *,
        repo: FillHistoryRepository,
        state_repo: _StateRepoProto,
        trade_history_repo: _TradeHistoryRepoProto,
        lock: threading.Lock | None = None,
    ) -> None:
        self._repo = repo
        self._state_repo = state_repo
        self._trade_history_repo = trade_history_repo
        # H5 (S49): on_fill_event runs on the pybit WS callback thread and reads
        # state_repo / trade_history_repo (SQLite connection family shared with the
        # main-thread Risk/State repos). The read→insert critical section must be
        # serialized against concurrent main-thread writes to avoid SQLite
        # "database is locked" / interleaved writes. A caller may inject a shared
        # lock (the repo/coordinator-layer lock); otherwise a dedicated lock is used.
        self._lock = lock if lock is not None else threading.Lock()

    def on_fill_event(self, evt: dict[str, Any]) -> None:
        """Parse Bybit V5 execution event → best-effort FillRecord insert.

        Error-swallowing pattern (mirrors ws_private._on_execution_raw): WS thread
        cannot crash on bad data. Top-level try/except guard catches mapping
        failures (bad timestamp, bad Decimal, etc.).
        """
        # Layer 1: always-on audit
        logger.info("fill_event_received: evt=%r", evt)

        # Layer 2: best-effort DB insert
        try:
            self._try_insert(evt)
        except Exception:  # noqa: BLE001 — WS callback thread must never crash on bad data (logged)
            logger.exception("fill_event_insert_failed: evt=%r", evt)

    def _try_insert(self, evt: dict[str, Any]) -> None:
        """Resolve lookup chain; insert if fully resolved, else skip+warn.

        H5 (S49): the entire lookup→insert path runs under ``self._lock`` so a
        WS-thread fill insert cannot interleave with a concurrent main-thread
        write on the shared SQLite connection family.
        """
        order_id = evt.get("orderId")
        if not order_id:
            logger.warning("fill_event_unresolved_skipping_db: no orderId, evt=%r", evt)
            return

        with self._lock:
            self._resolve_and_insert(evt, str(order_id))

    def _resolve_and_insert(self, evt: dict[str, Any], order_id: str) -> None:
        """Critical section (lock held by caller): resolve chain + insert."""
        state_row = self._state_repo.find_by_order_id(order_id)
        if state_row is None:
            logger.warning(
                "fill_event_unresolved_skipping_db: no execution_state for orderId=%s",
                order_id,
            )
            return

        # Current schema: ExecutionStateRow has bracket_id but no entry_signal_id.
        # Lookup chain breaks here — deferred к S13+ (needs schema migration adding
        # signal_id↔bracket_id link; Q7 zero-migration constraint blocks для S12).
        entry_signal_id = getattr(state_row, "entry_signal_id", None)
        if entry_signal_id is None:
            logger.warning(
                "fill_event_unresolved_skipping_db: bracket_id=%s resolved but "
                "entry_signal_id↔bracket_id schema link missing (deferred к S13)",
                getattr(state_row, "bracket_id", None),
            )
            return

        trade_id = self._trade_history_repo.find_trade_id_by_signal(entry_signal_id)
        if trade_id is None:
            logger.warning(
                "fill_event_unresolved_skipping_db: trade_history not yet written для "
                "entry_signal_id=%s (race condition; deferred к S13)",
                entry_signal_id,
            )
            return

        record = self._build_fill_record(evt=evt, parent_trade_id=trade_id)
        self._repo.insert_fill(record)

    @staticmethod
    def _build_fill_record(*, evt: dict[str, Any], parent_trade_id: int) -> FillRecord:
        """Map Bybit V5 execution item → FillRecord.

        Pure function (no I/O). Preserved for S13+ when lookup chain becomes
        resolvable; tested in isolation.
        """
        leaves_qty = Decimal(str(evt.get("leavesQty", "0")))
        return FillRecord(
            parent_trade_id=parent_trade_id,
            exec_id=str(evt["execId"]),
            fill_qty=Decimal(str(evt["execQty"])),
            fill_price=Decimal(str(evt["execPrice"])),
            fill_fee=Decimal(str(evt["execFee"])),
            fee_currency=str(evt.get("feeCurrency", "USDT")),
            is_partial=leaves_qty > 0,
            fill_ts=datetime.fromtimestamp(int(evt["execTime"]) / 1000, tz=UTC),
            recorded_at=datetime.now(UTC),
        )
