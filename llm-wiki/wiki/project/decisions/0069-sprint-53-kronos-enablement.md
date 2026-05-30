---
title: "0069. Sprint 53 — Kronos real-inference enablement"
type: decision
tags: [decision, adr, s53, kronos, ml-strategy, submodule, variant, import-fix, atr-fix, enablement]
created: 2026-05-30
updated: 2026-05-30
status: accepted
sources:
  - llm-wiki/wiki/project/pre-s53-backlog.md
  - llm-wiki/wiki/project/decisions/0068-sprint-52-kronos-integration.md
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
---

# 0069. Sprint 53 — Kronos real-inference enablement

**Status:** accepted
**Date:** 2026-05-30

## Контекст

S52 поставил Kronos-инфраструктуру (ADR 0068), но real-inference path оказался сломан. При попытке оператора запустить `RUN_ML=1` на M4 обнаружены три бага:

1. **Баг импорта (C8):** код делал `from kronos import KronosPredictor` — такого пакета нет; публичный репозиторий экспортирует `from model import`. Real-inference broken by design.
2. **Несовпадение токенизатора (CC1):** `KRONOS_MINI` (ctx=2048) требует `NeoQuasar/Kronos-Tokenizer-2k`, а S52 использовал `NeoQuasar/Kronos-Tokenizer-base` (ctx=512 — базовый токенизатор). Пара `mini↔base-tokenizer` генерирует неверные last/next tokens → некорректный forecast.
3. **`atr_14=0` в KronosStrategy (CC2):** `_build_signal` заглушал ATR нулём. `risk_manager` вычисляет SL/TP bracket из `Signal.atr_14` → ATR=0 означает SL==entry price или деление на ноль → неторгуемый сигнал.

Оператор принял leakage-дисциплину (ADR 0068 GATE 0) после глубокого объяснения: backtest остаётся `RAW_PRETRAIN_LEAKAGE_SUSPECTED` (exploratory, не gate). S53 устраняет три бага + добавляет оба variant + формализует архитектуру доставки кода.

## Решение

### C8 — Исправление импорта: `from model import`

