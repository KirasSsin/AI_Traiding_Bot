"""ARCH-05 import-layering guard (S55 LOW).

Lower layers (src/backtest, src/dashboard) must NOT import from src.__main__ —
the CLI entry / composition root sits at the TOP of the dependency stack. The
OHLCV-loading + single-symbol WFA helpers were relocated to
src/backtest/data_loading.py so these runners depend on a peer module, not the
entry point. This static source-scan prevents the inversion from reappearing.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"

# Modules that previously reached into the CLI composition root for _load_ohlcv /
# _run_wfa_single_symbol (now src/backtest/data_loading.py).
_LOWER_LAYER_MODULES = [
    _SRC_ROOT / "backtest" / "volume_breakout_runner.py",
    _SRC_ROOT / "dashboard" / "backtest_runner.py",
    _SRC_ROOT / "backtest" / "data_loading.py",
]


def _imports_main(source_path: Path) -> bool:
    """True if the module has any `import src.__main__` / `from src.__main__ ...`."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "src.__main__":
            return True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "src.__main__":
                    return True
    return False


@pytest.mark.parametrize("module_path", _LOWER_LAYER_MODULES, ids=lambda p: p.name)
def test_lower_layer_does_not_import_from_cli_root(module_path: Path) -> None:
    assert module_path.exists(), f"expected source file missing: {module_path}"
    assert not _imports_main(module_path), (
        f"{module_path.name} imports from src.__main__ (CLI composition root) — "
        "layering inversion (ARCH-05). Import from src.backtest.data_loading instead."
    )
