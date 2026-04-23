"""Tests for CircuitBreakerDetector — TDD RED phase."""

from decimal import Decimal

import pytest
from src.risk.circuit_breakers import CircuitBreakerConfig, CircuitBreakerDetector
from src.risk.models import HaltState


@pytest.fixture()
def cfg() -> CircuitBreakerConfig:
    return CircuitBreakerConfig(
        l1_dd=Decimal("0.15"),
        l2_dd=Decimal("0.22"),
        l3_dd=Decimal("0.30"),
        flash_abs=Decimal("0.08"),
        flash_atr_mult=Decimal("3.0"),
    )


@pytest.fixture()
def detector(cfg: CircuitBreakerConfig) -> CircuitBreakerDetector:
    return CircuitBreakerDetector(cfg)


# ---------------------------------------------------------------------------
# check_drawdown
# ---------------------------------------------------------------------------

class TestCheckDrawdown:
    def test_no_drawdown_same_price(self, detector: CircuitBreakerDetector) -> None:
        assert detector.check_drawdown(peak=Decimal("10000"), current=Decimal("10000")) == HaltState.L0

    def test_below_l1_threshold(self, detector: CircuitBreakerDetector) -> None:
        # DD = (10000 - 9001) / 10000 = 9.99% < 15%
        assert detector.check_drawdown(peak=Decimal("10000"), current=Decimal("9001")) == HaltState.L0

    def test_exactly_l1(self, detector: CircuitBreakerDetector) -> None:
        # DD = (10000 - 8500) / 10000 = 15.0% → L1
        assert detector.check_drawdown(peak=Decimal("10000"), current=Decimal("8500")) == HaltState.L1

    def test_between_l1_and_l2(self, detector: CircuitBreakerDetector) -> None:
        # DD = 20% → L1
        assert detector.check_drawdown(peak=Decimal("10000"), current=Decimal("8000")) == HaltState.L1

    def test_exactly_l2(self, detector: CircuitBreakerDetector) -> None:
        # DD = (10000 - 7800) / 10000 = 22.0% → L2
        assert detector.check_drawdown(peak=Decimal("10000"), current=Decimal("7800")) == HaltState.L2

    def test_between_l2_and_l3(self, detector: CircuitBreakerDetector) -> None:
        # DD = 25% → L2
        assert detector.check_drawdown(peak=Decimal("10000"), current=Decimal("7500")) == HaltState.L2

    def test_exactly_l3(self, detector: CircuitBreakerDetector) -> None:
        # DD = (10000 - 7000) / 10000 = 30.0% → L3
        assert detector.check_drawdown(peak=Decimal("10000"), current=Decimal("7000")) == HaltState.L3

    def test_above_l3(self, detector: CircuitBreakerDetector) -> None:
        # DD = 50% → L3
        assert detector.check_drawdown(peak=Decimal("10000"), current=Decimal("5000")) == HaltState.L3

    def test_above_peak(self, detector: CircuitBreakerDetector) -> None:
        # current > peak → L0
        assert detector.check_drawdown(peak=Decimal("10000"), current=Decimal("10500")) == HaltState.L0

    def test_peak_zero(self, detector: CircuitBreakerDetector) -> None:
        assert detector.check_drawdown(peak=Decimal("0"), current=Decimal("100")) == HaltState.L0

    def test_peak_negative(self, detector: CircuitBreakerDetector) -> None:
        assert detector.check_drawdown(peak=Decimal("-1"), current=Decimal("100")) == HaltState.L0

    def test_boundary_l1_exact_decimal(self, detector: CircuitBreakerDetector) -> None:
        # DD = exactly 0.15 → L1 (>= triggers)
        peak = Decimal("100")
        current = Decimal("85")  # DD = 15/100 = 0.15
        assert detector.check_drawdown(peak=peak, current=current) == HaltState.L1

    def test_boundary_l2_exact_decimal(self, detector: CircuitBreakerDetector) -> None:
        peak = Decimal("100")
        current = Decimal("78")  # DD = 22/100 = 0.22
        assert detector.check_drawdown(peak=peak, current=current) == HaltState.L2

    def test_boundary_l3_exact_decimal(self, detector: CircuitBreakerDetector) -> None:
        peak = Decimal("100")
        current = Decimal("70")  # DD = 30/100 = 0.30
        assert detector.check_drawdown(peak=peak, current=current) == HaltState.L3

    def test_highest_level_returned(self, detector: CircuitBreakerDetector) -> None:
        # Verify L3 is returned, not L1 or L2, at extreme DD
        result = detector.check_drawdown(peak=Decimal("10000"), current=Decimal("6000"))
        assert result == HaltState.L3

    def test_pure_no_state_mutation(self, detector: CircuitBreakerDetector) -> None:
        # Calling multiple times returns consistent results (no state)
        r1 = detector.check_drawdown(peak=Decimal("10000"), current=Decimal("7000"))
        r2 = detector.check_drawdown(peak=Decimal("10000"), current=Decimal("9500"))
        r3 = detector.check_drawdown(peak=Decimal("10000"), current=Decimal("7000"))
        assert r1 == HaltState.L3
        assert r2 == HaltState.L0
        assert r3 == HaltState.L3


