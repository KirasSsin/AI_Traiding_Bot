"""Tests for EquityTracker — 24h rolling HWM. Task 8 Sprint 4."""

import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from src.platform.db import connect, init_db
from src.risk.equity_tracker import EquityTracker

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"

_UTC = UTC


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    init_db(db_path, MIGRATIONS_DIR)
    return connect(db_path)


@pytest.fixture()
def tracker(db: sqlite3.Connection) -> EquityTracker:
    return EquityTracker(db)


# ---------------------------------------------------------------------------
# record()
# ---------------------------------------------------------------------------


def test_record_returns_positive_snapshot_id(tracker: EquityTracker) -> None:
    snap_id = tracker.record(
        realized=Decimal("10000"),
        unrealized=Decimal("500"),
        ts=datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC),
        source="BAR_CLOSE",
    )
    assert isinstance(snap_id, int)
    assert snap_id > 0


def test_record_computes_total_equity(tracker: EquityTracker, db: sqlite3.Connection) -> None:
    snap_id = tracker.record(
        realized=Decimal("10000"),
        unrealized=Decimal("250.50"),
        ts=datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC),
        source="BAR_CLOSE",
    )
    row = db.execute(
        "SELECT total_equity FROM equity_snapshots WHERE snapshot_id = ?", (snap_id,)
    ).fetchone()
    assert Decimal(row[0]) == Decimal("10250.50")


def test_record_rejects_negative_realized(tracker: EquityTracker) -> None:
    with pytest.raises(ValueError, match="realized must be >= 0"):
        tracker.record(
            realized=Decimal("-1"),
            unrealized=Decimal("0"),
            ts=datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC),
            source="BAR_CLOSE",
        )


def test_record_accepts_negative_unrealized(tracker: EquityTracker) -> None:
    """Mark-to-market loss on open position is valid."""
    snap_id = tracker.record(
        realized=Decimal("10000"),
        unrealized=Decimal("-300"),
        ts=datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC),
        source="POSITION_CLOSE",
    )
    assert snap_id > 0


def test_record_invalid_source_raises(db: sqlite3.Connection) -> None:
    """CHECK constraint on source column must reject unknown values."""
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO equity_snapshots (ts, realized_equity, unrealized_pnl, total_equity, source) "
            "VALUES (?, ?, ?, ?, ?)",
            ("2026-04-23T12:00:00+00:00", "10000", "0", "10000", "INVALID"),
        )
        db.commit()


# ---------------------------------------------------------------------------
# current_total()
# ---------------------------------------------------------------------------


def test_current_total_returns_none_when_empty(tracker: EquityTracker) -> None:
    assert tracker.current_total() is None


def test_current_total_returns_latest_by_ts(tracker: EquityTracker) -> None:
    """current_total orders by ts DESC, not insertion order."""
    base = datetime(2026, 4, 23, 10, 0, 0, tzinfo=_UTC)
    tracker.record(
        realized=Decimal("10000"),
        unrealized=Decimal("0"),
        ts=base + timedelta(hours=2),  # newer
        source="BAR_CLOSE",
    )
    tracker.record(
        realized=Decimal("9000"),
        unrealized=Decimal("0"),
        ts=base,  # older, inserted second
        source="BAR_CLOSE",
    )
    # Latest by ts is base+2h → total = 10000
    assert tracker.current_total() == Decimal("10000")


# ---------------------------------------------------------------------------
# peak_equity_24h()
# ---------------------------------------------------------------------------


def test_peak_equity_24h_returns_none_when_empty(tracker: EquityTracker) -> None:
    now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC)
    assert tracker.peak_equity_24h(now=now) is None


def test_peak_equity_24h_returns_max_in_window(tracker: EquityTracker) -> None:
    now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC)
    for equity, hours_ago in [("9000", 1), ("11000", 3), ("10000", 6)]:
        tracker.record(
            realized=Decimal(equity),
            unrealized=Decimal("0"),
            ts=now - timedelta(hours=hours_ago),
            source="BAR_CLOSE",
        )
    assert tracker.peak_equity_24h(now=now) == Decimal("11000")


