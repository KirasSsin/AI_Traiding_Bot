"""Smoke tests for scripts/run_kronos_s52.py — torch-free CI guard.

Verifies:
1. The module imports successfully without torch installed.
2. COMBOS contains exactly the 11 (symbol, timeframe) pairs from ADR 0068.
3. The RUN_ML guard: calling main() without RUN_ML=1 prints the skip message
   and returns 0, without any torch ImportError.
4. COMBOS elements are (str, str) tuples with valid values.
"""

from __future__ import annotations

import importlib
import os
import sys
import types

import pytest


@pytest.fixture(autouse=True)
def _cleanup_torch_stub() -> None:
    """Remove any torch=None stub from sys.modules after each test.

    _import_script() injects ``sys.modules["torch"] = None`` to prevent
    accidental torch imports during the smoke test.  Without cleanup this
    stub leaks across test sessions and breaks test_ml_optional_dep.py's
    ``test_core_imports_without_torch`` (which asserts torch is absent).
    The fixture is autouse so every test in this module is covered.
    """
    yield  # type: ignore[misc]
    sys.modules.pop("torch", None)


def _import_script() -> types.ModuleType:
    """Import scripts/run_kronos_s52.py cleanly, ensuring no torch side-effect."""
    # Ensure torch is NOT importable so a top-level import would fail loudly.
    sys.modules.setdefault("torch", None)  # type: ignore[assignment]

    # Add repo root to path (mirrors scripts/ convention).
    from pathlib import Path

    repo_root = str(Path(__file__).resolve().parent.parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Invalidate caches in case prior import attempt happened.
    importlib.invalidate_caches()
    return importlib.import_module("scripts.run_kronos_s52")


def test_module_imports_without_torch() -> None:
    """Module must import cleanly even when torch is absent."""
    mod = _import_script()
    assert mod is not None


def test_combos_count() -> None:
    """COMBOS must contain exactly 11 entries (ADR 0068 scope)."""
    mod = _import_script()
    assert len(mod.COMBOS) == 11


def test_combos_symbols_and_timeframes() -> None:
    """COMBOS must match the 11 (symbol, timeframe) pairs from ADR 0068."""
    mod = _import_script()
    expected = {
        ("BTCUSDT", "5m"),
        ("BTCUSDT", "15m"),
        ("BTCUSDT", "1h"),
        ("BTCUSDT", "4h"),
        ("BTCUSDT", "1d"),
        ("ETHUSDT", "15m"),
        ("ETHUSDT", "1h"),
        ("ETHUSDT", "4h"),
        ("SOLUSDT", "15m"),
        ("SOLUSDT", "1h"),
        ("SOLUSDT", "4h"),
    }
    # Each COMBO is (symbol, timeframe, parquet_path) — extract first two fields.
    actual = {(c[0], c[1]) for c in mod.COMBOS}
    assert actual == expected


def test_no_run_ml_exits_zero(capsys: object) -> None:
    """Without RUN_ML=1, main() must print the skip message and return 0."""
    # Ensure RUN_ML is not set.
    os.environ.pop("RUN_ML", None)
    mod = _import_script()

    ret = mod.main()

    assert ret == 0, f"Expected exit 0 without RUN_ML, got {ret}"
    captured = capsys.readouterr()
    output = captured.out + captured.err
    # Must mention the skip / instruction.
    assert "RUN_ML" in output or "pip install" in output.lower() or "skip" in output.lower()


def test_combos_are_three_tuples() -> None:
    """Each COMBO must be a 3-tuple: (symbol, timeframe, parquet_path)."""
    mod = _import_script()
    for combo in mod.COMBOS:
        assert len(combo) == 3, f"Expected 3-tuple, got {combo!r}"
        symbol, timeframe, path = combo
        assert isinstance(symbol, str)
        assert isinstance(timeframe, str)
        assert isinstance(path, str)
        assert path.endswith(".parquet"), f"Expected .parquet path, got {path!r}"
