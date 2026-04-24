---
title: Domain Models (pydantic v2) — Bar / Signal / Order / Fill
type: component
tags: [platform, domain-models, pydantic, marketdata, signalgen, execution]
created: 2026-04-20
updated: 2026-04-20
sources: [src/marketdata/models.py, src/signalgen/models.py, src/execution/models.py, tests/unit/test_marketdata_models.py, tests/unit/test_signalgen_models.py, tests/unit/test_execution_models.py]
status: stable
---

# Domain Models (pydantic v2)

**TL;DR:** Четыре immutable pydantic v2 модели с жёсткими инвариантами: `Bar` (OHLC + UTC времена), `Signal` (LONG/FLAT + look-ahead invariant), `Order` (executed_qty ≤ orig_qty), `Fill` (frozen append-only запись исполнения).

## Definition / Purpose

Реализация [[../decisions/0006-pydantic-v2-for-domain-models]]. Каждая модель живёт в своём bounded context:

### `src/marketdata/models.py` — `Bar` + `DataQuality`

- `DataQuality(StrEnum)` — `OK | GAP | STALE | SUSPECT`.
- `Bar(BaseModel, frozen=True, extra="forbid")` — OHLCV свеча:
  - `symbol` (regex `^[A-Z]+USDT$`), `interval` (Literal из 6 TF).
  - `open_time`, `close_time` — `datetime` (UTC, ns precision per [[../decisions/0007-utc-timestamps-ns-precision]]).
  - `open/high/low/close` — `Decimal`, `volume/trade_count ≥ 0`.
  - `is_closed: bool`, `data_quality: DataQuality` (default OK).
- **Invariants (`model_validator mode=after`)**:
  - `high >= max(open, close)`,
  - `low <= min(open, close)`,
  - `close_time > open_time`.

### `src/signalgen/models.py` — `Signal` + `SignalSide`

- `SignalSide(StrEnum)` — `LONG | FLAT`. `SHORT` не используется v0.1 (spot only, [[../decisions/0004-binance-spot-as-initial-venue]]).
- `Signal(BaseModel, frozen=True, extra="forbid")`:
  - `signal_id: UUID`, `symbol`, `side: SignalSide`.
  - `bar_close_time`, `generated_at` — времена закрытия бара и эмиссии сигнала.
  - Indicator snapshot: `ema_fast`, `ema_slow`, `adx_14` (0..100), `plus_di_14`, `minus_di_14`, `rsi_14` (0..100), `atr_14` (≥0).
  - `reason: str` (≤128 chars, код из 28 enum-значений per [[../../trading/concepts/reason-codes]]).
- **Invariant (look-ahead)**: `generated_at >= bar_close_time` — защита от [[../../trading/concepts/look-ahead-bias]].

### `src/execution/models.py` — `Order` / `Fill` + enums

- `OrderSide`: `BUY | SELL`. `OrderType`: `MARKET | LIMIT | STOP_MARKET | STOP_LIMIT | TAKE_PROFIT`. `OrderStatus`: `NEW | PARTIALLY_FILLED | FILLED | CANCELED | EXPIRED | REJECTED`.
- `Order(BaseModel, extra="forbid")` — **mutable** (status/executed_qty обновляются оркестратором при fills):
  - `client_order_id` (1..64 chars), `exch_order_id: str | None`, `symbol`.
  - `orig_qty > 0`, `executed_qty >= 0`, `price: Decimal | None`.
  - `created_at`, `updated_at`.
  - **Invariant**: `executed_qty <= orig_qty`.
- `Fill(BaseModel, frozen=True, extra="forbid")` — immutable event записи сделки:
  - `client_order_id`, `trade_id > 0` (от биржи), `qty > 0`, `price > 0`, `fee >= 0`, `fee_asset`, `is_maker: bool`, `filled_at`.

## Key properties

- **Frozen by default** — `Bar`, `Signal`, `Fill` immutable; `Order` — единственная mutable модель (allowed by design: status changes).
- **`extra="forbid"`** — любое неизвестное поле = ValidationError, защита от опечаток.
- **Decimal, не float** — для цен/объёмов (защита от FP-ошибок в денежных расчётах).
- **regex на `symbol`** — `^[A-Z]+USDT$` гарантирует USDT-quoted спот-пару.
- **model_validator** вместо `@field_validator` — инварианты кросс-полевые (OHLC связывает 4 поля).

## Invariants (CRITICAL — verified by tests + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | `Signal.generated_at >= bar_close_time` — look-ahead pydantic validator | `src/core/models.py` Signal model_validator | `tests/property/test_lookahead.py` |
| 2 | `Bar` OHLC UTC ns timestamps (no naive datetime) | `src/core/models.py` Bar model + ADR 0007 | `tests/unit/test_marketdata_models.py` |
| 3 | `Order.executed_qty <= orig_qty` (no overfill) | `src/core/models.py` Order model_validator | `tests/unit/test_execution_models.py` |
| 4 | `Fill` frozen (append-only, no mutation) | `src/core/models.py` Fill `model_config = {"frozen": True}` | `tests/unit/test_execution_models.py` |

## Usage

```python
from decimal import Decimal
from datetime import datetime, UTC
from src.marketdata.models import Bar, DataQuality

bar = Bar(
    symbol="BTCUSDT", interval="1h",
    open_time=datetime(2026,4,20,tzinfo=UTC),
    close_time=datetime(2026,4,20,1,tzinfo=UTC),
    open=Decimal("60000"), high=Decimal("60500"),
    low=Decimal("59800"), close=Decimal("60200"),
    volume=Decimal("1.5"), trade_count=100,
    is_closed=True, data_quality=DataQuality.OK,
)
# bar.open = Decimal("59000")  # raises FrozenInstanceError
```

## Related

- [[../architecture/bounded-contexts]] — три контекста, в которых живут модели.
- [[../architecture/domain-events]] — BarClosed / SignalEmitted / OrderFilled используют эти типы в payload.
- [[../decisions/0006-pydantic-v2-for-domain-models]] — ADR за pydantic v2.
- [[../decisions/0007-utc-timestamps-ns-precision]] — все datetime поля UTC ns.
- [[storage]] — Parquet writer использует `Bar`, SQLite `orders`/`fills` таблицы соответствуют `Order`/`Fill`.

## Sources

- `src/marketdata/models.py`, `src/signalgen/models.py`, `src/execution/models.py`.
- Тесты (11): `tests/unit/test_marketdata_models.py` (5), `test_signalgen_models.py` (3), `test_execution_models.py` (3) — покрывают happy path + каждый invariant.
