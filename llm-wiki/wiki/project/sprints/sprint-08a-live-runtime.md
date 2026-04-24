---
title: Sprint 8a — Live Runtime (RuntimeManager + REST bar poller + KILL_SWITCH + threading lock policy)
type: sprint
tags: [sprint-8a, execution, runtime, orchestration, bar-poller, kill-switch, threading, adr-0022]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/decisions/0022-sprint-8a-live-runtime
  - project/plans/2026-04-24-sprint-8a-live-runtime
---

# Sprint 8a — Live Runtime

## Overview

Sprint 8a закрывает критический gap из S7: до S8a Coordinator/Reconciler/FSM работали ТОЛЬКО в unit-test fixtures — bot не запускался end-to-end. S8a поднимает live runtime: `python -m src run` стартует и торгует на Demo Mainnet. Закрывает ADR 0021 line 364 deferral (KILL_SWITCH wired через sentinel-file CLI). Driver loop ownership = `RuntimeManager` (ADR 0022 sub-decision 1: sync + threading, NOT asyncio). Threading lock policy на Coordinator (RLock 6 methods) + Reconciler (Lock 2 methods) — Task 0 mandatory против pybit thread × main thread race. Reason codes 42 → 45 (HALT_RUNTIME_CRASH, HALT_BAR_POLL_STALL, KILL_SWITCH_REQUESTED). FSM +11 KILL_SWITCH_REQUESTED transitions (59 → 70).

**S8 split:** S8a = orchestration (this sprint); S8b = carry-over fixes + ADR 0023 ([[sprint-08b-carryover]]).

**Trader-expert verdict applied:** brainstorm round 1 (10 CONFIRM / 7 REVISE / 1 DEFER) + round 2 single-item (U1 stall threshold 12→24).

## Plan / ADR links

- Plan: [[../plans/2026-04-24-sprint-8a-live-runtime]]
- ADR (NEW): [[../decisions/0022-sprint-8a-live-runtime]]
- ADR (extends): [[../decisions/0021-sprint-7-resilience]]

## Deliverables

37 commits на ветке `feature/sprint-8a-live-runtime`. Squash-merge `2205743` (--no-ff) → tag `v0.1.0-alpha.8a`. 2411 +/255 - LoC. 73 new S8a-specific tests across runtime/FSM/lock/CLI scopes.

### RuntimeManager (G1) — process lifecycle owner

- `src/runtime/manager.py` (231 LoC) — `RuntimeManager` class:
  - `run()` blocking entry: bootstrap → start WS consumer → tick loop → graceful shutdown
  - Tick pipeline (single-thread, sequential): `_maybe_kill_switch` → `_check_alive_inline` → `_poll_bar_and_strategy` → `_poll_or_arm_oco`
  - Crash path: unhandled exception → `coordinator.request_halt(HALT_RUNTIME_CRASH)` → `_shutdown(reason=HALT_RUNTIME_CRASH)` → re-raise
  - Idempotent `shutdown(reason)` (graceful drain)
- See [[../components/runtime-manager]]

### REST bar poller (G2)

- `src/runtime/bar_source.py` (~150 LoC) — `BarSource` class:
  - REST `kline` 5s cadence (default `runtime_bar_poll_cadence_seconds=5`)
  - Stall detection: N consecutive failures → `should_halt() → True` → `request_halt(HALT_BAR_POLL_STALL)` (default N=24 = 120s, trader-expert round 2 verdict: bar-poller stall ≠ position-safety event, OCO bracket exchange-side, false-halt cost dominates)
  - Catch-up reads bars без signal generation (no look-ahead)
- See [[../components/bar-poller]]

### KILL_SWITCH wiring (G3) — sentinel-file CLI

- `src/__main__.py:_cmd_kill` — `python -m src kill` writes `Settings.runtime_kill_switch_path` (default `.kill_switch`)
- RuntimeManager polls `sentinel.exists()` каждый tick → `request_halt(KILL_SWITCH_REQUESTED)` → `_stopping = True`
- Choice rationale: sentinel chosen over SIGUSR1 (supervisor collision risk, trader-expert verdict)
- (S8b T4 follow-up: atomic write via `os.open`+`os.replace`)

### Threading lock policy (G4) — Task 0 mandatory

- `src/execution/coordinator.py` — `threading.RLock` (reentrant) wraps 8 public methods: `bootstrap`, `start_bracket`, `on_order_event`, `on_ws_reconnect`, `arm_oco`, `flatten`, `request_halt`, `reconcile_arming_ttl`
- `src/execution/reconciler.py` — `threading.Lock` (non-reentrant) wraps 2 methods: `on_wallet_event`, `reconcile`
- Защищает от pybit thread (event callbacks) × main thread (RuntimeManager tick) race на shared FSM row

