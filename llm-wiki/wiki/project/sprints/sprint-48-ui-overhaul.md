---
title: "Sprint 48 — UI Overhaul (9 жалоб + Bybit balance + Glossary вкладка)"
type: sprint
tags: [sprint-48, ui-overhaul, glossary, bybit-balance, dashboard]
created: 2026-05-11
updated: 2026-05-11
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
  - llm-wiki/wiki/project/decisions/0017-review-agent-harness.md
  - llm-wiki/wiki/project/plans/2026-05-11-sprint-48-ui-overhaul.md
  - llm-wiki/wiki/project/pre-s48-backlog.md
---

# Sprint 48 — UI Overhaul (9 жалоб + Bybit balance + Glossary вкладка)

## Обзор

UI Overhaul: 9 операторских жалоб на интерфейс дашборда + реальный Bybit balance вместо фиксированных $10000 + новая вкладка Glossary с RU расшифровкой всех аббревиатур и метрик. Всего 24 задачи в 6 блоках (Bucket 0: рефакторинг subdirs / Bucket A: backend / Bucket B: frontend bugs / Bucket C: Bybit balance / Bucket D: Glossary tab / Bucket E: RU язык + wiki sync). Архитектурный ревьюер и frontend-developer провели pre-plan validation (5 APPROVE_WITH_CONDITIONS — C1-C5 BINDING).

## План + ссылки на ADR

- Plan: [[../plans/2026-05-11-sprint-48-ui-overhaul]]
- Backlog (PHASE 2): [[../pre-s48-backlog]]
- ADR 0014 (acceptance gates): [[../decisions/0014-walk-forward-train2000-test500]]
- ADR 0017 (review-agent harness): [[../decisions/0017-review-agent-harness]]
- Предыдущий спринт: [[sprint-47-tech-debt-carryovers]]

## Доставленная функциональность

### Frontend (компоненты)

- **Component subdirs refactor (T1, Bucket 0 / архитектор C5 BINDING):** `src/dashboard_react/src/components/` реструктуризирован в 6 поддиректорий: `tabs/`, `charts/`, `forms/`, `metrics/`, `shared/`, `glossary/`. Import paths обновлены во всех ~22 компонентах. Устраняет плоскую структуру ещё до роста.
- **EquityChart 3-line tooltip + initialBalance (T8, Bug A):** tooltip при наведении показывает 3 строки — дата / Equity% / Balance USDT (вычисляется из `initialBalance` prop). Prop `initialBalance` добавлен в `EquityChart` и `EquityChartWrapper`.
- **MetricsTable секционный разделитель (T10, Bug D):** визуальный разделитель между GATE-BLOCKING (T1-T6) и INFORMATIONAL метриками. Informational-строки отображаются с `opacity: 0.55` + иконкой ℹ. Ссылка на Glossary вкладку добавлена в footer.
- **FailAnalysisTab упрощение к chips (T11, Bug F):** детальный WHY-failed разбор заменён на chip-list с цветовой индикацией PASS/FAIL + ссылки на Glossary для каждого критерия. Устраняет ошибку "Неизвестный критерий: t1".
- **DocumentationTab ▸ убран (T12, Bug G):** префикс `▸` удалён из 4 заголовков карточек — misleading стрелки отсутствуют.
- **HistoryTab accordion expand (T13+T14, Bug H):** per-row inline accordion (single-open, ESC-close, RU summary при `verdict ∈ {WFA_FAIL, WFA_FAIL_DATA, FAIL}`). `RunDetailsPanel` показывает balance / winrate / PnL. Архитектор C4 BINDING выполнен.
- **GlossaryTab NEW (T15-T19, Bug E):** новая вкладка (4-я в App nav). Section-based sticky TOC + динамический фильтр по стратегии (через `useStrategyContext` C2) + поиск по терму/описанию (case-insensitive substring) + anchor deeplinks. Unknown strategy → show-all + `console.warn`. `useStrategyContext` URL query state hook (архитектор C2 BINDING).
- **BalanceBadge NEW (T21):** презентационный компонент с 4 состояниями: LIVE (зелёный) / CACHED (оранжевый + timestamp) / OFFLINE (серый) / Loading (spinner). `useBybitBalance` hook с `localStorage` cache (`bybit_balance_cache_v1`, FALLBACK_BALANCE=10000).
- **ConfigureBacktest Bybit balance integration (T22, Bug C):** `useBybitBalance` + `BalanceBadge` подключены в форму. `initialBalance` state синхронизирован через `useEffect`. `INITIAL BALANCE` поле отображает живой баланс. `onResult` callback расширен до `(response, initialBalance)`. `App.tsx handleResult` + `setInitialBalance` → `EquityChart`.

### Backend

