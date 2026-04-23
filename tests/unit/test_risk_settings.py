"""Tests for risk-related Settings fields and config_hash()."""

from decimal import Decimal
from pathlib import Path

import pytest
from src.platform.config import Settings


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "bot.db",
        parquet_dir=tmp_path / "parquet",
        risk_override_path=tmp_path / "state" / "cb_override.json",
    )


def test_risk_defaults_present(settings: Settings) -> None:
    assert settings.risk_max_position_pct_cap == Decimal("0.05")
    assert settings.risk_sl_atr_multiplier == Decimal("1.5")
    assert settings.risk_tp_atr_multiplier == Decimal("3.0")
    assert settings.risk_cb_l1_dd == Decimal("0.15")
    assert settings.risk_cb_l2_dd == Decimal("0.22")
    assert settings.risk_cb_l3_dd == Decimal("0.30")
    assert settings.risk_cb_flash_abs == Decimal("0.08")
    assert settings.risk_cb_flash_atr_mult == Decimal("3.0")
    assert settings.risk_kelly_phase1_cap == Decimal("0.01")
    assert settings.risk_kelly_phase2_cap == Decimal("0.02")
    assert settings.risk_kelly_phase3_cap == Decimal("0.03")
    assert settings.risk_kelly_phase4_cap == Decimal("0.05")


def test_risk_override_path_type(settings: Settings) -> None:
    assert isinstance(settings.risk_override_path, Path)


def test_config_hash_is_deterministic(settings: Settings) -> None:
    h1 = settings.config_hash()
    h2 = settings.config_hash()
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_config_hash_changes_with_value(tmp_path: Path) -> None:
    s1 = Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "bot.db",
        parquet_dir=tmp_path / "parquet",
        risk_override_path=tmp_path / "state" / "cb_override.json",
        risk_cb_l1_dd=Decimal("0.15"),
    )
    s2 = Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "bot.db",
        parquet_dir=tmp_path / "parquet",
        risk_override_path=tmp_path / "state" / "cb_override.json",
        risk_cb_l1_dd=Decimal("0.20"),  # changed
    )
    assert s1.config_hash() != s2.config_hash()
