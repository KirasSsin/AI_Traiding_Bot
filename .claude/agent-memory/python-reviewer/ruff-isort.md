---
name: Ruff import sort (I001) in test files
description: Test files with from __future__ import annotations + pytest imports trigger ruff I001 when isort grouping is off
type: feedback
---

Rule: ruff I001 fires in test files when `from __future__ import annotations` block is not separated from stdlib imports AND pytest (third-party) is not in its own group.

**Why:** ruff enforces isort section ordering: future → stdlib → third-party → first-party. When `from __future__` and `from decimal import Decimal` (stdlib) and `import pytest` (third-party) are written in a single contiguous block without a blank line separating third-party from stdlib, I001 triggers.

**How to apply:** flag ruff I001 in test files as a MEDIUM concern (fixable with `ruff --fix`), not a blocker. The fix is automatic — do not manually reorder. Remind that `pyproject.toml` isort config may need `known_third_party = ["pytest"]` if auto-detection is unreliable.
