"""Tests for compute_qty pure function — Sprint 4, Task 5."""

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from src.risk.sizing import compute_qty

# ---------------------------------------------------------------------------
# Basic correctness
# ---------------------------------------------------------------------------


def test_basic_value():
    """qty = (fraction * equity) / (k * atr) = (0.02 * 10000) / (1.5 * 500) = 200 / 750."""
    result = compute_qty(
        equity=Decimal("10000"),
        fraction=Decimal("0.02"),
        atr=Decimal("500"),
        price=Decimal("40000"),
        k=Decimal("1.5"),
    )
    expected = Decimal("200") / Decimal("750")
    assert abs(result - expected) < Decimal("0.0001")


def test_returns_decimal():
    result = compute_qty(
        equity=Decimal("10000"),
        fraction=Decimal("0.02"),
        atr=Decimal("500"),
        price=Decimal("40000"),
        k=Decimal("1.5"),
    )
    assert isinstance(result, Decimal)


def test_result_non_negative():
    result = compute_qty(
        equity=Decimal("5000"),
        fraction=Decimal("0.01"),
        atr=Decimal("100"),
        price=Decimal("1000"),
        k=Decimal("1.5"),
    )
    assert result >= Decimal("0")


# ---------------------------------------------------------------------------
# Defensive zero cases
# ---------------------------------------------------------------------------


def test_fraction_zero_returns_zero():
    result = compute_qty(
        equity=Decimal("10000"),
        fraction=Decimal("0"),
        atr=Decimal("500"),
        price=Decimal("40000"),
        k=Decimal("1.5"),
    )
    assert result == Decimal("0")


def test_atr_zero_returns_zero():
    result = compute_qty(
        equity=Decimal("10000"),
        fraction=Decimal("0.02"),
        atr=Decimal("0"),
        price=Decimal("40000"),
        k=Decimal("1.5"),
    )
    assert result == Decimal("0")


# ---------------------------------------------------------------------------
# ValueError on negative inputs
# ---------------------------------------------------------------------------


def test_negative_equity_raises():
    with pytest.raises(ValueError):
        compute_qty(
            equity=Decimal("-1"),
            fraction=Decimal("0.02"),
            atr=Decimal("500"),
            price=Decimal("40000"),
            k=Decimal("1.5"),
        )


def test_negative_fraction_raises():
    with pytest.raises(ValueError):
        compute_qty(
            equity=Decimal("10000"),
            fraction=Decimal("-0.01"),
            atr=Decimal("500"),
            price=Decimal("40000"),
            k=Decimal("1.5"),
        )


def test_negative_atr_raises():
    with pytest.raises(ValueError):
        compute_qty(
            equity=Decimal("10000"),
            fraction=Decimal("0.02"),
            atr=Decimal("-1"),
            price=Decimal("40000"),
            k=Decimal("1.5"),
        )


# ---------------------------------------------------------------------------
# Property test: cap invariant via hypothesis
# ---------------------------------------------------------------------------

_decimal_strategy = st.decimals(
    min_value="0",
    max_value="1000000",
    allow_nan=False,
    allow_infinity=False,
    places=8,
)

_fraction_strategy = st.decimals(
    min_value="0",
    max_value="0.05",
    allow_nan=False,
    allow_infinity=False,
    places=8,
)

_atr_strategy = st.decimals(
    min_value="0.00000001",
    max_value="100000",
    allow_nan=False,
    allow_infinity=False,
    places=8,
)

_price_strategy = st.decimals(
    min_value="0.00000001",
    max_value="1000000",
    allow_nan=False,
    allow_infinity=False,
    places=8,
)


@given(
    equity=_decimal_strategy,
    fraction=_fraction_strategy,
    atr=_atr_strategy,
    price=_price_strategy,
)
@settings(max_examples=200)
def test_cap_invariant(equity, fraction, atr, price):
    """result * k * atr <= fraction * equity  (with small rounding tolerance)."""
    k = Decimal("1.5")
    result = compute_qty(equity=equity, fraction=fraction, atr=atr, price=price, k=k)
    tolerance = fraction * equity * Decimal("1e-9") + Decimal("1e-18")
    assert result * k * atr <= fraction * equity + tolerance
    assert result >= Decimal("0")
