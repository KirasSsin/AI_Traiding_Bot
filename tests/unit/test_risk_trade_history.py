"""Tests for TradeHistoryRepository + TradeRecord (Sprint 4 Task 7)."""

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.platform.db import connect, init_db

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    init_db(db_path, MIGRATIONS_DIR)
    return connect(db_path)


def _make_record(**overrides):
    """Build a valid TradeRecord with sensible defaults."""
    from src.risk.trade_history import TradeRecord
    from src.risk.reason_codes import ReasonCode

    now = datetime.now(timezone.utc)
    defaults = dict(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=now - timedelta(hours=1),
        exit_ts=now,
        qty=Decimal("0.001"),
        entry_price=Decimal("50000.00"),
        exit_price=Decimal("51000.00"),
        pnl_quote=Decimal("1.00"),
        pnl_pct=Decimal("0.02"),
        fees_paid=Decimal("0.50"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=now,
    )
    defaults.update(overrides)
    return TradeRecord(**defaults)


# ---------------------------------------------------------------------------
# Basic insert + count
# ---------------------------------------------------------------------------

def test_insert_returns_positive_trade_id(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    record = _make_record()
    trade_id = repo.insert_closed_trade(record)

    assert isinstance(trade_id, int)
    assert trade_id > 0


def test_count_after_single_insert(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    repo.insert_closed_trade(_make_record())
    assert repo.count() == 1


def test_count_multiple_inserts(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    for _ in range(5):
        repo.insert_closed_trade(_make_record())
    assert repo.count() == 5


# ---------------------------------------------------------------------------
# Decimal roundtrip (no float drift)
# ---------------------------------------------------------------------------

def test_decimal_roundtrip_exact(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    record = _make_record(
        qty=Decimal("0.00000001"),
        entry_price=Decimal("99999.99999999"),
        exit_price=Decimal("100000.00000001"),
        pnl_quote=Decimal("-0.00000001"),
        pnl_pct=Decimal("-0.0000000001"),
        fees_paid=Decimal("0.00000001"),
    )
    repo.insert_closed_trade(record)
    now = datetime.now(timezone.utc)
    rows = repo.load_recent(window_days=1, now=now)

    assert len(rows) == 1
    r = rows[0]
    assert r.qty == record.qty
    assert r.entry_price == record.entry_price
    assert r.exit_price == record.exit_price
    assert r.pnl_quote == record.pnl_quote
    assert r.pnl_pct == record.pnl_pct
    assert r.fees_paid == record.fees_paid


# ---------------------------------------------------------------------------
# load_recent window cutoff
# ---------------------------------------------------------------------------

def test_load_recent_excludes_old_trade(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    now = datetime.now(timezone.utc)
    old_exit = now - timedelta(days=100)
    repo.insert_closed_trade(_make_record(exit_ts=old_exit, entry_ts=old_exit - timedelta(hours=1)))

    result = repo.load_recent(window_days=90, now=now)
    assert result == []


def test_load_recent_includes_recent_trade(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    now = datetime.now(timezone.utc)
    repo.insert_closed_trade(_make_record(exit_ts=now - timedelta(days=10)))

    result = repo.load_recent(window_days=90, now=now)
    assert len(result) == 1


def test_load_recent_default_window_90_days(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    now = datetime.now(timezone.utc)
    # 80 days ago — within 90-day window
    repo.insert_closed_trade(_make_record(exit_ts=now - timedelta(days=80)))
    # 100 days ago — outside
    old = now - timedelta(days=100)
    repo.insert_closed_trade(_make_record(exit_ts=old, entry_ts=old - timedelta(hours=1)))

    result = repo.load_recent(now=now)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# load_recent ordering
# ---------------------------------------------------------------------------

def test_load_recent_ordered_asc_by_exit_ts(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    now = datetime.now(timezone.utc)
    t1 = now - timedelta(days=5)
    t2 = now - timedelta(days=3)
    t3 = now - timedelta(days=1)

    repo.insert_closed_trade(_make_record(exit_ts=t3))
    repo.insert_closed_trade(_make_record(exit_ts=t1))
    repo.insert_closed_trade(_make_record(exit_ts=t2))

    rows = repo.load_recent(window_days=90, now=now)
    exits = [r.exit_ts for r in rows]
    assert exits == sorted(exits)


# ---------------------------------------------------------------------------
# Negative window_days raises
# ---------------------------------------------------------------------------

def test_negative_window_days_raises(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    with pytest.raises(ValueError, match="non-negative"):
        repo.load_recent(window_days=-1)


# ---------------------------------------------------------------------------
# Pydantic validation: invalid kelly_phase
# ---------------------------------------------------------------------------

def test_invalid_kelly_phase_raises_before_insert(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    with pytest.raises(ValidationError):
        record = _make_record(kelly_phase=5)
        repo.insert_closed_trade(record)  # should not reach here


# ---------------------------------------------------------------------------
# Full field roundtrip (all scalar fields preserved)
# ---------------------------------------------------------------------------

def test_full_roundtrip_preserves_all_fields(db):
    from src.risk.trade_history import TradeHistoryRepository
    from src.risk.reason_codes import ReasonCode

    repo = TradeHistoryRepository(db)
    sig_id = uuid4()
    now = datetime.now(timezone.utc)
    entry = now - timedelta(hours=2)

    record = _make_record(
        symbol="ETHUSDT",
        entry_signal_id=sig_id,
        entry_ts=entry,
        exit_ts=now - timedelta(minutes=5),
        qty=Decimal("1.5"),
        entry_price=Decimal("3000.00"),
        exit_price=Decimal("3100.00"),
        pnl_quote=Decimal("150.00"),
        pnl_pct=Decimal("0.0333"),
        fees_paid=Decimal("2.00"),
        reason_code=ReasonCode.EXIT_SL_HIT,
        kelly_phase=3,
        recorded_at=now,
    )
    trade_id = repo.insert_closed_trade(record)
    rows = repo.load_recent(window_days=1, now=now)

    assert len(rows) == 1
    r = rows[0]
    assert r.trade_id == trade_id
    assert r.symbol == "ETHUSDT"
    assert r.entry_signal_id == sig_id
    assert r.reason_code == ReasonCode.EXIT_SL_HIT
    assert r.kelly_phase == 3


# ---------------------------------------------------------------------------
# DB persistence: two repo instances on same connection
# ---------------------------------------------------------------------------

def test_persistence_across_repo_instances(db):
    from src.risk.trade_history import TradeHistoryRepository

    repo1 = TradeHistoryRepository(db)
    repo1.insert_closed_trade(_make_record())

    repo2 = TradeHistoryRepository(db)
    now = datetime.now(timezone.utc)
    assert len(repo2.load_recent(window_days=1, now=now)) == 1
    assert repo2.count() == 1


# ---------------------------------------------------------------------------
# Blocker 1: AwareDatetime
# ---------------------------------------------------------------------------

def test_naive_datetime_rejected():
    """TradeRecord must reject naive datetimes (Blocker 1)."""
    from src.risk.trade_history import TradeRecord

    naive = datetime(2024, 1, 1, 12, 0, 0)  # no tzinfo
    with pytest.raises(ValidationError):
        _make_record(entry_ts=naive)


def test_aware_datetime_accepted():
    """TradeRecord accepts aware UTC datetimes (Blocker 1)."""
    from src.risk.trade_history import TradeRecord

    aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    record = _make_record(entry_ts=aware)
    assert record.entry_ts == aware


# ---------------------------------------------------------------------------
# Blocker 2: UNIQUE entry_signal_id — duplicate insert returns existing id
# ---------------------------------------------------------------------------

def test_duplicate_entry_signal_id_returns_existing_id(db):
    """Second insert with same entry_signal_id returns first trade_id, count == 1 (Blocker 2)."""
    from src.risk.trade_history import TradeHistoryRepository

    repo = TradeHistoryRepository(db)
    sig_id = uuid4()
    record = _make_record(entry_signal_id=sig_id)

    first_id = repo.insert_closed_trade(record)
    second_id = repo.insert_closed_trade(record)

    assert second_id == first_id
    assert repo.count() == 1
