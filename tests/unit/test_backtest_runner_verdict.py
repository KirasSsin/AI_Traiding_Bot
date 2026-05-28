"""S49 BATCH 5 (H8+H10) — _compute_verdict helper unit tests.

trader-expert BINDING verdict: ТОЛЬКО gate-blocking критерии определяют verdict:
  - T5 n_trades floor (>= 50)
  - DSR (>= 0.95) → dsr_pass
  - MC permutation (p <= 0.05) → mc_pass
  - per-fold OOS/IS Sharpe (>= 0.7) → failed_folds
  - n_eff (>= 50)

Informational (НЕ блокируют verdict, отображаются в UI): T1/T2/T3/T4/T6.
Canonical criterion keys MUST match FailAnalysisTab ALL_CRITERIA:
  t5_floor / sharpe_gate / mc_gate / dsr_threshold / n_eff_threshold.
"""

from __future__ import annotations

import pytest
from src.dashboard.backtest_runner import _compute_verdict


# Helper: all-pass baseline kwargs (gates green).
def _passing() -> dict[str, object]:
    return {
        "n_trades": 120,
        "dsr_pass": True,
        "mc_pass": True,
        "failed_folds": [],
        "n_eff": 60,
    }


def test_all_gates_pass_verdict_pass() -> None:
    failed, verdict = _compute_verdict(**_passing())  # type: ignore[arg-type]
    assert failed == []
    assert verdict == "PASS"


# --- T3 (max drawdown) NEVER gates — informational. ---
# The helper никогда не получает T3 как вход — verdict не зависит от drawdown.
# Любой исход gate-blocking входов не порождает "t3" в failed_criteria.
@pytest.mark.parametrize("failed_folds", [[], [0], [1, 2]])
def test_t3_never_in_failed_criteria(failed_folds: list[int]) -> None:
    kwargs = _passing()
    kwargs["failed_folds"] = failed_folds
    failed, _ = _compute_verdict(**kwargs)  # type: ignore[arg-type]
    assert "t3" not in failed


# --- T1/T2/T4/T6 informational — never appear. ---
def test_informational_criteria_never_appear() -> None:
    # Force every gate to fail → failed_criteria full of gate-blocking keys.
    failed, verdict = _compute_verdict(
        n_trades=10,
        dsr_pass=False,
        mc_pass=False,
        failed_folds=[0, 1],
        n_eff=5,
    )
    assert verdict == "FAIL"
    for informational in ("t1", "t2", "t3", "t4", "t6"):
        assert informational not in failed


# --- T5 n_trades floor. ---
def test_t5_floor_below_50_fails() -> None:
    kwargs = _passing()
    kwargs["n_trades"] = 49
    failed, verdict = _compute_verdict(**kwargs)  # type: ignore[arg-type]
    assert "t5_floor" in failed
    assert verdict == "FAIL"


def test_t5_floor_at_50_passes() -> None:
    kwargs = _passing()
    kwargs["n_trades"] = 50
    failed, verdict = _compute_verdict(**kwargs)  # type: ignore[arg-type]
    assert "t5_floor" not in failed
    assert verdict == "PASS"


# --- DSR gate. ---
def test_dsr_fail_appends_dsr_threshold() -> None:
    kwargs = _passing()
    kwargs["dsr_pass"] = False
    failed, verdict = _compute_verdict(**kwargs)  # type: ignore[arg-type]
    assert "dsr_threshold" in failed
    assert verdict == "FAIL"


# --- MC gate. ---
def test_mc_fail_appends_mc_gate() -> None:
    kwargs = _passing()
    kwargs["mc_pass"] = False
    failed, verdict = _compute_verdict(**kwargs)  # type: ignore[arg-type]
    assert "mc_gate" in failed
    assert verdict == "FAIL"


# --- Sharpe gate (per-fold). ---
def test_failed_folds_appends_sharpe_gate() -> None:
    kwargs = _passing()
    kwargs["failed_folds"] = [0, 2]
    failed, verdict = _compute_verdict(**kwargs)  # type: ignore[arg-type]
    assert "sharpe_gate" in failed
    assert verdict == "FAIL"


# --- n_eff floor. ---
def test_n_eff_below_50_appends_n_eff_threshold() -> None:
    kwargs = _passing()
    kwargs["n_eff"] = 49
    failed, verdict = _compute_verdict(**kwargs)  # type: ignore[arg-type]
    assert "n_eff_threshold" in failed
    assert verdict == "FAIL"


def test_only_canonical_keys_emitted() -> None:
    """Every emitted key must be a FailAnalysisTab gate-blocking canonical key."""
    canonical = {"t5_floor", "sharpe_gate", "mc_gate", "dsr_threshold", "n_eff_threshold"}
    failed, _ = _compute_verdict(
        n_trades=10,
        dsr_pass=False,
        mc_pass=False,
        failed_folds=[0],
        n_eff=5,
    )
    assert set(failed) <= canonical
    assert set(failed) == canonical
