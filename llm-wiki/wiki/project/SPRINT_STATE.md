---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S58 auto-resume (приоритет оператора) — mega-run v2 (S57 shipped)
sprint: 58
phase: 3-plan
branch: feature/sprint-58-auto-resume
tag: v0.1.0-alpha.57  # последний shipped
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

## Phase tracking (S58)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | chapter marked; ветка auto-resume |
| 2 Brainstorm | done | ресерч claude-code-guide + A2 (102ч простоя); PRE-PLAN arch APPROVE_WITH_CONDITIONS |
| 3 Plan | done | plans/2026-07-02-sprint-58-auto-resume.md + условия C-1..C-3 вписаны |
| 4 Execute | done | T1-T4, per-task коммиты; C-1/C-3 закрыты в коде |
| 5 Verify | done | 7 мок-сценариев + hardening (badsid/malformed) green; plutil/bash -n/py_compile OK; launchd loaded, kickstart чистый |
| 6 Review | done | security APPROVE (LOW×3 исправлены в спринте) + arch post-impl APPROVE (условия закрыты) |
| 7 Sync | done | component page + index + CLAUDE.md + AUTO-блоки; kit-drift clean |
| 8 Ship | done (local) | sprint-58 page + squash-merge + tag v0.1.0-alpha.58 |
| 9 Close | done | OQ-4 оператору (CLI /login) → сразу S59 Gates |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
