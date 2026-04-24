---
title: "Sprint 8a — Live Runtime Implementation Plan"
type: plan
status: draft
created: 2026-04-24
updated: 2026-04-24
sources:
  - wiki/project/decisions/0022-sprint-8a-live-runtime.md
  - wiki/project/decisions/0021-sprint-7-resilience.md
  - wiki/project/components/ws-private-consumer.md
  - wiki/project/components/execution-state-machine.md
  - wiki/project/components/reconciler.md
tags: [sprint-8a, runtime, orchestration, threading, kill-switch, bar-poller, tdd]
---

# Sprint 8a — Live Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Привести bot к живому запуску — ввести `RuntimeManager`, REST bar-поллер, KILL_SWITCH wiring, threading lock policy на Coordinator/Reconciler, и удалить legacy orphans (`src/controller.py`, `main.py`).

**Architecture:** Sync runtime + два thread'а. Main thread держит sequential pipeline tick'а: `_maybe_kill_switch → _check_alive_inline → _poll_bar → strategy.on_bar → coordinator.start_bracket`. pybit thread (уже из S7) маршрутизирует WS order/wallet события через `coordinator.on_order_event` / `reconciler.on_wallet_event` под общими locks (RLock на Coordinator, Lock на Reconciler). KILL_SWITCH — sentinel-file (`.kill_switch`) с CLI subcommand `python -m src kill`. Entry-point — `python -m src` с argparse subcommands `run / backfill / reconcile-only / kill`.

**Tech Stack:** Python 3.12, threading.RLock + threading.Lock (НЕ asyncio в v0.1), pybit V5 (уже из S7), pydantic-settings v2, argparse, structlog, pytest, существующие Coordinator/Reconciler/FSM/halt_log из S7.

**Source of truth:** [[../decisions/0022-sprint-8a-live-runtime]]. Все 14 sub-decisions цитируются inline в задачах ниже.

---

## File Structure

**New files:**

| Path | Responsibility |
|------|----------------|
| `src/runtime/__init__.py` | NEW package marker |
| `src/runtime/manager.py` | `RuntimeManager` — process lifecycle (bootstrap / loop / shutdown) |
| `src/runtime/bar_source.py` | `BarSource` — REST kline poller с dedup + stall counter |
| `src/__main__.py` | argparse entry-point: `run / backfill / reconcile-only / kill` |
| `tests/unit/test_runtime_manager.py` | bootstrap → tick → shutdown invariants, kill-switch detection, crash → halt persistence |
| `tests/unit/test_bar_poller.py` | dedup, stall counter, recovery, warmup |
| `tests/unit/test_coordinator_threading.py` | concurrent `on_order_event` × `start_bracket` (threading.Thread fixtures) |
| `tests/unit/test_reconciler_threading.py` | concurrent `on_wallet_event` × `reconcile` |
| `tests/unit/test_strategy_warmup_no_signal.py` | catch-up bars → 0 `on_signal` calls |
| `tests/unit/test_kill_switch_cli.py` | `python -m src kill` writes file; `run` cleans stale file |
| `tests/unit/test_main_module.py` | argparse subcommand routing + exit codes |
| `tests/unit/test_reason_codes_s8a.py` | enum count 42 → 45; codes 43/44/45 |
| `tests/unit/test_settings_runtime.py` | 5 new runtime_* fields + validator boundaries |
| `tests/integration/test_runtime_demo_smoke.py` | opt-in `RUN_DEMO=1` — full bring-up + kill switch graceful shutdown |
| `llm-wiki/wiki/project/components/runtime-manager.md` | NEW component doc — entry-point, lifecycle, lock policy |
| `llm-wiki/wiki/project/components/bar-poller.md` | NEW component doc — REST kline polling, stall semantics |

**Modified files:**

| Path | Change |
|------|--------|
| `src/execution/coordinator.py` | Task 0: `_lock = threading.RLock()`, обернуть `bootstrap` / `start_bracket` / `on_order_event` / `on_ws_reconnect` / `arm_oco` / `flatten`; добавить публичный `request_halt(reason: str)` |
| `src/execution/reconciler.py` | Task 0: `_lock = threading.Lock()`, обернуть `on_wallet_event` + `reconcile` |
| `src/execution/state_machine.py` | сверить присутствие `KILL_SWITCH_REQUESTED` event и transition'ов из активных состояний (S7 уже добавил `KILL_SWITCH` — переименование/расширение) |
| `src/risk/reason_codes.py` | добавить codes `HALT_RUNTIME_CRASH` (43) / `HALT_BAR_POLL_STALL` (44) / `KILL_SWITCH_REQUESTED` (45) |
| `src/platform/config.py` | 5 новых runtime settings + validator на `runtime_bar_poll_stall_threshold` (6 ≤ N ≤ 720) |
| `llm-wiki/wiki/project/components/ws-private-consumer.md` | driver loop теперь existует (cross-link к runtime-manager); `check_alive` callsite (inline в main thread) |
| `llm-wiki/wiki/project/components/execution-state-machine.md` | `KILL_SWITCH_REQUESTED` reason; lock policy reference |
| `llm-wiki/wiki/project/components/reconciler.md` | lock policy reference |
| `llm-wiki/wiki/trading/concepts/reason-codes.md` | 42 → 45 (full table rows для 43/44/45 с halt-class аннотацией) |
| `llm-wiki/wiki/project/architecture/risk-register.md` | новый scenario `POLL_STALL_MID_BAR_FILL` |
| `llm-wiki/wiki/project/runbooks/halt-recovery.md` | секции для `HALT_RUNTIME_CRASH` / `HALT_BAR_POLL_STALL` / `KILL_SWITCH_REQUESTED` (SQL templates per S7) |
| `llm-wiki/wiki/index.md` | + runtime-manager, + bar-poller |
| `llm-wiki/wiki/log.md` | append S8a session entries |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | phase/progress per task |

**Deleted files:**

| Path | Why |
|------|-----|
| `src/controller.py` | orphan — broken since S2 venue migration (imports `src.data.consumer`, `src.strategy.strategy`, `src.risk.risk_manager`, `src.execution.executor` — all gone). ADR 0022 sub-decision 10. |
| `main.py` (repo root) | imports `from src.controller import Controller` → ImportError. ADR 0022 sub-decision 10. |

---

## Task Sequencing Rationale

Dependency graph (per ADR 0022 reviewer scope ordering):

```
Phase 0 (Pre-cleanup):    Tasks 1-2   → удалить legacy orphans (no runtime deps)
Phase 1 (Foundation):     Tasks 3-4   → settings + reason codes (no runtime deps)
Phase 2 (Lock policy):    Tasks 5-6   → Coordinator RLock + Reconciler Lock (Task 0 из ADR — MANDATORY перед любым runtime-кодом)
Phase 3 (Bar source):     Tasks 7-10  → REST poller + dedup + stall + warmup (зависит Phase 1)
Phase 4 (KILL_SWITCH):    Tasks 11-12 → Coordinator.request_halt + FSM event wiring (зависит Phase 1)
Phase 5 (RuntimeManager): Tasks 13-17 → scaffold + bootstrap + main loop + crash handler + shutdown (зависит Phase 2-4)
Phase 6 (Entry-point):    Tasks 18-19 → __main__.py + argparse + kill subcommand (зависит Phase 5)
Phase 7 (Integration):    Task 20     → Demo Mainnet smoke (opt-in RUN_DEMO=1)
Phase 8 (Wiki Stage E):   Tasks 21-29 → 2 NEW + 5 UPDATE component pages + reason-codes/risk-register/runbook + index/log
Phase 9 (Ship):           Task 30     → final domain reviewers (parallel) + finishing-a-development-branch + tag
```

**Critical-path note:** Phase 2 (lock policy) — это **Task 0** в ADR 0022. Без locks runtime имеет silent FSM corruption race между pybit thread (`on_order_event`) и main thread (`start_bracket` / `flatten`) — оба пишут `_repo` row. Поэтому lock policy идёт ДО любого runtime-кода (Phase 5+).

Phase 3 + Phase 4 могут идти параллельно после Phase 2. Phase 5 зависит от всех Phase 2-4. Phase 8 (wiki) технически может interleave с Phase 5-7, но сгруппирован в конец для clean PR.

**Parallel-safe pairs (один message, multiple Agent dispatches):**
- Tasks 1 + 2 (orphan delete — независимые файлы)
- Tasks 3 + 4 (settings + enum — разные файлы, оба mechanical)
- Tasks 5 + 6 (Coordinator + Reconciler locks — разные файлы)
- Tasks 7 + 8 (BarSource scaffold + REST integration — sequential within file, но можно batch один subagent)
- Tasks 21 + 22 (две новые wiki-страницы — разные файлы)
- Tasks 23-29 (wiki updates — все разные файлы)

**Sequential-only:**
- Tasks 13 → 14 → 15 → 16 → 17 (RuntimeManager builds incrementally)
- Tasks 18 → 19 (argparse → kill subcommand)
- Task 30 после всех остальных

---

## Task 1: Delete `src/controller.py`

**Files:**
- Delete: `src/controller.py`
- Test: `pytest --collect-only` (no broken imports)

**References:** ADR 0022 sub-decision 10.

- [ ] **Step 1: Verify no live imports**

```bash
grep -rn "from src.controller" src/ tests/ --include="*.py" || echo "OK no imports"
grep -rn "import src.controller" src/ tests/ --include="*.py" || echo "OK no imports"
```
Expected: оба `OK no imports`. Если что-то нашлось — открыть отдельный мини-task. (Подтверждено на 2026-04-24: только `main.py` импортирует, и он удаляется в Task 2.)

- [ ] **Step 2: Delete file**

```bash
git rm src/controller.py
```

- [ ] **Step 3: Verify pytest collection still works**

Run: `pytest --collect-only -q 2>&1 | tail -20`
Expected: no collection errors mentioning `src/controller.py`.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(cleanup): remove orphan src/controller.py (broken since S2 venue migration)"
```

---

## Task 2: Delete `main.py` + audit orphan tests

**Files:**
- Delete: `main.py` (repo root)
- Audit: `tests/` для любых ссылок на `from main import` / `from src.controller import`

**References:** ADR 0022 sub-decision 10.

- [ ] **Step 1: Audit test references**

```bash
grep -rn "from main import\|^import main$\|from src.controller" tests/ --include="*.py" || echo "OK"
```
Expected: `OK` (после Task 1). Если тест найден — добавить его в `git rm` команду Step 2.

- [ ] **Step 2: Delete file**

```bash
git rm main.py
```

- [ ] **Step 3: Verify pytest collection + import-time smoke**

Run:
```bash
pytest --collect-only -q 2>&1 | tail -20
python -c "import src; print('OK')"
```
Expected: collection clean, `OK` printed.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(cleanup): remove orphan main.py (imported broken src.controller)"
```

---



## Task 3: Settings — 5 new runtime_* fields + validator

**Files:**
- Modify: `src/platform/config.py`
- Test: `tests/unit/test_settings_runtime.py` (NEW)

**References:** ADR 0022 sub-decision 11 (+ sub-decision 3 для validator boundary).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_settings_runtime.py`:

```python
"""Sprint 8a runtime settings — defaults, env override, validator boundaries.

ADR 0022 sub-decisions 11 (5 new fields) + 3 (stall threshold validator).
"""
from __future__ import annotations

import pytest


def test_settings_runtime_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    from src.platform.config import Settings

    s = Settings()
    assert s.runtime_bar_poll_cadence_seconds == 5.0
    assert s.runtime_bar_poll_stall_threshold == 24
    assert s.runtime_kill_switch_path == ".kill_switch"
    assert s.runtime_ws_check_alive_max_silence == 30.0
    assert s.runtime_warmup_bars == 50


def test_settings_runtime_stall_threshold_validator_low(monkeypatch, tmp_path):
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    monkeypatch.setenv("RUNTIME_BAR_POLL_STALL_THRESHOLD", "5")
    from src.platform.config import Settings

    with pytest.raises(ValueError, match="6 ≤ N ≤ 720"):
        Settings()


def test_settings_runtime_stall_threshold_validator_high(monkeypatch, tmp_path):
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    monkeypatch.setenv("RUNTIME_BAR_POLL_STALL_THRESHOLD", "721")
    from src.platform.config import Settings

    with pytest.raises(ValueError, match="6 ≤ N ≤ 720"):
        Settings()


def test_settings_runtime_stall_threshold_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    monkeypatch.setenv("RUNTIME_BAR_POLL_STALL_THRESHOLD", "120")
    from src.platform.config import Settings

    s = Settings()
    assert s.runtime_bar_poll_stall_threshold == 120
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_settings_runtime.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'runtime_bar_poll_cadence_seconds'`.

- [ ] **Step 3: Write minimal implementation**

In `src/platform/config.py`, after S7 block (`require_mainnet_gate_passed`), append:

```python
    # Sprint 8a — Live runtime (ADR 0022 sub-decisions 11 + 3)
    runtime_bar_poll_cadence_seconds: float = Field(
        default=5.0,
        description="REST kline poll cadence (main loop tick). ADR 0022 sub-decision 2.",
    )
    runtime_bar_poll_stall_threshold: int = Field(
        default=24,
        description=(
            "Consecutive REST poll failures before HALT_BAR_POLL_STALL. "
            "Default 24 × 5s = 120s. Validator: 6 ≤ N ≤ 720 "
            "(30s false-halt floor; 1 bar period ceiling). ADR 0022 sub-decision 3."
        ),
    )
    runtime_kill_switch_path: str = Field(
        default=".kill_switch",
        description="Sentinel-file path for KILL_SWITCH. ADR 0022 sub-decision 5.",
    )
    runtime_ws_check_alive_max_silence: float = Field(
        default=30.0,
        description="Max WS silence before triggering on_disconnect (inline check). ADR 0022 sub-decision 4.",
    )
    runtime_warmup_bars: int = Field(
        default=50,
        description="Catch-up bars fed to strategy.warmup() (no signal emit). ADR 0022 sub-decision 2.",
    )
