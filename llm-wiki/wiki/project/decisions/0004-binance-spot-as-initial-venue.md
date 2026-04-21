---
title: 0004. Binance Spot as initial venue
type: decision
tags: [adr, v0.1, venue, exchange, binance, superseded-by-0016]
created: 2026-04-19
updated: 2026-04-21
status: superseded
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0004. Binance Spot as initial venue

> Superseded on 2026-04-21 by ADR 0016. Retained for historical context — do not follow as current guidance.

**Status:** Superseded by [[0016-bybit-spot-supersedes-binance]] (2026-04-21)
**Date:** 2026-04-19

## Context
Для v0.1 нужна единственная площадка: фокус на end-to-end pipeline, не на
адаптер-зоопарк. Требования: высокая ликвидность (узкие спреды для sqrt-модели
слиппеджа), документированный REST+WebSocket API, testnet для paper-trading,
широкий универс пар, zero-fee на часть пар.

## Decision
We will use Binance Spot в качестве единственной venue для v0.1. Интеграция
через `python-binance` (или прямой httpx+websockets). Testnet
(`testnet.binance.vision`) — для paper-trading и CI smoke-tests. Mainnet —
только после прохождения all gates (walk-forward + MC permutations, circuit
breakers).

## Consequences
- (+) Высочайшая ликвидность spot-рынка → sqrt-модель слиппеджа применима.
- (+) Бесплатный testnet с полноценным API — честное paper-trading.
- (+) Стабильный, документированный API с rate-limit в заголовках.
- (−) Жёсткая завязка на одного провайдера — regulatory risk (US/UK).
- (−) Rate-limits (1200 req/min weighted) — решается локальным bucket'ом.
- (0) Абстракция `Exchange` port всё равно нужна для тестируемости — добавление
  второй venue (OKX/Bybit) будет стоить только адаптер.

## Alternatives considered
- Binance Futures USDT-M: отвергнуто для v0.1 — funding-rate, маржинальные риски,
  ликвидация. Вернёмся в v0.2+.
- Bybit / OKX: отвергнуто — хороший API, но нет выигрыша для MVP, больше
  фрагментации ликвидности в тесте.
- Coinbase Pro: отвергнуто — меньший универс, хуже для alt-coins.
- Мультивенью сразу: отвергнуто (YAGNI) — усложняет execution и reconciliation.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §3, §11
- Binance API docs: https://binance-docs.github.io/apidocs/spot/en/
- See [[0010-sqrt-slippage-model]]
