# Sprint 53 — Kronos Real-Inference Enablement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. SEQUENTIAL dispatch (one task at a time — shared-branch parallel caused churn S50/S51). TDD strict. Per-task commit + SPRINT_STATE update. torch ABSENT in dev/CI — all tests mock-based; real inference = operator M4 only.

**Goal:** Make Kronos real-inference actually work (fix 3 shipped S52 bugs), support both model variants (base + mini) with correct per-variant tokenizer, adapt Signal to our bracket logic (real ATR), keep CI torch-free.

**Architecture:** Kronos code delivered via git submodule `third_party/kronos/` (pinned sha), imported `from model import ...` lazily inside `KronosModelAdapter.__init__` (sys.path scoped to the method, never module-level → CI isolation preserved). `KronosVariant` frozen dataclass encodes the tokenizer↔context coupling structurally. Signal rule V3 stays LOCKED (operator ESC-1); only the ATR=0 functional bug is fixed. Backtest remains exploratory `RAW_PRETRAIN_LEAKAGE_SUSPECTED`.

**Tech Stack:** Python 3.12, git submodule, torch (optional `[ml]`, mps on M4), pytest. Branch `feature/sprint-53-kronos-enablement`.

**Binding conditions (ADR 0069, from architecture PRE-PLAN):** C8 import fix · C9 submodule pinned sha · C10 KronosVariant dataclass · C11 extract `_kronos_dispatch.py` · C12 CI isolation + submodule-existence test · C13 two-step error message.

**Variants (locked):**
- `KRONOS_BASE` = (`NeoQuasar/Kronos-base`, `NeoQuasar/Kronos-Tokenizer-base`, ctx=512)
- `KRONOS_MINI` = (`NeoQuasar/Kronos-mini`, `NeoQuasar/Kronos-Tokenizer-2k`, ctx=2048)

**Pinned submodule sha:** `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (master HEAD per arch PRE-PLAN; operator verifies before first RUN_ML=1).

---

## File structure

| File | Responsibility | Task |
|------|----------------|------|
| `.gitmodules` + `third_party/kronos/` (submodule) | Kronos model code delivery | T1 |
| `tests/unit/test_kronos_submodule.py` | submodule existence guard (RUN_ML-gated) | T1 |
| `src/ml/kronos_variant.py` | `KronosVariant` dataclass + KRONOS_BASE/KRONOS_MINI singletons | T2 |
| `tests/unit/test_kronos_variant.py` | variant invariant tests | T2 |
| `src/ml/kronos_adapter.py` | import fix + variant param + error message | T3 |
| `src/signalgen/kronos_strategy.py` | real ATR fill (Track A) | T4 |
| `src/dashboard/_kronos_dispatch.py` (new) | extracted Kronos dispatch | T5 |
| `src/dashboard/backtest_runner.py` | delegate to `_kronos_dispatch`, variant presets | T5, T6 |
| `scripts/run_kronos_s53.py` (rename) | variant selector + tokenizer-2k fix + rebuild warning | T7 |
| `llm-wiki/.../decisions/0069-*.md` + wiki | ADR + sync + current-state split | T8 |

---

## Task T1: git submodule third_party/kronos + existence guard (C9, C12)

**Files:**
- Create: `.gitmodules` (git-managed), `third_party/kronos/` (submodule gitlink)
- Test: `tests/unit/test_kronos_submodule.py`

- [ ] **Step 1: Add the submodule (needs network — may require sandbox disable)**

Run:
```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git submodule add https://github.com/shiyu-coder/Kronos third_party/kronos
cd third_party/kronos && git checkout 67b630e67f6a18c9e9be918d9b4337c960db1e9a && cd ../..
```
Expected: `.gitmodules` created, `third_party/kronos/model/__init__.py` exists. If network blocked in sandbox → run with `dangerouslyDisableSandbox: true`. If still blocked → document in commit that operator must run `git submodule update --init` on M4; create `.gitmodules` manually + skip checkout.

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/test_kronos_submodule.py
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
```

- [ ] **Step 3: Run test to verify .gitmodules assertion**

Run: `.venv/bin/pytest tests/unit/test_kronos_submodule.py -v`
Expected: `test_gitmodules_registers_kronos` PASS, `test_kronos_model_module_present_when_run_ml` SKIPPED (no RUN_ML).