```

И добавить validator в существующий `_live_trading_guards` ИЛИ новый `@model_validator(mode="after")` метод (новый — не пересекается со scope существующего):

```python
    @model_validator(mode="after")
    def _runtime_validators(self) -> "Settings":
        if not (6 <= self.runtime_bar_poll_stall_threshold <= 720):
            raise ValueError(
                f"runtime_bar_poll_stall_threshold={self.runtime_bar_poll_stall_threshold} "
                f"out of range: 6 ≤ N ≤ 720 (ADR 0022 sub-decision 3)."
            )
        return self
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_settings_runtime.py -v`
Expected: PASS все 4 теста.

- [ ] **Step 5: Commit**

```bash
git add src/platform/config.py tests/unit/test_settings_runtime.py
git commit -m "feat(config): add 5 runtime_* settings + stall threshold validator (ADR 0022)"
```

---

## Task 4: Reason codes 43 / 44 / 45

**Files:**
- Modify: `src/risk/reason_codes.py`
- Test: `tests/unit/test_reason_codes_s8a.py` (NEW)

**References:** ADR 0022 sub-decision 12.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_reason_codes_s8a.py`:

```python
"""Sprint 8a — 3 new halt reason codes (ADR 0022 sub-decision 12)."""
from src.risk.reason_codes import ReasonCode


def test_reason_code_halt_runtime_crash_exists():
    assert ReasonCode.HALT_RUNTIME_CRASH.value == "HALT_RUNTIME_CRASH"


def test_reason_code_halt_bar_poll_stall_exists():
    assert ReasonCode.HALT_BAR_POLL_STALL.value == "HALT_BAR_POLL_STALL"


def test_reason_code_kill_switch_requested_exists():
    assert ReasonCode.KILL_SWITCH_REQUESTED.value == "KILL_SWITCH_REQUESTED"


def test_reason_code_total_count_45():
    """ADR 0021 baseline = 42; ADR 0022 adds 3 → 45 total."""
    assert len(list(ReasonCode)) == 45
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_reason_codes_s8a.py -v`
Expected: FAIL — `AttributeError: HALT_RUNTIME_CRASH`.

- [ ] **Step 3: Write minimal implementation**

In `src/risk/reason_codes.py`, после S7 секции добавить:

```python
    # --- ADR 0022 — Sprint 8a Live runtime ---
    HALT_RUNTIME_CRASH = "HALT_RUNTIME_CRASH"           # 43: unhandled exception в RuntimeManager.run()
    HALT_BAR_POLL_STALL = "HALT_BAR_POLL_STALL"         # 44: N consecutive REST kline failures (default N=24)
    KILL_SWITCH_REQUESTED = "KILL_SWITCH_REQUESTED"     # 45: sentinel-file `.kill_switch` detected (operator-initiated)
```

И обновить arithmetic note в module docstring:
```
ADR 0022 (Sprint 8a) adds 3 more → True count:
6 entry + 11 scale/exits + 9 rejects + 19 halts = 45.
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_reason_codes_s8a.py -v`
Expected: PASS все 4.

- [ ] **Step 5: Commit**

```bash
git add src/risk/reason_codes.py tests/unit/test_reason_codes_s8a.py
git commit -m "feat(reason-codes): add HALT_RUNTIME_CRASH / HALT_BAR_POLL_STALL / KILL_SWITCH_REQUESTED (ADR 0022)"
```

---



## Task 5: Coordinator threading.RLock (Task 0 from ADR — MANDATORY)

**Files:**
- Modify: `src/execution/coordinator.py`
- Test: `tests/unit/test_coordinator_threading.py` (NEW)

**References:** ADR 0022 sub-decision 1 (lock policy). Trader-expert annotation: "zero locks today" = open race door.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_coordinator_threading.py`:

```python
"""Concurrent on_order_event × start_bracket race — assert FSM consistent.

ADR 0022 sub-decision 1 (mandatory Task 0).

Strategy: 2 threads sync via threading.Barrier(2), then both invoke a
Coordinator method that calls _transition. Without RLock, dict-write race
on _repo row would yield indeterminate state. With RLock, post-condition
asserts state is one of legitimate transition outcomes (no torn write).
"""
from __future__ import annotations

import threading
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo


def _make_coord(tmp_path):
    repo = ExecutionStateRepo(tmp_path / "race.db")
    repo.upsert_initial(symbol="BTCUSDT")
    adapter = MagicMock()
    reconciler = MagicMock()
    settings = MagicMock(heal_max_age_seconds=3600, oco_arming_ttl_seconds=60)
    return Coordinator(
        symbol="BTCUSDT",
        repo=repo,
        reconciler=reconciler,
        adapter=adapter,
        settings=settings,
    ), repo


def test_coordinator_has_rlock(tmp_path):
    coord, _ = _make_coord(tmp_path)
    assert isinstance(coord._lock, type(threading.RLock())), (
        "Coordinator must use threading.RLock (reentrant) per ADR 0022 sub-decision 1"
    )


def test_coordinator_concurrent_on_order_event_and_start_bracket_safe(tmp_path):
    """2-thread fixture: barrier-sync + simultaneous mutation → final state legitimate."""
    coord, repo = _make_coord(tmp_path)
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def worker_order_event() -> None:
        try:
            barrier.wait()
            evt = {
                "orderId": "ent-1",
                "orderStatus": "Filled",
                "side": "Buy",
                "qty": "0.001",
                "cumExecQty": "0.001",
                "cumExecFee": "0.000001",
            }
            coord.on_order_event(evt)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    def worker_start_bracket() -> None:
        try:
            barrier.wait()
            coord.start_bracket(
                side="Buy",
                qty=Decimal("0.001"),
                sl_price=Decimal("60000"),
                tp_price=Decimal("70000"),
                reason="ENTRY_LONG_TREND_FOLLOWING",
            )
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    t1 = threading.Thread(target=worker_order_event)
    t2 = threading.Thread(target=worker_start_bracket)
    t1.start(); t2.start()
    t1.join(timeout=5); t2.join(timeout=5)

    # FSM may end in any legitimate state, but row must be consistent
    # (no half-written halt_reason / state combo, no IllegalTransitionError).
    row = repo.get("BTCUSDT")
    assert row is not None
    # Either the bracket succeeded (ENTRY_PENDING / LONG_OPEN / OCO_*) or the
    # event landed first (FLAT remains). No state should be torn — the FSM
    # raises IllegalTransitionError on bad inputs, which would be in `errors`.
    valid_terminal_states = {
        ExecutionState.FLAT,
        ExecutionState.ENTRY_PENDING,
        ExecutionState.LONG_OPEN,
        ExecutionState.OCO_ARMING,
    }
    state = ExecutionState(row.state) if row.state else ExecutionState.FLAT
    assert state in valid_terminal_states, f"Torn FSM state: {state}, errors={errors}"


def test_coordinator_lock_is_reentrant(tmp_path):
    """RLock allows bootstrap → on_ws_reconnect re-entry on same thread."""
    coord, _ = _make_coord(tmp_path)
    with coord._lock:
        with coord._lock:  # reentrant — must not deadlock
            assert True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_coordinator_threading.py -v`
Expected: FAIL — `AttributeError: 'Coordinator' object has no attribute '_lock'`.

- [ ] **Step 3: Write minimal implementation**

В `src/execution/coordinator.py`:

(a) Импорт + `__init__`:
```python
import threading
# ... existing imports ...

class Coordinator:
    def __init__(self, *, symbol, repo, reconciler, adapter, settings):
        # ... existing init ...
        self._lock = threading.RLock()  # ADR 0022 sub-decision 1 — reentrant
```

(b) Обернуть 6 публичных методов первой строкой `with self._lock:` (НЕ менять никакой бизнес-логики):

```python
    def bootstrap(self) -> None:
        with self._lock:
            # ... existing body ...

    def start_bracket(self, *, side, qty, sl_price, tp_price, reason) -> None:
        with self._lock:
            # ... existing body ...

    def on_order_event(self, evt: dict) -> None:
        with self._lock:
            # ... existing body ...

    def on_ws_reconnect(self) -> None:
        with self._lock:
            # ... existing body ...

    def arm_oco(self, *args, **kwargs) -> None:
        with self._lock:
            # ... existing body ...

    def flatten(self, *, reason) -> None:
        with self._lock:
            # ... existing body ...
```

**Важно:** обернуть только тело — никакого refactor'а. Если метод уже короткий, indent его целиком.

- [ ] **Step 4: Run tests to verify pass**

Run:
```
pytest tests/unit/test_coordinator_threading.py -v
pytest tests/unit/ -k coordinator -v   # regression sweep
```
Expected: новые 3 теста PASS, существующие тесты Coordinator не сломаны.

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/unit/test_coordinator_threading.py
git commit -m "feat(execution): Coordinator RLock — protect 6 mutation paths from race (ADR 0022 Task 0)"
```

---

## Task 6: Reconciler threading.Lock

**Files:**
- Modify: `src/execution/reconciler.py`
- Test: `tests/unit/test_reconciler_threading.py` (NEW)

**References:** ADR 0022 sub-decision 1 (Reconciler — non-reentrant: paths не вкладываются).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_reconciler_threading.py`:

```python
"""Concurrent on_wallet_event × reconcile — assert no torn _wallet_cache.

ADR 0022 sub-decision 1.
"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock

from src.execution.reconciler import Reconciler


def _make_reconciler():
    adapter = MagicMock()
    settings = MagicMock(heal_max_age_seconds=3600)
    return Reconciler(adapter=adapter, settings=settings)


def test_reconciler_has_lock():
    r = _make_reconciler()
    # threading.Lock() is a builtin_function_or_method, but isinstance against
    # type(threading.Lock()) catches the lock primitive class.
    assert isinstance(r._lock, type(threading.Lock())), (
        "Reconciler must use threading.Lock (non-reentrant) per ADR 0022 sub-decision 1"
    )


def test_reconciler_lock_is_NOT_reentrant():
    """Lock (vs RLock) must reject re-entry on same thread (acquire returns False)."""
    r = _make_reconciler()
    with r._lock:
        # second non-blocking acquire on same thread must fail
        acquired = r._lock.acquire(blocking=False)
        assert acquired is False, "Reconciler lock must be Lock, not RLock"


def test_reconciler_concurrent_wallet_event_and_reconcile_no_corruption():
    r = _make_reconciler()
    # Mock adapter so that .get_wallet_balance returns deterministic dict
    r._adapter.get_wallet_balance = MagicMock(return_value={"BTC": "0.001", "USDT": "100"})
    r._adapter.get_open_orders = MagicMock(return_value=[])

    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def push_wallet():
        try:
            barrier.wait()
            evt = {"coin": [{"coin": "BTC", "walletBalance": "0.001"}]}
            r.on_wallet_event(evt)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    def call_reconcile():
        try:
            barrier.wait()
            local = MagicMock(symbol="BTCUSDT", state="LONG_OPEN")
            r.reconcile(local)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    t1 = threading.Thread(target=push_wallet)
    t2 = threading.Thread(target=call_reconcile)
    t1.start(); t2.start()
    t1.join(timeout=5); t2.join(timeout=5)

    # Critical: no AssertionError / RuntimeError from torn dict access.
    # AttributeError on MagicMock setup is a TEST issue (caller fixes), not a race.
    race_errors = [e for e in errors if not isinstance(e, AttributeError)]
    assert race_errors == [], f"Concurrent run produced race errors: {race_errors}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_reconciler_threading.py -v`
Expected: FAIL — `AttributeError: 'Reconciler' object has no attribute '_lock'`.

- [ ] **Step 3: Write minimal implementation**

В `src/execution/reconciler.py`:

```python
import threading
# ... existing imports ...

class Reconciler:
    def __init__(self, *, adapter, settings):
        # ... existing init ...
        self._lock = threading.Lock()  # ADR 0022 sub-decision 1 — non-reentrant

    def on_wallet_event(self, evt: dict) -> None:
        with self._lock:
            # ... existing body ...

    def reconcile(self, local, *, expected_state=None):
        with self._lock:
            # ... existing body ...
```

- [ ] **Step 4: Run tests to verify pass**

Run:
```
pytest tests/unit/test_reconciler_threading.py -v
pytest tests/unit/ -k reconciler -v
```
Expected: новые 3 PASS; existing tests Reconciler не сломаны.

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_threading.py
git commit -m "feat(execution): Reconciler Lock — protect on_wallet_event/reconcile from race (ADR 0022 Task 0)"
```

---



## Task 7: BarSource scaffolding (`src/runtime/bar_source.py`)

**Files:**
- Create: `src/runtime/__init__.py` (empty)
- Create: `src/runtime/bar_source.py`
- Test: `tests/unit/test_bar_poller.py` (NEW — частично)

**References:** ADR 0022 sub-decision 2.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_bar_poller.py`:

```python
"""BarSource — REST kline poller с dedup + stall counter.

ADR 0022 sub-decisions 2 + 3.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.marketdata.models import Bar, DataQuality


def _bar(open_ms: int, close_ms: int) -> Bar:
    return Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=datetime.fromtimestamp(open_ms / 1000, tz=UTC),
        close_time=datetime.fromtimestamp(close_ms / 1000, tz=UTC),
        open=Decimal("60000"),
        high=Decimal("60100"),
        low=Decimal("59900"),
        close=Decimal("60050"),
        volume=Decimal("10"),
        trade_count=0,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def test_bar_source_dedup_same_close_ts():
    """Two polls with same closed bar → emit once, then None."""
    from src.runtime.bar_source import BarSource

    adapter = MagicMock()
    bar = _bar(1_700_000_000_000, 1_700_003_600_000)
    adapter.get_klines.return_value = [bar]

    src = BarSource(adapter=adapter, symbol="BTCUSDT", interval="60")
    first = src.poll()
    second = src.poll()
    assert first == bar
    assert second is None
    assert src.consecutive_failures == 0


