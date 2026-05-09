---
title: 0002. Python-only stack for MVP
type: decision
tags: [adr, v0.1, language, stack, performance]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0002. Python-only stack for MVP

**Status:** Accepted
**Date:** 2026-04-19

## Context
Альтернативные ревью (Qwen, ChatGPT) предлагали гибрид Rust+Python или даже
Rust-only MVP ради "производительности". Фактический профиль нагрузки v0.1:
1-часовой таймфрейм → 8760 баров/год → ~1 событие в час. Мы не HFT. Введение
второго языка удваивает сложность сборки, CI, отладки и онбординга.

## Decision
We will use Python-only stack (asyncio + uvloop + pandas/numpy + pydantic v2) для
всего кода v0.1: data ingest, strategy, risk, execution, backtest. Rust/C++
рассматривается только при переходе к sub-10μs tick-to-trade (не планируется
в v0.1–v0.3).

## Consequences
- (+) Один язык, один toolchain, один debugger — быстрее итерация.
- (+) uvloop даёт ~105K req/s на 1 ядре — 5+ порядков запаса над 1 event/hour.
- (+) Богатая экосистема quant-библиотек (pandas, numpy, scipy, statsmodels).
- (−) CPU-bound участки (MC-пермутации на 2000+ итераций) требуют внимания —
  векторизация numpy или numba при необходимости.
- (−) GIL ограничивает многопоточность — решается через asyncio и multiprocessing.
- (0) Путь к Rust остаётся открытым через PyO3, если понадобится.

## Alternatives considered
- Rust+Python гибрид (Qwen): отвергнуто — 2× сложности сборки без выигрыша
  на 1H-таймфрейме; преждевременная оптимизация (Knuth 1974).
- Rust MVP (ChatGPT): отвергнуто — catastrophic overkill для 8760 events/year,
  блокирует быструю итерацию стратегий.
- Go: отвергнуто — слабая quant-экосистема, нет pandas-аналога.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §3 (Stack), §11
- Knuth D., "Structured Programming with go to Statements" (1974)
- MagicStack uvloop benchmarks — 105K req/s, 1KiB payload, single core
- See [[0008-event-loop-uvloop]]

## Связанные

- [[../sprints/sprint-01-foundation]] — спринт, где Python-стек был материализован
