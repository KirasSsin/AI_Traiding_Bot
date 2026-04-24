---
title: Execution — Bybit Private WS Consumer
type: component
tags: [execution, websocket, bybit, sprint-7, adr-0021]
created: 2026-04-24
updated: 2026-04-24
sources: [src/execution/bybit/ws_private.py, tests/unit/test_ws_private_consumer.py, project/decisions/0021-sprint-7-resilience.md]
status: stable
---

# Execution — Bybit Private WS Consumer

**TL;DR:** Passive consumer Bybit V5 private stream (`order` + `wallet` topics) на pybit `unified_trading.WebSocket`. ADR 0021 sub-decision 6 — wire on_disconnect через underlying `WebSocketApp.on_close` close-hook + heartbeat watchdog (`check_alive`) как backstop.

## Definition / Purpose

Bybit private WS поставляет два потока, нужных coordinator'у/reconciler'у:

- **`order` topic** — статусы ордеров (New / PartiallyFilled / Filled / Cancelled / Triggered) с `cumExecQty` / `cumExecFee` / `feeCurrency` / `avgPrice`.
- **`wallet` topic** — обновления `walletBalance` (canonical source of truth for Spot position; ADR 0020 sub-decision 4).

Consumer **не управляет торговлей** — только парсит и форвардит coordinator'у/reconciler'у. Driver loop отнесён в S8 (B1 narrow scope).

## Interface

```python
consumer = BybitPrivateWSConsumer(
    api_key="...",
    api_secret="...",
    endpoint="wss://stream-demo.bybit.com/v5/private",
    coordinator=coord,    # реализует on_order_event(evt) + on_ws_reconnect()
    reconciler=reco,      # реализует on_wallet_event(evt)
)
consumer.start()           # subscribe к order + wallet topics
consumer.check_alive()     # backstop watchdog, периодический вызов
consumer.stop()
```

## Disconnect detection (ADR 0021 sub-decision 6)

pybit **не предоставляет** user-level disconnect callback. Consumer комбинирует два независимых пути:

### Path 1 — close-hook на underlying `WebSocketApp`

`_install_close_hook()` после `start()` оборачивает inner `ws.on_close` (websocket-client) callback'ом, который вызывает `on_disconnect()` → `coordinator.on_ws_reconnect()`. Try/except защищает от breaking change в pybit layout.

### Path 2 — heartbeat watchdog (`check_alive`)

Backstop. Периодический worker зовёт `check_alive(max_silence_seconds=30.0)`:

```python
def check_alive(self, *, max_silence_seconds: float = 30.0) -> bool:
    if self._ws is None:
        return False
    last = getattr(self._ws, "last_ping_time", None)
    if last is None:
        return True   # baseline ещё не установлен
    if time.time() - float(last) > max_silence_seconds:
        self.on_disconnect()
        return False
    return True
```

Если pybit upgrade сломает close-hook — silence-based detection всё равно сработает.

## Order parser

`_on_order_raw(msg)` → `_parse_order(item)` → `coordinator.on_order_event(evt)`.

**Critical guard (ADR 0021 sub-decision 6):** для `orderStatus ∈ {Filled, PartiallyFilled}` обязательны `cumExecFee` + `feeCurrency`. Если отсутствуют — ERROR log + drop event (никогда не форвардить `None` fees, иначе `compute_oco_qty` примет zero-fee и оставит pyль на стороне base-coin).

`New` / `Cancelled` / `Rejected` / `Triggered` — fees не ожидаются, событие пробрасывается как есть.

## Wallet parser

`_on_wallet_raw(msg)` → диспатчит каждый `coin`-row отдельно через `reconciler.on_wallet_event({"coin": ..., "walletBalance": ...})`. Multi-coin обновления (например, `BTC` + `USDT`) приводят к двум вызовам.

## Endpoint pinning

Endpoint URL содержит маркер площадки:

| URL substring | Mode | pybit kwargs |
|---|---|---|
| `testnet` | testnet | `testnet=True` |
| `demo` | demo mainnet | `demo=True` |
| ни тот ни другой | mainnet | оба False |

## Known limitations

- **Threading модель — pybit-внутренняя.** Consumer не контролирует worker thread напрямую; pybit отдельный поток на канал.
- **Driver loop отсутствует в v0.1.** B1 narrow scope (passive consumer); orchestration `check_alive` worker отнесён в S8 вместе с runtime entry-point.
- **Reconnect — внешняя ответственность.** `on_ws_reconnect` лишь триггерит coordinator → reconciler. Сам пере-подключиться pybit'ом не управляем (он сам ретраит).

## Invariants (CRITICAL — verified by tests + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | Order events with `orderStatus ∈ {Filled, PartiallyFilled}` MUST have `cumExecFee + feeCurrency` — missing → ERROR log + drop (never forward None fees to `compute_oco_qty`) | `src/execution/bybit/ws_private.py` mandatory-field guard + ADR 0021 sub-decision 8 | `tests/unit/test_ws_private_consumer.py` |
| 2 | Dual reconnect paths (close-hook + heartbeat watchdog) — one path failing doesn't kill reconnect | `src/execution/bybit/ws_private.py` close-hook + `check_alive` watchdog + ADR 0021 sub-decision 6 | `tests/property/test_bootstrap_ws_reconnect_idempotent.py` |
| 3 | Passive consumer — routes events to Coordinator/Reconciler, no FSM mutation own | `src/execution/bybit/ws_private.py` (no `_transition` calls) | (architecture rule) |

## Related

- `[[../decisions/0021-sprint-7-resilience]]` — sub-decision 6 (WS-reconnect wiring).
- `[[coordinator]]` — sink: routes order events → `coordinator.on_order_event()`; WS-reconnect → `coordinator.on_ws_reconnect()` (S7 sub-decision 6).
- `[[reconciler]]` — потребитель wallet events + post-reconnect диффер.
- `[[execution-state-machine]]` — `WS_RECONNECT` event consumer.
- `[[bybit-adapter]]` — REST partner (выставляет ордера, consumer слушает их события).
- `[[oco]]` — bracket lifecycle, реагирует на order events.

## Driver loop (S8a closed)

До S8a `BybitPrivateWSConsumer` был passive: `start()` / `stop()` без owner. Sprint 8a (ADR 0022) ввёл [[runtime-manager]] как driver:

- `RuntimeManager.run()` вызывает `ws_consumer.start()` после `coordinator.bootstrap()`.
- `ws_consumer.check_alive(max_silence_seconds=...)` вызывается **inline** в каждом tick'е main thread'а — НЕ из отдельного worker thread (ADR 0022 sub-decision 4 — устраняет same-cadence race с bar-поллером).
- `RuntimeManager._shutdown(reason)` вызывает `ws_consumer.stop()` (idempotent).

См. таблицу lock policy в [[runtime-manager]] — Coordinator-side callbacks (`on_order_event`, `on_ws_reconnect`) acquire `Coordinator._lock` (RLock).

## Sources

- `src/execution/bybit/ws_private.py`
- `tests/unit/test_ws_private_consumer.py` (8 tests: init, on_disconnect, check_alive×2, parser×3, wallet×1)
