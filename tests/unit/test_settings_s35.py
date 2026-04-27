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


def test_s35_demo_active_blocks_testnet_false() -> None:
    """S35 T2 security-auditor HIGH #2: testnet=False alone routes к MAINNET endpoint.

    Even с live_trading=False, Bybit adapter routes by testnet flag.
    s35_demo_active=True + testnet=False → BLOCK construction.
    """
    with pytest.raises(ValueError, match="S35 δ TESTNET demo requires testnet=True"):
        Settings(
            **_BASE_KW,
            testnet=False,
            live_trading=False,
            s35_demo_active=True,
        )


def test_s35_demo_active_runtime_mutation_blocked() -> None:
    """S35 T2 security-auditor HIGH #1: validate_assignment blocks post-construction bypass.

    Settings constructed valid (testnet=True + s35_demo_active=True), then attempt
    к flip live_trading=True at runtime → ValidationError, не silent acceptance.
    """
    from pydantic import ValidationError

    s = Settings(
        **_BASE_KW,
        testnet=True,
        live_trading=False,
        s35_demo_active=True,
    )
    # Runtime mutation must re-trigger validators per validate_assignment=True
    with pytest.raises(ValidationError):
        s.live_trading = True


def test_s35_demo_active_runtime_testnet_flip_blocked() -> None:
    """validate_assignment also catches testnet flip after construction."""
    from pydantic import ValidationError

    s = Settings(
        **_BASE_KW,
        testnet=True,
        live_trading=False,
        s35_demo_active=True,
    )
    with pytest.raises(ValidationError):
        s.testnet = False
