"""Runtime Settings per ADR 0016 (Bybit Spot testnet MVP).

Security:
    Bybit API credentials are REQUIRED env vars (no defaults committed to git
    per ADR 0018 sub-decision 9 — Sprint 4 security audit C1, CWE-798).
    Override-store HMAC key (risk_override_hmac_key) is REQUIRED, separate
    from the API secret, so that secret rotation does not invalidate active
    overrides (ADR 0018 sub-decision 9, audit H2/CWE-345).
"""

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Allowlist for config_hash() — only the risk thresholds operators reason
# about when issuing a manual circuit-breaker override. Excludes secrets
# (CWE-532), paths, observability flags, and strategy params that do not
# bear on a halt-bypass decision. Source: ADR 0018 sub-decision 9 (audit H1).
_HASH_ALLOWLIST: frozenset[str] = frozenset(
    {
        "risk_max_position_pct_cap",
        "risk_sl_atr_multiplier",
        "risk_tp_atr_multiplier",
        "risk_cb_l1_dd",
        "risk_cb_l2_dd",
        "risk_cb_l3_dd",
        "risk_cb_flash_abs",
        "risk_cb_flash_atr_mult",
        "risk_kelly_phase1_cap",
        "risk_kelly_phase2_cap",
        "risk_kelly_phase3_cap",
        "risk_kelly_phase4_cap",
    }
)


class Settings(BaseSettings):
    """Loaded from env / .env. Bybit creds + HMAC key REQUIRED — no defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Bybit credentials (REQUIRED — no defaults; CWE-798)
    bybit_api_key: str = Field(..., min_length=8)
    bybit_api_secret: str = Field(..., min_length=8)
    testnet: bool = True

    # Runtime flags
    trading_enabled: bool = False
    live_trading: bool = False

    # Strategy parameters (v0.1 defaults — см. trading/strategies/ema-crossover-adx-rsi.md)
    strategy_ema_fast: int = 12
    strategy_ema_slow: int = 26
    strategy_adx_period: int = 14
    strategy_adx_threshold: Decimal = Decimal("25")
    strategy_rsi_period: int = 14
    strategy_rsi_oversold: Decimal = Decimal("30")
    strategy_rsi_overbought: Decimal = Decimal("70")
    strategy_atr_period: int = 14

    # Paths (required)
    data_dir: Path
    log_dir: Path
    db_path: Path
    parquet_dir: Path

    # Observability
    sentry_dsn: str | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Risk-module parameters (Sprint 4 Task 2 — locked design)
    risk_max_position_pct_cap: Decimal = Decimal("0.05")
    risk_sl_atr_multiplier: Decimal = Decimal("1.5")
    risk_tp_atr_multiplier: Decimal = Decimal("3.0")
    risk_cb_l1_dd: Decimal = Decimal("0.15")
    risk_cb_l2_dd: Decimal = Decimal("0.22")
    risk_cb_l3_dd: Decimal = Decimal("0.30")
    risk_cb_flash_abs: Decimal = Decimal("0.08")
    risk_cb_flash_atr_mult: Decimal = Decimal("3.0")
    risk_kelly_phase1_cap: Decimal = Decimal("0.01")
    risk_kelly_phase2_cap: Decimal = Decimal("0.02")
    risk_kelly_phase3_cap: Decimal = Decimal("0.03")
    risk_kelly_phase4_cap: Decimal = Decimal("0.05")
    # Sprint 6 — Spot OCO emulation (ADR 0020 sub-decisions 11/12)
    oco_arming_ttl_seconds: int = 60
    oco_dust_threshold_btc: Decimal = Decimal("0.00001")

    # Sprint 7 — Resilience (ADR 0021 sub-decisions 4 + 8)
    heal_max_age_seconds: int = Field(
        default=3600,
        description="Max age (seconds) of execution_state row for HEAL-narrow on bootstrap. "
        "Beyond this → HALT_BOOTSTRAP_AMBIGUOUS with sub_reason=stale_age. "
        "Default = 1 bar period of v0.1 strategy (1H).",
    )
    require_mainnet_gate_passed: bool = Field(
        default=True,
        description="If True, mainnet config change is blocked until Phase G testnet probes pass. ADR 0021 sub-decision 8.",
    )

    risk_override_path: Path = Path("./state/cb_override.json")
    # HMAC-SHA256 key for override file integrity (REQUIRED, separate from
    # API secret so credential rotation does not invalidate operator
    # overrides — ADR 0018 sub-decision 9, audit H2/CWE-345).
    risk_override_hmac_key: str = Field(..., min_length=32)

    @model_validator(mode="after")
    def _live_trading_guards(self) -> "Settings":
        if self.live_trading and not self.trading_enabled:
            raise ValueError("live_trading requires trading_enabled=True")
        if self.live_trading and self.testnet:
            raise ValueError("live_trading requires testnet=False (mainnet-only)")
        return self

    def config_hash(self) -> str:
        """SHA-256 over the risk-threshold allowlist only.

        Excludes secrets (CWE-532), paths, observability flags, strategy
        params, and the HMAC key — only fields an operator weighs when
        approving a manual halt-override are covered. ADR 0018 sub-dec 9.
        """
        import hashlib
        import json

        data = self.model_dump(mode="json")
        risk_only = {k: data[k] for k in sorted(_HASH_ALLOWLIST) if k in data}
        canonical = json.dumps(
            risk_only, sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
