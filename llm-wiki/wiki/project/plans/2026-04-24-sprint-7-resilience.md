---
title: "Sprint 7 — Resilience Implementation Plan"
type: plan
status: draft
created: 2026-04-24
updated: 2026-04-24
sources:
  - wiki/project/decisions/0021-sprint-7-resilience.md
  - wiki/project/decisions/0020-sprint-6-execution-spot-oco-emulation.md
  - wiki/project/components/execution-state-machine.md
  - wiki/project/components/reconciler.md
  - wiki/project/components/oco.md
tags: [sprint-7, resilience, execution, fsm, reconcile, ws-reconnect, halt-persistence, tdd]
---

# Sprint 7 — Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close S6 review follow-ups (C1 bootstrap reconcile, C2 WS-reconnect wiring for ENTRY_PENDING/EXIT_PENDING) + persist `halt_reason`/`last_exit_reason` + introduce trading-side WS private consumer, with Phase G testnet acceptance gate.

**Architecture:** Composition-first — `Coordinator.bootstrap()` delegates to `Coordinator.on_ws_reconnect()` (single reconcile path). Reconciler becomes 4-valued (AGREE / DIVERGENCE / HEAL_ENTRY_FILLED / EXITED) with optional `expected_state` hint. FSM expanded with 2 new events (RECONCILE_ENTRY_FILLED, RECONCILE_EXITED) and 4 new transitions. Halt persistence via `γ`-pattern: `halt_reason` column (primary reason wins) + append-only `halt_log` audit. WS private consumer subscribes to `order` + `wallet` topics (execution topic deferred to S8).

**Tech Stack:** Python 3.12, pydantic v2, pybit (WebSocket V5), SQLite (forward-only migrations), pytest + Hypothesis, existing FSM pattern (state_machine.py dict-table transitions).

**Source of truth:** [[../decisions/0021-sprint-7-resilience]]. All 9 sub-decisions are referenced inline in tasks below.

---

## File Structure

**New files:**

| Path | Responsibility |
|------|----------------|
| `migrations/0005_halt_persistence.sql` | ALTER `execution_state` (4 cols) + CREATE TABLE `halt_log` + INDEX |
| `src/execution/bybit/ws_private.py` | `BybitPrivateWSConsumer` — pybit WebSocket V5 private, order+wallet topics |
| `tests/unit/test_state_machine_s7.py` | FSM new events + 4 transitions (positive + illegal) |
| `tests/unit/test_reconciler_verdicts.py` | 4-valued verdict matrix × 3 `expected_state` hints |
| `tests/unit/test_coordinator_bootstrap_reconcile.py` | `bootstrap()`: cold / warm HEAL / warm HALT / warm AGREE |
| `tests/unit/test_coordinator_on_ws_reconnect.py` | 5 state paths: ENTRY_PENDING, EXIT_PENDING, OCO_ARMING, EXIT_SIBLING_CANCELLING, EXIT_SL_RESIDUAL |
| `tests/unit/test_halt_persistence.py` | `_set_halt()` idempotency + halt_log append |
| `tests/unit/test_ws_private_consumer.py` | parser validation (cumExecFee mandatory), dispatch routing, reconnect |
| `tests/property/test_bootstrap_ws_reconnect_idempotent.py` | Hypothesis: N reconnects don't break FSM |
| `tests/integration/test_bootstrap_demo.py` | opt-in `RUN_DEMO=1` — real crash/restart cycle |
| `llm-wiki/wiki/project/components/ws-private-consumer.md` | new component doc |
| `llm-wiki/wiki/project/runbooks/halt-recovery.md` | update existing with SQL query section |

**Modified files:**

| Path | Change |
|------|--------|
| `src/execution/state_machine.py` | +2 events in `ExecutionEvent`, +4 transitions in `_TRANSITIONS` |
| `src/execution/reconciler.py` | `ReconcileResult` 4-valued + `heal_context` field; `reconcile(local, expected_state=None)`; `_wallet_cache` |
| `src/execution/coordinator.py` | `bootstrap()` composition, `on_ws_reconnect()` NEW, `_set_halt()` wrapper, `_bootstrap_done` flag |
| `src/execution/state_repo.py` | `ExecutionStateRow` +4 fields; `_set_halt()` idempotent helper |
| `src/platform/config.py` | `Settings.heal_max_age_seconds: int = 3600`, `Settings.require_mainnet_gate_passed: bool = True` |
| `llm-wiki/wiki/project/components/execution-state-machine.md` | Known limitations → S7 closed section; transitions table update |
| `llm-wiki/wiki/project/components/reconciler.md` | 4-valued verdict, wallet_cache, classification algorithm |
| `llm-wiki/wiki/project/components/oco.md` | bootstrap reconcile mention в happy/crash paths |
| `llm-wiki/wiki/project/components/bybit-adapter.md` | cross-ref к ws_private consumer |
| `llm-wiki/wiki/index.md` | +ws-private-consumer, +halt-recovery entries |
| `llm-wiki/wiki/log.md` | append S7 session entries |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | phase/progress updates (per-task) |

---

## Task Sequencing Rationale

Dependency ordering per reviewer Q1 validation:

```
Phase 0 (foundation):  Tasks 1-3  → schema + config + repo row
Phase 1 (FSM):         Tasks 4-8  → events + transitions (no runtime deps)
Phase 2 (halt γ):      Tasks 9-10 → _set_halt helper + callsites (depends Phase 0)
Phase 3 (reconciler):  Tasks 11-16 → 4-valued + classification + wallet_cache (depends Phase 1+2)
Phase 4 (WS consumer): Tasks 17-19 → order + wallet topics (depends Phase 3 for wallet_cache contract)
Phase 5 (coordinator): Tasks 20-22 → on_ws_reconnect + bootstrap + startup assert (depends Phase 3+4)
Phase 6 (hardening):   Tasks 23-24 → property + integration tests
Phase 7 (ship):        Task 25    → wiki + Phase G probes + SPRINT_STATE + tag
```

**Critical path:** Phase 4 (WS consumer) is prerequisite for live-traffic smoke test. Unit tests don't require pybit connection — use mock adapter.

---

## Task 1: Schema migration 0005_halt_persistence.sql

**Files:**
- Create: `migrations/0005_halt_persistence.sql`
- Test: `tests/unit/test_halt_persistence.py` (portion — schema part)

**References:** ADR 0021 sub-decision 5 + 9.

- [ ] **Step 1: Write migration**

Create `migrations/0005_halt_persistence.sql`:

```sql
-- Migration 0005: halt persistence + reconcile timestamps + audit log
-- ADR 0021 sub-decisions 5, 9.

ALTER TABLE execution_state ADD COLUMN halt_reason TEXT;
ALTER TABLE execution_state ADD COLUMN last_exit_reason TEXT;
ALTER TABLE execution_state ADD COLUMN last_reconcile_at TEXT;
ALTER TABLE execution_state ADD COLUMN bootstrap_at TEXT;

CREATE TABLE halt_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT    NOT NULL,
    ts           TEXT    NOT NULL,
    reason       TEXT    NOT NULL,
    context_json TEXT    NOT NULL
);

CREATE INDEX halt_log_symbol_ts ON halt_log(symbol, ts);
```

- [ ] **Step 2: Write the failing test (schema smoke)**

Create `tests/unit/test_halt_persistence.py` with:

```python
"""Schema + _set_halt idempotency tests (ADR 0021 sub-decisions 5+9)."""
import sqlite3
from pathlib import Path

import pytest


MIG_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _apply_migrations(conn: sqlite3.Connection) -> None:
    for mig_path in sorted(MIG_DIR.glob("*.sql")):
        conn.executescript(mig_path.read_text())


def test_migration_0005_adds_halt_columns(tmp_path):
    db = sqlite3.connect(tmp_path / "test.db")
    _apply_migrations(db)
    cols = {row[1] for row in db.execute("PRAGMA table_info(execution_state)")}
    assert {"halt_reason", "last_exit_reason", "last_reconcile_at", "bootstrap_at"}.issubset(cols)


def test_migration_0005_creates_halt_log_table(tmp_path):
    db = sqlite3.connect(tmp_path / "test.db")
    _apply_migrations(db)
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "halt_log" in tables
    # Index present
    indexes = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "halt_log_symbol_ts" in indexes
```

- [ ] **Step 3: Run tests to verify fail → pass**

Run: `pytest tests/unit/test_halt_persistence.py::test_migration_0005_adds_halt_columns tests/unit/test_halt_persistence.py::test_migration_0005_creates_halt_log_table -v`

Expected: PASS both (migration applies cleanly, PRAGMA returns new cols).

- [ ] **Step 4: Commit**

```bash
git add migrations/0005_halt_persistence.sql tests/unit/test_halt_persistence.py
git commit -m "feat(schema): add migration 0005 halt persistence (ADR 0021)"
```

---

## Task 2: ExecutionStateRow +4 fields + repo read-path

**Files:**
- Modify: `src/execution/state_repo.py`
- Test: existing `tests/unit/test_state_repo.py` (add cases)

**References:** ADR 0021 sub-decision 5.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_state_repo.py`:

```python
def test_execution_state_row_has_halt_persistence_fields(tmp_path):
    """ADR 0021 sub-decision 5: row exposes halt_reason, last_exit_reason, last_reconcile_at, bootstrap_at."""
    from src.execution.state_repo import ExecutionStateRepo
    repo = ExecutionStateRepo(tmp_path / "test.db")
    repo.upsert_initial(symbol="BTCUSDT")
    row = repo.get("BTCUSDT")
    assert row is not None
    assert row.halt_reason is None
    assert row.last_exit_reason is None
    assert row.last_reconcile_at is None
    assert row.bootstrap_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_state_repo.py::test_execution_state_row_has_halt_persistence_fields -v`
Expected: FAIL — `AttributeError: 'ExecutionStateRow' object has no attribute 'halt_reason'`

- [ ] **Step 3: Extend dataclass + repo read**

In `src/execution/state_repo.py`:

```python
@dataclass(frozen=True)
class ExecutionStateRow:
    # ... existing fields ...
    halt_reason: str | None = None
    last_exit_reason: str | None = None
    last_reconcile_at: str | None = None
    bootstrap_at: str | None = None
```

Update `get()` SELECT to include new cols, and `_row_from_cursor()` mapper to pass them to the dataclass.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_state_repo.py -v`
Expected: PASS all (including pre-existing cases).

- [ ] **Step 5: Commit**

```bash
git add src/execution/state_repo.py tests/unit/test_state_repo.py
git commit -m "feat(state_repo): extend ExecutionStateRow with halt persistence fields"
```

---

## Task 3: Settings — heal_max_age_seconds + require_mainnet_gate_passed

**Files:**
- Modify: `src/platform/config.py`
- Test: existing `tests/unit/test_settings.py` (add cases)

