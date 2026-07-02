---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S61 SHIPPED (alpha.61) — далее S62 Manifest & Telemetry
sprint: 61
phase: between-sprints
branch: main
tag: v0.1.0-alpha.61  # последний shipped (S61)
last_task_sha: 35ae188  # squash S61 на main — точка восстановления auto-resume
---

## Текущий статус

**Mega-run v2 (автономный прогон, план = [[KIT-MASTER-PLAN]]).** Порядок: ~~Фаза0~~ → ~~S57~~ → ~~S58 Auto-Resume~~ → ~~S59 Gates~~ → ~~S60 Docs-Sync~~ → ~~S61 State v2~~ → **S62 Manifest** → S63 Fable-team → S64 Plugins(внедрить ≤2) → отчёт+push. Директива: команда агентов участвует в каждом спринте; Workflow на design-шагах.

**S61 SHIPPED** (main `35ae188`, tag alpha.61): SPRINT_STATE v2 Вариант B — state-backup + state-integrity (fail-OPEN restore) + last_task_sha. Закалка по 6 раундам adversarial bypass-hunt (1 BLOCKER + 6 HIGH + 3 MEDIUM закрыты; 32 python + 38 bash regression). Остаток → [[kit-op-detect-hardening-backlog]] + S62 tamper-evidence. Детали → [[sprints/sprint-61-state-v2]].

**S62 «Manifest & Telemetry» (следующий):** skill-firing manifest в sprint-finish (P1-MANIFEST), kit-validation-checklist, cascade-хук (block full-read banned-файлов), budget-хук ревизия, tuning ADR (AUTOCOMPACT/MAX_THINKING). Carry: KIT-022 (malformed-frontmatter WARN), KIT-025 (heredoc→external .py), tamper-evidence review-артефактов (S59/S61 остаток).

**Важно при обрыве:** Auth `unset GITHUB_TOKEN GH_TOKEN` (Keychain gho_). Push origin — один, в конце прогона. src/ денежного ядра заморожен (kit-maintenance only). SPRINT_STATE стейджить ОТДЕЛЬНО от commit (иначе state-backup не увидит staged).

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
| 8 Ship | done | squash main 35ae188 + tag v0.1.0-alpha.61 |
| 9 Close | done | SPRINT_STATE between-sprints + log; → S62 Manifest & Telemetry |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
