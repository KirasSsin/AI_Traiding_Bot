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
        """Max total_equity in trailing 24h. None if no snapshots in window.

        Ranking is performed in Python over Decimal values rather than via
        SQL ``ORDER BY CAST(... AS REAL)`` — the latter downcasts a precise
        monetary string to IEEE-754 double for sorting, which can pick the
        wrong row when two equities differ only past 15 significant digits
        (ADR 0007 Decimal-strict, ADR 0018 sub-decision 9 / audit I1).

        Window is bounded (≤ ~24 rows for 1H bars + intra-bar snapshots
        in v0.1), so loading and reducing in Python is O(N) and trivial.
        """
        cutoff = (now or datetime.now(UTC)) - timedelta(hours=24)
        rows = self._conn.execute(
            "SELECT total_equity FROM equity_snapshots WHERE ts >= ?",
            (cutoff.isoformat(),),
        ).fetchall()
        values = [Decimal(r[0]) for r in rows if r[0] is not None]
        if not values:
            return None
        return max(values)

    def current_total(self) -> Decimal | None:
        """Latest total_equity (by ts DESC). None if empty."""
        row = self._conn.execute(
            "SELECT total_equity FROM equity_snapshots ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return Decimal(row[0])
