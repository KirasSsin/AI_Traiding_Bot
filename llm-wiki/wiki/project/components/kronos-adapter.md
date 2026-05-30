---
title: ml.kronos_adapter — KronosAdapter / KronosModelAdapter / MockKronosAdapter
type: component
tags: [component, ml, kronos, adapter, foundation-model, torch, protocol, s52]
created: 2026-05-30
updated: 2026-05-30
sources:
  - src/ml/kronos_adapter.py
  - tests/unit/test_kronos_adapter.py
  - wiki/project/decisions/0068-sprint-52-kronos-integration.md
status: stable
---

# Component: ml.kronos_adapter

**TL;DR:** Protocol-based boundary для Kronos ML inference. `KronosAdapter` = Protocol (структурная типизация). `KronosModelAdapter` = реальная реализация с lazy torch import. `MockKronosAdapter` = детерминированная заглушка без torch (CI + unit-тесты).

## Назначение

Архитектурный изоляционный слой (ADR 0068 C2): всё, что касается torch/transformers/HuggingFace, инкапсулировано здесь. На стороне вызывающего кода (prediction_cache, kronos_strategy) используется только Protocol — никакого импорта torch за пределами `src/ml/`.

## Public API

```python
# Protocol (структурная типизация — никакого наследования не требуется)
class KronosAdapter(Protocol):
    def predict(
        self,
        df: "pd.DataFrame",  # OHLCV с timestamp index
        x_timestamp: int,    # последний известный bar timestamp
        y_timestamp: int,    # целевой bar timestamp
        pred_len: int,       # горизонт прогноза (V2 LOCKED = 1)
        T: float,            # temperature (V4 LOCKED = 1.0)
        top_p: float,        # top_p nucleus sampling (V4 LOCKED = 0.9)
        sample_count: int,   # кол-во семплов (V4 LOCKED ≥ 20)
    ) -> "list[float]":
        """Возвращает список predicted_close значений (len = sample_count)."""
        ...

    @property
    def model_id(self) -> str: ...

    @property
    def weights_hash(self) -> str:
        """SHA-256 хэш весов модели для CacheKey provenance."""
        ...
```

```python
# Реальная реализация (lazy torch import — torch грузится только при первом вызове predict)
class KronosModelAdapter:
    def __init__(
        self,
        model_id: str = "NeoQuasar/Kronos-mini",
        device: str = "mps",
        max_context: int = 2048,
    ) -> None: ...
    def predict(self, ...) -> list[float]: ...

# CI/unit заглушка (детерминированная, без torch)
class MockKronosAdapter:
    def predict(self, ...) -> list[float]:
        """Возвращает детерминированные mock-значения на основе последнего close."""
        ...
```

## Ключевые свойства

| Свойство | Значение |
|----------|---------|
| torch import | Lazy (только внутри `predict()`, не на уровне модуля) |
| Decimal boundary | float32 → `Decimal(str(v))` на выходе `src/ml/` (ADR 0068 C6) |
| Детерминизм | torch seed + sample_count ≥ 20 + median ensemble + determinism test |
| CI-safe | MockKronosAdapter = без torch, без HF download, без MPS |
| AST guard | `tests/unit/test_kronos_adapter.py::test_torch_isolation` проверяет, что torch не импортируется в non-ml модулях |

## Compute

Реальный inference: Mac M4 Pro, `device="mps"`. Веса `NeoQuasar/Kronos-mini` (~4.1M params, ctx2048) — gitignored, download-on-demand via HuggingFace. Запуск: `RUN_ML=1 scripts/run_kronos_s52.py` (оффлайн cache-build).

## Связанные

- [[./prediction-cache]] — consumer (адаптер вызывается только при cache-build, не в on_bar)
- [[./kronos-strategy]] — конечный потребитель прогнозов (через cache)
- [[../decisions/0068-sprint-52-kronos-integration]] — ADR C1 (optional [ml] dep group) + C2 (Protocol boundary) + C5 (weights gitignored + CI mock) + C6 (Decimal boundary)
- [[../sprints/sprint-52-kronos]] — спринт создания компонента (T2)
