---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S66 Plugins (финал) — ship
sprint: 66
phase: 8-ship
branch: feature/sprint-66-plugins
tag: v0.1.0-alpha.65  # последний shipped (S65)
last_task_sha: 20d81c2  # HEAD последней задачи — точка восстановления auto-resume
---

## Текущий статус

**Mega-run v2 (автономный прогон, план = [[KIT-MASTER-PLAN]]).** Порядок: ~~S57~~…~~S65~~ → **S66 Plugins(≤2)** → отчёт+push (финал). Директивы (BINDING, оператор 2026-07-02): (1) doc-first — техдоки llm-wiki RU → код → docs/ RU, гейт docs/=WARN; (2) все вызываемые агенты = kit fable-5 через Workflow; (3) session-restore от техдоков llm-wiki; (4) минимум токенов. История → log.md + sprints/.

**S65 SHIPPED** (main `20d81c2`, tag alpha.65): таксономия 9 классов token-waste ошибок → skill workflow-authoring (parse-safe) + CLAUDE.md anti-waste +5 строк + message-hints в phase-advance/review-gate (матчер не тронут, 38-case regression intact). Дизайн fable-5 (arch+kit-auditor). Root op-detect → KIT-OD-1. Детали → [[sprints/sprint-65-error-harvest]].

**S66 «Plugins & Best Practices» (ФИНАЛ):** ресерч популярных Claude Code плагинов по звёздам GitHub, валидация совместимости, **внедрить ≤2** лучших (директива v2) с токен-метрикой, отчёт `plugins-research.md` (OQ-2). Затем kit-upgrade-report.md (сводка S57-S66) + **ОДИН** git push origin (весь прогон локально до сюда). Carry: current-state→AUTO-блок, docs/ бэкфилл+repoint→kit/, KIT-OD-1 (op-detect argv).

**Важно при обрыве:** Auth `unset GITHUB_TOKEN GH_TOKEN` (Keychain gho_). Push origin — один, в конце прогона. src/ заморожен (kit-maintenance). SPRINT_STATE стейджить ОТДЕЛЬНО от commit (иначе state-backup не увидит staged).

## Carry (не трогаем в mega-run: src/ денежного ядра заморожен)

- **BYBIT-08** (MEDIUM) — adapter-level typed `AmbiguousOrderOutcome`, свой ADR/спринт.
- atr_breakout ATR-index offset (ADR 0064) — own ADR+WFA до live.
- D5 forfeit-N policy; Track B Kronos enrichment — DEFER; forward paper-trade harness.
- Test-hygiene: тесты пишут в tracked `data/cross_trial_sharpes.json`.

---

## Phase tracking (S66 — финал)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | chapter marked |
| 2 Brainstorm | skipped | директива v2 (внедрить ≤2) |
| 3 Plan | done | web-ресерч + tech-страница plugins-research (doc-first) |
| 4 Execute | done | T1 ресерч, T2 фильтр (дубли отклонены), T3 Context7 в .mcp.json, T4 Frontend Design → OQ-7 |
| 5 Verify | done | .mcp.json валиден (3 сервера), Context7 v3.2.2 на npm, не дублирует |
| 6 Review | done | low-risk (ресерч+1 MCP, reversible); review в sprint-66; Blockers=0 |
| 7 Sync | done | plugins-research + sprint-66 + OQ-7 + index |
| 8 Ship | in_progress | manifest + squash + tag v0.1.0-alpha.66 |
| 9 Close | done-next | → ФИНАЛ: kit-upgrade-report + один push origin |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
