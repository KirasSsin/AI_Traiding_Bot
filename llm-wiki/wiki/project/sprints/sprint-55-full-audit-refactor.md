---
title: "Sprint 55 — Full-project audit + refactor"
type: sprint
tags: [sprint-55, audit, refactor, blocker-fixes, live-runtime, bybit, fsm, security, data-integrity, dashboard, quant-stats, s55]
created: 2026-06-26
updated: 2026-06-26
status: completed
sources:
  - llm-wiki/wiki/project/plans/2026-06-26-sprint-55-full-audit-refactor.md
  - llm-wiki/wiki/project/decisions/0071-sprint-55-cmd-wfa-dsr-units.md
---

# Sprint 55 — Full-project audit + refactor

## Обзор

S55 — полный аудит проекта на shipped main (tag `v0.1.0-alpha.54`) с последующим рефакторингом. Audit-workflow `w1hxvgkoa` (120 агентов, 9 измерений, 2× скептик-верификация) нашёл **43 подтверждённых дефекта**. Все исправлены через TDD + 2 раунда re-review (PHASE 6 + 6.2), которые выявили ещё 7 follow-up-фиксов.

**Природа спринта:** audit → refactor (не feature-спринт). Аудит покрыл trading-logic, Bybit API, архитектуру, quant-stats, data-integrity, security, dashboard, Python idioms, test-quality.

**Baseline (post-S54):** pytest 1525 / mypy 0/98 / reason_codes 67 / FSM 16/30/74.
**Post-S55:** unit pytest **1694** passed / 0 failed / integration **103** passed / mypy --strict **0**/101 / reason_codes **67** (без изменений) / FSM **16/30/76** (TL-NEW-01 +2) / frontend Vitest **51/51** + tsc/lint/build clean.

## Находки (43 подтверждённых + bonus QS-3)

### BLOCKER (2)

| ID | Описание |
|----|----------|
| **TL-01** | Live-runtime никогда не вооружал OCO + ронял exit-сигналы → unbounded-loss. Entry-fill не триггерил arm_oco; exit-сигналы не доходили до flatten. |
| **BYBIT-01** | REST и WS использовали разные Bybit-окружения (env) → fill-loop сломан. Ордера на одном env, fill-события с другого. |

### HIGH (9)

| ID | Описание |
|----|----------|
| **TL-02** | Streaming exit-priority дефект в обработке сигналов. |
| **BYBIT-02** | Emergency-flatten tri-state (SENT / NOT_SENT / AMBIGUOUS) классификация. |
| **BYBIT-03** | Унифицированная иерархия ошибок Bybit-адаптера. |
| **ARCH-02** | Reconcile I/O выполнялся под удержанным lock (off-lock relocation). |
| **QS-1** | DSR de-annualization — units-mismatch в money-gate. |
| **DI-01** | Multi-gap bars обрабатывались некорректно. |
| **DI-02** | BarSource ронял незакрытый (unclosed) bar. |
| **SEC-S55-01** | Path-traversal — добавлен allowlist. |
| **DASH-01** | RAW_PRETRAIN research-verdict render в dashboard. |

### MEDIUM (15)

| ID | Описание |
|----|----------|
| **TL-03 / TL-04** | Streaming exit-priority (продолжение TL-02). |
| **ARCH-03** | Public adapter API стабилизация. |
| **BYBIT-04** | Residual orderLinkId. |
| **BYBIT-05** | Residual step-floor dust. |
| **DI-03** | Migration integer-sort. |
| **DI-04** | Bar tz-aware. |
| **DASH-02** | MonthlyHeatmap — true monthly return. |
| **DASH-03** | Atomic cache write + single-flight lock. |
| **QS-2** | `_cmd_wfa` DSR units (ADR 0071). |
| **TQ-01..06** | Test-quality улучшения (6 пунктов). |

### LOW (17)

| ID | Описание |
|----|----------|
| **ARCH-05** | Layering relocation → `src/backtest/data_loading.py`. |
| **TL-06** | KronosStrategy `_current_side`. |
| **TL-07** | ReasonCode enums (вместо raw strings). |
| **QS-2-bars** | 4H bars_per_year = 2191. |
| **DI-06 / SEC-S55-03 / PY-5** | Atomic `prediction_cache.put`. |
| **SEC-S55-04** | WS log field-allowlist. |
| **PY-1..4** | CI / typing / DRY. |
| **TQ-07 / 08** | Test-quality (2 пункта). |
| **DASH-04** | HistoryTab RAW. |
| **DASH-05** | OPTGROUP_ORDER. |
| **BYBIT-06** | Kline stall guard (forward-progress в backward-walk). |

