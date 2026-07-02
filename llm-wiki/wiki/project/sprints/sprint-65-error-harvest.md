---
title: Sprint 65 — Error-Harvest & Kit Hardening: искоренение token-waste ошибок
type: summary
sprint: 65
created: 2026-07-02
updated: 2026-07-02
tag: v0.1.0-alpha.65
status: stable
---

# S65 — Error-Harvest & Kit Hardening

**TL;DR:** таксономия token-waste ошибок прогона S57-64 (9 классов) → превентивные паттерны в самые подходящие места кита с минимумом токенов и без дублирования. Дизайн через Workflow fable-5. src/ не тронут.

## Сделано

| T | Что | Proof |
|---|---|---|
| T1 | Tech-страница [[../components/error-taxonomy]] — 9 классов (сигнатура/цена/фикс). Ground truth прогона + grep 151× Unexpected token | страница (doc-first) |
| T2 | Workflow fable-5 (architecture-reviewer + kit-auditor): размещение паттернов без дублирования + проверка покрытия existing anti-waste | дизайн + coverage-verdict |
| T3 | Внедрение: новый skill `.claude/skills/workflow-authoring/SKILL.md` (parse-safe чеклист: plain JS, named schemas, no TS/backticks, registry-check); repo CLAUDE.md anti-waste +5 строк (workflow-парс, invisible-chars, op-detect false-fire, zsh quirks, git-checkout-clobber) + 1 правка (re-Read после мутирующего tool) + указатель на таксономию; message-hint «FALSE-FIRE → Edit/Grep» в phase-advance + review-gate | 38-case regression PASS; skills 9→10 |
| T4 | Carry S64: WARN-видимость 3 хуков (cascade verified печатает stderr; паттерн S61/S62) — принято; current-state→AUTO-блок kit-inventory → follow-up | — |

## Ключевые решения (fable-5 команда)
- **Не дублировать:** класс 2 (Edit-до-Read) и 6a (bare python) УЖЕ покрыты — отклонено добавление (bloat anti-pattern). Классы 4+8 и 6b+7 слиты по общей причине.
- **Op-detect false-fire (класс 5):** дёшево/безопасно = дисциплина + message-hint (матчер НЕ трогать). Отклонено сужение substring — риск-асимметрия: false-fire=токены (восстановимо) vs false-negative=разоружённый money-гейт (невосстановимо). Root fix → KIT-OD-1 (выделенный security-спринт, red/green через реальный вызов хука).
- **git-checkout-clobber:** единственный класс с ПОТЕРЕЙ РАБОТЫ (не только токенов) — отдельная строка.
- **Ирония:** класс 1 (workflow TS-parse) словлен LIVE при дизайне его же фикса (вложенные backticks в template) — добавлен под-случай.

## Ревью (Phase 6) — артефакт [[../reviews/review-s65]]

Design-workflow (architecture-reviewer + kit-auditor, оба fable-5) выполнил и дизайн, и проверку покрытия/дублирования — это и есть Phase-6 ревью. Реализация точно следует дизайну (38-case regression intact, selfcheck OK, drift clean).

## Related
[[../plans/2026-07-02-sprint-65-error-harvest]] · [[../components/error-taxonomy]] · [[kit-op-detect-hardening-backlog]] · [[../KIT-MASTER-PLAN]]