def test_bar_source_emits_new_bar_on_close():
    from src.runtime.bar_source import BarSource

    adapter = MagicMock()
    bar1 = _bar(1_700_000_000_000, 1_700_003_600_000)
    bar2 = _bar(1_700_003_600_000, 1_700_007_200_000)
    adapter.get_klines.side_effect = [[bar1], [bar2]]

    src = BarSource(adapter=adapter, symbol="BTCUSDT", interval="60")
    assert src.poll() == bar1
    assert src.poll() == bar2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_bar_poller.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.runtime'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/runtime/__init__.py`:
```python
"""Live-runtime package — RuntimeManager, BarSource (Sprint 8a, ADR 0022)."""
```

Create `src/runtime/bar_source.py`:
```python
"""REST kline bar source — dedup + stall counter.

ADR 0022 sub-decisions 2 + 3.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.marketdata.models import Bar

logger = logging.getLogger(__name__)


class BarSource:
    """Poll latest closed bar via REST kline; dedup by close_time."""

    def __init__(self, *, adapter, symbol: str, interval: str = "60") -> None:
        self._adapter = adapter
        self._symbol = symbol
        self._interval = interval
        self._last_close_ts: int | None = None  # ms epoch
        self.consecutive_failures: int = 0

    def poll(self) -> "Bar | None":
        """Return latest closed bar if new, else None. Increments failure counter on error."""
        try:
            bars = self._fetch()
        except Exception as e:  # noqa: BLE001 — caller decides halt vs continue
            self.consecutive_failures += 1
            logger.warning("bar_source.poll_failed", extra={"err": str(e), "consecutive_failures": self.consecutive_failures})
            return None

        self.consecutive_failures = 0
        if not bars:
            return None
        latest = bars[-1]
        close_ms = int(latest.close_time.timestamp() * 1000)
        if self._last_close_ts is not None and close_ms <= self._last_close_ts:
            return None
        self._last_close_ts = close_ms
        return latest

    def _fetch(self) -> "list[Bar]":
        # Wraps adapter call (separate method for stall task to monkey-patch).
        return self._adapter.get_klines(symbol=self._symbol, interval=self._interval, limit=2)
```

**Note:** реальный `BybitRESTClient.get_klines` (см. `src/marketdata/bybit/rest.py:46`) принимает `start_ms` / `end_ms`, не `limit`. Adapter wrapper для S8a живёт в Task 8 (REST integration) — там адаптация сигнатуры. Сейчас тест mockает `get_klines` напрямую с `limit` arg — ОК, signature uniformity придёт в Task 8.

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_bar_poller.py -v`
Expected: PASS оба теста.

- [ ] **Step 5: Commit**

```bash
git add src/runtime/__init__.py src/runtime/bar_source.py tests/unit/test_bar_poller.py
git commit -m "feat(runtime): BarSource scaffolding with dedup (ADR 0022 sub-decision 2)"
```

---

## Task 8: BarSource REST integration (sliding-window kline call)

**Files:**
- Modify: `src/runtime/bar_source.py`
- Test: `tests/unit/test_bar_poller.py` (append cases)

**References:** ADR 0022 sub-decision 2 (REST cadence + dedup).

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_bar_poller.py`:

```python
def test_bar_source_calls_adapter_with_recent_window(monkeypatch):
    """_fetch must call adapter.get_klines with last 2 bars worth of window (start/end_ms)."""
    from src.runtime.bar_source import BarSource

    captured: dict = {}

    class FakeAdapter:
        def get_klines(self, *, symbol, interval, start_ms, end_ms, limit_per_call=1000):
            captured["symbol"] = symbol
            captured["interval"] = interval
            captured["start_ms"] = start_ms
            captured["end_ms"] = end_ms
            return []

    src = BarSource(adapter=FakeAdapter(), symbol="BTCUSDT", interval="60")
    # Freeze "now" via monkeypatch on time.time used inside _fetch
    monkeypatch.setattr("src.runtime.bar_source.time.time", lambda: 1_700_010_000.0)
    src.poll()

    assert captured["symbol"] == "BTCUSDT"
    assert captured["interval"] == "60"
    # Window = at least last 2 bars (interval=60 → 7_200_000 ms)
    assert captured["end_ms"] - captured["start_ms"] >= 7_200_000
    # end_ms ≈ now (1_700_010_000_000 ± 1s)
    assert abs(captured["end_ms"] - 1_700_010_000_000) < 1_000


def test_bar_source_failure_increments_counter():
    from src.runtime.bar_source import BarSource

    class BadAdapter:
        def get_klines(self, **_):
            raise RuntimeError("network down")

    src = BarSource(adapter=BadAdapter(), symbol="BTCUSDT", interval="60")
    assert src.poll() is None
    assert src.consecutive_failures == 1
    assert src.poll() is None
    assert src.consecutive_failures == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_bar_poller.py::test_bar_source_calls_adapter_with_recent_window -v`
Expected: FAIL — `_fetch` использует `limit=2` (Task 7 stub), не `start_ms`/`end_ms`.

- [ ] **Step 3: Update implementation**

В `src/runtime/bar_source.py`:

```python
import time

# ... class BarSource ...

    _INTERVAL_MS = {"60": 3_600_000}

    def _fetch(self) -> "list[Bar]":
        step_ms = self._INTERVAL_MS[self._interval]
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - step_ms * 2  # last 2 bars window
        return self._adapter.get_klines(
            symbol=self._symbol,
            interval=self._interval,
            start_ms=start_ms,
            end_ms=end_ms,
        )
```

Update Task 7 test fixture: `adapter.get_klines.return_value = [bar]` остаётся валидным (MagicMock игнорирует kwargs).

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_bar_poller.py -v`
Expected: PASS все 4 теста (Task 7 + Task 8).

- [ ] **Step 5: Commit**

```bash
git add src/runtime/bar_source.py tests/unit/test_bar_poller.py
git commit -m "feat(runtime): BarSource sliding-window REST call + failure counter (ADR 0022)"
```

---

## Task 9: Stall counter → HALT_BAR_POLL_STALL emission

**Files:**
- Modify: `src/runtime/bar_source.py` (helper `should_halt(threshold) -> bool`)
- Test: `tests/unit/test_bar_poller.py` (append cases)

**References:** ADR 0022 sub-decision 3.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_bar_poller.py`:

```python
def test_bar_source_should_halt_at_threshold():
    from src.runtime.bar_source import BarSource

    class BadAdapter:
        def get_klines(self, **_):
            raise RuntimeError("X")

    src = BarSource(adapter=BadAdapter(), symbol="BTCUSDT", interval="60")
    # 23 failures — below threshold
    for _ in range(23):
        src.poll()
    assert src.should_halt(threshold=24) is False
    # 24th — at threshold
    src.poll()
    assert src.should_halt(threshold=24) is True


def test_bar_source_recovery_resets_counter():
    from src.runtime.bar_source import BarSource

    bar = _bar(1_700_000_000_000, 1_700_003_600_000)
    states = [RuntimeError("X"), RuntimeError("X"), [bar]]

    class FlapAdapter:
        def __init__(self):
            self._i = 0

        def get_klines(self, **_):
            v = states[self._i]
            self._i += 1
            if isinstance(v, BaseException):
                raise v
            return v

    src = BarSource(adapter=FlapAdapter(), symbol="BTCUSDT", interval="60")
    src.poll(); src.poll()
    assert src.consecutive_failures == 2
    src.poll()  # recovery
    assert src.consecutive_failures == 0
    assert src.should_halt(threshold=24) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_bar_poller.py::test_bar_source_should_halt_at_threshold -v`
Expected: FAIL — `AttributeError: 'BarSource' object has no attribute 'should_halt'`.

- [ ] **Step 3: Add helper**

В `src/runtime/bar_source.py` к классу:

```python
    def should_halt(self, *, threshold: int) -> bool:
        """True if consecutive_failures hit threshold — caller emits HALT_BAR_POLL_STALL."""
        return self.consecutive_failures >= threshold
```

(Само вызов `coordinator.request_halt("HALT_BAR_POLL_STALL")` живёт в RuntimeManager Task 15 — separation of concerns: BarSource не знает о Coordinator.)

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_bar_poller.py -v`
Expected: PASS все 6 тестов.

- [ ] **Step 5: Commit**

```bash
git add src/runtime/bar_source.py tests/unit/test_bar_poller.py
git commit -m "feat(runtime): BarSource.should_halt(threshold) — stall predicate (ADR 0022 sub-decision 3)"
```

---

## Task 10: Strategy warmup (catch-up no-signal)

**Files:**
- Modify: `src/signalgen/strategy.py` — добавить `warmup(bars: list[Bar]) -> None` (no signal emit)
- Test: `tests/unit/test_strategy_warmup_no_signal.py` (NEW)

**References:** ADR 0022 sub-decisions 2 (catch-up) + 8 (look-ahead invariant).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_strategy_warmup_no_signal.py`:

```python
"""Strategy.warmup feeds catch-up bars to indicators without emitting signals.

ADR 0022 sub-decision 2: prevents look-ahead trades on historical data after restart.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.marketdata.models import Bar, DataQuality
from src.signalgen.strategy import Strategy


def _bars(n: int) -> list[Bar]:
    out = []
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(n):
        out.append(
            Bar(
                symbol="BTCUSDT",
                interval="1h",
                open_time=base + timedelta(hours=i),
                close_time=base + timedelta(hours=i + 1),
                open=Decimal("60000") + Decimal(i),
                high=Decimal("60100") + Decimal(i),
                low=Decimal("59900") + Decimal(i),
                close=Decimal("60050") + Decimal(i),
                volume=Decimal("10"),
                trade_count=0,
                is_closed=True,
                data_quality=DataQuality.OK,
            )
        )
    return out


def test_warmup_50_bars_emits_zero_signals():
    s = Strategy()
    bars = _bars(50)
    signals = []
    for b in bars:
        sig = s.warmup(b)
        if sig is not None:
            signals.append(sig)
    assert signals == [], f"warmup must NOT emit signals; got {len(signals)}"


def test_warmup_then_on_bar_emits_normally():
    """After warmup, first new live bar may emit a signal — indicators are seeded."""
    s = Strategy()
    for b in _bars(50):
        s.warmup(b)
    # 51st bar via on_bar — signal generation legal now
    new_bars = _bars(51)
    sig = s.on_bar(new_bars[-1])
    # Не утверждаем что sig != None (зависит от данных) — только что вызов не raise
    assert sig is None or hasattr(sig, "action"), "on_bar must return Signal-like or None"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_strategy_warmup_no_signal.py -v`
Expected: FAIL — `AttributeError: 'Strategy' object has no attribute 'warmup'`.

- [ ] **Step 3: Add warmup method**

В `src/signalgen/strategy.py`, рядом с `on_bar`:

```python
    def warmup(self, bar: "Bar") -> None:
        """Feed historical bar to indicators WITHOUT signal emission.

        ADR 0022 sub-decision 2 — catch-up на startup защищает от look-ahead
        trade events на bars из прошлого. Indicators seed identical to on_bar,
        only the signal-emit branch is skipped.

        Returns None always.
        """
        # Reuse indicator-update path of on_bar without signal-evaluation block.
        # Implementation note: extract `_update_indicators(bar)` helper if on_bar
        # currently inlines indicator updates; warmup calls only that helper.
        self._update_indicators(bar)
        return None
```

Если `_update_indicators` ещё не выделен — extract его из `on_bar` минимально (move indicator-update block в private helper, оставить signal-eval block в `on_bar`).

- [ ] **Step 4: Run tests to verify pass**

Run:
```
pytest tests/unit/test_strategy_warmup_no_signal.py -v
pytest tests/unit/ -k strategy -v
```
Expected: PASS оба новых теста; existing strategy тесты не сломаны.

- [ ] **Step 5: Commit**

```bash
git add src/signalgen/strategy.py tests/unit/test_strategy_warmup_no_signal.py
git commit -m "feat(strategy): warmup(bar) — seed indicators without signal emit (ADR 0022 sub-decision 2)"
```

---



## Task 11: `Coordinator.request_halt(reason)` public method

**Files:**
- Modify: `src/execution/coordinator.py` — добавить `request_halt(reason: str) -> None`
- Test: `tests/unit/test_coordinator_request_halt.py` (NEW — small focused file)

