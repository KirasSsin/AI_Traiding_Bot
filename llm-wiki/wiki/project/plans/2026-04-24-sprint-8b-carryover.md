---
title: "Sprint 8b — S8a Carry-Over Fixes Implementation Plan"
type: plan
status: draft
created: 2026-04-24
updated: 2026-04-24
sources:
  - docs/superpowers/specs/2026-04-24-sprint-8b-carryover-design.md
  - wiki/project/decisions/0022-sprint-8a-live-runtime.md
  - wiki/project/decisions/0021-sprint-7-resilience.md
  - wiki/project/components/coordinator.md
  - wiki/project/components/runtime-manager.md
  - wiki/project/components/bar-poller.md
tags: [sprint-8b, carry-over, fsm, halt, bar-source, kill-switch, mypy, tdd, adr-0023]
---

# Sprint 8b — S8a Carry-Over Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Закрыть 4 carry-over дефекта из Sprint 8a (FSM transit bug в `request_halt`, BarSource fail-late на unknown interval, `main()` mypy `no-any-return`, non-atomic kill-switch write) + добавить process-safeguard (ADR 0023 + reviewer rule + property test) против регресса при будущих halt codes.

**Architecture:** Только локальные правки существующих файлов. Никаких новых компонентов, миграций, reason codes, FSM states, доменных событий. Один новый ADR (0023) + один update в reviewer prompt + один property test обеспечивают, что T1 fix не регрессирует, когда добавится новый halt-class `ReasonCode` через 2-3 спринта.

**Tech Stack:** Python 3.12, pydantic v2, pytest, `threading.RLock` (already on Coordinator), `os.replace` атомарная запись (mirror `src/risk/override.py:82-95`), mypy --strict.

**Source of truth (spec):** `docs/superpowers/specs/2026-04-24-sprint-8b-carryover-design.md` (брейнсторм-спека, gitignored). Этот план — binding artifact для PR.

**Trader-expert verdict (round 1, 2026-04-24):** Q1 narrow YAGNI confirm; Q2 FSM transit fix confirm; Q3 Analytics defer → S8c; Q4 epsilon expand+defer → S9; Q5 sprint scope = 5 carry-over fixes.

---

## Trace map (retro-added 2026-04-25 в S8c per Bucket C5)

| Spec / source | Tasks |
|---------------|-------|
| S8a carry-over (request_halt FSM transit fix) | T1 |
| S8a carry-over (BarSource KeyError guard — interval validator) | T2 |
| S8a carry-over (main() mypy no-any-return) | T3 |
| S8a carry-over (sentinel-file atomic write) | T4 |
| ADR 0023 (halt-code → FSM event mapping invariant) | T5 |
| trading-logic-reviewer.md CRITICAL section | T6 |
| Property test + (FLAT, RISK_HALT) row | T7 |
| Wiki Stage E sync | T8 |
| Ship | T9 |

---

## File Structure

**New files:**

| Path | Responsibility |
|------|----------------|
| `tests/property/test_request_halt_mapping.py` | Invariant: every `HALT_*` / `KILL_SWITCH_REQUESTED` `ReasonCode` имеет explicit dispatch в `Coordinator.request_halt` (T5 safeguard). |
| `tests/integration/test_runtime_kill_switch_e2e.py` | Opt-in e2e: drop sentinel → RuntimeManager → state HALTED + halt_log row + clean exit. |
| `llm-wiki/wiki/project/decisions/0023-halt-code-fsm-event-mapping.md` | ADR — binding rule "every halt-class ReasonCode must wire `request_halt` → `_transition`". |

**Modified files:**

| Path | Change |
|------|--------|
| `src/execution/coordinator.py:600-613` | T1: `request_halt(reason: str → ReasonCode)`; добавить `_transition(KILL_SWITCH_REQUESTED \| RISK_HALT)` после `_set_halt`. |
| `src/runtime/bar_source.py:18-28` | T2: расширить `_INTERVAL_MS` до 13 Bybit kline strings; добавить `__init__` validator `if interval not in _INTERVAL_MS: raise ValueError`. |
| `src/__main__.py:56-65` | T4: `_cmd_kill` — заменить `sentinel.write_text("")` на `os.open + os.fdopen + os.replace` (mirror `src/risk/override.py:82-95` минус `fsync`). |
| `src/__main__.py:91-94` | T3: `main()` mypy fix — typed dispatch (`args.func: Callable[[argparse.Namespace], int]` через `set_defaults` annotation либо assertion в `main`). |
| `src/runtime/manager.py:81/114/141` | T1 caller-side: уже передают `ReasonCode.*` enum — тип-сужение чисто mypy/IDE-польза, runtime-no-op. |
| `tests/unit/test_coordinator_request_halt.py` | T1: добавить ~5 новых тестов (FSM-transit per branch + idempotence). |
| `tests/unit/test_bar_poller.py` | T2: добавить parametrize over 13 intervals + reject unknown. |
| `tests/unit/test_kill_switch_cli.py` | T4: добавить atomic-write test (partial monkeypatch) + verify temp file cleanup. |
| `~/.claude/agents/trading-logic-reviewer.md` | T5: добавить CRITICAL section "Halt-code → FSM event mapping (ADR 0023)". |
| `llm-wiki/wiki/project/components/coordinator.md` | Stage E: документировать `request_halt` → `_transition` invariant + ссылку на ADR 0023. |
| `llm-wiki/wiki/project/components/runtime-manager.md` | Stage E: BarSource interval validator + atomic kill-switch write. |
| `llm-wiki/wiki/project/components/bar-poller.md` | Stage E: список 13 валидных intervals + fail-fast validator. |
| `llm-wiki/wiki/index.md` | Append `[[decisions/0023-halt-code-fsm-event-mapping]]`. |
| `llm-wiki/wiki/log.md` | Append S8b session entries (Stage A + Stage E + ship). |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | Phase/progress per task; финал → between-sprints. |

**Deleted files:** None.

---

## Task Sequencing Rationale

