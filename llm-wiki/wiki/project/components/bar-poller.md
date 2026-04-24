---
title: BarSource (REST kline poller)
type: component
tags: [runtime, marketdata, polling, sprint-8a]
created: 2026-04-24
updated: 2026-04-24
sources:
  - wiki/project/decisions/0022-sprint-8a-live-runtime.md
status: stable
---

# BarSource (REST kline poller)

**TL;DR:** REST `kline` poller (5s cadence). Возвращает последний closed bar если новый, иначе None. Дедупликация по `close_time`. После N consecutive failures предикат `should_halt(threshold)` возвращает True — RuntimeManager эмитит `HALT_BAR_POLL_STALL`.

## Definition / Purpose

Файл: `src/runtime/bar_source.py`. Заменяет absent driver loop: до S8a kline данные читали только batch-скрипты backfill'а. Live-runtime требует tick-source.

## Public API

```python
class BarSource:
    def __init__(self, *, adapter, symbol: str, interval: str = "60") -> None: ...
    def poll(self) -> Bar | None: ...
    def should_halt(self, *, threshold: int) -> bool: ...
    consecutive_failures: int  # public read-only counter
```

## Why REST, not WS kline

WS kline streams **partial** bar updates (open bar). Для close-on-close signal (look-ahead invariant) нужны только closed bars. REST дёшев: 1 req/5s = 720 req/час, c большим запасом до Bybit rate limit (600 req/min). WS добавил бы async loop без выигрыша в latency на 1H timeframe (см. ADR 0022 sub-decision 2).

## Dedup invariant

`_last_close_ts` хранит ms epoch последнего emit'нутого bar'а. Если поллер видит `close_time <= _last_close_ts` — возвращает None. Это защищает от duplicate `strategy.on_bar(bar)` вызовов.

## Stall semantics

| Counter state | Action |
|---|---|
| 0 | normal (last poll OK) |
| 1..threshold-1 | tolerated (transient REST failure) |
| ≥ threshold (default 24) | `should_halt(threshold) → True` → RuntimeManager emits `HALT_BAR_POLL_STALL` |

При успешном poll'е counter сбрасывается в 0 (recovery).

## Threshold validation rules

`runtime_bar_poll_stall_threshold` validator: 6 ≤ N ≤ 720.
- 6 (= 30s) — false-halt floor (короче — слишком чувствительно к 1-2 transient hiccup'ам Bybit)
- 720 (= 1 bar period @ 5s cadence) — потолок (дольше = bar-poller stall переходит границу bar close → mid-bar fill possible).

Default 24 (= 120s = 3.3% от 3600s bar period). Trader-expert verdict: stall ≠ position-safety (OCO bracket exchange-side; WS consumer routes order events независимо). False-halt cost dominates → 24 better balances 12 (см. ADR 0022 Alt-5).

## Halt class annotation

`HALT_BAR_POLL_STALL` — **signal-pipeline halt class**, not execution-safety.

## Documented degradation: mid-bar fill

Stall длиной > 30 минут перед close может вызвать **mid-bar fill** вместо open fill (RuntimeManager пропустит close moment, signal эмитится позже на следующем tick'е после recovery). Это **slippage**, не correctness violation. Monitored через structlog `runtime.bar_poll_stall` event с полем `consecutive_failures`. Подробнее: [[../architecture/risk-register]] → POLL_STALL_MID_BAR_FILL scenario.

## Related

- [[runtime-manager]] — owner of poll cadence + halt emission
- [[bybit-adapter]] — REST kline endpoint wrapper
- [[../decisions/0022-sprint-8a-live-runtime]] — sub-decisions 2 + 3

## Sources

- [[../decisions/0022-sprint-8a-live-runtime]]
