"""ADR 0020 sub-decision 9: bootstrap discovers highest prior attempt# from exchange evidence,
so resume after crash never reuses an old orderLinkId."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow


@dataclass
class _FakeAdapter:
    open_orders_resp: list[dict] = field(default_factory=list)
    history_resp: list[dict] = field(default_factory=list)

    def get_open_orders(self, *, symbol):
        return list(self.open_orders_resp)

    def get_order_history(self, *, symbol, limit=50):
        return list(self.history_resp)


def _seed_repo(repo, *, bracket_id, last_attempt_num=1):
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.OCO_ARMED,
        position_qty=Decimal("0.001"),
        entry_price=Decimal("65000"),
        oco_main_order_id=None,
        bracket_id=bracket_id,
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=Decimal("0.001"),
        arming_started_at=None,
        last_attempt_num=last_attempt_num,
        updated_at="2026-04-23T10:00:00+00:00",
    ))


@pytest.fixture
def coordinator_with_history(tmp_path):
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    bracket_id = "abcd1234"
    _seed_repo(repo, bracket_id=bracket_id, last_attempt_num=1)
    adapter = _FakeAdapter(
        open_orders_resp=[],
        history_resp=[
            {"orderLinkId": f"oco-{bracket_id}-tp-1", "orderStatus": "Cancelled"},
            {"orderLinkId": f"oco-{bracket_id}-sl-2", "orderStatus": "Cancelled"},
            {"orderLinkId": f"oco-{bracket_id}-tp-2", "orderStatus": "Cancelled"},
            {"orderLinkId": "oco-other-tp-9", "orderStatus": "Cancelled"},  # different bracket
            {"orderLinkId": "not-an-oco-link", "orderStatus": "Filled"},   # noise
        ],
    )
    coord = Coordinator(adapter=adapter, repo=repo, reconciler=None,
                        symbol="BTCUSDT", base_coin="BTC")
    return type("H", (), {"adapter": adapter, "repo": repo, "coordinator": coord,
                           "bracket_id": bracket_id})()


@pytest.fixture
def coordinator_clean(tmp_path):
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    bracket_id = "cleanid1"
    _seed_repo(repo, bracket_id=bracket_id, last_attempt_num=1)
    adapter = _FakeAdapter()  # no open orders, no history
    coord = Coordinator(adapter=adapter, repo=repo, reconciler=None,
                        symbol="BTCUSDT", base_coin="BTC")
    return type("H", (), {"adapter": adapter, "repo": repo, "coordinator": coord,
                           "bracket_id": bracket_id})()


def test_bootstrap_detects_prior_attempt_from_history(coordinator_with_history):
    h = coordinator_with_history
    h.coordinator.bootstrap()
    row = h.repo.get("BTCUSDT")
    assert row.last_attempt_num == 2  # highest seen for our bracket_id


def test_bootstrap_no_prior_attempts_keeps_existing_attempt(coordinator_clean):
    h = coordinator_clean
    h.coordinator.bootstrap()
    row = h.repo.get("BTCUSDT")
    assert row.last_attempt_num == 1  # unchanged (no evidence to bump)


def test_bootstrap_no_bracket_id_is_noop(tmp_path):
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    # No row at all
    coord = Coordinator(adapter=_FakeAdapter(), repo=repo, reconciler=None,
                        symbol="BTCUSDT", base_coin="BTC")
    coord.bootstrap()  # should not raise
    assert repo.get("BTCUSDT") is None