# ---------------------------------------------------------------------------
# check_flash
# ---------------------------------------------------------------------------

class TestCheckFlash:
    def test_no_change(self, detector: CircuitBreakerDetector) -> None:
        # delta=0, threshold=max(0.08, 0.15)=0.15 → False
        assert detector.check_flash(
            bar_close=Decimal("100"), prev_close=Decimal("100"), atr=Decimal("5")
        ) is False

    def test_atr_driven_threshold_triggers(self, detector: CircuitBreakerDetector) -> None:
        # delta = |84 - 100| / 100 = 0.16
        # atr_pct = 3.0 * 5 / 100 = 0.15
        # threshold = max(0.08, 0.15) = 0.15
        # 0.16 > 0.15 → True
        assert detector.check_flash(
            bar_close=Decimal("84"), prev_close=Decimal("100"), atr=Decimal("5")
        ) is True

    def test_atr_driven_threshold_no_trigger(self, detector: CircuitBreakerDetector) -> None:
        # delta = |92.5 - 100| / 100 = 0.075
        # threshold = max(0.08, 0.15) = 0.15
        # 0.075 < 0.15 → False
        assert detector.check_flash(
            bar_close=Decimal("92.5"), prev_close=Decimal("100"), atr=Decimal("5")
        ) is False

    def test_absolute_floor_triggers(self, detector: CircuitBreakerDetector) -> None:
        # delta = |91 - 100| / 100 = 0.09
        # atr_pct = 3.0 * 1 / 100 = 0.03
        # threshold = max(0.08, 0.03) = 0.08
        # 0.09 > 0.08 → True
        assert detector.check_flash(
            bar_close=Decimal("91"), prev_close=Decimal("100"), atr=Decimal("1")
        ) is True

    def test_strict_gt_not_gte(self, detector: CircuitBreakerDetector) -> None:
        # delta = |92 - 100| / 100 = 0.08
        # threshold = max(0.08, 0.03) = 0.08
        # 0.08 NOT > 0.08 → False (strict >)
        assert detector.check_flash(
            bar_close=Decimal("92"), prev_close=Decimal("100"), atr=Decimal("1")
        ) is False

    def test_prev_close_zero(self, detector: CircuitBreakerDetector) -> None:
        assert detector.check_flash(
            bar_close=Decimal("100"), prev_close=Decimal("0"), atr=Decimal("5")
        ) is False

    def test_prev_close_negative(self, detector: CircuitBreakerDetector) -> None:
        assert detector.check_flash(
            bar_close=Decimal("100"), prev_close=Decimal("-1"), atr=Decimal("5")
        ) is False

    def test_positive_shock_triggers(self, detector: CircuitBreakerDetector) -> None:
        # bar > prev — upward shock — magnitude check
        # delta = |116 - 100| / 100 = 0.16 > 0.15 → True
        assert detector.check_flash(
            bar_close=Decimal("116"), prev_close=Decimal("100"), atr=Decimal("5")
        ) is True

    def test_positive_shock_no_trigger(self, detector: CircuitBreakerDetector) -> None:
        # delta = |110 - 100| / 100 = 0.10 < 0.15 → False
        assert detector.check_flash(
            bar_close=Decimal("110"), prev_close=Decimal("100"), atr=Decimal("5")
        ) is False

    def test_pure_no_state_mutation(self, detector: CircuitBreakerDetector) -> None:
        r1 = detector.check_flash(bar_close=Decimal("84"), prev_close=Decimal("100"), atr=Decimal("5"))
        r2 = detector.check_flash(bar_close=Decimal("100"), prev_close=Decimal("100"), atr=Decimal("5"))
        r3 = detector.check_flash(bar_close=Decimal("84"), prev_close=Decimal("100"), atr=Decimal("5"))
        assert r1 is True
        assert r2 is False
        assert r3 is True
