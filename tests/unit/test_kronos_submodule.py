"""Guard: Kronos submodule must be present for real inference (RUN_ML=1)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KRONOS_MODEL_INIT = _REPO_ROOT / "third_party" / "kronos" / "model" / "__init__.py"


def test_gitmodules_registers_kronos() -> None:
    gitmodules = _REPO_ROOT / ".gitmodules"
    assert gitmodules.exists(), ".gitmodules missing"
    text = gitmodules.read_text(encoding="utf-8")
    assert "third_party/kronos" in text
    assert "shiyu-coder/Kronos" in text


@pytest.mark.skipif(
    os.environ.get("RUN_ML") != "1",
    reason="Kronos submodule content only required for real inference (RUN_ML=1)",
)
def test_kronos_model_module_present_when_run_ml() -> None:
    assert _KRONOS_MODEL_INIT.exists(), (
        "third_party/kronos/model/__init__.py missing — run "
        "`git submodule update --init third_party/kronos`"
    )