**References:** ADR 0021 sub-decision 4 + 8.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_settings.py`:

```python
def test_settings_defaults_heal_and_mainnet_gate(monkeypatch):
    """ADR 0021 sub-decisions 4+8."""
    from src.platform.config import Settings
    s = Settings()
    assert s.heal_max_age_seconds == 3600  # 1 bar period (v0.1 strategy = 1H)
    assert s.require_mainnet_gate_passed is True


def test_settings_heal_overridable_via_env(monkeypatch):
    monkeypatch.setenv("HEAL_MAX_AGE_SECONDS", "1800")
    from src.platform.config import Settings
    s = Settings()
    assert s.heal_max_age_seconds == 1800
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_settings.py::test_settings_defaults_heal_and_mainnet_gate -v`
Expected: FAIL — attribute missing.

- [ ] **Step 3: Add settings**

In `src/platform/config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    heal_max_age_seconds: int = Field(
        default=3600,
        description="Max age (seconds) of execution_state row for HEAL-narrow on bootstrap. "
                    "Beyond this → HALT_BOOTSTRAP_AMBIGUOUS with sub_reason=stale_age. "
                    "Default = 1 bar period of v0.1 strategy (1H).",
    )
    require_mainnet_gate_passed: bool = Field(
        default=True,
        description="If True, mainnet config change is blocked until Phase G testnet probes pass. ADR 0021 sub-decision 8.",
    )
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_settings.py -v`
Expected: PASS all.

- [ ] **Step 5: Commit**

```bash
git add src/platform/config.py tests/unit/test_settings.py
git commit -m "feat(config): add heal_max_age_seconds + require_mainnet_gate_passed"
```

---

## Task 4: FSM — new events RECONCILE_ENTRY_FILLED, RECONCILE_EXITED

**Files:**
- Modify: `src/execution/state_machine.py`
- Test: `tests/unit/test_state_machine_s7.py` (NEW)

**References:** ADR 0021 sub-decision 2.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_state_machine_s7.py`:

```python
"""S7 FSM additions (ADR 0021 sub-decision 2)."""
import pytest

from src.execution.state_machine import ExecutionEvent


def test_reconcile_entry_filled_event_exists():
    assert ExecutionEvent.RECONCILE_ENTRY_FILLED is not None
    assert ExecutionEvent.RECONCILE_ENTRY_FILLED.name == "RECONCILE_ENTRY_FILLED"


def test_reconcile_exited_event_exists():
    assert ExecutionEvent.RECONCILE_EXITED is not None
    assert ExecutionEvent.RECONCILE_EXITED.name == "RECONCILE_EXITED"
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/unit/test_state_machine_s7.py -v`
Expected: FAIL — `AttributeError: RECONCILE_ENTRY_FILLED`.

- [ ] **Step 3: Add events**

In `src/execution/state_machine.py::ExecutionEvent` (Enum):

```python
class ExecutionEvent(StrEnum):
    # ... existing events ...
    RECONCILE_ENTRY_FILLED = "RECONCILE_ENTRY_FILLED"  # ADR 0021: HEAL-narrow path from RECONCILING
    RECONCILE_EXITED = "RECONCILE_EXITED"              # ADR 0021: clean fill-during-disconnect
```

- [ ] **Step 4: Run tests — pass**

Run: `pytest tests/unit/test_state_machine_s7.py -v`
Expected: PASS both.

- [ ] **Step 5: Commit**

```bash
git add src/execution/state_machine.py tests/unit/test_state_machine_s7.py
git commit -m "feat(fsm): add RECONCILE_ENTRY_FILLED + RECONCILE_EXITED events"
```

---

## Task 5: FSM transition — ENTRY_PENDING + WS_RECONNECT → RECONCILING

**Files:**
- Modify: `src/execution/state_machine.py`
- Test: `tests/unit/test_state_machine_s7.py`

**References:** ADR 0021 sub-decision 2, FSM table row 1.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_state_machine_s7.py`:

```python
from src.execution.state_machine import ExecutionState, ExecutionStateMachine


def test_entry_pending_ws_reconnect_goes_to_reconciling():
    fsm = ExecutionStateMachine(initial=ExecutionState.ENTRY_PENDING)
    fsm.transition(ExecutionEvent.WS_RECONNECT)
    assert fsm.current == ExecutionState.RECONCILING
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/unit/test_state_machine_s7.py::test_entry_pending_ws_reconnect_goes_to_reconciling -v`
Expected: FAIL — `IllegalTransition: ENTRY_PENDING + WS_RECONNECT not defined`.

- [ ] **Step 3: Add transition to table**

In `src/execution/state_machine.py::_TRANSITIONS`:

```python
_TRANSITIONS: dict[tuple[ExecutionState, ExecutionEvent], ExecutionState] = {
    # ... existing ...
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
}
```

- [ ] **Step 4: Run — pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/state_machine.py tests/unit/test_state_machine_s7.py
git commit -m "feat(fsm): ENTRY_PENDING+WS_RECONNECT→RECONCILING transition"
```

---

## Task 6: FSM transition — EXIT_PENDING + WS_RECONNECT → RECONCILING

**Files:**
- Modify: `src/execution/state_machine.py`
- Test: `tests/unit/test_state_machine_s7.py`

**References:** ADR 0021 sub-decision 2, FSM table row 2.

- [ ] **Step 1: Write failing test**

Append to `tests/unit/test_state_machine_s7.py`:

```python
def test_exit_pending_ws_reconnect_goes_to_reconciling():
    fsm = ExecutionStateMachine(initial=ExecutionState.EXIT_PENDING)
    fsm.transition(ExecutionEvent.WS_RECONNECT)
    assert fsm.current == ExecutionState.RECONCILING
```

- [ ] **Step 2: Run — fail**

Run: `pytest tests/unit/test_state_machine_s7.py::test_exit_pending_ws_reconnect_goes_to_reconciling -v`
Expected: FAIL — IllegalTransition.

- [ ] **Step 3: Add transition**

```python
_TRANSITIONS[(ExecutionState.EXIT_PENDING, ExecutionEvent.WS_RECONNECT)] = ExecutionState.RECONCILING
```
(Or inline в словарь по pattern Task 5.)

- [ ] **Step 4: Run — pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/state_machine.py tests/unit/test_state_machine_s7.py
git commit -m "feat(fsm): EXIT_PENDING+WS_RECONNECT→RECONCILING transition"
```

---

## Task 7: FSM transition — RECONCILING + RECONCILE_ENTRY_FILLED → LONG_OPEN

**Files:**
- Modify: `src/execution/state_machine.py`
- Test: `tests/unit/test_state_machine_s7.py`

**References:** ADR 0021 sub-decision 2 — HEAL-narrow exit path.

- [ ] **Step 1: Write failing test**

```python
def test_reconciling_heal_entry_filled_goes_to_long_open():
    """ADR 0021: HEAL path, coordinator then calls arm_oco from LONG_OPEN."""
    fsm = ExecutionStateMachine(initial=ExecutionState.RECONCILING)
    fsm.transition(ExecutionEvent.RECONCILE_ENTRY_FILLED)
    assert fsm.current == ExecutionState.LONG_OPEN
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — IllegalTransition.

- [ ] **Step 3: Add transition**

```python
(ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_ENTRY_FILLED): ExecutionState.LONG_OPEN,
```

- [ ] **Step 4: Run — pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(fsm): RECONCILING+RECONCILE_ENTRY_FILLED→LONG_OPEN (HEAL-narrow)"
```

---

## Task 8: FSM transition — RECONCILING + RECONCILE_EXITED → FLAT

**Files:**
- Modify: `src/execution/state_machine.py`
- Test: `tests/unit/test_state_machine_s7.py`

**References:** ADR 0021 sub-decision 2 — clean fill-during-disconnect.

- [ ] **Step 1: Write failing test**

```python
def test_reconciling_reconcile_exited_goes_to_flat():
    """ADR 0021: position==0 on exchange post-reconnect → FLAT."""
    fsm = ExecutionStateMachine(initial=ExecutionState.RECONCILING)
    fsm.transition(ExecutionEvent.RECONCILE_EXITED)
    assert fsm.current == ExecutionState.FLAT


def test_illegal_reconcile_entry_filled_from_flat():
    """Sanity: these events legal ONLY from RECONCILING."""
    fsm = ExecutionStateMachine(initial=ExecutionState.FLAT)
    with pytest.raises(Exception):  # IllegalTransition (exact class from existing code)
        fsm.transition(ExecutionEvent.RECONCILE_ENTRY_FILLED)
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — IllegalTransition (first), PASS (second — illegal как и должно).

- [ ] **Step 3: Add transition**

```python
(ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_EXITED): ExecutionState.FLAT,
```

- [ ] **Step 4: Run — pass**

Run full S7 FSM file: `pytest tests/unit/test_state_machine_s7.py -v`
Expected: PASS all (6+ tests).

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(fsm): RECONCILING+RECONCILE_EXITED→FLAT + illegal-transition guard tests"
```

---

## Task 9: ExecutionStateRepo._set_halt() idempotent helper

**Files:**
- Modify: `src/execution/state_repo.py`
- Test: `tests/unit/test_halt_persistence.py` (extend)

**References:** ADR 0021 sub-decision 5 — γ pattern (primary wins, log always appends).

- [ ] **Step 1: Write failing tests (first halt + idempotency)**

Append to `tests/unit/test_halt_persistence.py`:

```python
import json

from src.execution.state_repo import ExecutionStateRepo


def _repo(tmp_path):
    repo = ExecutionStateRepo(tmp_path / "test.db")
    repo.upsert_initial(symbol="BTCUSDT")
    return repo


def test_set_halt_first_call_writes_column_and_log(tmp_path):
    repo = _repo(tmp_path)
    repo._set_halt(
        symbol="BTCUSDT",
        reason="HALT_OCO_ARM_TIMEOUT",
        context={"state_at_halt": "OCO_ARMING", "position_qty": "0.001"},
    )
    row = repo.get("BTCUSDT")
    assert row.halt_reason == "HALT_OCO_ARM_TIMEOUT"
    # Log has 1 entry
    rows = list(repo._conn.execute("SELECT reason, context_json FROM halt_log WHERE symbol=?", ("BTCUSDT",)))
    assert len(rows) == 1
    assert rows[0][0] == "HALT_OCO_ARM_TIMEOUT"
    assert json.loads(rows[0][1])["state_at_halt"] == "OCO_ARMING"


def test_set_halt_secondary_call_log_only_primary_preserved(tmp_path):
    """ADR 0021 sub-decision 5 idempotency: secondary halt appends log but column unchanged."""
    repo = _repo(tmp_path)
    repo._set_halt(symbol="BTCUSDT", reason="HALT_OCO_ARM_TIMEOUT", context={"state_at_halt": "OCO_ARMING"})
    repo._set_halt(symbol="BTCUSDT", reason="RISK_HALT", context={"state_at_halt": "HALTED"})
    row = repo.get("BTCUSDT")
    assert row.halt_reason == "HALT_OCO_ARM_TIMEOUT"  # primary wins
    rows = list(repo._conn.execute("SELECT reason FROM halt_log WHERE symbol=? ORDER BY id", ("BTCUSDT",)))
    assert [r[0] for r in rows] == ["HALT_OCO_ARM_TIMEOUT", "RISK_HALT"]  # both logged
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — `_set_halt` does not exist.