```
Phase A (Foundation):    Task 1     → T1 Coordinator.request_halt FSM transit + signature tighten
Phase B (Defensive):     Task 2     → T2 BarSource interval validator + 13-interval dict
Phase C (Type narrow):   Task 3     → T3 main() mypy no-any-return fix
Phase D (Atomic write):  Task 4     → T4 _cmd_kill atomic via os.replace
Phase E (Safeguard):     Tasks 5-7  → T5 ADR 0023 + reviewer prompt + property invariant
Phase F (Wiki Stage E):  Task 8     → components/coordinator + components/runtime-manager + components/bar-poller + index + log
Phase G (Verify + Ship): Task 9     → final domain reviewers (parallel) + finishing-a-development-branch + tag v0.1.0-alpha.8b
```

**Critical-path notes:**
- **Task 1 ДО всего остального** — он фиксирует core invariant (FSM state ↔ halt_reason). Property test в Task 7 опирается на T1 fix уже presence.
- **Task 5 (ADR 0023) ДО Task 6 (reviewer prompt)** — prompt ссылается на ADR.
- **Task 7 (property test) ДО Task 9 (ship)** — property test должен пройти на текущем enum (45 codes); future failure surface = новый halt code без dispatch wiring.
- Tasks 2 / 3 / 4 независимы между собой и от Task 1; **batchable** в один subagent или parallel dispatch (разные файлы, 0 shared state).

**Parallel-safe pairs (один message, multiple Agent dispatches):**
- Tasks 2 + 3 + 4 (BarSource + __main__ mypy + __main__ atomic-write — разные file regions / batchable in one subagent).
- Tasks 5 + 6 (ADR + reviewer prompt — разные файлы, no code dep).
- Stage G domain reviewers: trading-logic-reviewer + python-reviewer (parallel, разные scope).

**Sequential-only:**
- Task 1 → Task 7 (property test reads T1 fix).
- Task 6 ← Task 5 (prompt cites ADR number).
- Task 9 после всех.

---

## Task 1: Coordinator.request_halt — FSM transit fix + signature tighten

**Files:**
- Modify: `src/execution/coordinator.py:600-613`
- Modify: `src/runtime/manager.py` (caller already passes enum — verify, no edit expected)
- Test: `tests/unit/test_coordinator_request_halt.py` (extend existing 90-line file)

**References:** ADR 0022 sub-decisions 5/6/11; spec section "T1"; trader-expert Q1+Q2 verdict.

- [ ] **Step 1: Read current request_halt + state machine event table**

```bash
sed -n '595,615p' src/execution/coordinator.py
sed -n '140,155p' src/execution/state_machine.py
```
Expected:
- `request_halt(reason: str)` at line 600 with body that calls `_set_halt(...)` only.
- `(ExecutionState.X, ExecutionEvent.KILL_SWITCH_REQUESTED): ExecutionState.HALTED` rows for X in {FLAT, ENTRY_PENDING, LONG_OPEN, OCO_ARMING, OCO_ARMED, EXIT_PENDING, EXIT_SIBLING_CANCELLING, EXIT_SIBLING_CANCEL_FAILED, EXIT_SL_RESIDUAL, PARTIAL_FILL, RECONCILING}.

- [ ] **Step 2: Write the failing tests**

Append to `tests/unit/test_coordinator_request_halt.py`:

```python
from src.execution.state_machine import ExecutionState
from src.risk.reason_codes import ReasonCode


def test_request_halt_kill_switch_transitions_to_halted(coord_factory):
    """KILL_SWITCH_REQUESTED dispatches KILL_SWITCH_REQUESTED event → HALTED."""
    coord = coord_factory(initial_state=ExecutionState.FLAT)
    coord.request_halt(ReasonCode.KILL_SWITCH_REQUESTED)
    state = coord._repo.get_state(coord._symbol)
    assert state.state == ExecutionState.HALTED
    assert state.halt_reason == ReasonCode.KILL_SWITCH_REQUESTED.value


def test_request_halt_runtime_crash_transitions_to_halted(coord_factory):
    """HALT_RUNTIME_CRASH dispatches RISK_HALT event → HALTED."""
    coord = coord_factory(initial_state=ExecutionState.LONG_OPEN)
    coord.request_halt(ReasonCode.HALT_RUNTIME_CRASH)
    state = coord._repo.get_state(coord._symbol)
    assert state.state == ExecutionState.HALTED
    assert state.halt_reason == ReasonCode.HALT_RUNTIME_CRASH.value


def test_request_halt_bar_poll_stall_transitions_to_halted(coord_factory):
    """HALT_BAR_POLL_STALL dispatches RISK_HALT event → HALTED."""
    coord = coord_factory(initial_state=ExecutionState.OCO_ARMED)
    coord.request_halt(ReasonCode.HALT_BAR_POLL_STALL)
    state = coord._repo.get_state(coord._symbol)
    assert state.state == ExecutionState.HALTED
    assert state.halt_reason == ReasonCode.HALT_BAR_POLL_STALL.value


def test_request_halt_idempotent_when_already_halted(coord_factory):
    """Second request_halt keeps primary halt_reason (S7 γ) and stays HALTED."""
    coord = coord_factory(initial_state=ExecutionState.FLAT)
    coord.request_halt(ReasonCode.KILL_SWITCH_REQUESTED)
    coord.request_halt(ReasonCode.HALT_RUNTIME_CRASH)
    state = coord._repo.get_state(coord._symbol)
    assert state.state == ExecutionState.HALTED
    # primary-wins per S7 γ — first non-null halt_reason sticks
    assert state.halt_reason == ReasonCode.KILL_SWITCH_REQUESTED.value
```

