"""S36 T3: EquityTracker.intraday_dd_pct + hwm_since методы (HaltGate inputs)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from src.platform.db import connect, init_db
from src.risk.equity_tracker import EquityTracker

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"


@pytest.fixture
def in_memory_equity_tracker(tmp_path: Path) -> EquityTracker:
    """File-based SQLite + migrations applied (matches project pattern)."""
    db_path = tmp_path / "test.db"
    init_db(db_path, MIGRATIONS_DIR)
    conn = connect(db_path)
    return EquityTracker(conn)


def test_intraday_dd_pct_zero_when_no_drawdown(in_memory_equity_tracker: EquityTracker) -> None:
    """Equity flat OR rising → DD = 0."""
    et = in_memory_equity_tracker
    base = datetime(2026, 1, 1, 0, tzinfo=UTC)
    et.record(realized=Decimal("1000"), unrealized=Decimal("0"), ts=base, source="MANUAL")
    et.record(
        realized=Decimal("1000"),
        unrealized=Decimal("100"),
        ts=base + timedelta(hours=1),
        source="MANUAL",
    )
    assert et.intraday_dd_pct(now=base + timedelta(hours=2)) == Decimal("0")


def test_intraday_dd_pct_returns_relative_drop_from_24h_peak(
    in_memory_equity_tracker: EquityTracker,
) -> None:
    """Peak 1100 → current 1000 = 9.09% DD."""
    et = in_memory_equity_tracker
    base = datetime(2026, 1, 1, 0, tzinfo=UTC)
    # Peak set first
    et.record(realized=Decimal("1000"), unrealized=Decimal("100"), ts=base, source="MANUAL")
    # Drop to 1000
    et.record(
        realized=Decimal("1000"),
        unrealized=Decimal("0"),
        ts=base + timedelta(hours=1),
        source="MANUAL",
    )
    dd = et.intraday_dd_pct(now=base + timedelta(hours=2))
    expected = (Decimal("1100") - Decimal("1000")) / Decimal("1100")
    assert dd == expected


def test_intraday_dd_pct_zero_when_no_snapshots(in_memory_equity_tracker: EquityTracker) -> None:
    """Empty table → DD = 0 (defensive default)."""
    assert in_memory_equity_tracker.intraday_dd_pct() == Decimal("0")


def test_hwm_since_returns_max_total_equity(in_memory_equity_tracker: EquityTracker) -> None:
    """HWM since timestamp = max(total_equity) since ts (inclusive)."""
    et = in_memory_equity_tracker
    base = datetime(2026, 1, 1, 0, tzinfo=UTC)
    et.record(
        realized=Decimal("500"), unrealized=Decimal("0"), ts=base, source="MANUAL"
    )  # before since
    activation = base + timedelta(hours=1)
    et.record(realized=Decimal("1000"), unrealized=Decimal("0"), ts=activation, source="MANUAL")
    et.record(
        realized=Decimal("1000"),
        unrealized=Decimal("200"),
        ts=activation + timedelta(hours=1),
        source="MANUAL",
    )
    et.record(
        realized=Decimal("1000"),
        unrealized=Decimal("100"),
        ts=activation + timedelta(hours=2),
        source="MANUAL",
    )
    assert et.hwm_since(since_ts=activation) == Decimal("1200")


def test_hwm_since_returns_none_when_no_records_after_ts(
    in_memory_equity_tracker: EquityTracker,
) -> None:
    """HWM since future timestamp = None."""
    et = in_memory_equity_tracker
    base = datetime(2026, 1, 1, 0, tzinfo=UTC)
    et.record(realized=Decimal("1000"), unrealized=Decimal("0"), ts=base, source="MANUAL")
    assert et.hwm_since(since_ts=base + timedelta(days=10)) is None
