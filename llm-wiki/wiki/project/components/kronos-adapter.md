---
title: ml.kronos_adapter — KronosAdapter / KronosModelAdapter / MockKronosAdapter
type: component
tags: [component, ml, kronos, adapter, foundation-model, torch, protocol, variant, submodule, s52, s53]
created: 2026-05-30
updated: 2026-05-30
sources:
  - src/ml/kronos_adapter.py
  - src/ml/kronos_variant.py
  - tests/unit/test_kronos_adapter.py
  - wiki/project/decisions/0068-sprint-52-kronos-integration.md
  - wiki/project/decisions/0069-sprint-53-kronos-enablement.md
status: stable
---

# Component: ml.kronos_adapter

**TL;DR:** Protocol-based boundary для Kronos ML inference. `KronosAdapter` = Protocol (структурная типизация). `KronosModelAdapter` = реальная реализация с lazy `from model import` через git submodule `third_party/kronos/`. `MockKronosAdapter` = детерминированная заглушка без torch (CI + unit-тесты).

## Назначение

Архитектурный изоляционный слой (ADR 0068 C2): всё, что касается torch/Kronos, инкапсулировано здесь. На стороне вызывающего кода (prediction_cache, kronos_strategy) используется только Protocol — никакого импорта torch за пределами `src/ml/`.

## Delivery (S53)

Kronos-код доставляется через git submodule `third_party/kronos/` (pinned sha `67b630e67f6a18c9e9be918d9b4337c960db1e9a`). Корректный импорт: `from model import Kronos, KronosPredictor, KronosTokenizer`. `KronosModelAdapter.__init__` добавляет `third_party/kronos/` в `sys.path` внутри метода (scoped, не module-level).

```bash
# Оператор ОБЯЗАН перед первым RUN_ML=1:
git submodule update --init third_party/kronos
```

## Public API (post-S53)

```python
# Protocol (структурная типизация)
class KronosAdapter(Protocol):
    def predict(
        self,
        ohlcv_df: pd.DataFrame,
        lookback: int,
        horizon: int,
    ) -> list[Decimal]:
        """Forecast horizon close prices as list[Decimal]."""
        ...
```

```python
# Реальная реализация — принимает KronosVariant (S53 C10)
class KronosModelAdapter:
    def __init__(
        self,
        variant: KronosVariant,   # KRONOS_BASE или KRONOS_MINI (src/ml/kronos_variant.py)
        device: str = "mps",
        *,
        temperature: float = 1.0,
        top_p: float = 0.9,
        sample_count: int = 1,
        revision: str | None = None,  # SECURITY: pin перед RUN_ML=1
    ) -> None: ...

# CI/unit заглушка (детерминированная, без torch)
class MockKronosAdapter:
    def predict(self, ohlcv_df, lookback, horizon) -> list[Decimal]:
        """Экстраполирует last close × DRIFT_PER_STEP."""
        ...
```

## KronosVariant (S53 C10)

```python
# src/ml/kronos_variant.py
KRONOS_BASE = KronosVariant(name="base", model_id="NeoQuasar/Kronos-base",
                             tokenizer_id="NeoQuasar/Kronos-Tokenizer-base", max_context=512)
KRONOS_MINI = KronosVariant(name="mini", model_id="NeoQuasar/Kronos-mini",
                             tokenizer_id="NeoQuasar/Kronos-Tokenizer-2k", max_context=2048)
```

Структурная кодировка исключает повторение S52-бага (mini с base-токенизатором).

## Ключевые свойства

| Свойство | Значение |
|----------|---------|
| torch import | Lazy — `from model import ...` внутри `__init__`, не на уровне модуля (C8) |
| Submodule | `third_party/kronos/` pinned sha (C9); `sys.path` scoped в метод |
| Decimal boundary | float32 → `Decimal(str(v))` на выходе `src/ml/` (ADR 0068 C6) |
| KronosVariant | Frozen dataclass — гарантирует правильный tokenizer↔max_context (C10 S53) |
| CI-safe | MockKronosAdapter = без torch, без HF download, без MPS |
| Error hint | `ImportError`: 2 шага — `git submodule update --init` + `pip install .[ml]` (C13) |
| predict-sig guard | `test_predict_forwards_correct_kwargs_to_predictor` — блокирует call contract без torch (CC3 S53) |

## Compute

Реальный inference: Mac M4 Pro, `device="mps"`. Веса gitignored, download-on-demand. Запуск: `RUN_ML=1 scripts/run_kronos_s53.py --variant {base|mini}` (оффлайн cache-build). Оба variant = exploratory `RAW_PRETRAIN_LEAKAGE_SUSPECTED`.

## Связанные

- `KronosVariant` dataclass (`src/ml/kronos_variant.py`, S53 C10) — base/mini singletons (документирован в этой странице выше)
- [[./prediction-cache]] — consumer (адаптер вызывается только при cache-build, не в on_bar)
- [[./kronos-strategy]] — конечный потребитель прогнозов (через cache)
- [[../decisions/0069-sprint-53-kronos-enablement]] — ADR 0069 (S53: import fix + variant + submodule + two-step error)
- [[../decisions/0068-sprint-52-kronos-integration]] — ADR 0068 (S52: Protocol boundary + Decimal boundary + CI mock)
- [[../sprints/sprint-53-kronos-enablement]] — спринт S53 (T3 adapter fix)
- [[../sprints/sprint-52-kronos]] — спринт создания компонента (T2)
