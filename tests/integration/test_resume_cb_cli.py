"""Integration tests for resume_cb CLI — TDD RED."""

import argparse
import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.risk.resume_cb import main, parse_duration


# ---------------------------------------------------------------------------
# parse_duration
# ---------------------------------------------------------------------------


def test_parse_duration_1h():
    assert parse_duration("1h") == timedelta(hours=1)


def test_parse_duration_30m():
    assert parse_duration("30m") == timedelta(minutes=30)


def test_parse_duration_1d():
    assert parse_duration("1d") == timedelta(days=1)


def test_parse_duration_invalid_raises():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_duration("abc")


def test_parse_duration_no_unit_raises():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_duration("60")


# ---------------------------------------------------------------------------
# main() — happy path
# ---------------------------------------------------------------------------


def test_main_creates_override_file(tmp_path: Path):
    override_path = tmp_path / "state" / "cb_override.json"

    mock_settings = MagicMock()
    mock_settings.risk_override_path = override_path
    mock_settings.config_hash.return_value = "c" * 64

    with patch("src.risk.resume_cb.Settings", return_value=mock_settings):
        rc = main(["--level", "L2", "--reason", "test override", "--expires-in", "30m"])

    assert rc == 0
    assert override_path.exists()

    data = json.loads(override_path.read_text())
    assert data["level"] == "L2"
    assert data["reason"] == "test override"
    assert data["config_hash"] == "c" * 64


def test_main_default_expires_in(tmp_path: Path):
    """Default --expires-in is 1h."""
    override_path = tmp_path / "cb_override.json"

    mock_settings = MagicMock()
    mock_settings.risk_override_path = override_path
    mock_settings.config_hash.return_value = "d" * 64

    with patch("src.risk.resume_cb.Settings", return_value=mock_settings):
        rc = main(["--level", "FLASH", "--reason", "flash test"])

    assert rc == 0
    data = json.loads(override_path.read_text())
    from datetime import datetime, timezone

    created = datetime.fromisoformat(data["created_at"])
    expires = datetime.fromisoformat(data["expires_at"])
    delta = expires - created
    assert abs(delta.total_seconds() - 3600) < 5  # within 5s tolerance


def test_main_l3_level(tmp_path: Path):
    override_path = tmp_path / "cb_override.json"
    mock_settings = MagicMock()
    mock_settings.risk_override_path = override_path
    mock_settings.config_hash.return_value = "e" * 64

    with patch("src.risk.resume_cb.Settings", return_value=mock_settings):
        rc = main(["--level", "L3", "--reason", "drawdown breach", "--expires-in", "2h"])

    assert rc == 0
    data = json.loads(override_path.read_text())
    assert data["level"] == "L3"


# ---------------------------------------------------------------------------
# main() — invalid level (argparse exits)
# ---------------------------------------------------------------------------


def test_main_invalid_level_exits():
    with pytest.raises(SystemExit):
        main(["--level", "L99", "--reason", "bad"])