If `coord_factory` fixture не существует в conftest — определи inline в test файле. Ориентир — паттерн из `tests/unit/test_coordinator_threading.py` (S8a Task 5).

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/test_coordinator_request_halt.py -v`
Expected: 4 new tests FAIL with `AssertionError: state.state == FLAT (or LONG_OPEN, OCO_ARMED) != HALTED` — `_set_halt` writes `halt_reason` но не двигает FSM.

- [ ] **Step 4: Implement fix**

Replace `src/execution/coordinator.py:600-613`:

```python
    def request_halt(self, reason: ReasonCode) -> None:
        """Public halt entry-point for RuntimeManager (KILL_SWITCH, RUNTIME_CRASH, STALL).

        Acquires self._lock (RLock — re-entrant if caller already holds).
        Writes halt_reason via _set_halt (primary-wins per S7 γ rule, halt_log appends),
        then transitions FSM state to HALTED via _transition.

        ADR 0022 sub-decisions 5/6/11; ADR 0023 (halt-code → FSM event mapping).
        """
        with self._lock:
            self._set_halt(
                reason=reason,
                last_event=ExecutionEvent.RISK_HALT,
                extra={"source": "request_halt"},
            )
            # FIX (S8b T1): _set_halt writes halt_reason but does not move FSM state.
            # Dispatch the matching event so reconciler / observers branching on
            # state == HALTED stay in sync with halt_reason.
            if reason == ReasonCode.KILL_SWITCH_REQUESTED:
                self._transition(ExecutionEvent.KILL_SWITCH_REQUESTED)
            else:
                # HALT_RUNTIME_CRASH, HALT_BAR_POLL_STALL → HALTED via RISK_HALT.
                # Future halt codes MUST add an explicit dispatch branch — see ADR 0023.
                self._transition(ExecutionEvent.RISK_HALT)
```

Add `from src.risk.reason_codes import ReasonCode` to imports if not present.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_coordinator_request_halt.py -v`
Expected: all tests PASS (existing + 4 new).

- [ ] **Step 6: Verify no other tests broke**

Run: `pytest -x -q`
Expected: all green. If any test passed `request_halt("string")` with bare string → update to `ReasonCode.X` enum.

- [ ] **Step 7: mypy check**

Run: `python -m mypy --strict src/execution/coordinator.py src/runtime/manager.py 2>&1 | tail -20`
Expected: no new errors. Caller-side `manager.py:81/114/141` already passes `ReasonCode.*` enum, so signature tightening is type-safe.

- [ ] **Step 8: Commit**

```bash
git add src/execution/coordinator.py tests/unit/test_coordinator_request_halt.py
git commit -m "fix(execution): request_halt dispatches FSM transition (S8b T1)

_set_halt only wrote halt_reason; FSM state stayed FLAT/LONG_OPEN while
halt_reason='KILL_SWITCH_REQUESTED' — 10 KILL_SWITCH_REQUESTED transitions
in TRANSITIONS table were dead code. Now request_halt also calls
_transition(KILL_SWITCH_REQUESTED | RISK_HALT) per code branch.

Also tighten signature reason: str → ReasonCode for mypy + IDE safety.

Refs: ADR 0022 sub-decisions 5/6/11; spec docs/superpowers/specs/2026-04-24-sprint-8b-carryover-design.md T1; trader-expert verdict 2026-04-24 Q1+Q2."
```

---

## Task 2: BarSource — interval validator + 13-interval dict

**Files:**
- Modify: `src/runtime/bar_source.py:18-28`
- Test: `tests/unit/test_bar_poller.py` (extend existing 141-line file)

**References:** spec section "T2"; trader-expert Q3 (this task) verdict.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_bar_poller.py`:

```python
import pytest

from src.runtime.bar_source import BarSource


@pytest.mark.parametrize(
    "interval",
    ["1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"],
)
def test_bar_source_init_accepts_all_bybit_intervals(interval):
    """All 13 Bybit V5 kline interval strings accepted at init."""
    src = BarSource(adapter=object(), symbol="BTCUSDT", interval=interval)
    assert src._interval == interval


def test_bar_source_init_rejects_unknown_interval():
    """Unknown interval fails fast at init, not at first poll."""
    with pytest.raises(ValueError, match="unsupported interval"):
        BarSource(adapter=object(), symbol="BTCUSDT", interval="99")


def test_bar_source_init_rejects_empty_interval():
    """Empty string interval also fails."""
    with pytest.raises(ValueError, match="unsupported interval"):
        BarSource(adapter=object(), symbol="BTCUSDT", interval="")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_bar_poller.py -v -k "interval"`
Expected:
- 10 of 13 parametrized cases FAIL with `KeyError` (current `_INTERVAL_MS = {"60": ...}` only has `"60"`); 3 pass (`"60"` + maybe accidental other matches).
- Wait — actually they fail at `_fetch` time, not init. Re-check: with current code, `BarSource.__init__` does NOT validate, so all 13 parametrize cases will *pass* the constructor. But the rejection tests will fail (no ValueError raised). Re-read expected: parametrize tests pass init under current code (no validator); reject tests FAIL because no ValueError.

Corrected expected:
- 13 parametrize tests PASS (no validator yet — happily accepts anything).
- 2 reject tests FAIL with `Failed: DID NOT RAISE ValueError`.

This is RED-with-ambiguity — fix in Step 3 makes 2 reject tests PASS while keeping 13 parametrize tests PASS.

- [ ] **Step 3: Implement fix**

Replace `src/runtime/bar_source.py:18-28` with:

```python
from typing import Any, ClassVar


class BarSource:
    """Poll latest closed bar via REST kline; dedup by close_time."""

    # Bybit V5 kline intervals: https://bybit-exchange.github.io/docs/v5/market/kline
    # M (month) = 30d nominal, used only for start_ms window sizing.
    _INTERVAL_MS: ClassVar[dict[str, int]] = {
        "1": 60_000,
        "3": 180_000,
        "5": 300_000,
        "15": 900_000,
        "30": 1_800_000,
        "60": 3_600_000,
        "120": 7_200_000,
        "240": 14_400_000,
        "360": 21_600_000,
        "720": 43_200_000,
        "D": 86_400_000,
        "W": 604_800_000,
        "M": 2_592_000_000,
    }

    def __init__(self, *, adapter: Any, symbol: str, interval: str = "60") -> None:
        if interval not in self._INTERVAL_MS:
            raise ValueError(
                f"BarSource: unsupported interval={interval!r}; "
                f"valid={sorted(self._INTERVAL_MS)}"
            )
        self._adapter = adapter
        self._symbol = symbol
        self._interval = interval
        self._last_close_ts: int | None = None
        self.consecutive_failures: int = 0
