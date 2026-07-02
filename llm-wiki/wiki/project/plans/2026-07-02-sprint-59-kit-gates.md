---
title: Sprint 59 — Gates: принуждение вместо дисциплины (kit-maintenance)
type: plan
sprint: 59
updated: 2026-07-02
branch: feature/sprint-59-kit-gates
scope: кит-инфраструктура (хуки); src/ НЕ трогаем
source: KIT-MASTER-PLAN (KIT-002/003/009/013), VERIFICATION-LEDGER, A2 (75 hook-блоков: 58 = touch-шум adr-sync)
---

# План S59 — «Gates»

Фаза 2 SKIP (утверждённый бэклог). Все правки хуков: red/green через прямую подачу payload + bash -n; зеркало kit/ ↔ live синхронно (drift-guard проверит).

## Trace map

| T | KIT | Что делаем | Proof |
|---|---|---|---|
| T1 | KIT-002 | `sprint-flow-check.sh` + `phase-advance.sh`: источник истины = `SPRINT_STATE.phase`. Новая логика: (а) ветка `feature/sprint-NN-*` → прежние проверки (план-файл / Phase 5); (б) ветка НЕ sprint-паттерн И frontmatter `phase:` ∈ {2..8}* → БЛОК с инструкцией «переименуй ветку или выставь between-sprints/autoresearch»; (в) `between-sprints`/`autoresearch`/main → пропуск. *phase парсится из frontmatter `phase:` (форматы `3-plan`, `4-execution`…) | red: `chore/test`-ветка + phase:4 → exit 2 оба хука; green: та же ветка + between-sprints → exit 0; green: sprint-ветка со старым поведением |
| T2 | KIT-003 | Новый `review-gate.sh` (PreToolUse Bash): на `gh pr merge` И `git merge` sprint-веток — если diff main..HEAD трогает денежные пути (`src/signalgen|execution|risk|backtest`, `override`) → требовать `\| 6 Review \| done \|` в SPRINT_STATE И файл `llm-wiki/wiki/project/reviews/review-sNN.md` с `Blockers: 0`. Иначе exit 2. Fail-OPEN на инфра-ошибках | red: тестовый diff по src/risk без review-файла → блок; green: + review-s59.md (Blockers: 0) и Phase 6 done → пропуск; docs-only diff → пропуск без файла |
| T3 | KIT-009 | `adr-agent-sync-check.sh`: вместо mtime — содержательная проверка: для каждого изменённого ADR `NNNN-slug.md` номер `NNNN` должен встречаться grep'ом в теле ≥1 файла `~/.claude/agents/*.md`. `touch` больше не проходит (A2: 58 из 75 блоков были touch-ритуалом = шум) | red: новый ADR-номер нигде в агентах → блок; green: номер вписан в changelog-секцию агента → пропуск; touch без вписывания → всё равно блок |
| T4 | KIT-013 | Новый `pertask-state-warn.sh` (PreToolUse Bash, WARN-only exit 0): `git commit` затрагивает `src/**`, но staged-набор не содержит SPRINT_STATE.md → предупреждение в stderr (не блок — не душим bugfix-флоу; блок решим по неделе наблюдений) | коммит src-файла без state → WARN печатается, exit 0; с state → тишина |
| T5 | — | Подключение (review-gate, pertask-warn → settings.json PreToolUse), kit-зеркало, kit-inventory, component-страницы (2 новых хука + обновить 2 существующих), sprint-page | selfcheck 12 sh OK; drift clean; счётчики |

## Совместимость
- phase-advance формат строки `| 5 Verify |` сохраняется (S61 v2 мигрирует синхронно).
- Наш собственный прогон: локальный `git merge --squash` sprint-веток попадает под T2-матчер → мы сами обязаны создавать review-sNN.md с Фазы 6 каждого спринта (уже делаем по директиве; формализуется).
- hook-test скилл: red/green сценарии прогонять его механикой (env -i sandbox) где возможно.

## Фазы
1 done (chapter) → 2 skip → 3 этот файл → 4 T1-T5 → 5 bash -n + red/green всех гейтов + unit smoke → 6 architecture-reviewer + security-auditor (обход-анализ) параллельно → 7 wiki sync → 8 ship alpha.59 → 9 close → S60.
