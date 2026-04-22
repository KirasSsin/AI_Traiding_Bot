"""Risk domain models: HaltState and RiskAssessment.

Output of RiskManager.assess(signal). All models are immutable.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from src.risk.reason_codes import ReasonCode


class HaltState(StrEnum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    FLASH = "FLASH"


class RiskAssessment(BaseModel):
    """Output of RiskManager.assess(signal). Immutable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_id: UUID
    approved: bool
    qty: Decimal | None = Field(default=None, ge=0)
    sl_price: Decimal | None = Field(default=None, gt=0)
    tp_price: Decimal | None = Field(default=None, gt=0)
    kelly_phase: Literal[1, 2, 3, 4]
    kelly_fraction: Decimal = Field(..., ge=0)
    halt_state: HaltState
    reason_code: ReasonCode
    assessed_at: datetime

    @field_serializer("qty", "sl_price", "tp_price", "kelly_fraction")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return str(value)

    @model_validator(mode="after")
    def _consistency(self) -> "RiskAssessment":
        if self.approved:
            if self.qty is None or self.qty == Decimal(0):
                raise ValueError("approved=True requires qty > 0")
            if self.sl_price is None:
                raise ValueError("approved=True requires sl_price and tp_price")
            if self.tp_price is None:
                raise ValueError("approved=True requires sl_price and tp_price")
            if self.tp_price <= self.sl_price:
                raise ValueError("tp_price must be > sl_price")
        if not self.approved and self.qty not in (None, Decimal(0)):
            raise ValueError("approved=False requires qty=None or 0")
        return self
