---
title: Kill-switch CLI + entry-point (`python -m src`)
type: component
tags: [cli, kill-switch, operator, entry-point, sentinel-file, atomic-write, sprint-8a, sprint-8b, adr-0022, adr-0023]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/__main__.py
  - wiki/project/decisions/0022-sprint-8a-live-runtime.md
  - wiki/project/decisions/0023-halt-code-fsm-event-mapping.md
---

# Kill-switch CLI + entry-point

**TL;DR:** Operator-facing CLI surface — `python -m src <subcommand>` (ADR 0022 sub-decisions 5+9). Exposes four subcommands: kill / run / backfill / reconcile-only. Kill writes `.kill_switch` sentinel atomically; RuntimeManager polls each tick and halts via FSM dispatch (`KILL_SWITCH_REQUESTED → KILLED`) per ADR 0023 invariant.

**File:** `src/__main__.py` (117 LoC, S8a G6 + S8b T3/T4).

## Команды

| Command | Purpose | Status (S8b) |
|---------|---------|---------------|
| `python -m src run [--symbol SYMBOL]` | Start RuntimeManager (blocking — full bring-up) | Stub — DI wiring deferred to T20 integration test reference |
| `python -m src backfill --from DATE --to DATE` | OHLCV backfill (delegate to scripts/backfill.py) | Stub delegating (prints args, returns 0) |
| `python -m src reconcile-only [--symbol SYMBOL]` | Bootstrap + reconcile, no trading loop | Stub — same DI blocker as `run` |
| `python -m src kill` | Write `.kill_switch` sentinel atomically + exit 0 | LIVE (S8b T4 — atomic `os.open`+`os.replace`) |

Argparse handler type: `Callable[[argparse.Namespace], int]` — typed dispatch fixed in S8b T3 (mypy `--strict` compliance).

**Why `python -m src` not `bot`:** package is named `src` (per `pyproject.toml`). No `console_scripts` entry — avoids packaging complexity with zero v0.1 payoff (ADR 0022 sub-decision 9).

## `python -m src kill` — семантика записи sentinel-file

### Определение пути

- Default: `Settings.runtime_kill_switch_path = ".kill_switch"` (ADR 0022 sub-decision 5)
- Configurable via `RUNTIME_KILL_SWITCH_PATH` env var

### Атомарная запись (S8b T4)

Uses POSIX atomic-rename pattern, mirrors `src/risk/override.py:82-95` minus `os.fsync`:

```python
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

**Why no `fsync`:** sentinel is an operator-typed signal, paper-trade scope; fsync overhead not justified (trader-expert verdict, ADR 0022 sub-decision 5 rationale). Compare: `override.py` uses `fsync` because it guards money-critical safety overrides.

**Why module-level `import os`:** needed for `monkeypatch.setattr("src.__main__.os.replace", ...)` resolution in S8b T4 atomicity test (`tests/unit/test_kill_switch_cli.py`).

### Режим файла

`0o600` (owner read/write only) — prevents accidental tamper by other users on shared host. Tmp file also gets `0o600` before rename.

### Очистка устаревшего sentinel

`RuntimeManager.run()` unlinks `.kill_switch` on startup if it exists (stale from prior session). Without this cleanup the process would immediately halt on first tick (ADR 0022 sub-decision 5, lifecycle note).

## Опрос RuntimeManager

Each tick, `_maybe_kill_switch` executes as step 1 of the tick pipeline:

```python
def _maybe_kill_switch(self):
    if self._kill_switch_path.exists():
        self._coordinator.request_halt(KILL_SWITCH_REQUESTED)
        self._stopping = True