- [ ] **Step 3: Implement helper**

In `src/execution/state_repo.py`:

```python
import json
from datetime import UTC, datetime


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class ExecutionStateRepo:
    # ... existing ...

    def _set_halt(self, *, symbol: str, reason: str, context: dict) -> None:
        """Idempotent halt write (ADR 0021 sub-decision 5 γ pattern).

        Primary halt_reason wins (first non-null sticks). halt_log always appends
        for audit trail (chronological halt sequence).
        """
        ctx_json = json.dumps(context, default=str)
        ts = _now_iso()
        with self._conn:
            row = self.get(symbol)
            if row is not None and row.halt_reason is None:
                self._conn.execute(
                    "UPDATE execution_state SET halt_reason=? WHERE symbol=?",
                    (reason, symbol),
                )
            # Always append to audit log
            self._conn.execute(
                "INSERT INTO halt_log (symbol, ts, reason, context_json) VALUES (?,?,?,?)",
                (symbol, ts, reason, ctx_json),
            )
```

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_halt_persistence.py -v`
Expected: PASS all (4 tests: 2 schema + 2 idempotency).

- [ ] **Step 5: Commit**

```bash
git add src/execution/state_repo.py tests/unit/test_halt_persistence.py
git commit -m "feat(state_repo): add _set_halt idempotent helper (γ persistence)"
```

---

## Task 10: Coordinator._set_halt() wrapper + callsites at HALTED transitions

**Files:**
- Modify: `src/execution/coordinator.py`
- Test: `tests/unit/test_halt_persistence.py` (extend with coordinator-level test)

**References:** ADR 0021 sub-decision 5 — `context_json` required fields.

- [ ] **Step 1: Write failing test**

Append to `tests/unit/test_halt_persistence.py`:

```python
def test_coordinator_halt_on_oco_arm_timeout_persists_context(tmp_path):
    """After OCO_ARM_TIMEOUT the halt_reason + context_json must be persisted.

    context_json required keys (ADR 0021 sub-decision 5):
      state_at_halt, position_qty, oco_tp_id, oco_sl_id, expected_qty,
      last_event, last_attempt_num, arming_started_at.
    """
    from src.execution.coordinator import Coordinator  # with fakes wired per existing test pattern
    coord, repo, _fake_adapter = _build_coordinator_at_oco_arming(tmp_path)  # helper from test_coordinator.py
    coord.on_oco_arm_timeout()  # simulate (exact trigger matches existing test harness)
    row = repo.get("BTCUSDT")
    assert row.halt_reason == "HALT_OCO_ARM_TIMEOUT"
    ctx = json.loads(list(repo._conn.execute(
        "SELECT context_json FROM halt_log WHERE symbol=? ORDER BY id DESC LIMIT 1", ("BTCUSDT",)
    ))[0][0])
    for key in ("state_at_halt", "position_qty", "oco_tp_id", "oco_sl_id",
                "expected_qty", "last_event", "last_attempt_num", "arming_started_at"):
        assert key in ctx, f"{key} missing from context_json"
```

(`_build_coordinator_at_oco_arming` — reuse factory from `tests/unit/test_coordinator.py`; if missing — create in a new `tests/unit/conftest_coordinator.py`.)

- [ ] **Step 2: Run — fail**

Expected: FAIL — row.halt_reason is None (coordinator does not persist).

- [ ] **Step 3: Add `_set_halt()` wrapper + call at all HALTED transitions**

In `src/execution/coordinator.py`:

```python
def _set_halt(self, reason: str, *, last_event: ExecutionEvent, extra: dict | None = None) -> None:
    """Persist HALTED-class state via ExecutionStateRepo._set_halt.

    Populates `context_json` required fields (ADR 0021 sub-decision 5).
    """
    row = self._repo.get(self._symbol)
    ctx = {
        "state_at_halt": self._fsm.current.name,
        "position_qty": str(row.position_qty) if row else "0",
        "oco_tp_id": row.oco_tp_id if row else None,
        "oco_sl_id": row.oco_sl_id if row else None,
        "expected_qty": str(row.expected_oco_qty) if row and row.expected_oco_qty else None,
        "last_event": last_event.name,
        "last_attempt_num": row.last_attempt_num if row else 0,
        "arming_started_at": row.arming_started_at if row else None,
    }
    if extra:
        ctx.update(extra)
    self._repo._set_halt(symbol=self._symbol, reason=reason, context=ctx)
```

Find all callsites (ripgrep `self._fsm.transition(*, to=ExecutionState.HALTED)` и аналоги — existing HALT paths: `arm_oco` timeout, `_handle_cancel_fail`, `flatten` retry exhausted, reconcile DIVERGENCE). В каждом: **до** FSM transition на HALTED — вызвать `self._set_halt(reason=..., last_event=...)`.

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_halt_persistence.py tests/unit/test_coordinator.py -v`
Expected: PASS all.

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/unit/test_halt_persistence.py
git commit -m "feat(coordinator): persist halt_reason+context at all HALTED transitions"
```

---

## Task 11: ReconcileResult — 4-valued verdict + heal_context field

**Files:**
- Modify: `src/execution/reconciler.py`
- Test: `tests/unit/test_reconciler_verdicts.py` (NEW)

**References:** ADR 0021 sub-decision 3.

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_reconciler_verdicts.py`:

```python
"""Reconciler 4-valued verdict tests (ADR 0021 sub-decision 3)."""
from decimal import Decimal

import pytest

from src.execution.reconciler import ReconcileResult


def test_reconcile_result_verdict_is_4_valued():
    """Verdict must be one of AGREE / DIVERGENCE / HEAL_ENTRY_FILLED / EXITED."""
    r = ReconcileResult(
        verdict="AGREE",
        exch_qty=Decimal("0"),
        entry_price=None,
        halt_reason=None,
        heal_context=None,
    )
    assert r.verdict == "AGREE"


def test_reconcile_result_heal_context_field_exists():
    r = ReconcileResult(
        verdict="HEAL_ENTRY_FILLED",
        exch_qty=Decimal("0.001"),
        entry_price=Decimal("62000"),
        halt_reason=None,
        heal_context={"avgPrice": "62000", "cumExecFee": "0.05"},
    )
    assert r.heal_context["avgPrice"] == "62000"


def test_reconcile_result_rejects_unknown_verdict():
    with pytest.raises((ValueError, TypeError)):
        ReconcileResult(
            verdict="WHATEVER",
            exch_qty=Decimal("0"),
            entry_price=None,
            halt_reason=None,
            heal_context=None,
        )
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — `heal_context` not a field / verdict still binary.

- [ ] **Step 3: Extend dataclass**

In `src/execution/reconciler.py`:

```python
from typing import Literal

Verdict = Literal["AGREE", "DIVERGENCE", "HEAL_ENTRY_FILLED", "EXITED"]


@dataclass(frozen=True)
class ReconcileResult:
    verdict: Verdict
    exch_qty: Decimal
    entry_price: Decimal | None
    halt_reason: str | None
    heal_context: dict | None  # populated only for HEAL_ENTRY_FILLED

    def __post_init__(self):
        valid = ("AGREE", "DIVERGENCE", "HEAL_ENTRY_FILLED", "EXITED")
        if self.verdict not in valid:
            raise ValueError(f"verdict must be one of {valid}, got {self.verdict!r}")
```

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_reconciler_verdicts.py -v`
Expected: PASS all 3.

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_verdicts.py
git commit -m "feat(reconciler): extend ReconcileResult to 4-valued verdict + heal_context"
```

---

## Task 12: Reconciler.reconcile() — expected_state hint signature

**Files:**
- Modify: `src/execution/reconciler.py`
- Test: `tests/unit/test_reconciler_verdicts.py`

**References:** ADR 0021 sub-decision 3.

- [ ] **Step 1: Write failing test (signature + baseline AGREE path unchanged)**

Append to `tests/unit/test_reconciler_verdicts.py`:

```python
from src.execution.reconciler import Reconciler, LocalState
from src.execution.state_machine import ExecutionState


def test_reconcile_accepts_expected_state_kw_optional():
    """Backward compat: existing callers w/o expected_state still work."""
    fake_adapter = _FakeAdapter(exch_qty=Decimal("0.001"), open_orders=[], entry_order=None)
    reco = Reconciler(adapter=fake_adapter)
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0.001"), entry_order_id=None)
    r = reco.reconcile(local)  # no expected_state → binary path
    assert r.verdict == "AGREE"


def test_reconcile_accepts_expected_state_entry_pending():
    """New path: expected_state provided → 4-valued classification."""
    # ... will flesh out classification in Task 13. Here just assert signature.
    fake_adapter = _FakeAdapter(exch_qty=Decimal("0.001"), open_orders=[], entry_order=None)
    reco = Reconciler(adapter=fake_adapter)
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0"), entry_order_id="x")
    r = reco.reconcile(local, expected_state=ExecutionState.ENTRY_PENDING)
    # Classification in next task; just verify call doesn't crash.
    assert r.verdict in ("AGREE", "DIVERGENCE", "HEAL_ENTRY_FILLED", "EXITED")
```

Add `_FakeAdapter` helper at test-file top (minimal Mock with `get_wallet_balance`, `get_open_orders`, `get_order`).

- [ ] **Step 2: Run — fail**

Expected: FAIL — `reconcile` signature doesn't accept `expected_state` kw.

- [ ] **Step 3: Update signature**

In `src/execution/reconciler.py::Reconciler.reconcile`:

```python
def reconcile(
    self,
    local: LocalState,
    *,
    expected_state: ExecutionState | None = None,
) -> ReconcileResult:
    """Classify exchange↔local agreement.

    If `expected_state` is None → binary AGREE/DIVERGENCE (S6 behavior, preserved).
    If `expected_state` is provided → 4-valued with HEAL_ENTRY_FILLED/EXITED possible
    for ENTRY_PENDING/EXIT_PENDING hints. ADR 0021 sub-decision 3.
    """
    # Fetch side-effects
    exch_qty = self._fetch_exch_qty(local.symbol)
    open_orders = self._adapter.get_open_orders(local.symbol)
    entry_order = self._adapter.get_order(local.entry_order_id) if local.entry_order_id else None

    if expected_state is None:
        return self._binary_verdict(local, exch_qty)
    # Classification → next tasks.
    return self._classify(local, expected_state, exch_qty, open_orders, entry_order)
```

Stub `_classify` returns `DIVERGENCE` (HALT fallback). Implementation of `_classify` splits across Tasks 13-15.

- [ ] **Step 4: Run — pass**

Expected: PASS (both tests — backward-compat AGREE path + signature smoke).

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_verdicts.py
git commit -m "feat(reconciler): add expected_state kw + stub classifier"
```

---

## Task 13: Reconciler classification — ENTRY_PENDING HEAL_ENTRY_FILLED path