def test_peak_equity_24h_excludes_25h_old(tracker: EquityTracker) -> None:
    now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC)
    tracker.record(
        realized=Decimal("15000"),
        unrealized=Decimal("0"),
        ts=now - timedelta(hours=25),
        source="MANUAL",
    )
    assert tracker.peak_equity_24h(now=now) is None


def test_peak_equity_24h_includes_23h_old(tracker: EquityTracker) -> None:
    now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC)
    tracker.record(
        realized=Decimal("12000"),
        unrealized=Decimal("0"),
        ts=now - timedelta(hours=23),
        source="BAR_CLOSE",
    )
    assert tracker.peak_equity_24h(now=now) == Decimal("12000")


def test_peak_equity_24h_uses_utc_now_by_default(tracker: EquityTracker) -> None:
    """With no `now` arg, function uses wall-clock UTC — just verify it runs."""
    result = tracker.peak_equity_24h()
    assert result is None  # empty table


# ---------------------------------------------------------------------------
# Decimal exact roundtrip — no float drift
# ---------------------------------------------------------------------------


def test_decimal_roundtrip_exact(tracker: EquityTracker) -> None:
    precise = Decimal("12345.6789012345")
    tracker.record(
        realized=precise,
        unrealized=Decimal("0"),
        ts=datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC),
        source="BAR_CLOSE",
    )
    result = tracker.current_total()
    assert result == precise
    assert str(result) == str(precise)


# ---------------------------------------------------------------------------
# ISO-8601 boundary: 23:59 vs 00:01 across midnight
# ---------------------------------------------------------------------------


def test_peak_equity_24h_decimal_precision_beyond_double(tracker: EquityTracker) -> None:
    """Two equities differing only past 15 sig digits must rank by Decimal.

    ADR 0018 sub-decision 9 (audit I1) — previously the implementation used
    SQL ``ORDER BY CAST(total_equity AS REAL)`` which collapsed the values
    to IEEE-754 double for sorting. The two strings below round to the same
    float, so the SQL sort would return whichever the engine happened to
    place first — picking the wrong peak.
    """
    now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC)
    smaller = Decimal("12345.67890123450001")
    larger = Decimal("12345.67890123450002")
    # Sanity check: both collapse to the same float — proving the legacy
    # SQL CAST could not distinguish them.
    assert float(smaller) == float(larger)

    tracker.record(
        realized=smaller,
        unrealized=Decimal("0"),
        ts=now - timedelta(hours=2),
        source="BAR_CLOSE",
    )
    tracker.record(
        realized=larger,
        unrealized=Decimal("0"),
        ts=now - timedelta(hours=1),
        source="BAR_CLOSE",
    )
    assert tracker.peak_equity_24h(now=now) == larger


def test_iso8601_lexicographic_boundary(tracker: EquityTracker) -> None:
    """Timestamps spanning midnight compare correctly as ISO-8601 strings."""
    ts_2359 = datetime(2026, 4, 22, 23, 59, 0, tzinfo=_UTC)
    ts_0001 = datetime(2026, 4, 23, 0, 1, 0, tzinfo=_UTC)
    now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=_UTC)

    tracker.record(
        realized=Decimal("9500"),
        unrealized=Decimal("0"),
        ts=ts_2359,
        source="BAR_CLOSE",
    )
    tracker.record(
        realized=Decimal("9800"),
        unrealized=Decimal("0"),
        ts=ts_0001,
        source="BAR_CLOSE",
    )

    # Both are within 24h of now; peak should be 9800
    peak = tracker.peak_equity_24h(now=now)
    assert peak == Decimal("9800")

    # current_total should be 9800 (ts_0001 is later)
    assert tracker.current_total() == Decimal("9800")