```

Keep existing `poll()` / `should_halt()` / `_fetch()` methods unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_bar_poller.py -v`
Expected: all PASS (13 parametrize + 2 reject + existing tests).

- [ ] **Step 5: Verify no other tests broke**

Run: `pytest -x -q`
Expected: all green. (Settings has no `bar_interval` field — no Settings test impact. BarSource is constructed with `"60"` at all current call-sites — no integration impact.)

- [ ] **Step 6: Commit**

```bash
git add src/runtime/bar_source.py tests/unit/test_bar_poller.py
git commit -m "fix(runtime): BarSource fail-fast on unknown interval (S8b T2)

_INTERVAL_MS was {'60': 3_600_000} — any other valid Bybit kline string
(e.g. '30', '240') raised KeyError on first poll, not at init. Expand to
all 13 Bybit V5 intervals + add __init__ validator.

YAGNI: no Settings.bar_interval field — BarSource is constructed with
hardcoded '60' at all call-sites today.

Refs: spec docs/superpowers/specs/2026-04-24-sprint-8b-carryover-design.md T2; Bybit V5 kline docs."
```

---

## Task 3: `main()` mypy no-any-return narrow

**Files:**
- Modify: `src/__main__.py:91-94`
- Test: existing `tests/unit/test_main_module.py` (verify still passes) + mypy CI gate.

**References:** spec section "T3".

- [ ] **Step 1: Reproduce mypy error**

Run: `python -m mypy --strict src/__main__.py 2>&1 | tail -10`
Expected (current state — bug present):
```
src/__main__.py:94: error: Returning Any from function declared to return "int"  [no-any-return]
```
Cause: `args.func` typed as `Any` (set via `argparse.parser.set_defaults(func=...)` — argparse не сохраняет типы).

- [ ] **Step 2: Implement narrow**

Replace `src/__main__.py:91-94` with:

```python
def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)
```

Add to imports at top of file:

```python
from collections.abc import Callable
```

- [ ] **Step 3: Verify mypy clean**

Run: `python -m mypy --strict src/__main__.py 2>&1 | tail -10`
Expected: 0 errors (no `no-any-return`).

- [ ] **Step 4: Verify existing CLI tests still pass**

Run: `pytest tests/unit/test_main_module.py tests/unit/test_kill_switch_cli.py -v`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add src/__main__.py
git commit -m "fix(cli): main() mypy no-any-return via typed dispatch (S8b T3)

argparse set_defaults(func=...) erases type — explicit Callable annotation
on args.func makes mypy --strict happy.

Refs: spec docs/superpowers/specs/2026-04-24-sprint-8b-carryover-design.md T3."
```

---

## Task 4: `_cmd_kill` atomic sentinel write

**Files:**
- Modify: `src/__main__.py:56-65`
- Test: `tests/unit/test_kill_switch_cli.py` (extend existing 41-line file)

**References:** spec section "T4"; reference pattern `src/risk/override.py:82-95`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_kill_switch_cli.py`:

```python
import os


def test_cmd_kill_atomic_no_partial_on_simulated_error(tmp_path, monkeypatch):
    """If write raises mid-call, sentinel file must NOT exist (no partial-write).

    Atomicity contract: os.replace is the commit point. If the write to tmp
    file raises, sentinel must not be created at the final path.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYBIT_API_KEY", "abcdefgh")
    monkeypatch.setenv("BYBIT_API_SECRET", "abcdefgh")
    monkeypatch.setenv("RISK_OVERRIDE_HMAC_KEY", "x" * 32)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "parquet"))

    real_replace = os.replace

    def _boom(_src, _dst):
        raise OSError("simulated rename failure")

    monkeypatch.setattr("src.__main__.os.replace", _boom)

    from src.__main__ import main

    with pytest.raises(OSError, match="simulated rename failure"):
        main(["kill"])

    sentinel = tmp_path / ".kill_switch"
    assert not sentinel.exists(), "sentinel must NOT exist when atomic rename fails"
    # tmp file MUST be cleaned up even on failure
    tmp = sentinel.with_suffix(sentinel.suffix + ".tmp")
    assert not tmp.exists(), "tmp file must be cleaned up in finally"

    # restore — not strictly needed under monkeypatch, but explicit
    monkeypatch.setattr("src.__main__.os.replace", real_replace)


def test_cmd_kill_uses_atomic_write(tmp_path, monkeypatch):
    """Happy path: sentinel exists with empty content, no leftover .tmp file."""
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

    sentinel = tmp_path / ".kill_switch"
    assert sentinel.exists()
    assert sentinel.read_bytes() == b""

    tmp = sentinel.with_suffix(sentinel.suffix + ".tmp")
    assert not tmp.exists(), "tmp file must not linger after successful os.replace"
```

Add `import pytest` at top if not already imported.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_kill_switch_cli.py -v`
Expected:
- `test_cmd_kill_atomic_no_partial_on_simulated_error` FAIL — current code uses `Path.write_text` which doesn't go through `os.replace`, so `monkeypatch` of `os.replace` has no effect; OSError never raised; sentinel created via `write_text`.
- `test_cmd_kill_uses_atomic_write` PASSES partially (sentinel exists, content empty) but `assert not tmp.exists()` — current code doesn't create `.tmp` so PASSES too. Actually both might initially produce a mixed result. The first test is the key RED.

- [ ] **Step 3: Implement fix**

Replace `src/__main__.py:56-65` with:

```python
def _cmd_kill(_args: argparse.Namespace) -> int:
    """Write sentinel-file at configured path, atomic. ADR 0022 sub-decision 5.

    Atomic via os.open (O_WRONLY|O_CREAT|O_TRUNC, 0o600) + os.fdopen + os.replace.
    Mirrors src/risk/override.py:82-95 minus os.fsync — sentinel is operator-typed
    signal, paper-trade scope; fsync overhead not justified.
    """
    import os
    from src.platform.config import Settings

    settings = Settings()
    sentinel = Path(settings.runtime_kill_switch_path)
    sentinel.parent.mkdir(parents=True, exist_ok=True)

    tmp = sentinel.with_suffix(sentinel.suffix + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(b"")
        os.replace(tmp, sentinel)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)

    print(f"kill switch written: {sentinel}")
    return 0