- **`account_service.py` wrapper (T3, архитектор C1 BINDING):** `src/dashboard/account_service.py` — обёртка над Bybit client для получения баланса аккаунта. Изолирует bybit-api от dashboard routes. Pattern: dependency injection через `get_account_service()`.
- **`/api/bybit/balance` endpoint (T4):** `GET /api/bybit/balance` → `BalanceResponse(total_equity, available_balance, currency, cached_at)`. Использует `account_service`.
- **`glossary_data.py` RU словарь (T5):** `src/dashboard/glossary_data.py` — ~40+ RU записей для всех аббревиатур и метрик дашборда. `STRATEGY_TO_METRICS_MAP` — маппинг preset ID → применимые метрики.
- **`/api/glossary` endpoint (T6, архитектор C3 BINDING):** `GET /api/glossary?strategy=<id>` — единственный endpoint Glossary. Параметр `applies_to` — client-side фильтр. `GlossaryResponse` с `entries[]` + `strategy` поле.
- **`replay_engine` equity_curve emission (T2, Bug B fix):** `replay_engine` эмитирует `equity_curve` для legacy WFA presets. Устраняет пустой chart для стратегий, где equity_curve ранее не генерировался.
- **`RunRecord` balance fields + win_rate (T7, Bug H prereq):** `RunRecord` расширен полями `initial_balance`, `final_balance`, `win_rate` — необходимые данные для accordion HistoryTab.
- **`initial_balance` threading (T22):** `run_backtest()` принимает `initial_balance` kwarg. `BacktestPayload.initial_balance` добавлен.

### Тесты

| Набор | Количество | Примечания |
|-------|-----------|------------|
| Vitest unit | **32** | 23 (S47) + 4 (useStrategyContext) + 3 (HistoryTab accordion+ESC+RU) + 2 (MetricsTable divider) |
| Playwright E2E | **7** | 4 (S47) + 3 (equity-chart-all-presets: research/WFA/empty states) |
| pytest | **1056+** | +account_service + balance endpoint + glossary endpoint + RunRecord fields + replay equity_curve |

### Wiki

- `llm-wiki/wiki/project/sprints/sprint-48-ui-overhaul.md` (этот файл)
- `llm-wiki/wiki/project/architecture/current-state.md` — counts sprint pages 51→52, строка S48 в истории спринтов
- `llm-wiki/wiki/index.md` — запись sprint-48
- `llm-wiki/wiki/log.md` — sprint-end entry S48
- `llm-wiki/wiki/project/SPRINT_STATE.md` — phase=5-verify, 24/24 done

## Operator-surfaced bugs (A-I)

- **Bug A (tooltip + balance):** EquityChart tooltip 3-line с Balance USDT из `initialBalance`. Динамический баланс из Bybit API заменяет фиксированные $10000.
- **Bug B (chart все стратегии):** `replay_engine` расширен для эмиссии `equity_curve` для WFA/legacy presets — chart работает для всех пресетов включая WFA.
- **Bug C (Bybit balance fetch):** реальный баланс аккаунта через `/api/bybit/balance` → `account_service.py` → Bybit API. `BalanceBadge` показывает LIVE/CACHED/OFFLINE статус.
- **Bug D (informational distinction):** `MetricsTable` — разделитель + opacity 0.55 для informational (T1-T6 vs DSR/MC/n_eff — визуально разграничены).
- **Bug E (Glossary tab CORE):** новая вкладка Glossary — полная реализация (бэкенд glossary_data + /api/glossary + фронтенд GlossaryTab + useStrategyContext + App nav).
- **Bug F (chip упрощение):** `FailAnalysisTab` → chip-list PASS/FAIL (цветовые) с ссылками на Glossary. Детальный WHY-failed разбор убран (перенесён в Glossary).
- **Bug G (triangle remove):** `DocumentationTab` — удалён `▸` из 4 card titles.
- **Bug H (expand с RU):** `HistoryTab` accordion expand per-row (single-open + ESC + RU summary для FAIL verdicts).
- **Bug I (language enforcement):** `CLAUDE.md` таблица запрещённых англицизмов — механическое enforcement RU языка в операторском чате.

## Архитектурные binding conditions (C1-C5)

- **C1 (account_service wrapper):** выполнено — `src/dashboard/account_service.py` с dependency injection. Bybit client изолирован от dashboard routes.
- **C2 (URL query state):** выполнено — `useStrategyContext` hook хранит `strategy` в URL query parameter (`?strategy=<id>`). Deep-link и browser back работают.
- **C3 (single glossary endpoint):** выполнено — `/api/glossary?strategy=<id>` единственный endpoint. Client-side `applies_to` filter. Нет per-metric endpoint proliferation.
- **C4 (HistoryTab accordion single-open):** выполнено — только один row открыт одновременно. ESC close. RunDetailsPanel в inline accordion.
- **C5 (component subdirs):** выполнено — `tabs/`, `charts/`, `forms/`, `metrics/`, `shared/`, `glossary/` поддиректории. Pre-plan T1 refactor.

