"""S37 T4 — clock injection в _check_halt_gate per ADR 0057 SD-5.

Enables deterministic property tests (months_since calculation depends on clock).
Pattern matches RiskManager.__init__(clock=...) S8a precedent.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.equity_tracker import EquityTracker
from src.risk.reason_codes import ReasonCode
from src.risk.state_repo import StateRepository
from src.risk.trade_history import TradeHistoryRepository
from src.runtime.manager import RuntimeManager

_MIGRATIONS = Path(__file__).parents[2] / "migrations"


def _settings(tmp_path: Path) -> Settings:
    return Settings(  # type: ignore[arg-type]
        bybit_api_key="test_key_at_least_8",
        bybit_api_secret="test_secret_at_least_8",
        risk_override_hmac_key="test_key_min_32_chars_for_audit_h2_compliance",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "test.db",
        parquet_dir=tmp_path / "parquet",
        testnet=True,
        live_trading=False,
        s35_demo_active=True,
        s35_halt_dd_intraday=Decimal("0.20"),
        s35_halt_dd_multiday=Decimal("0.15"),
        s35_halt_consecutive_losses=5,
        s35_halt_no_trade_months=6,
    )


def _runtime(tmp_path: Path, *, clock=None) -> tuple[RuntimeManager, MagicMock]:
    settings = _settings(tmp_path)
    init_db(settings.db_path, _MIGRATIONS)
    conn = connect(settings.db_path)
    coord = MagicMock()
    coord.symbol = "BTCUSDT"
    kwargs = {
        "coordinator": coord,
        "reconciler": MagicMock(),
        "ws_consumer": MagicMock(check_alive=MagicMock(return_value=True)),
        "bar_source": MagicMock(),
        "strategy": MagicMock(),
        "risk_manager": MagicMock(),
        "settings": settings,
        "equity_tracker": EquityTracker(conn),
        "trade_repo": TradeHistoryRepository(conn),
        "state_repo": StateRepository(conn),
    }
    if clock is not None:
        kwargs["clock"] = clock
    rm = RuntimeManager(**kwargs)
    return rm, coord


def test_default_clock_is_datetime_now_utc(tmp_path: Path) -> None:
    """Default clock = datetime.now(UTC) — backward-compat preserved."""
    rm, _ = _runtime(tmp_path)
    # Verify default attribute set
    assert callable(rm._clock)
    # Default clock returns aware UTC datetime близко к real now
    now = rm._clock()
    real_now = datetime.now(UTC)
    delta = abs((now - real_now).total_seconds())
    assert delta < 1.0
    assert now.tzinfo is UTC


def test_injected_clock_used_for_activation_ts_persistence(tmp_path: Path) -> None:
    """ADR 0057 SD-5: injected clock controls activation_ts value на first call."""
    fixed_now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    rm, _ = _runtime(tmp_path, clock=lambda: fixed_now)
    rm._check_halt_gate()
    # Verify persisted activation_ts matches injected clock
    record = rm._state_repo.get_signed(
        "runtime:halt_gate:activation_ts",
        hmac_key=rm._settings.risk_override_hmac_key,
    )
    assert record is not None
    assert record["value"] == fixed_now.isoformat()


def test_injected_clock_drives_no_trade_timeout_calculation(tmp_path: Path) -> None:
    """ADR 0057 SD-5: clock determines months_since без real wall-clock dependency.

    Activation 7mo ago + clock=now → fires NO_TRADE_TIMEOUT deterministically.
    """
    fixed_now = datetime(2027, 1, 1, tzinfo=UTC)
    activation = fixed_now - timedelta(days=7 * 30)
    rm, coord = _runtime(tmp_path, clock=lambda: fixed_now)
    # Pre-seed activation_ts 7mo ago (signed)
    rm._state_repo.set_signed(
        "runtime:halt_gate:activation_ts",
        {"value": activation.isoformat()},
        hmac_key=rm._settings.risk_override_hmac_key,
    )
    halted = rm._check_halt_gate()
    assert halted is True
    coord.request_halt.assert_called_once_with(ReasonCode.HALT_S36_NO_TRADE_TIMEOUT)