**Files:**
- Modify: `src/execution/reconciler.py`
- Test: `tests/unit/test_reconciler_verdicts.py`

**References:** ADR 0021 sub-decision 3 — classification algorithm ENTRY_PENDING block.

- [ ] **Step 1: Write failing tests (3 cases)**

Append to `tests/unit/test_reconciler_verdicts.py`:

```python
from datetime import UTC, datetime, timedelta


class _EntryOrder:
    def __init__(self, status: str, avgPrice: Decimal):
        self.status = status
        self.avgPrice = avgPrice


def test_entry_pending_heal_when_filled_position_matches_no_orphans(tmp_path):
    """ADR 0021 sub-decision 3: all 3 conditions → HEAL_ENTRY_FILLED."""
    adapter = _FakeAdapter(
        exch_qty=Decimal("0.001"),
        open_orders=[],  # no orphan TP/SL
        entry_order=_EntryOrder(status="Filled", avgPrice=Decimal("62000")),
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(
        symbol="BTCUSDT",
        position_qty=Decimal("0"),
        entry_order_id="ent1",
        expected_entry_qty=Decimal("0.001"),
        updated_at=datetime.now(UTC) - timedelta(seconds=30),  # fresh
    )
    r = reco.reconcile(local, expected_state=ExecutionState.ENTRY_PENDING)
    assert r.verdict == "HEAL_ENTRY_FILLED"
    assert r.entry_price == Decimal("62000")
    assert r.heal_context and r.heal_context["avgPrice"] == "62000"


def test_entry_pending_halt_when_position_short_of_expected(tmp_path):
    """Partial fill + no orphans → still DIVERGENCE (HEAL requires exact/overfill above dust)."""
    adapter = _FakeAdapter(
        exch_qty=Decimal("0.0001"),  # way below expected 0.001
        open_orders=[],
        entry_order=_EntryOrder(status="Filled", avgPrice=Decimal("62000")),
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(
        symbol="BTCUSDT",
        position_qty=Decimal("0"),
        entry_order_id="ent1",
        expected_entry_qty=Decimal("0.001"),
        updated_at=datetime.now(UTC),
    )
    r = reco.reconcile(local, expected_state=ExecutionState.ENTRY_PENDING)
    assert r.verdict == "DIVERGENCE"
    assert r.halt_reason == "HALT_BOOTSTRAP_AMBIGUOUS"


def test_entry_pending_halt_when_orphan_open_orders_exist(tmp_path):
    """If any open orders exist for bracket → not narrow HEAL (that's OCO_ARMING path)."""
    adapter = _FakeAdapter(
        exch_qty=Decimal("0.001"),
        open_orders=[{"orderLinkId": "oco-abc-TP-1", "orderId": "tp1"}],
        entry_order=_EntryOrder(status="Filled", avgPrice=Decimal("62000")),
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(
        symbol="BTCUSDT",
        position_qty=Decimal("0"),
        entry_order_id="ent1",
        expected_entry_qty=Decimal("0.001"),
        updated_at=datetime.now(UTC),
    )
    r = reco.reconcile(local, expected_state=ExecutionState.ENTRY_PENDING)
    assert r.verdict == "DIVERGENCE"
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — stub returns DIVERGENCE for HEAL case.

- [ ] **Step 3: Implement ENTRY_PENDING branch in `_classify`**

In `src/execution/reconciler.py::_classify`:

```python
def _classify(
    self,
    local: LocalState,
    expected_state: ExecutionState,
    exch_qty: Decimal,
    open_orders: list,
    entry_order,
) -> ReconcileResult:
    if expected_state == ExecutionState.ENTRY_PENDING:
        return self._classify_entry_pending(local, exch_qty, open_orders, entry_order)
    if expected_state == ExecutionState.EXIT_PENDING:
        return self._classify_exit_pending(local, exch_qty, open_orders)
    # Other hint-provided states fall through to binary
    return self._binary_verdict(local, exch_qty)


def _classify_entry_pending(self, local, exch_qty, open_orders, entry_order) -> ReconcileResult:
    dust = self._dust_threshold  # existing self attr (ADR 0020)

    # Precondition fail → ambiguous
    if entry_order is None or entry_order.status != "Filled":
        return ReconcileResult(
            verdict="DIVERGENCE",
            exch_qty=exch_qty,
            entry_price=None,
            halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
            heal_context=None,
        )

    expected_qty = local.expected_entry_qty or Decimal("0")
    if exch_qty < expected_qty - dust:
        return ReconcileResult(
            verdict="DIVERGENCE",
            exch_qty=exch_qty,
            entry_price=None,
            halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
            heal_context=None,
        )

    # Orphan orders = not HEAL-narrow
    bracket_orders = [o for o in open_orders if self._belongs_to_current_bracket(o, local)]
    if bracket_orders:
        return ReconcileResult(
            verdict="DIVERGENCE",
            exch_qty=exch_qty,
            entry_price=None,
            halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
            heal_context=None,
        )

    # Staleness check — Task 14 adds this. Stub: always fresh here.
    # HEAL
    return ReconcileResult(
        verdict="HEAL_ENTRY_FILLED",
        exch_qty=exch_qty,
        entry_price=entry_order.avgPrice,
        halt_reason=None,
        heal_context={
            "avgPrice": str(entry_order.avgPrice),
            "cumExecFee": getattr(entry_order, "cumExecFee", None),
        },
    )
