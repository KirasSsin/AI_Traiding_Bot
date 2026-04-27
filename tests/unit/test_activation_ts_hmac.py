"""S37 T3 — activation_ts HMAC integrity per ADR 0057 SD-4 + ADR 0018 H2 pattern.

Without HMAC: attacker/operator rollback SQLite value resets multiday HWM window,
defeats halt enforcement.

Post-fix: tampered value raises ValueError на read → halt path triggered.
"""

from pathlib import Path

import pytest
from src.platform.db import connect, init_db
from src.risk.state_repo import StateRepository

_MIGRATIONS = Path(__file__).parents[2] / "migrations"
_HMAC_KEY = "test_key_min_32_chars_for_audit_h2_compliance"


@pytest.fixture
def state_repo(tmp_path: Path) -> StateRepository:
    db_path = tmp_path / "test.db"
    init_db(db_path, _MIGRATIONS)
    conn = connect(db_path)
    return StateRepository(conn)


def test_set_signed_persists_envelope_with_signature(state_repo: StateRepository) -> None:
    """ADR 0057 SD-4: set_signed wraps value в HMAC envelope."""
    state_repo.set_signed(
        "runtime:halt_gate:activation_ts",
        {"value": "2026-04-27T12:00:00+00:00"},
        hmac_key=_HMAC_KEY,
    )
    raw = state_repo.get("runtime:halt_gate:activation_ts")
    assert raw is not None
    assert "payload" in raw
    assert "sig" in raw
    assert raw["payload"] == {"value": "2026-04-27T12:00:00+00:00"}
    assert len(raw["sig"]) == 64  # HMAC-SHA256 hex


def test_get_signed_returns_payload_when_signature_valid(state_repo: StateRepository) -> None:
    """Round-trip: set_signed → get_signed returns original payload."""
    payload = {"value": "2026-04-27T12:00:00+00:00"}
    state_repo.set_signed("runtime:halt_gate:activation_ts", payload, hmac_key=_HMAC_KEY)
    result = state_repo.get_signed("runtime:halt_gate:activation_ts", hmac_key=_HMAC_KEY)
    assert result == payload


def test_get_signed_returns_none_when_key_missing(state_repo: StateRepository) -> None:
    """Missing key → None (caller knows к initialize)."""
    result = state_repo.get_signed("runtime:halt_gate:activation_ts", hmac_key=_HMAC_KEY)
    assert result is None


def test_get_signed_raises_on_tampered_payload(state_repo: StateRepository) -> None:
    """ADR 0057 SD-4: tampered SQLite value raises ValueError."""
    # Set valid signed value
    state_repo.set_signed(
        "runtime:halt_gate:activation_ts",
        {"value": "2026-04-27T12:00:00+00:00"},
        hmac_key=_HMAC_KEY,
    )
    # Tamper directly via .set (replaces envelope с different payload, OLD sig)
    state_repo.set(
        "runtime:halt_gate:activation_ts",
        {"payload": {"value": "2026-01-01T00:00:00+00:00"}, "sig": "0" * 64},  # wrong sig
    )
    with pytest.raises(ValueError, match="HMAC"):
        state_repo.get_signed("runtime:halt_gate:activation_ts", hmac_key=_HMAC_KEY)


def test_get_signed_raises_on_missing_envelope_fields(state_repo: StateRepository) -> None:
    """Bare value (no payload/sig wrapper) raises ValueError."""
    state_repo.set("runtime:halt_gate:activation_ts", {"value": "raw_no_envelope"})
    with pytest.raises(ValueError, match="HMAC envelope"):
        state_repo.get_signed("runtime:halt_gate:activation_ts", hmac_key=_HMAC_KEY)


def test_get_signed_raises_on_wrong_key(state_repo: StateRepository) -> None:
    """Different HMAC key fails verification (sig mismatch)."""
    state_repo.set_signed(
        "runtime:halt_gate:activation_ts",
        {"value": "2026-04-27T12:00:00+00:00"},
        hmac_key=_HMAC_KEY,
    )
    wrong_key = "wrong_key_min_32_chars_different_from_original_"
    with pytest.raises(ValueError, match="HMAC"):
        state_repo.get_signed("runtime:halt_gate:activation_ts", hmac_key=wrong_key)
