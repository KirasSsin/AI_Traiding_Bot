"""T1 torch-isolation guard (Sprint 52 Kronos C1).

Test A: Core modules (signalgen + 6 strategies + dashboard backtest_runner) import
        successfully even when torch is absent (it is absent in dev env by design).

Test B: No source file OUTSIDE src/ml/ contains a top-level `import torch` /
        `from torch` statement. Regression guard for C1 lazy-isolation invariant.
"""

import ast
import importlib
import os
import sys


def test_core_imports_without_torch() -> None:
    """Test A: core modules import cleanly with torch absent."""
    # Verify torch is genuinely absent (the whole point of this test).
    assert "torch" not in sys.modules, "torch must not be pre-imported"
    try:
        # If torch IS installed, we can't falsify isolation here — skip gracefully.
        import pytest
        import torch  # noqa: F401

        pytest.skip("torch is installed in this env; isolation test N/A")
    except ImportError:
        pass  # Expected: torch absent — proceed to import checks.

    modules_under_test = [
        "src.signalgen",
        "src.signalgen.strategy",
        "src.signalgen.atr_breakout_strategy",
        "src.signalgen.donchian_strategy",
        "src.signalgen.mean_reversion_strategy",
        "src.signalgen.supertrend_strategy",
        "src.signalgen.volume_breakout_strategy",
        "src.dashboard.backtest_runner",
    ]
    for mod in modules_under_test:
        importlib.import_module(mod)  # raises ImportError if broken


def test_no_top_level_torch_import_outside_ml() -> None:
    """Test B: no *.py file outside src/ml/ has a top-level torch import."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src_root = os.path.join(repo_root, "src")

    violations: list[str] = []

    for dirpath, _dirnames, filenames in os.walk(src_root):
        # Skip src/ml/ — that is where torch IS allowed.
        rel_dir = os.path.relpath(dirpath, src_root)
        if rel_dir == "ml" or rel_dir.startswith("ml" + os.sep):
            continue

        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, encoding="utf-8") as fh:
                    source = fh.read()
                tree = ast.parse(source, filename=filepath)
            except SyntaxError:
                continue  # Skip unparseable files (generated, etc.)

            for node in ast.iter_child_nodes(tree):
                # Only top-level (module-body) imports.
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "torch" or alias.name.startswith("torch."):
                            violations.append(f"{filepath}: import {alias.name}")
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and (node.module == "torch" or node.module.startswith("torch."))
                ):
                    violations.append(f"{filepath}: from {node.module} import ...")

    assert violations == [], (
        "Top-level torch imports found outside src/ml/ (breaks C1 isolation):\n"
        + "\n".join(violations)
    )
