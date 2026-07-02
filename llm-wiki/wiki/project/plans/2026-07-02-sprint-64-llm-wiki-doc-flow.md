---
title: Sprint 64 — LLM-Wiki Audit & Doc-Flow (план)
type: plan
sprint: 64
created: 2026-07-02
status: active
---

# S64 — LLM-Wiki Audit & Doc-Flow (mega-run 8, вставка перед плагинами)

**Цель:** (1) проверить и апгрейдить `llm-wiki/` против паттерна knowledge-base + нашей цели; (2) внедрить BINDING-правило потока документации: техдоки llm-wiki (RU) → код → пользовательские `docs/` (RU); (3) усилить session-restore от техдоков. src/ денежного ядра не трогаем.

## Метод (директива оператора)
Аудит + дизайн правила — через **Workflow, kit-агенты fable-5** (kit-auditor + architecture-reviewer + doc-reviewer-depth). Основной луп минимизируем.

## Задачи

| T | Что | Acceptance |
|---|---|---|
| T1 | kit-auditor: полный аудит `llm-wiki/wiki/**` — orphans, битые `[[ссылки]]`, актуальность index.md/log.md, **RU-язык всех страниц** (EN → инкрементальный перевод), рассинхрон счётчиков | severity-список; чинибельное закрыто в спринте |
| T2 | Правило **doc-first** в места кита (не дублировать): `CLAUDE.md` (repo+global) + `development-workflow.md` + `sprint-flow-ru.md` — Фаза 3 обязана создать/обновить техстраницу llm-wiki (RU) ДО кода; Фаза 8/9 — обновить пользовательские `docs/` | правило в 3 местах, ссылки не дублируют текст |
| T3 | Мягкий якорь: WARN если спринт тронул `src/**`/`kit/**` но не обновил `docs/**` в том же прогоне (расширение docs-staleness, НЕ новый хук; docs/=WARN per оператор) | red: src без docs → WARN; green: docs тронуты / [docs-ignore] |
| T4 | sprint-orient читает техдоки llm-wiki первоисточником: добавить mental-map + components/README к priming (сейчас только SPRINT_STATE + log) | skill обновлён |
| T5 | Апгрейд из idea-документа (только применимое, YAGNI): периодический lint = kit-auditor прогон; index/log дисциплина зафиксирована; Dataview-frontmatter — только если выгодно | ADR/заметка о принятом/отклонённом |
| T6 | Пользовательская docs/ страница про сам процесс (doc-first) — как первый пример нового правила (dogfood) | docs/ страница создана |
| T7 | Verify + Review + Sync + Ship alpha.64 + Close | manifest 7/7; review Blockers=0 |

## Границы
- RU-язык: llm-wiki + docs/ + sprint-страницы = русский (валидация оператором). Код/идентификаторы/inter-agent = English.
- docs/ гейт = WARN (не блок) — решение оператора.
- Не тащить лишнее из idea-документа (qmd MCP уже есть как wiki-sa; Marp/image-handling — не нужно).
