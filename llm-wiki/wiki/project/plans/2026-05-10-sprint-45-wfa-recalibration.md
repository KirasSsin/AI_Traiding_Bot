---
title: "Sprint 45 — WFA recalibration + quant discipline corrections + uniform 3.3y data"
type: plan
tags: [sprint-45, wfa-recalibration, dsr, cross-trial-log, data-uniform]
created: 2026-05-10
updated: 2026-05-10
status: ready
sources:
  - llm-wiki/wiki/project/pre-s45-backlog.md
---

# Sprint 45 — WFA Recalibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix S44 quant discipline gaps (B1 cross_trial_log dedup, C1 n_trials per-strategy, B2 train slice docs), make data uniform 3.3y (remove 8.7y BTC binance exception), recalibrate WFA params для 4H/D low-frequency tier (1 attempt only per ESC-1), re-run 11 combos и capture honest verdict.

**Architecture:** ADR 0014 amendment introduces low-frequency tier (4H/D: test_bars=250, train_bars=1500, k_folds=5, embargo=20) — anti-snooping derived from trade-frequency analysis в ADR 0065 BEFORE recalibration run. CrossTrialLog gains idempotency guard в `append_trial()` via composite key (sprint, symbol). `run_research_wfa()` default `n_trials` 11→1 (fail-safe); per-runner explicit pass. Uniform 3.3y data — `BTCUSDT_4h_binance.parquet` removed from registry.

**Tech Stack:** Python 3.12, pytest, numpy, pandas. NO new dependencies.

**Branch:** `feature/sprint-45-wfa-recalibration`

**Models:** opus T6 (ADR 0014 amendment + recalibration code — judgment-heavy, anti-snooping discipline). sonnet T1-T5, T7-T8.

---

## File Trace Map (PHASE 3 step 1a HARD-GATE)

| File | Action | Tasks |
|------|--------|-------|
| `src/backtest/atr_breakout_runner.py:51` | MODIFY (`PARQUET_BY_COMBO[(BTCUSDT, 240)]` change) | T1 |
| `data/BTCUSDT_4h_binance.parquet` | DELETE (move к `data/_archive/`) | T1 |
| `src/analytics/cross_trial_log.py:97-119` | MODIFY (`append_trial()` idempotency guard) | T3 |
| `data/cross_trial_sharpes.json` | RESET к `{"trials": []}` | T3 |
| `src/backtest/research_wfa.py` | MODIFY (default n_trials=1, B2 docs, low-freq tier) | T4 + T5 + T6 |
| `src/backtest/atr_breakout_runner.py` (`_run_atr_breakout_wfa`) | MODIFY (n_trials=10 explicit, low-freq tier select) | T4 + T6 |
| `src/backtest/volume_breakout_runner.py` (`_run_volume_breakout_wfa`) | MODIFY (n_trials=1 explicit, low-freq tier select) | T4 + T6 |
| `tests/integration/test_atr_breakout_baseline_floor.py` | MODIFY (3.3y window) | T1 |
| `tests/integration/test_atr_breakout_dashboard_contract.py` | MODIFY (3.3y window assertions) | T1 |
| `tests/integration/test_atr_breakout_wfa.py` | MODIFY (n_trials assertion + 3.3y) | T4 |
| `tests/integration/test_volume_breakout_wfa.py` | MODIFY (n_trials=1 assertion) | T4 |
| `tests/unit/test_cross_trial_log.py` | CREATE OR EXTEND (dedup tests) | T3 |
| `tests/unit/test_research_wfa.py` | MODIFY (default n_trials=1 test, low-freq tier test) | T4 + T6 |
| `llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md` | MODIFY (amendment section) | T6 |
| `llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-pre-registration.md` | MODIFY (3.3y baseline note) | T2 |
| `llm-wiki/wiki/project/decisions/0065-sprint-45-wfa-recalibration.md` | CREATE | T8 |
| `llm-wiki/wiki/project/sprints/sprint-45-wfa-recalibration.md` | CREATE | T8 |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY | T8 |
| `llm-wiki/wiki/index.md` + `log.md` | MODIFY/APPEND | T8 |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY (per-task) | every task |

---

## Task 1: Uniform 3.3y data — remove 8.7y BTC binance exception

**Files:**
- Modify: `src/backtest/atr_breakout_runner.py:51` (PARQUET_BY_COMBO entry)
- Move: `data/BTCUSDT_4h_binance.parquet` → `data/_archive/BTCUSDT_4h_binance.parquet`
- Modify: `tests/integration/test_atr_breakout_baseline_floor.py` (3.3y window dates)
- Modify: `tests/integration/test_atr_breakout_dashboard_contract.py` (3.3y assertions)

- [ ] **Step 1: Failing test**

Append к `tests/integration/test_atr_breakout_baseline_floor.py`:

```python
@pytest.mark.integration
def test_atr_breakout_btc_4h_uses_3y_data_not_binance_8y() -> None:
    """S45 T1 — uniform 3.3y data. PARQUET_BY_COMBO[(BTCUSDT,240)] must point к 3.3y file."""
    from src.backtest.atr_breakout_runner import PARQUET_BY_COMBO
    path = PARQUET_BY_COMBO[("BTCUSDT", "240")]
    assert "binance" not in path.lower(), f"BTC 4H still using 8.7y binance file: {path}"
    assert "BTCUSDT_4h.parquet" in path, f"Expected 3.3y file, got: {path}"
```

