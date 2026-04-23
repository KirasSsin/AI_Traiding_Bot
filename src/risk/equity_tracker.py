"""EquityTracker — SQLite-backed equity snapshot store with 24h rolling HWM."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from sqlite3 import Connection
from typing import Literal

SnapshotSource = Literal["BAR_CLOSE", "POSITION_CLOSE", "MANUAL"]


class EquityTracker:
    """SQLite-backed equity snapshot store with 24h rolling HWM query."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def record(
        self,
        *,
        realized: Decimal,
        unrealized: Decimal,
        ts: datetime,
        source: SnapshotSource,
    ) -> int:
        """Insert snapshot and return snapshot_id. total_equity = realized + unrealized.

        Commits its own transaction. For atomic multi-write flushes, use
        :meth:`record_no_commit` and wrap with an outer ``with self._conn:``.
        """
        if realized < 0:
            raise ValueError("realized must be >= 0")
        total = realized + unrealized
        cursor = self._conn.execute(
            """INSERT INTO equity_snapshots
               (ts, realized_equity, unrealized_pnl, total_equity, source)
               VALUES (?, ?, ?, ?, ?)""",
            (ts.isoformat(), str(realized), str(unrealized), str(total), source),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def record_no_commit(
        self,
        *,
        realized: Decimal,
        unrealized: Decimal,
        ts: datetime,
        source: SnapshotSource,
    ) -> int:
        """Insert snapshot WITHOUT committing — caller owns the transaction.

        Used by RiskManager.update_equity to flush equity + CB state in
        one atomic ``with conn:`` block (invariant #5 of risk-manager.md).
        """
        if realized < 0:
            raise ValueError("realized must be >= 0")
        total = realized + unrealized
        cursor = self._conn.execute(
            """INSERT INTO equity_snapshots
               (ts, realized_equity, unrealized_pnl, total_equity, source)
               VALUES (?, ?, ?, ?, ?)""",
            (ts.isoformat(), str(realized), str(unrealized), str(total), source),
        )
        return int(cursor.lastrowid)

    def peak_equity_24h(self, *, now: datetime | None = None) -> Decimal | None:
        """Max total_equity in trailing 24h. None if no snapshots in window."""
        cutoff = (now or datetime.now(UTC)) - timedelta(hours=24)
        row = self._conn.execute(
            "SELECT total_equity FROM equity_snapshots WHERE ts >= ?"
            " ORDER BY CAST(total_equity AS REAL) DESC LIMIT 1",
            (cutoff.isoformat(),),
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return Decimal(row[0])

    def current_total(self) -> Decimal | None:
        """Latest total_equity (by ts DESC). None if empty."""
        row = self._conn.execute(
            "SELECT total_equity FROM equity_snapshots ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return Decimal(row[0])
