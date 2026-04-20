from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.signalgen.models import Signal, SignalSide


def test_signal_valid():
    sig = Signal(
        signal_id=uuid4(),
        symbol="BTCUSDT",
        side=SignalSide.LONG,
        bar_close_time=datetime(2026, 4, 20, 1, 0, tzinfo=timezone.utc),
        generated_at=datetime(2026, 4, 20, 1, 0, 1, tzinfo=timezone.utc),
        ema_fast=Decimal("60100"),
        ema_slow=Decimal("60050"),
        adx_14=Decimal("28"),
        plus_di_14=Decimal("25"),
        minus_di_14=Decimal("15"),
        rsi_14=Decimal("55"),
        atr_14=Decimal("250"),
        reason="EMA_CROSS_UP_WITH_ADX_CONFIRM",
    )
    assert sig.side == SignalSide.LONG


def test_signal_generated_after_bar_close():
    with pytest.raises(ValidationError, match="generated_at"):
        Signal(
            signal_id=uuid4(),
            symbol="BTCUSDT",
            side=SignalSide.LONG,
            bar_close_time=datetime(2026, 4, 20, 1, 0, tzinfo=timezone.utc),
            generated_at=datetime(2026, 4, 20, 0, 59, tzinfo=timezone.utc),
            ema_fast=Decimal("60100"),
            ema_slow=Decimal("60050"),
            adx_14=Decimal("28"),
            plus_di_14=Decimal("25"),
            minus_di_14=Decimal("15"),
            rsi_14=Decimal("55"),
            atr_14=Decimal("250"),
            reason="X",
        )


def test_signal_flat_side_allowed():
    sig = Signal(
        signal_id=uuid4(),
        symbol="BTCUSDT",
        side=SignalSide.FLAT,
        bar_close_time=datetime(2026, 4, 20, 1, 0, tzinfo=timezone.utc),
        generated_at=datetime(2026, 4, 20, 1, 0, 1, tzinfo=timezone.utc),
        ema_fast=Decimal("60100"),
        ema_slow=Decimal("60050"),
        adx_14=Decimal("18"),
        plus_di_14=Decimal("20"),
        minus_di_14=Decimal("19"),
        rsi_14=Decimal("50"),
        atr_14=Decimal("250"),
        reason="NO_SIGNAL",
    )
    assert sig.side == SignalSide.FLAT