Kronos-код (https://github.com/shiyu-coder/Kronos) экспортирует классы из модуля `model/`, не из пакета `kronos`. Корректный импорт:
```python
from model import Kronos, KronosPredictor, KronosTokenizer
```

### Q1 — Доставка кода: git submodule (pip-from-git EMPIRИЧЕСКИ НЕВОЗМОЖЕН)

Попытка `pip install git+https://github.com/shiyu-coder/Kronos` провалилась: у репозитория нет `setup.py` / `pyproject.toml` — pip не может его установить как пакет. Единственный работающий способ — **git submodule**:

```
third_party/kronos/   ← git submodule, pinned sha 67b630e67f6a18c9e9be918d9b4337c960db1e9a
```

`KronosModelAdapter.__init__` добавляет `third_party/kronos/` в `sys.path` внутри метода (scoped, не module-level) → модуль `model` становится доступен. CI-изоляция сохранена: `third_party/` не сканируется AST guard; `from model import` внутри метода не попадает в проверку top-level import.

**Оператор ОБЯЗАН** перед первым `RUN_ML=1` выполнить:
```bash
git submodule update --init third_party/kronos
```

### C9 — Submodule pinned sha

Pinned sha: `67b630e67f6a18c9e9be918d9b4337c960db1e9a` (master HEAD на момент S53). Оператор верифицирует sha перед любым `RUN_ML=1` run.

### C10 — KronosVariant dataclass (Q2 — оба variant)

Новый `src/ml/kronos_variant.py` — immutable frozen dataclass, кодирующий тройку `(model_id, tokenizer_id, max_context)`:

| Вариант | model_id | tokenizer_id | max_context |
|---------|----------|-------------|-------------|
| `KRONOS_BASE` | `NeoQuasar/Kronos-base` | `NeoQuasar/Kronos-Tokenizer-base` | 512 |
| `KRONOS_MINI` | `NeoQuasar/Kronos-mini` | `NeoQuasar/Kronos-Tokenizer-2k` | 2048 |

Структурная кодировка исключает повторение бага S52: правильный токенизатор привязан к variant на уровне типа.

### Q3 — V3 сигнал LOCKED, только ATR fix (Track A)

Оператор подтвердил ESC-1: сигнальное правило V3 остаётся без изменений (`predicted_close[h=1] > current×(1+threshold)`, long-only). Исправляется только функциональный баг ATR=0: `KronosStrategy` поддерживает инкрементальный Wilder ATR (`_WilderATR` из `src/signalgen/indicators.py`), заполняет `Signal.atr_14` реальным значением. Если ATR ещё не прогрет (< 14 баров) — сигнал не генерируется (нет SL = нет сделки, безопасно).

Track B (обогащение сигнала: predicted_high/low как SL/TP, multi-horizon) — DEFERRED до forward paper-trade.

### C11 — Извлечение `_kronos_dispatch.py`

`src/dashboard/backtest_runner.py` достиг >1500 строк (HARD-GATE). Kronos-специфичный dispatch вынесен в `src/dashboard/_kronos_dispatch.py` (константы + `_read_kronos_manifest` + `_load_kronos_df` + `run_kronos_dispatch`). `backtest_runner.py` делегирует через `run_kronos_dispatch(req)`.

### Q4 — Оба variant exploratory, no-cherry-pick

Оба variant (base + mini) — exploratory (`RAW_PRETRAIN_LEAKAGE_SUSPECTED`). **Запрещено** выбирать «лучший» variant/combo по backtest-результату — это selection bias поверх уже существующего pretrain leakage. Предупреждение добавлено в описание preset в dashboard. Валидный выбор — только forward paper-trade на post-cutoff (~post-2025-08) данных.

### C12 — CI изоляция + submodule existence test

Тест `tests/unit/test_kronos_submodule.py`:
- `test_gitmodules_registers_kronos` — ALWAYS runs: проверяет `.gitmodules` на наличие `third_party/kronos` + `shiyu-coder/Kronos`.
- `test_kronos_model_module_present_when_run_ml` — `skipif(RUN_ML != "1")`: проверяет `third_party/kronos/model/__init__.py` только при `RUN_ML=1`.

Тест `test_predict_forwards_correct_kwargs_to_predictor` (CC3) — блокирует call contract `KronosModelAdapter.predict()` без torch через `object.__new__` + ручная установка атрибутов.

### C13 — Двухшаговое сообщение об ошибке

`KronosModelAdapter.__init__` при отсутствии submodule/torch поднимает:
```
ImportError: Kronos model code / torch unavailable. Two steps required:
1) git submodule update --init third_party/kronos
2) pip install -e '.[ml]'
```

### Q5 — Forward harness → S54+

Механизм forward paper-trade (единственная валидная Kronos-валидация) — DEFERRED к S54+. Формальная hypothesis #11 (N_trials increment + cross_trial pool "kronos" fill) остаётся DEFERRED до ≥6 мес post-cutoff forward data.

## Последствия

### Положительные

- Real-inference работает на M4 после `git submodule update --init` + `pip install .[ml]` + установки `KRONOS_REVISION`.
- Оба variant (base + mini) поддерживаются корректно: правильный токенизатор, правильный max_context, bracket-ready ATR.
- `KronosVariant` dataclass — структурная гарантия корректной пары `model↔tokenizer` навсегда.
- god-object `backtest_runner.py` разгружен (< 1500 LoC после C11).

### Ограничения

- Backtest остаётся `RAW_PRETRAIN_LEAKAGE_SUSPECTED` (exploratory, не gate) — без изменений vs S52.
- Formal hypothesis #11 DEFERRED — Kronos может никогда не пройти formal gate (принято оператором).
- Смена variant или токенизатора invalidates `weights_hash` → полный rebuild кэша (`data/kronos_cache/`).
- Оператор ОБЯЗАН верифицировать `KRONOS_REVISION` sha перед `RUN_ML=1` (torch.load pickle = ACE risk).

### Изменения canonical counts

Reason codes **67** (без изменений vs S52 — S53 не добавляет новых reason codes). FSM 16/30/74 — без изменений.

## Related

- [[../pre-s53-backlog]] — полный brainstorm trail C8-C13 + Q1-Q5 + 3 bugs
- [[0068-sprint-52-kronos-integration]] — S52 Kronos integration (ADR 0068, parent)
- [[0014-walk-forward-train2000-test500]] — WFA gates (почему backtest невалиден для Kronos)
