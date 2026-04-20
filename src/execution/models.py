"""Order-execution domain models."""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(StrEnum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_order_id: str = Field(..., min_length=1, max_length=64)
    exch_order_id: str | None
    symbol: str = Field(..., pattern=r"^[A-Z]+USDT$")
    side: OrderSide
    type: OrderType
    status: OrderStatus
    orig_qty: Decimal = Field(..., gt=0)
    executed_qty: Decimal = Field(..., ge=0)
    price: Decimal | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _exec_not_exceeds_orig(self) -> "Order":
        if self.executed_qty > self.orig_qty:
            raise ValueError("executed_qty must be <= orig_qty")
        return self


class Fill(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    client_order_id: str = Field(..., min_length=1)
    trade_id: int = Field(..., gt=0)
    qty: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fee: Decimal = Field(..., ge=0)
    fee_asset: str = Field(..., min_length=1)
    is_maker: bool
    filled_at: datetime