- [ ] **Step 4: Verify CI isolation unchanged**

Run: `.venv/bin/pytest tests/unit/test_ml_optional_dep.py -q`
Expected: 2 passed (AST guard only scans `src/`; `third_party/` invisible → no torch leak).

- [ ] **Step 5: Commit**

```bash
git add .gitmodules third_party/kronos tests/unit/test_kronos_submodule.py
git commit -m "feat(s53): git submodule third_party/kronos pinned + existence guard (C9 C12 T1)"
```

---

## Task T2: KronosVariant frozen dataclass (C10)

**Files:**
- Create: `src/ml/kronos_variant.py`
- Test: `tests/unit/test_kronos_variant.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_kronos_variant.py
from __future__ import annotations

import pytest

from src.ml.kronos_variant import KRONOS_BASE, KRONOS_MINI, KronosVariant, variant_by_name


def test_base_variant_fields() -> None:
    assert KRONOS_BASE.name == "base"
    assert KRONOS_BASE.model_id == "NeoQuasar/Kronos-base"
    assert KRONOS_BASE.tokenizer_id == "NeoQuasar/Kronos-Tokenizer-base"
    assert KRONOS_BASE.max_context == 512


def test_mini_variant_fields_correct_tokenizer() -> None:
    # mini MUST pair with the 2k tokenizer (S52 bug used -base)
    assert KRONOS_MINI.name == "mini"
    assert KRONOS_MINI.model_id == "NeoQuasar/Kronos-mini"
    assert KRONOS_MINI.tokenizer_id == "NeoQuasar/Kronos-Tokenizer-2k"
    assert KRONOS_MINI.max_context == 2048


def test_variant_is_frozen() -> None:
    with pytest.raises(Exception):
        KRONOS_BASE.max_context = 999  # type: ignore[misc]


def test_variant_by_name_resolves() -> None:
    assert variant_by_name("base") is KRONOS_BASE
    assert variant_by_name("mini") is KRONOS_MINI


def test_variant_by_name_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown Kronos variant"):
        variant_by_name("large")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_kronos_variant.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.ml.kronos_variant'`.

- [ ] **Step 3: Implement**

```python
# src/ml/kronos_variant.py
"""Kronos model variants (Sprint 53, ADR 0069 C10).

Each variant binds a (model_id, tokenizer_id, max_context) triple. The
tokenizer↔context coupling is encoded structurally so it cannot be set wrong:
mini REQUIRES the 2k tokenizer (ctx 2048); base/small REQUIRE the base
tokenizer (ctx 512). S52 paired mini with the base tokenizer — a bug.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KronosVariant:
    """Immutable Kronos model configuration."""

    name: str
    model_id: str
    tokenizer_id: str
    max_context: int


KRONOS_BASE = KronosVariant(
    name="base",
    model_id="NeoQuasar/Kronos-base",
    tokenizer_id="NeoQuasar/Kronos-Tokenizer-base",
    max_context=512,
)

KRONOS_MINI = KronosVariant(
    name="mini",
    model_id="NeoQuasar/Kronos-mini",
    tokenizer_id="NeoQuasar/Kronos-Tokenizer-2k",
    max_context=2048,
)

_BY_NAME: dict[str, KronosVariant] = {v.name: v for v in (KRONOS_BASE, KRONOS_MINI)}


def variant_by_name(name: str) -> KronosVariant:
    """Resolve a variant by its short name (``base`` | ``mini``)."""
    try:
        return _BY_NAME[name]
    except KeyError as exc:
        raise ValueError(f"unknown Kronos variant: {name!r}") from exc
```

- [ ] **Step 4: Run test + mypy**

Run: `.venv/bin/pytest tests/unit/test_kronos_variant.py -q && .venv/bin/mypy src/ml/kronos_variant.py --strict`
Expected: 5 passed, mypy 0 errors.

- [ ] **Step 5: Commit**

```bash
git add src/ml/kronos_variant.py tests/unit/test_kronos_variant.py
git commit -m "feat(s53): KronosVariant dataclass (base+mini, correct tokenizers) (C10 T2)"
```

---

## Task T3: adapter import fix + variant param + error message (C8, C13)