## Тесты / качество

- Python unit: 1056+ (рост за счёт account_service + balance/glossary endpoints + RunRecord + replay equity_curve)
- Python integration: ~58 (unchanged)
- mypy --strict src/: 0 errors
- Vitest unit: 32 (было 23 → +9)
- Playwright E2E: 7 (было 4 → +3 equity-chart-all-presets)
- lint+tsc+build: CLEAN (все T8-T19 коммиты проверяли lint/tsc/build)

## Canonical counts (post-S48)

| Метрика | Значение |
|---------|----------|
| FSM states | **16** (без изменений) |
| FSM events | **30** (без изменений) |
| FSM transitions | **74** (без изменений) |
| Reason codes | **56** (без изменений — UI sprint, не backend risk) |
| ADRs | **66** (без изменений — нет новых ADR в S48) |
| Sprint pages | **52** (этот файл) |
| Components | **48** (BalanceBadge + GlossaryTab — компоненты React, не wiki component pages) |
| Vitest | **32** (+9 vs S47) |
| Playwright E2E | **7** (+3 vs S47) |

## Wiki updates

- `llm-wiki/wiki/project/sprints/sprint-48-ui-overhaul.md` (NEW — этот файл)
- `llm-wiki/wiki/project/architecture/current-state.md` (sprint pages 51→52 / sprint history row S48)
- `llm-wiki/wiki/index.md` (sprint-48 entry)
- `llm-wiki/wiki/log.md` (S48 sprint-end entry append)
- `llm-wiki/wiki/project/SPRINT_STATE.md` (T24 done + phase=5-verify)

## Open issues для S49

- **Косметика (operator решит post-S48 review):**
  - Цвета в дизайн-токены (`--color-status-fail/pass/warn`, `--color-text-disabled`)
  - Шрифты + spacing scale унификация
  - Empty/loading/error states во всех компонентах
  - A11y minimum (контраст ≥ 4.5:1 + tablist ARIA + keyboard nav Glossary)
- **S47 carry-overs:**
  - Vitest tests #4 (`computeMonthlyData`) + #5 (`VerdictPanel` mapping)
  - README npm install note (operator first-time setup)
  - F8 `block_size` constant unification
  - MonthlyHeatmap eslint cleanup
  - Item #7 RiskSharedDeps shim cleanup + Item #10 DD_MULTIDAY boundary scenarios
  - BacktestResponse.metrics typing tighten
  - `BybitAdapterError` structured context fields
  - `FailAnalysisTab` + `VerdictPanel` RTL render tests
  - Wiki narrative cleanup (ReasonCode dual-enum attribution)
- **Post-S48 buffer:**
  - mean_reversion S15/S17 LONG-only clarification в DocumentationTab
  - `useStrategyContext` edge: first render race (URL vs defaultPreset)
  - Glossary TOC mobile scroll (sticky header overlap)

## Key decisions

- **Pre-plan validation (обязательна per ADR 0046):** architecture-reviewer + frontend-developer dispatched ДО plan lock. Binding conditions C1-C5 встроены в план. Ни одного архитектурного регресса в PHASE 4.
- **URL query state (C2) вместо React Context-only:** `useStrategyContext` сохраняет `strategy` в URL для deep-link + browser back. Решение убирает coupling Glossary к ConfigureBacktest состоянию.
- **Single glossary endpoint (C3):** один `/api/glossary?strategy=<id>` вместо per-metric endpoints. Client-side `applies_to` filter → меньше API surface, проще кешировать.
- **Chip simplification (Bug F):** детальный WHY-failed разбор (S47 T15) заменён на chips + ссылки. Детали теперь в Glossary. Принцип: complexity в одном месте (Glossary), не дублируется в FailAnalysisTab.
- **Component subdirs (T1 первый, C5 pre-plan):** refactor до написания нового кода (GlossaryTab/BalanceBadge) — устраняет import path chaos при добавлении компонентов.

## Связанные

- [[../plans/2026-05-11-sprint-48-ui-overhaul]] — implementation plan (24 tasks)
- [[../pre-s48-backlog]] — PHASE 2 brainstorm trail + operator binding decisions + pre-plan validation verdicts
- [[../decisions/0014-walk-forward-train2000-test500]] — ADR 0014 acceptance gates (MetricsTable T1-T6)
- [[../decisions/0017-review-agent-harness]] — ADR 0017 review-agent harness (PHASE 6 reviewers)
- [[sprint-47-tech-debt-carryovers]] — предыдущий спринт
- [[sprint-46-react-migration]] — React migration (S46) — исходная база компонентов
