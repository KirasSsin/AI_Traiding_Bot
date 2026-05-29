---
title: "Sprint 49 — Full Tech-Review Audit (9 параллельных ревьюеров, все домены)"
type: sprint
tags: [sprint-49, tech-review, audit, blockers, security, bybit, verdict, reason-codes, tdd]
created: 2026-05-29
updated: 2026-05-29
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
  - llm-wiki/wiki/project/decisions/0021-sprint-7-resilience.md
  - llm-wiki/wiki/project/decisions/0023-halt-code-fsm-event-mapping.md
---

# Sprint 49 — Full Tech-Review Audit

## Обзор

S49 = полный аудит всей кодовой базы 9 параллельными доменными ревьюерами (opus). Никакого новых функций — только поиск и устранение дефектов. Охват: 14.5k строк `src/` Python + 4.2k строк React/TypeScript + 21.7k строк тестов. Audit-first подход: сначала review → план → TDD-исправление → повторный review → ship.

**Baseline (post-S48):** pytest 1065 / mypy 0 / Vitest 36 / Playwright 7 / reason_codes 56.
**Post-S49:** pytest 1350 (+285) / mypy 0 / Vitest 43 / Playwright 7 / reason_codes **63** (+7).

## Метод: 9 параллельных ревьюеров (opus)

Все 9 доменных агентов dispatched одновременно для параллельного аудита:

| Агент | Домен | Основные находки |
|-------|-------|-----------------|
| `bybit-api-reviewer` | Bybit V5 API protocol | B1 duplicate-order, B2 unguarded schema |
| `data-integrity` | Data quality + storage | B3 WS gap-fill, B4 atomic Parquet |
| `security-auditor` | OWASP + trading-specific | `.env` chmod 600, H1 path-traversal |
| `trading-logic` | Strategy + execution | H4 state_repo halt order, H10 T3 verdict |
| `quant-stats` | DSR / MC / metrics | H7 migration 004 money REAL→TEXT |
| `python-reviewer` | Code quality, typing | M3 narrow except, L1-L8 ruff/style |
| `test-engineer` | Coverage + property tests | H9 resume_cb 0%→96%, M8 compute_metrics |
| `dashboard-reviewer` | FastAPI + React | H2 FastAPI response_model, H3 TTL cache |
| `architecture-reviewer` | ADR alignment | H8 _compute_verdict extraction |

Итог первого раунда: **5 BLOCKER + 10 HIGH + 8 MEDIUM + 8 LOW**.

## BLOCKER-исправления (B1-B4 + env)

### B1 — Bybit дублирующиеся ордера (детерминированный orderLinkId)

**Проблема:** `orderLinkId` генерировался без привязки к сигналу — при сетевом retry возможно двойное исполнение ордера.

**Исправление:** `src/execution/bybit/adapter.py` — `orderLinkId = f"{signal_id}:{side}:{qty}"` (детерминированный, идемпотентный). Bybit V5 отклоняет дублирующийся `orderLinkId` в пределах сессии → двойной ордер невозможен.

### B2 — Unguarded schema access в Bybit adapter

**Проблема:** прямой dict-доступ к ответу Bybit без проверки структуры — `KeyError` при неожиданном формате.

**Исправление:** `_safe_extract_list()` guard применён к точкам разбора ответа. `BybitAdapterError` с контекстными полями заменяет голый `KeyError`.

### B3 — WS gap-fill wiring (DataQuality.GAP)

**Проблема:** WebSocket gap-fill событие не ставило флаг `DataQuality.GAP` — gap проходил незамеченным.

**Исправление:** `src/marketdata/gaps.py` + `pipeline.py` — wiring `DataQuality.GAP` при обнаружении пропуска в WS-потоке. Интеграционные тесты подтверждают флагирование.

### B4 — Не-атомарная запись Parquet

**Проблема:** `parquet_writer.py` писал файл напрямую — сбой в середине записи давал повреждённый Parquet без возможности восстановления.

