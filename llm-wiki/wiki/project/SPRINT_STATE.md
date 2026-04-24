---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-24-s8a-adr-accepted
sprint: 8a-live-runtime
phase: 3-planning
branch: main
tag: v0.1.0-alpha.7
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Sprint 8a — Live Runtime (ADR 0022) — phase 3 (planning).**
ADR 0022 ACCEPTED 2026-04-24. Trader-expert verdicts: round 1 (10 CONFIRM / 7 REVISE / 1 DEFER, 18 questions), round 2 (U1 REVISE: stall threshold 12→24). U2 user choice: sentinel-file CLI for KILL_SWITCH.

S7 Resilience (ADR 0021) merged, tag `v0.1.0-alpha.7`. S8b (Analytics per-fill) deferred until S8a merge.

## Завершённые задачи (S7, 25 tasks)

- [x] Migration 0005_halt_persistence.sql (halt_reason + last_exit_reason + bootstrap_at + halt_log audit)
- [x] FSM v3: 16 states / 29 events / 59 transitions (-2 silent dups, +6 reconcile/timeout)
- [x] Reconciler 4-valued verdict (AGREE/DIVERGENCE/HEAL_ENTRY_FILLED/EXITED) + heal_max_age_seconds=3600
- [x] Coordinator.bootstrap() always reconciles + _bootstrap_done assert + _RECONCILABLE_STATES (9 states)
- [x] start_bracket entry_ack.order_id capture для HEAL path
- [x] BybitPrivateWSConsumer: pybit close-hook + check_alive watchdog (ADR 0021 sub-decision 6)
- [x] Reason codes 39→42 (+HALT_BOOTSTRAP_AMBIGUOUS, +HALT_EXIT_RECONCILE_DIVERGENCE, +EXIT_RECONCILE_DETECTED)
- [x] γ halt persistence (write-ahead halt_log → execution_state.halt_reason; primary-wins)
- [x] Property test: bootstrap+ws-reconnect idempotent under N reconnects
- [x] Integration test (opt-in Demo): bootstrap HEAL path
- [x] Final domain reviewers (parallel trading-logic + python): 7 BLOCKERS closed (commit 97b29cb)
- [x] Test suite: 481 unit/integration/property pass; 28 skipped (pre-existing gaps unrelated)
- [x] Wiki Stage E: 5 components + runbook + NEW ws-private-consumer.md + reason-codes + index + log

## В процессе

S8a PHASE 3 — writing-plans для ADR 0022 (~30 TDD tasks). Plan path: `wiki/project/plans/2026-04-24-sprint-8a-live-runtime.md`.

## Следующее действие

Dispatch writing-plans для S8a. После plan approval → branch `feature/sprint-8a-live-runtime` + PHASE 4 subagent-driven execution. Task 0 = threading lock policy (mandatory prerequisite).

Опционально (operator): `git push origin main && git push --tags` если S7 ещё не запушен.

## Ключевые решения S8a brainstorm

- **S8 split:** S8a (live runtime) + S8b (Analytics + WS+REST epsilon). Один subsystem per sprint (B1 principle).
- **Concurrency:** sync + 2 threads (main + pybit). NO asyncio в v0.1. Mandatory Task 0 = threading.RLock на Coordinator + threading.Lock на Reconciler.
- **Bar feed:** REST kline @ 5s (NO WS kline — partial bar updates incompatible с close-on-close signal).
- **Stall threshold = 24** (120s; trader-expert round 2: bar-poller stall ≠ position-safety event, OCO bracket exchange-side preserves capital). Validator 6 ≤ N ≤ 720.
- **KILL_SWITCH = sentinel-file CLI** (`python -m src kill` writes `.kill_switch`). Cross-platform, no signal collision (vs SIGUSR1 alternative rejected).
- **check_alive INLINE** в bar-poll loop (eliminates same-cadence race с separate worker thread).
- **REST canonical wallet truth** (per ADR 0020 sub-decision 4) — drop wallet_disagreement_epsilon (defer to S8b).
- **3 new reason codes (42→45):** 43=HALT_RUNTIME_CRASH, 44=HALT_BAR_POLL_STALL, 45=KILL_SWITCH_REQUESTED.
- **Entry-point:** `python -m src` + argparse subcommands (run/backfill/reconcile-only/kill).
- **DELETE:** `src/controller.py` + `main.py` (orphans broken since S2).

## Блокеры / concerns

- Pre-existing test_risk_flow OverrideStore signature drift (unrelated to S7).
- pyarrow/talib/asyncio test gaps (28 skipped) — defer до S8+.

## Активные файлы (где работаем — S8a)

**NEW:**
- `src/runtime/__init__.py` + `manager.py` + `bar_source.py` — RuntimeManager owns lifecycle
- `src/__main__.py` — argparse entry-point

**MODIFY:**
- `src/execution/coordinator.py` — Task 0: RLock на 6 методов
- `src/execution/reconciler.py` — Task 0: Lock на 2 метода
- `src/platform/config.py` — 5 new runtime_* settings + validator
- `src/execution/reason_codes.py` — +43, +44, +45

**DELETE:**
- `src/controller.py` (orphan, broken since S2)
- `main.py` (root, ImportError на src.controller)

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Перенеси task из "В процессе" → "Завершённые задачи" (checkbox)
3. Обнови "Следующее действие" — конкретное, с командой если применимо
4. Добавь в "Ключевые решения" только нетривиальное
5. Обнови `updated:` в frontmatter
