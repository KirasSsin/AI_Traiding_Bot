"""HaltGate — S35 δ TESTNET pre-committed halt criteria evaluation.

Per pre-s35-backlog.md ROUND 3 binding (8 pre-commitments + HALT criteria):
  - DD >= -20% intraday → halt + S36 honest close
  - DD >= -15% multi-day → halt + S36 honest close
  - >=5 consecutive losing trades → operator review
  - >=6 months without n>=30 closed trades → halt + S36 honest close

Priority ordering (first trigger wins, evaluated top-к-bottom):
  1. DD_INTRADAY (most urgent — flash drawdown)
  2. DD_MULTIDAY (cumulative loss)
  3. CONSECUTIVE_LOSSES (degenerate-edge signal)
  4. NO_TRADE_TIMEOUT (signal-frequency starvation)

Returns first matching HaltTrigger or None если все checks pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class HaltTrigger(StrEnum):
    """S35 δ halt trigger categories — written к halt_log.context_json."""

    DD_INTRADAY = "S35_DD_INTRADAY"
    DD_MULTIDAY = "S35_DD_MULTIDAY"
    CONSECUTIVE_LOSSES = "S35_CONSECUTIVE_LOSSES"
    NO_TRADE_TIMEOUT = "S35_NO_TRADE_TIMEOUT"


@dataclass(frozen=True)
class HaltGate:
    """Pre-committed halt criteria evaluator. All thresholds Decimal/int."""

    dd_intraday_threshold: Decimal
    dd_multiday_threshold: Decimal
    consecutive_losses_threshold: int
    no_trade_months_threshold: int

    def __post_init__(self) -> None:
        if self.dd_intraday_threshold <= Decimal("0"):
            raise ValueError("dd_intraday_threshold must be positive")
        if self.dd_multiday_threshold <= Decimal("0"):
            raise ValueError("dd_multiday_threshold must be positive")
        if self.consecutive_losses_threshold < 1:
            raise ValueError("consecutive_losses_threshold must be >= 1")
        if self.no_trade_months_threshold < 1:
            raise ValueError("no_trade_months_threshold must be >= 1")

    def evaluate(
        self,
        *,
        intraday_dd: Decimal,
        multiday_dd: Decimal,
        consecutive_losses: int,
        months_since_last_trade: int,
    ) -> HaltTrigger | None:
        """Return first triggered halt category или None если все pass.

        Priority order: intraday DD > multi-day DD > consecutive losses > no-trade timeout.
        """
        if intraday_dd >= self.dd_intraday_threshold:
            return HaltTrigger.DD_INTRADAY
        if multiday_dd >= self.dd_multiday_threshold:
            return HaltTrigger.DD_MULTIDAY
        if consecutive_losses >= self.consecutive_losses_threshold:
            return HaltTrigger.CONSECUTIVE_LOSSES
        if months_since_last_trade >= self.no_trade_months_threshold:
            return HaltTrigger.NO_TRADE_TIMEOUT
        return None