**Исправление:** `write_temp = path.with_suffix('.tmp') → os.replace(write_temp, path)`. Атомарный паттерн temp+replace — либо файл записан полностью, либо остаётся старый.

### .env chmod 600 (security)

**Проблема:** `.env` с API-ключами не имел ограничений на чтение.

**Исправление:** `src/platform/config.py` startup-проверка — `chmod 600 .env` автоматически при загрузке конфига если права шире 0o600. Логирование предупреждения.

## HIGH-исправления (H1-H10)

| ID | Файл | Суть |
|----|------|------|
| H1 | `src/dashboard/backtest_runner.py` | `run_id` regex anchored `^[A-Za-z0-9_-]+$` — предотвращает path-traversal |
| H2 | `src/dashboard/app.py` | FastAPI `response_model` добавлен к 4 endpoint, `async def` → `def` (blocking IO), date validation `HTTPException 422` |
| H3 | `src/dashboard/account_service.py` | Server-side TTL cache 30 секунд — предотвращает rate limit при multi-instance |
| H4 | `src/execution/state_repo.py` | Halt write-ahead: `state_repo.save(HALTED)` ДО `coordinator.dispatch(HALT)` per ADR 0021 SD-5 |
| H5 | `src/execution/fill_recorder_adapter.py` | `threading.Lock` добавлен к `FillRecorderAdapter._flush()` — предотвращает race condition |
| H6 | `src/risk/reason_codes.py` | +7 кодов: EMA (2) + mean-reversion (3) + Donchian (2) attribution codes; 56→63 |
| H7 | `src/platform/db.py` (migration 004) | `money` колонка `REAL→TEXT` (exact decimal) — предотвращает floating-point drift в PnL |
| H8 | `src/dashboard/backtest_runner.py` | `_compute_verdict()` выделена отдельной функцией — логика вердикта изолирована и тестируема |
| H9 | `tests/unit/test_resume_cb.py` | `resume_cb` coverage 0%→96% — 18 новых unit-тестов |
| H10 | `src/dashboard/backtest_runner.py` | T3 verdict семантика: только T5/DSR/MC/sharpe_gate/n_eff = gate-blocking; T1/T2/T3/T4/T6 = informational |

## T3 RESOLUTION — Trader-expert binding verdict

**Суть разногласия (S48 carry-over B2):** `_compute_verdict` включал `"t3"` (max drawdown ≥ 25%) в `failed_criteria` при формировании WFA_FAIL вердикта, хотя ADR 0014 + MetricsTable UI декларируют T3 как informational.

**Trader-expert process (ROUND 1+2):**
- ROUND 1: trader-expert рекомендует исключить T3 из gate-blocking — drawdown информационна, не торговый стоп.
- ROUND 2: architecture-reviewer подтвердил: только T5 count + DSR + MC p-value + sharpe_gate + n_eff — настоящие acceptance gates (имеют числовые пороги из ADR 0014). T1/T2/T3/T4/T6 = informational (качественные индикаторы, не блокирующие).

**Binding verdict:** gate-blocking = `{t5, dsr, mc, sharpe_gate, n_eff}`. `_compute_verdict` исправлен: T1/T2/T3/T4/T6 убраны из логики failed-criteria.

**ADR + документация обновлены:**
- `wiki/project/decisions/0014-walk-forward-train2000-test500.md` — добавлена таблица gate-blocking vs informational
- `wiki/project/architecture/acceptance-criteria.md` — явная таблица с порогами и ролями каждой метрики

**UI (MetricsTable, FailAnalysisTab):** не тронут — уже корректно показывал GATE-BLOCKING/INFORMATIONAL разделитель (S48 T10).

## MEDIUM + LOW исправления