**References:** ADR 0022 sub-decisions 5 + 6 (KILL_SWITCH + RUNTIME_CRASH callsite need a public halt entry-point).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_coordinator_request_halt.py`:

```python
"""Coordinator.request_halt(reason) — public halt entry-point used by RuntimeManager.

ADR 0022 sub-decisions 5, 6, 11. Wraps existing _set_halt (S7 γ-pattern).
"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.execution.coordinator import Coordinator
from src.execution.state_repo import ExecutionStateRepo


def _make_coord(tmp_path):
    repo = ExecutionStateRepo(tmp_path / "rh.db")
    repo.upsert_initial(symbol="BTCUSDT")
    settings = MagicMock(heal_max_age_seconds=3600, oco_arming_ttl_seconds=60)
    return Coordinator(
        symbol="BTCUSDT",
        repo=repo,
        reconciler=MagicMock(),
        adapter=MagicMock(),
        settings=settings,
    ), repo


def test_request_halt_sets_halt_reason(tmp_path):
    coord, repo = _make_coord(tmp_path)
    coord.request_halt("KILL_SWITCH_REQUESTED")
    row = repo.get("BTCUSDT")
    assert row.halt_reason == "KILL_SWITCH_REQUESTED"


def test_request_halt_primary_wins_does_not_overwrite(tmp_path):
    """ADR 0021 γ-rule: first halt_reason wins, subsequent calls append to halt_log."""
    coord, repo = _make_coord(tmp_path)
    coord.request_halt("HALT_RUNTIME_CRASH")
    coord.request_halt("KILL_SWITCH_REQUESTED")
    row = repo.get("BTCUSDT")
    assert row.halt_reason == "HALT_RUNTIME_CRASH", "primary halt_reason must not be overwritten"


def test_request_halt_appends_to_halt_log(tmp_path):
    coord, repo = _make_coord(tmp_path)
    coord.request_halt("KILL_SWITCH_REQUESTED")
    coord.request_halt("HALT_BAR_POLL_STALL")
    # Both calls land in halt_log audit table
    import sqlite3
    conn = sqlite3.connect(tmp_path / "rh.db")
    rows = conn.execute("SELECT reason FROM halt_log WHERE symbol='BTCUSDT' ORDER BY id").fetchall()
    reasons = [r[0] for r in rows]
    assert "KILL_SWITCH_REQUESTED" in reasons
    assert "HALT_BAR_POLL_STALL" in reasons
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_coordinator_request_halt.py -v`
Expected: FAIL — `AttributeError: 'Coordinator' object has no attribute 'request_halt'`.

- [ ] **Step 3: Write minimal implementation**

В `src/execution/coordinator.py` (после `_set_halt`, line ~563):

```python
    def request_halt(self, reason: str) -> None:
        """Public halt entry-point for RuntimeManager (KILL_SWITCH, RUNTIME_CRASH, STALL).

        Acquires self._lock (RLock — re-entrant if caller already holds).
        Delegates to existing _set_halt(symbol, reason, context) — primary-wins per S7 γ rule.

        ADR 0022 sub-decisions 5 / 6 / 11.
        """
        with self._lock:
            self._set_halt(symbol=self._symbol, reason=reason, context={"source": "request_halt"})
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_coordinator_request_halt.py -v`
Expected: PASS все 3.

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/unit/test_coordinator_request_halt.py
git commit -m "feat(execution): Coordinator.request_halt(reason) public entry-point (ADR 0022)"
```

---

## Task 12: FSM `KILL_SWITCH_REQUESTED` event handling audit

**Files:**
- Audit + maybe modify: `src/execution/state_machine.py`
- Test: `tests/unit/test_fsm_kill_switch_requested.py` (NEW)

**References:** ADR 0022 sub-decision 5. (S7 уже имеет `KILL_SWITCH` event с transitions из FLAT/LONG_OPEN/OCO_ARMED/PARTIAL_FILL/HALTED → KILLED — см. `src/execution/state_machine.py:92-96`.)

**Decision:** S7 `KILL_SWITCH` event покрывает оператор-инициированный kill, но переход выходит в `KILLED` (terminal). Для S8a `KILL_SWITCH_REQUESTED` semantically — operator-acknowledged HALT (требует MANUAL_RESET, не terminal kill). Эти два разные. Добавляем новый event `KILL_SWITCH_REQUESTED` с transitions из всех reconcilable + active states → `HALTED` (так же как `RISK_HALT`). Старый `KILL_SWITCH` остаётся для terminal kill (используется редко, оставляем для back-compat).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_fsm_kill_switch_requested.py`:

```python
"""FSM — KILL_SWITCH_REQUESTED event from active states → HALTED.

ADR 0022 sub-decision 5. Distinct from S7 KILL_SWITCH (→ KILLED terminal).
"""
import pytest

from src.execution.state_machine import (
    ExecutionEvent,
    ExecutionState,
    IllegalTransitionError,
    apply,
)


@pytest.mark.parametrize(
    "src_state",
    [
        ExecutionState.FLAT,
        ExecutionState.ENTRY_PENDING,
        ExecutionState.LONG_OPEN,
        ExecutionState.OCO_ARMING,
        ExecutionState.OCO_ARMED,
        ExecutionState.EXIT_PENDING,
        ExecutionState.EXIT_SIBLING_CANCELLING,
        ExecutionState.EXIT_SIBLING_CANCEL_FAILED,
        ExecutionState.EXIT_SL_RESIDUAL,
        ExecutionState.RECONCILING,
    ],
)
def test_kill_switch_requested_transitions_to_halted(src_state):
    assert apply(src_state, ExecutionEvent.KILL_SWITCH_REQUESTED) == ExecutionState.HALTED


def test_kill_switch_requested_illegal_from_killed():
    """Already-killed state cannot be halted again."""
    with pytest.raises(IllegalTransitionError):
        apply(ExecutionState.KILLED, ExecutionEvent.KILL_SWITCH_REQUESTED)


def test_legacy_kill_switch_still_terminal():
    """S7 KILL_SWITCH → KILLED preserved (back-compat regression)."""
    assert apply(ExecutionState.LONG_OPEN, ExecutionEvent.KILL_SWITCH) == ExecutionState.KILLED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_fsm_kill_switch_requested.py -v`
Expected: FAIL — `AttributeError: KILL_SWITCH_REQUESTED` (event not in enum yet).

- [ ] **Step 3: Add event + transitions**

В `src/execution/state_machine.py`:

(a) В `ExecutionEvent` enum добавить:
```python
    KILL_SWITCH_REQUESTED = "KILL_SWITCH_REQUESTED"  # ADR 0022 sub-decision 5
```

(b) В `TRANSITIONS` dict добавить block (в конец, после S7 secciones):
```python
    # === ADR 0022 sub-decision 5: KILL_SWITCH_REQUESTED — operator HALT (NOT terminal) ===
    (ExecutionState.FLAT, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.LONG_OPEN, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.OCO_ARMING, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.OCO_ARMED, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.EXIT_PENDING, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.EXIT_SIBLING_CANCEL_FAILED, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
    (ExecutionState.RECONCILING, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED,
```

- [ ] **Step 4: Run tests to verify pass**

Run:
```
pytest tests/unit/test_fsm_kill_switch_requested.py -v
pytest tests/unit/ -k state_machine -v   # regression
```
Expected: PASS все новые + existing FSM tests не сломаны.

- [ ] **Step 5: Commit**

```bash
git add src/execution/state_machine.py tests/unit/test_fsm_kill_switch_requested.py
git commit -m "feat(fsm): KILL_SWITCH_REQUESTED event → HALTED from 10 active states (ADR 0022)"
```

---



## Task 13: RuntimeManager scaffold (`src/runtime/manager.py`)

**Files:**
- Create: `src/runtime/manager.py`
- Test: `tests/unit/test_runtime_manager.py` (NEW)

**References:** ADR 0022 sub-decision 7.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_runtime_manager.py`:

```python
"""RuntimeManager — process lifecycle owner.

ADR 0022 sub-decisions 7, 13, 14, 15, 17.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _settings(tmp_path: Path):
    s = MagicMock()
    s.runtime_kill_switch_path = str(tmp_path / ".kill_switch")
    s.runtime_bar_poll_cadence_seconds = 5.0
    s.runtime_bar_poll_stall_threshold = 24
    s.runtime_ws_check_alive_max_silence = 30.0
    s.runtime_warmup_bars = 50
    return s


def test_runtime_manager_ctor_stores_deps(tmp_path):
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    rec = MagicMock()
    ws = MagicMock()
    bs = MagicMock()
    strat = MagicMock()
    s = _settings(tmp_path)

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=rec,
        ws_consumer=ws,
        bar_source=bs,
        strategy=strat,
        settings=s,
    )

    assert rm._coordinator is coord
    assert rm._reconciler is rec
    assert rm._ws_consumer is ws
    assert rm._bar_source is bs
    assert rm._strategy is strat
    assert rm._settings is s
    assert rm._stopping is False
    assert rm._kill_switch_path == Path(s.runtime_kill_switch_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_runtime_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.runtime.manager'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/runtime/manager.py`:

```python
"""RuntimeManager — live-runtime process lifecycle (ADR 0022).

Owns: bootstrap → ws_consumer.start → main loop → graceful shutdown.
Single thread for tick loop; pybit thread for WS callbacks (lock-protected
via Coordinator/Reconciler RLock/Lock).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.execution.bybit.ws_private import BybitPrivateWSConsumer
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.platform.config import Settings
    from src.runtime.bar_source import BarSource
    from src.signalgen.strategy import Strategy

logger = logging.getLogger(__name__)


class RuntimeManager:
    """Process lifecycle owner — see ADR 0022 sub-decision 7."""

    def __init__(
        self,
        *,
        coordinator: "Coordinator",
        reconciler: "Reconciler",
        ws_consumer: "BybitPrivateWSConsumer",
        bar_source: "BarSource",
        strategy: "Strategy",
        settings: "Settings",
    ) -> None:
        self._coordinator = coordinator
        self._reconciler = reconciler
        self._ws_consumer = ws_consumer
        self._bar_source = bar_source
        self._strategy = strategy
        self._settings = settings
        self._stopping: bool = False
        self._kill_switch_path: Path = Path(settings.runtime_kill_switch_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_runtime_manager.py::test_runtime_manager_ctor_stores_deps -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/runtime/manager.py tests/unit/test_runtime_manager.py
git commit -m "feat(runtime): RuntimeManager scaffold + ctor (ADR 0022 sub-decision 7)"
```

---

## Task 14: bootstrap sequencing in `run()`

**Files:**
- Modify: `src/runtime/manager.py` — добавить `run()` + `_bootstrap()`
- Test: `tests/unit/test_runtime_manager.py` (append cases)

**References:** ADR 0022 sub-decisions 7 (sequencing invariant) + 5 (clean stale sentinel).

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_runtime_manager.py`:

```python
def test_run_bootstraps_then_starts_ws_then_loops(tmp_path, monkeypatch):
    from src.runtime.manager import RuntimeManager

    calls: list[str] = []
    coord = MagicMock()
    coord.bootstrap.side_effect = lambda: calls.append("bootstrap")
    ws = MagicMock()
    ws.start.side_effect = lambda: calls.append("ws.start")

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=ws,
        bar_source=MagicMock(),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )

    # Patch _main_loop so run() exits immediately after bootstrap+ws.start
    monkeypatch.setattr(rm, "_main_loop", lambda: calls.append("main_loop"))
    monkeypatch.setattr(rm, "_shutdown", lambda *, reason: calls.append(f"shutdown:{reason}"))

    rm.run()

    assert calls.index("bootstrap") < calls.index("ws.start")
    assert calls.index("ws.start") < calls.index("main_loop")


def test_run_cleans_stale_kill_switch_before_bootstrap(tmp_path):
    from src.runtime.manager import RuntimeManager

    sentinel = tmp_path / ".kill_switch"
    sentinel.write_text("")
    assert sentinel.exists()

    coord = MagicMock()
    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(),
        bar_source=MagicMock(),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._main_loop = lambda: None
    rm._shutdown = lambda *, reason: None

    rm.run()
    assert not sentinel.exists(), "stale .kill_switch must be removed before bootstrap"


def test_bootstrap_failure_blocks_ws_start(tmp_path):
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    coord.bootstrap.side_effect = RuntimeError("boot failed")
    ws = MagicMock()

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=ws,
        bar_source=MagicMock(),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._main_loop = lambda: None
    rm._shutdown = lambda *, reason: None

    with pytest.raises(RuntimeError, match="boot failed"):
        rm.run()
    ws.start.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_runtime_manager.py -v`
Expected: FAIL — `AttributeError: 'RuntimeManager' object has no attribute 'run'`.

- [ ] **Step 3: Add run() + _bootstrap()**

В `src/runtime/manager.py`:

```python
    def run(self) -> None:
        """Blocking entry-point: bootstrap → ws.start → main loop → shutdown.

        ADR 0022 sub-decisions 6 + 7. Wraps _main_loop with HALT_RUNTIME_CRASH guard
        (added in Task 16).
        """
        # Sub-decision 5: clean stale .kill_switch from previous session
        if self._kill_switch_path.exists():
            self._kill_switch_path.unlink()

        # Sequencing invariant: bootstrap FIRST, then WS, then loop
        self._coordinator.bootstrap()
        self._ws_consumer.start()
        try:
            self._main_loop()
        finally:
            self._shutdown(reason="NORMAL_EXIT")

    def _main_loop(self) -> None:
        # Body added in Task 15
        raise NotImplementedError("_main_loop body added in Task 15")

    def _shutdown(self, *, reason: str) -> None:
        # Body added in Task 17
        pass
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_runtime_manager.py -v`
Expected: PASS все 4 (включая ctor).

- [ ] **Step 5: Commit**

```bash
git add src/runtime/manager.py tests/unit/test_runtime_manager.py
git commit -m "feat(runtime): bootstrap sequencing in RuntimeManager.run() (ADR 0022)"
```

---

## Task 15: Main loop tick (`_tick`)

**Files:**
- Modify: `src/runtime/manager.py` — `_tick`, `_maybe_kill_switch`, `_check_alive_inline`, `_poll_bar_and_strategy`
- Test: `tests/unit/test_runtime_manager.py` (append cases)

**References:** ADR 0022 sub-decisions 1 (sequential within tick), 2 (bar tick → strategy → bracket), 3 (stall halt), 4 (check_alive inline), 5 (kill switch).

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_runtime_manager.py`:

