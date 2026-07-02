---
name: docs-update
description: После изменения src/ или kit/ синхронизирует ТОЛЬКО затронутые страницы docs/ (пользовательская документация) через конвейер doc-writer→doc-reviewer-depth→doc-linker. Use proactively в Фазе 7 (Sync) параллельно wiki-update, ИЛИ когда docs-staleness-check.sh выдал WARN (S64: docs/=WARN). Инкрементально (не полный ребилд) — экономия токенов. S60, симметрия к wiki-update.
---

# docs-update — инкрементальная синхронизация docs/ с кодом

Парный к `wiki-update` (тот ведёт `llm-wiki/` для ИИ; этот — `docs/` для человека). Обновляет **только затронутые** страницы, не весь корпус.

## Когда

- Фаза 7 (Sync) любого спринта, тронувшего `src/**` или `kit/**` — параллельно `wiki-update`.
- Реактивно: `docs-staleness-check.sh` выдал WARN (источник изменён, страница отстала; S64 docs/=WARN, не блок).
- НЕ запускать при `[docs-ignore]`-правках (формат/комменты/type hints).

## Шаги

**Шаг 1 — что изменилось:**
```bash
git diff --name-only <base>..HEAD -- 'src/**' 'kit/**'
```

**Шаг 2 — какие страницы docs/ затронуты (обратный индекс, дёшево):**
```bash
# manifest.json = source_files: frontmatter всех страниц (кэш)
python3 kit/hooks/lib/docs_manifest.py docs        # регенерировать при дрейфе
# для каждого изменённого источника — привязанные страницы:
python3 -c "import json; m=json.load(open('docs/manifest.json')); [print(p) for s in ['<src-file>'] for p in m.get(s,[])]"
```
Только эти страницы идут в конвейер. Ничего не затронуто → docs-update завершён.

**Шаг 3 — конвейер (S56, по затронутым страницам):**
1. `doc-writer` — переписывает страницу из актуального кода (каждый факт → `file:line`).
2. `doc-reviewer-depth` (fable-5) — сверяет КАЖДОЕ число/формулу против `src/` (Bash-пересчёт).
3. Для money-core страниц (`money_core: true` во frontmatter) — доп. доменный ревьюер (`trading-logic-reviewer`/`quant-stats-reviewer`/…).
4. `doc-linker` — чинит/строит `[[ссылки]]` затронутых страниц.

Параллелить независимые страницы (`superpowers:dispatching-parallel-agents`). Money-core → строго через доменного ревьюера, не пропускать.

**Шаг 4 — локальная проверка до пуша:**
```bash
python3 kit/hooks/lib/docs_manifest.py docs                        # обновить кэш
cd docs && python3 ~/.claude/hooks/lib/docs_broken_link_scan.py . | grep -E '^(0[0-9]|10)-'   # 0 битых в каноне
```

## HARD-GATE (в Фазе 7)

Перед Ship: `docs-broken-link-check.sh` clean (битые ссылки = БЛОК). `docs-staleness-check.sh` = WARN (S64: docs/=WARN — реши осознанно, не блок).

## Анти-паттерны
- ❌ Полный ребилд всех 128 страниц вместо затронутых (токен-разбазаривание).
- ❌ «Обновлю docs потом» — staleness-хук не пустит push.
- ❌ Пропуск доменного ревьюера на money_core странице.
- ❌ Секреты в docs/ (страницы под git).

Связь: [[wiki/project/components/review-gate-hook]] (парный money-гейт), `docs-staleness-check.sh`, `docs-broken-link-check.sh`, `kit/hooks/lib/docs_manifest.py`.