| ID | Суть |
|----|------|
| M1 | `final_balance_quote` — compound equity, не additive `_running_pct` sum |
| M2 | `useStrategyContext` multi-instance: `popstate` listener + URL sync при mount |
| M3 | Narrow broad `except Exception` → конкретные типы исключений; lazy logging `%s` |
| M4 | `block_bootstrap` docstring — edge-null warning добавлен |
| M5 | hardcoded-holding placeholder — clarity комментарий |
| M6 | `RunRecord` length invariant: `raise ValueError` вместо silent truncation |
| M7 | `MonthlyHeatmap` return math — correct monthly compound return formula |
| M8 | `ReasonCode` coverage sweep (56→63 attribution codes) + `compute_metrics` property test |
| L1-L8 | ruff: dead imports, F-strings, ARG002 rename, dust-tolerance qty equality, import-order |

## Повторный review (6 агентов) — все APPROVE

После применения всех исправлений 6 агентов dispatched для повторной проверки:

| Агент | Вердикт | Замечания |
|-------|---------|-----------|
| `bybit-api-reviewer` | **APPROVE** | B1+B2 корректны; orderLinkId детерминирован |
| `trading-logic` (verdict) | **APPROVE** | H10 T3 семантика правильная; ADR aligned |
| `data-integrity` | **APPROVE** | B3+B4 корректны; M1 compound equity правильный |
| `dashboard-reviewer` | **APPROVE** | H2+H3 FastAPI fixes clean |
| `security-auditor` | **APPROVE** | .env chmod + H1 path-traversal + H5 lock — все OK |
| `python-reviewer` | **APPROVE** | M3+L1-L8 clean; typing preserved |

**0 регрессий.** +2 defense-in-depth: anchored regex (H1), `raise ValueError` (M6).

## Gates (post-S49)

| Инструмент | Результат | Дельта |
|-----------|----------|--------|
| pytest unit | **1350 passed** | +285 vs 1065 baseline |
| mypy --strict | **0 errors / 89 files** | unchanged |
| Vitest unit | **43** | +7 vs 36 (S48) |
| Playwright E2E | **7** | unchanged |
| ruff lint | **clean** | — |
| tsc --noEmit | **0 errors** | — |
| Vite build | **clean** | — |

## Reason codes: 56→63

**H6** добавил 7 кодов attribution в `src/risk/reason_codes.py`:

- EMA crossover: `EXIT_EMA_SIGNAL_FLIP`, `EXIT_EMA_ADX_FILTER`
- Mean-reversion: `EXIT_MR_RSI_EXIT`, `EXIT_MR_BB_EXIT`, `EXIT_MR_TIME_STOP`
- Donchian: `EXIT_DCH_TRAIL_STOP`, `EXIT_DCH_SIGNAL_FLIP`

Проверка: `.venv/bin/python -c "from src.risk.reason_codes import ReasonCode; print(len(list(ReasonCode)))"` → **63**.

## Key decisions

- **Audit-first sprint без новых фич:** 100% бюджета на поиск и устранение дефектов. Первый спринт с 9 параллельными ревьюерами opus одновременно.
- **T3 gate-blocking RESOLVED (binding):** trader-expert + architecture-reviewer binding verdict устранил S48 carry-over B2. ADR 0014 + acceptance-criteria.md обновлены, UI не тронут (уже корректен).
- **Atomic Parquet (B4):** temp+replace паттерн — стандарт для всех будущих Parquet-записей.
- **orderLinkId детерминированность (B1):** `signal_id:side:qty` схема — защита от двойного исполнения при retry. Binding precedent для новых ордеров.
- **H4 halt write-ahead order (ADR 0021 SD-5):** подтверждён и enforcement добавлен в тест.

## Связанные

- [[../decisions/0014-walk-forward-train2000-test500]] — ADR 0014 acceptance gates + T3 gate-blocking table (обновлён S49)
- [[../decisions/0021-sprint-7-resilience]] — ADR 0021 SD-5 halt write-ahead order (H4 исправление)
- [[../decisions/0023-halt-code-fsm-event-mapping]] — ADR 0023 halt-code mapping invariant
- [[sprint-48-ui-overhaul]] — предыдущий спринт (S48)