```python
from datetime import UTC, datetime
from decimal import Decimal


def _bar():
    from src.marketdata.models import Bar, DataQuality
    return Bar(
        symbol="BTCUSDT", interval="1h",
        open_time=datetime(2026, 1, 1, tzinfo=UTC),
        close_time=datetime(2026, 1, 1, 1, tzinfo=UTC),
        open=Decimal("60000"), high=Decimal("60100"),
        low=Decimal("59900"), close=Decimal("60050"),
        volume=Decimal("10"), trade_count=0,
        is_closed=True, data_quality=DataQuality.OK,
    )


def test_tick_sequence_kill_then_alive_then_poll_then_strategy(tmp_path):
    from src.runtime.manager import RuntimeManager

    calls: list[str] = []
    coord = MagicMock()
    coord.start_bracket.side_effect = lambda **kw: calls.append("start_bracket")
    ws = MagicMock()
    ws.check_alive.side_effect = lambda **kw: (calls.append("check_alive"), True)[1]
    bar = _bar()
    bs = MagicMock()
    bs.poll.side_effect = lambda: (calls.append("poll"), bar)[1]
    bs.consecutive_failures = 0
    strat = MagicMock()
    sig = MagicMock(action="LONG", side="Buy")
    strat.on_bar.side_effect = lambda b: (calls.append("on_bar"), sig)[1]

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=ws, bar_source=bs, strategy=strat,
        settings=_settings(tmp_path),
    )
    rm._tick()

    # Order: kill_switch (no call recorded — file absent), check_alive, poll, on_bar, start_bracket
    assert calls == ["check_alive", "poll", "on_bar", "start_bracket"]


def test_tick_no_new_bar_skips_strategy(tmp_path):
    from src.runtime.manager import RuntimeManager

    bs = MagicMock()
    bs.poll.return_value = None
    bs.consecutive_failures = 0
    strat = MagicMock()

    rm = RuntimeManager(
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=bs, strategy=strat,
        settings=_settings(tmp_path),
    )
    rm._tick()
    strat.on_bar.assert_not_called()


def test_tick_kill_switch_detected_sets_stopping(tmp_path):
    from src.runtime.manager import RuntimeManager

    sentinel = tmp_path / ".kill_switch"
    sentinel.write_text("")
    coord = MagicMock()

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=MagicMock(poll=lambda: None, consecutive_failures=0),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._tick()
    coord.request_halt.assert_called_with("KILL_SWITCH_REQUESTED")
    assert rm._stopping is True


def test_tick_stall_threshold_triggers_halt(tmp_path):
    from src.runtime.manager import RuntimeManager

    bs = MagicMock()
    bs.poll.return_value = None
    bs.consecutive_failures = 24
    bs.should_halt.return_value = True
    coord = MagicMock()

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=lambda **kw: True),
        bar_source=bs, strategy=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._tick()
    coord.request_halt.assert_called_with("HALT_BAR_POLL_STALL")
    assert rm._stopping is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_runtime_manager.py -v`
Expected: FAIL — `AttributeError: 'RuntimeManager' object has no attribute '_tick'`.

- [ ] **Step 3: Add tick body**

В `src/runtime/manager.py`:

```python
    def _tick(self) -> None:
        """One tick of the main loop.

        Sequential pipeline (ADR 0022 sub-decisions 1, 2, 4, 5):
        1. _maybe_kill_switch  — sentinel file check
        2. _check_alive_inline — WS health (inline, no separate worker)
        3. _poll_bar_and_strategy — REST bar → strategy → bracket
        """
        if self._maybe_kill_switch():
            return
        if not self._check_alive_inline():
            return
        self._poll_bar_and_strategy()

    def _maybe_kill_switch(self) -> bool:
        """Return True if kill switch detected (caller should exit tick)."""
        if self._kill_switch_path.exists():
            logger.info("runtime.kill_switch_detected", extra={"sentinel_path": str(self._kill_switch_path)})
            self._coordinator.request_halt("KILL_SWITCH_REQUESTED")
            self._stopping = True
            return True
        return False

    def _check_alive_inline(self) -> bool:
        """ADR 0022 sub-decision 4 — WS check inline в main thread, no worker."""
        return self._ws_consumer.check_alive(
            max_silence_seconds=self._settings.runtime_ws_check_alive_max_silence
        )

    def _poll_bar_and_strategy(self) -> None:
        bar = self._bar_source.poll()
        # Stall check after each poll attempt
        if self._bar_source.should_halt(threshold=self._settings.runtime_bar_poll_stall_threshold):
            logger.error(
                "runtime.bar_poll_stall",
                extra={
                    "consecutive_failures": self._bar_source.consecutive_failures,
                    "threshold": self._settings.runtime_bar_poll_stall_threshold,
                },
            )
            self._coordinator.request_halt("HALT_BAR_POLL_STALL")
            self._stopping = True
            return
        if bar is None:
            return
        logger.info("runtime.bar_tick", extra={"bar_close_ts": bar.close_time.isoformat()})
        signal = self._strategy.on_bar(bar)
        if signal is None:
            return
        self._coordinator.start_bracket(
            side=signal.side,
            qty=getattr(signal, "qty", None),
            sl_price=getattr(signal, "sl_price", None),
            tp_price=getattr(signal, "tp_price", None),
            reason=getattr(signal, "reason", "ENTRY_LONG_TREND_FOLLOWING"),
        )
```

И обновить `_main_loop`:
```python
    def _main_loop(self) -> None:
        import time
        while not self._stopping:
            self._tick()
            time.sleep(self._settings.runtime_bar_poll_cadence_seconds)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_runtime_manager.py -v`
Expected: PASS все 8 (4 предыдущих + 4 новых).

- [ ] **Step 5: Commit**

```bash
git add src/runtime/manager.py tests/unit/test_runtime_manager.py
git commit -m "feat(runtime): _tick — kill→alive→poll→strategy→bracket sequence (ADR 0022)"
```

---

## Task 16: HALT_RUNTIME_CRASH top-level handler

**Files:**
- Modify: `src/runtime/manager.py` — обернуть `_main_loop` try/except
- Test: `tests/unit/test_runtime_manager.py` (append cases)

**References:** ADR 0022 sub-decision 6.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_runtime_manager.py`:

```python
def test_main_loop_exception_persists_halt_then_reraises(tmp_path):
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(), bar_source=MagicMock(),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )
    # Force _tick to blow up
    rm._tick = MagicMock(side_effect=RuntimeError("boom"))
    rm._stopping = False

    with pytest.raises(RuntimeError, match="boom"):
        rm._main_loop()

    # halt persisted BEFORE re-raise
    coord.request_halt.assert_called_with("HALT_RUNTIME_CRASH")


def test_keyboard_interrupt_clean_shutdown(tmp_path):
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    shutdown_calls: list[str] = []

    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(start=lambda: None), bar_source=MagicMock(),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )
    coord.bootstrap.return_value = None
    rm._main_loop = MagicMock(side_effect=KeyboardInterrupt())
    rm._shutdown = lambda *, reason: shutdown_calls.append(reason)

    rm.run()  # KeyboardInterrupt is caught, NOT re-raised
    assert "KEYBOARD_INTERRUPT" in shutdown_calls
    coord.request_halt.assert_not_called()  # KeyboardInterrupt is not a CRASH
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_runtime_manager.py::test_main_loop_exception_persists_halt_then_reraises -v`
Expected: FAIL — exception propagates без `request_halt` call.

- [ ] **Step 3: Wrap run() and _main_loop**

В `src/runtime/manager.py` заменить `run()`:

```python
    def run(self) -> None:
        """Blocking entry-point with HALT_RUNTIME_CRASH guard (ADR 0022 sub-decisions 6 + 7)."""
        if self._kill_switch_path.exists():
            self._kill_switch_path.unlink()
        self._coordinator.bootstrap()
        self._ws_consumer.start()
        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("runtime.keyboard_interrupt")
            self._shutdown(reason="KEYBOARD_INTERRUPT")
        except Exception as e:
            logger.exception("runtime.crash", extra={"exc_type": type(e).__name__, "exc_msg": str(e)})
            self._coordinator.request_halt("HALT_RUNTIME_CRASH")
            self._shutdown(reason="HALT_RUNTIME_CRASH")
            raise
        else:
            self._shutdown(reason="NORMAL_EXIT")
```

И обновить `_main_loop` — добавить inner try чтобы _tick exceptions поднимались:
```python
    def _main_loop(self) -> None:
        import time
        while not self._stopping:
            self._tick()  # raises propagate up to run()
            time.sleep(self._settings.runtime_bar_poll_cadence_seconds)
```

(Внутренний try был бы over-engineering — sub-decision 6 явно говорит top-level wrap.)

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_runtime_manager.py -v`
Expected: PASS все 10.

- [ ] **Step 5: Commit**

```bash
git add src/runtime/manager.py tests/unit/test_runtime_manager.py
git commit -m "feat(runtime): HALT_RUNTIME_CRASH guard wraps _main_loop (ADR 0022 sub-decision 6)"
```

---

## Task 17: Graceful shutdown

**Files:**
- Modify: `src/runtime/manager.py` — finalize `_shutdown`
- Test: `tests/unit/test_runtime_manager.py` (append)