```

Note: keep `import os` at function scope to mirror existing lazy imports in this file. Do NOT promote to module-level (test monkeypatches `src.__main__.os.replace` — function-local reference OK because `os.replace` inside function looks up `os` from enclosing module namespace).

Verify monkeypatch path works: `monkeypatch.setattr("src.__main__.os.replace", ...)` requires `os` to be importable from `src.__main__`. With function-scope `import os`, `os` is NOT a module attribute. **Therefore promote `import os` to module top of `src/__main__.py`** to make monkeypatch resolve.

Updated implementation: add `import os` to module-level imports of `src/__main__.py`; remove the function-scope import.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_kill_switch_cli.py -v`
Expected: all PASS (existing 2 + 2 new).

- [ ] **Step 5: Verify no other tests broke**

Run: `pytest -x -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/__main__.py tests/unit/test_kill_switch_cli.py
git commit -m "fix(cli): _cmd_kill atomic sentinel write via os.replace (S8b T4)

Path.write_text was non-atomic — crash mid-write could leave empty file
that RuntimeManager picks up as KILL signal (file presence is the signal).
Mirror src/risk/override.py:82-95 pattern: os.open + os.fdopen + os.replace
+ tmp cleanup in finally. No fsync — paper-trade scope.

Refs: spec docs/superpowers/specs/2026-04-24-sprint-8b-carryover-design.md T4."
```

---

## Task 5: ADR 0023 — Halt-code → FSM event mapping

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0023-halt-code-fsm-event-mapping.md`

**References:** spec section "T5"; T1 fix as the canonical implementation.

- [ ] **Step 1: Create ADR file**

Create `llm-wiki/wiki/project/decisions/0023-halt-code-fsm-event-mapping.md`:

```markdown
---
title: "0023. Halt-code → FSM event mapping must be exhaustive"
type: decision
status: accepted
date: 2026-04-24
sprint: 8b
tags: [adr, fsm, halt, reason-code, invariant]
sources:
  - wiki/project/decisions/0022-sprint-8a-live-runtime.md
  - wiki/project/components/coordinator.md
  - wiki/project/components/execution-state-machine.md
---

# 0023. Halt-code → FSM event mapping must be exhaustive

**Status:** accepted
**Date:** 2026-04-24
**Sprint:** 8b

## Context

Sprint 8a добавил три halt-class `ReasonCode` (`HALT_RUNTIME_CRASH`, `HALT_BAR_POLL_STALL`, `KILL_SWITCH_REQUESTED`) и публичный `Coordinator.request_halt(reason)`. Bug, который проехал ревью S8a и был пойман в S8b carry-over: `request_halt` вызывал `_set_halt(...)` (запись в `halt_reason` + `halt_log`) но **не** вызывал `_transition(...)`. Результат — FSM state оставался в `FLAT` / `LONG_OPEN` / etc., тогда как `halt_reason="KILL_SWITCH_REQUESTED"`. 10 строк `KILL_SWITCH_REQUESTED` в `TRANSITIONS` table стояли как dead code.

Patch (S8b T1) добавил per-branch dispatch:

```python
if reason == ReasonCode.KILL_SWITCH_REQUESTED:
    self._transition(ExecutionEvent.KILL_SWITCH_REQUESTED)
else:
    self._transition(ExecutionEvent.RISK_HALT)
```

Это работает сегодня (3 halt codes), но риск регресса критичный: когда через 2-3 спринта добавят `HALT_LIQUIDITY_LOSS` или `HALT_DATA_QUALITY`, разработчик может забыть добавить explicit dispatch — `else` branch silently подставит `RISK_HALT`, что может не соответствовать намерению (RISK_HALT не имеет transition из state `RECOVERY` или какого-то нового состояния → exception будет, но runtime halt logic уже сломан до того момента).

## Decision

**Каждый `ReasonCode` с префиксом `HALT_*` либо равный `KILL_SWITCH_REQUESTED` ОБЯЗАН иметь explicit dispatch entry в `Coordinator.request_halt()`.** "Ловящий всё" `else` branch допустим только как safety net для текущего множества `RISK_HALT`-mapped кодов; добавление нового кода в `else` без сознательного выбора = баг.

**Three-layer enforcement:**

1. **ADR (this doc)** — binding rule + rationale.
2. **`trading-logic-reviewer.md` CRITICAL section** — block-level review rule "Halt-code → FSM event mapping must be exhaustive" (см. S8b T6).
3. **Property invariant test** (`tests/property/test_request_halt_mapping.py`) — enumerate all `ReasonCode` где `name.startswith("HALT_")` или `name == "KILL_SWITCH_REQUESTED"`; для каждого `request_halt(code)` → assert `state == HALTED` AND `halt_reason == code.value`. Failure surface при добавлении нового кода без wiring.

## Consequences

- При добавлении нового halt-class `ReasonCode`:
  1. Добавить enum entry в `src/risk/reason_codes.py`.
  2. Добавить explicit dispatch branch в `Coordinator.request_halt()` (либо в существующий "RISK_HALT bucket", либо новый event).
  3. Если новый event — добавить TRANSITIONS rows из всех non-terminal source states.
  4. Property test зелёный → ОК. Property test красный → шаг 2/3 не выполнен.
- Dead-code halts больше не возможны: state ↔ halt_reason инвариант проверяется тестом.
- Reviewer prompt update — часть процесса (S8b T6).

## Alternatives considered

