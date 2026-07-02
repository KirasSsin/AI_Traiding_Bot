---
title: Sprint 63 — Fable-5 Team (план)
type: plan
sprint: 63
created: 2026-07-02
status: active
---

# S63 — Fable-5 Team (mega-run 7/8)

**Цель:** команда агентов на fable-5 (kit-работа), политика пинов, три новых агента для kit-цикла (kit-auditor / merge-analyst / release-manager), смоук-проверка.

## Задачи

| T | ID | Что | Acceptance |
|---|---|---|---|
| T1 | MATRIX-4.1 | architecture-reviewer + trader-expert → claude-fable-5 (security-auditor уже fable-5) | model-пин fable-5, kit+live sync |
| T2 | PIN-POLICY | ADR 0075: политика «когда пинить версию vs алиас» + триггер ревью при смене платформенного дефолта + скан stale-пинов (frontend-developer opus-4-7) | ADR + список пинов приведён к политике |
| T3 | KIT-AUDITOR | Новый агент `kit-auditor` — периодический аудит целостности кита (хуки/агенты/скиллы drift, settings-секреты, orphan-страницы). Дизайн через workflow (kit-агенты fable-5) | agent-файл + smoke |
| T4 | MERGE-ANALYST | Новый агент `merge-analyst` — pre-merge анализ диффа (риск, затронутые контуры, gaps). Дизайн через workflow | agent-файл + smoke |
| T5 | RELEASE-MANAGER | Новый агент `release-manager` — ship-оркестрация (манифест, тег, changelog, sprint-page). Дизайн через workflow | agent-файл + smoke |
| T6 | SMOKE | Смоук-тест каждого нового агента (dispatch → sane output) + kit-inventory обновление счётчиков (15→18 агентов) | 3 smoke pass; каноны обновлены |
| T7 | — | Подключение (kit-зеркало), component/index, review, ship | selfcheck OK; drift clean |

## Метод (директива оператора)
Дизайн новых агентов + ревью pin-policy — через **Workflow с kit-агентами (fable-5)**: architecture-reviewer проектирует спеки (tools/triggers/model), затем автор-инлайн. Максимум fable-5, минимум основного лупа (opus 4.8).

## Порядок фаз
1 orient (done) → 2 skip → 3 план → 4 T1-T7 → 5 verify → 6 review (arch+security) → 7 sync → 8 ship alpha.63 → 9 close → S64.

## Границы
- Новые агенты — kit-maintenance назначение (не трогают src/ денежного ядра).
- Смоук = dispatch + вменяемый вывод, не полный E2E.
