---
title: Execution — BybitMarketAdapter
type: component
tags: [execution, bybit, adapter, anti-corruption-layer, sprint-5, sprint-6, adr-0020]
created: 2026-04-21
updated: 2026-04-23
sources: [src/execution/bybit/adapter.py, src/execution/bybit/errors.py, tests/unit/test_bybit_adapter.py, tests/unit/test_bybit_errors.py, project/decisions/0020-sprint-6-execution-spot-oco-emulation.md]
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

## Sprint 6 additions (ADR 0020)

### Banned Spot fields

Следующие поля **запрещены** и гвардятся в `place_order` (ADR 0020 sub-decision 3). Bybit Spot V5 отклоняет их с `retCode 170130` (probe v1):

```
tpslMode, takeProfit, stopLoss, tpOrderType, slOrderType, triggerDirection
```

`marketUnit=quoteCoin` — также запрещён: вызывает накопление дрейфа на 16-й знак (probe v2 S2). Адаптер всегда пинит `marketUnit=baseCoin`.

### Новые методы

**`place_limit_order(symbol, side, qty, price, order_link_id) -> OrderAck`**
TP-нога 3-ордерного Spot OCO bracket. Payload: `orderType=Limit, timeInForce=GTC`.

**`place_stop_market_order(symbol, side, qty, trigger_price, order_link_id) -> OrderAck`**
SL-нога Spot OCO. Payload: `orderType=Market, orderFilter=StopOrder, triggerBy=LastPrice`. `timeInForce` **опущен** — Bybit Spot Stop молча перезаписывает `GTC→IOC` (probe v3-D); IOC partial-fills обрабатываются на `EXIT_SL_RESIDUAL`.

**`cancel_order(symbol, order_id) -> CancelResult`**
`retCode 110001` → `CancelResult(cancelled=False, reason_code=REJECT_ORDER_ALREADY_TERMINAL)` — нефатальная гонка с Filled (ADR 0020 sub-decision 6).

**`cancel_all_orders(symbol) -> None`**
Bulk-отмена для flatten-каскада и emergency halt.

**`get_order(symbol, order_id) -> OrderSnapshot`**
Читает `cum_exec_qty / cum_exec_fee / fee_currency / avg_price`. V5 GET `/v5/order/realtime` с `orderId`.

**`get_open_orders(symbol) -> list[dict]`**
V5 GET `/v5/order/realtime` — активные ордера (Untriggered/New/PartiallyFilled). Используется при bootstrap для обнаружения prior-attempt (ADR 0020 sub-decision 9).

**`get_order_history(symbol, limit=50) -> list[dict]`**
V5 GET `/v5/order/history` — терминальные ордера за ~7 дней. Используется при bootstrap (ADR 0020 sub-decision 9).

**`get_wallet_balance(coin) -> WalletSnapshot`**
Канонический источник истины о Spot-позиции (ADR 0020 sub-decision 4). Возвращает `WalletSnapshot(coin, wallet_balance, available, locked)`.

### TIF override note

Bybit Spot Stop молча переписывает `timeInForce=GTC` → `IOC` (probe v3-D). Адаптер полностью опускает `timeInForce` в `place_stop_market_order`; IOC partial-fills обрабатываются на уровне состояния `EXIT_SL_RESIDUAL` в FSM.

## Invariants (CRITICAL — verified by tests + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | Banned-field guard: `tpslMode/takeProfit/stopLoss` → retCode 170130 — fields stripped pre-send | `src/execution/bybit/adapter.py::BybitMarketAdapter.place_order` + ADR 0020 sub-decision 1 | `tests/unit/test_bybit_adapter_spot_guard.py::test_place_market_rejects_banned_spot_fields` |
| 2 | `marketUnit=baseCoin` always — `quoteCoin` causes 16th-decimal drift | `src/execution/bybit/adapter.py::BybitMarketAdapter.place_order` + ADR 0020 sub-decision 3 | `tests/unit/test_bybit_adapter_spot_guard.py::test_place_market_passes_marketunit_basecoin` |
| 3 | SL `timeInForce` omitted — Bybit Spot Stop silently rewrites GTC→IOC | `src/execution/bybit/adapter.py::BybitMarketAdapter.place_stop_market_order` + ADR 0020 sub-decision 6 | (probe-validated) |
| 4 | retCode=110001 on cancel = non-fatal (race with Filled) | `src/execution/bybit/adapter.py::BybitMarketAdapter.cancel_order` + `src/execution/bybit/errors.py` | `tests/unit/test_bybit_adapter_cancel.py::test_cancel_order_already_terminal_returns_reason_code` |

## Related

- [[../decisions/0016-bybit-spot-supersedes-binance]] — error-map таблица.
- [[../decisions/0020-sprint-6-execution-spot-oco-emulation]] — sub-decisions 1, 2, 3, 4, 6, 9.
- [[../decisions/0021-sprint-7-resilience]] — `OrderSnapshot` snake_case fields (S7 reconciler consumer).
- [[../architecture/bounded-contexts]] — Execution ACL.
- [[execution-state-machine]] — `OCO_ARMING`, `EXIT_SL_RESIDUAL`, `EXIT_SIBLING_CANCELLING`.
- [[oco]] — builder SL/TP уровней, использует новые методы адаптера.
- [[ws-private-consumer]] — WS-counterpart (REST adapter + WS consumer пара).
- [[models]] — `Order`, `OrderSide`, `OrderType`, `OrderStatus`.
- [[../../trading/concepts/reason-codes]] — 42 codes, subset покрыт v0.1.

## Sources

- `src/execution/bybit/adapter.py`, `src/execution/bybit/errors.py`.
- Тесты: `test_bybit_adapter.py` (4), `test_bybit_errors.py` (7).