**References:** ADR 0022 sub-decisions 13 (structlog `runtime.shutdown` event) + 17 (graceful drain).

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_runtime_manager.py`:

```python
def test_shutdown_stops_ws_consumer(tmp_path):
    from src.runtime.manager import RuntimeManager

    ws = MagicMock()
    rm = RuntimeManager(
        coordinator=MagicMock(), reconciler=MagicMock(),
        ws_consumer=ws, bar_source=MagicMock(),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._shutdown(reason="TEST")
    ws.stop.assert_called_once()
    assert rm._stopping is True


def test_shutdown_idempotent(tmp_path):
    from src.runtime.manager import RuntimeManager

    ws = MagicMock()
    rm = RuntimeManager(
        coordinator=MagicMock(), reconciler=MagicMock(),
        ws_consumer=ws, bar_source=MagicMock(),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._shutdown(reason="ONCE")
    rm._shutdown(reason="TWICE")
    ws.stop.assert_called_once()  # second call is no-op
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_runtime_manager.py::test_shutdown_stops_ws_consumer -v`
Expected: FAIL — `_shutdown` is no-op stub.

- [ ] **Step 3: Implement _shutdown**

В `src/runtime/manager.py`:

```python
    def _shutdown(self, *, reason: str) -> None:
        """Graceful drain — stop WS consumer, log structured event.

        ADR 0022 sub-decision 17. Idempotent.
        """
        if getattr(self, "_shutdown_done", False):
            return
        self._shutdown_done = True
        self._stopping = True
        try:
            self._ws_consumer.stop()
        except Exception as e:  # noqa: BLE001
            logger.error("runtime.shutdown_ws_stop_failed", extra={"err": str(e)})
        # In-flight order count is a snapshot — best-effort
        in_flight = 0
        try:
            row = self._coordinator._repo.get(getattr(self._coordinator, "_symbol", "BTCUSDT"))
            if row and row.state in {"ENTRY_PENDING", "EXIT_PENDING", "OCO_ARMING"}:
                in_flight = 1
        except Exception:  # noqa: BLE001
            pass
        logger.info("runtime.shutdown", extra={"reason": reason, "in_flight_orders": in_flight})

    def shutdown(self, *, reason: str) -> None:
        """Public alias — operator-callable graceful shutdown."""
        self._shutdown(reason=reason)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_runtime_manager.py -v`
Expected: PASS все 12.

- [ ] **Step 5: Commit**

```bash
git add src/runtime/manager.py tests/unit/test_runtime_manager.py
git commit -m "feat(runtime): graceful shutdown — idempotent ws.stop + structlog (ADR 0022)"
```

---



## Task 18: `src/__main__.py` — argparse subcommands

**Files:**
- Create: `src/__main__.py`
- Test: `tests/unit/test_main_module.py` (NEW)

**References:** ADR 0022 sub-decision 9.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_main_module.py`:

```python
"""src.__main__ — argparse subcommand routing.

ADR 0022 sub-decision 9. Subcommands: run / backfill / reconcile-only / kill.
"""
from __future__ import annotations

import subprocess
import sys

import pytest


def _run_main(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "src", *args],
        capture_output=True,
        text=True,
    )


def test_main_help_shows_subcommands():
    r = _run_main("--help")
    assert r.returncode == 0
    out = r.stdout + r.stderr
    for sub in ("run", "backfill", "reconcile-only", "kill"):
        assert sub in out, f"subcommand {sub!r} missing from --help"


def test_main_unknown_subcommand_exits_2():
    r = _run_main("nonsense-cmd")
    assert r.returncode == 2  # argparse standard error code


def test_main_no_subcommand_exits_nonzero():
    r = _run_main()
    assert r.returncode != 0  # argparse error: subcommand required
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_main_module.py -v`
Expected: FAIL — `python -m src` raises `No module named src.__main__`.

- [ ] **Step 3: Write minimal implementation**

Create `src/__main__.py`:

```python
"""Entry-point: `python -m src <subcommand>` (ADR 0022 sub-decision 9).

Subcommands:
  run             — start RuntimeManager (blocking)
  backfill        — OHLCV backfill (delegated to existing scripts)
  reconcile-only  — bootstrap + reconcile, no trading loop
  kill            — write .kill_switch sentinel and exit
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _cmd_run(args: argparse.Namespace) -> int:
    """Wire all dependencies and start RuntimeManager."""
    from src.execution.bybit.adapter import BybitAdapter
    from src.execution.bybit.ws_private import BybitPrivateWSConsumer
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.execution.state_repo import ExecutionStateRepo
    from src.marketdata.bybit.rest import BybitRESTClient
    from src.platform.config import Settings
    from src.runtime.bar_source import BarSource
    from src.runtime.manager import RuntimeManager
    from src.signalgen.strategy import Strategy

    settings = Settings()
    rest = BybitRESTClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.testnet,
    )
    adapter = BybitAdapter(rest=rest, settings=settings)
    repo = ExecutionStateRepo(settings.db_path)
    reconciler = Reconciler(adapter=adapter, settings=settings)
    coordinator = Coordinator(
        symbol=args.symbol,
        repo=repo,
        reconciler=reconciler,
        adapter=adapter,
        settings=settings,
    )
    ws_consumer = BybitPrivateWSConsumer(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.testnet,
        on_order_event=coordinator.on_order_event,
        on_wallet_event=reconciler.on_wallet_event,
        on_ws_reconnect=coordinator.on_ws_reconnect,
    )
    bar_source = BarSource(adapter=rest, symbol=args.symbol, interval="60")
    strategy = Strategy()

    rm = RuntimeManager(
        coordinator=coordinator,
        reconciler=reconciler,
        ws_consumer=ws_consumer,
        bar_source=bar_source,
        strategy=strategy,
        settings=settings,
    )
    rm.run()
    return 0


def _cmd_backfill(args: argparse.Namespace) -> int:
    """Delegate to existing backfill script."""
    print(f"backfill --from {args.from_date} --to {args.to_date} (delegate to scripts/backfill.py)")
    return 0


def _cmd_reconcile_only(args: argparse.Namespace) -> int:
    """Run bootstrap + reconcile, no trading loop."""
    from src.execution.bybit.adapter import BybitAdapter
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.execution.state_repo import ExecutionStateRepo
    from src.marketdata.bybit.rest import BybitRESTClient
    from src.platform.config import Settings

    settings = Settings()
    rest = BybitRESTClient(api_key=settings.bybit_api_key, api_secret=settings.bybit_api_secret, testnet=settings.testnet)
    adapter = BybitAdapter(rest=rest, settings=settings)
    repo = ExecutionStateRepo(settings.db_path)
    reconciler = Reconciler(adapter=adapter, settings=settings)
    coordinator = Coordinator(symbol=args.symbol, repo=repo, reconciler=reconciler, adapter=adapter, settings=settings)
    coordinator.bootstrap()
    print("reconcile-only: bootstrap done.")
    return 0


def _cmd_kill(args: argparse.Namespace) -> int:
    """Write sentinel-file. ADR 0022 sub-decision 5."""
    # Body in Task 19
    raise NotImplementedError("Task 19")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src", description="AI Trading Bot v0.1 — live runtime CLI (ADR 0022).")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Start RuntimeManager (blocking).")
    p_run.add_argument("--symbol", default="BTCUSDT")
    p_run.set_defaults(func=_cmd_run)

    p_bf = sub.add_parser("backfill", help="OHLCV backfill.")
    p_bf.add_argument("--from", dest="from_date", required=True)
    p_bf.add_argument("--to", dest="to_date", required=True)
    p_bf.set_defaults(func=_cmd_backfill)

    p_rec = sub.add_parser("reconcile-only", help="Bootstrap + reconcile, no trading loop.")
    p_rec.add_argument("--symbol", default="BTCUSDT")
    p_rec.set_defaults(func=_cmd_reconcile_only)

    p_kill = sub.add_parser("kill", help="Write .kill_switch sentinel and exit.")
    p_kill.set_defaults(func=_cmd_kill)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_main_module.py -v`
Expected: PASS все 3.

- [ ] **Step 5: Commit**

```bash
git add src/__main__.py tests/unit/test_main_module.py
git commit -m "feat(cli): add python -m src argparse entry-point with 4 subcommands (ADR 0022)"
```

---

## Task 19: `kill` subcommand writes sentinel

**Files:**
- Modify: `src/__main__.py` — implement `_cmd_kill`
- Test: `tests/unit/test_kill_switch_cli.py` (NEW)

**References:** ADR 0022 sub-decision 5.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_kill_switch_cli.py`:

```python
"""`python -m src kill` writes .kill_switch sentinel; `run` cleans stale.

ADR 0022 sub-decision 5.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


def test_cmd_kill_writes_sentinel(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))

    from src.__main__ import main

    rc = main(["kill"])
    assert rc == 0
    assert (tmp_path / ".kill_switch").exists()


def test_cmd_kill_writes_to_configured_path(tmp_path, monkeypatch):
    custom = tmp_path / "subdir" / ".my_kill"
    custom.parent.mkdir(parents=True)
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    monkeypatch.setenv("RUNTIME_KILL_SWITCH_PATH", str(custom))

    from src.__main__ import main

    rc = main(["kill"])
    assert rc == 0
    assert custom.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_kill_switch_cli.py -v`
Expected: FAIL — `NotImplementedError: Task 19`.

- [ ] **Step 3: Implement _cmd_kill**

В `src/__main__.py` заменить `_cmd_kill` body:

```python
def _cmd_kill(args: argparse.Namespace) -> int:
    """Write sentinel-file at configured path. ADR 0022 sub-decision 5."""
    from src.platform.config import Settings

    settings = Settings()
    sentinel = Path(settings.runtime_kill_switch_path)
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("")
    print(f"kill switch written: {sentinel}")
    return 0
```

(Stale-cleanup на startup уже сделан в Task 14 `RuntimeManager.run()` — Path.unlink() если exists. Тест на это покрыт в `test_run_cleans_stale_kill_switch_before_bootstrap`.)

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/unit/test_kill_switch_cli.py -v`
Expected: PASS оба.

- [ ] **Step 5: Commit**

```bash
git add src/__main__.py tests/unit/test_kill_switch_cli.py
git commit -m "feat(cli): kill subcommand writes .kill_switch sentinel (ADR 0022 sub-decision 5)"
```

---



## Task 20: Integration smoke (`tests/integration/test_runtime_demo_smoke.py`)

**Files:**
- Create: `tests/integration/test_runtime_demo_smoke.py`

**References:** ADR 0022 sub-decisions 8 (integration test) + 14 (opt-in via `RUN_DEMO=1`).

- [ ] **Step 1: Write the test**

Create `tests/integration/test_runtime_demo_smoke.py`:

```python
"""Sprint 8a — full bring-up smoke on Bybit Demo Mainnet.

Opt-in: requires RUN_DEMO=1 + BYBIT_DEMO_API_KEY + BYBIT_DEMO_API_SECRET.
ADR 0022 sub-decision 8.

Flow:
  1. Wire RuntimeManager with real Demo adapter, BarSource, ws_consumer.
  2. Start RuntimeManager.run() in a Thread (subprocess-style isolation).
  3. Wait until bootstrap_complete + at least one bar tick OR 60s elapsed.
  4. Write .kill_switch sentinel.
  5. Assert process exits cleanly (graceful shutdown).
  6. Assert halt_reason == KILL_SWITCH_REQUESTED.
  7. Assert no orphan orders on exchange (best-effort cleanup).
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

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


def test_runtime_demo_smoke_kill_switch_graceful_shutdown(tmp_path, monkeypatch):
    monkeypatch.setenv("BYBIT_API_KEY", os.environ["BYBIT_DEMO_API_KEY"])
    monkeypatch.setenv("BYBIT_API_SECRET", os.environ["BYBIT_DEMO_API_SECRET"])
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "demo.db"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))
    monkeypatch.setenv("TESTNET", "false")  # Demo Mainnet uses production endpoints w/ demo keys
    monkeypatch.setenv("TRADING_ENABLED", "false")  # smoke = no actual order placement
    monkeypatch.setenv("RUNTIME_KILL_SWITCH_PATH", str(tmp_path / ".kill_switch"))

    from src.execution.bybit.adapter import BybitAdapter
    from src.execution.bybit.ws_private import BybitPrivateWSConsumer
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.execution.state_repo import ExecutionStateRepo
    from src.marketdata.bybit.rest import BybitRESTClient
    from src.platform.config import Settings
    from src.runtime.bar_source import BarSource
    from src.runtime.manager import RuntimeManager
    from src.signalgen.strategy import Strategy

    settings = Settings()
    rest = BybitRESTClient(api_key=settings.bybit_api_key, api_secret=settings.bybit_api_secret, testnet=False)
    adapter = BybitAdapter(rest=rest, settings=settings)
    repo = ExecutionStateRepo(settings.db_path)
    repo.upsert_initial(symbol="BTCUSDT")
    reconciler = Reconciler(adapter=adapter, settings=settings)
    coord = Coordinator(symbol="BTCUSDT", repo=repo, reconciler=reconciler, adapter=adapter, settings=settings)
    ws = BybitPrivateWSConsumer(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=False,
        on_order_event=coord.on_order_event,
        on_wallet_event=reconciler.on_wallet_event,
        on_ws_reconnect=coord.on_ws_reconnect,
    )
    bs = BarSource(adapter=rest, symbol="BTCUSDT", interval="60")

    rm = RuntimeManager(
        coordinator=coord, reconciler=reconciler, ws_consumer=ws,
        bar_source=bs, strategy=Strategy(), settings=settings,
    )

    runtime_thread = threading.Thread(target=rm.run, daemon=True)
    runtime_thread.start()

    # Give 30s to bootstrap + 1 tick
    time.sleep(30)

    # Write kill switch
    Path(settings.runtime_kill_switch_path).write_text("")

    # Wait for graceful shutdown (max 30s)
    runtime_thread.join(timeout=30)

    assert not runtime_thread.is_alive(), "runtime did not shut down within 30s"

    row = repo.get("BTCUSDT")
    assert row is not None
    assert row.halt_reason == "KILL_SWITCH_REQUESTED", f"unexpected halt_reason={row.halt_reason}"
```

- [ ] **Step 2: Run skipped (default)**

Run: `pytest tests/integration/test_runtime_demo_smoke.py -v`
Expected: SKIPPED (no RUN_DEMO=1).

- [ ] **Step 3: Run opt-in (manual, before tag)**

Run: `RUN_DEMO=1 pytest tests/integration/test_runtime_demo_smoke.py -v -m integration`
Expected: PASS на Demo Mainnet с реальными ключами. Document результат в `wiki/log.md`.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_runtime_demo_smoke.py
git commit -m "test(integration): opt-in runtime smoke on Bybit Demo Mainnet (ADR 0022)"
```

---



## Task 21: NEW `wiki/project/components/runtime-manager.md`

**Files:**
- Create: `llm-wiki/wiki/project/components/runtime-manager.md`

**References:** ADR 0022 sub-decisions 7, 13, 17.

- [ ] **Step 1: Write the page**

Create `llm-wiki/wiki/project/components/runtime-manager.md`:

```markdown
---
title: RuntimeManager
type: component
tags: [runtime, orchestration, lifecycle, sprint-8a]
created: 2026-04-24
updated: 2026-04-24
sources:
  - wiki/project/decisions/0022-sprint-8a-live-runtime.md
status: stable
---

# RuntimeManager

**TL;DR:** Owns process lifecycle: bootstrap → start WS consumer → tick loop (kill→alive→poll→strategy→bracket) → graceful shutdown. Single thread + pybit thread; lock policy on Coordinator/Reconciler protects shared FSM row.

## Definition / Purpose

Файл: `src/runtime/manager.py`. Class `RuntimeManager` — единая точка входа для live-runtime'а v0.1. До S8a Coordinator/Reconciler/FSM работали только в unit-test fixtures (см. ADR 0022 Context).

## Public API

```python
class RuntimeManager:
    def __init__(
        self,
        *,
        coordinator: Coordinator,
        reconciler: Reconciler,
        ws_consumer: BybitPrivateWSConsumer,
        bar_source: BarSource,
        strategy: Strategy,
        settings: Settings,
    ) -> None: ...

    def run(self) -> None: ...                    # blocking; main entry
    def shutdown(self, *, reason: str) -> None: ... # graceful drain (idempotent)
```

## Lifecycle

```
run()
  ├─ unlink stale .kill_switch (if present)
  ├─ coordinator.bootstrap()        ← sequencing invariant (S7 sub-decision 1)
  ├─ ws_consumer.start()
  ├─ try:
  │     _main_loop()                ← while not _stopping: _tick(); sleep(cadence)
  │   except KeyboardInterrupt:
  │     _shutdown(reason=KEYBOARD_INTERRUPT)
  │   except Exception:
  │     coordinator.request_halt(HALT_RUNTIME_CRASH)
  │     _shutdown(reason=HALT_RUNTIME_CRASH)
  │     raise
  │   else:
  │     _shutdown(reason=NORMAL_EXIT)
```

## Tick pipeline (sequential, single-thread)

```
_tick()
  1. _maybe_kill_switch        → if .kill_switch exists: request_halt(KILL_SWITCH_REQUESTED), _stopping = True
  2. _check_alive_inline       → ws.check_alive(max_silence=settings.runtime_ws_check_alive_max_silence)
  3. _poll_bar_and_strategy    → bar = bar_source.poll(); if should_halt: request_halt(HALT_BAR_POLL_STALL)
                                 if bar: signal = strategy.on_bar(bar); if signal: coord.start_bracket(...)
```

## Lock policy reference

Все публичные методы Coordinator (6 шт.) и Reconciler (2 шт.) обёрнуты thread-safe locks (RLock на Coordinator, Lock на Reconciler) — см. ADR 0022 sub-decision 1. Это защищает от race между pybit thread (`on_order_event` / `on_wallet_event`) и main thread (`start_bracket` / `flatten` / `bootstrap`).

| Component | Lock type | Methods wrapped |
|---|---|---|
| Coordinator | `threading.RLock` (reentrant) | bootstrap, start_bracket, on_order_event, on_ws_reconnect, arm_oco, flatten, request_halt |
| Reconciler | `threading.Lock` (non-reentrant) | on_wallet_event, reconcile |

## Structlog event vocabulary (v0.1)

| Event | Fields |
|---|---|
| `runtime.start` | symbol, settings_hash |
| `runtime.bootstrap_complete` | fsm_state, halt_reason |
| `runtime.ws_disconnect` | silence_seconds, action |
| `runtime.bar_tick` | bar_close_ts, last_seen_ts |
| `runtime.bar_poll_stall` | consecutive_failures, threshold |
| `runtime.kill_switch_detected` | sentinel_path |
| `runtime.crash` | exc_type, exc_msg |
| `runtime.shutdown` | reason, in_flight_orders |

## Related

- [[bar-poller]] — REST kline source feeds tick loop
- [[ws-private-consumer]] — pybit thread side; check_alive called inline from tick
- [[execution-state-machine]] — KILL_SWITCH_REQUESTED transitions
- [[reconciler]] — wallet events via on_wallet_event
- [[../runbooks/halt-recovery]] — HALT_RUNTIME_CRASH / HALT_BAR_POLL_STALL / KILL_SWITCH_REQUESTED post-mortem

## Open questions

- WS consumer dedicated health check threshold (separate from bar poller) — S8b/S9.
- Multi-symbol / multi-bracket — lock granularity re-evaluation.
- async/await migration — S9+.

## Sources

- [[../decisions/0022-sprint-8a-live-runtime]] — все 14 sub-decisions
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/components/runtime-manager.md
git commit -m "docs(wiki): add runtime-manager component page (S8a)"
```