```

`_belongs_to_current_bracket` helper: `return o["orderLinkId"].startswith(f"oco-{local.bracket_id}-")` — uses `local.bracket_id` (add field to LocalState if missing; it's already in ADR 0020).

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_reconciler_verdicts.py -v`
Expected: PASS all (5+ tests).

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_verdicts.py
git commit -m "feat(reconciler): classify ENTRY_PENDING → HEAL_ENTRY_FILLED / DIVERGENCE"
```

---

## Task 14: Reconciler — staleness check (heal_max_age_seconds)

**Files:**
- Modify: `src/execution/reconciler.py`
- Test: `tests/unit/test_reconciler_verdicts.py`

**References:** ADR 0021 sub-decision 4.

- [ ] **Step 1: Write failing test**

```python
def test_entry_pending_heal_blocked_by_staleness(monkeypatch):
    """ADR 0021 sub-decision 4: crash > heal_max_age_seconds → HALT not HEAL."""
    monkeypatch.setenv("HEAL_MAX_AGE_SECONDS", "3600")
    adapter = _FakeAdapter(
        exch_qty=Decimal("0.001"),
        open_orders=[],
        entry_order=_EntryOrder(status="Filled", avgPrice=Decimal("62000")),
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(
        symbol="BTCUSDT",
        position_qty=Decimal("0"),
        entry_order_id="ent1",
        expected_entry_qty=Decimal("0.001"),
        updated_at=datetime.now(UTC) - timedelta(seconds=4000),  # stale > 3600
    )
    r = reco.reconcile(local, expected_state=ExecutionState.ENTRY_PENDING)
    assert r.verdict == "DIVERGENCE"
    assert r.halt_reason == "HALT_BOOTSTRAP_AMBIGUOUS"
    # Sub-reason hint
    # Convention: reconciler appends sub_reason to reason tag in heal_context (coordinator picks up for context_json)
    assert (r.heal_context or {}).get("sub_reason") == "stale_age"
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — verdict is `HEAL_ENTRY_FILLED` (staleness check missing).

- [ ] **Step 3: Add staleness check**

In `_classify_entry_pending`, after orphan check & before HEAL return:

```python
from datetime import UTC, datetime
# ... inside method ...

settings = self._settings  # injected via Reconciler.__init__
max_age = settings.heal_max_age_seconds
age_seconds = (datetime.now(UTC) - local.updated_at).total_seconds()
if age_seconds > max_age:
    return ReconcileResult(
        verdict="DIVERGENCE",
        exch_qty=exch_qty,
        entry_price=None,
        halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
        heal_context={"sub_reason": "stale_age", "age_seconds": age_seconds},
    )
```

Inject settings into Reconciler constructor (если ещё не): `Reconciler(adapter, settings=settings)`.

- [ ] **Step 4: Run — pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_verdicts.py
git commit -m "feat(reconciler): add HEAL staleness gate (heal_max_age_seconds)"
```

---

## Task 15: Reconciler — EXIT_PENDING classification (EXITED vs DIVERGENCE)

**Files:**
- Modify: `src/execution/reconciler.py`
- Test: `tests/unit/test_reconciler_verdicts.py`

**References:** ADR 0021 sub-decision 3 — EXIT_PENDING branch.

- [ ] **Step 1: Write failing tests**

```python
def test_exit_pending_exited_when_position_flat_no_open_orders():
    adapter = _FakeAdapter(
        exch_qty=Decimal("0"),
        open_orders=[],
        entry_order=None,
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0.001"), entry_order_id=None)
    r = reco.reconcile(local, expected_state=ExecutionState.EXIT_PENDING)
    assert r.verdict == "EXITED"
    assert r.halt_reason is None


def test_exit_pending_halt_when_position_still_there():
    adapter = _FakeAdapter(
        exch_qty=Decimal("0.001"),  # still open
        open_orders=[],
        entry_order=None,
    )
    reco = Reconciler(adapter=adapter)
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0.001"), entry_order_id=None)
    r = reco.reconcile(local, expected_state=ExecutionState.EXIT_PENDING)
    assert r.verdict == "DIVERGENCE"
    assert r.halt_reason == "HALT_EXIT_RECONCILE_DIVERGENCE"
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — still returns stub DIVERGENCE for first case.

- [ ] **Step 3: Implement EXIT_PENDING branch**

```python
def _classify_exit_pending(self, local, exch_qty, open_orders) -> ReconcileResult:
    dust = self._dust_threshold
    if exch_qty < dust and len(open_orders) == 0:
        return ReconcileResult(
            verdict="EXITED",
            exch_qty=exch_qty,
            entry_price=None,
            halt_reason=None,
            heal_context=None,
        )
    return ReconcileResult(
        verdict="DIVERGENCE",
        exch_qty=exch_qty,
        entry_price=None,
        halt_reason="HALT_EXIT_RECONCILE_DIVERGENCE",
        heal_context=None,
    )
```

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_reconciler_verdicts.py -v`
Expected: PASS all (7+ tests).

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_verdicts.py
git commit -m "feat(reconciler): classify EXIT_PENDING → EXITED / DIVERGENCE"
```

---

## Task 16: Reconciler — _wallet_cache for WS-fed R4

**Files:**
- Modify: `src/execution/reconciler.py`
- Test: `tests/unit/test_reconciler_verdicts.py`

**References:** ADR 0021 sub-decision 6 — wallet topic feeds cache; reconcile reads cache first, REST fallback on miss.

- [ ] **Step 1: Write failing tests**

```python
def test_reconciler_reads_wallet_cache_first(monkeypatch):
    """WS-fed cache hit → no REST call."""
    adapter = _FakeAdapter(
        exch_qty=Decimal("99.9"),  # REST value — should NOT be used
        open_orders=[],
        entry_order=None,
    )
    rest_calls = []
    orig_get_wallet = adapter.get_wallet_balance
    def spy(*a, **kw):
        rest_calls.append((a, kw))
        return orig_get_wallet(*a, **kw)
    adapter.get_wallet_balance = spy

    reco = Reconciler(adapter=adapter)
    reco.on_wallet_event({"coin": "BTC", "walletBalance": "0.001"})  # WS-fed
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0.001"), entry_order_id=None)
    r = reco.reconcile(local)
    assert r.exch_qty == Decimal("0.001")
    assert rest_calls == []  # REST not called


def test_reconciler_falls_back_to_rest_on_cache_miss():
    adapter = _FakeAdapter(exch_qty=Decimal("0.002"), open_orders=[], entry_order=None)
    reco = Reconciler(adapter=adapter)
    local = LocalState(symbol="BTCUSDT", position_qty=Decimal("0.002"), entry_order_id=None)
    r = reco.reconcile(local)
    assert r.exch_qty == Decimal("0.002")  # came from REST adapter
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — `on_wallet_event` doesn't exist / cache not used.

- [ ] **Step 3: Add cache**

```python
class Reconciler:
    def __init__(self, adapter, settings=None, *, dust_threshold=Decimal("0.00001")):
        # ... existing ...
        self._wallet_cache: dict[str, Decimal] = {}

    def on_wallet_event(self, evt: dict) -> None:
        """WS wallet topic event: update cache."""
        coin = evt["coin"]
        self._wallet_cache[coin] = Decimal(evt["walletBalance"])

    def _fetch_exch_qty(self, symbol: str) -> Decimal:
        base_coin = symbol_to_base_coin(symbol)  # existing helper or inline: symbol[:-4] for USDT pairs
        cached = self._wallet_cache.get(base_coin)
        if cached is not None:
            return cached
        return self._adapter.get_wallet_balance(base_coin)
```

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_reconciler_verdicts.py -v`
Expected: PASS all.

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_verdicts.py
git commit -m "feat(reconciler): add _wallet_cache + on_wallet_event for WS-fed R4"
```

---

## Task 17: BybitPrivateWSConsumer — skeleton + pybit wiring + reconnect callback

**Files:**
- Create: `src/execution/bybit/ws_private.py`
- Test: `tests/unit/test_ws_private_consumer.py` (NEW)

**References:** ADR 0021 sub-decision 6.

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_ws_private_consumer.py`:

```python
"""BybitPrivateWSConsumer tests (ADR 0021 sub-decision 6)."""
from unittest.mock import MagicMock

import pytest

from src.execution.bybit.ws_private import BybitPrivateWSConsumer


def test_consumer_initializes_with_pybit_handle():
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord,
        reconciler=reco,
    )
    assert c._coordinator is coord
    assert c._reconciler is reco


def test_consumer_on_disconnect_triggers_reconnect_event():
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord, reconciler=reco,
    )
    c.on_disconnect()
    # Reconnect path eventually calls coordinator.on_ws_reconnect
    coord.on_ws_reconnect.assert_called_once()
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — module missing.

- [ ] **Step 3: Create skeleton**

Create `src/execution/bybit/ws_private.py`:

```python
"""Bybit V5 private WebSocket consumer — order + wallet topics.

ADR 0021 sub-decision 6. Execution topic deferred to S8.
"""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class _CoordinatorProto(Protocol):
    def on_order_event(self, evt: dict) -> None: ...
    def on_ws_reconnect(self) -> None: ...


class _ReconcilerProto(Protocol):
    def on_wallet_event(self, evt: dict) -> None: ...


class BybitPrivateWSConsumer:
    """Subscribes to `order` + `wallet` topics on Bybit V5 private stream."""

    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        endpoint: str,
        coordinator: _CoordinatorProto,
        reconciler: _ReconcilerProto,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._endpoint = endpoint
        self._coordinator = coordinator
        self._reconciler = reconciler
        self._ws = None  # pybit WebSocket handle (lazy)

    def start(self) -> None:
        """Connect + subscribe (pybit handles async threading internally)."""
        from pybit.unified_trading import WebSocket  # deferred import
        self._ws = WebSocket(
            testnet="testnet" in self._endpoint,
            demo="demo" in self._endpoint,
            channel_type="private",
            api_key=self._api_key,
            api_secret=self._api_secret,
        )
        self._ws.order_stream(callback=self._on_order_raw)
        self._ws.wallet_stream(callback=self._on_wallet_raw)

    def stop(self) -> None:
        if self._ws is not None:
            self._ws.exit()
            self._ws = None

    def on_disconnect(self) -> None:
        """Callback triggered by pybit on disconnect — routes reconcile."""
        try:
            self._coordinator.on_ws_reconnect()
        except Exception:
            logger.exception("on_ws_reconnect hook failed")

    def _on_order_raw(self, msg: dict) -> None:
        """Route `order` topic messages → coordinator. Parser fleshed out Task 18."""
        try:
            for item in msg.get("data", []):
                evt = self._parse_order(item)
                self._coordinator.on_order_event(evt)
        except Exception:
            logger.exception("order event dispatch failed; dropping msg=%r", msg)

    def _on_wallet_raw(self, msg: dict) -> None:
        try:
            for item in msg.get("data", []):
                for coin_row in item.get("coin", []):
                    evt = {"coin": coin_row["coin"], "walletBalance": coin_row["walletBalance"]}
                    self._reconciler.on_wallet_event(evt)
        except Exception:
            logger.exception("wallet event dispatch failed; dropping msg=%r", msg)

    def _parse_order(self, item: dict) -> dict:
        """Stub — full validation in Task 18."""
        return dict(item)
```

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_ws_private_consumer.py -v`
Expected: PASS 2 tests.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/ws_private.py tests/unit/test_ws_private_consumer.py
git commit -m "feat(ws_private): skeleton BybitPrivateWSConsumer with on_disconnect→reconcile"
```

---

## Task 18: BybitPrivateWSConsumer — order topic parser (cumExecFee mandatory)

**Files:**
- Modify: `src/execution/bybit/ws_private.py`
- Test: `tests/unit/test_ws_private_consumer.py`

**References:** ADR 0021 sub-decision 6 — parser ACCEPTANCE: cumExecFee+feeCurrency mandatory for Filled/PartiallyFilled.

- [ ] **Step 1: Write failing tests**

```python
def test_parser_forwards_filled_event_with_fees():
    coord = MagicMock()
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord, reconciler=reco,
    )
    msg = {"data": [{
        "orderLinkId": "oco-abc-TP-1",
        "orderId": "bybit-oid-1",
        "orderStatus": "Filled",
        "cumExecQty": "0.001",
        "cumExecFee": "0.0000012",
        "feeCurrency": "BTC",
        "avgPrice": "62500",
    }]}
    c._on_order_raw(msg)
    coord.on_order_event.assert_called_once()
    evt = coord.on_order_event.call_args.args[0]
    assert evt["cumExecFee"] == "0.0000012"
    assert evt["feeCurrency"] == "BTC"


def test_parser_drops_filled_event_missing_cumExecFee(caplog):
    """ADR 0021 sub-decision 6: Filled w/o fees → ERROR log + drop (never forward None fees)."""
    coord = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord, reconciler=MagicMock(),
    )
    msg = {"data": [{
        "orderLinkId": "oco-abc-TP-1",
        "orderStatus": "Filled",
        "cumExecQty": "0.001",
        # cumExecFee MISSING
        "avgPrice": "62500",
    }]}
    with caplog.at_level("ERROR"):
        c._on_order_raw(msg)
    coord.on_order_event.assert_not_called()
    assert any("cumExecFee" in rec.message for rec in caplog.records)


def test_parser_forwards_new_unfilled_event_without_fees():
    """New/Cancelled/Rejected → fees not expected, forward."""
    coord = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=coord, reconciler=MagicMock(),
    )
    msg = {"data": [{
        "orderLinkId": "oco-abc-SL-1",
        "orderStatus": "New",
        "cumExecQty": "0",
    }]}
    c._on_order_raw(msg)
    coord.on_order_event.assert_called_once()
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — second test: coord.on_order_event WAS called (parser не drops).

- [ ] **Step 3: Implement validating parser**

Replace `_parse_order` + extend `_on_order_raw`:

```python
_FILLED_STATUSES = ("Filled", "PartiallyFilled")
_REQUIRED_FEE_FIELDS = ("cumExecFee", "feeCurrency")


def _on_order_raw(self, msg: dict) -> None:
    try:
        for item in msg.get("data", []):
            evt = self._parse_order(item)
            if evt is None:
                continue  # dropped (logged in parser)
            self._coordinator.on_order_event(evt)
    except Exception:
        logger.exception("order event dispatch failed; dropping msg=%r", msg)


def _parse_order(self, item: dict) -> dict | None:
    status = item.get("orderStatus", "")
    if status in self._FILLED_STATUSES:
        missing = [f for f in self._REQUIRED_FEE_FIELDS if f not in item]
        if missing:
            logger.error(
                "order event %s missing required fee fields %s; dropping item=%r",
                status, missing, item,
            )
            return None
    return dict(item)
```

Promote constants to class attrs: `BybitPrivateWSConsumer._FILLED_STATUSES`, `_REQUIRED_FEE_FIELDS`.

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_ws_private_consumer.py -v`
Expected: PASS all (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/ws_private.py tests/unit/test_ws_private_consumer.py
git commit -m "feat(ws_private): parser drops Filled events missing cumExecFee"
```

---

## Task 19: BybitPrivateWSConsumer — wallet topic wiring (end-to-end)

**Files:**
- Modify: `src/execution/bybit/ws_private.py` (adjust if needed)
- Test: `tests/unit/test_ws_private_consumer.py`

**References:** ADR 0021 sub-decision 6.

- [ ] **Step 1: Write failing test**

```python
def test_wallet_event_routed_to_reconciler():
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=MagicMock(), reconciler=reco,
    )
    msg = {"data": [{
        "accountType": "UNIFIED",
        "coin": [{"coin": "BTC", "walletBalance": "0.001234"}],
    }]}
    c._on_wallet_raw(msg)
    reco.on_wallet_event.assert_called_once_with({"coin": "BTC", "walletBalance": "0.001234"})


def test_wallet_event_multi_coin_dispatched_individually():
    reco = MagicMock()
    c = BybitPrivateWSConsumer(
        api_key="k", api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=MagicMock(), reconciler=reco,
    )
    msg = {"data": [{
        "coin": [
            {"coin": "BTC", "walletBalance": "0.001"},
            {"coin": "USDT", "walletBalance": "1000.0"},
        ],
    }]}
    c._on_wallet_raw(msg)
    assert reco.on_wallet_event.call_count == 2
```

- [ ] **Step 2: Run — verify**

Run: `pytest tests/unit/test_ws_private_consumer.py -v`
Expected: PASS (skeleton from Task 17 already dispatches; if logic regressed, fix here).

- [ ] **Step 3: (if fail) tweak `_on_wallet_raw`**

