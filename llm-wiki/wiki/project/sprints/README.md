---
title: Sprints — per-sprint delivery records
type: summary
tags: [sprints, retrospective, workflow]
created: 2026-04-22
updated: 2026-04-22
status: stable
---

# Project — Sprints

Директория фиксирует **фактически поставленное** в каждом спринте v0.1 — между pre-execution планом (`plans/`) и хронологическим логом (`log.md`).

## Назначение

- **Продолжать работу между сессиями.** Новая сессия LLM читает sprint-page и понимает контекст без перечитывания десятков файлов.
- **Выявлять drift** между планом и реализацией (отклонения фиксируются явно).
- **Переиспользовать паттерны** — если следующий спринт похож по структуре, шаблон ускоряет написание плана.
- **Track follow-ups** — что оставлено на «потом» и почему.

## Границы (что тут НЕ хранится)

- Детализованные TDD-steps → `plans/YYYY-MM-DD-sprint-N-<slug>.md`.
- Хронологические правки вики → `log.md` (append-only).
- Архитектурные решения → `decisions/NNNN-<slug>.md` (ADR).
- Описания компонентов → `components/<name>.md`.

Sprint-page ссылается на всё это, но не дублирует.

## Именование

- `sprint-NN-<kebab-slug>.md`, где NN — двузначный номер, slug — короткое имя спринта.
- Синхронизирован с тегом: Sprint 1 → `v0.1.0-alpha.1`, Sprint 2 → `v0.1.0-alpha.2`, и т.д.

## Шаблон

````markdown
---
title: Sprint N — <Name>
type: summary
tags: [sprint, sprint-N, <domain-tags>]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [project/plans/YYYY-MM-DD-sprint-N-<slug>.md]
status: done | in-progress
---

# Sprint N — <Name>

**Dates:** YYYY-MM-DD → YYYY-MM-DD
**Plan:** [[../plans/YYYY-MM-DD-sprint-N-<slug>]]
**Tag:** `v0.1.0-alpha.N`
**Merge PR:** #NNN
**Commit range:** `<base>..<head>`

## Goal

Одна фраза — source of truth: `migration-plan.md §SN`.

## Scope delivered

### Code
Список путей с однострочным описанием ответственности. Без дублирования содержимого component-страниц.

### Wiki
Созданные / изменённые wiki-страницы со ссылкой.

### Removed / migrated
Что убрано и куда перенесено (если есть).

## Decisions & deviations

Нумерованный список отклонений от плана + их обоснование. Каждый пункт — одна строка факт + одна причина.

- **Deviation:** ... — **Rationale:** ...
- **New ADR:** 00NN — краткий предмет.

## Verification

- `make check`: результат (N passed, ruff/mypy status).
- Test counts: unit / integration.
- Manual checks (если были).

## Impact on downstream

Как этот sprint раз-блокирует / ограничивает следующие спринты. Конкретно: какие артефакты становятся зависимостями.

## Follow-ups carried forward

Chevron-style checklist того, что НЕ сделано и идёт дальше:

- [ ] Title — rationale / scope / target sprint.

## Related

- Plan: `[[../plans/...]]`
- ADRs: `[[../decisions/00NN-...]]`
- Components: `[[../components/...]]`
- Concepts: `[[../../trading/concepts/...]]` (если релевантно)
````

## Процесс обновления

1. **В конце спринта:** создать `sprint-NN-<slug>.md`, заполнить все секции.
2. **Обновить `index.md`:** добавить ссылку в раздел `Project — Sprints`.
3. **Обновить `log.md`:** append-entry с `## [YYYY-MM-DD] sprint | N completed`.
4. **Если переносятся follow-ups:** добавить их в `sprint-(N+1).md` секции `Dependencies from previous sprints` при её создании.

## Related

- [[../architecture/migration-plan]] — source of truth для sprint boundaries.
- [[../architecture/development-workflow]] — Superpowers pipeline.
- [[../../../CLAUDE|llm-wiki/CLAUDE]] — wiki-maintenance правила.
