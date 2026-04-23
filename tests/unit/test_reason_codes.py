"""Tests for ReasonCode enum extensions (Sprint 5 Task 1).

ADR ref: wiki/project/decisions/0019-sprint-5-execution-decisions.md sub-decision 4
"""

import sys
import pytest

# Direct import to bypass config parsing in Python 3.9
import importlib.util
spec = importlib.util.spec_from_file_location("reason_codes", "src/risk/reason_codes.py")
reason_codes_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reason_codes_module)
ReasonCode = reason_codes_module.ReasonCode


def test_halt_reconcile_divergence_in_enum():
    assert ReasonCode.HALT_RECONCILE_DIVERGENCE.value == "HALT_RECONCILE_DIVERGENCE"


def test_exit_oco_partial_timeout_in_enum():
    assert ReasonCode.EXIT_OCO_PARTIAL_TIMEOUT.value == "EXIT_OCO_PARTIAL_TIMEOUT"


def test_total_reason_codes_count():
    assert len(ReasonCode) == 31  # was 29 → +2 in S5