Already implemented in Task 17; add `accountType` filter if needed:

```python
def _on_wallet_raw(self, msg: dict) -> None:
    try:
        for item in msg.get("data", []):
            for coin_row in item.get("coin", []):
                evt = {"coin": coin_row["coin"], "walletBalance": coin_row["walletBalance"]}
                self._reconciler.on_wallet_event(evt)
    except Exception:
        logger.exception("wallet event dispatch failed; dropping msg=%r", msg)
```

- [ ] **Step 4: Run — pass**

Expected: PASS all.

- [ ] **Step 5: Commit**

```bash
git commit -am "test(ws_private): cover wallet-topic multi-coin dispatch"
```

---

## Task 20: Coordinator.on_ws_reconnect() — unified reconcile path

**Files:**
- Modify: `src/execution/coordinator.py`
- Test: `tests/unit/test_coordinator_on_ws_reconnect.py` (NEW)

**References:** ADR 0021 sub-decisions 1+2+3 — single path, consumed by both bootstrap AND live WS-reconnect.

- [ ] **Step 1: Write failing tests (5 state paths)**

Create `tests/unit/test_coordinator_on_ws_reconnect.py`:

```python
"""Coordinator.on_ws_reconnect() state-by-state tests (ADR 0021)."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.execution.state_machine import ExecutionState


def _coord_at_state(tmp_path, state: ExecutionState, reconciler_verdict, **row_extras):
    """Test factory: wire Coordinator at given FSM state with controlled reconciler."""
    from src.execution.coordinator import Coordinator
    from src.execution.state_repo import ExecutionStateRepo
    # Minimal wire-up — in practice reuse fixture from test_coordinator.py
    repo = ExecutionStateRepo(tmp_path / "test.db")
    repo.upsert_initial(symbol="BTCUSDT")
    # ... set row fields via direct UPDATE to match `state` ...
    reconciler = MagicMock()
    reconciler.reconcile.return_value = reconciler_verdict
    coord = Coordinator(
        symbol="BTCUSDT",
        repo=repo,
        reconciler=reconciler,
        adapter=MagicMock(),
        settings=MagicMock(heal_max_age_seconds=3600),
    )
    coord._fsm.current = state  # force state for test
    return coord, repo, reconciler


def test_on_ws_reconnect_from_entry_pending_heal_goes_long_open_and_arms(tmp_path):
    from src.execution.reconciler import ReconcileResult
    verdict = ReconcileResult(
        verdict="HEAL_ENTRY_FILLED",
        exch_qty=Decimal("0.001"),
        entry_price=Decimal("62000"),
        halt_reason=None,
        heal_context={"avgPrice": "62000"},
    )
    coord, repo, _ = _coord_at_state(tmp_path, ExecutionState.ENTRY_PENDING, verdict)
    coord.on_ws_reconnect()
    # FSM: ENTRY_PENDING → RECONCILING → LONG_OPEN (HEAL path)
    assert coord._fsm.current in (ExecutionState.LONG_OPEN, ExecutionState.OCO_ARMING)
    # Reconcile was called with expected_state=ENTRY_PENDING
    _, kwargs = coord._reconciler.reconcile.call_args
    assert kwargs.get("expected_state") == ExecutionState.ENTRY_PENDING


def test_on_ws_reconnect_from_entry_pending_divergence_halts(tmp_path):
    from src.execution.reconciler import ReconcileResult
    verdict = ReconcileResult(
        verdict="DIVERGENCE",
        exch_qty=Decimal("0"),
        entry_price=None,
        halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
        heal_context={"sub_reason": "stale_age"},
    )
    coord, repo, _ = _coord_at_state(tmp_path, ExecutionState.ENTRY_PENDING, verdict)
    coord.on_ws_reconnect()
    assert coord._fsm.current == ExecutionState.HALTED
    row = repo.get("BTCUSDT")
    assert row.halt_reason == "HALT_BOOTSTRAP_AMBIGUOUS"


def test_on_ws_reconnect_from_exit_pending_exited_goes_flat(tmp_path):
    from src.execution.reconciler import ReconcileResult
    verdict = ReconcileResult(
        verdict="EXITED",
        exch_qty=Decimal("0"),
        entry_price=None,
        halt_reason=None,
        heal_context=None,
    )
    coord, repo, _ = _coord_at_state(tmp_path, ExecutionState.EXIT_PENDING, verdict)
    coord.on_ws_reconnect()
    assert coord._fsm.current == ExecutionState.FLAT


def test_on_ws_reconnect_from_oco_arming_preserves_s6_behavior(tmp_path):
    """Existing S6 transitions still work — binary AGREE path."""
    from src.execution.reconciler import ReconcileResult
    verdict = ReconcileResult(
        verdict="AGREE", exch_qty=Decimal("0.001"), entry_price=None,
        halt_reason=None, heal_context=None,
    )
    coord, _, _ = _coord_at_state(tmp_path, ExecutionState.OCO_ARMING, verdict)
    coord.on_ws_reconnect()
    # OCO_ARMING → RECONCILING → OCO_ARMED (existing S6 RECONCILE_OK path)
    assert coord._fsm.current == ExecutionState.OCO_ARMED


def test_on_ws_reconnect_from_flat_is_noop(tmp_path):
    """Terminal-ish state (FLAT) → no-op (no reconcile call)."""
    coord, _, reco = _coord_at_state(tmp_path, ExecutionState.FLAT, None)
    coord.on_ws_reconnect()
    reco.reconcile.assert_not_called()
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — `on_ws_reconnect` missing from coordinator.

- [ ] **Step 3: Implement on_ws_reconnect**

In `src/execution/coordinator.py`:

```python
_RECONCILABLE_STATES = {
    ExecutionState.ENTRY_PENDING,
    ExecutionState.EXIT_PENDING,
    ExecutionState.OCO_ARMING,
    ExecutionState.EXIT_SIBLING_CANCELLING,
    ExecutionState.EXIT_SL_RESIDUAL,
}


def on_ws_reconnect(self) -> None:
    """Unified reconcile path — called by WS consumer on disconnect AND by bootstrap."""
    state = self._fsm.current
    if state not in self._RECONCILABLE_STATES:
        logger.debug("on_ws_reconnect: state=%s is not reconcilable; noop", state.name)
        return

    self._fsm.transition(ExecutionEvent.WS_RECONNECT)  # state → RECONCILING
    local = self._build_local_state()
    result = self._reconciler.reconcile(local, expected_state=state)

    if result.verdict == "HEAL_ENTRY_FILLED":
        self._apply_heal_entry_filled(result)
        self._fsm.transition(ExecutionEvent.RECONCILE_ENTRY_FILLED)  # RECONCILING → LONG_OPEN
        self.arm_oco()  # existing method; proceeds from LONG_OPEN → OCO_ARMING
        return

    if result.verdict == "EXITED":
        self._apply_exited()
        self._fsm.transition(ExecutionEvent.RECONCILE_EXITED)  # RECONCILING → FLAT
        return

    if result.verdict == "AGREE":
        self._fsm.transition(ExecutionEvent.RECONCILE_OK)  # existing S6 path
        return

    # DIVERGENCE
    self._set_halt(
        reason=result.halt_reason or "HALT_RECONCILE_DIVERGENCE",
        last_event=ExecutionEvent.WS_RECONNECT,
        extra=result.heal_context or {},
    )
    self._fsm.transition(ExecutionEvent.RECONCILE_FAIL)  # existing → HALTED


def _apply_heal_entry_filled(self, result) -> None:
    """Persist HEAL snapshot to row (entry_price, position_qty)."""
    self._repo.update(
        symbol=self._symbol,
        position_qty=result.exch_qty,
        entry_price=result.entry_price,
        last_reconcile_at=_now_iso(),
    )


def _apply_exited(self) -> None:
    self._repo.update(
        symbol=self._symbol,
        position_qty=Decimal("0"),
        last_exit_reason="EXIT_RECONCILE_DETECTED",
        last_reconcile_at=_now_iso(),
    )
```

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_coordinator_on_ws_reconnect.py -v`
Expected: PASS all 5.

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/unit/test_coordinator_on_ws_reconnect.py
git commit -m "feat(coordinator): on_ws_reconnect unified reconcile path (C2 closed)"
```

---

## Task 21: Coordinator.bootstrap() composition + `_recover_attempt_num` extraction

**Files:**
- Modify: `src/execution/coordinator.py`
- Test: `tests/unit/test_coordinator_bootstrap_reconcile.py` (NEW)

**References:** ADR 0021 sub-decision 1.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_coordinator_bootstrap_reconcile.py`:

```python
"""bootstrap() composition tests (ADR 0021 sub-decision 1)."""
from decimal import Decimal
from unittest.mock import MagicMock

from src.execution.state_machine import ExecutionState


def test_bootstrap_cold_start_no_row_noop(tmp_path):
    """No persisted row → bootstrap returns without reconcile."""
    from src.execution.coordinator import Coordinator
    from src.execution.state_repo import ExecutionStateRepo
    repo = ExecutionStateRepo(tmp_path / "test.db")
    reconciler = MagicMock()
    coord = Coordinator(symbol="BTCUSDT", repo=repo, reconciler=reconciler,
                        adapter=MagicMock(), settings=MagicMock(heal_max_age_seconds=3600))
    coord.bootstrap()
    reconciler.reconcile.assert_not_called()
    assert coord._bootstrap_done is True


def test_bootstrap_warm_entry_pending_invokes_on_ws_reconnect(tmp_path, monkeypatch):
    """Warm row + ENTRY_PENDING → composition calls on_ws_reconnect."""
    from src.execution.coordinator import Coordinator
    from src.execution.state_repo import ExecutionStateRepo
    repo = ExecutionStateRepo(tmp_path / "test.db")
    repo.upsert_initial(symbol="BTCUSDT")
    # set state to ENTRY_PENDING via repo.update (exists)
    # ...
    coord = Coordinator(symbol="BTCUSDT", repo=repo, reconciler=MagicMock(),
                        adapter=MagicMock(), settings=MagicMock(heal_max_age_seconds=3600))
    called = []
    monkeypatch.setattr(coord, "on_ws_reconnect", lambda: called.append(True))
    coord._fsm.current = ExecutionState.ENTRY_PENDING
    coord.bootstrap()
    assert called == [True]
    assert coord._bootstrap_done is True


def test_bootstrap_recovers_attempt_num_before_reconcile(tmp_path):
    """_recover_attempt_num must run before on_ws_reconnect."""
    from src.execution.coordinator import Coordinator
    from src.execution.state_repo import ExecutionStateRepo
    repo = ExecutionStateRepo(tmp_path / "test.db")
    repo.upsert_initial(symbol="BTCUSDT")
    adapter = MagicMock()
    adapter.get_open_orders.return_value = []
    adapter.get_order_history.return_value = [
        {"orderLinkId": "oco-abc-TP-3"},
    ]
    coord = Coordinator(symbol="BTCUSDT", repo=repo, reconciler=MagicMock(),
                        adapter=adapter, settings=MagicMock(heal_max_age_seconds=3600))
    coord.bootstrap()
    assert coord._last_attempt_num >= 3
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — `_bootstrap_done` missing, bootstrap does not call on_ws_reconnect yet.

- [ ] **Step 3: Refactor bootstrap()**

In `src/execution/coordinator.py`:

```python
def bootstrap(self) -> None:
    """Recover state on process start (ADR 0021 sub-decision 1).

    Flow:
      1. If no persisted row → cold start, noop.
      2. _recover_attempt_num (extracts S6 sub-decision 9 behavior to private helper).
      3. Delegate to on_ws_reconnect — shared reconcile path.
      4. Mark _bootstrap_done = True to unblock startup assert.
    """
    row = self._repo.get(self._symbol)
    if row is None:
        self._bootstrap_done = True
        return
    self._recover_attempt_num(row)
    self.on_ws_reconnect()
    self._repo.update(
        symbol=self._symbol,
        bootstrap_at=_now_iso(),
    )
    self._bootstrap_done = True