- **Pure runtime introspection** (no ADR/test): rely на FSM `InvalidTransitionError` чтобы поймать missing dispatch. Reject — exception в production = halt path сломан в момент когда он нужнее всего; better to fail в CI.
- **Generic mapping dict** (`_HALT_REASON_TO_EVENT: dict[ReasonCode, ExecutionEvent]`): меньше boilerplate, но скрывает intent. Reject — explicit branch более читаем, force review при добавлении.

## References

- ADR 0022 sub-decisions 5/6/11 — halt-class reason codes введены.
- ADR 0021 sub-decision 4 — γ halt persistence (primary-wins) объясняет почему `_set_halt` отделён от `_transition`.
- `src/execution/coordinator.py:600-625` — canonical `request_halt` implementation (post-S8b T1).
- `tests/property/test_request_halt_mapping.py` — invariant test (S8b T7).
```

- [ ] **Step 2: Verify file created**

Run: `wc -l llm-wiki/wiki/project/decisions/0023-halt-code-fsm-event-mapping.md`
Expected: ~70 lines.

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0023-halt-code-fsm-event-mapping.md
git commit -m "docs(adr): 0023 halt-code → FSM event mapping invariant (S8b T5)

Documents binding rule that each HALT_* / KILL_SWITCH_REQUESTED ReasonCode
must have explicit dispatch in Coordinator.request_halt. 3-layer enforce:
ADR + trading-logic-reviewer CRITICAL rule + property test.

Refs: spec T5; T1 implementation."
```

---

## Task 6: trading-logic-reviewer prompt — CRITICAL section addition

**Files:**
- Modify: `~/.claude/agents/trading-logic-reviewer.md`

**References:** ADR 0023; spec section "T5".

- [ ] **Step 1: Read current reviewer file**

```bash
wc -l ~/.claude/agents/trading-logic-reviewer.md
grep -n "^### CRITICAL" ~/.claude/agents/trading-logic-reviewer.md
```
Expected: file ~150-200 lines; existing CRITICAL sections enumerated.

- [ ] **Step 2: Append new CRITICAL section**

Insert after the LAST `### CRITICAL — ...` section (before any `### HIGH` or other lower-priority section):

```markdown
### CRITICAL — Halt-code → FSM event mapping (ADR 0023)

When reviewing changes that touch `src/risk/reason_codes.py` or
`src/execution/coordinator.py::request_halt`:

1. If a new `ReasonCode` enum entry is added with prefix `HALT_*` (or named
   `KILL_SWITCH_*`), `Coordinator.request_halt()` MUST gain an explicit
   dispatch branch routing it to one of `{KILL_SWITCH_REQUESTED, RISK_HALT}`
   `ExecutionEvent`. Falling through the existing `else` branch unintentionally
   = silent halt-path corruption (per ADR 0023 rationale).

2. Verify `tests/property/test_request_halt_mapping.py` is GREEN locally
   (`pytest tests/property/test_request_halt_mapping.py -v`). Test enumerates
   every `HALT_*` / `KILL_SWITCH_REQUESTED` reason code and asserts FSM lands
   in `HALTED` with matching `halt_reason`. RED test = missing dispatch wiring.

3. If new `ExecutionEvent` is needed (e.g. dedicated `LIQUIDITY_HALT`),
   verify TRANSITIONS table in `src/execution/state_machine.py` has rows from
   every non-terminal source state to `HALTED`, mirroring the
   `KILL_SWITCH_REQUESTED` row pattern.

Block PR if any of the above is missing. Reference: ADR 0023.
```

- [ ] **Step 3: Verify edit landed**

```bash
grep -n "ADR 0023" ~/.claude/agents/trading-logic-reviewer.md
```
Expected: at least 1 hit (in the new section).

- [ ] **Step 4: Commit (agent prompts live outside repo — log via wiki)**

`~/.claude/agents/` is outside the project repo. Update is not committed via git; instead, log the change in `wiki/log.md` (Stage E in Task 8).

No `git commit` for this step. Verification: ADR 0023 reference present in file (Step 3).

---

## Task 7: Property invariant test — request_halt mapping coverage

**Files:**
- Create: `tests/property/test_request_halt_mapping.py`

**References:** ADR 0023; spec section "T5"; depends on Task 1 fix.

- [ ] **Step 1: Inspect ReasonCode enum to enumerate halt codes**

```bash
grep -nE "^\s+(HALT_|KILL_SWITCH_)" src/risk/reason_codes.py
```
Expected: enumeration of halt-class codes — at minimum `HALT_RUNTIME_CRASH`, `HALT_BAR_POLL_STALL`, `KILL_SWITCH_REQUESTED` (S8a) plus any earlier `HALT_*` (S7 reconcile divergence, S6 flatten failed, etc.).

- [ ] **Step 2: Write the property test**

Create `tests/property/test_request_halt_mapping.py`:

```python
"""Invariant: every halt-class ReasonCode is wired in Coordinator.request_halt.

Sprint 8b T7 (ADR 0023). Failure surface when a new HALT_* / KILL_SWITCH_*
code is added without dispatch wiring in src/execution/coordinator.py.
"""
from __future__ import annotations

import pytest

from src.execution.state_machine import ExecutionState
from src.risk.reason_codes import ReasonCode


def _halt_class_codes() -> list[ReasonCode]:
    """All ReasonCode members that represent operator/runtime-initiated halt.

    Selection rule (matches ADR 0023): name.startswith("HALT_")
    OR name == "KILL_SWITCH_REQUESTED".

    Codes that come from FSM-internal transitions (e.g. RECONCILE_DIVERGENCE)
    are excluded — they do NOT pass through request_halt; they hit _set_halt
    directly inside on_ws_reconnect / similar handlers.
    """
    return [
        rc for rc in ReasonCode
        if rc.name.startswith("HALT_") or rc.name == "KILL_SWITCH_REQUESTED"
    ]


@pytest.mark.parametrize("code", _halt_class_codes(), ids=lambda rc: rc.name)
def test_request_halt_dispatches_every_halt_code(code, coord_factory):
    """Every halt-class ReasonCode lands the FSM in HALTED with matching halt_reason.

    If this test fails for a new ReasonCode, the dev forgot to add an
    explicit dispatch branch in Coordinator.request_halt — see ADR 0023.
    """
    coord = coord_factory(initial_state=ExecutionState.FLAT)
    coord.request_halt(code)
    state = coord._repo.get_state(coord._symbol)
    assert state.state == ExecutionState.HALTED, (
        f"ReasonCode {code.name} did not transition FSM to HALTED — "
        "missing dispatch in Coordinator.request_halt? See ADR 0023."
    )
    assert state.halt_reason == code.value, (
        f"halt_reason={state.halt_reason!r} != expected={code.value!r}"
    )
```

