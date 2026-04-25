---
title: MarketData — BarBuilder
type: component
tags: [marketdata, bar-builder, venue-agnostic, edge-cases]
created: 2026-04-21
updated: 2026-04-21
sources: [src/marketdata/bar_builder.py, tests/unit/test_bar_builder.py]
status: stable
---

# MarketData — BarBuilder

**TL;DR:** Venue-agnostic aggregator WS kline-сообщений → `Bar`. Enforces 3 инварианта: `confirm=true` gate, dedup, out-of-order reject. Детектирует и синтезирует GAP bars.

## Definition / Purpose

Принимает dict с полями `start/end/open/high/low/close/volume/confirm` (форма Bybit V5 kline payload). Возвращает `Bar` только если `confirm=true`; иначе `None`.

### Методы

- `process(msg: dict) -> Bar | None` — базовый путь.
- `process_with_gap_fill(msg) -> tuple[Bar | None, Bar | None]` — детектит gap (`open_ms > last_confirmed + interval`) и возвращает `(synthetic_gap_bar, real_bar)`.

### Инварианты (соответствие [[../architecture/edge-cases]])

| Edge case # | Детекция | Реакция |
|---|---|---|
| #1 | `open_ms > last + interval` | Синтетический GAP bar (OHLCV=0, `data_quality=GAP`) |
| #4 | Duplicate `open_ms` после confirm | `OutOfOrderError("duplicate")` |
| #7 | `open_ms < last` | `OutOfOrderError("out-of-order")` |
| #5 | OHLC inconsistent | pydantic Bar model validator → `ValueError` |

## Key properties

- **Venue-agnostic** — никакого pybit/Binance в интерфейсе; работает с dict.
- **Stateful per instance** — хранит `last_confirmed_open_ms`. Один instance = один symbol+interval.
- **No forward-fill в GAP** (per edge-cases #1) — GAP bar имеет OHLCV=0, downstream skip signal.

## Invariants (CRITICAL — verified by tests + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | `confirm=true` gate — non-confirmed bars always return `None` | `src/marketdata/bar_builder.py::BarBuilder.process` | `tests/unit/test_bar_builder.py::test_returns_none_on_non_confirm` |
| 2 | Dedup: duplicate `open_ms` after confirm → `OutOfOrderError` | `src/marketdata/bar_builder.py::BarBuilder._check_order` | `tests/unit/test_bar_builder.py::test_duplicate_after_confirmed_is_rejected` |
| 3 | Out-of-order: `open_ms < last_confirmed` → `OutOfOrderError` | `src/marketdata/bar_builder.py::BarBuilder._check_order` | `tests/unit/test_bar_builder.py::test_out_of_order_is_rejected` |
| 4 | Stateful per instance — one instance per symbol+interval | `src/marketdata/bar_builder.py::BarBuilder.__init__` | (architecture rule) |

## Related

- [[../architecture/edge-cases]] — источник invariant-списка.
- [[models]] — `Bar`, `DataQuality`.
- [[../decisions/0007-utc-timestamps-ns-precision]] — UTC ns datetime.
- [[bybit-ws]] — поставщик сообщений.

## Sources

- `src/marketdata/bar_builder.py`.
- `tests/unit/test_bar_builder.py` (6: confirm/non-confirm/dup-nonconfirm/dup-after-confirm/out-of-order/gap).
