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

--- Wiki arithmetic note ---
wiki header says "6+7+8+7=28" but exits section lists 8 codes (not 7)
and halts section lists 7 codes (not 6). True count: 6+8+8+7=29.
Follow-up: ADR amendment to fix wiki header arithmetic.
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

    # Scale / exits (8)
    SCALE_OUT_PARTIAL = "SCALE_OUT_PARTIAL"
    EXIT_SL_HIT = "EXIT_SL_HIT"
    EXIT_TP_HIT = "EXIT_TP_HIT"
    EXIT_TRAILING_STOP = "EXIT_TRAILING_STOP"
    EXIT_SIGNAL_FLIP = "EXIT_SIGNAL_FLIP"
    EXIT_TIME_STOP = "EXIT_TIME_STOP"
    EXIT_MANUAL_OVERRIDE = "EXIT_MANUAL_OVERRIDE"
    EXIT_CIRCUIT_BREAKER = "EXIT_CIRCUIT_BREAKER"
    EXIT_OCO_PARTIAL_TIMEOUT = "EXIT_OCO_PARTIAL_TIMEOUT"

    # Rejects (8)
    REJECT_RISK_EXCEEDED = "REJECT_RISK_EXCEEDED"
    REJECT_INSUFFICIENT_BALANCE = "REJECT_INSUFFICIENT_BALANCE"
    REJECT_STALE_DATA = "REJECT_STALE_DATA"
    REJECT_RATE_LIMITED = "REJECT_RATE_LIMITED"
    REJECT_CLOCK_DRIFT = "REJECT_CLOCK_DRIFT"
    REJECT_MIN_NOTIONAL = "REJECT_MIN_NOTIONAL"
    REJECT_FILTER_PRICE = "REJECT_FILTER_PRICE"
    REJECT_DUPLICATE_SIGNAL = "REJECT_DUPLICATE_SIGNAL"

    # Halts (7)
    HALT_DRAWDOWN_L1 = "HALT_DRAWDOWN_L1"
    HALT_DRAWDOWN_L2 = "HALT_DRAWDOWN_L2"
    HALT_DRAWDOWN_L3 = "HALT_DRAWDOWN_L3"
    HALT_FLASH_CRASH = "HALT_FLASH_CRASH"
    HALT_DATA_QUALITY = "HALT_DATA_QUALITY"
    HALT_EXCHANGE_OUTAGE = "HALT_EXCHANGE_OUTAGE"
    HALT_KILL_SWITCH = "HALT_KILL_SWITCH"
    HALT_RECONCILE_DIVERGENCE = "HALT_RECONCILE_DIVERGENCE"
