"""Canonical reason codes for audit-log and risk events.

Source: wiki/trading/concepts/reason-codes.md
ADR: wiki/project/decisions/ (see reason-codes-schema, domain-events).

IMMUTABLE: codes are never renamed. New codes require ADR amendment first.

--- Mapping notes (non-canonical prompt names → canonical codes) ---
Prompt-spec names NOT in wiki and their resolutions:
  APPROVED              → not a reason code; use RiskAssessment.approved=True +
                          one of ENTRY_* or SCALE_* codes
  RISK_REJECT_HALT_L1   → HALT_DRAWDOWN_L1
  RISK_REJECT_HALT_L2   → HALT_DRAWDOWN_L2
  RISK_REJECT_HALT_L3   → HALT_DRAWDOWN_L3
  RISK_REJECT_HALT_FLASH→ HALT_FLASH_CRASH
  RISK_REJECT_INVALID_SIGNAL → REJECT_DUPLICATE_SIGNAL (closest; see Follow-up)
  RISK_REJECT_ZERO_QTY  → REJECT_RISK_EXCEEDED (closest; see Follow-up)

Follow-up: ADR amendment needed for RISK_REJECT_INVALID_SIGNAL and
RISK_REJECT_ZERO_QTY if those become distinct audit categories.

--- Wiki arithmetic note (post-ADR 0020) ---
Pre-S5 wiki header said "6+7+8+7=28"; S5 added EXIT_OCO_PARTIAL_TIMEOUT +
HALT_RECONCILE_DIVERGENCE → 31. ADR 0020 (Sprint 6) adds 8 more → 39.
ADR 0021 (Sprint 7) adds 3 more → True count:
6 entry + 11 scale/exits + 9 rejects + 16 halts = 42.
ADR 0022 (Sprint 8a) adds 3 more → True count:
6 entry + 11 scale/exits + 9 rejects + 19 halts = 45.
"""

from enum import StrEnum