**Files:**
- Modify: `src/ml/kronos_adapter.py` (`KronosModelAdapter.__init__`, lines ~60-107; `_ML_EXTRA_HINT`)
- Test: `tests/unit/test_kronos_adapter.py` (extend)

- [ ] **Step 1: Write the failing test (ImportError message + variant signature)**

Add to `tests/unit/test_kronos_adapter.py`:
```python
def test_model_adapter_accepts_variant_and_raises_two_step_hint() -> None:
    from src.ml.kronos_variant import KRONOS_BASE
    from src.ml.kronos_adapter import KronosModelAdapter

    # torch/Kronos absent here → __init__ must raise ImportError with the
    # two-step operator instruction (submodule init + pip install ml).
    with pytest.raises(ImportError) as exc:
        KronosModelAdapter(variant=KRONOS_BASE, device="cpu")
    msg = str(exc.value)
    assert "submodule" in msg.lower()
    assert "[ml]" in msg
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_kronos_adapter.py::test_model_adapter_accepts_variant_and_raises_two_step_hint -q`
Expected: FAIL (current `__init__` takes `model_id`/`tokenizer_id`, not `variant`; old hint lacks "submodule").

- [ ] **Step 3: Rewrite `__init__` — variant param, sys.path-scoped import, two-step hint**