- [ ] **Step 2: Verify FAIL**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_baseline_floor.py::test_atr_breakout_btc_4h_uses_3y_data_not_binance_8y -v -m integration
```

Expected: FAIL — currently `PARQUET_BY_COMBO[("BTCUSDT", "240")] = "data/BTCUSDT_4h_binance.parquet"`.

- [ ] **Step 3: Update PARQUET_BY_COMBO**

In `src/backtest/atr_breakout_runner.py:51-65`, find:
```python
PARQUET_BY_COMBO: dict[tuple[str, str], str] = {
    ("BTCUSDT", "15"): "data/BTCUSDT_15m.parquet",
    ("BTCUSDT", "240"): "data/BTCUSDT_4h_binance.parquet",  # 8.7y
    ...
}
```

Change `("BTCUSDT", "240")` value к `"data/BTCUSDT_4h.parquet"` (3.3y standard).

- [ ] **Step 4: Move 8.7y file к archive (preserve, не delete)**

```bash
mkdir -p data/_archive
mv data/BTCUSDT_4h_binance.parquet data/_archive/BTCUSDT_4h_binance.parquet
ls -la data/_archive/
```

- [ ] **Step 5: Update existing baseline tests к use 3.3y dates**

Find any test asserting `start_date=date(2017, 8, 17)` OR `end_date=date(2026, 4, 30)` для BTC 4H. Replace с 3.3y window:
- `start_date=date(2023, 1, 1)`
- `end_date=date(2026, 4, 26)`

Specifically check files:
```bash
grep -rn "2017-08-17\|2017, 8, 17" tests/ src/ llm-wiki/ 2>&1 | head
```

For each match: update к 3.3y range. Update PnL assertion if any (BTC 4H 3.3y ≈ +183%, не +819%).

- [ ] **Step 6: Run tests verify PASS**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_baseline_floor.py tests/integration/test_atr_breakout_dashboard_contract.py -v -m integration 2>&1 | tail -15
```

Expected: All PASS. PnL для BTC 4H = +183.10% (3.3y, не +819 from 8.7y).

- [ ] **Step 7: Commit**

```bash
git add src/backtest/atr_breakout_runner.py tests/ data/_archive/
git rm data/BTCUSDT_4h_binance.parquet 2>/dev/null || true  # untracked, skip git rm
git commit -m "feat(s45): uniform 3.3y data — remove BTC 4H 8.7y binance exception"
```

(Note: `BTCUSDT_4h_binance.parquet` was не git-tracked due `.gitignore: data/`. `mv` outside git — just untracked file relocation.)

- [ ] **Step 8: SPRINT_STATE update**

Add S45 section, T1 done, T2 next.

---

## Task 2: Update ADR 0060 baseline (3.3y recompute)

**Files:**
- Modify: `llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-pre-registration.md`

- [ ] **Step 1: Read current ADR 0060**

```bash
.venv/bin/python -c "
from src.backtest.atr_breakout_runner import run_atr_breakout_backtest
from datetime import date
r = run_atr_breakout_backtest(symbol='BTCUSDT', interval='240', start_date=date(2023, 1, 1), end_date=date(2026, 4, 26))
print(f'BTC 4H 3.3y baseline: PnL={r[\"total_pnl_pct\"]:.2f}%, Sharpe={r[\"sharpe\"]:.4f}, n_trades={r[\"n_trades\"]}')
"
```

Expected output: `PnL≈+183.10%, Sharpe≈2.09, n_trades≈28`.

- [ ] **Step 2: Append amendment к ADR 0060**

Append section:

```markdown

## Поправка S45 (2026-05-10): uniform 3.3y baseline

Per S45 operator decision — uniform 3.3y data для всех combos. `BTCUSDT_4h_binance.parquet` (8.7y) removed from `PARQUET_BY_COMBO` registry, archived в `data/_archive/`.

**Recomputed BTC 4H baseline на 3.3y window (2023-01-01 → 2026-04-26):**
- Full-period PnL: **≈+183.10%** (was +819.81% на 8.7y)
- Sharpe: **≈2.09** (was 1.11 на 8.7y)
- n_trades: **≈28** (was 69 на 8.7y)

LOCKED params (atr_period=9, mult=2.5, stop_period=21, stop_mult=1.5) UNCHANGED. Only data window changed.

Original 8.7y baseline preserved в archive для reference. Production discipline = 3.3y uniform.
```

