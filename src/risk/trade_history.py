"""Trade history persistence: TradeRecord + TradeHistoryRepository.

Sprint 4 Task 7.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlite3 import Connection
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.risk.reason_codes import ReasonCode


class TradeRecord(BaseModel):
    """Closed trade record. Decimal monetary, ISO-8601 UTC timestamps."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trade_id: int | None = None  # None pre-insert; set by AUTOINCREMENT
    symbol: str
    entry_signal_id: UUID
    entry_ts: datetime
    exit_ts: datetime
    qty: Decimal = Field(..., gt=0)
    entry_price: Decimal = Field(..., gt=0)
    exit_price: Decimal = Field(..., gt=0)
    pnl_quote: Decimal  # signed
    pnl_pct: Decimal  # signed (e.g. 0.012 = +1.2%)
    fees_paid: Decimal = Field(..., ge=0)
    reason_code: ReasonCode
    kelly_phase: Literal[1, 2, 3, 4]
    recorded_at: datetime


class TradeHistoryRepository:
    """SQLite-backed trade history. Decimal->str on write, str->Decimal on read."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def insert_closed_trade(self, record: TradeRecord) -> int:
        """Insert and return new trade_id."""
        cursor = self._conn.execute(
            """INSERT INTO trade_history (
                symbol, entry_signal_id, entry_ts, exit_ts, qty,
                entry_price, exit_price, pnl_quote, pnl_pct, fees_paid,
                reason_code, kelly_phase, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.symbol,
                str(record.entry_signal_id),
                record.entry_ts.isoformat(),
                record.exit_ts.isoformat(),
                str(record.qty),
                str(record.entry_price),
                str(record.exit_price),
                str(record.pnl_quote),
                str(record.pnl_pct),
                str(record.fees_paid),
                record.reason_code.value,
                record.kelly_phase,
                record.recorded_at.isoformat(),
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def load_recent(
        self, *, window_days: int = 90, now: datetime | None = None
    ) -> list[TradeRecord]:
        """Load trades with exit_ts >= (now - window_days)."""
        if window_days < 0:
            raise ValueError("window_days must be non-negative")
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=window_days)
        rows = self._conn.execute(
            """SELECT trade_id, symbol, entry_signal_id, entry_ts, exit_ts, qty,
                      entry_price, exit_price, pnl_quote, pnl_pct, fees_paid,
                      reason_code, kelly_phase, recorded_at
               FROM trade_history
               WHERE exit_ts >= ?
               ORDER BY exit_ts ASC""",
            (cutoff.isoformat(),),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def count(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM trade_history").fetchone()[0]
        )

    @staticmethod
    def _row_to_record(row: tuple) -> TradeRecord:
        return TradeRecord(
            trade_id=row[0],
            symbol=row[1],
            entry_signal_id=UUID(row[2]),
            entry_ts=datetime.fromisoformat(row[3]),
            exit_ts=datetime.fromisoformat(row[4]),
            qty=Decimal(row[5]),
            entry_price=Decimal(row[6]),
            exit_price=Decimal(row[7]),
            pnl_quote=Decimal(row[8]),
            pnl_pct=Decimal(row[9]),
            fees_paid=Decimal(row[10]),
            reason_code=ReasonCode(row[11]),
            kelly_phase=row[12],
            recorded_at=datetime.fromisoformat(row[13]),
        )
