"""SQLite persistence for execution FSM state. ADR 0019 sub-decision 3."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from src.execution.state_machine import ExecutionState


@dataclass(frozen=True)
class ExecutionStateRow:
    symbol: str
    state: ExecutionState
    position_qty: Decimal
    entry_price: Decimal | None
    oco_main_order_id: str | None
    updated_at: str  # ISO-8601 UTC


class ExecutionStateRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, row: ExecutionStateRow) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO execution_state
                    (symbol, state, position_qty, entry_price, oco_main_order_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    state=excluded.state,
                    position_qty=excluded.position_qty,
                    entry_price=excluded.entry_price,
                    oco_main_order_id=excluded.oco_main_order_id,
                    updated_at=excluded.updated_at
                """,
                (
                    row.symbol,
                    row.state.value,
                    str(row.position_qty),
                    str(row.entry_price) if row.entry_price is not None else None,
                    row.oco_main_order_id,
                    row.updated_at,
                ),
            )

    def get(self, symbol: str) -> ExecutionStateRow | None:
        cur = self._conn.execute(
            "SELECT symbol, state, position_qty, entry_price, oco_main_order_id, updated_at "
            "FROM execution_state WHERE symbol = ?",
            (symbol,),
        )
        r = cur.fetchone()
        if r is None:
            return None
        return ExecutionStateRow(
            symbol=r[0],
            state=ExecutionState(r[1]),
            position_qty=Decimal(r[2]),
            entry_price=Decimal(r[3]) if r[3] is not None else None,
            oco_main_order_id=r[4],
            updated_at=r[5],
        )
