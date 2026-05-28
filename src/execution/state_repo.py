"""SQLite persistence for execution FSM state. ADR 0019 sub-decision 3 + ADR 0020 sub-decision 2."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.execution.state_machine import ExecutionState


@dataclass(frozen=True)
class ExecutionStateRow:
    symbol: str
    state: ExecutionState
    position_qty: Decimal
    entry_price: Decimal | None
    oco_main_order_id: str | None  # legacy S5: new code writes None
    bracket_id: str | None
    oco_tp_order_id: str | None
    oco_sl_order_id: str | None
    expected_oco_qty: Decimal | None
    arming_started_at: str | None  # ISO-8601 UTC; only set in OCO_ARMING
    last_attempt_num: int
    updated_at: str  # ISO-8601 UTC
    halt_reason: str | None = None
    last_exit_reason: str | None = None
    last_reconcile_at: str | None = None  # ISO-8601 UTC; updated each reconcile call
    bootstrap_at: str | None = None  # ISO-8601 UTC; set once per process startup


_COLUMNS = (
    "symbol, state, position_qty, entry_price, oco_main_order_id, "
    "bracket_id, oco_tp_order_id, oco_sl_order_id, expected_oco_qty, "
    "arming_started_at, last_attempt_num, updated_at, "
    "halt_reason, last_exit_reason, last_reconcile_at, bootstrap_at"
)


class ExecutionStateRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, row: ExecutionStateRow) -> None:
        with self._conn:
            self._conn.execute(
                f"""
                INSERT INTO execution_state ({_COLUMNS})
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    state=excluded.state,
                    position_qty=excluded.position_qty,
                    entry_price=excluded.entry_price,
                    oco_main_order_id=excluded.oco_main_order_id,
                    bracket_id=excluded.bracket_id,
                    oco_tp_order_id=excluded.oco_tp_order_id,
                    oco_sl_order_id=excluded.oco_sl_order_id,
                    expected_oco_qty=excluded.expected_oco_qty,
                    arming_started_at=excluded.arming_started_at,
                    last_attempt_num=excluded.last_attempt_num,
                    updated_at=excluded.updated_at,
                    halt_reason=excluded.halt_reason,
                    last_exit_reason=excluded.last_exit_reason,
                    last_reconcile_at=excluded.last_reconcile_at,
                    bootstrap_at=excluded.bootstrap_at
                """,
                (
                    row.symbol,
                    row.state.value,
                    str(row.position_qty),
                    str(row.entry_price) if row.entry_price is not None else None,
                    row.oco_main_order_id,
                    row.bracket_id,
                    row.oco_tp_order_id,
                    row.oco_sl_order_id,
                    str(row.expected_oco_qty) if row.expected_oco_qty is not None else None,
                    row.arming_started_at,
                    row.last_attempt_num,
                    row.updated_at,
                    row.halt_reason,
                    row.last_exit_reason,
                    row.last_reconcile_at,
                    row.bootstrap_at,
                ),
            )

    def get(self, symbol: str) -> ExecutionStateRow | None:
        cur = self._conn.execute(
            f"SELECT {_COLUMNS} FROM execution_state WHERE symbol = ?",
            (symbol,),
        )
        r = cur.fetchone()
        if r is None:
            return None
        return _row_to_dataclass(r)

    def find_by_order_id(self, order_id: str) -> ExecutionStateRow | None:
        """Find execution_state row where any of oco_main/tp/sl_order_id matches.

        S12 Q5 — used by FillRecorderAdapter for WS orderId → bracket_id resolution.
        Returns None if no match (race-condition safe).
        """
        cur = self._conn.execute(
            f"""SELECT {_COLUMNS} FROM execution_state
                WHERE oco_main_order_id = ? OR oco_tp_order_id = ? OR oco_sl_order_id = ?
                LIMIT 1""",
            (order_id, order_id, order_id),
        )
        r = cur.fetchone()
        if r is None:
            return None
        return _row_to_dataclass(r)

    def _set_halt(self, *, symbol: str, reason: str, context: dict[str, Any]) -> None:
        """Persist HALT (ADR 0021 sub-decision 5 — γ pattern).

        Idempotency rule: ``halt_reason`` column accepts the FIRST non-null
        write only (primary wins); subsequent halts leave the column unchanged.
        ``halt_log`` always appends — chronological audit trail of every halt
        event the coordinator emitted.

        Safe to call when no execution_state row exists yet (bootstrap path):
        only the audit log is written.
        """
        ts = datetime.now(tz=UTC).isoformat()
        ctx_json = json.dumps(context, default=str, sort_keys=True)
        with self._conn:
            cur = self._conn.execute(
                "SELECT halt_reason FROM execution_state WHERE symbol = ?",
                (symbol,),
            )
            existing = cur.fetchone()
            # Write-ahead audit (ADR 0021 sub-decision 5): append the halt_log row
            # BEFORE the execution_state UPDATE. Both run in one transaction so the
            # outcome is identical on commit, but ordering the audit INSERT first
            # preserves the invariant for any future split-txn refactor (no audit
            # gap if the column UPDATE were ever to commit separately).
            self._conn.execute(
                "INSERT INTO halt_log (symbol, ts, reason, context_json) " "VALUES (?, ?, ?, ?)",
                (symbol, ts, reason, ctx_json),
            )
            if existing is not None and existing[0] is None:
                self._conn.execute(
                    "UPDATE execution_state SET halt_reason = ?, updated_at = ? "
                    "WHERE symbol = ? AND halt_reason IS NULL",
                    (reason, ts, symbol),
                )


def _row_to_dataclass(r: tuple[Any, ...]) -> ExecutionStateRow:
    return ExecutionStateRow(
        symbol=r[0],
        state=ExecutionState(r[1]),
        position_qty=Decimal(r[2]),
        entry_price=Decimal(r[3]) if r[3] is not None else None,
        oco_main_order_id=r[4],
        bracket_id=r[5],
        oco_tp_order_id=r[6],
        oco_sl_order_id=r[7],
        expected_oco_qty=Decimal(r[8]) if r[8] is not None else None,
        arming_started_at=r[9],
        last_attempt_num=int(r[10]),
        updated_at=r[11],
        halt_reason=r[12],
        last_exit_reason=r[13],
        last_reconcile_at=r[14],
        bootstrap_at=r[15],
    )
