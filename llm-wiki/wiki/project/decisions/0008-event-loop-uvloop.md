---
title: 0008. Event loop: uvloop
type: decision
tags: [adr, v0.1, async, performance, event-loop]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0008. Event loop: uvloop

**Status:** Accepted
**Date:** 2026-04-19

## Context
Бот — I/O-bound приложение: WebSocket подписки на стаканы/трейды, REST-запросы,
писатели в SQLite/Parquet. Стандартный `asyncio` event loop работает, но даёт
значимый overhead. Хотя v0.1 на 1H-таймфрейме формально не нуждается
в производительности, замена одной строкой bootstrap даёт бесплатный запас.

## Decision
We will use `uvloop` (libuv-based) в качестве дефолтной политики asyncio
event loop на Linux/macOS. Подключение — один вызов `uvloop.install()` в
entry-point. Windows остаётся на default-loop (uvloop не поддерживает).

## Consequences
- (+) ~105K req/s на 1KiB payload на одном ядре (MagicStack benchmarks) —
  5+ порядков запаса над 1 event/hour.
- (+) Меньше latency jitter на WebSocket-потоках.
- (+) Zero API changes — весь async-код остаётся прежним.
- (−) Windows-поддержки нет → dev на Windows использует default loop (ok для MVP).
- (−) Трейсбеки иногда на libuv, не всегда user-friendly.
- (0) При переходе на trio/anyio uvloop не нужен, но мы остаёмся на asyncio.

## Alternatives considered
- Default asyncio loop: отвергнуто — без выгоды, когда uvloop бесплатен.
- trio: отвергнуто — другая модель (structured concurrency), больше rework,
  уже экосистемы драйверов.
- anyio: рассматривался — полезен как уровень абстракции, но не даёт perf.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §3
- uvloop benchmarks: https://magic.io/blog/uvloop-blazing-fast-python-networking/
- See [[0002-python-only-for-mvp]]
