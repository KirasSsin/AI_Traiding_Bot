---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S59 SHIPPED — далее S60 docs-sync
sprint: 59
phase: 4-execution
branch: feature/sprint-59-kit-gates
tag: v0.1.0-alpha.58  # последний shipped
---

## Текущий статус

**Mega-run v2 (автономный прогон, план = [[KIT-MASTER-PLAN]]).** Порядок: ~~Фаза0~~ → ~~S57~~ → **S58 Auto-Resume (приоритет оператора)** → S59 Gates → S60 Docs-Sync (+мердж chore = закрытие S56) → S61 State v2 → S62 Manifest → S63 Fable-team → S64 Plugins(внедрить ≤2) → отчёт+push. Директива: команда агентов участвует в каждом спринте; Workflow на design-шагах.

**S58 «Auto-Resume»:** сессия упёрлась в лимит → маркер → launchd-опросник → `claude --continue` при сбросе → продолжение с SPRINT_STATE.next_action. Сейчас: фоновый ресерч (claude-code-guide) + A2-анализ логов (agent), затем план-финал + PRE-PLAN architecture-reviewer.

**Важно при обрыве:** S56 docs (128 стр) на `chore/kit-integrate-headroom-ponytail`, мердж в S60 шаг 0. Auth: `unset GITHUB_TOKEN GH_TOKEN` (Keychain gho_). Push origin — один, в конце прогона.

**S57 shipped** (local main `c474f84`, tag alpha.57): kit/ в git, hooks-selfcheck, kit-inventory, секрет удалён. Счётчики: states=16, events=30, transitions=76, reason_codes=67. Детали → [[sprints/sprint-57-kit-ground-truth]].

## Carry (не трогаем в mega-run: src/ денежного ядра заморожен)

- **BYBIT-08** (MEDIUM) — adapter-level typed `AmbiguousOrderOutcome`, свой ADR/спринт.
- atr_breakout ATR-index offset (ADR 0064) — own ADR+WFA до live.
- D5 forfeit-N policy; Track B Kronos enrichment — DEFER; forward paper-trade harness.
- Test-hygiene: тесты пишут в tracked `data/cross_trial_sharpes.json`.

---

## Phase tracking (S59)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | chapter marked |
| 2 Brainstorm | skipped (approved backlog) | — |
| 3 Plan | done | plans/2026-07-02-sprint-59-kit-gates.md |
| 4 Execute | done | T1-T5 per-task коммиты |
| 5 Verify | done | red/green все 4 гейта + re-tests после ревью-фиксов; bash -n 17 хуков; selfcheck OK |
| 6 Review | done | arch APPROVE_WITH_CONDITIONS + security APPROVE w/ Concerns → ВСЕ условия закрыты; review-s59.md Blockers: 0 |
| 7 Sync | done | 2 новые component-страницы + adr-sync обновлена + index + AUTO |
| 8 Ship | done (local) | sprint-59 page + squash + tag v0.1.0-alpha.59 |
| 9 Close | done | → S60 Docs-Sync (шаг 0: мердж chore = закрытие S56) |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
