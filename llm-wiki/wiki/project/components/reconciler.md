---
title: Execution — Reconciler (4-valued verdict, post-reconnect state diff)
type: component
tags: [execution, reconciler, ws-reconnect, sprint-5, sprint-6, sprint-7, adr-0020, adr-0021]
created: 2026-04-23
updated: 2026-04-24
sources: [src/execution/reconciler.py, tests/unit/test_reconciler_fetch.py, tests/unit/test_reconciler_diff.py, tests/unit/test_reconciler_verdicts.py, project/decisions/0019-sprint-5-execution-decisions.md, project/decisions/0020-sprint-6-execution-spot-oco-emulation.md, project/decisions/0021-sprint-7-resilience.md]
status: stable
---

# Execution — Reconciler

**TL;DR:** После WS reconnect фечит exchange state (open orders + wallet) и diff'ит против local FSM row. **S7: 4-valued verdict** (`AGREE` / `DIVERGENCE` / `HEAL_ENTRY_FILLED` / `EXITED`) с `expected_state` hint и `heal_max_age_seconds` cutoff (ADR 0021 sub-decisions 1, 3, 4).

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

### `ReconcileResult` (S7 v3, 4-valued)

```python
@dataclass(frozen=True, slots=True)
class ReconcileResult:
    verdict: str                          # "AGREE" | "DIVERGENCE" | "HEAL_ENTRY_FILLED" | "EXITED"
    position_qty: Decimal                 # exchange truth (wallet)
    entry_price: Decimal | None           # preserved on AGREE; None on DIVERGENCE/HEAL/EXITED
    open_order_link_ids: tuple[str, ...]
    recommended_state: str | None = None  # на DIVERGENCE → "HALTED"
    halt_reason: str | None = None        # на DIVERGENCE → "HALT_RECONCILE_DIVERGENCE" / "HALT_EXIT_RECONCILE_DIVERGENCE"
    expected_state: str | None = None     # hint для coordinator: target state на heal/exit
    heal_context: dict | None = None      # avg_price + cum_exec_fee + fee_currency для bracket reconstruction
```

## S7 — 4-valued verdicts (ADR 0021)

Старый бинарный AGREE/DIVERGENCE приводил к over-halting: WS-разрыв между place + fill для ENTRY_PENDING всегда промотировал в HALTED, даже когда биржа уже подтвердила fill. S7 разделяет 4 случая:

| Verdict | Когда | Coordinator действие |
|---|---|---|
| `AGREE` | exchange и local совпадают | no-op |
| `DIVERGENCE` | local active, exchange flat ИЛИ qty mismatch > dust | `HALTED + halt_reason` (bootstrap или exit) |
| `HEAL_ENTRY_FILLED` | local ENTRY_PENDING + exchange FILLED + age < `heal_max_age_seconds` | Воссоздать bracket: emit `RECONCILE_ENTRY_FILLED`, заполнить `entry_price/cum_exec_fee/fee_currency` из `heal_context`, перейти в OCO_ARMING |
| `EXITED` | local active, exchange flat, exit-индикаторы найдены в order history | `EXIT_RECONCILE_DETECTED` → FLAT |

### `heal_max_age_seconds = 3600`

ADR 0021 sub-decision 4. Heal допустим только если возраст fill < 1 час (period 1H bar). Старее — DIVERGENCE (рынок мог двинуться, OCO-уровни stale, реконструкция небезопасна).

### Entry order id capture (ADR 0021 sub-decision 1)

`Coordinator.start_bracket()` теперь пишет `entry_ack.order_id` в `oco_main_order_id` **до** ожидания filled-эха. Reconciler использует `local.entry_order_id` (через `oco_main_order_id`) для `get_order(order_id=...)` — без этого HEAL-путь был мёртв (нечем было адресовать ордер).

### Изменения в сигнатуре `Reconciler.__init__` (S7)

```python
Reconciler(
    *,
    query: ExchangeQueryClient,
    base_coin: str,
    symbol: str,
    dust_threshold: Decimal = Decimal("0.00001"),
    heal_max_age_seconds: int = 3600,    # S7 ADR 0021 sub-decision 4
)
```

`fetch_exchange_state()` теперь без аргументов (symbol и coin хранятся в `__init__`).

### `OrderSnapshot` field naming (S7)

Адаптер возвращает `OrderSnapshot` с snake_case полями (`order_status`, `avg_price`, `cum_exec_fee`, `fee_currency`). Pre-S7 reconciler использовал camelCase (`status`, `avgPrice`) — путь HEAL_ENTRY_FILLED был сломан runtime'но; зафиксировано финальным domain-review S7.

## Related

- `[[../decisions/0019-sprint-5-execution-decisions]]` — sub-decision 3 (Reconcile-as-truth).
- `[[../decisions/0020-sprint-6-execution-spot-oco-emulation]]` — sub-decision 4 (wallet balance truth, no get_position).
- `[[../decisions/0021-sprint-7-resilience]]` — sub-decisions 1 (bootstrap), 3 (4-valued + EXITED), 4 (heal_max_age=3600).
- `[[execution-state-machine]]` — события `RECONCILE_OK` / `RECONCILE_DIVERGENCE` / `RECONCILE_ENTRY_FILLED` / `RECONCILE_EXITED`.
- `[[oco]]` — builder SL/TP уровней, связан с reconcile bootstrap + entry_order_id capture.
- `[[ws-private-consumer]]` — close-hook + check_alive watchdog → trigger reconcile.
- `[[../../trading/concepts/reason-codes]]` — `HALT_RECONCILE_DIVERGENCE`, `HALT_BOOTSTRAP_AMBIGUOUS`, `HALT_EXIT_RECONCILE_DIVERGENCE`, `EXIT_RECONCILE_DETECTED`.
- `[[bybit-rest]]` — источник данных (через `_http`).

## Sources

- `src/execution/reconciler.py`, `tests/unit/test_reconciler_{fetch,diff}.py`.
