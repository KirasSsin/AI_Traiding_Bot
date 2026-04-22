"""Tests for StateRepository — TDD RED."""

import sqlite3
from datetime import datetime, timezone

import pytest

from src.risk.state_repo import StateRepository


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.execute(
        """CREATE TABLE state (
            key        TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    c.commit()
    return c


@pytest.fixture()
def repo(conn: sqlite3.Connection) -> StateRepository:
    return StateRepository(conn)


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_get_missing_key_returns_none(repo: StateRepository):
    assert repo.get("risk:cb:current_level") is None


# ---------------------------------------------------------------------------
# set + get roundtrip
# ---------------------------------------------------------------------------


def test_set_then_get_roundtrip(repo: StateRepository):
    repo.set("risk:kelly:phase", {"phase": 1})
    assert repo.get("risk:kelly:phase") == {"phase": 1}


def test_set_twice_overwrites(repo: StateRepository, conn: sqlite3.Connection):
    repo.set("risk:kelly:phase", {"phase": 1})
    ts1 = conn.execute("SELECT updated_at FROM state WHERE key = ?", ("risk:kelly:phase",)).fetchone()[0]

    repo.set("risk:kelly:phase", {"phase": 2})
    row = conn.execute("SELECT value_json, updated_at FROM state WHERE key = ?", ("risk:kelly:phase",)).fetchone()
    assert '"phase": 2' in row[0] or "2" in row[0]
    # updated_at should be >= ts1 (monotone)
    assert row[1] >= ts1


def test_set_nested_value(repo: StateRepository):
    payload = {"params": {"edge": "0.1", "kelly_fraction": "0.5"}}
    repo.set("risk:kelly:params", payload)
    assert repo.get("risk:kelly:params") == payload


# ---------------------------------------------------------------------------
# update_many
# ---------------------------------------------------------------------------


def test_update_many_all_committed(repo: StateRepository):
    updates = {
        "risk:cb:current_level": {"level": "L1"},
        "risk:kelly:phase": {"phase": 2},
        "risk:kelly:params": {"edge": "0.05"},
    }
    repo.update_many(updates)
    assert repo.get("risk:cb:current_level") == {"level": "L1"}
    assert repo.get("risk:kelly:phase") == {"phase": 2}
    assert repo.get("risk:kelly:params") == {"edge": "0.05"}


def test_update_many_empty_noop(repo: StateRepository, conn: sqlite3.Connection):
    repo.set("risk:kelly:phase", {"phase": 1})
    repo.update_many({})
    # existing key unchanged
    assert repo.get("risk:kelly:phase") == {"phase": 1}
    count = conn.execute("SELECT COUNT(*) FROM state").fetchone()[0]
    assert count == 1


def test_update_many_overwrites_existing(repo: StateRepository):
    repo.set("risk:kelly:phase", {"phase": 1})
    repo.update_many({"risk:kelly:phase": {"phase": 3}})
    assert repo.get("risk:kelly:phase") == {"phase": 3}


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_removes_key(repo: StateRepository):
    repo.set("risk:cb:current_level", {"level": "L1"})
    repo.delete("risk:cb:current_level")
    assert repo.get("risk:cb:current_level") is None


def test_delete_nonexistent_noop(repo: StateRepository):
    repo.delete("nonexistent:key")  # must not raise
