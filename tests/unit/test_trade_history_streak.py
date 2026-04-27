"""S36 T3: TradeHistoryRepository.consecutive_losses + last_trade_ts (HaltGate inputs)."""

from datetime import UTC, datetime
from datetime import timedelta as td
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from src.platform.db import connect, init_db
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeHistoryRepository, TradeRecord

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"


@pytest.fixture
def in_memory_trade_history(tmp_path: Path) -> TradeHistoryRepository:
    db_path = tmp_path / "test.db"
    init_db(db_path, MIGRATIONS_DIR)
    conn = connect(db_path)
    return TradeHistoryRepository(conn)


def _make_trade(*, symbol: str, pnl: Decimal, exit_ts: datetime) -> TradeRecord:
    entry_ts = exit_ts - td(hours=1)
    return TradeRecord(
        symbol=symbol,
        entry_signal_id=uuid4(),
        entry_ts=entry_ts,
        exit_ts=exit_ts,
        qty=Decimal("0.1"),
        entry_price=Decimal("50000"),
        exit_price=Decimal("51000") if pnl > 0 else Decimal("49000"),
        pnl_quote=pnl,
        pnl_pct=Decimal("0.02") if pnl > 0 else Decimal("-0.02"),
        fees_paid=Decimal("0.5"),
        reason_code=ReasonCode.EXIT_SL_HIT,
        kelly_phase=1,
        recorded_at=exit_ts,
    )


def test_consecutive_losses_returns_tail_streak(
    in_memory_trade_history: TradeHistoryRepository,
) -> None:
    """3 trailing losses (after a win) → consecutive_losses = 3."""
    repo = in_memory_trade_history
    base = datetime(2026, 1, 1, 12, tzinfo=UTC)
    repo.insert_closed_trade(_make_trade(symbol="BTCUSDT", pnl=Decimal("100"), exit_ts=base))
    repo.insert_closed_trade(
        _make_trade(symbol="BTCUSDT", pnl=Decimal("-50"), exit_ts=base + td(hours=1))
    )
    repo.insert_closed_trade(
        _make_trade(symbol="BTCUSDT", pnl=Decimal("-30"), exit_ts=base + td(hours=2))
    )
    repo.insert_closed_trade(
        _make_trade(symbol="BTCUSDT", pnl=Decimal("-20"), exit_ts=base + td(hours=3))
    )
    assert repo.consecutive_losses(symbol="BTCUSDT") == 3


def test_consecutive_losses_resets_on_winning_trade(
    in_memory_trade_history: TradeHistoryRepository,
) -> None:
    """Most-recent trade is WIN → consecutive_losses = 0."""
    repo = in_memory_trade_history
    base = datetime(2026, 1, 1, 12, tzinfo=UTC)
    repo.insert_closed_trade(_make_trade(symbol="BTCUSDT", pnl=Decimal("-50"), exit_ts=base))
    repo.insert_closed_trade(
        _make_trade(symbol="BTCUSDT", pnl=Decimal("-30"), exit_ts=base + td(hours=1))
    )
    repo.insert_closed_trade(
        _make_trade(symbol="BTCUSDT", pnl=Decimal("100"), exit_ts=base + td(hours=2))
    )
    assert repo.consecutive_losses(symbol="BTCUSDT") == 0


def test_consecutive_losses_symbol_scoped(in_memory_trade_history: TradeHistoryRepository) -> None:
    """consecutive_losses filters by symbol."""
    repo = in_memory_trade_history
    base = datetime(2026, 1, 1, 12, tzinfo=UTC)
    repo.insert_closed_trade(_make_trade(symbol="BTCUSDT", pnl=Decimal("-50"), exit_ts=base))
    repo.insert_closed_trade(
        _make_trade(symbol="BTCUSDT", pnl=Decimal("-30"), exit_ts=base + td(hours=1))
    )
    repo.insert_closed_trade(
        _make_trade(symbol="ETHUSDT", pnl=Decimal("100"), exit_ts=base + td(hours=2))
    )
    assert repo.consecutive_losses(symbol="BTCUSDT") == 2
    assert repo.consecutive_losses(symbol="ETHUSDT") == 0


def test_consecutive_losses_empty_table_returns_zero(
    in_memory_trade_history: TradeHistoryRepository,
) -> None:
    """No trades → 0."""
    assert in_memory_trade_history.consecutive_losses(symbol="BTCUSDT") == 0


def test_last_trade_ts_returns_max_exit_ts(in_memory_trade_history: TradeHistoryRepository) -> None:
    """last_trade_ts = MAX(exit_ts) per symbol."""
    repo = in_memory_trade_history
    base = datetime(2026, 1, 1, 12, tzinfo=UTC)
    repo.insert_closed_trade(_make_trade(symbol="BTCUSDT", pnl=Decimal("100"), exit_ts=base))
    repo.insert_closed_trade(
        _make_trade(symbol="BTCUSDT", pnl=Decimal("-50"), exit_ts=base + td(hours=2))
    )
    repo.insert_closed_trade(
        _make_trade(symbol="BTCUSDT", pnl=Decimal("100"), exit_ts=base + td(hours=1))
    )
    last = repo.last_trade_ts(symbol="BTCUSDT")
    assert last is not None
    assert last == base + td(hours=2)


def test_last_trade_ts_none_when_no_trades(in_memory_trade_history: TradeHistoryRepository) -> None:
    """No trades → None."""
    assert in_memory_trade_history.last_trade_ts(symbol="BTCUSDT") is None
