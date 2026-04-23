---
title: Execution — BybitMarketAdapter
type: component
tags: [execution, bybit, adapter, anti-corruption-layer, sprint-5]
created: 2026-04-21
updated: 2026-04-23
sources: [src/execution/bybit/adapter.py, src/execution/bybit/errors.py, tests/unit/test_bybit_adapter.py, tests/unit/test_bybit_errors.py]
status: stable
---

# Execution — BybitMarketAdapter

**TL;DR:** MARKET spot orders на Bybit V5. Pre-trade validation через `BybitFilters`, post-trade маппинг retCode → `ReasonCode`.

## Definition / Purpose

Единственный код, который общается с `/v5/order/create` в v0.1. Scope — MARKET only per migration-plan §S2. LIMIT/OCO/STOP — Sprint S5.

### Интерфейс

```python
adapter = BybitMarketAdapter(rest_client, filters)
order: Order = adapter.place_market_order(
    client_order_id="CID-...",   # → orderLinkId
    side=OrderSide.BUY,
    qty=Decimal("0.001"),
    reference_price=Decimal("60000"),  # для min_order_amt check (не идёт в API)
)
```

### Цепочка

1. `filters.validate_order(qty, price)` — `FilterViolation` до API-вызова, если ниже min_order_qty / min_order_amt.
2. `pybit.HTTP.place_order(category="spot", orderType="Market", ...)`.
3. `retCode == 0` → `Order(status=NEW, exch_order_id=result.orderId)`.
4. `retCode != 0` → `map_error()` → `BybitAPIError(reason: ReasonCode)`.

### Error mapping (`src/execution/bybit/errors.py`)

| retCode | ReasonCode |
|---|---|
| 10002 | CLOCK_DRIFT |
| 10003 | WRONG_API_KEY |
| 10006 | RATE_LIMIT_HIT |
| 10016 | EXCHANGE_MAINTENANCE |
| 110007 | INSUFFICIENT_BALANCE |
| 110017 / 170131 / 170140 / 170213 | FILTER_VIOLATION |
| other | UNKNOWN_ERROR |

## Key properties

- **MARKET only** в v0.1 (per migration-plan).
- **client_order_id ≡ orderLinkId** (Bybit terminology).
- **Spot category hardcoded** — linear (perps) добавляется v0.2 через расширение, не modification.

## Sprint 5 extension — `tpslMode` for OCO bracket

Per ADR 0019 sub-decision 1 (native Bybit `tpslMode=Full`, not emulated):

```python
order = adapter.place_market_order(
    client_order_id=cid,
    side=OrderSide.BUY,
    qty=Decimal("0.001"),
    reference_price=last_price,
    take_profit=Decimal("75000"),
    stop_loss=Decimal("65000"),
    tpsl_mode="Full",
)
```

Все три kwargs опциональны и keyword-only. Non-OCO путь (без kwargs) byte-identical к pre-S5 поведению. Биржа гарантирует cancel-on-fill для OCO ног.

См. также: [[oco]] (builder для SL/TP уровней).

## Related

- [[../decisions/0016-bybit-spot-supersedes-binance]] — error-map таблица.
- [[../architecture/bounded-contexts]] — Execution ACL.
- [[models]] — `Order`, `OrderSide`, `OrderType`, `OrderStatus`.
- [[../../trading/concepts/reason-codes]] — 31 codes, subset покрыт v0.1.

## Sources

- `src/execution/bybit/adapter.py`, `src/execution/bybit/errors.py`.
- Тесты: `test_bybit_adapter.py` (4), `test_bybit_errors.py` (7).