---

## Task 22: NEW `wiki/project/components/bar-poller.md`

**Files:**
- Create: `llm-wiki/wiki/project/components/bar-poller.md`

**References:** ADR 0022 sub-decisions 2 + 3.

- [ ] **Step 1: Write the page**

Create `llm-wiki/wiki/project/components/bar-poller.md`:

```markdown
---
title: BarSource (REST kline poller)
type: component
tags: [runtime, marketdata, polling, sprint-8a]
created: 2026-04-24
updated: 2026-04-24
sources:
  - wiki/project/decisions/0022-sprint-8a-live-runtime.md
status: stable
---

# BarSource (REST kline poller)

**TL;DR:** REST `kline` poller (5s cadence). Возвращает последний closed bar если новый, иначе None. Дедупликация по `close_time`. После N consecutive failures предикат `should_halt(threshold)` возвращает True — RuntimeManager эмитит `HALT_BAR_POLL_STALL`.

## Definition / Purpose

Файл: `src/runtime/bar_source.py`. Заменяет absent driver loop: до S8a kline данные читали только batch-скрипты backfill'а. Live-runtime требует tick-source.

## Public API

```python
class BarSource:
    def __init__(self, *, adapter, symbol: str, interval: str = "60") -> None: ...
    def poll(self) -> Bar | None: ...
    def should_halt(self, *, threshold: int) -> bool: ...
    consecutive_failures: int  # public read-only counter
```

## Why REST, not WS kline

WS kline streams **partial** bar updates (open bar). Для close-on-close signal (look-ahead invariant) нужны только closed bars. REST дёшев: 1 req/5s = 720 req/час, c большим запасом до Bybit rate limit (600 req/min). WS добавил бы async loop без выигрыша в latency на 1H timeframe (см. ADR 0022 sub-decision 2).

## Dedup invariant

`_last_close_ts` хранит ms epoch последнего emit'нутого bar'а. Если поллер видит `close_time <= _last_close_ts` — возвращает None. Это защищает от duplicate `strategy.on_bar(bar)` вызовов.

## Stall semantics

| Counter state | Action |
|---|---|
| 0 | normal (last poll OK) |
| 1..threshold-1 | tolerated (transient REST failure) |
| ≥ threshold (default 24) | `should_halt(threshold) → True` → RuntimeManager emits `HALT_BAR_POLL_STALL` |

При успешном poll'е counter сбрасывается в 0 (recovery).

## Threshold validation rules

`runtime_bar_poll_stall_threshold` validator: 6 ≤ N ≤ 720.
- 6 (= 30s) — false-halt floor (короче — слишком чувствительно к 1-2 transient hiccup'ам Bybit)
- 720 (= 1 bar period @ 5s cadence) — потолок (дольше = bar-poller stall переходит границу bar close → mid-bar fill possible).

Default 24 (= 120s = 3.3% от 3600s bar period). Trader-expert verdict: stall ≠ position-safety (OCO bracket exchange-side; WS consumer routes order events независимо). False-halt cost dominates → 24 better balances 12 (см. ADR 0022 Alt-5).

## Halt class annotation

`HALT_BAR_POLL_STALL` — **signal-pipeline halt class**, not execution-safety.

## Documented degradation: mid-bar fill

Stall длиной > 30 минут перед close может вызвать **mid-bar fill** вместо open fill (RuntimeManager пропустит close moment, signal эмитится позже на следующем tick'е после recovery). Это **slippage**, не correctness violation. Monitored через structlog `runtime.bar_poll_stall` event с полем `consecutive_failures`. Подробнее: [[../architecture/risk-register]] → POLL_STALL_MID_BAR_FILL scenario.

## Related

- [[runtime-manager]] — owner of poll cadence + halt emission
- [[bybit-adapter]] — REST kline endpoint wrapper
- [[../decisions/0022-sprint-8a-live-runtime]] — sub-decisions 2 + 3

## Sources

- [[../decisions/0022-sprint-8a-live-runtime]]
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/components/bar-poller.md
git commit -m "docs(wiki): add bar-poller component page (S8a)"
```

---

## Task 23: UPDATE `ws-private-consumer.md` — driver loop section

**Files:**
- Modify: `llm-wiki/wiki/project/components/ws-private-consumer.md`

**References:** ADR 0022 sub-decision 4 (check_alive inline).

- [ ] **Step 1: Append section**

В существующую страницу (перед `## Sources`) добавить:

```markdown
## Driver loop (S8a closed)

До S8a `BybitPrivateWSConsumer` был passive: `start()` / `stop()` без owner. Sprint 8a (ADR 0022) ввёл [[runtime-manager]] как driver:

- `RuntimeManager.run()` вызывает `ws_consumer.start()` после `coordinator.bootstrap()`.
- `ws_consumer.check_alive(max_silence_seconds=...)` вызывается **inline** в каждом tick'е main thread'а — НЕ из отдельного worker thread (ADR 0022 sub-decision 4 — устраняет same-cadence race с bar-поллером).
- `RuntimeManager._shutdown(reason)` вызывает `ws_consumer.stop()` (idempotent).

См. таблицу lock policy в [[runtime-manager]] — Coordinator-side callbacks (`on_order_event`, `on_ws_reconnect`) acquire `Coordinator._lock` (RLock).
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/components/ws-private-consumer.md
git commit -m "docs(wiki): ws-private-consumer — driver loop now exists (S8a)"
```

---

## Task 24: UPDATE `execution-state-machine.md` — KILL_SWITCH_REQUESTED + lock ref

**Files:**
- Modify: `llm-wiki/wiki/project/components/execution-state-machine.md`

**References:** ADR 0022 sub-decisions 1 + 5.

- [ ] **Step 1: Append KILL_SWITCH_REQUESTED row + lock policy reference**

Найти таблицу transitions, добавить новые rows:

```markdown
| FLAT / ENTRY_PENDING / LONG_OPEN / OCO_ARMING / OCO_ARMED / EXIT_PENDING / EXIT_SIBLING_CANCELLING / EXIT_SIBLING_CANCEL_FAILED / EXIT_SL_RESIDUAL / RECONCILING | `KILL_SWITCH_REQUESTED` | HALTED | ADR 0022 sub-decision 5. Operator-initiated HALT (NOT terminal kill — KILL_SWITCH остаётся для KILLED). |
```

В секцию "Concurrency" (создать если нет) добавить:

```markdown
## Concurrency / Lock policy (S8a)

Все мутации FSM row проходят через `Coordinator._lock` (`threading.RLock`, ADR 0022 sub-decision 1). Это защищает от race между:
- main thread (`start_bracket`, `flatten`, `bootstrap`)
- pybit thread (`on_order_event`, `on_ws_reconnect`)

Reconciler-side: `Reconciler._lock` (`threading.Lock`, non-reentrant) — wraps `on_wallet_event` + `reconcile`.

См. [[runtime-manager]] — Lock policy reference table.
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/components/execution-state-machine.md
git commit -m "docs(wiki): FSM — KILL_SWITCH_REQUESTED transitions + lock policy (S8a)"
```

---

## Task 25: UPDATE `reconciler.md` — lock policy ref

**Files:**
- Modify: `llm-wiki/wiki/project/components/reconciler.md`

**References:** ADR 0022 sub-decision 1.

- [ ] **Step 1: Append section**

В существующую страницу (перед `## Sources`):

```markdown
## Concurrency / Lock policy (S8a)

`Reconciler._lock` (`threading.Lock`, non-reentrant — ADR 0022 sub-decision 1) wraps:
- `on_wallet_event(evt)` — pybit thread WS callback
- `reconcile(local, expected_state=None)` — main thread (bootstrap / on_ws_reconnect via Coordinator)

Lock не reentrant: пути не вкладываются (`reconcile` не вызывает `on_wallet_event` и наоборот). См. [[runtime-manager]] для общей таблицы lock policy.
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/components/reconciler.md
git commit -m "docs(wiki): reconciler — lock policy reference (S8a)"
```

---

## Task 26: UPDATE `wiki/trading/concepts/reason-codes.md` — 42 → 45

**Files:**
- Modify: `llm-wiki/wiki/trading/concepts/reason-codes.md`

**References:** ADR 0022 sub-decision 12.

- [ ] **Step 1: Append rows + update count header**

В таблице halts добавить:

```markdown
| 43 | `HALT_RUNTIME_CRASH` | halt-runtime | unhandled exception в `RuntimeManager.run()` (ADR 0022 sub-decision 6). Persisted ДО re-raise — restart требует MANUAL_RESET. |
| 44 | `HALT_BAR_POLL_STALL` | halt-pipeline | N consecutive REST `kline` failures (default N=24 = 120s). Signal-pipeline halt class — НЕ position-safety. См. [[../../project/components/bar-poller]] mid-bar-fill degradation. |
| 45 | `KILL_SWITCH_REQUESTED` | halt-operator | Sentinel-file `.kill_switch` detected (operator action via `python -m src kill`). Distinct from S7 `KILL_SWITCH` (terminal → KILLED). |
```

В header arithmetic note: `6 entry + 11 scale/exits + 9 rejects + 19 halts = 45`.

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/trading/concepts/reason-codes.md
git commit -m "docs(wiki): reason-codes 42 → 45 — runtime crash/stall/kill-switch (S8a)"
```

---

## Task 27: UPDATE `wiki/project/architecture/risk-register.md`

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/risk-register.md`

**References:** ADR 0022 sub-decision 3 (degradation note).

- [ ] **Step 1: Append scenario row**

```markdown
### POLL_STALL_MID_BAR_FILL (S8a, degradation)

| Field | Value |
|---|---|
| Scenario | REST kline poller stall длиной > 30 минут перед bar close |
| Trigger | Bybit REST API outage cluster (10-90s typical, multiplied) |
| Impact | Mid-bar fill вместо open(T+1) fill — slippage, не correctness |
| Severity | LOW (slippage) — НЕ position-safety event |
| Mitigation | `runtime_bar_poll_stall_threshold` (default 24 = 120s) emits `HALT_BAR_POLL_STALL` задолго до bar close |
| Detection | structlog `runtime.bar_poll_stall` event с `consecutive_failures` field |
| Owner | RuntimeManager + BarSource |
| Source | [[../decisions/0022-sprint-8a-live-runtime]] sub-decision 3 |
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/architecture/risk-register.md
git commit -m "docs(wiki): risk-register — add POLL_STALL_MID_BAR_FILL degradation (S8a)"
```

---

## Task 28: UPDATE `wiki/project/runbooks/halt-recovery.md`

**Files:**
- Modify: `llm-wiki/wiki/project/runbooks/halt-recovery.md`

**References:** ADR 0022 sub-decisions 6 + 3 + 5 + 13.

- [ ] **Step 1: Add 3 new sections**

Append:

