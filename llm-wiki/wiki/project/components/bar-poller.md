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

## Публичный API

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

### Supported intervals

`BarSource.__init__` validates the `interval` parameter against the 13 Bybit
V5 kline strings: `{"1", "3", "5", "15", "30", "60", "120", "240", "360",
"720", "D", "W", "M"}`. Unknown values raise `ValueError` at construction
(fail-fast vs. previous KeyError on first poll). v0.1 only uses `"60"` (1H);
the dict is the source of truth for any future call-site (S8b T2 fix).

No `Settings.bar_interval` field — interval is passed at construction by the
caller. YAGNI per trader-expert verdict 2026-04-24.

## Связанные

- [[runtime-manager]] — owner of poll cadence + halt emission
- [[bybit-adapter]] — REST kline endpoint wrapper
- [[bybit-rest]] — underlying REST client used by adapter for kline calls
- [[bar-builder]] — WS-based alternative that builds Bar from kline messages (venue-agnostic)
- [[../decisions/0022-sprint-8a-live-runtime]] — sub-decisions 2 + 3
- [[../runbooks/halt-recovery]] — operator runbook covering HALT_BAR_POLL_STALL (Operational class group)
- [[../sprints/sprint-08a-live-runtime]] — sprint where bar-poller (BarSource) was created
- [[../architecture/execution-timing]] — timing invariants (isClosed gate + bar-to-signal sequence).

## Sources

- [[../decisions/0022-sprint-8a-live-runtime]]
