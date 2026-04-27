"""S35 Settings invariants (ADR 0053 + pre-s35-backlog pre-commitment #1)."""

from pathlib import Path

import pytest
from src.platform.config import Settings

_BASE_KW: dict[str, object] = {
    "bybit_api_key": "test_key_at_least_8",
    "bybit_api_secret": "test_secret_at_least_8",
    "risk_override_hmac_key": "0" * 64,
    "data_dir": Path("./data"),
    "log_dir": Path("./logs"),
    "db_path": Path("./bot.db"),
    "parquet_dir": Path("./data/parquet"),
}


def test_s35_demo_active_blocks_mainnet() -> None:
    """S35 pre-commit #1: δ TESTNET-only invariant.

    s35_demo_active=True + live_trading=True → ValueError BLOCKS Settings construction.
    """
    with pytest.raises(ValueError, match="S35 δ TESTNET demo cannot run на MAINNET"):
        Settings(
            **_BASE_KW,
            testnet=False,
            trading_enabled=True,
            live_trading=True,
            s35_demo_active=True,
        )


def test_s35_demo_active_with_testnet_ok() -> None:
    s = Settings(
        **_BASE_KW,
        testnet=True,
        live_trading=False,
        s35_demo_active=True,
    )
    assert s.s35_demo_active is True
    assert s.live_trading is False


def test_s35_demo_inactive_with_mainnet_ok() -> None:
    """live_trading=True OK когда s35_demo_active=False (no S35 invariant trigger)."""
    s = Settings(
        **_BASE_KW,
        testnet=False,
        trading_enabled=True,
        live_trading=True,
        s35_demo_active=False,
    )
    assert s.live_trading is True
    assert s.s35_demo_active is False
