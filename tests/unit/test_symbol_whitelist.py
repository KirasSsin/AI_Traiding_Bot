"""S37 T2 — symbol whitelist + fail-closed semantic per ADR 0057 SD-1+SD-2+SD-3.

Critical: pre-S37 warn+skip silent bypass replaced с halt fail-closed.
"""

from __future__ import annotations

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


def _runtime(
    tmp_path: Path,
    *,
    symbol: str | None = "BTCUSDT",
    **settings_overrides: object,
) -> tuple[RuntimeManager, MagicMock]:
    from src.risk.manager import RiskSharedDeps

    settings = _settings(tmp_path, **settings_overrides)
    init_db(settings.db_path, _MIGRATIONS)
    conn = connect(settings.db_path)
    coord = MagicMock()
    coord.symbol = symbol
    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=MagicMock(return_value=True)),
        bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=settings,
        shared_deps=RiskSharedDeps(
            equity_tracker=EquityTracker(conn),
            trade_repo=TradeHistoryRepository(conn),
            state_repo=StateRepository(conn),
        ),
    )
    return rm, coord


def test_default_whitelist_is_btcusdt(tmp_path: Path) -> None:
    """ADR 0057 SD-3: default s35_demo_approved_symbols = [BTCUSDT]."""
    s = _settings(tmp_path)
    assert s.s35_demo_approved_symbols == ["BTCUSDT"]


def test_unknown_symbol_fails_closed_with_halt(tmp_path: Path) -> None:
    """ADR 0057 SD-2: unknown symbol → HALT_UNKNOWN_SYMBOL (NOT warn+skip)."""
    rm, coord = _runtime(tmp_path, symbol="ETHUSDT")  # NOT in default whitelist
    halted = rm._check_halt_gate()
    assert halted is True
    coord.request_halt.assert_called_once_with(ReasonCode.HALT_UNKNOWN_SYMBOL)


def test_none_symbol_fails_closed_with_halt(tmp_path: Path) -> None:
    """ADR 0057 SD-2: missing symbol (None) → HALT_UNKNOWN_SYMBOL."""
    rm, coord = _runtime(tmp_path, symbol=None)
    halted = rm._check_halt_gate()
    assert halted is True
    coord.request_halt.assert_called_once_with(ReasonCode.HALT_UNKNOWN_SYMBOL)


def test_whitelisted_symbol_proceeds(tmp_path: Path) -> None:
    """ADR 0057 SD-3: BTCUSDT в whitelist → no halt fired (no other trigger)."""
    rm, coord = _runtime(tmp_path, symbol="BTCUSDT")
    halted = rm._check_halt_gate()
    assert halted is False
    coord.request_halt.assert_not_called()


def test_custom_whitelist_extends_allowed_symbols(tmp_path: Path) -> None:
    """Operator can extend whitelist для multi-symbol future."""
    rm, coord = _runtime(
        tmp_path,
        symbol="ETHUSDT",
        s35_demo_approved_symbols=["BTCUSDT", "ETHUSDT"],
    )
    halted = rm._check_halt_gate()
    assert halted is False  # ETHUSDT now whitelisted
    coord.request_halt.assert_not_called()


def test_demo_inactive_skips_whitelist_check(tmp_path: Path) -> None:
    """S37 T2 trading-logic-reviewer C2: s35_demo_active=False MUST skip whitelist.

    Even с unknown symbol, demo inactive → return False без halt.
    Guards against future refactor accidentally re-ordering early-return.
    """
    rm, coord = _runtime(
        tmp_path,
        symbol="UNKNOWN",  # NOT в whitelist
        s35_demo_active=False,  # demo OFF
    )
    halted = rm._check_halt_gate()
    assert halted is False
    coord.request_halt.assert_not_called()


def test_whitelist_case_normalized_к_uppercase(tmp_path: Path) -> None:
    """S37 T2 security-auditor HIGH: operator typo (lowercase) normalized к uppercase.

    Pre-fix: STRATEGY_SYMBOL=BTCUSDT vs whitelist=[btcusdt] → silent halt loop.
    Post-fix: validator normalizes whitelist к uppercase at construction.
    """
    s = _settings(tmp_path, s35_demo_approved_symbols=["btcusdt", "ethusdt"])
    assert s.s35_demo_approved_symbols == ["BTCUSDT", "ETHUSDT"]


def test_lowercase_whitelist_matches_uppercase_symbol(tmp_path: Path) -> None:
    """Integration: lowercase whitelist input + uppercase coord symbol → no halt."""
    rm, coord = _runtime(
        tmp_path,
        symbol="BTCUSDT",
        s35_demo_approved_symbols=["btcusdt"],  # lowercase typo
    )
    halted = rm._check_halt_gate()
    assert halted is False  # normalized к BTCUSDT, matches coord
    coord.request_halt.assert_not_called()
