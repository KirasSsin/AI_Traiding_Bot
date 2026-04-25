"""Tests for FillRecord + FillHistoryRepository.

Sprint 9 Q3 B1.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from src.platform.db import init_db
from src.risk.fill_history import FillHistoryRepository, FillRecord

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _make_fill(*, exec_id: str = "exec_1", parent_trade_id: int = 1) -> FillRecord:
    return FillRecord(
        parent_trade_id=parent_trade_id,
        exec_id=exec_id,
        fill_qty=Decimal("0.5"),
        fill_price=Decimal("100000"),
        fill_fee=Decimal("0.05"),
        fee_currency="USDT",
        is_partial=False,
        fill_ts=datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 4, 25, 12, 0, 1, tzinfo=UTC),
    )


def _build_repo(tmp_path: Path) -> tuple[FillHistoryRepository, sqlite3.Connection]:
    db_path = tmp_path / "fh.db"
    init_db(db_path, MIG_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    # Seed parent trade_history row для FK
    conn.execute(
        """INSERT INTO trade_history (
            symbol, entry_signal_id, entry_ts, exit_ts, qty,
            entry_price, exit_price, pnl_quote, pnl_pct, fees_paid,
            reason_code, kelly_phase, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("BTCUSDT", "00000000-0000-0000-0000-000000000001",
         "2026-04-25T11:00:00+00:00", "2026-04-25T12:00:00+00:00",
         "0.5", "99500", "100000", "250", "0.005", "0.05",
         "EXIT_TP_HIT", 1, "2026-04-25T12:00:01+00:00"),
    )
    conn.commit()
    return FillHistoryRepository(conn), conn


def test_insert_fill_returns_fill_id(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    fill_id = repo.insert_fill(_make_fill())
    assert fill_id == 1


def test_insert_idempotent_on_duplicate_exec_id(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    fill_id_1 = repo.insert_fill(_make_fill(exec_id="dup"))
    fill_id_2 = repo.insert_fill(_make_fill(exec_id="dup"))
    assert fill_id_1 == fill_id_2  # same row returned


def test_load_by_trade_returns_ordered_by_fill_ts(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    fill_a = _make_fill(exec_id="a")
    fill_b_record = FillRecord(
        parent_trade_id=1,
        exec_id="b",
        fill_qty=Decimal("0.3"),
        fill_price=Decimal("100100"),
        fill_fee=Decimal("0.03"),
        fee_currency="USDT",
        is_partial=True,
        fill_ts=datetime(2026, 4, 25, 12, 1, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 4, 25, 12, 1, 1, tzinfo=UTC),
    )
    repo.insert_fill(fill_b_record)
    repo.insert_fill(fill_a)

    fills = repo.load_by_trade(parent_trade_id=1)
    assert len(fills) == 2
    assert fills[0].exec_id == "a"  # earlier fill_ts first
    assert fills[1].exec_id == "b"


def test_decimal_roundtrip(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    repo.insert_fill(_make_fill())
    fills = repo.load_by_trade(parent_trade_id=1)
    assert fills[0].fill_qty == Decimal("0.5")
    assert fills[0].fill_price == Decimal("100000")
    assert fills[0].fill_fee == Decimal("0.05")


def test_is_partial_flag_roundtrip(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    fill = FillRecord(
        parent_trade_id=1, exec_id="p", fill_qty=Decimal("0.5"),
        fill_price=Decimal("100000"), fill_fee=Decimal("0.05"),
        fee_currency="USDT", is_partial=True,
        fill_ts=datetime.now(UTC), recorded_at=datetime.now(UTC),
    )
    repo.insert_fill(fill)
    fills = repo.load_by_trade(parent_trade_id=1)
    assert fills[0].is_partial is True


def test_count(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    assert repo.count() == 0
    repo.insert_fill(_make_fill())
    assert repo.count() == 1


def test_negative_qty_rejected_at_model() -> None:
    with pytest.raises(ValueError):
        FillRecord(
            parent_trade_id=1, exec_id="x", fill_qty=Decimal("-0.5"),
            fill_price=Decimal("100000"), fill_fee=Decimal("0.05"),
            fee_currency="USDT", is_partial=False,
            fill_ts=datetime.now(UTC), recorded_at=datetime.now(UTC),
        )
