"""Trade history persistence: TradeRecord + TradeHistoryRepository.

Sprint 4 Task 7.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from sqlite3 import Connection
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from src.risk.reason_codes import ReasonCode


class TradeRecord(BaseModel):
    """Closed trade record. Decimal monetary, ISO-8601 UTC timestamps."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trade_id: int | None = None  # None pre-insert; set by AUTOINCREMENT
    symbol: str
    entry_signal_id: UUID
    entry_ts: AwareDatetime
    exit_ts: AwareDatetime
    qty: Decimal = Field(..., gt=0)
    entry_price: Decimal = Field(..., gt=0)
    exit_price: Decimal = Field(..., gt=0)
    pnl_quote: Decimal  # signed
    pnl_pct: Decimal  # signed (e.g. 0.012 = +1.2%)
    fees_paid: Decimal = Field(..., ge=0)
    reason_code: ReasonCode
    kelly_phase: Literal[1, 2, 3, 4]
    recorded_at: AwareDatetime


class TradeHistoryRepository:
    """SQLite-backed trade history. Decimal->str on write, str->Decimal on read."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def insert_closed_trade(self, record: TradeRecord) -> int:
        """Insert and return trade_id. Idempotent on duplicate entry_signal_id."""
        with self._conn:
            cursor = self._conn.execute(
                """INSERT OR IGNORE INTO trade_history (
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
        if cursor.lastrowid and cursor.rowcount > 0:
            return int(cursor.lastrowid)
        # Duplicate — fetch existing
        row = self._conn.execute(
            "SELECT trade_id FROM trade_history WHERE entry_signal_id = ?",
            (str(record.entry_signal_id),),
        ).fetchone()
        return int(row[0])

    def load_recent(
        self, *, window_days: int = 90, now: datetime | None = None
    ) -> list[TradeRecord]:
        """Load trades with exit_ts >= (now - window_days)."""
        if window_days < 0:
            raise ValueError("window_days must be non-negative")
        cutoff = (now or datetime.now(UTC)) - timedelta(days=window_days)
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

    def find_trade_id_by_signal(self, entry_signal_id: UUID) -> int | None:
        """Find trade_id by entry_signal_id (returns None если trade not yet closed).

        S12 Q5 — used by FillRecorderAdapter для parent_trade_id resolution.
        Wired but unreachable с current schema (execution_state has no signal_id link;
        deferred к S13+).
        """
        row = self._conn.execute(
            "SELECT trade_id FROM trade_history WHERE entry_signal_id = ?",
            (str(entry_signal_id),),
        ).fetchone()
        return int(row[0]) if row else None

    @staticmethod
    def _row_to_record(row: tuple[Any, ...]) -> TradeRecord:
        return TradeRecord(
            trade_id=row[0],
            symbol=row[1],
            entry_signal_id=UUID(row[2]),
            entry_ts=datetime.fromisoformat(row[3]).astimezone(UTC),
            exit_ts=datetime.fromisoformat(row[4]).astimezone(UTC),
            qty=Decimal(row[5]),
            entry_price=Decimal(row[6]),
            exit_price=Decimal(row[7]),
            pnl_quote=Decimal(row[8]),
            pnl_pct=Decimal(row[9]),
            fees_paid=Decimal(row[10]),
            reason_code=ReasonCode(row[11]),
            kelly_phase=row[12],
            recorded_at=datetime.fromisoformat(row[13]).astimezone(UTC),
        )
