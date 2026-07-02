---
title: SPRINT_STATE v2 — дизайн на PRE-PLAN гейт (S61)
type: design
updated: 2026-07-02
status: pre-plan
---

# SPRINT_STATE v2 — дизайн (PRE-PLAN, architecture-reviewer BINDING)

## Проблема (из бэклога + A2)
KIT-008: монолит SPRINT_STATE.md — 4 фазы ответственности (1/5/8/9), риск раздувания (инцидент S46: 86КБ заблокировал старт), потеря контекста при обрыве (A2: contextExceededCount=7). Усиливает auto-resume (S58 опирается на next_action) — но текущий state не отказоустойчив (обрыв посреди записи = повреждение).

## Текущее состояние (факты)
- SPRINT_STATE.md = 3.3КБ (лимит 6КБ соблюдается весь прогон).
- Читатели: хуки phase-advance / review-gate / sprint-flow-check / sprint-state-freshness / pertask-state-warn (grep строки `phase:`, `sprint:`, `| 5 Verify |`); 10 агентов (Sprint context priming — абсолютный путь SPRINT_STATE.md); 5 скиллов (sprint-orient/finish/wiki-update).
- **Blast radius полной миграции: ~20 файлов.**

## ДВА варианта — выбор за PRE-PLAN

### Вариант A — полное разделение (исходный план [GLM/MINIMAX/DEEPSEEK])
`state/CURRENT.md` ≤2КБ (спринт/фаза/ветка/тег/next_action/таблица задач/last_task_sha) + `state/BACKLOG.md` ≤4КБ (carry/blocked_by/risk_level) + `state/.backup/`. Старый SPRINT_STATE.md → тонкий redirect-стаб.
- **Плюс:** чистое разделение ответственности, жёсткие под-лимиты.
- **Минус:** миграция ~20 читателей (10 агентов праймят путь SPRINT_STATE.md; хуки перепарсить). Высокий риск сломать агентов/хуки одним спринтом. phase-advance формат `| 5 Verify |` мигрировать синхронно.

### Вариант B — инкрементальное упрочнение монолита (минимальный blast radius)
SPRINT_STATE.md остаётся единым (читатели не трогаются), но добавляется:
- `sprint-state-integrity-check.sh` (SessionStart + PreToolUse push): валидный YAML frontmatter, `phase ∈ {1..9, between-sprints, autoresearch}`, размер ≤6КБ; corrupted → авто-восстановление из `.backup/` + запись в log.
- Авто-бэкап `llm-wiki/wiki/project/state/.backup/SPRINT_STATE.<ts>.md` при каждой записи (через хук на git commit, трогающий SPRINT_STATE, ИЛИ шаг в sprint-orient/finish).
- Поле `last_task_sha:` в frontmatter (точка восстановления для auto-resume).
- **Плюс:** нулевой риск для 20 читателей; отказоустойчивость + last_task_sha — то, что реально усиливает auto-resume. Разделение файла — не самоцель (3.3КБ ≪ 6КБ, раздувание уже под контролем правилом).
- **Минус:** не решает «4 фазы ответственности» концептуально (но практически монолит 3.3КБ управляем).

## Рекомендация автора (не BINDING — решает reviewer)
Склоняюсь к **B**: реальная боль (A2) — потеря контекста при обрыве, а не размер (6КБ соблюдается). B даёт отказоустойчивость + last_task_sha с нулевым blast radius. Разделение (A) — рефакторинг ради чистоты с риском сломать 10 агентов, при том что монолит сейчас не раздут. A можно отложить в DEFER (ADR-черновик «когда пересматривать» — уже в KIT-D01).

## Вопрос к PRE-PLAN
1. A или B? (или гибрид: B сейчас + A как DEFER-ADR).
2. Если B: авто-бэкап через новый хук на `git commit` (SPRINT_STATE в staged → cp в .backup) ИЛИ через шаг в скиллах? Хук надёжнее (принуждение), но +1 PreToolUse.
3. integrity-hook fail-CLOSED (как hooks-selfcheck) или fail-OPEN с авто-восстановлением?

---

## PRE-PLAN ВЕРДИКТ (architecture-reviewer, BINDING, 2026-07-02): Вариант B

Обоснование: боль из A2 (contextExceededCount, инцидент 86КБ) помечена ЗАКРЫТОЙ в самом аудите (закрыта правилом ≤6КБ; файл 3365Б держится 5 спринтов). A = синхронная миграция 17 читателей (9 агентов + 5 хуков + 3 скилла; phase-advance/review-gate хардкодят путь и гейтят merge) в живом прогоне — рефакторинг ради чистоты, не фикс. A → DEFER-ADR (отдельный от KIT-D01).

Три sub-решения (BINDING):
1. **Авто-бэкап = хук** на `git commit` со staged SPRINT_STATE (не скилл — скилл 0% принуждения).
2. **integrity-check = fail-OPEN с авто-восстановлением** (НЕ fail-CLOSED — второй fail-CLOSED дедлочил бы unattended auto-resume S58).
3. **last_task_sha** = валидное поле; уточнить семантику (state-commit vs code-commit) — записываю code-commit HEAD (что уже написано, для восстановления) + переиспользую S58 progress_stamp.
