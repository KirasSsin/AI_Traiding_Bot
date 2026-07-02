---
title: "0073. SPRINT_STATE v2 — Вариант B (упрочнение), split отложен"
type: decision
status: accepted
created: 2026-07-02
updated: 2026-07-02
---

# 0073. SPRINT_STATE v2 — Вариант B; полное разделение (A) отложено

**Status:** accepted (S61)
**Date:** 2026-07-02

## Контекст

KIT-008: монолит SPRINT_STATE.md несёт 4 фазы ответственности (1/5/8/9), исторически раздувался (инцидент S46: 86КБ заблокировал старт), терялся при обрыве сессии (A2: contextExceededCount=7). Исследования [GLM][MINIMAX][DEEPSEEK] предлагали разделение на state/CURRENT.md + BACKLOG.md (Вариант A).

## Решение

**Вариант B** (упрочнение монолита), по BINDING PRE-PLAN вердикту architecture-reviewer:
- `state-backup.sh` — авто-бэкап перед коммитом (staged SPRINT_STATE → .backup/, ротация 20).
- `state-integrity-check.sh` — валидация YAML/phase/размер, **fail-OPEN с авто-восстановлением** из .backup.
- `last_task_sha:` во frontmatter — точка восстановления auto-resume.

**Вариант A (полное разделение) — ОТЛОЖЕН.** Отдельно от [[0072-kit-token-economy-tools-integration]] и KIT-D01 (тот про БД/LangGraph-state).

## Обоснование отсрочки A

- Боль, которой A мотивирован, ЗАКРЫТА: правило ≤6КБ держит файл на 3.4КБ 5+ спринтов подряд (A2 помечает инцидент 86КБ «закрыто»).
- Blast radius A: синхронная миграция 17 читателей (9 агентов хардкодят путь SPRINT_STATE.md в Sprint-priming; phase-advance/review-gate парсят строки таблицы и гейтят merge денежного ядра) — в живом автономном прогоне.
- B решает реальную боль (crash-durability + точка восстановления) с blast radius 0.

## Когда пересмотреть A (триггеры)

1. SPRINT_STATE.md стабильно > 5КБ несмотря на дисциплину ≤6КБ (частые oversize-WARN от integrity-хука).
2. Появилась ≥3-я независимая ось записи в state, которую монолит смешивает (реальная боль разделения ответственности, а не эстетика). *(Учёт: architecture-reviewer S61 отметил, что `last_task_sha` — 4-я ось git-recovery-bookkeeping; поле аддитивно, single-writer, новых путей мутации не даёт, но при следующей оценке триггера №2 его считать.)*
3. Миграция читателей удешевела (напр. агенты стали читать state через общий скилл-обёртку, а не хардкод пути).

## Последствия

- +2 PreToolUse-хука (state-backup, state-integrity), всего 13.
- Читатели (17) не тронуты — нулевой риск регрессии.
- auto-resume (S58) усилен last_task_sha.
- A остаётся живой опцией с явными триггерами пересмотра.
