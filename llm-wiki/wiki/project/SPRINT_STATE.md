---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-24
sprint: 8a
phase: between-sprints
branch: main
tag: v0.1.0-alpha.8a
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Sprint 8a — Live Runtime (ADR 0022) — MERGED + TAGGED.**
Merge commit `2205743`, tag `v0.1.0-alpha.8a`. Branch `feature/sprint-8a-live-runtime` сохранена локально (S6/S7 pattern).

Финальная статистика: 570 unit pass / 24 skip (clean env). 73 новых S8a-specific test'а. 3 reviewers (trading-logic opus + python-reviewer sonnet + data-integrity sonnet) — все BLOCKERS закрыты pre-merge.

S7 Resilience (ADR 0021) tag `v0.1.0-alpha.7` ранее merged.

## Завершённые задачи (S8a)

- [x] T0 Coordinator threading.RLock (6 mutation paths)
- [x] T1-T6 KILL_SWITCH_REQUESTED reason code + 10 FSM transitions + state_repo
- [x] T7-T8 Reconciler.Lock (on_wallet_event + reconcile)
- [x] T9-T11 Settings 5 runtime_* fields + threshold validator [6, 720]
- [x] T12 BarSource — REST kline poll + dedup + stall counter
- [x] T13-T17 RuntimeManager — bootstrap → ws.start → main loop → graceful shutdown
- [x] T18-T19 `python -m src` CLI (run / backfill / reconcile-only / kill)
- [x] T20 Bybit Demo integration smoke scaffold (RUN_DEMO=1 opt-in)
- [x] T21-T29 Wiki Stage E (runtime-manager + bar-poller + 3 updates + risk-register + halt-recovery + reason-codes 42→45 + index/log)
- [x] T30 Two-stage review + HIGH blockers fixed (None-guard + structlog migration + ruff cleanup)

## В процессе

(none — between-sprints)

## Следующее действие

**Open S8b brainstorm** — Sprint 8b — Analytics per-fill table + WS+REST epsilon-halt.

Старт: `/superpowers:brainstorming` → questionnaire → trader-expert → writing-plans → subagent-driven-development.

Опционально: `git push origin main && git push --tags` если нужно publish.

## Carry-over в S8b (concerns не блокирующие S8a merge)

- `request_halt` не transit'ит FSM → 10 KILL_SWITCH_REQUESTED transitions сейчас dead code. Wire в S8b.
- `BarSource._INTERVAL_MS` KeyError guard для unknown interval.
- `main()` mypy no-any-return narrow + tests ARG005 lambda-kwargs cleanup.
- Sentinel-file atomic write (mkdir + write_text race, harmless для empty).
- Pre-existing test_config.py 3 failures (env-pollution от .env, не S8a regression — CI green).
- Pre-existing test_risk_flow OverrideStore signature drift (S5 carry-over).

## Ключевые решения S8a (для истории)

- **S8 split:** S8a (live runtime) + S8b (Analytics + WS+REST epsilon). Один subsystem per sprint (B1).
- **Concurrency:** sync + 2 threads (main + pybit). NO asyncio в v0.1. Mandatory T0 = threading.RLock на Coordinator + threading.Lock на Reconciler.
- **Bar feed:** REST kline @ 5s (NO WS kline — partial bar updates incompatible с close-on-close signal).
- **Stall threshold = 24** (120s; trader-expert round 2: bar-poller stall ≠ position-safety event). Validator 6 ≤ N ≤ 720.
- **KILL_SWITCH = sentinel-file CLI** (`python -m src kill` writes `.kill_switch`). Cross-platform.
- **check_alive INLINE** в bar-poll loop (eliminates same-cadence race).
- **3 new reason codes (42→45):** 43=HALT_RUNTIME_CRASH, 44=HALT_BAR_POLL_STALL, 45=KILL_SWITCH_REQUESTED.
- **Entry-point:** `python -m src` + argparse subcommands.
- **DELETE:** `src/controller.py` + `main.py` (orphans broken since S2).

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Перенеси task из "В процессе" → "Завершённые задачи" (checkbox)
3. Обнови "Следующее действие" — конкретное, с командой если применимо
4. Добавь в "Ключевые решения" только нетривиальное
5. Обнови `updated:` в frontmatter
