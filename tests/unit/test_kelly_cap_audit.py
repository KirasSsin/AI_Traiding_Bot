"""Pre-commit #2 audit: Kelly phase3/4 caps must NOT exceed 0.25× formula multiplier.

Per S35 ROUND 3 binding (pre-s35-backlog.md):
  Quarter-Kelly (phase3) and Half-Kelly (phase4) hard caps must remain ≤ 0.25
  to bound tail risk during δ TESTNET live demo.
"""

from decimal import Decimal

from src.platform.config import Settings

_BASE = dict(
    bybit_api_key="test_api_key_value",
    bybit_api_secret="test_api_secret_value",  # noqa: S105 — test fixture, not a real secret
    risk_override_hmac_key="0" * 64,
)


def test_kelly_phase3_cap_not_exceeds_0_25():
    settings = Settings(**_BASE)
    assert settings.risk_kelly_phase3_cap <= Decimal("0.25"), (
        f"Phase 3 cap {settings.risk_kelly_phase3_cap} exceeds Quarter-Kelly bound "
        f"per S35 pre-commit #2"
    )


def test_kelly_phase4_cap_not_exceeds_0_25():
    settings = Settings(**_BASE)
    assert settings.risk_kelly_phase4_cap <= Decimal("0.25"), (
        f"Phase 4 cap {settings.risk_kelly_phase4_cap} exceeds bound "
        f"per S35 pre-commit #2 (defensive — Half-Kelly capped к Quarter)"
    )