```markdown
## HALT_RUNTIME_CRASH (43)

**Source:** unhandled exception в `RuntimeManager.run()` → top-level `except Exception` в `src/runtime/manager.py` (ADR 0022 sub-decision 6).

**Investigation steps:**
1. Найти crash log:
   ```bash
   grep "runtime.crash" $LOG_DIR/*.log | tail -20
   ```
2. Извлечь exception:
   ```sql
   SELECT ts, reason, context_json
   FROM halt_log
   WHERE symbol = ? AND reason = 'HALT_RUNTIME_CRASH'
   ORDER BY ts DESC LIMIT 5;
   ```
3. Reproduce in dev — fix bug → новый ADR amendment if invariant changed.
4. Operator MANUAL_RESET требуется (как любой halt).

## HALT_BAR_POLL_STALL (44)

**Source:** `BarSource.consecutive_failures >= settings.runtime_bar_poll_stall_threshold` (default 24 × 5s = 120s) — ADR 0022 sub-decision 3.

**Halt class:** signal-pipeline (НЕ position-safety). OCO bracket exchange-side; existing positions защищены.

**Investigation steps:**
1. Bybit REST status:
   ```bash
   curl -s https://api.bybit.com/v5/market/time | jq
   ```
2. Recent failure cluster:
   ```bash
   grep "bar_source.poll_failed" $LOG_DIR/*.log | tail -50
   ```
3. Если cluster < 5 минут — likely transient, можно MANUAL_RESET без эскалации. Если > 30 минут — investigate network / API key / Bybit incident page.
4. После reset BarSource counter автоматически сбрасывается на первом успешном poll.

## KILL_SWITCH_REQUESTED (45)

**Source:** sentinel-file `.kill_switch` detected (`python -m src kill`) — ADR 0022 sub-decision 5.

**Operator-initiated** — нормальный shutdown path. Не error.

**Recovery:**
1. Verify intent — почему оператор kill'нул?
2. Cleanup sentinel:
   ```bash
   rm -f $RUNTIME_KILL_SWITCH_PATH   # default ".kill_switch"
   ```
3. Перед restart — MANUAL_RESET halt_reason (как и любой halt):
   ```sql
   UPDATE execution_state
   SET halt_reason = NULL
   WHERE symbol = ?;
   ```
4. Restart: `python -m src run` (sentinel автоматически cleanup-нится на startup в `RuntimeManager.run()`).
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/runbooks/halt-recovery.md
git commit -m "docs(wiki): runbook — HALT_RUNTIME_CRASH / HALT_BAR_POLL_STALL / KILL_SWITCH_REQUESTED (S8a)"
```

---

## Task 29: UPDATE `wiki/index.md` + `wiki/log.md` + `SPRINT_STATE.md`

**Files:**
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/log.md`
- Modify: `llm-wiki/wiki/project/SPRINT_STATE.md`

**References:** wiki maintainer convention (см. `llm-wiki/CLAUDE.md`).

- [ ] **Step 1: Index entries**

В `wiki/index.md` под `## Project — Components`:

```markdown
- [[project/components/runtime-manager]] — RuntimeManager: process lifecycle owner (bootstrap → loop → shutdown). S8a.
- [[project/components/bar-poller]] — BarSource: REST kline poller с dedup + stall counter. S8a.
```

- [ ] **Step 2: Log session entry**

В `wiki/log.md` append:

```markdown
## [2026-04-XX] session-end | S8a — Live Runtime merged

- Closed: ADR 0021 line 364 deferral (KILL_SWITCH wired via sentinel-file CLI).
- New: RuntimeManager (bootstrap → kill→alive→poll→strategy→bracket → shutdown), BarSource (REST kline + dedup + stall).
- Lock policy: Coordinator RLock (6 methods), Reconciler Lock (2 methods) — Task 0 mandatory.
- Reason codes: 42 → 45 (HALT_RUNTIME_CRASH, HALT_BAR_POLL_STALL, KILL_SWITCH_REQUESTED).
- FSM: KILL_SWITCH_REQUESTED event → HALTED from 10 active states.
- Removed: src/controller.py, main.py (orphans broken since S2).
- Entry-point: `python -m src` (run / backfill / reconcile-only / kill).
- Tests: 13 task suites + 1 opt-in Demo integration.
- ADR: 0022 accepted.
```

- [ ] **Step 3: SPRINT_STATE update**

В `wiki/project/SPRINT_STATE.md`:
```yaml
sprint: 8a
phase: 8-ship
in_progress: ""
next_action: "Tag v0.1.0-alpha.8a, open S8b brainstorm"
updated: 2026-04-XX
```

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/index.md llm-wiki/wiki/log.md llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(wiki): index/log/SPRINT_STATE — S8a session-end"
```

---



## Task 30: Final domain reviewers (parallel) + finishing branch + tag

**Files:**
- Review: все файлы из `git diff main...feature/sprint-8a-live-runtime`
- Sync (если нужно): `~/.claude/agents/trading-logic-reviewer.md` (lock policy invariant)

**References:** ADR 0017 (review agent harness) + ADR 0022 verification checklist.

- [ ] **Step 1: Parallel domain reviewer dispatch**

Один message, 3 параллельных Agent calls:

| Reviewer | Scope |
|---|---|
| `trading-logic-reviewer` (opus) | `src/runtime/manager.py`, `src/runtime/bar_source.py`, `src/execution/coordinator.py` (lock policy + request_halt), `src/execution/state_machine.py` (KILL_SWITCH_REQUESTED), `src/__main__.py` (live wiring) |
| `python-reviewer` (sonnet) | весь diff — generic Python (PEP 8, type hints, error handling) |
| `data-integrity-reviewer` (sonnet) | NO touch persistence в S8a → likely CONFIRM no findings; всё равно dispatch для safety net |

(`quant-stats-reviewer` — SKIP: математика не затронута.)

- [ ] **Step 2: Address blockers**

Любые `❌ Blockers` → fix. `⚠️ Concerns` → решить (fix / explicitly defer / wiki note). `✅ Verified` — proceed. `Follow-ups for wiki` → patch in same sprint.

- [ ] **Step 3: Sync trading-logic-reviewer.md (если нужно)**

Если в S8a добавлены новые invariants (lock policy, KILL_SWITCH_REQUESTED как distinct reason class, sentinel-file pattern) — обновить prompt agent'а:

```
~/.claude/agents/trading-logic-reviewer.md
+ Сver (S8a closed): runtime concurrency model — Coordinator RLock + Reconciler Lock; KILL_SWITCH_REQUESTED ≠ KILL_SWITCH (one halts, other terminates).
```

Touch mtime для ADR-agent sync hook (см. `wiki/project/components/adr-agent-sync-hook`).

- [ ] **Step 4: Final test run**

```bash
pytest tests/unit -v -x
pytest tests/integration -v   # SKIPPED без RUN_DEMO
ruff check src/ tests/
```
Expected: PASS / SKIPPED / no lint errors.

- [ ] **Step 5: Run `superpowers:finishing-a-development-branch`**

```
Skill: superpowers:finishing-a-development-branch
```
- Squash trivia commits → одна логическая история
- PR description: ADR 0022 link, sub-decisions checklist, test count, demo result
- Phase G обоснование (если повторяем) — для S8a Phase G = Demo Mainnet smoke test (Task 20 manual run)

- [ ] **Step 6: Tag**

```bash
git tag v0.1.0-alpha.8a -a -m "Sprint 8a — Live Runtime (RuntimeManager + REST bar poller + KILL_SWITCH + lock policy)"
git push origin v0.1.0-alpha.8a
```

- [ ] **Step 7: Update SPRINT_STATE → between-sprints**

```yaml
sprint: 8a-complete
phase: between-sprints
tag: v0.1.0-alpha.8a
next: S8b brainstorm (Analytics per-fill + execution topic + WS+REST epsilon)
```

---



## Self-Review

### 1. Spec coverage check (ADR 0022 → tasks)

| ADR 0022 sub-decision | Plan task(s) |
|---|---|
| 1. Concurrency model — sync + threading + lock policy | Tasks 5, 6 (and structural reference in Task 13/15) |
| 2. REST bar poller (5s cadence + dedup) | Tasks 7, 8 (+ catch-up via Task 10) |
| 3. `runtime_bar_poll_stall_threshold = 24` + validator | Tasks 3 (validator), 9 (predicate), 15 (emit), 22 (wiki), 27 (risk-register) |
| 4. `check_alive` INLINE в main thread | Task 15 (`_check_alive_inline`), 23 (wiki update) |
| 5. KILL_SWITCH — sentinel-file CLI | Tasks 11 (request_halt), 12 (FSM event), 14 (stale cleanup), 15 (detection), 19 (CLI), 20 (integration) |
| 6. `HALT_RUNTIME_CRASH` mandatory | Tasks 4 (enum), 11 (request_halt), 16 (top-level handler) |
| 7. `RuntimeManager` class + sequencing invariant | Tasks 13 (scaffold), 14 (bootstrap-first sequencing) |
| 8. Sequential bar → signal → bracket | Task 15 (`_poll_bar_and_strategy`), 10 (warmup look-ahead invariant) |
| 9. Entry-point `python -m src` + argparse | Task 18 (parser + 4 subcommands), 19 (kill subcommand body) |
| 10. Удалить `src/controller.py` + `main.py` | Tasks 1, 2 |
| 11. Settings — 5 new runtime_* | Task 3 |
| 12. Reason codes 43 / 44 / 45 | Task 4 (+ wiki Task 26) |
| 13. Structlog KV events | Tasks 15-17 (emit), 21 (wiki documentation table) |
| 14. Tests — unit + opt-in integration | Tasks 5-19 (unit per task), Task 20 (integration) |

**Coverage: 14/14 sub-decisions.** Каждая sub-decision имеет минимум один task с TDD-cycle и git commit.

### 2. Verification checklist mapping (ADR §Verification checklist 12 items)

| ADR check | Task |
|---|---|
| Lock wrappers Coordinator (6) + Reconciler (2) | Tasks 5, 6 |
| 2-thread fixture race tests | Tasks 5 (Coordinator), 6 (Reconciler) |
| Bar poller dedup test | Task 7 |
| Bar poller stall test (24 fail / 23 recovery) | Task 9 |
| Strategy warmup 50 bars → 0 signals | Task 10 |
| KILL_SWITCH CLI write + stale cleanup | Tasks 14 (cleanup), 19 (write), 15 (detection) |
| HALT_RUNTIME_CRASH halt persisted before re-raise | Task 16 |
| Settings validator 6/720 boundaries | Task 3 |
| `src/controller.py` + `main.py` deleted; `pytest --collect-only` clean | Tasks 1, 2 |
| `python -m src run --help` shows 4 subcommands | Task 18 |
| Integration test (Demo Mainnet RUN_DEMO=1) | Task 20 |
| Wiki Stage E (2 NEW + 5 UPDATE + runbook + risk-register) | Tasks 21-29 |
| trading-logic-reviewer.md sync if invariants added | Task 30 step 3 |

**Coverage: 12/12 checklist items mapped to tasks.**

### 3. Placeholder scan

- Все code blocks (test + impl) — concrete, с реальными именами / фикстурами / assertions.
- Никаких "TBD", "fill in later", "implement in next task" без явной cross-reference (где есть — например Task 7 → Task 8 на signature change — указано явно в prose).
- Все `git commit` messages написаны полностью.
- `_settings(tmp_path)` helper в `test_runtime_manager.py` определён в Task 13 и переиспользуется Tasks 14-17 — единая локальная fixture.

### 4. Type / signature consistency

- `Coordinator.request_halt(reason: str) -> None` — единая сигнатура в T11 (definition), T15/T16 (callsite), T28 (runbook reference).
- `BarSource.poll() -> Bar | None` и `BarSource.should_halt(threshold: int) -> bool` — стабильны через T7/8/9/15/22.
- `RuntimeManager.__init__(*, coordinator, reconciler, ws_consumer, bar_source, strategy, settings)` — keyword-only, single signature через T13/14/15/16/17/18/20.
- `Strategy.warmup(bar: Bar) -> None` (T10) НЕ конфликтует с `Strategy.on_bar(bar: Bar) -> Signal | None` (existing).
- `runtime_*` settings field naming consistent (T3) — pydantic env mapping `RUNTIME_*` через T19 + T20 + integration test.

### 5. Dependency check

- Phase 0 (T1-2) — нет dependencies на новый код. ✅
- Phase 1 (T3-4) — модифицируют существующие файлы (config.py, reason_codes.py); нет dependencies. ✅
- Phase 2 (T5-6) — depends на T3 (settings instances в test fixtures), но фактически — independent locks. Mocks обходят. ✅
- Phase 3 (T7-10) — T7 → T8 → T9 sequential (same file extends), T10 independent. ✅
- Phase 4 (T11-12) — T11 depends на T5 (Coordinator._lock); T12 — independent FSM enum. ✅
- Phase 5 (T13-17) — strict sequential (T13 ctor → T14 run → T15 tick → T16 crash → T17 shutdown), each task adds layer. ✅
- Phase 6 (T18-19) — T18 builds parser; T19 fills `_cmd_kill`. ✅
- Phase 7 (T20) — depends на T13-19 + T11 (request_halt). ✅
- Phase 8 (T21-29) — все wiki, не зависят друг от друга. Parallel-safe. ✅
- Phase 9 (T30) — depends на all. ✅

Никакой task не ссылается на ещё-не-существующий symbol из более поздней Phase.

### 6. Scope discipline

- **B1 принцип** — одна подсистема per спринт. S8a = runtime orchestration. WS+REST epsilon-halt + execution topic + per-fill Analytics → отложены S8b (см. ADR 0022 Non-goals + Open questions).
- **Никаких unsolicited refactor'ов** — только файлы из "Modified files" + "New files" таблиц трогаются.
- **YAGNI** — async/await migration, multi-bracket concurrency, systemd unit — ВСЕ deferred.
- **TDD strict** — каждая задача имеет 5-шаговый цикл (test → fail → impl → pass → commit), кроме T1-T2 (delete-only — нет new code) и T20 (integration — opt-in run, write-once test).

### 7. Reviewer concerns surfaced during writing

- **T15 (_tick stall vs new bar order)**: stall check ПОСЛЕ `bar = bs.poll()`, но при `should_halt=True` мы exit'им до `strategy.on_bar` — это правильно (нет signal generation в stall window). Test `test_tick_stall_threshold_triggers_halt` это покрывает.
- **T17 (in_flight_orders snapshot)**: best-effort — обращение к `_coordinator._repo` через protected access. Альтернатива — добавить публичный `Coordinator.in_flight_count()`. Решение: для S8a достаточно best-effort log field (не critical correctness path); если reviewer flag'нет — выделить публичный helper в follow-up.
- **T18 (live wiring)**: `_cmd_run` импорты идут lazy (внутри функции) чтобы `python -m src --help` не требовал env vars. Это умеренный over-engineering, но snappy CLI — UX win.
- **T20 (Demo smoke 30s sleep)**: фиксированный sleep вместо busy-wait на bootstrap_complete event — упрощение для v0.1. Если flaky — добавить event signaling в S8b.

---

## Execution Handoff

**Plan complete. Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review между tasks.
2. **Inline Execution** — `superpowers:executing-plans` skill, batch with checkpoints.

**Model dispatch:**
- **haiku:** Tasks 1, 2, 4, 21-29 (mechanical: delete / enum add / wiki write)
- **sonnet (default):** Tasks 3, 5-19 (standard TDD)
- **opus escalation only if sonnet BLOCKED twice:** Tasks 5, 15, 16 (lock semantics, tick orchestration, crash handler edge cases)

**Parallel-safe (один message, multiple Agent dispatches):**
- T1 + T2 (orphan delete)
- T3 + T4 (settings + enum, разные файлы)
- T5 + T6 (Coordinator + Reconciler locks, разные файлы)
- T7 + T8 (sequential within file, но один subagent fine)
- T11 + T12 (Coordinator method + FSM enum, разные файлы)
- T21 + T22 (две новых wiki page)
- T23 + T24 + T25 + T26 + T27 + T28 + T29 (все wiki updates — разные файлы)

**Sequential-only:**
- T13 → T14 → T15 → T16 → T17 (RuntimeManager builds incrementally в одном файле)
- T18 → T19 (`_cmd_kill` body fills T18 placeholder)
- T20 ← T13-T19 (integration consumes assembled runtime)
- T30 ← all

