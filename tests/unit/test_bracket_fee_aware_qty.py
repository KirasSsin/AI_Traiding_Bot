# tests/unit/test_bracket_fee_aware_qty.py
"""ADR 0020 sub-decision 5 (G5): TP/SL qty must subtract base-coin fees from cumExecQty.
On Spot Buy, fees are charged in BTC (base_coin=feeCurrency). Skipping this leaves dust
that the OCO legs can't cancel — bracket gets stuck with residual."""
from decimal import Decimal
import pytest
from src.execution.bracket import compute_oco_qty


def test_qty_subtracts_fee_when_fee_currency_matches_base():
    qty = compute_oco_qty(
        cum_exec_qty=Decimal("0.001"),
        cum_exec_fee=Decimal("0.000001"),
        fee_currency="BTC",
        base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    assert qty == Decimal("0.000999")


def test_qty_unchanged_when_fee_currency_differs():
    qty = compute_oco_qty(
        cum_exec_qty=Decimal("0.001"),
        cum_exec_fee=Decimal("70.00"),
        fee_currency="USDT",
        base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    assert qty == Decimal("0.001")


def test_qty_floored_to_step_after_fee_subtract():
    qty = compute_oco_qty(
        cum_exec_qty=Decimal("0.001"),
        cum_exec_fee=Decimal("0.0000007"),
        fee_currency="BTC",
        base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    assert qty == Decimal("0.000999")


def test_qty_zero_when_fee_exceeds_qty():
    qty = compute_oco_qty(
        cum_exec_qty=Decimal("0.000001"),
        cum_exec_fee=Decimal("0.000002"),
        fee_currency="BTC",
        base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    assert qty == Decimal("0")
