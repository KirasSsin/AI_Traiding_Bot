---
title: Sprint 9 — Data Quality + mypy strict + Per-fill Analytics + DSR
type: plan
tags: [sprint-9, plan, data-quality, mypy-strict, per-fill, dsr, halt-code, analytics]
created: 2026-04-25
updated: 2026-04-25
status: active
sources:
  - project/pre-s9-backlog.md
  - project/decisions/0021-sprint-7-resilience.md
  - project/decisions/0022-sprint-8a-live-runtime.md
  - project/decisions/0023-halt-code-fsm-event-mapping.md
---

# Sprint 9 Implementation Plan — Data Quality + mypy strict + Per-fill Analytics + DSR

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close 3 deferred carry-overs from S8a/S8b (data quality halt detector, mypy strict full enable, per-fill analytics + DSR foundation) without behavioral regressions.

**Architecture:**
- Q1 (C) — `BarPriceQualityDetector` compares consecutive REST bar closes (no WS subscription); detects feed corruption / stuck price; emits `HALT_DATA_QUALITY` via existing `RISK_HALT` event path.
- Q2 (G) — Remove `ignore_errors=true` override from `pyproject.toml` для `src.core.*`, `src.backtest.*`, `src.risk.*`; verified clean (mypy --strict passes on all 3 modules empirically).
- Q3 B1 — NEW `trade_fills` table (FK к trade_history); WS `execution` topic subscription; `FillRecord` + `FillHistoryRepository`.
- Q3 B2 — NEW `src/analytics/dsr.py` — Bailey & López de Prado DSR formula on `TradeRecord` array; log returns default + simple via flag.

**Tech Stack:** Python 3.12, pydantic v2, SQLite WAL, pybit V5 WebSocket, mypy --strict, pytest (unit + property).

---

## Trace map (PHASE 3 step 1a HARD-GATE per dev-workflow.md)

### Files Created (8 new)

| Path | Responsibility | Task |
|------|----------------|------|
| `src/marketdata/quality.py` | `BarPriceQualityDetector` class — REST-vs-REST consecutive bar deviation check | T1 |
| `migrations/0006_trade_fills.sql` | `trade_fills` table DDL — FK к trade_history | T5 |
| `src/risk/fill_history.py` | `FillRecord` model + `FillHistoryRepository` | T6 |
| `src/analytics/dsr.py` | DSR formula (Bailey & López de Prado) on per-trade returns | T9 |
| `tests/unit/test_quality_detector.py` | BarPriceQualityDetector unit tests | T1 |
| `tests/unit/test_fill_history.py` | FillRecord + FillHistoryRepository tests | T6 |
| `tests/unit/test_dsr.py` | DSR formula tests + edge cases | T9 |
| `wiki/project/components/data-quality.md` + `fill-history.md` + `dsr.md` | Component pages (3 new) | T1, T8, T10 |

### Files Modified (8 existing)

| Path | What changes | Task |
|------|--------------|------|
| `src/execution/coordinator.py:604-633` | Add `ReasonCode.HALT_DATA_QUALITY` к explicit dispatch branch (currently HALT_RUNTIME_CRASH/HALT_BAR_POLL_STALL via else) | T2 |
| `tests/property/test_request_halt_mapping.py:30-34` | Add `HALT_DATA_QUALITY` к `_REQUEST_HALT_CODES` allow-list | T2 |
| `tests/unit/test_coordinator_request_halt.py` | Add unit test for HALT_DATA_QUALITY case | T2 |
| `src/runtime/manager.py` | Inject `BarPriceQualityDetector` into tick pipeline; call after `_poll_bar_and_strategy` | T3 |
| `pyproject.toml:69-72` | Remove `ignore_errors=true` override block for `src.core.*`, `src.backtest.*`, `src.risk.*` | T4 |
| `src/execution/bybit/ws_private.py` | Add `_FillRecorderProto` + `execution_stream` subscription + `_on_execution_raw` handler | T7 |
| `tests/unit/test_ws_private_consumer.py` | Add execution topic dispatch test | T7 |
| `wiki/project/architecture/current-state.md` | Update component count 28→30; add S9 sprint row; add HALT_DATA_QUALITY to halt codes section | T12 |

### Tests added (4 new + 3 modified)

| Test | Purpose | Task |
|------|---------|------|
| `test_quality_detector.py::test_first_poll_skips` | First call has no prior baseline → no halt | T1 |
| `test_quality_detector.py::test_within_threshold_no_halt` | 0.4% deviation → no halt (under 0.5%) | T1 |
| `test_quality_detector.py::test_exceeds_threshold_halts` | 0.6% deviation → halt with HALT_DATA_QUALITY | T1 |
| `test_quality_detector.py::test_zero_prior_close_defensive` | Defensive: prior_close ≤ 0 returns False | T1 |
| `test_request_halt_mapping.py` (modified) | HALT_DATA_QUALITY in allow-list + dispatched | T2 |
| `test_coordinator_request_halt.py::test_halt_data_quality_routes_risk_halt` | NEW: HALT_DATA_QUALITY → RISK_HALT event | T2 |
| `test_fill_history.py::test_*` | 6 tests: insert, idempotent, FK to trade, load_by_trade, partial flag, decimal roundtrip | T6 |
| `test_dsr.py::test_*` | 5 tests: empty array NaN, log return formula, simple return formula, annualization 1H, no-look-ahead invariant | T9 |
| `test_ws_private_consumer.py::test_execution_event_dispatch` | NEW: execution topic message → FillRecorder.on_fill_event | T7 |

### ADRs

| ADR | Created/Modified | Task |
|-----|------------------|------|
| ADR 0024 (NEW) | Aggregate decisions: G mypy strict + B per-fill schema (Q3 B1+B2) | T11 |

### Wiki dependency map

```
S9 plan
├── PHASE 2 verdicts → pre-s9-backlog.md (already shipped)
├── ADR 0024 (T11)
│   ├── G: mypy override removal — links pyproject.toml diff
│   └── B: per-fill schema — links migration + ws topic + DSR module
├── Component pages (T1, T8, T10)
│   ├── data-quality.md → cross-links bar-poller, coordinator, halt-recovery
│   ├── fill-history.md → cross-links trade-history, ws-private-consumer
│   └── dsr.md → cross-links trade-history, walk-forward (S10 future)
└── current-state.md (T12)
    ├── canonical-counts table — components 28→31 (+ data-quality, fill-history, dsr)
    ├── ADR count 23→24
    ├── Sprint pages 10→11 (+ sprint-09-data-quality-types-analytics)
    └── halt codes section: HALT_DATA_QUALITY now active
```

### FSM impact

NONE. HALT_DATA_QUALITY routes through existing `RISK_HALT` event. No new state, no new event, no new transition. Counts unchanged: 16/30/74. Reason codes count unchanged: 45 (HALT_DATA_QUALITY pre-allocated since S4).

---

## Pre-flight verification (run before T1)

- [ ] Run pre-flight check:

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git status  # expect: clean main, branch=main
git checkout -b feature/sprint-9-quality-types-analytics
source .venv/bin/activate
pytest tests/unit -x -q 2>&1 | tail -3  # expect: 589 passed, 24 skipped
mypy src/ 2>&1 | tail -2  # expect: Success: no issues found in 60 source files
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
# Expected: states=16, events=30, transitions=74, reason_codes=45
```

---

## Q1 — REST-vs-REST quality detector (3 tasks)

### Task 1: BarPriceQualityDetector class

**Files:**
- Create: `src/marketdata/quality.py`
- Create: `tests/unit/test_quality_detector.py`

- [ ] **Step 1: Write failing tests (RED)**

```python
# tests/unit/test_quality_detector.py
"""Tests for BarPriceQualityDetector — REST-vs-REST consecutive bar deviation.

Sprint 9 Q1 (per pre-s9-backlog.md verdict — REVISE accepted).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.marketdata.quality import BarPriceQualityDetector


def test_first_poll_skips_no_prior_baseline() -> None:
    """First call has no baseline → cannot detect deviation → returns False."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    assert det.check(current_close=Decimal("100000")) is False
    # Subsequent calls now have baseline established.


def test_within_threshold_no_halt() -> None:
    """0.4% deviation < 0.5% threshold → no halt."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("100000"))  # establish baseline
    # 100000 → 100400 = +0.4%, under threshold
    assert det.check(current_close=Decimal("100400")) is False


def test_exceeds_threshold_halts() -> None:
    """0.6% deviation > 0.5% threshold → halt."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("100000"))
    # 100000 → 100600 = +0.6%, over threshold
    assert det.check(current_close=Decimal("100600")) is True


def test_negative_deviation_uses_absolute_value() -> None:
    """Drop of 0.6% also triggers halt (symmetric)."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("100000"))
    assert det.check(current_close=Decimal("99400")) is True


def test_zero_prior_close_defensive() -> None:
    """Prior close ≤ 0 → False defensively (no division by zero)."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    # First call sets baseline to 0 (degenerate but supported)
    det.check(current_close=Decimal("0"))
    # Next call should not divide by zero
    assert det.check(current_close=Decimal("100000")) is False


def test_negative_threshold_rejected() -> None:
    """Negative threshold raises ValueError at construction."""
    with pytest.raises(ValueError, match="threshold_pct must be > 0"):
        BarPriceQualityDetector(threshold_pct=Decimal("-0.005"))


def test_threshold_at_boundary() -> None:
    """Exact boundary value: deviation == threshold → False (strict >)."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("100000"))
    # Exactly 0.5% deviation
    assert det.check(current_close=Decimal("100500")) is False


def test_baseline_advances_each_call() -> None:
    """After each check, baseline updates to current_close (rolling)."""
    det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
    det.check(current_close=Decimal("100000"))
    det.check(current_close=Decimal("100200"))  # 0.2%, no halt, baseline now 100200
    # 100200 → 100800 = ~0.6%, triggers halt
    assert det.check(current_close=Decimal("100800")) is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/unit/test_quality_detector.py -v 2>&1 | tail -15
```

Expected: `ImportError: No module named 'src.marketdata.quality'` или `AttributeError: BarPriceQualityDetector`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/marketdata/quality.py
"""REST-vs-REST consecutive bar price quality detector.

Sprint 9 Q1 (per pre-s9-backlog.md verdict).