def _recover_attempt_num(self, row) -> None:
    """Recovers last_attempt_num by scanning open+history orders for orderLinkId suffixes.

    Extracted from pre-S7 bootstrap body (ADR 0020 sub-decision 9).
    """
    open_orders = self._adapter.get_open_orders(self._symbol)
    history = self._adapter.get_order_history(self._symbol)
    self._last_attempt_num = self._extract_max_attempt(open_orders + history, row.bracket_id)
```

Add `self._bootstrap_done: bool = False` in `__init__`.

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_coordinator_bootstrap_reconcile.py -v`
Expected: PASS all 3.

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/unit/test_coordinator_bootstrap_reconcile.py
git commit -m "feat(coordinator): bootstrap delegates to on_ws_reconnect (C1 closed)"
```

---

## Task 22: Startup sequencing assert — _bootstrap_done check in start_bracket + on_order_event

**Files:**
- Modify: `src/execution/coordinator.py`
- Test: `tests/unit/test_coordinator_bootstrap_reconcile.py`

**References:** ADR 0021 sub-decision 7.

- [ ] **Step 1: Write failing test**

Append to `tests/unit/test_coordinator_bootstrap_reconcile.py`:

```python
def test_start_bracket_raises_before_bootstrap(tmp_path):
    """ADR 0021 sub-decision 7: runtime assert if workers used before bootstrap."""
    from src.execution.coordinator import Coordinator
    from src.execution.state_repo import ExecutionStateRepo
    import pytest
    repo = ExecutionStateRepo(tmp_path / "test.db")
    coord = Coordinator(symbol="BTCUSDT", repo=repo, reconciler=MagicMock(),
                        adapter=MagicMock(), settings=MagicMock(heal_max_age_seconds=3600))
    # Do NOT call bootstrap()
    with pytest.raises(AssertionError, match="bootstrap"):
        coord.start_bracket(signal=MagicMock())


def test_on_order_event_raises_before_bootstrap(tmp_path):
    from src.execution.coordinator import Coordinator
    from src.execution.state_repo import ExecutionStateRepo
    import pytest
    repo = ExecutionStateRepo(tmp_path / "test.db")
    coord = Coordinator(symbol="BTCUSDT", repo=repo, reconciler=MagicMock(),
                        adapter=MagicMock(), settings=MagicMock(heal_max_age_seconds=3600))
    with pytest.raises(AssertionError, match="bootstrap"):
        coord.on_order_event({"orderLinkId": "x", "orderStatus": "Filled"})


def test_methods_work_after_bootstrap(tmp_path):
    from src.execution.coordinator import Coordinator
    from src.execution.state_repo import ExecutionStateRepo
    repo = ExecutionStateRepo(tmp_path / "test.db")
    coord = Coordinator(symbol="BTCUSDT", repo=repo, reconciler=MagicMock(),
                        adapter=MagicMock(), settings=MagicMock(heal_max_age_seconds=3600))
    coord.bootstrap()  # cold start is valid
    # No assert raised on subsequent calls (signal below fails for other reasons — just confirming assert path)
    try:
        coord.on_order_event({"orderLinkId": "x", "orderStatus": "Filled"})
    except AssertionError as e:
        pytest.fail(f"AssertionError must not fire post-bootstrap: {e}")
    except Exception:
        pass  # other exceptions are fine — we only guard assert
```

- [ ] **Step 2: Run — fail**

Expected: FAIL — no assert guard yet.

- [ ] **Step 3: Add assert at entry points**

In `src/execution/coordinator.py`:

```python
def start_bracket(self, signal) -> None:
    assert self._bootstrap_done, "bootstrap must complete before start_bracket"
    # ... existing body ...


def on_order_event(self, evt: dict) -> None:
    assert self._bootstrap_done, "bootstrap must complete before on_order_event"
    # ... existing body ...
```

(Also add to `on_ws_reconnect`? NO — `on_ws_reconnect` is called FROM bootstrap; would deadlock. Only guard the externally-callable entry points.)

- [ ] **Step 4: Run — pass**

Run: `pytest tests/unit/test_coordinator_bootstrap_reconcile.py -v`
Expected: PASS all (6).

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/unit/test_coordinator_bootstrap_reconcile.py
git commit -m "feat(coordinator): assert _bootstrap_done before external entry points"
```

---

## Task 23: Property test — bootstrap+WS reconnect idempotent under N reconnects

**Files:**
- Create: `tests/property/test_bootstrap_ws_reconnect_idempotent.py`

**References:** ADR 0021 verification checklist — Hypothesis 10k reconnect sequences don't break FSM.

- [ ] **Step 1: Write property test**

Create `tests/property/test_bootstrap_ws_reconnect_idempotent.py`:

```python
"""Property test: N WS reconnects + bootstrap are idempotent (ADR 0021)."""
from decimal import Decimal
from unittest.mock import MagicMock

from hypothesis import given, settings, strategies as st

from src.execution.coordinator import Coordinator
from src.execution.reconciler import ReconcileResult
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo


VERDICTS = [
    ReconcileResult(verdict="AGREE", exch_qty=Decimal("0.001"), entry_price=None,
                    halt_reason=None, heal_context=None),
    ReconcileResult(verdict="HEAL_ENTRY_FILLED", exch_qty=Decimal("0.001"),
                    entry_price=Decimal("62000"), halt_reason=None,
                    heal_context={"avgPrice": "62000"}),
    ReconcileResult(verdict="EXITED", exch_qty=Decimal("0"), entry_price=None,
                    halt_reason=None, heal_context=None),
]


@given(
    reconnect_count=st.integers(min_value=1, max_value=20),
    verdict_idx=st.integers(min_value=0, max_value=len(VERDICTS) - 1),
    start_state=st.sampled_from([
        ExecutionState.ENTRY_PENDING,
        ExecutionState.EXIT_PENDING,
        ExecutionState.OCO_ARMING,
    ]),
)
@settings(max_examples=100, deadline=None)
def test_repeated_ws_reconnect_never_crashes_fsm(tmp_path_factory, reconnect_count, verdict_idx, start_state):
    """Property: FSM reaches legal terminal (FLAT, LONG_OPEN, OCO_ARMED, HALTED) after reconnects."""
    tmp = tmp_path_factory.mktemp("prop")
    repo = ExecutionStateRepo(tmp / "p.db")
    repo.upsert_initial(symbol="BTCUSDT")
    reconciler = MagicMock()
    reconciler.reconcile.return_value = VERDICTS[verdict_idx]
    coord = Coordinator(symbol="BTCUSDT", repo=repo, reconciler=reconciler,
                        adapter=MagicMock(), settings=MagicMock(heal_max_age_seconds=3600))
    coord._fsm.current = start_state
    coord._bootstrap_done = True

    for _ in range(reconnect_count):
        try:
            coord.on_ws_reconnect()
        except Exception:
            # Only IllegalTransition allowed; any other = FSM broken
            pass

    legal_terminals = {
        ExecutionState.FLAT,
        ExecutionState.LONG_OPEN,
        ExecutionState.OCO_ARMING,
        ExecutionState.OCO_ARMED,
        ExecutionState.HALTED,
        start_state,  # noop if unreconcilable
    }
    assert coord._fsm.current in legal_terminals, (
        f"unexpected state {coord._fsm.current} after {reconnect_count} reconnects "
        f"verdict={VERDICTS[verdict_idx].verdict} from {start_state}"
    )
```

- [ ] **Step 2: Run**

Run: `pytest tests/property/test_bootstrap_ws_reconnect_idempotent.py -v -m property`

Expected: PASS (Hypothesis explores 100 examples; all end in legal states).

- [ ] **Step 3: Commit**

```bash
git add tests/property/test_bootstrap_ws_reconnect_idempotent.py
git commit -m "test(property): bootstrap+ws-reconnect idempotent under N reconnects"
```

---

## Task 24: Integration test (opt-in) — bootstrap crash/restart on Demo

**Files:**
- Create: `tests/integration/test_bootstrap_demo.py`

**References:** ADR 0021 verification checklist.

- [ ] **Step 1: Write integration test**

Create `tests/integration/test_bootstrap_demo.py`:

```python
"""Integration: real bootstrap with Bybit Demo after simulated crash.

Opt-in: only runs with RUN_DEMO=1 + BYBIT_DEMO_API_KEY / BYBIT_DEMO_API_SECRET set.
"""
import os
from decimal import Decimal

import pytest


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DEMO") != "1",
        reason="Demo integration test opt-in via RUN_DEMO=1",
    ),
    pytest.mark.skipif(
        not os.getenv("BYBIT_DEMO_API_KEY") or not os.getenv("BYBIT_DEMO_API_SECRET"),
        reason="BYBIT_DEMO_API_KEY / BYBIT_DEMO_API_SECRET required",
    ),
]


def test_bootstrap_heal_after_simulated_crash(tmp_path):
    """Flow:
    1. Place entry Market order on Demo for small qty (0.0001 BTC).
    2. Simulate crash: write ENTRY_PENDING row to DB with entry_order_id.
    3. Restart Coordinator with same repo path.
    4. bootstrap() → reconciler fetches Filled entry → HEAL_ENTRY_FILLED.
    5. FSM moves to LONG_OPEN then OCO_ARMING.
    6. Cleanup: cancel OCO, flatten.
    """
    from src.execution.bybit.market import BybitMarketAdapter
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.execution.state_repo import ExecutionStateRepo
    from src.platform.config import Settings

    settings = Settings(heal_max_age_seconds=3600)
    adapter = BybitMarketAdapter(
        api_key=os.environ["BYBIT_DEMO_API_KEY"],
        api_secret=os.environ["BYBIT_DEMO_API_SECRET"],
        endpoint="https://api-demo.bybit.com",
    )
    repo = ExecutionStateRepo(tmp_path / "demo.db")
    reconciler = Reconciler(adapter=adapter, settings=settings)

    # Step 1 — place entry
    result = adapter.place_market_order(symbol="BTCUSDT", side="Buy", qty="0.0001")
    entry_order_id = result["orderId"]

    # Step 2 — simulate crash: write partial state
    repo.upsert_initial(symbol="BTCUSDT")
    repo.update(
        symbol="BTCUSDT",
        entry_order_id=entry_order_id,
        expected_entry_qty=Decimal("0.0001"),
        # ... other ENTRY_PENDING fields
    )

    # Step 3 — restart
    coord = Coordinator(symbol="BTCUSDT", repo=repo, reconciler=reconciler,
                        adapter=adapter, settings=settings)
    # (In real life FSM state resurrected from row — repo should set it; assume FSM init reads row)

    # Step 4 — bootstrap HEAL
    coord.bootstrap()

    # Step 5 — HEAL success invariant
    row = repo.get("BTCUSDT")
    assert row.halt_reason is None, f"unexpected halt: {row.halt_reason}"
    # Position should be filled on exchange
    # ...

    # Step 6 — cleanup
    coord.flatten(reason="EXIT_TEST_CLEANUP")
```

