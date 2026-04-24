---
title: RuntimeManager
type: component
tags: [runtime, orchestration, lifecycle, sprint-8a]
created: 2026-04-24
updated: 2026-04-24
sources:
  - wiki/project/decisions/0022-sprint-8a-live-runtime.md
status: stable
---

# RuntimeManager

**TL;DR:** Owns process lifecycle: bootstrap → start WS consumer → tick loop (kill→alive→poll→strategy→bracket) → graceful shutdown. Single thread + pybit thread; lock policy on Coordinator/Reconciler protects shared FSM row.

## Definition / Purpose

Файл: `src/runtime/manager.py`. Class `RuntimeManager` — единая точка входа для live-runtime'а v0.1. До S8a Coordinator/Reconciler/FSM работали только в unit-test fixtures (см. ADR 0022 Context).

## Public API

```python
class RuntimeManager:
    def __init__(
        self,
        *,
        coordinator: Coordinator,
        reconciler: Reconciler,
        ws_consumer: BybitPrivateWSConsumer,
        bar_source: BarSource,
        strategy: Strategy,
        settings: Settings,
        risk_manager: RiskManager,
    ) -> None: ...

    def run(self) -> None: ...                    # blocking; main entry
    def shutdown(self, *, reason: str) -> None: ... # graceful drain (idempotent)
```

## Lifecycle

```
run()
  ├─ unlink stale .kill_switch (if present)
  ├─ coordinator.bootstrap()        ← sequencing invariant (S7 sub-decision 1)
  ├─ ws_consumer.start()
  ├─ try:
  │     _main_loop()                ← while not _stopping: _tick(); sleep(cadence)
  │   except KeyboardInterrupt:
  │     _shutdown(reason=KEYBOARD_INTERRUPT)
  │   except Exception:
  │     coordinator.request_halt(HALT_RUNTIME_CRASH)
  │     _shutdown(reason=HALT_RUNTIME_CRASH)
  │     raise
  │   else:
  │     _shutdown(reason=NORMAL_EXIT)
```

## Tick pipeline (sequential, single-thread)

```
_tick()
  1. _maybe_kill_switch        → if .kill_switch exists: request_halt(KILL_SWITCH_REQUESTED), _stopping = True
  2. _check_alive_inline       → ws.check_alive(max_silence=settings.runtime_ws_check_alive_max_silence)
  3. _poll_bar_and_strategy    → bar = bar_source.poll(); if should_halt: request_halt(HALT_BAR_POLL_STALL)
                                 if bar: signal = strategy.on_bar(bar)
                                 FSM pre-check: row.state == FLAT (else skip — one-open-order invariant)
                                 risk_manager.assess(signal, mark_price=bar.close) → assessment
                                 if assessment.approved: coord.start_bracket(entry_qty=, entry_side=, tp_price=, sl_trigger_price=)
```

## Lock policy reference

Все публичные методы Coordinator (6 шт.) и Reconciler (2 шт.) обёрнуты thread-safe locks (RLock на Coordinator, Lock на Reconciler) — см. ADR 0022 sub-decision 1. Это защищает от race между pybit thread (`on_order_event` / `on_wallet_event`) и main thread (`start_bracket` / `flatten` / `bootstrap`).

| Component | Lock type | Methods wrapped |
|---|---|---|
| Coordinator | `threading.RLock` (reentrant) | bootstrap, start_bracket, on_order_event, on_ws_reconnect, arm_oco, flatten, request_halt |
| Reconciler | `threading.Lock` (non-reentrant) | on_wallet_event, reconcile |

## Structlog event vocabulary (v0.1)

| Event | Fields |
|---|---|
| `runtime.start` | symbol, settings_hash |
| `runtime.bootstrap_complete` | fsm_state, halt_reason |
| `runtime.ws_disconnect` | silence_seconds, action |
| `runtime.bar_tick` | bar_close_ts, last_seen_ts |
| `runtime.bar_poll_stall` | consecutive_failures, threshold |
| `runtime.kill_switch_detected` | sentinel_path |
| `runtime.crash` | exc_type, exc_msg |
| `runtime.shutdown` | reason, in_flight_orders |

## Related

- [[bar-poller]] — REST kline source feeds tick loop
- [[ws-private-consumer]] — pybit thread side; check_alive called inline from tick
- [[execution-state-machine]] — KILL_SWITCH_REQUESTED transitions
- [[reconciler]] — wallet events via on_wallet_event
- [[../runbooks/halt-recovery]] — HALT_RUNTIME_CRASH / HALT_BAR_POLL_STALL / KILL_SWITCH_REQUESTED post-mortem

## Open questions

- WS consumer dedicated health check threshold (separate from bar poller) — S8b/S9.
- Multi-symbol / multi-bracket — lock granularity re-evaluation.
- async/await migration — S9+.

## Sources

- [[../decisions/0022-sprint-8a-live-runtime]] — все 14 sub-decisions
