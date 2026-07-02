---
title: Sprint 66 — Plugins & Best Practices (план)
type: plan
sprint: 66
created: 2026-07-02
status: active
---

# S66 — Plugins & Best Practices (финал mega-run)

**Цель:** ресерч популярных Claude Code плагинов по звёздам/инсталлам, валидация совместимости с НАШИМ зрелым китом, **внедрить ≤2** лучших (директива v2) с токен-метрикой. src/ не трогаем.

## Задачи
- T1: Web-ресерч (WebSearch) — топ по инсталлам/звёздам (Anthropic directory + awesome-lists).
- T2: Фильтр по fit — отклонить дубли (superpowers уже есть; reviewers/sprint-finish покрывают).
- T3: Внедрить ≤2 безусловно-ценных без дубля (Context7 MCP) в `.mcp.json` (reversible).
- T4: Спорные (Frontend Design) → OQ оператору (OQ-2: оператор выбирает).
- T5-7: Отчёт [[../plugins-research]] + Verify + Ship alpha.66 + Close.

## Метод
Ресерч — WebSearch (built-in). Токен-метрика — ожидаемая экономия на итерациях API-ошибок. Тех-страница = [[../plugins-research]] (doc-first).

## Границы
- «≤2» = up to 2, не ровно 2 (YAGNI: не ставить дубли ради числа).
- Установка MCP = reversible (`.mcp.json` project-scoped).
