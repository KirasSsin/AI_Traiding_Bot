---
title: "Sprint 53 — Kronos real-inference enablement"
type: sprint
tags: [sprint-53, kronos, ml-strategy, submodule, variant, atr-fix, import-fix, enablement, reason-codes-67, s53]
created: 2026-05-30
updated: 2026-05-30
status: completed
sources:
  - llm-wiki/wiki/project/plans/2026-05-30-sprint-53-kronos-enablement.md
  - llm-wiki/wiki/project/decisions/0069-sprint-53-kronos-enablement.md
  - llm-wiki/wiki/project/pre-s53-backlog.md
---

# Sprint 53 — Kronos real-inference enablement

## Обзор

S52 поставил Kronos-инфраструктуру, но real-inference path оказался сломан тремя багами. S53 чинит все три + добавляет оба variant (base + mini) + формализует архитектуру доставки кода через git submodule.

**Baseline (post-S52):** pytest 1481 / mypy 0 / reason_codes 67.
**Post-S53:** pytest ~1512 / mypy 0 / reason_codes **67** (без изменений — S53 не добавляет новых reason codes).

## 3 бага S52 (все устранены)

| Баг | Описание | Статус |
|-----|----------|--------|
| **CC1** import | `from kronos import` → нет такого пакета; нужен `from model import` | FIXED T3 |
| **CC1** tokenizer мисматч | mini использовал `-base` токенизатор вместо `-2k` | FIXED T2 |
| **CC2** ATR=0 | `KronosStrategy._build_signal` заглушал `atr_14=0` → broken bracket sizing | FIXED T4 |

## Задачи (T1-T8)

| Задача | Описание | Binding condition |
|--------|----------|-------------------|
| **T1** | git submodule `third_party/kronos` (sha 67b630e) + existence guard | C9, C12 |
| **T2** | `src/ml/kronos_variant.py` — KronosVariant frozen dataclass (KRONOS_BASE + KRONOS_MINI) | C10 |
| **T3** | `src/ml/kronos_adapter.py` — import fix (`from model import`) + variant param + two-step error msg | C8, C13 |
| **T4** | `src/signalgen/kronos_strategy.py` — реальный Wilder ATR (Track A, CC2 BLOCKER) | CC2 |
| **T5** | `src/dashboard/_kronos_dispatch.py` — extract из backtest_runner (god-object split, <1500 LoC) | C11 |
| **T6** | Variant dispatch: 2×11 presets + no-cherry-pick предупреждение в dashboard | Q2, Q4 |
| **T7** | `scripts/run_kronos_s53.py` — rename + variant selector + rebuild warning | CC1, CC4, CC5 |
| **T8** | ADR 0069 + predict-sig guard (CC3) + wiki sync + current-state.md split | C12, CC3 |

## Ключевые архитектурные решения (ADR 0069 C8-C13)

| Условие | Суть |
|---------|------|
| **C8** | Import fix: `from model import Kronos, KronosPredictor, KronosTokenizer` (submodule-based) |
| **C9** | Submodule pinned sha `67b630e67f6a18c9e9be918d9b4337c960db1e9a` |
| **C10** | `KronosVariant` frozen dataclass — структурная кодировка `model↔tokenizer↔max_context` |
| **C11** | `_kronos_dispatch.py` — extracted из backtest_runner; `backtest_runner` < 1500 LoC |
| **C12** | CI isolation: `test_gitmodules_registers_kronos` ALWAYS + `test_kronos_model_module_present_when_run_ml` SKIP без RUN_ML; predict-sig guard CC3 (`object.__new__` bypass) |
| **C13** | Два шага в error msg: `git submodule update --init third_party/kronos` + `pip install -e '.[ml]'` |

## Brainstorm verdicts (Q1-Q5, pre-s53-backlog.md)

| Вопрос | Вердикт |
|--------|---------|
| **Q1** | git submodule (pip-from-git EMPIRИЧЕСКИ НЕВОЗМОЖЕН — нет setup.py/pyproject у репо) |
| **Q2** | Оба variant: KRONOS_BASE (ctx512/tok-base) + KRONOS_MINI (ctx2048/tok-2k) |
| **Q3** | V3 LOCKED (ESC-1 operator), ATR fix only (Track A); enrichment Track B DEFERRED |
| **Q4** | Оба exploratory, no-cherry-pick (leakage discipline) |
| **Q5** | Forward harness → S54+ |

## Variants (LOCKED)

| Вариант | model_id | tokenizer_id | max_context |
|---------|----------|-------------|-------------|
| `KRONOS_BASE` | `NeoQuasar/Kronos-base` | `NeoQuasar/Kronos-Tokenizer-base` | 512 |
| `KRONOS_MINI` | `NeoQuasar/Kronos-mini` | `NeoQuasar/Kronos-Tokenizer-2k` | 2048 |

## Gates (post-S53)

| Gate | Результат |
|------|-----------|
| pytest unit | ~**1512** passed |
| mypy --strict | **0** errors |
| reason_codes | **67** (без изменений vs S52) |
| FSM states/events/transitions | **16/30/74** (без изменений) |
| backtest_runner | **< 1500** LoC (после C11 extract) |
| torch isolation AST | PASS (torch не импортируется в non-ml модулях) |
| CI (no torch) | PASS (MockKronosAdapter) |

## Оператор M4 runbook (post-S53)

```bash
# Шаг 1: инициализация submodule (необходимо один раз)
git submodule update --init third_party/kronos

# Шаг 2: установка ml зависимостей
pip install -e ".[ml]"

# Шаг 3: установить revision (SECURITY — верифицировать sha перед запуском)
export KRONOS_REVISION="<verified_commit_sha>"

# Шаг 4: cache-build для base variant
RUN_ML=1 .venv/bin/python scripts/run_kronos_s53.py --variant base

# Шаг 5: cache-build для mini variant
RUN_ML=1 .venv/bin/python scripts/run_kronos_s53.py --variant mini

# Шаг 6: exploratory backtest через dashboard
python -m src.dashboard  # → dropdown «ML / Прогноз»
```

**ВАЖНО:** смена variant/tokenizer invalidates `weights_hash` → полный rebuild кэша `data/kronos_cache/`. Backtest обоих variant = exploratory `RAW_PRETRAIN_LEAKAGE_SUSPECTED` — selection по backtest-результату запрещён (leakage + selection bias).

## Deferred

- **Formal hypothesis #11**: N_trials++ + cross_trial pool "kronos" fill → DEFERRED до ≥6 мес post-cutoff (~post-2025-08) forward data.
- **Track B** signal enrichment: predicted_high/low SL/TP, multi-horizon → DEFERRED до forward paper-trade.
- **Forward paper-trade harness** → S54+.

## Related

- [[../decisions/0069-sprint-53-kronos-enablement]] — ADR 0069 (accepted)
- [[../decisions/0068-sprint-52-kronos-integration]] — ADR 0068 (parent, S52 Kronos foundation)
- [[../components/kronos-adapter]] — обновлён S53 (variant param, submodule delivery, from model import)
- [[../components/kronos-strategy]] — обновлён S53 (real ATR fix)
- [[../components/prediction-cache]] — unchanged S53
- [[sprint-52-kronos]] — предыдущий спринт (baseline 1481/0/67)
- [[../plans/2026-05-30-sprint-53-kronos-enablement]] — план T1-T8