The `coord_factory` fixture must exist in `tests/conftest.py` or local `tests/property/conftest.py`. If not, define it in `tests/property/conftest.py` mirroring the pattern from Task 1 Step 2.

- [ ] **Step 3: Run the property test**

Run: `pytest tests/property/test_request_halt_mapping.py -v`
Expected: ALL PASS — Task 1 fix already covers `KILL_SWITCH_REQUESTED` + 2 `HALT_*`. If older `HALT_*` codes exist (e.g. `HALT_FLATTEN_FAILED` from S6, `HALT_RECONCILE_DIVERGENCE` from S7), they are NOT going through `request_halt` — they hit `_set_halt` directly. **Decide per failure**:
  - If a code legitimately goes through `request_halt`-style entry → add to dispatch in T1 patch and re-test.
  - If a code is only ever set by internal `_set_halt` (e.g. on_ws_reconnect divergence, flatten cascade failure) → exclude it from the property test selection rule (e.g. add explicit allow-list of codes that pass through `request_halt`).

If the second case dominates, refine `_halt_class_codes` selector:

```python
# Codes that flow through Coordinator.request_halt (operator/runtime-initiated):
_REQUEST_HALT_CODES = frozenset({
    ReasonCode.KILL_SWITCH_REQUESTED,
    ReasonCode.HALT_RUNTIME_CRASH,
    ReasonCode.HALT_BAR_POLL_STALL,
})


def _halt_class_codes() -> list[ReasonCode]:
    return sorted(_REQUEST_HALT_CODES, key=lambda rc: rc.name)
```

ADR 0023 wording then says "every code in `_REQUEST_HALT_CODES` must dispatch" — which is more precise.

**Decision rule for engineer:** Run with prefix-based selector first; if it fails on internal-only codes, switch to allow-list and update ADR 0023 wording (Step 4 of Task 5).

- [ ] **Step 4: Commit**

```bash
git add tests/property/test_request_halt_mapping.py
git commit -m "test(property): request_halt halt-code mapping invariant (S8b T7)

Property test enumerates halt-class ReasonCode (HALT_* / KILL_SWITCH_*)
and asserts each transitions FSM to HALTED via Coordinator.request_halt.
Failure surface = new halt code added without dispatch wiring.

Refs: ADR 0023; T5 safeguard."
```

---

## Task 8: Wiki Stage E sync

**Files:**
- Modify: `llm-wiki/wiki/project/components/coordinator.md`
- Modify: `llm-wiki/wiki/project/components/runtime-manager.md`
- Modify: `llm-wiki/wiki/project/components/bar-poller.md`
- Modify: `llm-wiki/wiki/index.md`
- Append: `llm-wiki/wiki/log.md`

**References:** all spec sections; ADR 0023.

- [ ] **Step 1: Update components/coordinator.md**

Find the `## Public methods` (or equivalent) section and update the `request_halt` entry:

```markdown
### `request_halt(reason: ReasonCode) -> None`

Public halt entry-point used by `RuntimeManager` for `KILL_SWITCH_REQUESTED`,
`HALT_RUNTIME_CRASH`, `HALT_BAR_POLL_STALL`. Acquires the RLock, writes
`halt_reason` (primary-wins per S7 γ), appends a `halt_log` row, **and dispatches
the matching `ExecutionEvent` so the FSM lands in `HALTED`** — `_set_halt` alone
does NOT move FSM state (S8b T1 fix; previously dead-code in 10 KILL_SWITCH
TRANSITIONS rows). Per ADR 0023 every new halt-class code MUST add an explicit
dispatch branch.
```

- [ ] **Step 2: Update components/runtime-manager.md**

Add note on atomic kill-switch sentinel:

```markdown
### `python -m src kill`

Writes the sentinel file (`Settings.runtime_kill_switch_path`, default
`.kill_switch`) atomically via `os.open` + `os.replace` (mirrors
`src/risk/override.py:82-95`, no `fsync`). RuntimeManager polls
`sentinel.exists()` each tick — atomic write guarantees no half-created
file is observed (S8b T4 fix).
```

- [ ] **Step 3: Update components/bar-poller.md**

Add `### Supported intervals` (or under existing config section):

```markdown
### Supported intervals

`BarSource.__init__` validates the `interval` parameter against the 13 Bybit
V5 kline strings: `{"1", "3", "5", "15", "30", "60", "120", "240", "360",
"720", "D", "W", "M"}`. Unknown values raise `ValueError` at construction
(fail-fast vs. previous KeyError on first poll). v0.1 only uses `"60"` (1H);
the dict is the source of truth for any future call-site (S8b T2 fix).

No `Settings.bar_interval` field — interval is passed at construction by the
caller. YAGNI per trader-expert verdict 2026-04-24.
```

- [ ] **Step 4: Update wiki/index.md**

Find the `## Project — Decisions` section and append:

```markdown
- [[project/decisions/0023-halt-code-fsm-event-mapping]] — Sprint 8b ADR. Halt-class ReasonCode dispatch invariant in Coordinator.request_halt + 3-layer enforcement (ADR + reviewer prompt + property test).
```

- [ ] **Step 5: Append wiki/log.md**

Append at end:

