---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S65 Error-Harvest — ship
sprint: 65
phase: 8-ship
branch: feature/sprint-65-error-harvest
tag: v0.1.0-alpha.64  # последний shipped (S64)
last_task_sha: 997c8b2  # HEAD последней задачи — точка восстановления auto-resume
---

## Текущий статус

**Mega-run v2 (автономный прогон, план = [[KIT-MASTER-PLAN]]).** Порядок: ~~S57~~…~~S64~~ → **S65 Error-Harvest** → S66 Plugins(≤2) → отчёт+push. Директивы (BINDING, оператор 2026-07-02): (1) doc-first — техдоки llm-wiki RU → код → docs/ RU, гейт docs/=WARN; (2) все вызываемые агенты = kit fable-5 через Workflow (осн. луп opus 4.8 дорогой — минимизировать); (3) session-restore от техдоков llm-wiki; (4) минимум токенов. История спринтов → log.md + sprints/.

**S64 SHIPPED** (main `598729a`, tag alpha.64): doc-first правило (llm-wiki RU → код → docs/ RU; docs/=WARN) в CLAUDE.md+sprint-flow-ru+orient(4b)+manifest(3b); аудит llm-wiki (fable-5) закрыл HIGH-дрейф current-state; docs/-страница эволюции. Ревью arch APPROVE_WITH_CONDITIONS (2 HIGH закрыты). Детали → [[sprints/sprint-64-llm-wiki-doc-flow]].

**S65 «Error-Harvest» (следующий):** из логов `/Users/Apple/Downloads/session-export-1782940628374` вытащить token-waste ошибки (Edit-до-Read, workflow TS-parse, hook false-fire на merge-литерале, bash-ошибки, unicode-Edit, Read overflow, ruff re-stage, agent-registry) → превентивные паттерны. Carry из S64: current-state→AUTO-блок (kit-inventory), WARN-видимость red-тест 3 хуков, docs/ бэкфилл+repoint source_files→kit/.

**Важно при обрыве:** Auth `unset GITHUB_TOKEN GH_TOKEN` (Keychain gho_). Push origin — один, в конце прогона. src/ заморожен (kit-maintenance). SPRINT_STATE стейджить ОТДЕЛЬНО от commit (иначе state-backup не увидит staged).

## Carry (не трогаем в mega-run: src/ денежного ядра заморожен)

- **BYBIT-08** (MEDIUM) — adapter-level typed `AmbiguousOrderOutcome`, свой ADR/спринт.
- atr_breakout ATR-index offset (ADR 0064) — own ADR+WFA до live.
- D5 forfeit-N policy; Track B Kronos enrichment — DEFER; forward paper-trade harness.
- Test-hygiene: тесты пишут в tracked `data/cross_trial_sharpes.json`.

---

## Phase tracking (S65)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | chapter marked |
| 2 Brainstorm | skipped (validated) | таксономия из ground truth прогона |
| 3 Plan | done | plan + tech-страница error-taxonomy (doc-first) |
| 4 Execute | done | T1 taxonomy, T2 design-workflow fable-5, T3 skill workflow-authoring + anti-waste +5 + message-hints, T4 carry |
| 5 Verify | done | 38-case gate regression PASS, bash -n оба гейта, selfcheck, drift clean, skills 9→10 |
| 6 Review | done | design-workflow (arch + kit-auditor fable-5) = дизайн+coverage; review-s65 Blockers=0 |
| 7 Sync | done | sprint-65 + review + index + error-taxonomy |
| 8 Ship | in_progress | manifest + squash + tag v0.1.0-alpha.65 |
| 9 Close | pending | → S66 Plugins |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