### Reason codes (G5) — 42 → 45

- `src/risk/reason_codes.py` — 3 new ADR 0022 entries:
  - `HALT_RUNTIME_CRASH` (43): unhandled exception в `RuntimeManager.run()`
  - `HALT_BAR_POLL_STALL` (44): N consecutive REST kline failures
  - `KILL_SWITCH_REQUESTED` (45): sentinel-file `.kill_switch` detected (operator-initiated)

### FSM expansion — KILL_SWITCH_REQUESTED event + 11 transitions

- `src/execution/state_machine.py` — `ExecutionEvent.KILL_SWITCH_REQUESTED` (new, 30th event)
- 11 transitions: `(state, KILL_SWITCH_REQUESTED) → KILLED` for всех non-terminal states (FLAT, ENTRY_PENDING, LONG_OPEN, OCO_ARMING, OCO_ARMED, EXIT_PENDING, EXIT_SIBLING_CANCELLING, EXIT_SIBLING_CANCEL_FAILED, EXIT_SL_RESIDUAL, RECONCILING, HALTED)
- TRANSITIONS: 59 → 70
- See [[../components/execution-state-machine]]

### Entry point (G6)

- `src/__main__.py` (117 LoC) — `python -m src` argparse subcommands:
  - `run` — start RuntimeManager (TODO: full DI wiring deferred to T20 integration test)
  - `backfill --from --to` — delegate to scripts
  - `reconcile-only` — bootstrap + reconcile, no trading loop
  - `kill` — write sentinel file (S8b T4: atomic via os.open+os.replace)

### Orphan cleanup (G7)

- Removed: `src/controller.py` (broken since S2), `main.py` top-level (imports broken `src.controller`)

### Demo Mainnet integration test (G8)

- `tests/integration/test_runtime_smoke.py` — opt-in `RUN_DEMO=1`. Full bring-up → one bar tick → graceful shutdown.

## Reviewer summary

- trading-logic (sonnet): NO blockers
- python-reviewer (sonnet): 2 HIGH BLOCKERs fixed in `0e2359c` — None-guard for `assessment.qty/tp_price/sl_price` + structlog migration `manager.py`/`bar_source.py`
- data-integrity (sonnet): NO blockers
- Lint cleanup `62be604` (UP037 + ARG001 + F401, ruff clean)

## Tests

- 570 unit pass / 24 skipped (clean env)
- 73 new S8a-specific tests
- 3 pre-existing test_config.py failures = local `.env` env-pollution (verified false positive on clean clone — CI green)

## Wiki updates (Stage E)

- runtime-manager.md NEW (T8 deliverable)
- bar-poller.md NEW (T8 deliverable)
- index.md +runtime-manager / +bar-poller (T8)
- log.md (S8a session-end + sprint-ship entries 2026-04-24)
- This sprint page (created в pre-S8c batch 2026-04-25 per Bucket A2)

## Carry-over → S8b

Closed by S8b ([[sprint-08b-carryover]]):
1. ✅ `request_halt` → wire FSM transition (10 KILL_SWITCH_REQUESTED transitions currently dead code) — S8b T1
2. ✅ `BarSource._INTERVAL_MS` KeyError guard — S8b T2
3. ✅ `main()` mypy no-any-return narrow + tests ARG005 cleanup — S8b T3
4. ✅ Sentinel-file atomic write — S8b T4

## Key decisions (для истории, ADR 0022 highlights)

- **Concurrency model = sync + threading** (Q1 CONFIRM, CC1 REVISE добавляет lock policy). Async/await migration → S9+.
- **Bar poller = REST kline** (Q2 CONFIRM). Cadence 5s, не WS-based, decouples от pybit thread.
- **Stall threshold = 24** (U1 trader-expert round 2 REVISE, бывший 12) — bar-poller stall ≠ position-safety event.
- **KILL_SWITCH = sentinel-file** (U2 trader-expert verdict) — chosen over SIGUSR1 (supervisor collision risk).
- **RuntimeManager owns lifecycle**, NOT Coordinator (Coordinator = FSM owner; RuntimeManager = process owner).

## Related

- Prior sprint: [[sprint-07-resilience]] (S7)
- Next sprint: [[sprint-08b-carryover]] (S8b)
- Components: [[../components/runtime-manager]], [[../components/bar-poller]], [[../components/coordinator]], [[../components/execution-state-machine]], [[../components/ws-private-consumer]]
- Runbooks: [[../runbooks/halt-recovery]] — HALT_RUNTIME_CRASH / HALT_BAR_POLL_STALL / KILL_SWITCH_REQUESTED post-mortem
