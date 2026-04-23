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
    mock_settings.risk_override_hmac_key = "k" * 32
    mock_settings.config_hash.return_value = "c" * 64

    with patch("src.risk.resume_cb.Settings", return_value=mock_settings):
        rc = main(["--level", "L2", "--reason", "test override", "--expires-in", "30m"])

    assert rc == 0
    assert override_path.exists()

    # ADR 0018 sub-decision 9 (audit H2) — file is now an HMAC envelope:
    # {"payload": <CbOverride JSON>, "sig": <hex>}.
    envelope = json.loads(override_path.read_text())
    assert "sig" in envelope
    payload = envelope["payload"]
    assert payload["level"] == "L2"
    assert payload["reason"] == "test override"
    assert payload["config_hash"] == "c" * 64


def test_main_default_expires_in(tmp_path: Path):
    """Default --expires-in is 1h."""
    override_path = tmp_path / "cb_override.json"

    mock_settings = MagicMock()
    mock_settings.risk_override_path = override_path
    mock_settings.risk_override_hmac_key = "k" * 32
    mock_settings.config_hash.return_value = "d" * 64

    with patch("src.risk.resume_cb.Settings", return_value=mock_settings):
        rc = main(["--level", "FLASH", "--reason", "flash test"])

    assert rc == 0
    payload = json.loads(override_path.read_text())["payload"]
    from datetime import datetime

    created = datetime.fromisoformat(payload["created_at"])
    expires = datetime.fromisoformat(payload["expires_at"])
    delta = expires - created
    assert abs(delta.total_seconds() - 3600) < 5  # within 5s tolerance


def test_main_l3_level(tmp_path: Path):
    override_path = tmp_path / "cb_override.json"
    mock_settings = MagicMock()
    mock_settings.risk_override_path = override_path
    mock_settings.risk_override_hmac_key = "k" * 32
    mock_settings.config_hash.return_value = "e" * 64

    with patch("src.risk.resume_cb.Settings", return_value=mock_settings):
        rc = main(["--level", "L3", "--reason", "drawdown breach", "--expires-in", "2h"])

    assert rc == 0
    payload = json.loads(override_path.read_text())["payload"]
    assert payload["level"] == "L3"


def test_main_does_not_print_override_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Audit L3 (CWE-532) — absolute override path must not appear in stdout."""
    override_path = tmp_path / "secret_dir" / "cb_override.json"
    mock_settings = MagicMock()
    mock_settings.risk_override_path = override_path
    mock_settings.risk_override_hmac_key = "k" * 32
    mock_settings.config_hash.return_value = "f" * 64

    with patch("src.risk.resume_cb.Settings", return_value=mock_settings):
        main(["--level", "L2", "--reason", "no leak", "--expires-in", "30m"])

    captured = capsys.readouterr()
    assert str(override_path) not in captured.out
    assert "secret_dir" not in captured.out


# ---------------------------------------------------------------------------
# main() — invalid level (argparse exits)
# ---------------------------------------------------------------------------


def test_main_invalid_level_exits():
    with pytest.raises(SystemExit):
        main(["--level", "L99", "--reason", "bad"])
