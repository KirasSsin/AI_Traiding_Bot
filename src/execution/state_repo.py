"""SQLite persistence for execution FSM state. ADR 0019 sub-decision 3 + ADR 0020 sub-decision 2."""
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
    oco_main_order_id: str | None  # legacy S5: new code writes None
    bracket_id: str | None
    oco_tp_order_id: str | None
    oco_sl_order_id: str | None
    expected_oco_qty: Decimal | None
    arming_started_at: str | None  # ISO-8601 UTC; only set in OCO_ARMING
    last_attempt_num: int
    updated_at: str  # ISO-8601 UTC


_COLUMNS = (
    "symbol, state, position_qty, entry_price, oco_main_order_id, "
    "bracket_id, oco_tp_order_id, oco_sl_order_id, expected_oco_qty, "
    "arming_started_at, last_attempt_num, updated_at"
)


class ExecutionStateRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, row: ExecutionStateRow) -> None:
        with self._conn:
            self._conn.execute(
                f"""
                INSERT INTO execution_state ({_COLUMNS})
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    updated_at=excluded.updated_at
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


def _row_to_dataclass(r: tuple) -> ExecutionStateRow:
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
    )