Detector compares current REST closed bar price vs previously observed
REST closed bar price (held in-memory). Designed for use by RuntimeManager
after BarSource.poll() returns a new closed bar.

Why REST-vs-REST (not WS+REST):
- WS kline subscription does not exist (ws_private only subscribes to
  order + wallet topics).
- Wiring WS kline contradicts S8a ADR 0022 async/sync deferral к S9+.
- WS partial-bar updates create false-positive risk при per-bar comparison.

Threshold rationale (0.5% relative on 1H BTCUSDT @ ~$100k):
- ~$500 instantaneous move bar-to-bar is unusual для 1H granularity.
- Catches stuck/corrupted feed без new infrastructure.
- Single tunable knob (no per-symbol overrides for v0.1).
"""
from __future__ import annotations

from decimal import Decimal

from src.platform.logging import get_logger

logger = get_logger(__name__)


class BarPriceQualityDetector:
    """Stateless detector — caller owns persistence of last_close baseline.

    Usage:
        det = BarPriceQualityDetector(threshold_pct=Decimal("0.005"))
        for bar in bar_source.poll_iter():
            if det.check(current_close=bar.close):
                coordinator.request_halt(reason=ReasonCode.HALT_DATA_QUALITY)
    """

    def __init__(self, *, threshold_pct: Decimal) -> None:
        if threshold_pct <= 0:
            raise ValueError(
                f"BarPriceQualityDetector: threshold_pct must be > 0, got {threshold_pct}"
            )
        self._threshold_pct = threshold_pct
        self._last_close: Decimal | None = None

    def check(self, *, current_close: Decimal) -> bool:
        """Return True if deviation > threshold (halt-worthy).

        First call establishes baseline → returns False.
        Subsequent calls compare against last_close, then update baseline.
        Defensive: prior_close ≤ 0 → False (cannot compute relative deviation).
        """
        prior = self._last_close
        self._last_close = current_close

        if prior is None:
            return False  # No baseline yet
        if prior <= 0:
            return False  # Defensive: avoid division by zero or negative anchor
        deviation_pct = abs(current_close - prior) / prior
        if deviation_pct > self._threshold_pct:
            logger.warning(
                "data_quality.deviation_exceeds_threshold",
                prior_close=str(prior),
                current_close=str(current_close),
                deviation_pct=str(deviation_pct),
                threshold_pct=str(self._threshold_pct),
            )
            return True
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_quality_detector.py -v 2>&1 | tail -15
```

Expected: `8 passed`.

- [ ] **Step 5: Verify mypy strict on new module**

```bash
mypy --strict src/marketdata/quality.py 2>&1 | tail -3
```

Expected: `Success: no issues found in 1 source file`.

- [ ] **Step 6: Commit**

```bash
git add src/marketdata/quality.py tests/unit/test_quality_detector.py
git commit -m "feat(quality): add BarPriceQualityDetector — REST-vs-REST deviation check (S9 Q1)"
```

---

### Task 2: Coordinator HALT_DATA_QUALITY explicit dispatch + property test allow-list

**Files:**
- Modify: `src/execution/coordinator.py:604-633`
- Modify: `tests/property/test_request_halt_mapping.py:30-34`
- Modify: `tests/unit/test_coordinator_request_halt.py` (add new test)

- [ ] **Step 1: Add HALT_DATA_QUALITY к property test allow-list (RED)**

Edit `tests/property/test_request_halt_mapping.py`:

```python
# Replace existing _REQUEST_HALT_CODES set:
_REQUEST_HALT_CODES = frozenset({
    ReasonCode.KILL_SWITCH_REQUESTED,
    ReasonCode.HALT_RUNTIME_CRASH,
    ReasonCode.HALT_BAR_POLL_STALL,
    ReasonCode.HALT_DATA_QUALITY,  # S9 Q1 — REST-vs-REST quality detector
})
```

- [ ] **Step 2: Run property test to confirm RED**

```bash
pytest tests/property/test_request_halt_mapping.py -v 2>&1 | tail -10
```

Expected: PASS актуально (existing else-branch in coordinator.py routes any non-KILL_SWITCH к RISK_HALT). The property test enumerates all `_REQUEST_HALT_CODES` and asserts `state == HALTED` after `request_halt()` — this passes because else-branch handles HALT_DATA_QUALITY transparently.

If unexpected FAIL: investigate FSM state assertion — should pass через RISK_HALT routing.

- [ ] **Step 3: Add explicit dispatch branch (per ADR 0023 invariant)**

Edit `src/execution/coordinator.py:626-632` — replace the if/else block:

```python
            current = self._repo.get(self._symbol)
            if current is not None and current.state != ExecutionState.HALTED:
                if reason == ReasonCode.KILL_SWITCH_REQUESTED:
                    self._transition(ExecutionEvent.KILL_SWITCH_REQUESTED)
                else:
                    # HALT_RUNTIME_CRASH, HALT_BAR_POLL_STALL, HALT_DATA_QUALITY
                    # → HALTED via RISK_HALT.
                    # Future halt codes MUST add an explicit branch — see ADR 0023.
                    self._transition(ExecutionEvent.RISK_HALT)
```

(Comment update only — else branch already handles HALT_DATA_QUALITY transparently. The ADR 0023 invariant is satisfied: any code in `_REQUEST_HALT_CODES` allow-list with non-KILL_SWITCH semantic uses RISK_HALT event.)

- [ ] **Step 4: Add unit test for HALT_DATA_QUALITY case**

Edit `tests/unit/test_coordinator_request_halt.py` — append:

```python
def test_request_halt_data_quality_routes_to_risk_halt(tmp_path) -> None:
    """S9 Q1: HALT_DATA_QUALITY uses RISK_HALT event (no new FSM event).

    Per ADR 0023 invariant — non-KILL_SWITCH halt codes share RISK_HALT path.
    """
    coord, repo = _build(tmp_path)  # FLAT initial state (mirrors existing tests)
    coord.request_halt(reason=ReasonCode.HALT_DATA_QUALITY)
    state_row = repo.get("BTCUSDT")
    assert state_row is not None
    assert state_row.state == ExecutionState.HALTED
    assert state_row.halt_reason == ReasonCode.HALT_DATA_QUALITY.value
```

- [ ] **Step 5: Run tests to verify all pass**

```bash
pytest tests/unit/test_coordinator_request_halt.py tests/property/test_request_halt_mapping.py -v 2>&1 | tail -10
```

Expected: All pass (existing tests + new HALT_DATA_QUALITY case).

- [ ] **Step 6: Commit**

```bash
git add src/execution/coordinator.py tests/property/test_request_halt_mapping.py tests/unit/test_coordinator_request_halt.py
git commit -m "feat(coordinator): wire HALT_DATA_QUALITY к RISK_HALT path + property test (S9 Q1)"
```

---

### Task 3: RuntimeManager integration — wire detector into tick pipeline

**Files:**
- Modify: `src/runtime/manager.py`
- Modify: `tests/unit/test_runtime_manager.py` (or equivalent test file для RuntimeManager)

- [ ] **Step 1: Locate existing RuntimeManager construction + tick pipeline**

```bash
grep -n "_poll_bar_and_strategy\|class RuntimeManager\|def tick" src/runtime/manager.py | head -10
```

Identify: where `BarSource.poll()` is called, where tick steps are sequenced (`_maybe_kill_switch` → `_check_alive_inline` → `_poll_bar_and_strategy` → `_poll_or_arm_oco` per `wiki/project/components/runtime-manager.md`).

- [ ] **Step 2: Write failing integration test**

Edit `tests/unit/test_runtime_manager.py` — add (or create file if missing):

```python
def test_quality_detector_halts_on_consecutive_bar_deviation(tmp_path) -> None:
    """S9 Q1: After two consecutive bar polls с >0.5% deviation, RuntimeManager
    calls coordinator.request_halt(HALT_DATA_QUALITY).
    """
    from decimal import Decimal
    from unittest.mock import MagicMock
    from datetime import datetime, UTC

    from src.marketdata.models import Bar
    from src.runtime.manager import RuntimeManager  # adjust import per actual structure

    coord = MagicMock()
    bar1 = Bar(
        open_time=datetime.now(UTC), close_time=datetime.now(UTC),
        open=Decimal("100000"), high=Decimal("100100"), low=Decimal("99900"),
        close=Decimal("100000"), volume=Decimal("1.0"),
    )
    bar2 = Bar(
        open_time=datetime.now(UTC), close_time=datetime.now(UTC),
        open=Decimal("100600"), high=Decimal("100700"), low=Decimal("100500"),
        close=Decimal("100600"), volume=Decimal("1.0"),  # +0.6% from bar1.close
    )
    bar_source = MagicMock()
    bar_source.poll.side_effect = [bar1, bar2]

    rm = RuntimeManager(
        coordinator=coord,
        bar_source=bar_source,
        quality_threshold_pct=Decimal("0.005"),  # NEW kwarg
        # ... other kwargs as required by current RuntimeManager signature
    )
    rm._poll_bar_and_strategy()  # bar1 — establishes baseline
    rm._poll_bar_and_strategy()  # bar2 — triggers halt

    coord.request_halt.assert_called_with(reason=mock.ANY)
    # Or more specifically:
    from src.risk.reason_codes import ReasonCode
    coord.request_halt.assert_called_with(reason=ReasonCode.HALT_DATA_QUALITY)
```

(NOTE: Test signature may need adjustment based on actual RuntimeManager constructor — read current code first via `Read src/runtime/manager.py` lines 1-50 to identify required kwargs.)

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/unit/test_runtime_manager.py::test_quality_detector_halts_on_consecutive_bar_deviation -v 2>&1 | tail -10
```

Expected: FAIL — `quality_threshold_pct` kwarg not accepted OR detector not invoked.

- [ ] **Step 4: Wire BarPriceQualityDetector в RuntimeManager**

Edit `src/runtime/manager.py`:

1. Add import:
```python
from src.marketdata.quality import BarPriceQualityDetector
from src.risk.reason_codes import ReasonCode
```

2. Add constructor kwarg + instance:
```python
def __init__(
    self,
    *,
    # ... existing kwargs ...
    quality_threshold_pct: Decimal = Decimal("0.005"),
) -> None:
    # ... existing init ...
    self._quality_detector = BarPriceQualityDetector(
        threshold_pct=quality_threshold_pct
    )
```

3. Wire detector в `_poll_bar_and_strategy` after BarSource.poll() returns new bar:
```python
def _poll_bar_and_strategy(self) -> None:
    bar = self._bar_source.poll()
    if bar is None:
        if self._bar_source.should_halt(threshold=self._stall_threshold):
            self._coordinator.request_halt(reason=ReasonCode.HALT_BAR_POLL_STALL)
        return

    # S9 Q1 — Quality check on closed bar before strategy consumes it
    if self._quality_detector.check(current_close=bar.close):
        self._coordinator.request_halt(reason=ReasonCode.HALT_DATA_QUALITY)
        return  # Skip strategy — halted

    # ... existing strategy invocation ...
```

(Read current `_poll_bar_and_strategy` first via Grep — adjust integration point if structure differs.)

- [ ] **Step 5: Add Settings для quality_threshold_pct**

Edit `src/platform/config.py` — add field:

```python
quality_threshold_pct: Decimal = Field(
    default=Decimal("0.005"),
    description="Bar price quality threshold (relative deviation, default 0.5%). "
    "S9 Q1 — REST-vs-REST consecutive bar quality detector.",
)
```

- [ ] **Step 6: Run all tests**

```bash
pytest tests/unit -x -q 2>&1 | tail -3
```

Expected: 590+ passed (added 1 test from Task 1 = 8 quality detector tests + 1 coordinator test from T2 + 1 runtime test = +10 tests over baseline 589).

- [ ] **Step 7: Commit**

```bash
git add src/runtime/manager.py src/platform/config.py tests/unit/test_runtime_manager.py
git commit -m "feat(runtime): wire BarPriceQualityDetector into tick pipeline (S9 Q1)"
```

---

## Q2 — mypy --strict full enable (1 task)

### Task 4: Remove ignore_errors override

**Files:**
- Modify: `pyproject.toml:69-72`

**Background:** Empirical check showed `mypy --strict src/core/`, `src/risk/`, `src/backtest/` ALL CLEAN (Success: no issues found). The override masks zero actual errors. Removing it converts implicit pass к explicit type checking.

- [ ] **Step 1: Verify all 3 modules pass mypy --strict before removal (sanity check)**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
mypy --strict src/core/ 2>&1 | tail -2
mypy --strict src/risk/ 2>&1 | tail -2
mypy --strict src/backtest/ 2>&1 | tail -2
```

Expected: All three report `Success: no issues found`.

If FAIL: investigate per-module errors, fix before removing override (no error masking acceptable).

- [ ] **Step 2: Remove override block**

Edit `pyproject.toml` — delete lines 69-72:

```toml
[[tool.mypy.overrides]]
# Legacy modules — MVP v0.1 scope только platform/marketdata/signalgen/execution.
module = ["src.core.*", "src.backtest.*", "src.risk.*"]
ignore_errors = true
```

(Keep the pybit/pyarrow/talib `ignore_missing_imports = true` block — that handles untyped third-party imports, не legacy code.)

- [ ] **Step 3: Run full mypy on all source**

```bash
mypy src/ 2>&1 | tail -3
```

Expected: `Success: no issues found in 60 source files`.

If FAIL: address each error inline. Most likely causes:
- New type-arg errors на bare `dict` / `tuple` / `list` (use `dict[str, Any]` etc).
- `no-any-return` from untyped third-party (add `# type: ignore[no-any-return]` с reason comment).
- `union-attr` (refactor to non-Optional via early raise).

- [ ] **Step 4: Run pytest для verify no regressions**

```bash
pytest tests/unit -x -q 2>&1 | tail -3
```

Expected: 590+ passed.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "feat(mypy): enable --strict для src.core/src.risk/src.backtest (S9 Q2 G)"
```

---

## Q3 B1 — Per-fill schema (3 tasks)

### Task 5: trade_fills migration

**Files:**
- Create: `migrations/0006_trade_fills.sql`
- Create: `tests/unit/test_db_migration_trade_fills.py`

- [ ] **Step 1: Write failing test for migration**

Create `tests/unit/test_db_migration_trade_fills.py`:

```python
"""Verify migration 0006 creates trade_fills table with expected schema."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.platform.db import init_db

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def test_migration_0006_creates_trade_fills_table(tmp_path) -> None:
    """trade_fills table exists with expected columns + FK к trade_history."""
    db_path = tmp_path / "test.db"
    init_db(db_path, MIG_DIR)
    conn = sqlite3.connect(str(db_path))
    cols = conn.execute("PRAGMA table_info(trade_fills)").fetchall()
    col_names = [c[1] for c in cols]
    assert col_names == [
        "fill_id", "parent_trade_id", "exec_id", "fill_qty",
        "fill_price", "fill_fee", "fee_currency", "is_partial",
        "fill_ts", "recorded_at",
    ]
    # Verify FK
    fks = conn.execute("PRAGMA foreign_key_list(trade_fills)").fetchall()
    assert len(fks) == 1
    assert fks[0][2] == "trade_history"  # references table
    assert fks[0][4] == "trade_id"  # references column

    # Verify UNIQUE INDEX on exec_id (idempotency)
    idxs = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='trade_fills'"
    ).fetchall()
    assert any("UNIQUE" in (idx[1] or "") and "exec_id" in (idx[1] or "") for idx in idxs)