class ReasonCode(StrEnum):
    # Entry (6)
    ENTRY_LONG_TREND_FOLLOWING = "ENTRY_LONG_TREND_FOLLOWING"
    ENTRY_SHORT_TREND_FOLLOWING = "ENTRY_SHORT_TREND_FOLLOWING"
    ENTRY_LONG_PULLBACK = "ENTRY_LONG_PULLBACK"
    ENTRY_SHORT_PULLBACK = "ENTRY_SHORT_PULLBACK"
    SCALE_IN_LONG = "SCALE_IN_LONG"
    SCALE_IN_SHORT = "SCALE_IN_SHORT"

    # Scale / exits (11 — including EXIT_RECONCILE_DETECTED defined below in ADR 0021 block for ADR traceability)
    SCALE_OUT_PARTIAL = "SCALE_OUT_PARTIAL"
    EXIT_SL_HIT = "EXIT_SL_HIT"
    EXIT_TP_HIT = "EXIT_TP_HIT"
    EXIT_TRAILING_STOP = "EXIT_TRAILING_STOP"
    EXIT_SIGNAL_FLIP = "EXIT_SIGNAL_FLIP"
    EXIT_TIME_STOP = "EXIT_TIME_STOP"
    EXIT_MANUAL_OVERRIDE = "EXIT_MANUAL_OVERRIDE"
    EXIT_CIRCUIT_BREAKER = "EXIT_CIRCUIT_BREAKER"
    EXIT_OCO_PARTIAL_TIMEOUT = "EXIT_OCO_PARTIAL_TIMEOUT"
    EXIT_STOP_RESIDUAL_FLATTEN = "EXIT_STOP_RESIDUAL_FLATTEN"

    # Rejects (9)
    REJECT_RISK_EXCEEDED = "REJECT_RISK_EXCEEDED"
    REJECT_INSUFFICIENT_BALANCE = "REJECT_INSUFFICIENT_BALANCE"
    REJECT_STALE_DATA = "REJECT_STALE_DATA"
    REJECT_RATE_LIMITED = "REJECT_RATE_LIMITED"
    REJECT_CLOCK_DRIFT = "REJECT_CLOCK_DRIFT"
    REJECT_MIN_NOTIONAL = "REJECT_MIN_NOTIONAL"
    REJECT_FILTER_PRICE = "REJECT_FILTER_PRICE"
    REJECT_DUPLICATE_SIGNAL = "REJECT_DUPLICATE_SIGNAL"
    REJECT_ORDER_ALREADY_TERMINAL = "REJECT_ORDER_ALREADY_TERMINAL"

    # Halts (19)
    HALT_DRAWDOWN_L1 = "HALT_DRAWDOWN_L1"
    HALT_DRAWDOWN_L2 = "HALT_DRAWDOWN_L2"
    HALT_DRAWDOWN_L3 = "HALT_DRAWDOWN_L3"
    HALT_FLASH_CRASH = "HALT_FLASH_CRASH"
    HALT_DATA_QUALITY = "HALT_DATA_QUALITY"
    HALT_EXCHANGE_OUTAGE = "HALT_EXCHANGE_OUTAGE"
    HALT_KILL_SWITCH = "HALT_KILL_SWITCH"
    HALT_RECONCILE_DIVERGENCE = "HALT_RECONCILE_DIVERGENCE"

    # --- ADR 0020 sub-decision 7 — Sprint 6 Spot OCO emulation ---
    HALT_BRACKET_INCOMPLETE = "HALT_BRACKET_INCOMPLETE"
    HALT_OCO_ARM_TIMEOUT = "HALT_OCO_ARM_TIMEOUT"
    HALT_OCO_SIBLING_STUCK = "HALT_OCO_SIBLING_STUCK"
    HALT_PARTIAL_FILL_BELOW_MIN = "HALT_PARTIAL_FILL_BELOW_MIN"
    HALT_FLATTEN_FAILED = "HALT_FLATTEN_FAILED"
    HALT_PHANTOM_SL = "HALT_PHANTOM_SL"

    # --- ADR 0021 — Sprint 7 Resilience (bootstrap + reconcile) ---
    HALT_BOOTSTRAP_AMBIGUOUS = "HALT_BOOTSTRAP_AMBIGUOUS"
    HALT_EXIT_RECONCILE_DIVERGENCE = "HALT_EXIT_RECONCILE_DIVERGENCE"
    # NOTE: EXIT_RECONCILE_DETECTED is an exit-class code (counted under
    # "Scale / exits" total = 11 in wiki/architecture/reason-codes-schema.md);
    # placed here for ADR-0021 grouping/traceability, not categorization.
    EXIT_RECONCILE_DETECTED = "EXIT_RECONCILE_DETECTED"

    # --- ADR 0022 — Sprint 8a Live runtime ---
    HALT_RUNTIME_CRASH = "HALT_RUNTIME_CRASH"  # 43: unhandled exception in RuntimeManager.run()
    HALT_BAR_POLL_STALL = (
        "HALT_BAR_POLL_STALL"  # 44: N consecutive REST kline failures (default N=24)
    )
    KILL_SWITCH_REQUESTED = (
        "KILL_SWITCH_REQUESTED"  # 45: sentinel-file `.kill_switch` detected (operator-initiated)
    )

    # --- ADR 0055 — Sprint 36 δ TESTNET HaltGate triggers (SD-4) ---
    HALT_S36_DD_INTRADAY = "HALT_S36_DD_INTRADAY"  # 46: intraday DD trigger
    HALT_S36_DD_MULTIDAY = "HALT_S36_DD_MULTIDAY"  # 47: multi-day DD trigger
    HALT_S36_CONSECUTIVE_LOSSES = "HALT_S36_CONSECUTIVE_LOSSES"  # 48: loss streak trigger
    HALT_S36_NO_TRADE_TIMEOUT = "HALT_S36_NO_TRADE_TIMEOUT"  # 49: signal-frequency starvation
