---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S66 SHIPPED (alpha.66) — mega-run завершён; финал = отчёт + push
sprint: 66
phase: between-sprints
branch: main
tag: v0.1.0-alpha.66  # последний shipped (S66) — ФИНАЛ прогона
last_task_sha: 77cb996  # squash S66 на main — точка восстановления auto-resume
---

## Текущий статус

**Mega-run v2 ЗАВЕРШЁН** (план = [[KIT-MASTER-PLAN]]). ~~S57~~…~~S66~~ отгружены локально (теги alpha.57…alpha.66). **Финал (осталось):** (1) `kit-upgrade-report.md` — сводка S57-S66; (2) **ОДИН** git push origin (весь прогон локально; `unset GITHUB_TOKEN GH_TOKEN`).

**S66 SHIPPED** (main `77cb996`, tag alpha.66): ресерч Claude Code плагинов → внедрён Context7 MCP (`.mcp.json`, docs библиотек, токен-экономия, reversible); Frontend Design → оператору (OQ-7); дубли отклонены (кит зрелый). Детали → [[sprints/sprint-66-plugins]] · [[plugins-research]].

**Carry (после прогона / оператору):** KIT-OD-1 (op-detect argv-классификация, выделенный security-спринт), KIT-OD-2 (tamper review↔diff), current-state→AUTO-блок kit-inventory, docs/ бэкфилл S57-63 + repoint source_files→kit/, tuning A/B (ADR 0074). OQ: 1 (токен), 4 (CLI /login), 5 (reload агентов), 6 (doc-writer тир), 7 (Frontend Design).

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
| 8 Ship | done | manifest 7/7 + squash main 77cb996 + tag v0.1.0-alpha.66 |
| 9 Close | done | mega-run завершён; → ФИНАЛ: kit-upgrade-report + один push origin |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