```

1. `sentinel.exists()` check (non-blocking filesystem call)
2. If `True` → `coordinator.request_halt(KILL_SWITCH_REQUESTED)` + set `_stopping = True`
3. Main loop exits; graceful `_shutdown(reason=KILL_SWITCH_REQUESTED)` called
4. `runtime.kill_switch_detected {sentinel_path}` structlog event emitted

Polling latency = 1 tick (5s by default, `Settings.runtime_bar_poll_cadence_seconds`). Acceptable for manual operator action (ADR 0022 sub-decision 5 — SIGUSR1 rejected due to supervisor collision risk).

См. [[runtime-manager]] tick pipeline для full step order.

## Диспетчеризация FSM (инвариант ADR 0023)

`Coordinator.request_halt(KILL_SWITCH_REQUESTED)` per ADR 0023:

- Calls `_set_halt(reason)` (write `halt_reason` + `halt_log` row, S7 γ primary-wins persistence)
- Then explicit dispatch branch: `self._transition(ExecutionEvent.KILL_SWITCH_REQUESTED)`
- **HALTED-guard:** skip transition if already in HALTED state (preserves S7 γ idempotency)
- **11 transitions** cover all non-terminal source states: FLAT, ENTRY_PENDING, LONG_OPEN, OCO_ARMING, OCO_ARMED, EXIT_PENDING, EXIT_SIBLING_CANCELLING, EXIT_SIBLING_CANCEL_FAILED, EXIT_SL_RESIDUAL, RECONCILING, HALTED

**ADR 0023 binding rule:** every `ReasonCode` with prefix `HALT_*` or equal to `KILL_SWITCH_REQUESTED` MUST have explicit dispatch entry in `Coordinator.request_halt()`. Enforced by property invariant test `tests/property/test_request_halt_mapping.py` (enumerates all qualifying `ReasonCode` values, asserts `state == HALTED` AND `halt_reason == code.value` after each `request_halt` call). Catches missing wiring at CI time rather than in production.

canonical implementation: `src/execution/coordinator.py:600-625` (post-S8b T1).

См. [[execution-state-machine]] + [[../decisions/0023-halt-code-fsm-event-mapping]] для invariant detail.

## Восстановление (процедура оператора)

After a kill-switch halt:

1. RuntimeManager logs `runtime.kill_switch_detected` + `runtime.shutdown {reason=KILL_SWITCH_REQUESTED}` and exits
2. Operator investigates root cause (structlog JSON, `halt_log` table audit)
3. Manually delete sentinel: `rm .kill_switch`
4. Restart: `python -m src run`
5. RuntimeManager startup unlinks any stale `.kill_switch`, then calls `coordinator.bootstrap()` → reconciler 4-valued verdict
6. If HEAL applied → resume OK; if DIVERGENCE → HALTED state, requires manual_reset

## Почему sentinel-file (не SIGUSR1)

ADR 0022 sub-decision 5 evaluated both options:

| Mechanism | Issue | Verdict |
|-----------|-------|---------|
| SIGUSR1 | Conflict with systemd/launchd supervisor semantics; macOS launchd uses SIGUSR* for its own purposes | Rejected |
| Sentinel-file | Cross-platform, no signal collision, deterministic under supervisor; 1-tick (5s) latency acceptable for manual action | Chosen |

## Тесты

- `tests/unit/test_kill_switch_cli.py` — `python -m src kill` writes file atomically; `os.replace` monkeypatched for atomicity assertion (S8b T4)
- `tests/unit/test_main_module.py` — argparse subcommand routing, `_build_parser()` help text
- `tests/unit/test_runtime_manager.py` — `_maybe_kill_switch` detection → graceful shutdown; stale file removed on startup
- `tests/property/test_request_halt_mapping.py` — ADR 0023 exhaustive dispatch invariant (S8b T7)

## Вне scope / отложено

- **SIGUSR1 handler** — deferred per ADR 0022 (supervisor collision risk, sentinel chosen). v0.2 may add as secondary trigger.
- **External REST endpoint** — risk-dashboard override hook → v0.2.
- **Systemd/launchd service unit** — ops concern, separate artifact post-tag.
- **`run` + `reconcile-only` full DI wiring** — TODO carry-over; T20 integration test reference will establish wiring pattern.

## Ссылки из

- [[coordinator]] — `request_halt(KILL_SWITCH_REQUESTED)` triggered by sentinel detection
- [[runtime-manager]] — `_maybe_kill_switch` tick step polls sentinel; calls `request_halt` + sets `_stopping = True`
- [[../decisions/0022-sprint-8a-live-runtime]] — ADR sub-decisions 5+6 (sentinel-file + entry-point)
- [[../decisions/0023-halt-code-fsm-event-mapping]] — KILL_SWITCH_REQUESTED dispatch invariant

## Связанные

- [[runtime-manager]] — owns tick pipeline + `_maybe_kill_switch` step + lifecycle
- [[coordinator]] — `request_halt` FSM dispatch (ADR 0023 invariant)
- [[execution-state-machine]] — `KILL_SWITCH_REQUESTED` event + 11 transitions (FSM total: 74)
- [[risk-override]] — same atomic-write pattern (template for kill-switch S8b T4)
- [[../decisions/0022-sprint-8a-live-runtime]] — sub-decisions 5 (sentinel-file), 9 (entry-point)
- [[../decisions/0023-halt-code-fsm-event-mapping]] — halt-code → FSM event exhaustive mapping
- [[../runbooks/halt-recovery]] — operator runbook covering KILL_SWITCH_REQUESTED + 18 другие halt codes (Operational class group)

## Источники

- `src/__main__.py` — full file (117 LoC, S8a G6 + S8b T3/T4)
- ADR 0022 sub-decisions 5, 9, G3, G6
- ADR 0023 (halt-code → FSM event mapping invariant, S8b)
- S8b T4 commit (atomic write fix: `os.open`+`os.replace`, tmp cleanup in `finally`)
