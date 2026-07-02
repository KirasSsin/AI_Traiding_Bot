---
title: Sprint 61 — SPRINT_STATE v2 (Вариант B: упрочнение монолита, kit-maintenance)
type: plan
sprint: 61
updated: 2026-07-02
branch: feature/sprint-61-sprint-state-v2
scope: state-инфраструктура (хуки, frontmatter); src/ НЕ трогаем
source: KIT-008 + PRE-PLAN вердикт architecture-reviewer (Вариант B, BINDING)
---

# План S61 — «SPRINT_STATE v2» (Вариант B)

Фаза 2 = PRE-PLAN гейт (done, вердикт B). Blast radius 0: монолит SPRINT_STATE.md остаётся, читатели не трогаются. Добавляем отказоустойчивость + last_task_sha (усиливает auto-resume S58).

## Trace map

| T | Что | Proof |
|---|---|---|
| T1 | `state-backup.sh` (PreToolUse Bash): `git commit` со staged `SPRINT_STATE.md` → cp в `llm-wiki/wiki/project/state/.backup/SPRINT_STATE.<ts>.md` ПЕРЕД коммитом; ротация (последние 20). fail-OPEN | red/green: commit со state → бэкап появился; без state → нет |
| T2 | `state-integrity-check.sh` (SessionStart + PreToolUse push): валидный YAML frontmatter (sprint/phase/branch), phase∈{1..9,between-sprints,autoresearch}, размер ≤6КБ; corrupted → авто-восстановление из последнего .backup + log. **fail-OPEN** (не дедлочить auto-resume) | red: битый YAML → восстановлен из бэкапа, лог; green: валидный → тишина; oversize → WARN |
| T3 | Поле `last_task_sha:` в frontmatter SPRINT_STATE (= HEAD code-commit последней задачи; для точки восстановления auto-resume). Обновление — часть per-task протокола; sprint-orient читает, auto-resume poller использует | поле присутствует; sprint-orient его показывает; poller читает |
| T4 | DEFER-ADR «SPRINT_STATE split (Вариант A)» — когда пересматривать (файл >5КБ стабильно ИЛИ >3 фаз ответственности болят). Отдельный от KIT-D01 | ADR-файл создан, в index |
| T5 | Подключение (2 хука), kit-зеркало, component-страница, kit-inventory, sprint-page. auto-resume poller: читать last_task_sha в resume-контекст | selfcheck; drift clean; счётчики |

## Совместимость
- Читатели SPRINT_STATE (17) НЕ трогаются — формат монолита сохранён, только +поле last_task_sha во frontmatter (агенты/хуки его игнорят, не ломаются).
- phase-advance строка `| 5 Verify |` — без изменений.
- Новый `state/` каталог только для `.backup/` (не путать с Вариантом A `state/CURRENT.md`).

## Фазы
1 done → 2 done (PRE-PLAN B) → 3 этот файл → 4 T1-T5 → 5 red/green хуков (битый YAML → восстановление; бэкап-ротация) + bash -n → 6 architecture + security (unattended восстановление = зона) → 7 wiki → 8 ship alpha.61 → 9 close → S62.
