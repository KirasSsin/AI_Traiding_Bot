"""Tests for WFA acceptance gate (per ADR 0014 + 0015 AND-combined).

Sprint 10 Q2 (per pre-s10-backlog.md verdict — DSR informational, NOT gate).
"""
from __future__ import annotations

from src.backtest.walk_forward import evaluate_acceptance_gate


def test_passes_when_all_folds_meet_sharpe_and_p_value() -> None:
    """All 5 folds OOS/IS Sharpe >= 0.7 + MC p <= 0.05 → PASS."""
    fold_sharpes = [0.8, 0.75, 0.85, 0.72, 0.9]
    mc_p_value = 0.02
    result = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes,
        mc_p_value=mc_p_value,
        sharpe_threshold=0.7,
        p_threshold=0.05,
    )
    assert result["passed"] is True
    assert result["sharpe_gate_passed"] is True
    assert result["mc_gate_passed"] is True


def test_fails_when_any_fold_below_sharpe_threshold() -> None:
    """One fold OOS/IS < 0.7 → FAIL (per-fold AND)."""
    fold_sharpes = [0.8, 0.5, 0.85, 0.72, 0.9]
    result = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes,
        mc_p_value=0.02,
        sharpe_threshold=0.7,
        p_threshold=0.05,
    )
    assert result["passed"] is False
    assert result["sharpe_gate_passed"] is False
    assert result["mc_gate_passed"] is True
    assert result["failed_folds"] == [1]


def test_fails_when_p_value_above_threshold() -> None:
    """Sharpe OK but p > 0.05 → FAIL."""
    fold_sharpes = [0.8, 0.75, 0.85, 0.72, 0.9]
    result = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes,
        mc_p_value=0.10,
        sharpe_threshold=0.7,
        p_threshold=0.05,
    )
    assert result["passed"] is False
    assert result["sharpe_gate_passed"] is True
    assert result["mc_gate_passed"] is False


def test_dsr_not_in_gate_decision() -> None:
    """DSR computed but NOT in pass/fail decision (Q2 trader REVISE)."""
    fold_sharpes = [0.8, 0.75, 0.85, 0.72, 0.9]
    result = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes,
        mc_p_value=0.02,
        sharpe_threshold=0.7,
        p_threshold=0.05,
    )
    assert "dsr_gate_passed" not in result
    assert result["passed"] is True
