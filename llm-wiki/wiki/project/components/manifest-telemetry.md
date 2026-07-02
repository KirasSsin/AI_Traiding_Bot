---
title: Manifest & Telemetry — skill-firing manifest, cascade-WARN, tamper-evidence (S62)
type: component
tags: [kit, hook, telemetry, verification, tamper-evidence]
created: 2026-07-02
updated: 2026-07-02
sources: [kit/skill-manifest.sh, kit/hooks/cascade-read-check.sh, kit/hooks/lib/cascade_check.py, kit/hooks/review-gate.sh, kit/hooks/lib/docs_manifest.py]
status: stable
---

# S62 — Manifest & Telemetry

**TL;DR:** «скилл выстрелил» и «гейт сработал» из надежды → проверяемый артефакт. Плюс закрыт остаток S59/S61 (tamper-evidence) и часть token-экономии (cascade).

## Компоненты

| Что | Событие | Роль |
|---|---|---|
| `skill-manifest.sh` (P1-MANIFEST) | sprint-finish Фаза 8 (ручной вызов) | проверяет наблюдаемые артефакты 7 фаз (plan / коммиты спринта / Phase-5 done / review-sNN Blockers:0+ревьюер / components/ тронуты / sprint-NN / тег); `exit 1` = STOP до тега |
| `cascade-read-check.sh` + `lib/cascade_check.py` (P1-CASCADE) | PreToolUse Bash+Read | WARN (fail-OPEN) на полное чтение banned/>50КБ (Read-без-limit, `cat/less`); тихо при limit/пайпе/малом. Механизирует единственную автоматизируемую часть каскада wiki→mem→grep→read (ADR 0043) |
| review-gate tamper-evidence (KIT-TAMPER) | PreToolUse merge | review-sNN.md должен быть ЗАКОММИЧЕН в диапазоне `main..merge_ref` + иметь строку ревьюера — не просто лежать в рабочем дереве (same-session forgery). Закрывает принятую границу S59/S61 |
| `docs_manifest.py` SRC_RE (KIT-022) | docs-staleness / manifest regen | `[ \t]*` вместо `\s*` — block-list `source_files` больше не хватается как мусор `- a.py`; нераспознанный `source_files` → WARN, не молчание |

## Философия
`verification-before-completion` применённая к самому киту: ненаблюдаемое «скилл загрузился» → наблюдаемое «артефакт скилла появился» (`test -f`/`grep`). Дёшево, честно, ловит пропуск фазы.

## Границы / остаток
- Манифест — эвристики (Phase-4 = коммиты с меткой `(sN)`, Phase-7 = components/ тронуты). Ложные STOP/OK возможны на нестандартном профиле; STOP → добери артефакт вручную.
- tamper-evidence НЕ закрывает op-detect-argv остаток (`git -c alias merge` минует детект ДО tamper) — [[../kit-op-detect-hardening-backlog]].
- cascade banned-list дублирует CLAUDE.md §9 (риск дрейфа) → авто-генерация списка = follow-up.
- KIT-025 (heredoc→external .py): аудит 14 хуков — 13 используют безопасный single-line `python3 -c` (JSON-извлечение); docs-staleness имеет 2 python-heredoc (22 стр) БЕЗ backtick'ов внутри → нет P1-BASHN break-риска; вынос = low-value hygiene, не сделан.

## Related
- [[review-gate-hook]] (tamper-evidence расширяет KIT-003) · [[docs-sync-gate]] (KIT-022 в manifest) · [[../decisions/0074-runtime-tuning]] (tuning ADR) · [[state-integrity-hook]]
