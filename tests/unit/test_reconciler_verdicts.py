"""Reconciler 4-valued verdict tests (ADR 0021 sub-decision 3)."""
from decimal import Decimal

import pytest

from src.execution.reconciler import ReconcileResult


def test_reconcile_result_verdict_is_4_valued():
    """Verdict must be one of AGREE / DIVERGENCE / HEAL_ENTRY_FILLED / EXITED."""
    r = ReconcileResult(
        verdict="AGREE",
        exch_qty=Decimal("0"),
        entry_price=None,
        halt_reason=None,
        heal_context=None,
    )
    assert r.verdict == "AGREE"


def test_reconcile_result_heal_context_field_exists():
    r = ReconcileResult(
        verdict="HEAL_ENTRY_FILLED",
        exch_qty=Decimal("0.001"),
        entry_price=Decimal("62000"),
        halt_reason=None,
        heal_context={"avgPrice": "62000", "cumExecFee": "0.05"},
    )
    assert r.heal_context["avgPrice"] == "62000"


def test_reconcile_result_rejects_unknown_verdict():
    with pytest.raises((ValueError, TypeError)):
        ReconcileResult(
            verdict="WHATEVER",
            exch_qty=Decimal("0"),
            entry_price=None,
            halt_reason=None,
            heal_context=None,
        )
