"""Acceptance gate amendment tests — S34 T4 (per ADR 0052 LOCKED).

Validates n_eff threshold enforcement + amended T5 floor + tightened MC threshold.
Per consilium 10-item pre-commit list:
- T5 floor 100 → 50
- n_eff threshold ≥ 50 (NEW, Kish 1965 mandatory)
- MC threshold ≤ 0.05 (tightened от 0.10)
- T6 + DSR + acceptance_gate UNCHANGED
"""

from __future__ import annotations

from src.backtest.walk_forward import evaluate_acceptance_gate


def test_amended_gates_n_eff_threshold_enforced():
    """n_eff < 50 → FAIL even если raw n ≥ 50 (Kish 1965 deflation per S33 lesson)."""
    # S33 actual data: raw=66 PASS, n_eff=26 FAIL
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=[0.8, 0.9, 1.0, 1.1, 1.2],  # all > sharpe_threshold
        mc_p_value=0.04,  # passes amended ≤ 0.05
        n_trades_raw=66,
        n_trades_n_eff=26,  # FAIL — below new threshold 50
        n_eff_threshold=50,
        t5_floor=50,
    )
    assert gate["passed"] is False
    assert "n_eff_threshold" in gate.get("failed_criteria", [])


def test_amended_gates_t5_floor_50():
    """T5 floor 50 — n_raw < 50 fails."""
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=[0.8, 0.9, 1.0, 1.1, 1.2],
        mc_p_value=0.04,
        n_trades_raw=45,  # FAIL — below new floor 50
        n_trades_n_eff=45,
        n_eff_threshold=50,
        t5_floor=50,
    )
    assert gate["passed"] is False
    assert "t5_floor" in gate.get("failed_criteria", [])


def test_amended_gates_mc_threshold_tightened():
    """MC threshold 0.05 — p > 0.05 fails (tightened от 0.10)."""
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=[0.8, 0.9, 1.0, 1.1, 1.2],
        mc_p_value=0.08,  # FAIL — above amended 0.05 threshold
        n_trades_raw=60,
        n_trades_n_eff=55,
        n_eff_threshold=50,
        t5_floor=50,
        p_threshold=0.05,
    )
    assert gate["passed"] is False
    assert gate["mc_gate_passed"] is False


def test_amended_gates_all_pass():
    """All amended gates pass = overall PASS."""
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=[0.8, 0.9, 1.0, 1.1, 1.2],
        mc_p_value=0.02,
        n_trades_raw=80,
        n_trades_n_eff=55,
        n_eff_threshold=50,
        t5_floor=50,
        p_threshold=0.05,
    )
    assert gate["passed"] is True
    assert gate.get("failed_criteria", []) == []


def test_amended_gates_backward_compat_v05():
    """Without n_eff/t5_floor args, defaults к v0.5 behavior (no n_eff check, no T5 check)."""
    # Backward-compat: existing callers без new args continue working
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=[0.8, 0.9, 1.0, 1.1, 1.2],
        mc_p_value=0.04,
    )
    assert "passed" in gate
    assert gate["sharpe_gate_passed"] is True
    assert gate["mc_gate_passed"] is True
    # No failed_criteria когда new args не provided
    assert gate.get("failed_criteria", []) == []
