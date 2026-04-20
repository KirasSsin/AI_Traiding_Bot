"""Signal-generation domain models."""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SignalSide(StrEnum):
    LONG = "LONG"
    FLAT = "FLAT"
    # SHORT не используется в v0.1 (spot only)


class Signal(BaseModel):
    """Trading signal emitted on bar close. Immutable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_id: UUID
    symbol: str = Field(..., pattern=r"^[A-Z]+USDT$")
    side: SignalSide
    bar_close_time: datetime
    generated_at: datetime

    # Indicator snapshot
    ema_fast: Decimal
    ema_slow: Decimal
    adx_14: Decimal = Field(..., ge=0, le=100)
    plus_di_14: Decimal = Field(..., ge=0, le=100)
    minus_di_14: Decimal = Field(..., ge=0, le=100)
    rsi_14: Decimal = Field(..., ge=0, le=100)
    atr_14: Decimal = Field(..., ge=0)

    reason: str = Field(..., max_length=128)

    @model_validator(mode="after")
    def _generated_after_close(self) -> "Signal":
        if self.generated_at < self.bar_close_time:
            raise ValueError(
                "generated_at must be >= bar_close_time (look-ahead invariant)"
            )
        return self
