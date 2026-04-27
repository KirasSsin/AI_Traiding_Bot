"""S36 T4: HaltGate wire-up в RuntimeManager._tick integration tests.

Per ADR 0055 SD-4 — HaltTrigger → ReasonCode dispatch verification.
Coverage:
  1. DD_INTRADAY trigger → HALT_S36_DD_INTRADAY
  2. CONSECUTIVE_LOSSES trigger → HALT_S36_CONSECUTIVE_LOSSES
  3. No-trigger path → returns False, no halt
  4. Demo-inactive bypass → returns False without computation
  5. activation_ts persisted on first call, NOT overwritten on subsequent
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.equity_tracker import EquityTracker
from src.risk.reason_codes import ReasonCode
from src.risk.state_repo import StateRepository
from src.risk.trade_history import TradeHistoryRepository, TradeRecord
from src.runtime.manager import RuntimeManager

_MIGRATIONS = Path(__file__).parents[2] / "migrations"


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    base: dict[str, object] = {
        "bybit_api_key": "test_key_at_least_8",
        "bybit_api_secret": "test_secret_at_least_8",
        "risk_override_hmac_key": "test_key_min_32_chars_for_audit_h2_compliance",
        "data_dir": tmp_path / "data",
        "log_dir": tmp_path / "logs",
        "db_path": tmp_path / "test.db",
        "parquet_dir": tmp_path / "parquet",
        "testnet": True,
        "live_trading": False,
        "s35_demo_active": True,
        "s35_halt_dd_intraday": Decimal("0.20"),
        "s35_halt_dd_multiday": Decimal("0.15"),
        "s35_halt_consecutive_losses": 5,
        "s35_halt_no_trade_months": 6,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.fixture
def runtime_with_demo_active(
    tmp_path: Path,
) -> tuple[RuntimeManager, MagicMock, EquityTracker, TradeHistoryRepository]:
    settings = _settings(tmp_path)
    init_db(settings.db_path, _MIGRATIONS)
    conn = connect(settings.db_path)

    et = EquityTracker(conn)
    th = TradeHistoryRepository(conn)
    sr = StateRepository(conn)

    coord = MagicMock()
    coord._symbol = "BTCUSDT"

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=MagicMock(return_value=True)),
        bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=settings,
        equity_tracker=et,
        trade_repo=th,
        state_repo=sr,
    )
    return rm, coord, et, th


def test_halt_gate_dd_intraday_fires_request_halt(
    runtime_with_demo_active: tuple[
        RuntimeManager, MagicMock, EquityTracker, TradeHistoryRepository
    ],
) -> None:
    rm, coord, et, _ = runtime_with_demo_active
    # Use timestamps near real now() — intraday_dd_pct queries trailing 24h window
    # via datetime.now(UTC). Outdated test fixtures (e.g. 2026-01-01) miss the window.
    now = datetime.now(UTC)
    et.record(
        realized=Decimal("1000"),
        unrealized=Decimal("0"),
        ts=now - timedelta(hours=3),
        source="MANUAL",
    )
    et.record(
        realized=Decimal("1000"),
        unrealized=Decimal("250"),
        ts=now - timedelta(hours=2),
        source="MANUAL",
    )
    # Drop > 20%: peak 1250 → current 980 (dd ~21.6%)
    et.record(
        realized=Decimal("980"),
        unrealized=Decimal("0"),
        ts=now - timedelta(hours=1),
        source="MANUAL",
    )
    halted = rm._check_halt_gate()
    assert halted is True
    coord.request_halt.assert_called_once_with(ReasonCode.HALT_S36_DD_INTRADAY)


def test_halt_gate_consecutive_losses_fires(
    runtime_with_demo_active: tuple[
        RuntimeManager, MagicMock, EquityTracker, TradeHistoryRepository
    ],
) -> None:
    rm, coord, _, th = runtime_with_demo_active
    base = datetime(2026, 1, 1, 12, tzinfo=UTC)
    for i in range(5):
        rec = TradeRecord(
            symbol="BTCUSDT",
            entry_signal_id=uuid4(),
            entry_ts=base + timedelta(hours=i),
            exit_ts=base + timedelta(hours=i, minutes=30),
            qty=Decimal("0.1"),
            entry_price=Decimal("50000"),
            exit_price=Decimal("49000"),
            pnl_quote=Decimal("-100"),
            pnl_pct=Decimal("-0.02"),
            fees_paid=Decimal("0.5"),
            reason_code=ReasonCode.EXIT_SL_HIT,
            kelly_phase=1,
            recorded_at=base + timedelta(hours=i, minutes=30),
        )
        th.insert_closed_trade(rec)
    halted = rm._check_halt_gate()
    assert halted is True
    coord.request_halt.assert_called_once_with(ReasonCode.HALT_S36_CONSECUTIVE_LOSSES)


def test_halt_gate_no_trigger_returns_false(
    runtime_with_demo_active: tuple[
        RuntimeManager, MagicMock, EquityTracker, TradeHistoryRepository
    ],
) -> None:
    rm, coord, et, _ = runtime_with_demo_active
    base = datetime(2026, 1, 1, 0, tzinfo=UTC)
    et.record(realized=Decimal("1000"), unrealized=Decimal("0"), ts=base, source="MANUAL")
    halted = rm._check_halt_gate()
    assert halted is False
    coord.request_halt.assert_not_called()


def test_halt_gate_inactive_when_demo_disabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, s35_demo_active=False)
    init_db(settings.db_path, _MIGRATIONS)
    conn = connect(settings.db_path)
    coord = MagicMock()
    coord._symbol = "BTCUSDT"
    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=MagicMock(return_value=True)),
        bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=settings,
        equity_tracker=EquityTracker(conn),
        trade_repo=TradeHistoryRepository(conn),
        state_repo=StateRepository(conn),
    )
    halted = rm._check_halt_gate()
    assert halted is False
    coord.request_halt.assert_not_called()


def test_halt_gate_activation_ts_persisted_on_first_call(
    runtime_with_demo_active: tuple[
        RuntimeManager, MagicMock, EquityTracker, TradeHistoryRepository
    ],
) -> None:
    rm, _, _, _ = runtime_with_demo_active
    rm._check_halt_gate()
    activation = rm._state_repo.get("runtime:halt_gate:activation_ts")
    assert activation is not None
    assert "value" in activation
    # Subsequent call should not overwrite
    first_ts = activation["value"]
    rm._check_halt_gate()
    activation2 = rm._state_repo.get("runtime:halt_gate:activation_ts")
    assert activation2 is not None
    assert activation2["value"] == first_ts


def test_halt_gate_dd_multiday_fires(
    runtime_with_demo_active: tuple[
        RuntimeManager, MagicMock, EquityTracker, TradeHistoryRepository
    ],
) -> None:
    """S36 T4 trading-logic-reviewer C1: missing direct integration test for DD_MULTIDAY.

    HWM since activation_ts = 1500 → current = 1200 → multiday_dd = 20% > 15% threshold.
    Intraday window 24h carries только current = no intraday DD competing.
    """
    rm, coord, et, _ = runtime_with_demo_active
    now = datetime.now(UTC)
    # Pre-seed activation_ts 3 days ago — equity records placed AFTER activation
    activation = now - timedelta(days=3)
    rm._state_repo.set("runtime:halt_gate:activation_ts", {"value": activation.isoformat()})
    # Peak 1500 (2 days ago, > 24h window — outside intraday but inside multiday)
    et.record(
        realized=Decimal("1500"),
        unrealized=Decimal("0"),
        ts=now - timedelta(days=2),
        source="MANUAL",
    )
    # Current 1200 (now, inside 24h window)
    et.record(
        realized=Decimal("1200"),
        unrealized=Decimal("0"),
        ts=now,
        source="MANUAL",
    )
    halted = rm._check_halt_gate()
    assert halted is True
    coord.request_halt.assert_called_once_with(ReasonCode.HALT_S36_DD_MULTIDAY)


def test_halt_gate_no_trade_timeout_fires_after_activation(
    runtime_with_demo_active: tuple[
        RuntimeManager, MagicMock, EquityTracker, TradeHistoryRepository
    ],
) -> None:
    """S36 T4 trading-logic-reviewer C1: missing direct integration test для NO_TRADE_TIMEOUT.

    No trades + activation_ts > 6mo ago (pre-seeded в state_repo) → fires NO_TRADE_TIMEOUT.
    """
    rm, coord, _, _ = runtime_with_demo_active
    seven_months_ago = datetime.now(UTC) - timedelta(days=7 * 30)
    rm._state_repo.set("runtime:halt_gate:activation_ts", {"value": seven_months_ago.isoformat()})
    halted = rm._check_halt_gate()
    assert halted is True
    coord.request_halt.assert_called_once_with(ReasonCode.HALT_S36_NO_TRADE_TIMEOUT)
