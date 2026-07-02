---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S61 ship — SPRINT_STATE v2 (Вариант B)
sprint: 61
phase: 8-ship
branch: feature/sprint-61-sprint-state-v2
tag: v0.1.0-alpha.60  # последний shipped (S60)
last_task_sha: a87deec  # HEAD последней задачи — точка восстановления auto-resume (S61 KIT-008)
---

## Текущий статус

**Mega-run v2 (автономный прогон, план = [[KIT-MASTER-PLAN]]).** Порядок: ~~Фаза0~~ → ~~S57~~ → ~~S58 Auto-Resume~~ → ~~S59 Gates~~ → ~~S60 Docs-Sync~~ → **S61 State v2** → S62 Manifest → S63 Fable-team → S64 Plugins(внедрить ≤2) → отчёт+push. Директива: команда агентов участвует в каждом спринте; Workflow на design-шагах.

**S61 «SPRINT_STATE v2 (Вариант B)»:** упрочнение монолита (не разделение — ADR [[decisions/0073-sprint-state-v2-variant-b]]). state-backup.sh (авто-бэкап перед коммитом, ротация 20) + state-integrity-check.sh (валидация YAML/phase/размер, fail-OPEN с авто-восстановлением из .backup) + `last_task_sha` во frontmatter (точка восстановления auto-resume). Split (Вариант A) ОТЛОЖЕН с триггерами пересмотра. Компонент: [[components/state-integrity-hook]].

**Важно при обрыве:** Auth `unset GITHUB_TOKEN GH_TOKEN` (Keychain gho_). Push origin — один, в конце прогона. src/ денежного ядра заморожен (kit-maintenance only).

## Carry (не трогаем в mega-run: src/ денежного ядра заморожен)

- **BYBIT-08** (MEDIUM) — adapter-level typed `AmbiguousOrderOutcome`, свой ADR/спринт.
- atr_breakout ATR-index offset (ADR 0064) — own ADR+WFA до live.
- D5 forfeit-N policy; Track B Kronos enrichment — DEFER; forward paper-trade harness.
- Test-hygiene: тесты пишут в tracked `data/cross_trial_sharpes.json`.

---

## Phase tracking (S61)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | chapter marked |
| 2 Brainstorm | skipped (approved backlog) | KIT-008 из UNIFIED-BACKLOG |
| 3 Plan | done | plans/2026-07-02-sprint-61-state-v2.md; PRE-PLAN arch → Вариант B BINDING |
| 4 Execute | done | T1-T5: state-backup, state-integrity+lib, last_task_sha, ADR 0073, wiring settings.json |
| 5 Verify | done | regression 32 python + 38 bash gate, ruff/bash -n/py_compile/selfcheck OK, size 3.5КБ |
| 6 Review | done | arch APPROVE_WITH_CONDITIONS (закрыт) + security: 6 раундов adversarial-hunt (1 BLOCKER+6 HIGH+3 MEDIUM все закрыты), review-s61 Blockers=0. Остаток → [[kit-op-detect-hardening-backlog]] |
| 7 Sync | done | component state-integrity-hook + ADR 0073 + index + sprint-orient/poller last_task_sha + op-detect backlog |
| 8 Ship | in_progress | sprint-61 page + squash + tag v0.1.0-alpha.61 |
| 9 Close | pending | → S62 Manifest & Telemetry |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
