---
title: Sprint 60 — Docs-Sync Gate + закрытие S56 (kit-maintenance)
type: plan
sprint: 60
updated: 2026-07-02
branch: feature/sprint-60-docs-sync-gate
scope: docs/ + хуки; src/ НЕ трогаем
source: KIT-MASTER-PLAN (KIT-004/016/019), задача №3 оператора (docs самообновляются)
---

# План S60 — «Docs-Sync Gate»

Прямой ответ на задачу №3 оператора: любая правка src/kit → docs/ обновляется. Клонирует доказанную механику (adr-agent-sync + wiki-broken-link), переиспользует S56-агентов.

## Trace map

| T | KIT | Что | Proof |
|---|---|---|---|
| T0 | KIT-019 | Мердж корпуса S56 (128 стр docs) с chore-ветки → закрытие S56 (docs-спринт без тега, контент едет с alpha.60) | 159 md-файлов в docs/ на ветке; 0 конфликтов |
| T3 | KIT-004 | `docs_manifest.py` — обратный индекс source_files→pages (кэш docs/manifest.json) | 140 источников/328 привязок |
| T1 | KIT-004 | `docs-staleness-check.sh` — src/kit изменён, привязанная страница нет → блок; `[docs-ignore]` escape; quotepath-safe | red/green песочница |
| T2 | KIT-016 | `docs-broken-link-check.sh` — битые навигационные wiki-ссылки каноничного корпуса (00-10) → блок; scanner игнорит инлайн-код-примеры | red/green |
| T5 | P2-DOCLINKS | Починка 71 битой ссылки корпуса через doc-linker workflow (4 агента параллельно) | канон 71→0 |
| T4 | — | Скилл `docs-update` (инкрементальный конвейер по затронутым страницам) + правило Docs-Sync Gate в CLAUDE.md + Фаза 7 = wiki+docs | скилл зарегистрирован |
| T6 | — | Подключение хуков (settings PreToolUse), kit-зеркало, kit-inventory, component-страницы, sprint-page | selfcheck OK; drift clean |

## Границы
- Не-каноничные файлы docs/ (старый монолит KIT.md, `_навигация/` review-артефакты, superpowers/) — вне gate-скана (не пользовательская навигация). Каноника = docs/0X-*/, docs/10-*.
- `Без названия.md` (чужой) вынесен из docs/ → оператору.
- manifest.json — кэш; источник истины = frontmatter source_files.

## Фазы
1 done → 2 skip → 3 этот файл → 4 T0-T6 (per-task коммиты) → 5 red/green хуков + канон-скан 0 + manifest --check → 6 architecture + security → 7 wiki + CLAUDE.md правило → 8 ship alpha.60 → 9 close → S61.

## Ревью-условия (закрыты в спринте)

**architecture APPROVE_WITH_CONDITIONS:**
- HIGH-1: `[docs-ignore]` был range-wide → теперь ПОФАЙЛОВО (маркер в коммите, где источник последний раз менялся). Re-test: kelly (свой коммит без ignore) блокирует, fsm (ignore в своём коммите) освобождён.
- HIGH-2: manifest = кэш без принуждения → хук строит СВЕЖИЙ индекс из frontmatter во временный файл перед доверием (tracked manifest.json не мутируется). Re-test: новая привязка видна при устаревшем закоммиченном manifest. + hooks-selfcheck WARN на дрейф.
- MEDIUM 3/4/5, LOW 6 → бэклог (malformed-frontmatter WARN; coverage-gap 43% src+весь kit без bindings; money_core prose-only; heredoc→external .py) — [[UNIFIED-BACKLOG-S57]] дополнен.

**security APPROVE — ship-safe:** полный секрет-скан 128 стр + история chore = 0 полных токенов; probely-страница только `ghp_LkYj…`; хуки без инъекций. LOW-1 (manifest fail-open) + LOW-4 (.obsidian/.DS_Store) закрыты в спринте.

**Бонус:** review-gate matcher fix (git merge-base/tree/file исключены) — вылезло при мердже корпуса, поправлено в 434b143.
