"""Per-fill history persistence: FillRecord + FillHistoryRepository.

Sprint 9 Q3 B1 (per pre-s9-backlog.md).

Mirrors trade_history.py pattern. Stores fills granularly для analytics
(slippage measurement, fee breakdown, partial-fill audit). Idempotent
on exec_id (UNIQUE INDEX) under at-least-once WS delivery.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from sqlite3 import Connection
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class FillRecord(BaseModel):
    """Single execution fill. Decimal monetary, ISO-8601 UTC timestamps."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fill_id: int | None = None  # None pre-insert; set by AUTOINCREMENT
    parent_trade_id: int = Field(..., gt=0)
    exec_id: str  # Bybit V5 execution-list event id
    fill_qty: Decimal = Field(..., gt=0)
    fill_price: Decimal = Field(..., gt=0)
    fill_fee: Decimal = Field(..., ge=0)
    fee_currency: str
    is_partial: bool
    fill_ts: AwareDatetime
    recorded_at: AwareDatetime


class FillHistoryRepository:
    """SQLite-backed fill history. Decimal->str on write, str->Decimal on read."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def insert_fill(self, record: FillRecord) -> int:
        """Insert and return fill_id. Idempotent on duplicate exec_id."""
        with self._conn:
            cursor = self._conn.execute(
                """INSERT OR IGNORE INTO trade_fills (
                    parent_trade_id, exec_id, fill_qty, fill_price, fill_fee,
                    fee_currency, is_partial, fill_ts, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.parent_trade_id,
                    record.exec_id,
                    str(record.fill_qty),
                    str(record.fill_price),
                    str(record.fill_fee),
                    record.fee_currency,
                    1 if record.is_partial else 0,
                    record.fill_ts.isoformat(),
                    record.recorded_at.isoformat(),
                ),
            )
        if cursor.lastrowid and cursor.rowcount > 0:
            return int(cursor.lastrowid)
        # Duplicate — fetch existing
        row = self._conn.execute(
            "SELECT fill_id FROM trade_fills WHERE exec_id = ?",
            (record.exec_id,),
        ).fetchone()
        return int(row[0])

    def load_by_trade(self, *, parent_trade_id: int) -> list[FillRecord]:
        """Load all fills для given trade, ordered by fill_ts ASC."""
        rows = self._conn.execute(
            """SELECT fill_id, parent_trade_id, exec_id, fill_qty, fill_price,
                      fill_fee, fee_currency, is_partial, fill_ts, recorded_at
               FROM trade_fills
               WHERE parent_trade_id = ?
               ORDER BY fill_ts ASC""",
            (parent_trade_id,),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def count(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM trade_fills").fetchone()[0]
        )

    @staticmethod
    def _row_to_record(row: tuple[Any, ...]) -> FillRecord:
        return FillRecord(
            fill_id=row[0],
            parent_trade_id=row[1],
            exec_id=row[2],
            fill_qty=Decimal(row[3]),
            fill_price=Decimal(row[4]),
            fill_fee=Decimal(row[5]),
            fee_currency=row[6],
            is_partial=bool(row[7]),
            fill_ts=datetime.fromisoformat(row[8]).astimezone(UTC),
            recorded_at=datetime.fromisoformat(row[9]).astimezone(UTC),
        )
