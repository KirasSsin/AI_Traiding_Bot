"""Bybit V5 instruments-info → filter model + round/validate helpers."""

from decimal import ROUND_DOWN, Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class FilterViolation(ValueError):
    """Order params violate Bybit filters (LOT_SIZE / PRICE_FILTER / NOTIONAL)."""


class BybitFilters(BaseModel):
    """Single-class wrapper over V5 instruments-info filter shape."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    step_size: Decimal  # basePrecision
    tick_size: Decimal
    min_order_qty: Decimal
    max_order_qty: Decimal
    min_order_amt: Decimal  # minimum quote notional

    @classmethod
    def from_instruments_info(cls, response: dict[str, Any]) -> "BybitFilters":
        if response["retCode"] != 0:
            raise RuntimeError(f"instruments-info retCode={response['retCode']}")
        item = response["result"]["list"][0]
        lot = item["lotSizeFilter"]
        price = item["priceFilter"]
        return cls(
            symbol=item["symbol"],
            step_size=Decimal(lot["basePrecision"]),
            tick_size=Decimal(price["tickSize"]),
            min_order_qty=Decimal(lot["minOrderQty"]),
            max_order_qty=Decimal(lot["maxOrderQty"]),
            min_order_amt=Decimal(lot["minOrderAmt"]),
        )

    def round_qty(self, qty: Decimal) -> Decimal:
        """Round down to step_size (never exceed user-intended qty)."""
        return (qty / self.step_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * self.step_size

    def round_price(self, price: Decimal) -> Decimal:
        """Round to tick_size (DOWN keeps us on the safe side for BUY limits)."""
        return (price / self.tick_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * self.tick_size

    def validate_order(self, qty: Decimal, price: Decimal | None = None) -> None:
        """Raise FilterViolation if order would be rejected by exchange.

        price is optional: when None (e.g. MARKET orders), the min-notional check is
        skipped because there is no reference price available at order-build time.
        """
        if qty < self.min_order_qty:
            raise FilterViolation(f"qty {qty} < min_order_qty {self.min_order_qty}")
        if qty > self.max_order_qty:
            raise FilterViolation(f"qty {qty} > max_order_qty {self.max_order_qty}")
        if price is not None:
            notional = qty * price
            if notional < self.min_order_amt:
                raise FilterViolation(f"qty*price={notional} < min_order_amt {self.min_order_amt}")