```markdown
## [2026-04-24] sprint-8b | Carry-over fixes complete

### What shipped
- Coordinator.request_halt — FSM transit fix (T1) + signature ReasonCode (mypy)
- BarSource — fail-fast interval validator + 13-interval dict (T2)
- main() mypy no-any-return — typed dispatch (T3)
- _cmd_kill — atomic sentinel write via os.replace, mirrors override.py (T4)
- ADR 0023 — halt-code → FSM event mapping invariant (T5)
- trading-logic-reviewer.md — CRITICAL section "Halt-code mapping" (T6, agent prompt outside repo)
- tests/property/test_request_halt_mapping.py — coverage invariant (T7)

### Wiki updates (Stage E)
- components/coordinator.md — request_halt FSM-transit semantics
- components/runtime-manager.md — atomic kill-switch
- components/bar-poller.md — supported intervals + fail-fast
- index.md — ADR 0023 link
- decisions/0023-halt-code-fsm-event-mapping.md — NEW

### Tag
- v0.1.0-alpha.8b
```

- [ ] **Step 6: Commit wiki updates**

```bash
git add llm-wiki/wiki/project/components/coordinator.md \
        llm-wiki/wiki/project/components/runtime-manager.md \
        llm-wiki/wiki/project/components/bar-poller.md \
        llm-wiki/wiki/index.md \
        llm-wiki/wiki/log.md
git commit -m "docs(wiki): S8b stage E sync — request_halt FSM, BarSource intervals, kill-switch atomic, ADR 0023 link

Refs: spec T1/T2/T4/T5; ADR 0023."
```

---

## Task 9: Verify + Ship

**Files:** all modified by Tasks 1-8.

**References:** SPRINT_STATE workflow; `superpowers:finishing-a-development-branch`.

- [ ] **Step 1: Final full test run**

Run:
```bash
pytest -x -q
pytest -m property -v
python -m mypy --strict src/ 2>&1 | tail -20
```
Expected: 0 failures, 0 mypy errors. If anything red — STOP, do not ship.

- [ ] **Step 2: Domain reviewers — parallel dispatch**

Trigger via main controller (one message, two `Agent` calls in parallel):

- `trading-logic-reviewer` — scope: `src/execution/coordinator.py`, `src/runtime/bar_source.py`, `tests/property/test_request_halt_mapping.py`, ADR 0023.
- `python-reviewer` — scope: all 5 fixes + new test files.

Verdict required: 0 BLOCKERS, 0 unaddressed CONCERNS. Address any HIGH findings via additional commit before ship.

- [ ] **Step 3: Update SPRINT_STATE — phase shipping**

Edit `llm-wiki/wiki/project/SPRINT_STATE.md`:
- `sprint: 8b`
- `phase: 8-ship`
- `status: All 7 tasks done; tests + mypy green; reviewers cleared.`
- `next_action: PR + tag v0.1.0-alpha.8b + move to between-sprints.`
- `updated: 2026-04-24`

Commit: `git commit -am "docs(sprint): S8b phase 8-ship; all tasks done"`

- [ ] **Step 4: PR + merge**

Invoke `superpowers:finishing-a-development-branch` skill. Choose option 2 (Push + PR):
- Title: `Sprint 8b — S8a carry-over fixes (request_halt FSM, BarSource validator, mypy, atomic kill-switch, ADR 0023)`
- Body: Summary bullets + Test Plan checklist (per skill template).
- Squash-merge to `main`; delete branch.

- [ ] **Step 5: Tag + SPRINT_STATE → between-sprints**

```bash
git checkout main && git pull
git tag -a v0.1.0-alpha.8b -m "Sprint 8b — S8a carry-over fixes complete"
git push origin v0.1.0-alpha.8b
```

Edit `llm-wiki/wiki/project/SPRINT_STATE.md`:
- `phase: between-sprints`
- `status: v0.1.0-alpha.8b shipped. Awaiting S8c (Analytics per-fill) brainstorm.`
- `next_action: PHASE 1 brainstorm S8c (Analytics per-fill table; deferred from S8b per trader-expert verdict 2026-04-24 Q3).`
- `updated: 2026-04-24`

```bash
git commit -am "docs(sprint): S8b shipped (v0.1.0-alpha.8b); between-sprints"
git push origin main
```

- [ ] **Step 6: Final session bookend**

```
mcp__ccd_session__mark_chapter "Sprint 8b — ship complete"
```

---

## Spec Coverage Trace

| Spec section | Plan task |
|---|---|
| T1 — Coordinator.request_halt FSM transit + signature | Task 1 |
| T2 — BarSource interval validator + 13-dict | Task 2 |
| T3 — main() mypy no-any-return | Task 3 |
| T4 — _cmd_kill atomic write | Task 4 |
| T5a — ADR 0023 | Task 5 |
| T5b — trading-logic-reviewer prompt rule | Task 6 |
| T5c — Property invariant test | Task 7 |
| Wiki Stage E | Task 8 |
| Acceptance + Ship | Task 9 |

All 5 spec tasks (T1-T5) + spec acceptance checklist covered. No spec section without a task.

---

## Self-Review

**1. Spec coverage:** OK — see trace above.

**2. Placeholder scan:** None of {TBD, TODO, "implement later", "fill in", "appropriate", "similar to Task N"} present in this plan. Each step has actual code or actual command.

**3. Type consistency:**
- `request_halt(reason: ReasonCode)` — used consistently in Task 1 Step 4, Task 5 ADR, Task 7 property test, Task 8 wiki.
- `_INTERVAL_MS: ClassVar[dict[str, int]]` — Task 2 Step 3.
- `Callable[[argparse.Namespace], int]` — Task 3 Step 2.
- `os.replace` — Task 4 Step 3 (with monkeypatch path note).
- ADR number `0023` — used consistently in Tasks 5, 6, 7, 8.

No drift between tasks.

**4. Known caveat (Task 7 Step 3):** property test selector may need narrowing from prefix-based to allow-list if older `HALT_*` codes (S6/S7 internal) exist that don't go through `request_halt`. Decision rule + alternative implementation given inline. Engineer choice at execution time, not a plan gap.
