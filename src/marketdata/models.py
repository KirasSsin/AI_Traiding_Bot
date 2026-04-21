"""Market-data domain models (pydantic v2)."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DataQuality(StrEnum):
    OK = "OK"
    GAP = "GAP"
    STALE = "STALE"
    SUSPECT = "SUSPECT"


class Bar(BaseModel):
    """OHLCV bar with strict validation — immutable по convention."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(..., pattern=r"^[A-Z]+USDT$")
    interval: Literal["1m", "5m", "15m", "1h", "4h", "1d"]
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Field(..., ge=0)
    trade_count: int = Field(..., ge=0)
    is_closed: bool
    data_quality: DataQuality = DataQuality.OK

    @model_validator(mode="after")
    def _ohlc_invariants(self) -> "Bar":
        if self.high < max(self.open, self.close):
            raise ValueError("high must be >= max(open, close)")
        if self.low > min(self.open, self.close):
            raise ValueError("low must be <= min(open, close)")
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be > open_time")
        return self
