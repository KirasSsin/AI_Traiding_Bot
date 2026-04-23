---
title: Execution — Reconciler (post-reconnect state diff)
type: component
tags: [execution, reconciler, ws-reconnect, sprint-5, sprint-6, adr-0020]
created: 2026-04-23
updated: 2026-04-23
sources: [src/execution/reconciler.py, tests/unit/test_reconciler_fetch.py, tests/unit/test_reconciler_diff.py, project/decisions/0019-sprint-5-execution-decisions.md, project/decisions/0020-sprint-6-execution-spot-oco-emulation.md]
status: stable
---

# Execution — Reconciler

**TL;DR:** После WS reconnect фечит exchange state (open orders + position) и diff'ит против local FSM row. На расхождении — `RECONCILE_DIVERGENCE` → `HALT_RECONCILE_DIVERGENCE`.

## Definition / Purpose

После разрыва WebSocket-соединения локальный FSM может «отстать» от реального состояния биржи. Reconciler реализует подход reconcile-as-truth: exchange wins. SQLite служит warm-cache для быстрого старта, но при расхождении exchange-данные имеют приоритет. Coordinator (Task 8) использует вердикт Reconciler'а для обновления SQLite и FSM.

## Interface

```python
reconciler = Reconciler(client: ExchangeQueryClient)
state: ExchangeState = reconciler.fetch_exchange_state(symbol)
result: ReconcileResult = reconciler.reconcile(symbol, local: ExecutionStateRow | None)
# result.verdict in {ReconcileVerdict.OK, ReconcileVerdict.DIVERGENCE}
```

## Key properties

- `ExchangeQueryClient` — Protocol с `get_open_orders(symbol)` и `get_position(symbol)`. Конкретная реализация инжектится Coordinator'ом (Task 8) — для Bybit Spot v0.1 wrapper над `_http.get_open_orders` + `_http.get_wallet_balance`.
- Diff rules (v0.1 LONG-only):
  - Нет local row + exchange flat → OK.
  - Local in flat-set (FLAT/INIT/COOLDOWN/KILLED) + exchange flat → OK.
  - Local active + qty diff > `Decimal("1e-8")` → DIVERGENCE.
  - Local has `oco_main_order_id` + exchange не содержит matching `orderId` → DIVERGENCE.
- Reconciler НЕ пишет в SQLite сам — это делает Coordinator (exchange wins per ADR 0019).

## v2 (Sprint 6, ADR 0020)

### Protocol `ExchangeQueryClient` — без `get_position`

ADR 0020 sub-decision 4: Bybit Spot V5 не предоставляет endpoint `get_position`. Протокол `ExchangeQueryClient` теперь требует только два метода:

```python
class ExchangeQueryClient(Protocol):
    def get_wallet_balance(self, *, coin: str) -> WalletSnapshot: ...
    def get_open_orders(self, *, symbol: str) -> list[dict]: ...
```

`get_wallet_balance(coin=BTC)` — канонический источник истины о позиции. Возвращает `WalletSnapshot(coin, wallet_balance, available, locked)`.

### Пылевой порог (`dust_threshold`)

`derive_position_qty(state: ExchangeState) -> Decimal` применяет `dust_threshold` (по умолчанию `Decimal("0.00001")` BTC): если `wallet_balance < dust_threshold`, позиция считается FLAT. Это исключает фантомную позицию из-за накопленных округлений.

### Разделение ответственности: qty vs entry_price

Exchange владеет qty (wallet balance), локальный SQLite — entry_price:
- На вердикте AGREE: entry_price сохраняется из local state.
- На вердикте DIVERGENCE: entry_price сбрасывается в `None`, рекомендован HALT.

### `ReconcileResult` v2

Добавлены поля (реальные имена из `src/execution/reconciler.py`):

```python
@dataclass(frozen=True, slots=True)
class ReconcileResult:
    verdict: str                          # "AGREE" | "DIVERGENCE"
    position_qty: Decimal                 # exchange truth
    entry_price: Decimal | None           # preserved on AGREE, None on DIVERGENCE
    open_order_link_ids: tuple[str, ...]
    recommended_state: str | None = None  # на DIVERGENCE → "HALTED"
    halt_reason: str | None = None        # на DIVERGENCE → "HALT_RECONCILE_DIVERGENCE"
```

На DIVERGENCE: `recommended_state="HALTED"`, `halt_reason="HALT_RECONCILE_DIVERGENCE"`.

### Изменения в сигнатуре `Reconciler.__init__`

```python
Reconciler(
    *,
    query: ExchangeQueryClient,
    base_coin: str,
    symbol: str,
    dust_threshold: Decimal = Decimal("0.00001"),
)
```

`fetch_exchange_state()` теперь без аргументов (symbol и coin хранятся в `__init__`).

## Related

- `[[../decisions/0019-sprint-5-execution-decisions]]` — sub-decision 3 (Reconcile-as-truth).
- `[[../decisions/0020-sprint-6-execution-spot-oco-emulation]]` — sub-decision 4 (wallet balance truth, no get_position).
- `[[execution-state-machine]]` — события `RECONCILE_OK` / `RECONCILE_DIVERGENCE`.
- `[[oco]]` — builder SL/TP уровней, связан с reconcile bootstrap.
- `[[../../trading/concepts/reason-codes]]` — `HALT_RECONCILE_DIVERGENCE`.
- `[[bybit-rest]]` — источник данных (через `_http`).

## Sources

- `src/execution/reconciler.py`, `tests/unit/test_reconciler_{fetch,diff}.py`.