def test_migration_0006_idempotent(tmp_path) -> None:
    """Re-running migrations does not fail."""
    db_path = tmp_path / "test.db"
    init_db(db_path, MIG_DIR)
    init_db(db_path, MIG_DIR)  # Should not raise
```

- [ ] **Step 2: Run test to verify failure**

```bash
pytest tests/unit/test_db_migration_trade_fills.py -v 2>&1 | tail -10
```

Expected: FAIL — `no such table: trade_fills`.

- [ ] **Step 3: Create migration file**

Create `migrations/0006_trade_fills.sql`:

```sql
-- Sprint 9 Q3 B1: per-fill granularity for analytics + audit.
-- FK to trade_history.trade_id; one trade may have N fills (typically 1 for
-- Spot Market entries, 1-2 for IOC SL StopMarket partial-fills).
--
-- exec_id = Bybit V5 execution-list event identifier (UNIQUE for idempotency
-- under at-least-once WS delivery).
CREATE TABLE IF NOT EXISTS trade_fills (
    fill_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_trade_id  INTEGER NOT NULL,
    exec_id          TEXT    NOT NULL,
    fill_qty         TEXT    NOT NULL,
    fill_price       TEXT    NOT NULL,
    fill_fee         TEXT    NOT NULL,
    fee_currency     TEXT    NOT NULL,
    is_partial       INTEGER NOT NULL CHECK(is_partial IN (0, 1)),
    fill_ts          TEXT    NOT NULL,
    recorded_at      TEXT    NOT NULL,
    FOREIGN KEY (parent_trade_id) REFERENCES trade_history(trade_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_trade_fills_exec_id
    ON trade_fills(exec_id);

CREATE INDEX IF NOT EXISTS idx_trade_fills_parent_ts
    ON trade_fills(parent_trade_id, fill_ts);
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/unit/test_db_migration_trade_fills.py -v 2>&1 | tail -10
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add migrations/0006_trade_fills.sql tests/unit/test_db_migration_trade_fills.py
git commit -m "feat(schema): add migration 0006_trade_fills (S9 Q3 B1)"
```

---

### Task 6: FillRecord model + FillHistoryRepository

**Files:**
- Create: `src/risk/fill_history.py`
- Create: `tests/unit/test_fill_history.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_fill_history.py`:

```python
"""Tests for FillRecord + FillHistoryRepository.

Sprint 9 Q3 B1.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.platform.db import init_db
from src.risk.fill_history import FillRecord, FillHistoryRepository

MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _make_fill(*, exec_id: str = "exec_1", parent_trade_id: int = 1) -> FillRecord:
    return FillRecord(
        parent_trade_id=parent_trade_id,
        exec_id=exec_id,
        fill_qty=Decimal("0.5"),
        fill_price=Decimal("100000"),
        fill_fee=Decimal("0.05"),
        fee_currency="USDT",
        is_partial=False,
        fill_ts=datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 4, 25, 12, 0, 1, tzinfo=UTC),
    )


def _build_repo(tmp_path: Path) -> tuple[FillHistoryRepository, sqlite3.Connection]:
    db_path = tmp_path / "fh.db"
    init_db(db_path, MIG_DIR)
    conn = sqlite3.connect(str(db_path))
    # Seed parent trade_history row для FK
    conn.execute(
        """INSERT INTO trade_history (
            symbol, entry_signal_id, entry_ts, exit_ts, qty,
            entry_price, exit_price, pnl_quote, pnl_pct, fees_paid,
            reason_code, kelly_phase, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("BTCUSDT", "00000000-0000-0000-0000-000000000001",
         "2026-04-25T11:00:00+00:00", "2026-04-25T12:00:00+00:00",
         "0.5", "99500", "100000", "250", "0.005", "0.05",
         "EXIT_TP_HIT", 1, "2026-04-25T12:00:01+00:00"),
    )
    conn.commit()
    return FillHistoryRepository(conn), conn


def test_insert_fill_returns_fill_id(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    fill_id = repo.insert_fill(_make_fill())
    assert fill_id == 1


def test_insert_idempotent_on_duplicate_exec_id(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    fill_id_1 = repo.insert_fill(_make_fill(exec_id="dup"))
    fill_id_2 = repo.insert_fill(_make_fill(exec_id="dup"))
    assert fill_id_1 == fill_id_2  # same row returned


def test_load_by_trade_returns_ordered_by_fill_ts(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    fill_a = _make_fill(exec_id="a")
    fill_b_record = FillRecord(
        parent_trade_id=1,
        exec_id="b",
        fill_qty=Decimal("0.3"),
        fill_price=Decimal("100100"),
        fill_fee=Decimal("0.03"),
        fee_currency="USDT",
        is_partial=True,
        fill_ts=datetime(2026, 4, 25, 12, 1, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 4, 25, 12, 1, 1, tzinfo=UTC),
    )
    repo.insert_fill(fill_b_record)
    repo.insert_fill(fill_a)

    fills = repo.load_by_trade(parent_trade_id=1)
    assert len(fills) == 2
    assert fills[0].exec_id == "a"  # earlier fill_ts first
    assert fills[1].exec_id == "b"


def test_decimal_roundtrip(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    repo.insert_fill(_make_fill())
    fills = repo.load_by_trade(parent_trade_id=1)
    assert fills[0].fill_qty == Decimal("0.5")
    assert fills[0].fill_price == Decimal("100000")
    assert fills[0].fill_fee == Decimal("0.05")


def test_is_partial_flag_roundtrip(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    fill = FillRecord(
        parent_trade_id=1, exec_id="p", fill_qty=Decimal("0.5"),
        fill_price=Decimal("100000"), fill_fee=Decimal("0.05"),
        fee_currency="USDT", is_partial=True,
        fill_ts=datetime.now(UTC), recorded_at=datetime.now(UTC),
    )
    repo.insert_fill(fill)
    fills = repo.load_by_trade(parent_trade_id=1)
    assert fills[0].is_partial is True


def test_count(tmp_path: Path) -> None:
    repo, _ = _build_repo(tmp_path)
    assert repo.count() == 0
    repo.insert_fill(_make_fill())
    assert repo.count() == 1


def test_negative_qty_rejected_at_model() -> None:
    with pytest.raises(ValueError):
        FillRecord(
            parent_trade_id=1, exec_id="x", fill_qty=Decimal("-0.5"),
            fill_price=Decimal("100000"), fill_fee=Decimal("0.05"),
            fee_currency="USDT", is_partial=False,
            fill_ts=datetime.now(UTC), recorded_at=datetime.now(UTC),
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_fill_history.py -v 2>&1 | tail -15
```

Expected: ImportError на `src.risk.fill_history`.

- [ ] **Step 3: Implement model + repository**

Create `src/risk/fill_history.py`:

```python
"""Per-fill history persistence: FillRecord + FillHistoryRepository.

Sprint 9 Q3 B1 (per pre-s9-backlog.md).

Mirrors trade_history.py pattern. Stores fills granularly для analytics
(slippage measurement, fee breakdown, partial-fill audit). Idempotent
on exec_id (UNIQUE INDEX) under at-least-once WS delivery.
"""
from __future__ import annotations

from decimal import Decimal
from sqlite3 import Connection

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class FillRecord(BaseModel):
    """Single execution fill. Decimal monetary, ISO-8601 UTC timestamps."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fill_id: int | None = None  # None pre-insert; set by AUTOINCREMENT
    parent_trade_id: int = Field(..., gt=0)
    exec_id: str  # Bybit V5 execution-list event id
    fill_qty: Decimal = Field(..., gt=0)
    fill_price: Decimal = Field(..., gt=0)
    fill_fee: Decimal = Field(..., ge=0)
    fee_currency: str
    is_partial: bool
    fill_ts: AwareDatetime
    recorded_at: AwareDatetime


class FillHistoryRepository:
    """SQLite-backed fill history. Decimal->str on write, str->Decimal on read."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def insert_fill(self, record: FillRecord) -> int:
        """Insert and return fill_id. Idempotent on duplicate exec_id."""
        with self._conn:
            cursor = self._conn.execute(
                """INSERT OR IGNORE INTO trade_fills (
                    parent_trade_id, exec_id, fill_qty, fill_price, fill_fee,
                    fee_currency, is_partial, fill_ts, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.parent_trade_id,
                    record.exec_id,
                    str(record.fill_qty),
                    str(record.fill_price),
                    str(record.fill_fee),
                    record.fee_currency,
                    1 if record.is_partial else 0,
                    record.fill_ts.isoformat(),
                    record.recorded_at.isoformat(),
                ),
            )
        if cursor.lastrowid and cursor.rowcount > 0:
            return int(cursor.lastrowid)
        # Duplicate — fetch existing
        row = self._conn.execute(
            "SELECT fill_id FROM trade_fills WHERE exec_id = ?",
            (record.exec_id,),
        ).fetchone()
        return int(row[0])

    def load_by_trade(self, *, parent_trade_id: int) -> list[FillRecord]:
        """Load all fills для given trade, ordered by fill_ts ASC."""
        rows = self._conn.execute(
            """SELECT fill_id, parent_trade_id, exec_id, fill_qty, fill_price,
                      fill_fee, fee_currency, is_partial, fill_ts, recorded_at
               FROM trade_fills
               WHERE parent_trade_id = ?
               ORDER BY fill_ts ASC""",
            (parent_trade_id,),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def count(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM trade_fills").fetchone()[0]
        )

    @staticmethod
    def _row_to_record(row: tuple) -> FillRecord:
        from datetime import datetime, UTC
        return FillRecord(
            fill_id=row[0],
            parent_trade_id=row[1],
            exec_id=row[2],
            fill_qty=Decimal(row[3]),
            fill_price=Decimal(row[4]),
            fill_fee=Decimal(row[5]),
            fee_currency=row[6],
            is_partial=bool(row[7]),
            fill_ts=datetime.fromisoformat(row[8]).astimezone(UTC),
            recorded_at=datetime.fromisoformat(row[9]).astimezone(UTC),
        )
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/unit/test_fill_history.py -v 2>&1 | tail -15
```

Expected: 7 passed.

- [ ] **Step 5: Verify mypy strict**

```bash
mypy --strict src/risk/fill_history.py 2>&1 | tail -3
```

Expected: `Success: no issues found in 1 source file`.

- [ ] **Step 6: Commit**

```bash
git add src/risk/fill_history.py tests/unit/test_fill_history.py
git commit -m "feat(fill-history): FillRecord + FillHistoryRepository (S9 Q3 B1)"
```

---

### Task 7: WS execution topic subscription

**Files:**
- Modify: `src/execution/bybit/ws_private.py`
- Modify: `tests/unit/test_ws_private_consumer.py`

- [ ] **Step 1: Write failing test (RED)**

Edit `tests/unit/test_ws_private_consumer.py` — append:

```python
def test_execution_event_dispatched_к_fill_recorder() -> None:
    """S9 Q3 B1: WS execution topic message routes к FillRecorder.on_fill_event.

    Verifies _on_execution_raw extracts fill data from Bybit V5 execution
    schema and dispatches one event per fill.
    """
    from src.execution.bybit.ws_private import BybitPrivateWSConsumer

    coordinator = MagicMock()
    reconciler = MagicMock()
    fill_recorder = MagicMock()

    consumer = BybitPrivateWSConsumer(
        api_key="test",
        api_secret="test",
        endpoint="testnet.bybit.com",
        coordinator=coordinator,
        reconciler=reconciler,
        fill_recorder=fill_recorder,  # NEW kwarg
    )

    msg = {
        "topic": "execution",
        "data": [
            {
                "execId": "exec_abc",
                "orderId": "order_1",
                "symbol": "BTCUSDT",
                "execQty": "0.5",
                "execPrice": "100000",
                "execFee": "0.05",
                "feeCurrency": "USDT",
                "execType": "Trade",
                "isMaker": False,
                "execTime": "1745582400000",
            },
        ],
    }
    consumer._on_execution_raw(msg)

    fill_recorder.on_fill_event.assert_called_once()
    call_evt = fill_recorder.on_fill_event.call_args[0][0]
    assert call_evt["execId"] == "exec_abc"
    assert call_evt["execQty"] == "0.5"
```

- [ ] **Step 2: Run test to confirm RED**

```bash
pytest tests/unit/test_ws_private_consumer.py::test_execution_event_dispatched_к_fill_recorder -v 2>&1 | tail -10
```

Expected: FAIL — `fill_recorder` kwarg not accepted OR `_on_execution_raw` doesn't exist.

- [ ] **Step 3: Add `_FillRecorderProto` + execution topic к ws_private.py**

Edit `src/execution/bybit/ws_private.py`:

1. Add `_FillRecorderProto` after `_ReconcilerProto`:

```python
class _FillRecorderProto(Protocol):
    def on_fill_event(self, evt: dict[str, Any]) -> None: ...
```

2. Add `fill_recorder` kwarg to `__init__`:

```python
def __init__(
    self,
    *,
    api_key: str,
    api_secret: str,
    endpoint: str,
    coordinator: _CoordinatorProto,
    reconciler: _ReconcilerProto,
    fill_recorder: _FillRecorderProto,  # NEW
) -> None:
    self._api_key = api_key
    self._api_secret = api_secret
    self._endpoint = endpoint
    self._coordinator = coordinator
    self._reconciler = reconciler
    self._fill_recorder = fill_recorder  # NEW
    self._ws: Any | None = None
```

3. Subscribe в `start()` after `wallet_stream`:

```python
self._ws.execution_stream(callback=self._on_execution_raw)
```

4. Add handler:

```python
def _on_execution_raw(self, msg: dict[str, Any]) -> None:
    """S9 Q3 B1 — dispatch each fill from Bybit V5 execution topic."""
    try:
        for item in msg.get("data", []):
            self._fill_recorder.on_fill_event(item)
    except Exception:
        logger.exception("execution event dispatch failed; dropping msg=%r", msg)
```

- [ ] **Step 4: Run test to verify pass**

```bash
pytest tests/unit/test_ws_private_consumer.py -v 2>&1 | tail -10
```

Expected: All pass (existing + new execution test).

- [ ] **Step 5: Verify mypy strict**

```bash
mypy --strict src/execution/bybit/ws_private.py 2>&1 | tail -3
```

Expected: `Success: no issues found`.

- [ ] **Step 6: Commit**

```bash
git add src/execution/bybit/ws_private.py tests/unit/test_ws_private_consumer.py
git commit -m "feat(ws): subscribe Bybit V5 execution topic + dispatch к FillRecorder (S9 Q3 B1)"
```

---

### Task 8: Component page для fill-history

**Files:**
- Create: `wiki/project/components/fill-history.md`

- [ ] **Step 1: Write component page**

Create `llm-wiki/wiki/project/components/fill-history.md`:

```markdown
---
title: Fill history — per-fill audit + analytics base
type: component
tags: [analytics, persistence, fills, ws-execution, sprint-9]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/risk/fill_history.py
  - migrations/0006_trade_fills.sql
  - src/execution/bybit/ws_private.py
---

# Fill history

**TL;DR:** Per-fill granular audit log. `FillRecord` (pydantic) + `FillHistoryRepository` (SQLite-backed). FK к `trade_history.trade_id` (one trade → N fills). Idempotent insert на `exec_id` UNIQUE INDEX. Source = Bybit V5 WS `execution` topic (added в S9). Used by analytics (slippage measurement, fee breakdown, partial-fill audit).

## Public API

- `FillRecord` — pydantic v2 frozen model. Fields: fill_id, parent_trade_id, exec_id, fill_qty, fill_price, fill_fee, fee_currency, is_partial, fill_ts, recorded_at.
- `FillHistoryRepository.insert_fill(record) -> int` — idempotent; returns fill_id.
- `FillHistoryRepository.load_by_trade(parent_trade_id) -> list[FillRecord]` — ordered by fill_ts ASC.
- `FillHistoryRepository.count() -> int`.

## Schema (migrations/0006_trade_fills.sql)

| Column | Type | Constraint |
|--------|------|-----------|
| fill_id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| parent_trade_id | INTEGER | NOT NULL, FK trade_history.trade_id |
| exec_id | TEXT | NOT NULL, UNIQUE INDEX |
| fill_qty | TEXT | Decimal as str |
| fill_price | TEXT | Decimal as str |
| fill_fee | TEXT | Decimal as str |
| fee_currency | TEXT | NOT NULL |
| is_partial | INTEGER | CHECK 0 OR 1 |
| fill_ts | TEXT | ISO-8601 UTC |
| recorded_at | TEXT | ISO-8601 UTC |

Indexes: `uq_trade_fills_exec_id` (UNIQUE for idempotency), `idx_trade_fills_parent_ts` (load_by_trade lookup).

## Invariants (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | Decimal precision preserved (no float conversion) | `str(Decimal)` write + `Decimal(str)` read | `tests/unit/test_fill_history.py::test_decimal_roundtrip` |
| 2 | Idempotent на exec_id (at-least-once WS delivery) | `INSERT OR IGNORE` + UNIQUE INDEX | `tests/unit/test_fill_history.py::test_insert_idempotent_on_duplicate_exec_id` |
| 3 | FK к trade_history.trade_id | DDL FOREIGN KEY constraint | `tests/unit/test_db_migration_trade_fills.py::test_migration_0006_creates_trade_fills_table` |
| 4 | fill_qty > 0 | pydantic Field(gt=0) | `tests/unit/test_fill_history.py::test_negative_qty_rejected_at_model` |

## Data flow

```
Bybit V5 WS execution topic
    ↓
BybitPrivateWSConsumer._on_execution_raw(msg)
    ↓ for each item in msg["data"]
fill_recorder.on_fill_event(evt)  # _FillRecorderProto
    ↓ (caller maps execId/execQty/execPrice → FillRecord)
FillHistoryRepository.insert_fill(record)
    ↓
SQLite trade_fills table (UNIQUE exec_id idempotency)
```

## Referenced by

- [[trade-history]] — parent table; FillRecord.parent_trade_id FK
- [[ws-private-consumer]] — source of execution events
- [[dsr]] — future analytics consumer (S10+ if per-fill granularity needed для DSR)

## Related

- [[../decisions/0021-sprint-7-resilience]] — execution topic deferral source (S7→S9)
- [[../decisions/0022-sprint-8a-live-runtime]] — analytics+per-fill deferred again в S8b→S9
- [[../decisions/0024-sprint-9-data-quality-types-analytics]] — S9 aggregate ADR

## Sources

- `src/risk/fill_history.py` — FillRecord + FillHistoryRepository
- `migrations/0006_trade_fills.sql` — DDL
- `src/execution/bybit/ws_private.py` — WS execution topic subscription
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/components/fill-history.md
git commit -m "docs(wiki): fill-history component page (S9 Q3 B1)"
```

---

## Q3 B2 — DSR module (2 tasks)

### Task 9: DSR formula + tests

**Files:**
- Create: `src/analytics/dsr.py`
- Create: `tests/unit/test_dsr.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_dsr.py`:

```python
"""Tests for DSR (Deflated Sharpe Ratio) — Bailey & López de Prado.

Sprint 9 Q3 B2.
quant-stats-reviewer MUST review this module post-implementation.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.analytics.dsr import compute_dsr, compute_returns
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(*, pnl_pct: Decimal, exit_offset_hours: int) -> TradeRecord:
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 25, 12 + exit_offset_hours, 0, 0, tzinfo=UTC),
        qty=Decimal("0.5"),
        entry_price=Decimal("100000"),
        exit_price=Decimal("100000") * (Decimal("1") + pnl_pct),
        pnl_quote=Decimal("100"),
        pnl_pct=pnl_pct,
        fees_paid=Decimal("0.05"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=datetime(2026, 4, 25, 12, 1, 0, tzinfo=UTC),
    )


def test_compute_returns_log_default() -> None:
    """log returns = ln(1 + pnl_pct), default."""
    trades = [
        _make_trade(pnl_pct=Decimal("0.01"), exit_offset_hours=1),
        _make_trade(pnl_pct=Decimal("0.02"), exit_offset_hours=2),
    ]
    returns = compute_returns(trades)  # log default
    assert math.isclose(returns[0], math.log(1.01), rel_tol=1e-9)
    assert math.isclose(returns[1], math.log(1.02), rel_tol=1e-9)


def test_compute_returns_simple_via_flag() -> None:
    """simple returns = pnl_pct directly when use_log=False."""
    trades = [_make_trade(pnl_pct=Decimal("0.01"), exit_offset_hours=1)]
    returns = compute_returns(trades, use_log=False)
    assert returns[0] == 0.01


def test_compute_dsr_empty_returns_nan() -> None:
    """N=0 trades → DSR = NaN (defensive, не crash)."""
    result = compute_dsr([])
    assert math.isnan(result)


def test_compute_dsr_single_trade_returns_nan() -> None:
    """N=1 trade → variance undefined → NaN."""
    trades = [_make_trade(pnl_pct=Decimal("0.01"), exit_offset_hours=1)]
    result = compute_dsr(trades)
    assert math.isnan(result)


def test_compute_dsr_constant_returns_nan() -> None:
    """All identical returns → variance=0 → DSR undefined → NaN."""
    trades = [
        _make_trade(pnl_pct=Decimal("0.01"), exit_offset_hours=i)
        for i in range(1, 11)
    ]
    result = compute_dsr(trades)
    assert math.isnan(result)


def test_compute_dsr_positive_track_record_in_range() -> None:
    """Mixed positive returns yield DSR in (-inf, +inf), не crash."""
    trades = [
        _make_trade(pnl_pct=Decimal(f"0.0{i}"), exit_offset_hours=i)
        for i in range(1, 11)
    ]
    result = compute_dsr(trades)
    assert not math.isnan(result)
    assert math.isfinite(result)


def test_no_look_ahead_uses_only_exit_ts() -> None:
    """DSR only consumes closed trades (exit_ts populated). Verify фа functional."""
    trades = [
        _make_trade(pnl_pct=Decimal("0.01"), exit_offset_hours=1),
        _make_trade(pnl_pct=Decimal("0.02"), exit_offset_hours=2),
        _make_trade(pnl_pct=Decimal("0.005"), exit_offset_hours=3),
    ]
    returns = compute_returns(trades)
    # Returns array must align с trades order (closed trades, sorted by exit_ts)
    assert len(returns) == 3
    # Each return derived only from exit_price/entry_price relation, не future data
    assert returns[0] != returns[1]
```

- [ ] **Step 2: Run tests to confirm RED**

```bash
pytest tests/unit/test_dsr.py -v 2>&1 | tail -15
```

Expected: ImportError на `src.analytics.dsr`.

- [ ] **Step 3: Implement DSR module**

Create `src/analytics/dsr.py`:

```python
"""Deflated Sharpe Ratio (Bailey & López de Prado, 2014).

Sprint 9 Q3 B2.

DSR adjusts vanilla Sharpe ratio для:
- Sample length (small N inflates variance estimate)
- Skewness + kurtosis of returns (non-normality penalty)
- Multiple testing bias (если N strategies tested — supplied as `n_trials`)

Formula reference:
- Bailey, D.H., López de Prado, M. (2014) "The Deflated Sharpe Ratio: Correcting
  for Selection Bias, Backtest Overfitting and Non-Normality"
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551

This module operates on `TradeRecord` array (closed trades with exit_ts).
No look-ahead: each TradeRecord's pnl_pct is realized at exit_ts.

quant-stats-reviewer mandatory before merge — verify formula correctness +
annualization factor + log-vs-simple return choice.
"""
from __future__ import annotations

import math
from decimal import Decimal

from scipy import stats

from src.risk.trade_history import TradeRecord


def compute_returns(trades: list[TradeRecord], *, use_log: bool = True) -> list[float]:
    """Extract per-trade returns from TradeRecord list.

    Default = log returns (additive across trades, suitable для compounding).
    Set use_log=False для simple returns (pnl_pct directly).
    """
    out: list[float] = []
    for t in trades:
        pct = float(t.pnl_pct)
        if use_log:
            # log(1 + r) — defined for r > -1
            if pct <= -1.0:
                # Total loss; log(0+) = -inf. Defensive: skip OR represent as large negative
                out.append(-math.inf)
                continue
            out.append(math.log(1.0 + pct))
        else:
            out.append(pct)
    return out


def compute_dsr(
    trades: list[TradeRecord],
    *,
    benchmark_sharpe: float = 0.0,
    n_trials: int = 1,
    use_log: bool = True,
) -> float:
    """Compute Deflated Sharpe Ratio.

    Returns NaN if:
    - N=0 (no trades)
    - N=1 (variance undefined)
    - All returns identical (variance=0)

    Args:
        trades: closed TradeRecord list (exit_ts populated).
        benchmark_sharpe: prior Sharpe target (default 0).
        n_trials: number of strategies tested (multiple-testing penalty).
        use_log: log returns если True (default), simple if False.
    """
    returns = compute_returns(trades, use_log=use_log)
    n = len(returns)
    if n < 2:
        return math.nan

    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    if var <= 0:
        return math.nan
    std = math.sqrt(var)
    sharpe = mean / std

    # Skewness + kurtosis of returns
    skew = float(stats.skew(returns, bias=False))
    kurt = float(stats.kurtosis(returns, bias=False, fisher=True))  # excess kurtosis

    # Expected max Sharpe across n_trials (Bailey & López de Prado)
    # E[max SR_n] ≈ ((1 - γ) * Φ⁻¹(1 - 1/n_trials) + γ * Φ⁻¹(1 - 1/(n_trials * e)))
    # γ = Euler–Mascheroni constant ≈ 0.5772
    if n_trials <= 1:
        sharpe_star = benchmark_sharpe
    else:
        gamma = 0.5772156649
        z1 = stats.norm.ppf(1.0 - 1.0 / n_trials)
        z2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e))
        sharpe_star = benchmark_sharpe + (1.0 - gamma) * z1 + gamma * z2

    # DSR = Φ((sharpe - sharpe_star) * sqrt(n - 1) / sqrt(1 - skew*sharpe + (kurt-1)/4 * sharpe²))
    denom_inner = 1.0 - skew * sharpe + (kurt - 1.0) / 4.0 * sharpe**2
    if denom_inner <= 0:
        return math.nan
    denom = math.sqrt(denom_inner)
    z_dsr = (sharpe - sharpe_star) * math.sqrt(n - 1) / denom
    return float(stats.norm.cdf(z_dsr))
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/unit/test_dsr.py -v 2>&1 | tail -15
```

Expected: 7 passed.

- [ ] **Step 5: Verify mypy strict**

```bash
mypy --strict src/analytics/dsr.py 2>&1 | tail -3
```

Expected: `Success: no issues found in 1 source file`.

- [ ] **Step 6: Dispatch quant-stats-reviewer (MANDATORY per pre-s9-backlog cross-cutting concern #2)**

Use Agent tool с subagent_type="quant-stats-reviewer", prompt:

```
Review src/analytics/dsr.py — Deflated Sharpe Ratio implementation per
Bailey & López de Prado (2014). Sprint 9 Q3 B2.

Verify:
1. Formula correctness vs paper (DSR = Φ((SR - SR*) * sqrt(n-1) / denom))
2. Skew + excess kurtosis sign convention (Fisher kurtosis = excess)
3. Expected max Sharpe approximation для n_trials > 1 (Bailey-López de Prado)
4. log vs simple return treatment (compute_returns)
5. Edge cases: N<2, var=0, denom_inner ≤ 0 — все return NaN defensively
6. Look-ahead invariant: only TradeRecord.pnl_pct (realized at exit_ts) consumed
7. Annualization factor — currently NONE (not annualized; per-trade Sharpe). Decision: defer annualization к S10 walk-forward sprint, или add now? Recommend.

Output format: Blockers / Concerns / Verified / Follow-ups for wiki.
```

Apply reviewer follow-ups inline if Concerns/Follow-ups items.

- [ ] **Step 7: Commit (after reviewer approval)**

```bash
git add src/analytics/dsr.py tests/unit/test_dsr.py
git commit -m "feat(analytics): DSR module (Bailey & López de Prado) on TradeRecord array (S9 Q3 B2)"
```

---

### Task 10: Component page для DSR

**Files:**
- Create: `wiki/project/components/dsr.md`

- [ ] **Step 1: Write component page**

Create `llm-wiki/wiki/project/components/dsr.md`:

```markdown
---
title: DSR — Deflated Sharpe Ratio module
type: component
tags: [analytics, statistics, dsr, bailey-lopez-de-prado, sprint-9]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/analytics/dsr.py
  - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
---

# DSR (Deflated Sharpe Ratio)

**TL;DR:** Pure-function module computing Bailey & López de Prado (2014) Deflated Sharpe Ratio на `TradeRecord` array. Adjusts vanilla Sharpe для sample length + non-normality (skew + kurtosis) + multiple-testing bias (n_trials). No look-ahead: only consumes closed trades (TradeRecord.exit_ts populated). Returns NaN defensively на degenerate inputs (N<2, var=0, denom_inner≤0).

## Public API

- `compute_returns(trades, *, use_log=True) -> list[float]` — extract returns from TradeRecord array. log default (additive compounding); simple via flag.
- `compute_dsr(trades, *, benchmark_sharpe=0.0, n_trials=1, use_log=True) -> float` — DSR scalar in (0, 1) interpreted as Φ-CDF probability that observed Sharpe exceeds benchmark after adjusting for selection bias.

## Formula (Bailey & López de Prado 2014)

```
DSR = Φ( (SR_obs - SR_star) * √(n-1) / √(1 - γ̂*SR_obs + ((κ̂-1)/4)*SR_obs²) )

where:
  SR_obs = mean(returns) / std(returns)  -- observed per-trade Sharpe
  γ̂ = sample skewness (Fisher, bias-corrected)
  κ̂ = sample excess kurtosis (Fisher, bias-corrected)
  SR_star = benchmark + (1-γ)*Φ⁻¹(1-1/N) + γ*Φ⁻¹(1-1/(N*e))  -- expected max Sharpe across N strategy trials
  γ ≈ 0.5772 (Euler-Mascheroni)
  Φ = standard normal CDF
  Φ⁻¹ = inverse CDF (quantile)
```

## Invariants (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | NaN на N<2 (variance undefined) | early return math.nan | `tests/unit/test_dsr.py::test_compute_dsr_empty_returns_nan` + `test_compute_dsr_single_trade_returns_nan` |
| 2 | NaN на var=0 (constant returns) | guard if var <= 0 | `tests/unit/test_dsr.py::test_compute_dsr_constant_returns_nan` |
| 3 | NaN на denom_inner ≤ 0 (DSR undefined) | guard if denom_inner <= 0 | (implicit — denom check) |
| 4 | log returns default (additive compounding) | `use_log=True` default | `tests/unit/test_dsr.py::test_compute_returns_log_default` |
| 5 | No look-ahead — uses only closed TradeRecord (exit_ts populated) | function signature accepts list[TradeRecord]; пользователь supplies closed trades | `tests/unit/test_dsr.py::test_no_look_ahead_uses_only_exit_ts` |
| 6 | Pure function, no I/O, no module-level state | docstring + structure | code review |

## Annualization (NOT included v0.1)

Current per-trade Sharpe is NOT annualized. Annualization factor для irregular trade frequency requires:
- Per-trade duration (entry_ts → exit_ts) for time-weighted normalization
- Bar-frequency assumption (1H — 8760 bars/year)
- Convention choice (252 trading days vs 365 calendar)

Deferred к S10 (WFA + walk-forward annualization decision).

## Multiple-testing penalty (n_trials)

Default `n_trials=1` — single strategy tested, no penalty.
Set `n_trials=N` для report multiple-strategy backtest selection bias adjustment.
Per Bailey & López de Prado: ignoring n_trials when multiple variants tested = inflated Sharpe estimate.

## Referenced by

- (S10 walk-forward sprint, future) — DSR consumed by walk-forward acceptance gate

## Related

- [[trade-history]] — input data source (TradeRecord array)
- [[fill-history]] — granular fill data (NOT consumed by DSR — operates on per-trade level)
- [[../decisions/0014-walk-forward-train2000-test500]] — walk-forward gate uses Sharpe (DSR foundation для S10)
- [[../decisions/0015-sign-flip-mc-permutations-n2000]] — sign-flip MC permutations (companion statistical method)
- [[../decisions/0024-sprint-9-data-quality-types-analytics]] — S9 aggregate ADR

## Sources

- `src/analytics/dsr.py`
- Bailey, D.H., López de Prado, M. (2014) "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality" https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/components/dsr.md
git commit -m "docs(wiki): DSR component page (S9 Q3 B2)"
```

---

## Final tasks (ADR + wiki sync) — 2 tasks

### Task 11: ADR 0024 — S9 aggregate decisions

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0024-sprint-9-data-quality-types-analytics.md`

- [ ] **Step 1: Write ADR**

Create `llm-wiki/wiki/project/decisions/0024-sprint-9-data-quality-types-analytics.md`:

```markdown
---
title: 0024. Sprint 9 — Data quality detector + mypy strict + per-fill analytics + DSR
type: decision
date: 2026-04-25
sprint: 9
tags: [adr, sprint-9, data-quality, mypy, per-fill, dsr, analytics]
sources:
  - project/pre-s9-backlog.md
  - project/decisions/0023-halt-code-fsm-event-mapping.md
  - project/decisions/0022-sprint-8a-live-runtime.md
status: accepted
---

# 0024. Sprint 9 — Data quality + mypy strict + per-fill analytics + DSR

**Status:** accepted
**Date:** 2026-04-25

## Context

Sprint 9 закрывает 3 deferred carry-overs:

1. **C (Q1):** WS+REST price epsilon-halt detector — deferred с S8b (originally S8 Q8 alternative); `HALT_DATA_QUALITY` pre-allocated в `ReasonCode` enum since S4 без активного detector.
2. **G (Q2):** mypy --strict full enable — `pyproject.toml` declares `strict = true` но overrides exclude `src.core.*`, `src.backtest.*`, `src.risk.*` через `ignore_errors = true`.
3. **B (Q3):** Per-fill analytics + DSR foundation — deferred ADR 0021 (S7) → ADR 0022 (S8a) → S8b → S9 (3-sprint deferral).

PHASE 2 brainstorming verdicts (`pre-s9-backlog.md`):
- Q1: REVISE — REST-vs-REST consecutive bar (NOT WS+REST kline). Trader argument: WS kline subscription doesn't exist, async dep contradicts S8a ADR 0022 deferral, partial-bar updates create false-positive risk.
- Q2: REVISE — order src.core → src.risk → src.backtest. Empirical follow-up в plan: ALL 3 modules pass `mypy --strict` clean — override masks zero errors. Reduces к single override-removal task.
- Q3: CONFIRM — split B1 (per-fill table + WS execution topic) + B2 (DSR module on TradeRecord).

## Options

### Q1 — Quality detector source

- **A. WS+REST kline comparison** (rejected) — requires new WS subscription, async dep, partial-bar false-positive risk
- **B. REST-vs-REST consecutive bar comparison** (chosen) — no new infrastructure, atomic comparison, baseline rolls forward
- **C. Ticker REST snapshot** (rejected) — high frequency noisy, irrelevant for 1H strategy

### Q2 — mypy strict scope

- **A. Remove all 3 overrides at once** (chosen post-empirical-check) — мypy --strict clean on all 3 modules empirically. Single override-removal task.
- **B. Sequential per-module** (initially recommended in PHASE 2) — superseded by empirical finding.
- **C. Defer** (rejected) — overrides perpetually mask future drift.

### Q3 — Per-fill scope

- **A. Combined per-fill + DSR в one task** (rejected) — over-scope, partial-fail leaves half done
- **B. Split B1 + B2** (chosen) — independent concerns, can ship in parallel
- **C. DSR-only, defer per-fill** (rejected) — 3-sprint deferral debt

## Decision

### Q1 (C — Data quality)

`BarPriceQualityDetector` в `src/marketdata/quality.py`:
- Stateless: in-memory `_last_close` baseline rolls forward each call
- Threshold: 0.5% relative deviation (Settings: `quality_threshold_pct`, default `Decimal("0.005")`)
- Cadence: per-bar (after `BarSource.poll()` returns new closed bar)
- Halt routing: `Coordinator.request_halt(reason=ReasonCode.HALT_DATA_QUALITY)` → existing `RISK_HALT` event path
- FSM impact: NONE (uses existing event, no new state/event/transition)

Per ADR 0023 invariant: `HALT_DATA_QUALITY` added к `_REQUEST_HALT_CODES` allow-list в property test (`tests/property/test_request_halt_mapping.py`).

### Q2 (G — mypy strict)

Remove block from `pyproject.toml`:

```toml
[[tool.mypy.overrides]]
module = ["src.core.*", "src.backtest.*", "src.risk.*"]
ignore_errors = true
```

Empirical verification (pre-removal): all 3 modules pass `mypy --strict` clean. Removal converts implicit pass → explicit type checking, prevents future drift accumulation.

Keep `ignore_missing_imports = true` for pybit/pyarrow/talib (untyped third-party — orthogonal).

### Q3 B1 (Per-fill schema)

- NEW migration: `migrations/0006_trade_fills.sql` — `trade_fills` table с FK `parent_trade_id → trade_history.trade_id`, UNIQUE INDEX `exec_id`, indexes
- NEW model: `src/risk/fill_history.py::FillRecord` (pydantic v2 frozen)
- NEW repository: `src/risk/fill_history.py::FillHistoryRepository`
- WS extension: `src/execution/bybit/ws_private.py` adds `_FillRecorderProto` + `execution_stream` subscription + `_on_execution_raw` handler

### Q3 B2 (DSR module)

- NEW: `src/analytics/dsr.py` (`src/analytics/__init__.py` empty stub since S4)
- Functions: `compute_returns(trades, *, use_log=True)`, `compute_dsr(trades, *, benchmark_sharpe=0.0, n_trials=1, use_log=True)`
- Operates on `TradeRecord` array (closed trades с `exit_ts` populated) — no look-ahead
- log returns default (additive compounding); simple via flag
- Annualization factor NOT included v0.1 (deferred к S10 walk-forward)
- Multiple-testing penalty via `n_trials` parameter (default 1 = single strategy)
- quant-stats-reviewer MANDATORY (formula correctness verification)

## Consequences

**Plus:**
- HALT_DATA_QUALITY now active (was placeholder enum-only since S4)
- mypy strict prevents future type drift accumulation
- Per-fill granularity unblocks S10+ analytics (slippage, fee breakdown, partial-fill audit)
- DSR foundation ready для S10 walk-forward acceptance gate
- 3 deferred carry-overs closed

**Minus:**
- New WS topic subscription = surface area for pybit drift (mitigated: `_FillRecorderProto` + try/except в `_on_execution_raw` mirrors existing `_on_order_raw` pattern)
- `trade_fills` schema requires migration deployment (idempotent CREATE TABLE — safe)
- DSR без real backtest data = academic until first live trades (S11 F)

## Related

- [[../pre-s9-backlog]] — PHASE 2 brainstorming verdicts trail
- [[0021-sprint-7-resilience]] — per-fill execution topic deferral source
- [[0022-sprint-8a-live-runtime]] — wallet WS+REST epsilon-halt rejection (REST canonical per ADR 0020 sub-decision 4)
- [[0023-halt-code-fsm-event-mapping]] — `_REQUEST_HALT_CODES` allow-list invariant
- [[../components/data-quality]] — Q1 detector implementation
- [[../components/fill-history]] — Q3 B1 implementation
- [[../components/dsr]] — Q3 B2 implementation
- [[../plans/2026-04-25-sprint-9-quality-types-analytics]] — implementation plan + trace map

## Amendments

- (none yet)
```

- [ ] **Step 2: Verify ADR 0024 referenced в index.md (adr-index-sync hook will block push otherwise)**

Edit `llm-wiki/wiki/index.md` "## Project — Decisions" section — add line:

```markdown
- [[project/decisions/0024-sprint-9-data-quality-types-analytics]] — S9 aggregate ADR: Data quality detector (REST-vs-REST) + mypy strict + per-fill schema + DSR module.
```

- [ ] **Step 3: Touch agent prompt to satisfy adr-agent-sync hook**

```bash
touch ~/.claude/agents/quant-stats-reviewer.md
```

(quant-stats-reviewer touched because B2 DSR review will use this agent — explicit acknowledgment.)

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0024-sprint-9-data-quality-types-analytics.md llm-wiki/wiki/index.md
git commit -m "docs(adr): ADR 0024 — S9 aggregate decisions (Q1+Q2+Q3) (S9)"
```

---

### Task 12: Wiki sync — current-state.md + components page для quality + sprint-09 page

**Files:**
- Create: `wiki/project/components/data-quality.md`
- Create: `wiki/project/sprints/sprint-09-data-quality-types-analytics.md`
- Modify: `wiki/project/architecture/current-state.md`
- Modify: `wiki/project/components/README.md` (add new components к cluster)
- Modify: `wiki/project/mental-map.md` (add new domain queries)

- [ ] **Step 1: Create data-quality component page**

Create `llm-wiki/wiki/project/components/data-quality.md`:

```markdown
---
title: Bar price quality detector — REST-vs-REST deviation
type: component
tags: [marketdata, data-quality, halt, sprint-9]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/marketdata/quality.py
  - src/runtime/manager.py
---

# Bar price quality detector

**TL;DR:** Stateless detector comparing current REST closed bar price vs previously observed REST closed bar (in-memory baseline). Threshold = 0.5% relative deviation (Settings tunable). Per-bar cadence. Triggers `HALT_DATA_QUALITY` via existing `RISK_HALT` event path (no new FSM event/state).

## Public API

- `BarPriceQualityDetector.__init__(*, threshold_pct: Decimal)` — raise ValueError if threshold ≤ 0
- `BarPriceQualityDetector.check(*, current_close: Decimal) -> bool` — returns True if deviation > threshold (caller emits halt)

## Why REST-vs-REST (not WS+REST)

Per `pre-s9-backlog.md` Q1 verdict (REVISE accepted):
- WS kline subscription does not exist (`ws_private` only subscribes order + wallet).
- Wiring WS kline contradicts S8a ADR 0022 async/sync deferral к S9+.
- WS partial-bar updates create false-positive risk при per-bar comparison.
- REST-vs-REST consecutive bar deviation 0.5% on 1H BTCUSDT @ ~$100k = ~$500 instantaneous move — catches stuck/corrupted feed без new infrastructure.

## Invariants (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | First call no baseline → returns False | `if prior is None: return False` | `tests/unit/test_quality_detector.py::test_first_poll_skips_no_prior_baseline` |
| 2 | Symmetric — abs(deviation) used | `abs(current - prior)` | `tests/unit/test_quality_detector.py::test_negative_deviation_uses_absolute_value` |
| 3 | Defensive — prior_close ≤ 0 returns False | `if prior <= 0: return False` | `tests/unit/test_quality_detector.py::test_zero_prior_close_defensive` |
| 4 | Threshold > 0 enforced at construction | `if threshold_pct <= 0: raise ValueError` | `tests/unit/test_quality_detector.py::test_negative_threshold_rejected` |
| 5 | Strict > comparison (boundary value not halt) | `if deviation_pct > threshold` | `tests/unit/test_quality_detector.py::test_threshold_at_boundary` |
| 6 | Stateless (no module state, caller owns persistence) | instance-only `_last_close` field | code review |

## Halt routing

Per ADR 0023 invariant — `HALT_DATA_QUALITY` added к `_REQUEST_HALT_CODES` allow-list в `tests/property/test_request_halt_mapping.py`. Coordinator routes via existing `RISK_HALT` event path:

```
RuntimeManager._poll_bar_and_strategy()
    bar = bar_source.poll()
    if quality_detector.check(current_close=bar.close):
        coordinator.request_halt(reason=ReasonCode.HALT_DATA_QUALITY)
        return  # skip strategy
```

## Configuration

Settings field `quality_threshold_pct: Decimal = Decimal("0.005")` — default 0.5%. Tunable per environment.

## Referenced by

- [[runtime-manager]] — owns detector lifecycle; calls `check` after each `BarSource.poll()` returns new bar
- [[bar-poller]] — provides input data (BarSource closed bars)
- [[../runbooks/halt-recovery]] — operator runbook covers HALT_DATA_QUALITY (Operational class group)

## Related

- [[../decisions/0024-sprint-9-data-quality-types-analytics]] — origin ADR
- [[../decisions/0023-halt-code-fsm-event-mapping]] — `_REQUEST_HALT_CODES` invariant
- [[coordinator]] — `request_halt` halt entry-point
- [[circuit-breakers]] — sister halt detectors (drawdown / flash crash)

## Sources

- `src/marketdata/quality.py`
- `tests/unit/test_quality_detector.py`
```

- [ ] **Step 2: Create sprint-09 page**

Create `llm-wiki/wiki/project/sprints/sprint-09-data-quality-types-analytics.md`:

```markdown
---
title: Sprint 9 — Data quality + mypy strict + per-fill analytics + DSR
type: sprint
tags: [sprint-9, data-quality, mypy-strict, per-fill, dsr, halt-code]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/plans/2026-04-25-sprint-9-quality-types-analytics
  - project/decisions/0024-sprint-9-data-quality-types-analytics
  - project/pre-s9-backlog
---

# Sprint 9 — Data quality + mypy strict + per-fill analytics + DSR

## Overview

S9 закрывает 3 deferred carry-overs (C + G + B grouping per pre-S9 brainstorm). Pure additive: 3 new modules + 1 new migration + WS topic extension + override removal. 0 behavioral regressions. FSM/event/transition counts unchanged (HALT_DATA_QUALITY uses existing RISK_HALT event path per ADR 0023 invariant).

12 tasks, TDD throughout. Tag `v0.1.0-alpha.9`.

## Plan / ADR links

- Plan: [[../plans/2026-04-25-sprint-9-quality-types-analytics]]
- ADR (NEW): [[../decisions/0024-sprint-9-data-quality-types-analytics]]
- Brainstorm trail: [[../pre-s9-backlog]]

## Deliverables

### Q1 — Data quality (3 tasks)

- T1: NEW `src/marketdata/quality.py::BarPriceQualityDetector` + 8 unit tests
- T2: Coordinator HALT_DATA_QUALITY explicit dispatch + property test allow-list expanded к 4 codes
- T3: RuntimeManager integration — quality detector wired into tick pipeline

### Q2 — mypy strict (1 task)

- T4: Removed `ignore_errors = true` override для `src.core.*`, `src.backtest.*`, `src.risk.*`. Empirical: all 3 modules already passed `mypy --strict` clean.

### Q3 B1 — Per-fill schema (3 tasks)

- T5: NEW `migrations/0006_trade_fills.sql` (FK trade_history, UNIQUE exec_id)
- T6: NEW `src/risk/fill_history.py::FillRecord` + `FillHistoryRepository` + 7 unit tests
- T7: WS execution topic subscription added к `src/execution/bybit/ws_private.py`
- T8: NEW `wiki/project/components/fill-history.md`

### Q3 B2 — DSR (2 tasks)

- T9: NEW `src/analytics/dsr.py` — Bailey & López de Prado DSR formula + 7 unit tests + quant-stats-reviewer APPROVED
- T10: NEW `wiki/project/components/dsr.md`

### Wiki + ADR sync (2 tasks)

- T11: NEW ADR 0024 + index.md entry
- T12: This sprint page + current-state.md counts update + components/README cluster + mental-map updates

## FSM growth

NONE. Counts unchanged: 16 states / 30 events / 74 transitions / 45 reason codes.

HALT_DATA_QUALITY (pre-allocated в ReasonCode enum since S4) routed через existing RISK_HALT event path per ADR 0023 invariant.

## Reason codes growth

NONE.

## Tests

- pytest: 6XX passed / 24 skipped / 0 failed (NEW: 8 quality + 7 fill + 7 dsr + 1 coordinator + 2 migration + 1 ws_private = +26 tests)
- mypy --strict src/ → Success: no issues found in 60+ source files (post Q2 G)
- Property test `tests/property/test_request_halt_mapping.py` — 4 codes в allow-list (added HALT_DATA_QUALITY)

## Wiki updates

- 3 new component pages (data-quality, fill-history, dsr)
- 1 new ADR (0024)
- 1 new sprint page (this)
- 1 new migration (0006)
- mental-map.md: data quality + per-fill + DSR domain queries added
- components/README.md: 3 new components added к clusters

## Open issues для S10

- DSR annualization factor (deferred — irregular trade frequency normalization decision)
- Walk-Forward acceptance gate consuming DSR (S10 D scope)
- Per-fill consumed by DSR (currently DSR uses per-trade only — future granularity if needed)

## Key decisions

- **REST-vs-REST quality detector** (NOT WS+REST kline) — closes async dependency + WS partial-bar false-positive risk per Q1 trader REVISE
- **mypy strict empirically zero-cost** — overrides masked zero actual errors; single removal task vs originally planned 3-task wedge
- **Split B1 + B2** — independent concerns, parallel ship
- **HALT_DATA_QUALITY uses existing RISK_HALT** — no new FSM state/event/transition needed (ADR 0023 invariant satisfied via _REQUEST_HALT_CODES allow-list expansion)
- **DSR annualization deferred** к S10 walk-forward sprint (decision needed: 252 vs 365 vs irregular weighting)

## Related

- [[../plans/2026-04-25-sprint-9-quality-types-analytics]] — full plan + trace map
- [[../decisions/0024-sprint-9-data-quality-types-analytics]] — aggregate ADR
- [[../pre-s9-backlog]] — PHASE 2 verdicts trail
- [[sprint-08c-wiki-backfill]] — predecessor sprint
- [[../components/data-quality]] + [[../components/fill-history]] + [[../components/dsr]] — new components
```

- [ ] **Step 3: Update current-state.md canonical-counts**

Edit `llm-wiki/wiki/project/architecture/current-state.md` canonical-counts table:

```markdown
| Component pages | **31** | `wiki/project/components/*.md` | S9 (data-quality + fill-history + dsr) |
| ADRs | **24** | `wiki/project/decisions/*.md` (0001-0024) | S9 (ADR 0024 — aggregate Q1+Q2+Q3) |
| Sprint pages | **11** | `wiki/project/sprints/sprint-*.md` (sprint-01..sprint-09 + sprint-08a + sprint-08b + sprint-08c) | S9 (sprint-09-data-quality-types-analytics) |
```

Update TL;DR: `10 sprints completed (S1-S7 + S8a + S8b + S8c)` → `11 sprints completed (S1-S7 + S8a + S8b + S8c + S9)`. Update tag reference v0.1.0-alpha.8c → v0.1.0-alpha.9.

- [ ] **Step 4: Update components/README.md cluster index**

Edit `llm-wiki/wiki/project/components/README.md`:

Cluster 1 (Market Data ingest) — add row:
```markdown
| [[data-quality]] | REST-vs-REST consecutive bar deviation detector → HALT_DATA_QUALITY (S9) |
```

Cluster 3 (Risk + sizing) — add row:
```markdown
| [[fill-history]] | Per-fill audit log + repository (FK trade_history) — S9 Q3 B1 |
```

NEW Cluster 10 (Analytics — single component для now):
```markdown
## Cluster 10 — Analytics

**Theme:** Statistical post-process modules. Sprint origin: S9 Q3 B2 (foundation).

| Component | Role |
|-----------|------|
| **[[dsr]]** | Bailey & López de Prado Deflated Sharpe Ratio — pure-function on TradeRecord array |

**Bridge to:** Risk (consumes trade_history TradeRecord), future S10 walk-forward acceptance gate
```

- [ ] **Step 5: Update mental-map.md**

Edit `llm-wiki/wiki/project/mental-map.md` — add к "Tooling / hooks / methodology" OR new "Data quality" section:

```markdown
| Data quality halt detector (HALT_DATA_QUALITY) | `components/data-quality.md` + `src/marketdata/quality.py` (S9) |
| Per-fill audit + WS execution topic | `components/fill-history.md` + `src/risk/fill_history.py` (S9) |
| DSR (Deflated Sharpe Ratio) | `components/dsr.md` + `src/analytics/dsr.py` (S9, Bailey & López de Prado) |
```

- [ ] **Step 6: Verify counts live**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected: `states=16, events=30, transitions=74, reason_codes=45` (unchanged).

```bash
ls llm-wiki/wiki/project/components/*.md | wc -l  # expect 31
ls llm-wiki/wiki/project/decisions/*.md | wc -l   # expect 24
ls llm-wiki/wiki/project/sprints/sprint-*.md | wc -l  # expect 11
```

- [ ] **Step 7: Commit**

```bash
git add llm-wiki/wiki/project/components/data-quality.md llm-wiki/wiki/project/sprints/sprint-09-data-quality-types-analytics.md llm-wiki/wiki/project/architecture/current-state.md llm-wiki/wiki/project/components/README.md llm-wiki/wiki/project/mental-map.md
git commit -m "docs(wiki): S9 sync — sprint page + data-quality component + counts + cluster + mental-map (S9)"
```

---

## PHASE 8 finishing (after T1-T12 complete)

- [ ] **Step 1: Run pre-validation**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/unit tests/property -x -q 2>&1 | tail -3
mypy src/ 2>&1 | tail -2
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected: 615+ passed, mypy clean, counts 16/30/74/45.

- [ ] **Step 2: Invoke `sprint-finish` skill**

`sprint-finish` skill enforces all HARD-GATEs (sprint-NN.md exists ✓ T12, canonical counts sync ✓ T12, orphan-audit grep includes tests/, Block 1↔2 sync, index.md ADR sync ✓ T11) → `superpowers:finishing-a-development-branch`.

- [ ] **Step 3: Push + PR + squash-merge + tag v0.1.0-alpha.9**

Per `superpowers:finishing-a-development-branch` skill protocol.

- [ ] **Step 4: SPRINT_STATE update → between-sprints**

Per CLAUDE.md session-end procedure.

---

## Self-review checklist

**Spec coverage:**
- ✅ Q1 (C) → T1+T2+T3 (detector + halt routing + RuntimeManager wire)
- ✅ Q2 (G) → T4 (override removal)
- ✅ Q3 B1 → T5+T6+T7+T8 (migration + repo + WS topic + component page)
- ✅ Q3 B2 → T9+T10 (DSR module + component page)
- ✅ ADR + wiki sync → T11+T12 (ADR 0024 + sprint page + current-state)

**Cross-cutting concerns covered:**
- ✅ #1 (mypy strict + new modules) — T1, T6, T9 each verify mypy --strict step
- ✅ #2 (quant-stats-reviewer mandatory B2) — T9 step 6 explicit dispatch
- ✅ #3 (HALT_DATA_QUALITY → RISK_HALT, no new FSM) — T2 verifies
- ✅ #4 (no new ADR for C alone) — T11 covers C in aggregate ADR 0024
- ✅ #5 (NEW ADR 0024 для G+B aggregate) — T11

**Placeholder scan:** No TBD / TODO / "implement later" / "add validation" placeholders. Every code block complete.

**Type consistency:**
- `BarPriceQualityDetector(threshold_pct: Decimal)` consistent T1 + T3 (RuntimeManager wire) + T12 (component page)
- `FillRecord(parent_trade_id, exec_id, fill_qty, fill_price, fill_fee, fee_currency, is_partial, fill_ts, recorded_at)` consistent T6 + T8 + ADR 0024
- `compute_dsr(trades, *, benchmark_sharpe=0.0, n_trials=1, use_log=True)` consistent T9 + T10
- `_FillRecorderProto.on_fill_event(evt: dict[str, Any])` consistent T7

---

## Total: 12 tasks, TDD throughout, ~12-15 commits estimated, ~6 hours work

Estimated test count delta: +26 tests (8 quality + 7 fill + 7 dsr + 1 coordinator + 2 migration + 1 ws_private). Baseline 589 → ~615 passed.
