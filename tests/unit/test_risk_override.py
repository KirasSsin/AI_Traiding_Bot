"""Tests for OverrideStore and CbOverride — TDD RED."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.risk.override import CbOverride, OverrideStore


_NOW = datetime(2026, 4, 23, 12, 0, 0, tzinfo=timezone.utc)
_HASH = "a" * 64


def _make_override(**kwargs) -> CbOverride:
    defaults = dict(
        level="L2",
        reason="test reason",
        config_hash=_HASH,
        created_at=_NOW,
        expires_at=_NOW + timedelta(hours=1),
    )
    defaults.update(kwargs)
    return CbOverride(**defaults)


# ---------------------------------------------------------------------------
# CbOverride — Pydantic validation
# ---------------------------------------------------------------------------


def test_pydantic_bad_level_raises():
    with pytest.raises(ValidationError):
        CbOverride(
            level="L99",
            reason="test",
            config_hash=_HASH,
            created_at=_NOW,
            expires_at=_NOW + timedelta(hours=1),
        )


def test_pydantic_expires_before_created_allowed():
    """Caller responsibility — model does not enforce order."""
    ov = CbOverride(
        level="L3",
        reason="test",
        config_hash=_HASH,
        created_at=_NOW,
        expires_at=_NOW - timedelta(hours=1),
    )
    assert ov.expires_at < ov.created_at


def test_pydantic_empty_reason_raises():
    with pytest.raises(ValidationError):
        CbOverride(
            level="L2",
            reason="",
            config_hash=_HASH,
            created_at=_NOW,
            expires_at=_NOW + timedelta(hours=1),
        )


def test_pydantic_short_hash_raises():
    with pytest.raises(ValidationError):
        CbOverride(
            level="L2",
            reason="ok",
            config_hash="abc",
            created_at=_NOW,
            expires_at=_NOW + timedelta(hours=1),
        )


# ---------------------------------------------------------------------------
# OverrideStore — write + read roundtrip
# ---------------------------------------------------------------------------


def test_write_read_roundtrip(tmp_path: Path):
    store = OverrideStore(tmp_path / "cb_override.json")
    ov = _make_override()
    store.write(override=ov)
    result = store.read_active(now=_NOW - timedelta(seconds=1), expected_config_hash=_HASH)
    assert result == ov


def test_read_active_missing_file(tmp_path: Path):
    store = OverrideStore(tmp_path / "missing.json")
    assert store.read_active(now=_NOW, expected_config_hash=_HASH) is None


def test_read_active_hash_mismatch(tmp_path: Path):
    store = OverrideStore(tmp_path / "cb_override.json")
    store.write(override=_make_override())
    result = store.read_active(now=_NOW, expected_config_hash="b" * 64)
    assert result is None


def test_read_active_expired(tmp_path: Path):
    store = OverrideStore(tmp_path / "cb_override.json")
    ov = _make_override(
        created_at=_NOW - timedelta(hours=2),
        expires_at=_NOW - timedelta(hours=1),
    )
    store.write(override=ov)
    result = store.read_active(now=_NOW, expected_config_hash=_HASH)
    assert result is None


def test_read_active_exactly_at_expiry(tmp_path: Path):
    """now >= expires_at → expired."""
    store = OverrideStore(tmp_path / "cb_override.json")
    ov = _make_override(expires_at=_NOW)
    store.write(override=ov)
    result = store.read_active(now=_NOW, expected_config_hash=_HASH)
    assert result is None


# ---------------------------------------------------------------------------
# OverrideStore — consume
# ---------------------------------------------------------------------------


def test_consume_renames_file(tmp_path: Path):
    path = tmp_path / "cb_override.json"
    store = OverrideStore(path)
    ov = _make_override()
    store.write(override=ov)
    assert path.exists()
    store.consume(override=ov)
    assert not path.exists()
    consumed = list(tmp_path.glob("cb_override.consumed.*.json"))
    assert len(consumed) == 1


def test_consume_noop_if_no_file(tmp_path: Path):
    store = OverrideStore(tmp_path / "cb_override.json")
    ov = _make_override()
    store.consume(override=ov)  # must not raise


def test_write_creates_parent_dirs(tmp_path: Path):
    path = tmp_path / "deep" / "nested" / "cb_override.json"
    store = OverrideStore(path)
    store.write(override=_make_override())
    assert path.exists()