### Bonus

- **QS-3** — donchian DSR twin (тот же units-fix, что QS-1, на donchian_runner).

## FSM рост (74 → 76)

TL-NEW-01 (PHASE 6.2) добавил 2 новых перехода:

| States | Event | Target | Примечание |
|---|---|---|---|
| LONG_OPEN | `FLATTEN_FAILED` | HALTED | TL-NEW-01 (S55) |
| OCO_ARMING | `FLATTEN_FAILED` | HALTED | TL-NEW-01 (S55) |

States = **16** (без изменений), events = **30** (без изменений), reason_codes = **67** (без изменений). Только transitions выросли **74 → 76**.

## Deliverables

### Новые модули

| Модуль | Находка | Назначение |
|--------|---------|------------|
| `src/backtest/data_loading.py` | ARCH-05 | Layering relocation — изоляция загрузки данных. |
| `src/dashboard/_cache_io.py` | DASH-03-GAP-01 | Atomic cache writes (Kronos). |
| `src/ml/weights_hash.py` | TQ-05 | Weights-hash для test-quality. |

### Миграция

| Файл | Находка |
|------|---------|
| `migrations/0007_bracket_exit_prices.sql` | TL-01 (persist bracket exit prices). |

## Тесты

Все фиксы — TDD (RED → GREEN → COMMIT).

| Gate | Результат |
|------|-----------|
| pytest unit | **1694** passed / 0 failed |
| pytest integration | **103** passed |
| mypy --strict | **0** errors (101 файл) |
| ruff src/ | clean |
| frontend Vitest | **51/51** passed |
| frontend tsc / lint / build | clean |
| FSM states/events/transitions/reason_codes | **16/30/76/67** |

## PHASE 6 / 6.2 re-review (7 follow-up-фиксов)

2 раунда re-review выявили регрессии и пробелы:

| ID | Severity | Описание |
|----|----------|----------|
| **SEC-BYBIT01-INCOMPLETE** | HIGH | `demo=` на всех 4 RESTClient-сайтах + AST-gate. |
| **ARCH-02-REG-01** | HIGH | Bootstrap RLock освобождался поверх REST I/O. |
| **ARCH-03-REGRESSION** | HIGH | Integration `_FakeAdapter` props; integration-тесты не были в default-gate. |
| **TL-NEW-01** | MEDIUM | 2 новых FSM-перехода (74 → 76). |
| **DASH-03-GAP-01** | MEDIUM | Kronos atomic writes через новый `src/dashboard/_cache_io.py`. |
| **QS-6** | MEDIUM | `__main__` 4H bars_per_year → 2191. |
| **NEW-LOW-01** | LOW (DRY) | Консолидация `atomic_write_text`. |

## Открытые вопросы → S56

- **BYBIT-08 (CARRY)** — `coordinator._try_place_market_sell` bare-except классифицирует post-`retCode==0` OrderAck-parse-failure как NOT_SENT → flatten attempt-2 → double-sell. Pre-existing + редкий. Корректный фикс = adapter-level typed `AmbiguousOrderOutcome` через 3 `place_*`-варианта (coordinator type-split сломал бы intended retry-with-qty-step дизайн). Требует своего ADR/спринта.

## Ключевые решения

- **ADR 0071** — `_cmd_wfa` DSR units (QS-2). `wfa`-subcommand DSR sigma_SR строился из OOS/IS ratios на GLOBAL-пуле + без `annualization_factor` → units-mismatch money-gate. Fix: real annualized `fold_oos_sharpes` + class-scoped `sigma_sr(strategy_class="wfa_meanrev")` + `annualization_factor=sqrt(bars_per_year)` + namespaced persist. Наивный parity-патч отвергнут (инвертировал бы в false-positive). status: accepted (quant-stats-reviewer APPROVE_WITH_CONCERNS).

## Масштаб

70 commits, 106 файлов, +7189 / -956.

## Related

- [[../decisions/0071-sprint-55-cmd-wfa-dsr-units]] — ADR 0071 (accepted)
- [[../components/execution-state-machine]] — FSM 74 → 76 (TL-NEW-01)
- [[../architecture/current-state]] — canonical counts (FSM 76, ADRs 71)
- [[sprint-54-kronos-ui]] — предыдущий спринт (baseline 1525 / 16/30/74)
- [[../plans/2026-06-26-sprint-55-full-audit-refactor]] — план аудита
