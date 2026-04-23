---
title: Execution — Reconciler (post-reconnect state diff)
type: component
tags: [execution, reconciler, ws-reconnect, sprint-5]
created: 2026-04-23
updated: 2026-04-23
sources: [src/execution/reconciler.py, tests/unit/test_reconciler_fetch.py, tests/unit/test_reconciler_diff.py, project/decisions/0019-sprint-5-execution-decisions.md]
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

## Related

- `[[../decisions/0019-sprint-5-execution-decisions]]` — sub-decision 3 (Reconcile-as-truth).
- `[[execution-state-machine]]` — события `RECONCILE_OK` / `RECONCILE_DIVERGENCE`.
- `[[../../trading/concepts/reason-codes]]` — `HALT_RECONCILE_DIVERGENCE`.
- `[[bybit-rest]]` — источник данных (через `_http`).

## Sources

- `src/execution/reconciler.py`, `tests/unit/test_reconciler_{fetch,diff}.py`.
