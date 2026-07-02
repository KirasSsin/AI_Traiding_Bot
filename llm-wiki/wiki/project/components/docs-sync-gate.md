---
title: Docs-Sync Gate — docs/ самообновляется с кодом
type: component
tags: [kit, hook, enforcement, docs, docs-as-code]
created: 2026-07-02
updated: 2026-07-02
sources: [kit/hooks/docs-staleness-check.sh, kit/hooks/docs-broken-link-check.sh, kit/hooks/lib/docs_manifest.py, .claude/skills/docs-update/SKILL.md]
status: stable
---

# Docs-Sync Gate (S60) — задача №3 оператора закрыта

**TL;DR:** любая правка `src/**`/`kit/**` обязана в том же пуше обновить привязанные страницы `docs/`; битые wiki-ссылки каноничного корпуса блокируют push. Симметрия к wiki-контуру (wiki-update + wiki-broken-link), но для пользовательской документации.

## Компоненты

| Файл | Роль |
|---|---|
| `docs-staleness-check.sh` (KIT-004) | git push: источник изменён, привязанная страница нет → **WARN** (S64: docs/=WARN, решение оператора; пуш не блокируется). Escape `[docs-ignore]` для тривиального. quotepath-safe (кириллица) |
| `docs-broken-link-check.sh` (KIT-016) | git push с тронутыми docs/: битые навигационные wiki-ссылки каноники (00-10) → БЛОК |
| `docs_manifest.py` | обратный индекс `source_files:` frontmatter → `docs/manifest.json` (кэш для staleness, быстро без YAML-парсинга в bash). 140 источников/328 привязок |
| `docs_broken_link_scan.py` | скан wiki-ссылок: пути/alias/якоря; игнор код-блоков И инлайн-код-примеров |
| скилл `docs-update` | инкрементальный конвейер doc-writer→depth→(money: +домен)→linker по ТОЛЬКО затронутым страницам |

## Привязка (источник истины)
Frontmatter `source_files:` каждой страницы docs/ = «эта страница документирует эти файлы». Обратный индекс строится из него; manifest.json — кэш (регенерация `docs_manifest.py docs`). Покрытие opt-in: страница без `source_files` не под staleness-гейтом.

## Границы (S60 review)
- Каноника = `docs/0X-*/`, `docs/10-*`. Вне gate: старый монолит `KIT.md`, `_навигация/` (review-артефакты), `superpowers/`.
- manifest — кэш, не истина; дрейф ловится `docs_manifest.py --check`.

## Проверено (S60)
staleness red/green (src без страницы → блок; [docs-ignore]/страница-тоже → пропуск); broken-link red/green; scanner: инлайн-код-пример не ловится, реальная битая ловится; канон 71→0 после doc-linker workflow.

## Related
- [[review-gate-hook]] (парный money-гейт Фазы 6) · [[adr-agent-sync-hook]] (та же mtime→content эволюция) · [[../architecture/sprint-flow-ru]] Фаза 7