Replace `_ML_EXTRA_HINT` constant and `KronosModelAdapter.__init__` (read the file first). New `__init__`:
```python
    def __init__(
        self,
        variant: "KronosVariant",
        device: str = "mps",
        *,
        temperature: float = 1.0,
        top_p: float = 0.9,
        sample_count: int = 1,
        revision: str | None = None,
    ) -> None:
        """Load the Kronos model + tokenizer for ``variant`` (lazy import).

        SECURITY: pin ``revision`` to a verified commit SHA before any RUN_ML=1
        run — ``from_pretrained`` deserializes untrusted checkpoints (torch.load
        pickle = ACE). ``weights_hash`` is post-download provenance, NOT ACE
        prevention. The submodule sha pins the model *code*.

        Raises:
            ImportError: if the Kronos submodule code or torch is absent.
        """
        import os
        import sys

        kronos_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "third_party", "kronos")
        )
        try:
            if kronos_root not in sys.path:
                sys.path.insert(0, kronos_root)
            from model import (  # type: ignore[import-not-found]
                Kronos,
                KronosPredictor,
                KronosTokenizer,
            )
        except ImportError as exc:
            raise ImportError(
                "Kronos model code / torch unavailable. Two steps required: "
                "1) git submodule update --init third_party/kronos  "
                "2) pip install -e '.[ml]'"
            ) from exc

        self._device = device
        self._max_context = variant.max_context
        self._temperature = temperature
        self._top_p = top_p
        self._sample_count = sample_count

        model = Kronos.from_pretrained(variant.model_id, revision=revision)
        tokenizer = KronosTokenizer.from_pretrained(variant.tokenizer_id, revision=revision)
        self._predictor = KronosPredictor(
            model, tokenizer, device=device, max_context=variant.max_context
        )
```
Add `from src.ml.kronos_variant import KronosVariant` under `TYPE_CHECKING` (avoid runtime coupling cycle; it's only an annotation). Keep the existing `predict()` method unchanged below.

- [ ] **Step 4: Run adapter tests + isolation guard + mypy**

Run:
```bash
.venv/bin/pytest tests/unit/test_kronos_adapter.py tests/unit/test_ml_optional_dep.py -q
.venv/bin/mypy src/ml/kronos_adapter.py --strict
```
Expected: all pass (isolation guard STILL green — `from model import` is inside the method, not module top-level), mypy 0.

- [ ] **Step 5: Commit**

```bash
git add src/ml/kronos_adapter.py tests/unit/test_kronos_adapter.py
git commit -m "feat(s53): adapter from-model import via submodule + variant param + two-step hint (C8 C13 T3)"
```

---

## Task T4: KronosStrategy real ATR fill (Track A, CC2 — BLOCKER)

**Files:**
- Modify: `src/signalgen/kronos_strategy.py` (`__init__`, `on_bar`, `_build_signal`)
- Test: `tests/unit/test_kronos_strategy.py` (extend)

**Problem:** `_build_signal` sets `atr_14=Decimal("0")`. risk_manager sizes the SL/TP bracket from `Signal.atr_14` → ATR=0 means SL == entry price (or division-by-zero) → untradeable. Fix: maintain an incremental Wilder ATR over closed bars (reuse the project's existing `wilder_atr` / `_WilderATR` from `src/signalgen/indicators.py` — grep it first) and fill the real value.

- [ ] **Step 1: Confirm the existing ATR utility**

Run: `grep -n "wilder_atr\|class _WilderATR\|def atr" src/signalgen/indicators.py`
Expected: an incremental Wilder ATR helper exists (added S50/S51). Note its exact API (constructor + update(high, low, close) → Decimal | None during warm-up).

- [ ] **Step 2: Write the failing test**

Add to `tests/unit/test_kronos_strategy.py`:
```python
def test_signal_carries_real_atr_not_zero() -> None:
    """ENTRY/EXIT signals must have atr_14 > 0 after warm-up (bracket sizing)."""
    from decimal import Decimal
    # Build a strategy + feed >14 closed bars with non-trivial ranges so ATR warms up,
    # pre-populate cache to trigger an ENTRY on the last bar.
    strat = _make_kronos_strategy_with_cached_entry(period=14)  # test helper
    signal = _feed_warmup_then_entry(strat)  # returns the ENTRY signal
    assert signal is not None
    assert signal.reason == "ENTRY_LONG_KRONOS"
    assert signal.atr_14 > Decimal("0")  # NOT the old _ZERO stub
```
(Adapt `_make_kronos_strategy_with_cached_entry` / `_feed_warmup_then_entry` to the existing test fixtures in this file — reuse the cache-population + bar-construction helpers already present.)

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/bin/pytest tests/unit/test_kronos_strategy.py::test_signal_carries_real_atr_not_zero -q`
Expected: FAIL — `atr_14` is currently `Decimal("0")`.

- [ ] **Step 4: Implement — incremental ATR in the strategy**

In `KronosStrategy.__init__`: instantiate the Wilder ATR helper (`self._atr = _WilderATR(period=atr_period)` with `atr_period: int = 14` constructor param). In `on_bar` (AFTER the `is_closed` gate, BEFORE returning, for EVERY closed bar regardless of signal): `atr_value = self._atr.update(bar.high, bar.low, bar.close)`. Cache the latest non-None `atr_value` in `self._last_atr`. In `_build_signal`: pass `atr_14=self._last_atr if self._last_atr is not None else _ZERO`. If ATR not yet warmed up (None) on a bar that would ENTRY → return None (no trade without a valid SL — look-ahead-safe + risk-safe). Keep all other indicator fields `_ZERO` (Kronos doesn't compute EMA/RSI/etc.).

- [ ] **Step 5: Run test + isolation + mypy**

Run:
```bash
.venv/bin/pytest tests/unit/test_kronos_strategy.py tests/unit/test_ml_optional_dep.py -q
.venv/bin/mypy src/signalgen/kronos_strategy.py --strict
```
Expected: all pass, mypy 0. Update any existing test that asserted `atr_14 == 0` for Kronos signals.

- [ ] **Step 6: Commit**

```bash
git add src/signalgen/kronos_strategy.py tests/unit/test_kronos_strategy.py
git commit -m "fix(s53): KronosStrategy fills real Wilder ATR (bracket sizing, was 0) (Track A CC2 T4)"
```

---

## Task T5: extract _kronos_dispatch.py from backtest_runner (C11)

**Files:**
- Create: `src/dashboard/_kronos_dispatch.py`
- Modify: `src/dashboard/backtest_runner.py` (move Kronos functions, import + delegate)
- Test: `tests/unit/test_dashboard_kronos_preset.py` (still green) + `tests/unit/test_kronos_dispatch.py` (new)

**Why:** backtest_runner.py = 1682 LoC > 1500 HARD-GATE. Extract the Kronos-specific helpers (`_KRONOS_CACHE_DIR`, `_KRONOS_MANIFEST_NAME`, `_KRONOS_PARQUET_BY_COMBO`, `_read_kronos_manifest`, `_load_kronos_df`, the `type=="kronos"` dispatch body) into a focused module BEFORE adding variant branching (T6).

- [ ] **Step 1: Characterize current behavior (safety net)**

Run: `.venv/bin/pytest tests/unit/test_dashboard_kronos_preset.py -q`
Expected: GREEN baseline (record count). These tests must stay green after extraction.

- [ ] **Step 2: Create `_kronos_dispatch.py` with the moved functions**

Move (cut, not copy) from `backtest_runner.py`: the Kronos constants + `_read_kronos_manifest` + `_load_kronos_df` + a new `run_kronos_dispatch(req, *, cache_dir=_KRONOS_CACHE_DIR) -> dict[str, Any]` that contains the current `type=="kronos"` branch body (manifest read → cache-absent honest result OR `run_kronos_exploratory`). Full type hints + English docstrings. NO torch import.

- [ ] **Step 3: Rewire `backtest_runner.py` to delegate**

Replace the inline `type=="kronos"` block with:
```python
if preset.get("type") == "kronos":
    from src.dashboard._kronos_dispatch import run_kronos_dispatch
    return run_kronos_dispatch(req)
```

- [ ] **Step 4: Write a focused dispatch test**

```python
# tests/unit/test_kronos_dispatch.py
"""Direct tests for the extracted Kronos dispatch module."""
from __future__ import annotations
# ... import run_kronos_dispatch, build a req for an unsupported combo / no-cache /
# manifest-keyed cache (mirror the assertions previously in test_dashboard_kronos_preset.py:
# no-manifest → "not built", manifest+cache → hits, unsupported combo → ValueError).
```
Move the dispatch-level assertions here; keep preset-registry assertions in `test_dashboard_kronos_preset.py`.

- [ ] **Step 5: Verify size + tests + mypy**

Run:
```bash
wc -l src/dashboard/backtest_runner.py        # expect < 1500
.venv/bin/pytest tests/unit/test_dashboard_kronos_preset.py tests/unit/test_kronos_dispatch.py tests/unit/test_ml_optional_dep.py -q
.venv/bin/mypy src/dashboard/_kronos_dispatch.py src/dashboard/backtest_runner.py --strict
```
Expected: backtest_runner < 1500 LoC, all tests green, mypy 0.

- [ ] **Step 6: Commit**

```bash
git add src/dashboard/_kronos_dispatch.py src/dashboard/backtest_runner.py tests/unit/test_kronos_dispatch.py tests/unit/test_dashboard_kronos_preset.py
git commit -m "refactor(s53): extract _kronos_dispatch.py (backtest_runner <1500 LoC) (C11 T5)"
```

---

## Task T6: variant dispatch + presets + no-cherry-pick warning (Q2, Q4)

**Files:**
- Modify: `src/dashboard/_kronos_dispatch.py` (variant param in CacheKey reconstruction), `src/dashboard/backtest_runner.py` (presets)
- Test: `tests/unit/test_dashboard_kronos_preset.py` (extend), `tests/unit/test_kronos_dispatch.py`

- [ ] **Step 1: Write the failing test (both variants present + warning text)**

```python
def test_kronos_presets_expose_both_variants() -> None:
    from src.dashboard.backtest_runner import STRATEGY_PRESETS
    kp = STRATEGY_PRESETS["kronos"]
    variants = kp.get("supported_variants") or [v["variant"] for v in kp.get("variants", [])]
    assert set(variants) == {"base", "mini"}

def test_kronos_description_warns_no_cherry_pick() -> None:
    from src.dashboard.backtest_runner import STRATEGY_PRESETS
    desc = STRATEGY_PRESETS["kronos"]["description"]
    # Q4: forbid selecting "best" variant/combo by backtest
    assert "не выбир" in desc.lower() or "selection bias" in desc.lower() or "best" in desc.lower()
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv/bin/pytest tests/unit/test_dashboard_kronos_preset.py -k "variant or cherry" -q`
Expected: FAIL.

- [ ] **Step 3: Implement variant in preset + dispatch**

Add `supported_variants: ["base", "mini"]` (or a `variants` list) to the `kronos` preset; extend RU `description` with the Q4 warning ("сравнение вариантов/комбо по backtest НЕ обоснование выбора — leakage, нужен forward paper-trade"). In `run_kronos_dispatch`, read the requested `variant` from `req` (default "base"), resolve via `variant_by_name`, and use `variant.model_id` when reconstructing the lookup CacheKey from the manifest (manifest already stores `model_id`; match against the requested variant's model_id — if manifest model_id != requested variant → honest "this variant not cached" message). Keep verdict `RAW_PRETRAIN_LEAKAGE_SUSPECTED`.

- [ ] **Step 4: Run + frontend build (if types touched)**

Run:
```bash
.venv/bin/pytest tests/unit/test_dashboard_kronos_preset.py tests/unit/test_kronos_dispatch.py -q
```
If `req` schema gained a `variant` field that the React app must send → update `src/dashboard_react/src/api/types.ts` + run `cd src/dashboard_react && npm run build && npm run test`. Else report "frontend untouched".

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(s53): Kronos both-variant presets + dispatch + no-cherry-pick warning (Q2 Q4 T6)"
```

---

## Task T7: rename script run_kronos_s53.py + variant selector + tokenizer-2k + rebuild warning (CC1, CC4, CC5)

**Files:**
- Rename: `scripts/run_kronos_s52.py` → `scripts/run_kronos_s53.py` (git mv)
- Modify: the renamed script (use `KronosVariant`, `--variant` arg, manifest per variant, rebuild warning)
- Test: `tests/unit/test_run_kronos_s52_smoke.py` → rename to `test_run_kronos_s53_smoke.py`

- [ ] **Step 1: git mv + update smoke test import**

Run:
```bash
git mv scripts/run_kronos_s52.py scripts/run_kronos_s53.py
git mv tests/unit/test_run_kronos_s52_smoke.py tests/unit/test_run_kronos_s53_smoke.py
```
Update the smoke test's module-path references (`run_kronos_s52` → `run_kronos_s53`).

- [ ] **Step 2: Write/adjust failing smoke test (variant arg + tokenizer correctness)**

In `tests/unit/test_run_kronos_s53_smoke.py`:
```python
def test_script_uses_kronos_variant_singletons() -> None:
    mod = _import_script()  # existing helper
    # No hardcoded mismatched MODEL_ID/TOKENIZER_ID constants; uses KronosVariant.
    from src.ml.kronos_variant import KRONOS_BASE, KRONOS_MINI
    assert mod.resolve_variant("base") is KRONOS_BASE
    assert mod.resolve_variant("mini") is KRONOS_MINI
    # mini paired with 2k tokenizer (S52 bug fixed)
    assert KRONOS_MINI.tokenizer_id.endswith("Tokenizer-2k")
```

- [ ] **Step 3: Run to verify fail**

Run: `.venv/bin/pytest tests/unit/test_run_kronos_s53_smoke.py -q`
Expected: FAIL (script still has hardcoded `MODEL_ID`/`TOKENIZER_ID`).

- [ ] **Step 4: Implement — variant-driven script**

Replace hardcoded `MODEL_ID`/`TOKENIZER_ID`/`MAX_CONTEXT` with `KronosVariant` resolution: add `--variant {base,mini}` CLI arg (or env `KRONOS_VARIANT`, default base), `resolve_variant(name)` → `variant_by_name`. Pass `variant` to `KronosModelAdapter(variant=...)`. `_compute_weights_hash` hashes the variant's model+tokenizer repos. Per-variant manifest entry (manifest stores `model_id` = variant.model_id). Add a printed WARNING (CC4): "changing variant/tokenizer changes weights_hash → old cache entries become MISS → full rebuild required." Keep RUN_ML guard + KRONOS_REVISION + torch-only-in-RUN_ML-branch.

- [ ] **Step 5: Verify (no RUN_ML) + full suite**

Run:
```bash
.venv/bin/python scripts/run_kronos_s53.py --variant base   # prints skip+instructions, exit 0, no torch
.venv/bin/pytest tests/unit -q
.venv/bin/mypy scripts/run_kronos_s53.py --strict
```
Expected: skip message exit 0; full suite green; mypy 0. Grep for stale `run_kronos_s52` references across repo + wiki and update.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(s53): run_kronos_s53 variant selector + tokenizer-2k fix + rebuild warning (CC1 CC4 CC5 T7)"
```

---

## Task T8: predict() signature verify + ADR 0069 + wiki sync + current-state split (C12, CC3)

**Files:**
- Test: `tests/unit/test_kronos_adapter.py` (signature-shape assertion against mock that mimics real API)
- Create: `llm-wiki/wiki/project/decisions/0069-sprint-53-kronos-enablement.md`
- Modify: ADR 0068 (note import corrected in S53), `kronos-adapter.md`, `current-state.md` (+ split), `index.md`, `mental-map.md`, `log.md`, `sprints/sprint-53-kronos-enablement.md`

- [ ] **Step 1: predict() signature-shape guard (CC3)**

Add a test where a stand-in predictor object records the kwargs `KronosModelAdapter.predict` forwards to `self._predictor.predict(...)`, asserting it passes `df, x_timestamp, y_timestamp, pred_len, T, top_p, sample_count` (the real Kronos API) and reads `pred_df["close"]`. (Inject the stand-in by constructing the adapter with a patched `_predictor` — bypass the torch `__init__` via `object.__new__` + manual attr set, or a small factory. Goal: lock the call contract without torch.)

Run: `.venv/bin/pytest tests/unit/test_kronos_adapter.py -q` → GREEN.

- [ ] **Step 2: Create ADR 0069 (RU, status accepted)**

`## Контекст` (S52 shipped broken real-inference: import, tokenizer, ATR). `## Решение` (C8-C13 + Q1 submodule rationale incl. pip-from-git IMPOSSIBLE empirically + Q2 variant + Q3 V3-locked+ATR + Q4 no-cherry-pick + Q5 forward defer). `## Последствия` (real inference works on M4; operator must `git submodule update --init`; both variants exploratory). Link pre-s53-backlog + ADR 0068 + ADR 0014.

- [ ] **Step 3: current-state.md split (carry — 54KB > 50KB)**

Split per universal pattern: `current-state.md` (index + frontmatter + canonical-counts table + pointers) + `current-state-part-2.md` (sprint-history table). Verify both < 50KB. Update inbound links.

- [ ] **Step 4: Wiki sync**

Update `kronos-adapter.md` (variant param, submodule delivery, from-model import). current-state: add S53 row (no canonical count change — reason codes still 67, FSM unchanged). sprint-53 page. index.md ADR 0069 + sprint-53. mental-map (submodule location). log.md sprint-end entry.

- [ ] **Step 5: Verify counts + commit**

Run: `.venv/bin/python -c "from src.risk.reason_codes import ReasonCode; print(len(list(ReasonCode)))"` → 67.
```bash
git add llm-wiki/ tests/unit/test_kronos_adapter.py
git commit -m "docs(s53): ADR 0069 + predict-sig guard + current-state split + wiki sync (C12 CC3 T8)"
```

---

## PHASE 5 gates
pytest full suite GREEN (torch absent) · mypy --strict 0 · reason codes 67 (unchanged) · backtest_runner < 1500 LoC · `test_ml_optional_dep` AST guard GREEN (order-independent) · frontend build/Vitest clean (if touched) · `.venv/bin/python scripts/run_kronos_s53.py --variant base` skip-exit-0 no-torch.

## PHASE 6 reviewers (parallel)
architecture (C8-C13 met, submodule isolation) · python · trading-logic (ATR fix → bracket sizing correctness, V3 still look-ahead-safe) · data-integrity (variant cache-key parity, manifest per variant, tokenizer→weights_hash invalidation) · test-engineer (mock-vs-real boundary, submodule guard) · security (submodule sha pin + revision pin ACE) · dashboard (variant presets, no-cherry-pick warning surfaced) · doc.

## PHASE 8 ship
tag v0.1.0-alpha.53. Operator: `git submodule update --init third_party/kronos` → `pip install -e ".[ml]"` → set `KRONOS_REVISION` → `RUN_ML=1 .venv/bin/python scripts/run_kronos_s53.py --variant base` (and `--variant mini`) → exploratory backtest both variants.

## Self-Review
- C8→T3 · C9→T1 · C10→T2 · C11→T5 · C12→T1+T8 · C13→T3. CC1→T3+T7 · CC2→T4 · CC3→T8 · CC4→T7 · CC5→T7. Q2→T6 · Q3→T4(A)+deferred(B) · Q4→T6 · Q5→deferred S54+.
- Real inference unverifiable here (torch absent) → all tests mock/structural; M4 run is the real validation (post-ship).
- Sequential dispatch. torch never in CI/hot-path. Signal rule V3 unchanged (only ATR fill added).