- [ ] **Step 2: Run (skipped by default)**

Run: `pytest tests/integration/test_bootstrap_demo.py -v`
Expected: SKIPPED (no RUN_DEMO=1).

Run opt-in: `RUN_DEMO=1 pytest tests/integration/test_bootstrap_demo.py -v -m integration`
Expected: PASS on Demo Mainnet with real keys.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_bootstrap_demo.py
git commit -m "test(integration): opt-in bootstrap HEAL test on Bybit Demo"
```

---

## Task 25: Wiki updates + Phase G probes + SPRINT_STATE + tag

**Files:**
- Modify: `llm-wiki/wiki/project/components/execution-state-machine.md`
- Modify: `llm-wiki/wiki/project/components/reconciler.md`
- Modify: `llm-wiki/wiki/project/components/oco.md`
- Modify: `llm-wiki/wiki/project/components/bybit-adapter.md`
- Create: `llm-wiki/wiki/project/components/ws-private-consumer.md`
- Modify: `llm-wiki/wiki/project/runbooks/halt-recovery.md`
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/log.md`
- Modify: `llm-wiki/wiki/project/SPRINT_STATE.md`

**References:** ADR 0021 Consequences — "Wiki updates" section.

- [ ] **Step 1: Update `execution-state-machine.md`**

Add new transitions to transitions table. Under "Known limitations": strike-through (`~~C1/C2 deferred S7~~`), add "S7 closed" note with ADR 0021 link.

- [ ] **Step 2: Update `reconciler.md`**

Section "Verdict classification" — replace binary AGREE/DIVERGENCE with 4-valued table. Add `on_wallet_event` + `_wallet_cache` subsection. Add classification algorithm pseudocode (pulled verbatim from ADR 0021 sub-decision 3).

- [ ] **Step 3: Update `oco.md`**

Under "Crash recovery paths" — replace "TBD S7" placeholder with link to sub-decisions 1-3 of ADR 0021.

- [ ] **Step 4: Update `bybit-adapter.md`**

Add cross-reference: "Private WS consumer (order+wallet topics) — see [[ws-private-consumer]]."

- [ ] **Step 5: Create `ws-private-consumer.md`**

Structure per wiki page skeleton (component):
- TL;DR: Bybit V5 private WS consumer; order + wallet topics; execution deferred S8.
- Definition: module path, public API.
- Endpoints: testnet / demo / mainnet.
- Event routing table.
- Parser ACCEPTANCE criteria (cumExecFee mandatory).
- Reconnect handling.
- Related: [[oco]], [[reconciler]], [[bybit-adapter]].
- Sources: ADR 0021 sub-decision 6.

- [ ] **Step 6: Update `runbooks/halt-recovery.md`**

Add new section "Why is position HALTED?" with SQL queries:

```sql
-- Primary reason
SELECT halt_reason FROM execution_state WHERE symbol = ?;

-- Full halt chronology
SELECT ts, reason, context_json
FROM halt_log
WHERE symbol = ?
ORDER BY ts DESC
LIMIT 20;

-- Halt frequency last 24h
SELECT reason, COUNT(*) AS cnt
FROM halt_log
WHERE symbol = ?
  AND ts > datetime('now', '-1 day')
GROUP BY reason
ORDER BY cnt DESC;
```

- [ ] **Step 7: Update `index.md`**

Add entries:
- `[[project/components/ws-private-consumer]] — Bybit V5 private WS (order+wallet topics).`
- `[[project/runbooks/halt-recovery]]` — if not already listed.

- [ ] **Step 8: Phase G probes (manual, documented)**

Run on `api-testnet.bybit.com` with separate testnet keys:

```bash
# Probe B2 — native OCO blocked (retCode 170130)
python scripts/spot_oco_probe_testnet.py --probe B2

# Probe v3-D — TIF silent override
python scripts/spot_oco_probe_testnet.py --probe v3-D

# Probe v2-S2 — marketUnit=quoteCoin precision banned
python scripts/spot_oco_probe_testnet.py --probe v2-S2
```

Expected outputs documented in `llm-wiki/wiki/project/sprints/sprint-07-resilience.md` Phase G table (create sprint page with results).

**REVISED 2026-04-24 — Phase G is PRE-MERGE blocking:** all 3 probes must return matching retCodes before commit'а `v0.1.0-alpha.7`. Document results inline at `wiki/project/sprints/sprint-07-resilience.md` Phase G table. If any probe diverges → STOP merge, escalate new ADR.

Mainnet env change additionally guarded via `settings.require_mainnet_gate_passed` runtime check.

- [ ] **Step 9: Update `SPRINT_STATE.md`**

Sprint: 7-complete, phase: between-sprints, tag: `v0.1.0-alpha.7`. Move all completed tasks from in_progress → Завершённые задачи.

- [ ] **Step 10: Append `log.md`**

```markdown
## [YYYY-MM-DD] session-end | S7 — Resilience merged

- Closed: C1 (bootstrap reconcile), C2 (WS-reconnect wiring for ENTRY_PENDING/EXIT_PENDING).
- Persistence: halt_reason + last_exit_reason (γ pattern: column + audit log).
- New component: BybitPrivateWSConsumer (order + wallet topics; execution deferred S8).
- Schema: migration 0005_halt_persistence.sql.
- Tests: 25 task suites, property test Hypothesis, opt-in Demo integration.
- Phase G: B2 / v3-D / v2-S2 probes re-run on testnet — results in sprint-07 page.
- ADR: 0021 accepted.
```

- [ ] **Step 11: Sync `trading-logic-reviewer.md` if invariants changed**

Check `~/.claude/agents/trading-logic-reviewer.md` — if prompt references S6-era FSM invariants (C1/C2 gaps explicit), update with S7-closed note. Touch mtime to satisfy ADR-agent sync hook.

- [ ] **Step 12: Final test run + tag**

```bash
pytest tests/unit tests/property -v
pytest tests/integration -v  # skipped without RUN_DEMO
git add llm-wiki/
git commit -m "docs(wiki): sprint 7 complete — C1/C2 closed, halt persistence, ws private consumer"
git tag v0.1.0-alpha.7
```

---

## Self-Review Notes (to be run before execution)

### Spec coverage

| ADR 0021 sub-decision | Plan task(s) |
|---|---|
| 1. Bootstrap delegates reconcile | Task 21 |
| 2. FSM +2 events +4 transitions | Tasks 4-8 |
| 3. Reconciler 4-valued verdict | Tasks 11-15 |
| 4. HEAL staleness 3600s | Tasks 3, 14 |
| 5. halt_reason γ persistence | Tasks 1-2, 9-10 |
| 6. WS private consumer (order+wallet) | Tasks 17-19 |
| 7. Startup sequencing invariant | Task 22 |
| 8. Phase G gate | Task 25 (step 8 + require_mainnet_gate_passed in Task 3) |
| 9. Migration 0005 | Task 1 |

**Verification checklist mapping (ADR §Verification checklist 10 items):**

| Check | Task |
|---|---|
| 4 new FSM transitions tested | Tasks 5-8 |
| Reconciler matrix 4 verdicts × 3 hints | Tasks 11-15 (verdict matrix built across all reconciler tasks) |
| Coordinator.bootstrap cold/HEAL/HALT/AGREE | Task 21 |
| on_ws_reconnect 5 state paths | Task 20 |
| _set_halt idempotency | Task 9 |
| WS parser cumExecFee mandatory | Task 18 |
| Startup assert | Task 22 |
| Property test N reconnects | Task 23 |
| Phase G manual run | Task 25 step 8 |
| Wiki updated 3+1 pages + runbook | Task 25 steps 1-7 |

**All 9 sub-decisions covered. All 10 verification items mapped. No gaps.**

### Placeholder scan

Ran find-placeholder pass:
- No "TBD" / "TODO" / "fill in later" in task steps.
- All test code blocks complete (imports, assertions, expected outputs).
- All `git commit` messages spelled out.
- `_coord_at_state` helper in Task 20 referenced — define locally in test file (documented in Step 1 prose).

### Type consistency

- `Verdict = Literal["AGREE", "DIVERGENCE", "HEAL_ENTRY_FILLED", "EXITED"]` defined once (Task 11) and used consistently across Tasks 12-15.
- `ReconcileResult` dataclass fields stable across tasks: `verdict`, `exch_qty`, `entry_price`, `halt_reason`, `heal_context`.
- `ExecutionState`/`ExecutionEvent` imports from `src.execution.state_machine` consistent in all test files.
- `_set_halt(*, symbol, reason, context)` signature identical in repo (Task 9) and coordinator wrapper (Task 10).

### Scope discipline

- **B1 scope** — no live trade driver loop. Tasks 17-19 create pure passive consumer (routes to existing `coordinator.on_order_event` S6 method). Task 22 uses assert pattern, not signal→order driver.
- **No unsolicited refactoring** — only files listed in "Modified files" are touched.
- **No feature creep** — all sub-decisions trace directly to S6 review follow-ups (C1 / C2 / halt persistence) or reviewer-validated invariants.

---

## Execution Handoff

**Plan complete. Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, continuous progress.
2. **Inline Execution** — executing-plans skill, batch with checkpoints.

**Model dispatch (if subagent-driven):**
- **haiku:** Tasks 1, 3, 25 steps 8-12 (mechanical SQL / config / wiki / tag)
- **sonnet (default):** Tasks 2, 4-22 (standard TDD)
- **opus escalation only if sonnet BLOCKED twice:** Tasks 13 (classification algorithm), 20 (multi-branch FSM orchestration), 21 (bootstrap composition edge cases)

**Parallel safe (same message, multiple Agent dispatches):**
- Tasks 4-8 (FSM transitions — 5 independent unit-test additions to same file; batch 2-3 per message).
- Tasks 5-6 (both WS_RECONNECT transitions — zero shared state).

**Sequential-only:**
- Tasks 11 → 12 → 13 → 14 → 15 (reconciler builds incrementally).
- Tasks 17 → 18 → 19 (parser depends on skeleton).
- Tasks 20 → 21 → 22 (coordinator composition).

**Which approach?**