(Use exact computed numbers from Step 1 — fill placeholders с actual output.)

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-pre-registration.md
git commit -m "docs(s45): ADR 0060 amendment — 3.3y uniform baseline (recomputed)"
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): T2 done"
```

---

## Task 3: CrossTrialLog idempotency guard (B1 fix)

**Files:**
- Modify: `src/analytics/cross_trial_log.py:97-119` (`append_trial()`)
- Reset: `data/cross_trial_sharpes.json` к `{"trials": []}`
- Create: `tests/unit/test_cross_trial_log_dedup.py`

- [ ] **Step 1: Failing tests**

Create `tests/unit/test_cross_trial_log_dedup.py`:

```python
"""S45 T3 — CrossTrialLog idempotency guard tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.analytics.cross_trial_log import CrossTrialLog


def test_append_trial_idempotent_on_repeat_call(tmp_path: Path) -> None:
    """S45 B1 — same (sprint, symbol) tuple appended twice → only 1 entry."""
    log = CrossTrialLog(path=tmp_path / "log.json")
    log.append_trial(sprint=44, symbol="BTCUSDT_9_2.5", oos_sharpe=1.22)
    log.append_trial(sprint=44, symbol="BTCUSDT_9_2.5", oos_sharpe=1.22)  # duplicate
    assert log.n_trials() == 1


def test_append_trial_distinct_symbols_kept(tmp_path: Path) -> None:
    """Different (sprint, symbol) tuples appended separately."""
    log = CrossTrialLog(path=tmp_path / "log.json")
    log.append_trial(sprint=44, symbol="BTCUSDT_9_2.5", oos_sharpe=1.22)
    log.append_trial(sprint=44, symbol="ETHUSDT_14_2.5", oos_sharpe=0.85)
    log.append_trial(sprint=45, symbol="BTCUSDT_9_2.5", oos_sharpe=1.30)  # diff sprint
    assert log.n_trials() == 3


def test_append_trial_repeat_with_different_sharpe_overwrites(tmp_path: Path) -> None:
    """Same (sprint, symbol) с new oos_sharpe → updates existing entry, не duplicates."""
    log = CrossTrialLog(path=tmp_path / "log.json")
    log.append_trial(sprint=44, symbol="BTCUSDT_9_2.5", oos_sharpe=1.22)
    log.append_trial(sprint=44, symbol="BTCUSDT_9_2.5", oos_sharpe=1.55)  # update
    assert log.n_trials() == 1
    assert log.get_oos_sharpes() == [1.55]


def test_append_trial_legacy_no_symbol_arg_keeps_default(tmp_path: Path) -> None:
    """Backward compat: legacy callers без symbol kwarg use default 'BTCUSDT'."""
    log = CrossTrialLog(path=tmp_path / "log.json")
    log.append_trial(sprint=13, oos_sharpe=0.5)
    log.append_trial(sprint=13, oos_sharpe=0.5)  # same default symbol — dedup
    assert log.n_trials() == 1
```

- [ ] **Step 2: Run, verify FAIL**

```bash
.venv/bin/pytest tests/unit/test_cross_trial_log_dedup.py -v
```

Expected: 4 FAIL — current `append_trial()` blindly appends.

- [ ] **Step 3: Modify `append_trial()` с idempotency guard**

In `src/analytics/cross_trial_log.py`, find `append_trial()` body (lines ~97-119):

```python
    def append_trial(
        self,
        *,
        sprint: int,
        oos_sharpe: float,
        symbol: str = _DEFAULT_SYMBOL_BACKFILL,
    ) -> None:
        """Atomically append new trial entry. Creates parent dir if missing.

        Args:
            sprint: sprint number
            oos_sharpe: OOS Sharpe ratio
            symbol: trading pair symbol
        """
        trials = self._load()
        trials.append(
            TrialEntry(sprint=int(sprint), symbol=str(symbol), oos_sharpe=float(oos_sharpe))
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps({"trials": trials}, indent=2))
        tmp.rename(self._path)
```

Replace с:

```python
    def append_trial(
        self,
        *,
        sprint: int,
        oos_sharpe: float,
        symbol: str = _DEFAULT_SYMBOL_BACKFILL,
    ) -> None:
        """Atomically append new trial entry. Idempotent on (sprint, symbol) tuple.

        S45 B1 — duplicate (sprint, symbol) calls UPDATE existing entry's oos_sharpe
        instead of appending new row. Prevents log poisoning от dashboard reruns.

        Args:
            sprint: sprint number
            oos_sharpe: OOS Sharpe ratio
            symbol: trading pair symbol
        """
        trials = self._load()
        # S45 B1 idempotency guard — replace existing matching tuple OR append
        new_entry = TrialEntry(
            sprint=int(sprint), symbol=str(symbol), oos_sharpe=float(oos_sharpe),
        )
        existing_idx = next(
            (i for i, t in enumerate(trials)
             if t["sprint"] == new_entry["sprint"] and t["symbol"] == new_entry["symbol"]),
            None,
        )
        if existing_idx is not None:
            trials[existing_idx] = new_entry
        else:
            trials.append(new_entry)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps({"trials": trials}, indent=2))
        tmp.rename(self._path)
```

(Note: `TrialEntry` may be `TypedDict` or `dataclass` — verify `t["sprint"]` vs `t.sprint` access. Read class definition first.)

- [ ] **Step 4: Run tests, verify PASS**

```bash
.venv/bin/pytest tests/unit/test_cross_trial_log_dedup.py -v
.venv/bin/pytest tests/unit/test_cross_trial_log.py -v 2>&1 | tail -10  # existing tests still pass?
```

Expected: 4 new PASS, all existing PASS.

- [ ] **Step 5: Reset cross_trial_sharpes.json**

```bash
.venv/bin/python -c "
import json
from pathlib import Path
p = Path('data/cross_trial_sharpes.json')
p.write_text(json.dumps({'trials': []}, indent=2))
print('Reset cross_trial_sharpes.json к empty (S45 fresh start)')
"
```

- [ ] **Step 6: mypy + commit**

```bash
.venv/bin/mypy --strict src/analytics/cross_trial_log.py
git add src/analytics/cross_trial_log.py tests/unit/test_cross_trial_log_dedup.py data/cross_trial_sharpes.json
git commit -m "feat(s45): CrossTrialLog idempotency guard (B1 fix) + reset log"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T3 done"
```

---

## Task 4: n_trials per-strategy fix (C1)

**Files:**
- Modify: `src/backtest/research_wfa.py` (default `n_trials: int = 1`)
- Modify: `src/backtest/atr_breakout_runner.py::_run_atr_breakout_wfa()` (explicit `n_trials=10`)
- Modify: `src/backtest/volume_breakout_runner.py::_run_volume_breakout_wfa()` (explicit `n_trials=1`)
- Modify: tests

- [ ] **Step 1: Failing tests**

Append к `tests/integration/test_atr_breakout_wfa.py`:

```python
@pytest.mark.integration
def test_atr_breakout_wfa_uses_n_trials_10() -> None:
    """S45 C1 — atr_breakout family = 10 hypotheses (10 combos), n_trials=10 explicit."""
    from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa
    from datetime import date
    # Inspect via call stack — patch run_research_wfa к capture n_trials
    captured = {}
    import src.backtest.research_wfa as wfa_module
    orig = wfa_module.run_research_wfa
    def spy(*args, **kwargs):
        captured["n_trials"] = kwargs.get("n_trials")
        return orig(*args, **kwargs)
    wfa_module.run_research_wfa = spy
    try:
        _run_atr_breakout_wfa(
            symbol="BTCUSDT", interval="240",
            start_date=date(2023, 1, 1), end_date=date(2026, 4, 26),
        )
    finally:
        wfa_module.run_research_wfa = orig
    assert captured["n_trials"] == 10, f"Expected n_trials=10, got {captured['n_trials']}"
```

Append к `tests/integration/test_volume_breakout_wfa.py`:

```python
@pytest.mark.integration
def test_volume_breakout_wfa_uses_n_trials_1() -> None:
    """S45 C1 — volume_breakout = single hypothesis, n_trials=1 explicit."""
    from src.backtest.volume_breakout_runner import _run_volume_breakout_wfa
    from datetime import date
    captured = {}
    import src.backtest.research_wfa as wfa_module
    orig = wfa_module.run_research_wfa
    def spy(*args, **kwargs):
        captured["n_trials"] = kwargs.get("n_trials")
        return orig(*args, **kwargs)
    wfa_module.run_research_wfa = spy
    try:
        _run_volume_breakout_wfa(
            symbol="BTCUSDT", interval="240",
            start_date=date(2023, 1, 1), end_date=date(2026, 4, 26),
        )
    finally:
        wfa_module.run_research_wfa = orig
    assert captured["n_trials"] == 1, f"Expected n_trials=1, got {captured['n_trials']}"
```

Append к `tests/unit/test_research_wfa.py`:

```python
def test_run_research_wfa_default_n_trials_is_1() -> None:
    """S45 C1 — default n_trials=1 (fail-safe). Callers must explicit pass for >1."""
    import inspect
    from src.backtest.research_wfa import run_research_wfa
    sig = inspect.signature(run_research_wfa)
    assert sig.parameters["n_trials"].default == 1, (
        f"Default n_trials must be 1 (fail-safe), got {sig.parameters['n_trials'].default}"
    )
```

- [ ] **Step 2: Verify FAIL**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_wfa.py::test_atr_breakout_wfa_uses_n_trials_10 tests/integration/test_volume_breakout_wfa.py::test_volume_breakout_wfa_uses_n_trials_1 tests/unit/test_research_wfa.py::test_run_research_wfa_default_n_trials_is_1 -v -m integration 2>&1 | tail -15
```

Expected: 3 FAIL.

- [ ] **Step 3: Update default in `research_wfa.py`**

Find:
```python
    n_trials: int = 11,
```

Replace с:
```python
    n_trials: int = 1,  # S45 C1 — fail-safe default. Callers с multi-hypothesis families must explicit.
```

- [ ] **Step 4: Update `_run_atr_breakout_wfa()` к pass n_trials=10**

In `src/backtest/atr_breakout_runner.py::_run_atr_breakout_wfa()`, find `return run_research_wfa(...)` call. Add keyword `n_trials=10` (atr family = 10 hypotheses).

- [ ] **Step 5: Update `_run_volume_breakout_wfa()` к pass n_trials=1**

In `src/backtest/volume_breakout_runner.py::_run_volume_breakout_wfa()`, find `return run_research_wfa(...)` call. Add keyword `n_trials=1` (single hypothesis).

- [ ] **Step 6: Run tests**

```bash
.venv/bin/pytest tests/unit/test_research_wfa.py tests/integration/test_atr_breakout_wfa.py tests/integration/test_volume_breakout_wfa.py -v -m integration 2>&1 | tail -25
```

Expected: All PASS.

- [ ] **Step 7: mypy + commit**

```bash
.venv/bin/mypy --strict src/backtest/
git add src/backtest/research_wfa.py src/backtest/atr_breakout_runner.py src/backtest/volume_breakout_runner.py tests/
git commit -m "feat(s45): n_trials per-strategy fix (C1) — default 1, atr explicit 10, vb explicit 1"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T4 done"
```

---

## Task 5: B2 train slice docs (inline)

**Files:**
- Modify: `src/backtest/research_wfa.py` (docstring + inline comment в WFA loop)

- [ ] **Step 1: Add docstring section**

In `src/backtest/research_wfa.py::run_research_wfa()` docstring, append section:

```python
    """...existing docstring...

    NOTE on train slice (S45 B2 documentation gap fix):
    For LOCKED-params research strategies (atr_breakout, volume_breakout), the
    training slice from WindowSplitter is intentionally NOT passed к backtest_fn.
    Reason: parameters are pre-registered (LOCKED), so no in-sample fitting occurs
    per fold — train slice is vestigial для parameter-frozen strategies.

    The `wfa_params["train_bars"]` returned reflects WHERE test windows are positioned
    (offset from data start), не actual IS isolation. For autoresearch strategies
    that DO fit per fold (future), wrap backtest_fn that uses train_slice.
    """
```

In WFA loop `for fold_idx, (train_slice, test_slice) in enumerate(folds):`, add inline comment:

```python
    for fold_idx, (train_slice, test_slice) in enumerate(folds):
        # S45 B2 — train_slice intentionally NOT passed к backtest_fn for LOCKED-params
        # strategies (no per-fold fitting). See run_research_wfa docstring for rationale.
        if test_slice.empty:
            continue
        fold_result = backtest_fn(test_slice, params, bars_per_year)
        ...
```

- [ ] **Step 2: Verify mypy + tests still pass**

```bash
.venv/bin/mypy --strict src/backtest/research_wfa.py
.venv/bin/pytest tests/unit/test_research_wfa.py -v 2>&1 | tail -8
```

- [ ] **Step 3: Commit**

```bash
git add src/backtest/research_wfa.py
git commit -m "docs(s45): B2 train slice docs — explicit IS-isolation absence для LOCKED params"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T5 done"
```

---

## Task 6: ADR 0014 amendment + WFA recalibration code (low-freq tier) — **OPUS**

**Files:**
- Modify: `llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md` (amendment section)
- Modify: `src/backtest/research_wfa.py` (low-freq tier defaults)
- Modify: `src/backtest/atr_breakout_runner.py::_run_atr_breakout_wfa()` (auto-tier select)
- Modify: `src/backtest/volume_breakout_runner.py::_run_volume_breakout_wfa()` (auto-tier select)

**Why opus:** Anti-snooping discipline — recalibration values must be derived from trade-frequency analysis BEFORE recalibration run. Judgment-heavy decision boundary.

- [ ] **Step 1: Trade-frequency derivation (anti-snooping pre-commit)**

Compute expected trades per OOS window для each (symbol, interval) combo на 3.3y window. Run:

```bash
.venv/bin/python -c "
from src.backtest.atr_breakout_runner import run_atr_breakout_backtest, _BARS_PER_YEAR_BY_INTERVAL
from datetime import date
print(f'{\"combo\":<20} {\"bars/yr\":>8} {\"3.3y_trades\":>11} {\"trades/500bar\":>13} {\"trades/250bar\":>13}')
print('-' * 80)
for sym in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
    for tf in ['15', '60', '240', 'D']:
        if (sym, tf) == ('ETHUSDT', 'D') or (sym, tf) == ('SOLUSDT', 'D'):
            continue
        try:
            r = run_atr_breakout_backtest(
                symbol=sym, interval=tf,
                start_date=date(2023, 1, 1) if not (sym=='BTCUSDT' and tf=='D') else date(2023, 1, 2),
                end_date=date(2026, 4, 26),
            )
            n = r['n_trades']
            bpy = _BARS_PER_YEAR_BY_INTERVAL.get(tf, 2190)
            # Trades per 500-bar OOS window:
            t500 = n * (500 / r['bars_per_year']) / 3.3 * (500 / bpy)  # rough
            t250 = t500 / 2
            print(f'{sym}_{tf:<3}              {bpy:>8} {n:>11} {n/3.3 * 500/bpy:>13.2f} {n/3.3 * 250/bpy:>13.2f}')
        except Exception as e:
            print(f'{sym}_{tf}: ERROR {e}')
"
```

Capture output. This becomes the ADR 0014 amendment justification table.

- [ ] **Step 2: Append amendment к ADR 0014**

Append section к `llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md`:

```markdown

## Поправка S45 (2026-05-10): Low-frequency tier (4H/D)

S44 retrofit раскрыл что ADR 0014 default WFA params (train=2000/test=500/k=5/embargo=20) calibrated для FX 1H — структурно враждебны к 4H/D crypto strategies. Empirical evidence: atr_breakout 4H/D fires 5-20 trades в 500-bar OOS windows vs T5_FLOOR=50 minimum.

### Trade-frequency derivation (anti-snooping pre-commit)

Per S45 ADR 0065 trade-frequency analysis:

| Combo | bars/yr | 3.3y trades | trades/500bar | trades/250bar |
|-------|---------|-------------|---------------|---------------|
| (placeholder — fill from Step 1 output) |

### Tier definition

| Tier | Timeframes | train_bars | test_bars | k_folds | embargo | min_required |
|------|------------|------------|-----------|---------|---------|--------------|
| **High-freq (default ADR 0014)** | 5M, 15M, 1H | 2000 | 500 | 5 | 20 | 4520 |
| **Low-freq (S45 amendment)** | 4H, D | 1500 | 250 | 5 | 20 | 2770 |

**Rationale:** test_bars=250 doubles OOS trade density для low-freq strategies. train_bars=1500 keeps proportional reduction. T5_FLOOR=50 LOCKED — gates not relaxed (Bailey 2014 small-sample T-stat unreliability).

**Anti-snooping clause:** This amendment committed BEFORE S45 recalibration run. Values derived from trade-frequency analysis above, не fitted к pass any specific combo.

**Maximum 1 recalibration iteration:** Если post-S45 WFA still FAIL ВСЕ combos → S46 honest portfolio close per operator decision (ESC-1 (a)). Не further parameter shopping.
```

- [ ] **Step 3: Add tier-select logic в research_wfa.py**

In `src/backtest/research_wfa.py`, add module-level constant + helper:

```python
# S45 — Low-frequency tier params (ADR 0014 amendment)
_LOW_FREQ_INTERVALS: frozenset[str] = frozenset({"240", "D"})
_HIGH_FREQ_DEFAULTS = {"train_bars": 2000, "test_bars": 500, "k_folds": 5, "embargo_bars": 20}
_LOW_FREQ_DEFAULTS = {"train_bars": 1500, "test_bars": 250, "k_folds": 5, "embargo_bars": 20}


def get_wfa_tier_params(interval: str) -> dict[str, int]:
    """S45 — Return WFA params для interval tier per ADR 0014 S45 amendment.

    Low-freq (4H, D): train=1500/test=250/k=5/embargo=20 (min_required=2770)
    High-freq (5M, 15M, 1H): train=2000/test=500/k=5/embargo=20 (min_required=4520)
    """
    return dict(_LOW_FREQ_DEFAULTS) if interval in _LOW_FREQ_INTERVALS else dict(_HIGH_FREQ_DEFAULTS)
```

- [ ] **Step 4: Wire tier-select в `_run_atr_breakout_wfa()`**

In `src/backtest/atr_breakout_runner.py::_run_atr_breakout_wfa()`, modify default args. Replace existing signature defaults с tier-aware defaults.

Find:
```python
def _run_atr_breakout_wfa(
    *,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
    train_bars: int = 2000,
    test_bars: int = 500,
    k_folds: int = 5,
    embargo_bars: int = 20,
) -> dict[str, Any]:
```

Replace с:
```python
def _run_atr_breakout_wfa(
    *,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
    train_bars: int | None = None,
    test_bars: int | None = None,
    k_folds: int | None = None,
    embargo_bars: int | None = None,
) -> dict[str, Any]:
    """S45 — Use tier-aware defaults if не explicit override."""
    from src.backtest.research_wfa import get_wfa_tier_params
    tier = get_wfa_tier_params(interval)
    train_bars = train_bars if train_bars is not None else tier["train_bars"]
    test_bars = test_bars if test_bars is not None else tier["test_bars"]
    k_folds = k_folds if k_folds is not None else tier["k_folds"]
    embargo_bars = embargo_bars if embargo_bars is not None else tier["embargo_bars"]
```

(Continue с existing function body unchanged — params are now tier-resolved.)

- [ ] **Step 5: Same wiring for volume_breakout**

Apply equivalent tier-select logic к `_run_volume_breakout_wfa()`. Volume_breakout = BTCUSDT 4H → uses low-freq tier.

- [ ] **Step 6: Failing tests**

Append к `tests/unit/test_research_wfa.py`:

```python
def test_get_wfa_tier_params_low_freq_4h() -> None:
    """S45 — 4H interval returns low-freq tier params."""
    from src.backtest.research_wfa import get_wfa_tier_params
    p = get_wfa_tier_params("240")
    assert p["train_bars"] == 1500
    assert p["test_bars"] == 250
    assert p["k_folds"] == 5
    assert p["embargo_bars"] == 20


def test_get_wfa_tier_params_low_freq_d() -> None:
    """S45 — D interval returns low-freq tier params."""
    from src.backtest.research_wfa import get_wfa_tier_params
    p = get_wfa_tier_params("D")
    assert p["test_bars"] == 250


def test_get_wfa_tier_params_high_freq_15m() -> None:
    """S45 — 15M returns high-freq default tier."""
    from src.backtest.research_wfa import get_wfa_tier_params
    p = get_wfa_tier_params("15")
    assert p["train_bars"] == 2000
    assert p["test_bars"] == 500


def test_get_wfa_tier_params_high_freq_1h() -> None:
    """S45 — 1H returns high-freq default tier."""
    from src.backtest.research_wfa import get_wfa_tier_params
    p = get_wfa_tier_params("60")
    assert p["test_bars"] == 500
```

- [ ] **Step 7: Run tests + mypy**

```bash
.venv/bin/pytest tests/unit/test_research_wfa.py tests/integration/test_atr_breakout_wfa.py tests/integration/test_volume_breakout_wfa.py -v -m integration 2>&1 | tail -20
.venv/bin/mypy --strict src/backtest/
```

Expected: All PASS, 0 mypy errors.

- [ ] **Step 8: Commit**

```bash
git add src/backtest/ tests/ llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
git commit -m "feat(s45): WFA recalibration — ADR 0014 low-freq tier amendment (4H/D test_bars=250)"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T6 done"
```

---

## Task 7: Re-run 11 combos на recalibrated WFA + capture verdict table

**Files:**
- Modify: `data/cross_trial_sharpes.json` (will populate)

- [ ] **Step 1: Re-run all 11 combos после recalibration**

```bash
.venv/bin/python -c "
from src.dashboard.backtest_runner import BacktestRequest, run_backtest
combos = [
    ('atr_breakout', 'BTCUSDT', '15', '2023-01-01', '2026-04-26'),
    ('atr_breakout', 'BTCUSDT', '60', '2023-01-01', '2026-04-26'),
    ('atr_breakout', 'BTCUSDT', '240', '2023-01-01', '2026-04-26'),
    ('atr_breakout', 'BTCUSDT', 'D', '2023-01-02', '2026-04-26'),
    ('atr_breakout', 'ETHUSDT', '15', '2023-01-01', '2026-04-26'),
    ('atr_breakout', 'ETHUSDT', '60', '2023-01-01', '2026-04-26'),
    ('atr_breakout', 'ETHUSDT', '240', '2023-01-01', '2026-04-26'),
    ('atr_breakout', 'SOLUSDT', '15', '2023-01-01', '2026-04-26'),
    ('atr_breakout', 'SOLUSDT', '60', '2023-01-01', '2026-04-26'),
    ('atr_breakout', 'SOLUSDT', '240', '2023-01-01', '2026-04-26'),
    ('volume_breakout_iter10', 'BTCUSDT', '240', '2023-01-01', '2026-04-26'),
]
print(f'{\"combo\":<35} {\"verdict\":<14} {\"n_oos\":>5} {\"DSR\":<10} {\"MC_p\":<8} {\"failed\":<40}')
print('-' * 120)
for sid, sym, tf, start, end in combos:
    try:
        r = run_backtest(BacktestRequest(strategy_id=sid, symbol=sym, interval=tf, start=start, end=end), force=True)
        v = r.get('verdict', '?')
        dsr = r.get('dsr', None)
        mc = r.get('mc_p_value', None)
        n = r.get('wfa_total_bars', '?')
        fc = ','.join(r.get('failed_criteria', []))[:40]
        dsr_s = f'{dsr:.4f}' if isinstance(dsr, float) else 'NaN'
        mc_s = f'{mc:.4f}' if isinstance(mc, float) else 'NaN'
        n_oos = r.get('n_trades', '?')
        print(f'{sid}_{sym}_{tf:<5}{\" \"*max(0, 35 - len(sid)-len(sym)-len(tf)-2)} {v:<14} {n_oos:>5} {dsr_s:<10} {mc_s:<8} {fc:<40}')
    except Exception as e:
        print(f'{sid}_{sym}_{tf}: ERROR {type(e).__name__}: {e}')

print()
print('=== CROSS_TRIAL_LOG (post-S45) ===')
import json
with open('data/cross_trial_sharpes.json') as f:
    log = json.load(f)
print(f'trials count: {len(log[\"trials\"])}')
for t in log['trials']:
    print(f'  {t}')
"
```

This may take ~3-5 min. Capture full output для T8 ADR 0064 verdict table.

- [ ] **Step 2: Compare с pre-S45 verdicts (S44 baseline)**

Reference S44 verdict table from `llm-wiki/wiki/project/decisions/0064-sprint-44-wfa-retrofit.md`.

Document per-combo delta: verdict change OR failed_criteria change.

- [ ] **Step 3: Honest verdict assessment**

Per ESC-1 (1 attempt only):
- Если хотя бы 1 combo NEW WFA_PASS → S45 success. Document в ADR 0065. Operator decision на next steps.
- Если ВСЕ 11 still WFA_FAIL → ESC-1 trigger: S46 = honest portfolio close (operator excluded Path B).

- [ ] **Step 4: Commit**

```bash
git add data/cross_trial_sharpes.json
git commit -m "feat(s45): 11 combos re-run на recalibrated WFA — actual verdicts captured"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T7 done + verdict table"
```

(Save verdict table output к SPRINT_STATE для T8 reference.)

---

## Task 8: ADR 0065 + sprint-45 + wiki sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0065-sprint-45-wfa-recalibration.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-45-wfa-recalibration.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (counts ADRs 64→65, sprint pages 48→49, header)
- Modify: `llm-wiki/wiki/index.md`
- Append: `llm-wiki/wiki/log.md`

- [ ] **Step 1: ADR 0065**

Write `llm-wiki/wiki/project/decisions/0065-sprint-45-wfa-recalibration.md`:

```markdown
---
title: "0065. Sprint 45 — WFA recalibration + quant discipline + uniform 3.3y data"
type: decision
tags: [adr, sprint-45, wfa-recalibration, dsr, cross-trial-log, data-uniform]
created: 2026-05-10
updated: 2026-05-10
status: accepted
sources:
  - llm-wiki/wiki/project/pre-s45-backlog.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-45-wfa-recalibration.md
---

# 0065. Sprint 45 — WFA recalibration

**Status:** accepted
**Date:** 2026-05-10

## Контекст

S44 raскрыл что ВСЕ 11 research presets WFA_FAIL под ADR 0014 default WFA params. Common root cause: T5 floor (n≥50 trades в pooled OOS) — strategies fire 5-38 trades. Plus reviewer concerns: B1 cross_trial_log dedup blocker, C1 n_trials per-strategy bug, B2 train slice docs gap. Plus operator выявил 8.7y BTC binance file как inconsistent exception.

## Решения

### Decision A — Uniform 3.3y data
Removed `BTCUSDT_4h_binance.parquet` (8.7y exception) from `PARQUET_BY_COMBO` registry. Archived в `data/_archive/`. ADR 0060 baseline recomputed на 3.3y (≈+183%, не +819%).

### Decision B — CrossTrialLog idempotency
`append_trial()` теперь updates existing entry on duplicate (sprint, symbol) tuple OR appends new. Prevents log poisoning от dashboard reruns. Reset log к empty (S44 26 duplicate entries invalidated).

### Decision C — n_trials per-strategy
Default `run_research_wfa(n_trials=1)` (fail-safe). atr_breakout family explicit `n_trials=10` (10 hypotheses). volume_breakout explicit `n_trials=1` (single hypothesis). Correct DSR multi-testing penalty.

### Decision D — WFA recalibration (ADR 0014 amendment)
4H/D low-freq tier: `test_bars=250, train_bars=1500, k_folds=5, embargo_bars=20` (min_required=2770 vs 4520 default). High-freq (5M/15M/1H) unchanged. Anti-snooping: derivation table committed BEFORE recalibration run.

### Decision E — Honest verdict policy
Maximum 1 recalibration iteration (this ADR). Если still FAIL → S46 honest portfolio close. Operator excluded Path B (new strategies).

## Per-combo verdict table (S45 recalibrated, post-T7)

| Combo | n_oos | DSR | MC p | Verdict | Failed criteria |
|-------|-------|-----|------|---------|-----------------|
| (fill from T7 actual results) |

## Последствия

**Pros:**
- Discipline corrections shipped (B1 + C1 + B2 + uniform data).
- WFA recalibration honestly tested (single attempt per anti-snooping discipline).
- Honest verdict basis для S46 decision.

**Cons:**
- Recalibration may not save current portfolio. Operator must decide на S46.
- Sequential-additive ≠ live execution Kelly (per ADR 0012). Backtest = signal-quality discriminator.

**Carry-overs к S46+:**
- UI deferrals (drawdown subchart, per-trade markers, monthly heatmap) — S43 carry.
- S37/S38 long-standing (F8/M1-M4/Item 7/Item 10) — S47.
- Path B (new strategies) — EXCLUDED per operator.

## Verification

- Unit tests: ~975 (+5 new dedup + tier tests).
- Integration tests: ~58 (+3 n_trials assertion + recalibration verdict).
- mypy --strict: 0 errors.
- Canonical counts: 16/30/74/56 unchanged.

## Связанные

- [[../sprints/sprint-45-wfa-recalibration]]
- [[../plans/2026-05-10-sprint-45-wfa-recalibration]]
- [[../pre-s45-backlog]]
- [[0014-walk-forward-train2000-test500]] (amended)
- [[0052-sprint-34-acceptance-criteria-amendment]]
- [[0056-sprint-36-dsr-sigma-sr-amendment]]
- [[0060-sprint-40-atr-breakout-pre-registration]] (amended for 3.3y baseline)
- [[0064-sprint-44-wfa-retrofit]]
```

- [ ] **Step 2: sprint-45 page**

Analogous structure к sprint-44 page. Frontmatter + Цель + Доставленная функциональность (Код / Тесты / Wiki) + FSM/Reason codes UNCHANGED + Tests/качество + Решения + Влияние + Перенесённые задачи + Связанные.

- [ ] **Step 3: current-state.md**

Header: `# Current State (post-S45, 2026-05-10) — WFA recalibration + uniform 3.3y data (tag v0.1.0-alpha.45)`. Counts: ADRs 64→**65**, sprint pages 48→**49**. Sprint history row append.

- [ ] **Step 4: index.md**

Append sprint-45 entry + ADR 0065 entry (analogous к S44 pattern).

- [ ] **Step 5: log.md**

Append S45 sprint-end entry с tasks done + verdict summary + tag.

- [ ] **Step 6: Commit**

```bash
git add llm-wiki/
git commit -m "docs(s45): wiki sync — ADR 0065 + sprint-45 + index/log/current-state"
```

If pre-commit hook complains — fix + new commit.

- [ ] **Step 7: SPRINT_STATE final phase=8-ship**

```bash
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): T8 done, phase=8-ship"
```

---

## PHASE 6 — Domain Reviewers (MANDATORY before merge)

5 reviewers parallel after T8:

| Reviewer | Focus |
|----------|-------|
| `quant-stats-reviewer` | **CRITICAL** — n_trials per-strategy correctness, dedup guard idempotency, WFA tier param justification (anti-snooping), DSR computation post-fix |
| `trading-logic-reviewer` | LOCKED params unchanged, WFA fold split correctness, no look-ahead, sequential-additive preserved |
| `python-reviewer` | PEP 8, type hints, defensive guards, mypy clean |
| `test-engineer` | Dedup test thoroughness, tier param coverage, regression preservation, recalibration run capture |
| `doc-reviewer` | ADR 0014 amendment + ADR 0060 amendment + ADR 0065 frontmatter, wiki-link integrity, count consistency |

NO dashboard/security reviewers (pure backend quant fix).

Aggregate findings. Fix blockers before merge.

---

## PHASE 8 — Ship

```bash
.venv/bin/pytest tests/unit tests/integration -q
.venv/bin/mypy --strict src/
git push -u origin feature/sprint-45-wfa-recalibration
gh pr create --title "Sprint 45: WFA recalibration + quant discipline + uniform 3.3y" --body "..."
# squash-merge after reviewers GREEN
git tag -a v0.1.0-alpha.45 -m "Sprint 45 — WFA recalibration + quant discipline corrections. ADR 0065." <merge-sha>
git push origin v0.1.0-alpha.45
```

---

## Self-Review Verification

**Spec coverage:**
- T1: uniform 3.3y data + remove 8.7y exception → backlog "Decision A"
- T2: ADR 0060 baseline recompute → backlog "Decision A"
- T3: B1 dedup guard → backlog "Decision B"
- T4: C1 n_trials per-strategy → backlog "Decision C"
- T5: B2 train slice docs → backlog item
- T6: ADR 0014 amendment + WFA recalibration code → backlog "Decision D"
- T7: 11 combo re-run + verdict table → backlog "Decision E"
- T8: ADR 0065 + wiki sync

**Type consistency:**
- `n_trials: int = 1` consistent T4 + T6
- `get_wfa_tier_params(interval) -> dict[str, int]` consistent T6 callers
- `_LOW_FREQ_INTERVALS = frozenset({"240", "D"})` consistent T6

**Placeholder scan:** ADR 0065 verdict table (T8) marked "fill from T7 actual results" — required because depends on actual recalibration outcome. Acceptable PHASE 3 placeholder (filled at T8 execution time, not plan write time).

**Plan complete and saved to `llm-wiki/wiki/project/plans/2026-05-10-sprint-45-wfa-recalibration.md`.**
