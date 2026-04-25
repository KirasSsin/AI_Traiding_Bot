"""Tests for BarPriceQualityDetector — REST-vs-REST consecutive bar deviation.

Sprint 9 Q1 (per pre-s9-backlog.md verdict — REVISE accepted).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from src.marketdata.quality import BarPriceQualityDetector


def test_first_poll_skips_no_prior_baseline() -> None:
    """First call has no baseline → cannot detect deviation → returns False."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    assert det.check(current_close=Decimal("100000")) is False


def test_within_threshold_no_halt() -> None:
    """0.4% deviation < 0.5% threshold → no halt."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("100000"))  # establish baseline
    assert det.check(current_close=Decimal("100400")) is False


def test_exceeds_threshold_halts() -> None:
    """0.6% deviation > 0.5% threshold → halt."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("100000"))
    assert det.check(current_close=Decimal("100600")) is True


def test_negative_deviation_uses_absolute_value() -> None:
    """Drop of 0.6% also triggers halt (symmetric)."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("100000"))
    assert det.check(current_close=Decimal("99400")) is True


def test_zero_prior_close_defensive() -> None:
    """Prior close ≤ 0 → False defensively (no division by zero)."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("0"))
    assert det.check(current_close=Decimal("100000")) is False


def test_negative_threshold_rejected() -> None:
    """Negative threshold raises ValueError at construction."""
    with pytest.raises(ValueError, match="threshold_pct must be > 0"):
        BarPriceQualityDetector(threshold_pct=Decimal("-0.005"))


def test_threshold_at_boundary() -> None:
    """Exact boundary value: deviation == threshold → False (strict >)."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("100000"))
    assert det.check(current_close=Decimal("100500")) is False


def test_baseline_advances_each_call() -> None:
    """After each check, baseline updates to current_close (rolling)."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("100000"))
    det.check(current_close=Decimal("100200"))  # 0.2%, no halt, baseline now 100200
    # 100200 → 100800 = ~0.6%, triggers halt
    assert det.check(current_close=Decimal("100800")) is True
