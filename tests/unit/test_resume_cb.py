"""Unit coverage for resume_cb CLI — risk-critical resume-after-circuit-breaker (S49 H9).

`src/risk/resume_cb.py` is the operator CLI that issues a manual circuit-breaker
override (the "resume" lever). Its 31 statements were only exercised by the opt-in
integration test `tests/integration/test_resume_cb_cli.py`, which CI does not gate
on — leaving the live resume path 0% covered in the unit suite.

These tests are CLI/DB-independent: `Settings` and `OverrideStore` writes are
redirected to a `tmp_path` mock, so no live config or real override file is touched.
They assert the override-eligibility contract (level/reason/expiry are persisted as a
signed envelope) and the argparse boundaries (invalid level/duration rejected, audit
L3 path-leak guard).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.risk.resume_cb import main, parse_duration

# ---------------------------------------------------------------------------
# parse_duration — duration grammar (NNh | NNm | NNd)
# ---------------------------------------------------------------------------


def test_parse_duration_hours() -> None:
    assert parse_duration("1h") == timedelta(hours=1)
    assert parse_duration("12h") == timedelta(hours=12)


def test_parse_duration_minutes() -> None:
    assert parse_duration("30m") == timedelta(minutes=30)


def test_parse_duration_days() -> None:
    assert parse_duration("2d") == timedelta(days=2)


def test_parse_duration_invalid_word_raises() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_duration("abc")


def test_parse_duration_missing_unit_raises() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_duration("60")


def test_parse_duration_unknown_unit_raises() -> None:
    """Seconds suffix is not part of the grammar."""
    with pytest.raises(argparse.ArgumentTypeError):
        parse_duration("10s")


# ---------------------------------------------------------------------------
# main() helper — build a Settings mock pointed at a tmp override path
# ---------------------------------------------------------------------------


def _mock_settings(override_path: Path, config_hash: str = "c" * 64) -> MagicMock:
    settings = MagicMock()
    settings.risk_override_path = override_path
    settings.risk_override_hmac_key = "k" * 32
    settings.config_hash.return_value = config_hash
    return settings


# ---------------------------------------------------------------------------
# main() — resume-eligible (override written) happy path
# ---------------------------------------------------------------------------


def test_main_writes_signed_override_envelope(tmp_path: Path) -> None:
    """Resume-eligible path: a valid level/reason produces a signed override file."""
    override_path = tmp_path / "state" / "cb_override.json"
    with patch("src.risk.resume_cb.Settings", return_value=_mock_settings(override_path)):
        rc = main(["--level", "L2", "--reason", "operator resume", "--expires-in", "30m"])

    assert rc == 0
    assert override_path.exists()
    envelope = json.loads(override_path.read_text())
    # HMAC envelope shape (ADR 0018 sub-decision 9 / audit H2).
    assert set(envelope) == {"payload", "sig"}
    assert isinstance(envelope["sig"], str) and len(envelope["sig"]) == 64  # SHA-256 hex
    payload = envelope["payload"]
    assert payload["level"] == "L2"
    assert payload["reason"] == "operator resume"
    assert payload["config_hash"] == "c" * 64


@pytest.mark.parametrize("level", ["L2", "L3", "FLASH"])
def test_main_accepts_each_override_level(tmp_path: Path, level: str) -> None:
    """All three eligible override levels round-trip into the payload."""
    override_path = tmp_path / f"cb_override_{level}.json"
    with patch("src.risk.resume_cb.Settings", return_value=_mock_settings(override_path)):
        rc = main(["--level", level, "--reason", "lvl test", "--expires-in", "1h"])

    assert rc == 0
    payload = json.loads(override_path.read_text())["payload"]
    assert payload["level"] == level


def test_main_default_expiry_is_one_hour(tmp_path: Path) -> None:
    """Omitting --expires-in yields a 1h window (created_at → expires_at)."""
    override_path = tmp_path / "cb_override.json"
    with patch("src.risk.resume_cb.Settings", return_value=_mock_settings(override_path)):
        rc = main(["--level", "FLASH", "--reason", "default expiry"])

    assert rc == 0
    payload = json.loads(override_path.read_text())["payload"]
    created = datetime.fromisoformat(payload["created_at"])
    expires = datetime.fromisoformat(payload["expires_at"])
    assert abs((expires - created).total_seconds() - 3600) < 5


def test_main_custom_expiry_window(tmp_path: Path) -> None:
    override_path = tmp_path / "cb_override.json"
    with patch("src.risk.resume_cb.Settings", return_value=_mock_settings(override_path)):
        rc = main(["--level", "L3", "--reason", "2h window", "--expires-in", "2h"])

    assert rc == 0
    payload = json.loads(override_path.read_text())["payload"]
    created = datetime.fromisoformat(payload["created_at"])
    expires = datetime.fromisoformat(payload["expires_at"])
    assert abs((expires - created).total_seconds() - 7200) < 5


def test_main_overwrites_previous_override(tmp_path: Path) -> None:
    """Issuing a second override (already-resumed edge) replaces the file atomically."""
    override_path = tmp_path / "cb_override.json"
    with patch("src.risk.resume_cb.Settings", return_value=_mock_settings(override_path)):
        main(["--level", "L2", "--reason", "first", "--expires-in", "1h"])
        main(["--level", "FLASH", "--reason", "second", "--expires-in", "1h"])

    payload = json.loads(override_path.read_text())["payload"]
    assert payload["level"] == "FLASH"
    assert payload["reason"] == "second"


# ---------------------------------------------------------------------------
# main() — resume INELIGIBLE / rejected inputs (argparse exits non-zero)
# ---------------------------------------------------------------------------


def test_main_invalid_level_rejected() -> None:
    """A level outside {L2,L3,FLASH} is blocked (no override written)."""
    with pytest.raises(SystemExit):
        main(["--level", "L99", "--reason", "bad level"])


def test_main_missing_reason_rejected() -> None:
    """--reason is required (audit trail must record why the CB was overridden)."""
    with pytest.raises(SystemExit):
        main(["--level", "L2"])


def test_main_missing_level_rejected() -> None:
    with pytest.raises(SystemExit):
        main(["--reason", "no level"])


def test_main_invalid_duration_rejected() -> None:
    """A malformed --expires-in is blocked by the parse_duration type."""
    with pytest.raises(SystemExit):
        main(["--level", "L2", "--reason", "bad dur", "--expires-in", "soon"])


# ---------------------------------------------------------------------------
# main() — audit L3 (CWE-532): override path must not leak to stdout
# ---------------------------------------------------------------------------


def test_main_does_not_leak_override_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    override_path = tmp_path / "secret_dir" / "cb_override.json"
    with patch("src.risk.resume_cb.Settings", return_value=_mock_settings(override_path)):
        rc = main(["--level", "L2", "--reason", "no leak", "--expires-in", "30m"])

    assert rc == 0
    out = capsys.readouterr().out
    assert str(override_path) not in out
    assert "secret_dir" not in out
    # But the operator-facing summary still confirms the level + expiry.
    assert "level=L2" in out
