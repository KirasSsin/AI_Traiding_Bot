---
title: Sprint 62 — Manifest & Telemetry (план)
type: plan
sprint: 62
created: 2026-07-02
status: active
---

# S62 — Manifest & Telemetry (mega-run 6/8)

**Цель:** «скилл выстрелил» и «гейт сработал» из надежды → проверяемый артефакт. Плюс закрыть принятые границы S59/S61 (tamper-evidence) и token-экономию (cascade, budget, tuning).

## Задачи

| T | ID | Что | Acceptance |
|---|---|---|---|
| T1 | P1-MANIFEST | Skill-firing manifest в `sprint-finish` Фаза 8: проверка наличия per-phase артефактов (plan-файл, per-task коммиты ≈ строкам таблицы, Phase-5 вывод в sprint-NN, review-sNN.md, sync-diff, sprint-NN + тег). Печатает 7/7, расхождение = STOP | манифест печатается; отсутствие артефакта → нон-зеро |
| T2 | KIT-TAMPER | Tamper-evidence review-артефакта (S59/S61 остаток): review-gate проверяет что `review-sNN.md` закоммичен В ДИАПАЗОНЕ мерджа (`git log main..ref -- reviews/`) + схема вердикта (`Blockers: 0` + ≥1 reviewer-строка). Same-session forgery без коммита-в-range → блок | red: review вне range → блок; green: в range + схема → пропуск |
| T3 | P1-CASCADE | Хук `cascade-read-check.sh` (PreToolUse Bash): `cat`/`head`/`tail`-без-limit ИЛИ `Read` banned-from-full-read файла (00-All.md, планы, log.md) → WARN с напоминанием offset/grep. fail-OPEN | red: `cat log.md` → WARN; green: `cat` малого → тихо |
| T4 | P1-TUNING | ADR `0074-runtime-tuning`: обоснование `CLAUDE_AUTOCOMPACT_PCT=50` + `MAX_THINKING=10000` + протокол A/B (суммарные токены/спринт 50 vs 65). Решение по цифрам, не интуиции | ADR с методикой A/B + текущим статусом «измерить» |
| T5 | KIT-022/025 | KIT-022: malformed-frontmatter WARN в docs_manifest (не падать молча). KIT-025: вынести оставшиеся heredoc-python из хуков в `lib/*.py` (P1-BASHN) — аудит + вынос | grep heredoc-python в хуках = 0 (или задокументировано почему остаётся) |
| T6 | — | Подключение (хуки в settings + kit-зеркало), component-страницы, review, sync | selfcheck OK; kit-drift clean; regression |

## Порядок фаз
1 orient (done) → 2 skip (backlog) → 3 этот план → 4 T1-T6 TDD → 5 verify (red/green хуков + bash -n + selfcheck) → 6 review (architecture + security параллельно; 1 раунд adversarial для tamper/cascade) → 7 sync (wiki + docs если тронуты) → 8 ship alpha.62 → 9 close → S63.

## Границы
- Не трогаем src/ денежного ядра. tuning A/B — методика + ADR; фактический прогон A/B может уйти оператору (нужны 2 спринта для сравнения).
- op-detect argv-классификация — отдельный backlog [[../kit-op-detect-hardening-backlog]], НЕ в S62.
