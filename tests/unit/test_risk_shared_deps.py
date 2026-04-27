"""S38 T4 — RiskSharedDeps Demeter refactor per ADR 0058 SD-3.

Per ROUND 6 architecture-reviewer Item #7 carry-over:
  RuntimeManager accesses risk_manager.equity_tracker / trade_repo / state_repo
  properties — Demeter violation. Bundle into RiskSharedDeps NamedTuple.

CONSTRAINT: DI wiring ONLY. NOT touch _tick() OR HaltGate.evaluate().
Backward-compat: individual kwargs к RuntimeManager still work.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.equity_tracker import EquityTracker
from src.risk.manager import RiskManager, RiskSharedDeps
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
    )


def test_risk_shared_deps_namedtuple_exposes_three_fields() -> None:
    """RiskSharedDeps bundle has equity_tracker + trade_repo + state_repo."""
    deps = RiskSharedDeps(
        equity_tracker=MagicMock(),
        trade_repo=MagicMock(),
        state_repo=MagicMock(),
    )
    assert deps.equity_tracker is not None
    assert deps.trade_repo is not None
    assert deps.state_repo is not None


def test_risk_manager_shared_deps_property_returns_namedtuple(tmp_path: Path) -> None:
    """RiskManager.shared_deps property returns RiskSharedDeps bundle."""
    settings = _settings(tmp_path)
    init_db(settings.db_path, _MIGRATIONS)
    conn = connect(settings.db_path)
    rm = RiskManager(conn=conn, settings=settings, symbol="BTCUSDT")
    deps = rm.shared_deps
    assert isinstance(deps, RiskSharedDeps)
    assert deps.equity_tracker is rm.equity_tracker
    assert deps.trade_repo is rm.trade_repo
    assert deps.state_repo is rm.state_repo


def test_runtime_manager_accepts_shared_deps_kwarg(tmp_path: Path) -> None:
    """RuntimeManager constructor accepts shared_deps=RiskSharedDeps (preferred path)."""
    settings = _settings(tmp_path)
    init_db(settings.db_path, _MIGRATIONS)
    conn = connect(settings.db_path)
    et = EquityTracker(conn)
    th = TradeHistoryRepository(conn)
    sr = StateRepository(conn)
    deps = RiskSharedDeps(equity_tracker=et, trade_repo=th, state_repo=sr)
    rm = RuntimeManager(
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        ws_consumer=MagicMock(),
        bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=settings,
        shared_deps=deps,
    )
    assert rm._equity_tracker is et
    assert rm._trade_repo is th
    assert rm._state_repo is sr


def test_runtime_manager_backward_compat_individual_kwargs_still_work(tmp_path: Path) -> None:
    """Backward-compat: existing call sites pass equity_tracker= directly."""
    settings = _settings(tmp_path)
    init_db(settings.db_path, _MIGRATIONS)
    conn = connect(settings.db_path)
    et = EquityTracker(conn)
    th = TradeHistoryRepository(conn)
    sr = StateRepository(conn)
    rm = RuntimeManager(
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        ws_consumer=MagicMock(),
        bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=settings,
        equity_tracker=et,
        trade_repo=th,
        state_repo=sr,
    )
    assert rm._equity_tracker is et
    assert rm._trade_repo is th
    assert rm._state_repo is sr


def test_runtime_manager_raises_if_neither_shared_deps_nor_individual_kwargs(
    tmp_path: Path,
) -> None:
    """Defensive: missing both paths → ValueError."""
    settings = _settings(tmp_path)
    with pytest.raises(ValueError, match="must provide shared_deps OR all of"):
        RuntimeManager(
            coordinator=MagicMock(),
            reconciler=MagicMock(),
            ws_consumer=MagicMock(),
            bar_source=MagicMock(),
            strategy=MagicMock(),
            risk_manager=MagicMock(),
            settings=settings,
            # NEITHER shared_deps NOR individual kwargs
        )
