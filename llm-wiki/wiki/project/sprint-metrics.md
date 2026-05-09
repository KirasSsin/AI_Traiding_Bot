---
title: Sprint Metrics — скорость / процент ревизий / КУ / трекинг времени
type: metrics
tags: [metrics, velocity, revision-rate, ku, sprint-tracking, kit-improvement]
created: 2026-04-27
updated: 2026-05-09
status: active
sources:
  - project/decisions/0048-sprint-32d-kit-phase-3-improvements.md
  - project/SPRINT_STATE.md
---

# Sprint Metrics

**TL;DR:** Ручное обновление в конце каждого спринта (ФАЗА 9). Отслеживает скорость (задачи/спринт), найденные баги, итерации ревью, достигнутый КУ, затраченное время.

**Протокол обновления:** расширение skill `sprint-finish` (ФАЗА 9 Close) — см. секцию "Протокол обновления" внизу.

## Таблица по спринтам

Новые спринты добавляются сверху (обратная хронология).

| Спринт | Задачи | Багов найдено | Итераций ревью | Pytest count | КУ avg | Время | КУ/час | Примечания |
|--------|-------|---------------|----------------|--------------|--------|-------|--------|------------|
| S38 | 7 | 0 | 1 | 905 | 48% | ~7h | 69 | δ Parallel Hardening — F2 pnl_pct fix + bybit-api-reviewer + Item #7 Demeter + playbook |
| S37 | 8 | 2 | 2 | 897 | 48% | ~10h | 48 | Carry-overs Hardening — security HIGH × 2 + HMAC + clock injection + DSR boundary |
| S36 | 8 | 1 | 8 | 871 | — | — | — | δ TESTNET Activation — HaltGate wire-up + B1 critical fix + DSR amendment |
| S35 | 5 | 0 | 7 | 802 | — | — | — | δ TESTNET ready + α Donchian FAIL conjoint + ζ risk refactor |
| S34 | 5 | 0 | 0 | 808 | — | — | — | Hybrid 6-th honest close v0.6 + Amendment LOCKED |
| S33 | 6 | 1 | 15 | 803 | — | — | — | Trading Restart, F BACKTEST FAIL conjoint — 5 bugs (formula + replay + mypy) |
| S32d | 5 | 0 | 0 | 773 | 41% | ~2.5h | 56 | Kit Phase 3 final — S32 series complete |
| S32c | 4 | 0 | 0 | 773 | 51% | 1.5h | 75 | Kit Phase 2 reduced — 4 skill mappings + Fetch MCP + corpus scheme docs |
| S32b | 6 | 0 | 0 | 773 | 60.5% | 3h | 120 | Kit Phase 1 — CI + pre-commit + SQLite MCP + freshness hook + dashboard-reviewer (CI 3 fix iterations) |
| S32 | 6 | 0 | 0 | 773 | 60% | 45 min | 80 | Kit Phase 0 — P0 staleness fix + 5 skill mappings + cascade smart-explore + Phase 9 consolidate-memory |
| S31 | 6 | 0 | 0 | 762 | — | — | — | Kit Revision per Best Practices (kit-overview-ru NEW + CLAUDE.md prune -25%) |
| S30 | 8 | 0 | 0 | 762 | — | — | — | Tier-2 Agents (security/test/doc) + phase-advance hook + cascade |
| S29 | 4 | 0 | 0 | 762 | — | — | — | Full Superpowers Skills Integration (7 NEW skills + Skills × Phase map) |
| S28 | 6 | 0 | 0 | 762 | — | — | — | Process enforcement (sprint-flow-check hook + Russian process docs) |
| S27 | 8 | 5 (formula) | 12 | 762 | — | — | — | Formula bug fixes — TDD 5 bugs |
| S25 | — | 0 | 0 | 740 | — | — | — | Dashboard UI sprint |
| S23 | — | — | — | 712 | — | — | — | v0.5 honest close |
| S22 | — | — | — | 712 | — | — | — | BTC 4H test (62 trades, FAIL T5) |

**Примечание:** Трекинг КУ введён с S32 (серия kit improvement). Для спринтов до S32 — КУ/время ретроспективно не измерялись.

## Тренды (скользящие 5 спринтов, S37-S38 включены)

- **Скорость:** avg 7.5 задач/спринт (S37=8, S38=7 — рабочие спринты выше S32 серии)
- **Обнаружение багов:** 1-2 бага/спринт (review-intensive рабочие спринты — норма)
- **Тренд КУ:** 48%/48% (S37+S38) — стабильный, немного ниже S32b-пика
- **Тренд времени:** ~10h/~7h (S37 тяжелее из-за security fixes + review-iterations)
- **Тренд КУ/час:** 48/69 — S38 эффективнее за счёт короче спринта и точного scope

## Определения

- **Задачи** = количество завершённых задач T1-TN в плане спринта
- **Багов найдено** = выходы фаз 5/6 ревью (severity BLOCKER/HIGH)
- **Итераций ревью** = количество dispatch'ов ревьюеров в фазе 6 (1 если с первого прохода, 2+ если blocker → fix → re-review)
- **Pytest count** = итоговое количество пройденных тестов из вывода Phase 5 verify
- **КУ avg** = среднее КУ % по всем задачам (методология ADR 0045)
- **Время** = общая длительность сессии (оценка)
- **КУ/час** = КУ avg / часы = ROI

## Протокол обновления (ФАЗА 9 Close — расширение skill `sprint-finish`)

После SPRINT_STATE → коммита between-sprints:

1. Подсчитать завершённые задачи (из таблицы Deliverables спринт-страницы)
2. Подсчитать найденные баги (из выходов фаз 5/6 или pre-existing baseline preserved = 0)
3. Подсчитать итерации ревью (количество dispatch'ов в фазе 6, включая циклы fix→re-review)
4. Прочитать pytest passed count из Bash-вывода Phase 5 verify
5. Вычислить КУ avg из спринт-страницы (по-задачная таблица)
6. Время = оценка общей длительности сессии (от первого коммита до финального тега)
7. КУ/час = КУ avg / часы
8. Добавить строку в таблицу выше (новые — сверху)
9. Обновить секцию Тренды если накопилось 5+ спринтов одной серии

## Ретроспектива S37-S38

- **Паттерн "hardening sprint":** S37 = 8 задач security+quant, S38 = 7 задач correctness+review. Оба ~48% КУ — плотнее, чем S32 kit series (60%), из-за code review iterations и reviewer findings requiring fixes.
- **bybit-api-reviewer первый вызов (S38 T3):** dormant с S30 (создан в S32d). 20 findings (0 BLOCKER, 3 HIGH), все HIGH → pre-s39-backlog. Паттерн: review-создание в kit sprint → первый вызов через 6 спринтов.
- **Test count growth:** S36=871 → S37=897 (+26) → S38=905 (+8). S37 тест-интенсивнее из-за security fixes (8 + 6 + 3 + 2 + 5 тестов по задачам T2-T6).

## Связанное

- [[decisions/0045-sprint-32-kit-phase-0-improvements]] — методология КУ
- [[decisions/0046-sprint-32b-kit-phase-1-improvements]] — CI infrastructure
- [[decisions/0047-sprint-32c-kit-phase-2-improvements]] — паттерн reduced scope
- [[decisions/0048-sprint-32d-kit-phase-3-improvements]] — введён трекинг sprint metrics
- [[architecture/tooling-inventory-ru#23-anthropic-skillsschedule-wire-к-audit_formulaspy-s32d]] — schedule wire automation
