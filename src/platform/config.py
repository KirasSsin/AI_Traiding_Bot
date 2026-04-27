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
        # S35 T2 — δ TESTNET halt criteria (architecture-reviewer T2 carry: ADR 0018 H1)
        "s35_halt_dd_intraday",
        "s35_halt_dd_multiday",
        "s35_halt_consecutive_losses",
        "s35_halt_no_trade_months",
    }
)


class Settings(BaseSettings):
    """Loaded from env / .env. Bybit creds + HMAC key REQUIRED — no defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # S35 T2 security-auditor HIGH #1 — close runtime-mutation bypass of money-path
        # invariants (`_live_trading_guards`, `_validate_s35_demo_mainnet_exclusion`).
        # validate_assignment re-runs validators on every attribute set, preventing
        # post-construction `settings.live_trading = True` from skipping pre-commit #1.
        validate_assignment=True,
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
    risk_sl_atr_multiplier: Decimal = Field(
        default=Decimal("1.5"),
        gt=Decimal("0"),
        description=(
            "Stop-loss distance в ATR multiples (k в qty = (f * equity) / (k * atr)). "
            "S35 ζ refactor: explicit setting (no hard-coded sizing.compute_qty default). "
            "Calibration range 1.0-2.0 × ATR per ADR 0007. gt=0 prevents ZeroDivisionError "
            "downstream (per S35 T1 trading-logic-reviewer C1 hardening)."
        ),
    )
    # Sprint 35 — δ TESTNET live demo (ADR 0053 LOCKED, pre-s35-backlog ROUND 3 binding)
    s35_demo_active: bool = Field(
        default=False,
        description=(
            "S35 δ TESTNET live demo flag. When True, HaltGate activates "
            "S35-specific halt criteria (DD bounds, consecutive losses, no-trade timeout). "
            "MUST be False on MAINNET (live_trading=True invariant violated otherwise)."
        ),
    )
    s35_halt_dd_intraday: Decimal = Field(
        default=Decimal("0.20"),
        gt=Decimal("0"),
        le=Decimal("0.50"),
        description="S35 δ intraday DD halt threshold (-20% per pre-commit ROUND 3).",
    )
    s35_halt_dd_multiday: Decimal = Field(
        default=Decimal("0.15"),
        gt=Decimal("0"),
        le=Decimal("0.50"),
        description="S35 δ multi-day DD halt threshold (-15% per pre-commit ROUND 3).",
    )
    s35_halt_consecutive_losses: int = Field(
        default=5,
        ge=1,
        le=20,
        description="S35 δ consecutive losing trades trigger operator review.",
    )
    s35_halt_no_trade_months: int = Field(
        default=6,
        ge=1,
        le=24,
        description="S35 δ months без n>=30 closed trades → halt + S36 honest close.",
    )
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
        "Default = 1 bar period of 1H strategy. DEPRECATED at S19: prefer "
        "heal_max_bars (interval-agnostic). Legacy seconds value used iff "
        "heal_max_bars=None.",
    )
    heal_max_bars: int | None = Field(
        default=1,
        description="Max age (bars) of execution_state row for HEAL-narrow on bootstrap. "
        "S19 ADR 0034 Condition A2: interval-agnostic semantic refactor. "
        "Bootstrap (e.g. _cmd_run) derives heal_max_age_seconds = "
        "heal_max_bars * interval_seconds and passes derived value к Reconciler. "
        "If None, legacy heal_max_age_seconds field used directly (backward-compat). "
        "Default 1 bar matches pre-S19 1H semantic but applies к any interval.",
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

    # Sprint 8a — Live runtime (ADR 0022 sub-decisions 11 + 3)
    runtime_bar_poll_cadence_seconds: float = Field(
        default=5.0,
        description="REST kline poll cadence (main loop tick). ADR 0022 sub-decision 2.",
    )
    runtime_bar_poll_stall_threshold: int = Field(
        default=24,
        description=(
            "Consecutive REST poll failures before HALT_BAR_POLL_STALL. "
            "Default 24 × 5s = 120s. Validator: 6 ≤ N ≤ 720 "
            "(30s false-halt floor; 1 bar period ceiling). ADR 0022 sub-decision 3."
        ),
    )
    runtime_kill_switch_path: str = Field(
        default=".kill_switch",
        description="Sentinel-file path for KILL_SWITCH. ADR 0022 sub-decision 5.",
    )
    runtime_ws_check_alive_max_silence: float = Field(
        default=30.0,
        description="Max WS silence before triggering on_disconnect (inline check). ADR 0022 sub-decision 4.",
    )
    runtime_warmup_bars: int = Field(
        default=50,
        description="Catch-up bars fed to strategy.warmup() (no signal emit). ADR 0022 sub-decision 2.",
    )
    runtime_quality_threshold_pct: Decimal = Field(
        default=Decimal("0.005"),
        description=(
            "Bar price quality threshold (relative deviation, default 0.5%). "
            "S9 Q1 — REST-vs-REST consecutive bar quality detector. "
            "Triggers HALT_DATA_QUALITY via Coordinator.request_halt."
        ),
    )

    @model_validator(mode="after")
    def _runtime_validators(self) -> "Settings":
        if not (6 <= self.runtime_bar_poll_stall_threshold <= 720):
            raise ValueError(
                f"runtime_bar_poll_stall_threshold={self.runtime_bar_poll_stall_threshold} "
                f"out of range: 6 ≤ N ≤ 720 (ADR 0022 sub-decision 3)."
            )
        return self

    @model_validator(mode="after")
    def _live_trading_guards(self) -> "Settings":
        if self.live_trading and not self.trading_enabled:
            raise ValueError("live_trading requires trading_enabled=True")
        if self.live_trading and self.testnet:
            raise ValueError("live_trading requires testnet=False (mainnet-only)")
        return self

    @model_validator(mode="after")
    def _validate_s35_demo_mainnet_exclusion(self) -> "Settings":
        """S35 pre-commit #1: δ is TESTNET ONLY. Block any path к MAINNET.

        Per pre-s35-backlog.md ROUND 3 binding pre-commitment #1 LOCKED. Verbatim:
        "δ is TESTNET ONLY. No MAINNET until 12-month TESTNET evidence reviewed."

        Two checks per S35 T2 security-auditor HIGH #2:
          1. Block live_trading=True (mainnet routing flag)
          2. Block testnet=False (Bybit endpoint flag — adapter routes by `testnet`,
             not just live_trading; testnet=False alone routes к MAINNET endpoint
             with real-money creds even если live_trading=False)

        Mistake here = real MAINNET activation = capital loss risk.

        Implicit ordering note: depends on `_live_trading_guards` running first
        (per architecture-reviewer C4). Pydantic v2 `mode="after"` validators run
        в declaration order — DO NOT reorder без verifying invariant chain.
        """
        if self.s35_demo_active and self.live_trading:
            raise ValueError(
                "S35 δ TESTNET demo cannot run на MAINNET (live_trading=True). "
                "Set live_trading=False (testnet=True) OR disable s35_demo_active. "
                "Per pre-s35-backlog.md pre-commitment #1 LOCKED."
            )
        if self.s35_demo_active and not self.testnet:
            raise ValueError(
                "S35 δ TESTNET demo requires testnet=True (Bybit endpoint flag). "
                "testnet=False routes к MAINNET endpoint regardless of live_trading. "
                "Per pre-s35-backlog.md pre-commitment #1 LOCKED."
            )
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
        canonical = json.dumps(risk_only, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
