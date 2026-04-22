---
title: 0013. Circuit breakers L1/L2/L3 + flash
type: decision
tags: [adr, v0.1, risk, circuit-breaker, drawdown]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0013. Circuit breakers L1/L2/L3 + flash

**Status:** Accepted
**Date:** 2026-04-19

## Context
Любая стратегия рано или поздно встречает распределение, не представленное
в train-окне: смена регима, экзогенный шок, flash-crash. Без автоматических
"автовыключателей" реализуется классический risk of ruin — даже правильный
sizing не спасает, если стратегия не останавливается при накоплении просадки.

## Decision
We will implement четырёхуровневую систему circuit-breakers на equity-кривой
и баровых движениях (peak-to-trough drawdown считается от historical high):
- **L1 — Warning (DD ≥ 15%)**: предупреждение + **halve sizing** (каждая новая
  позиция × 0.5 до восстановления выше порога).
- **L2 — Halt (DD ≥ 22%)**: остановка открытия новых позиций на **24h**,
  существующие держатся по плану или закрываются вручную.
- **L3 — Full stop (DD ≥ 30%)**: полная остановка, ручной re-enable через
  подтверждённый runbook.
- **Flash (per-bar move)**: если модуль price change за 1 бар превышает
  `max(8%, 3·ATR)` — мгновенный halt на 1 час + alert.
Все пороги — в конфиге, все срабатывания логируются в SQLite (`risk_events`).

## Consequences
- (+) Ограничивает tail risk и дает человеку время вмешаться.
- (+) Совместимо с Kelly sizing (удваивает защиту после 15% DD).
- (+) Flash breaker ловит аномалии, которые DD-метрики не видят на одном баре.
- (−) Ложные срабатывания возможны — phases 1–2 боевого запуска = наблюдение.
- (−) L3 требует runbook'а и человека on-call.
- (0) Пороги подкрепляются аналогом NYSE Rule 7.12 (7%/13%/20% на S&P) —
  адаптировано под более волатильный crypto (15%/22%/30%).

## Alternatives considered
- Только per-trade stop-loss: отвергнуто — не защищает от серии мелких убытков.
- Только годовой stop-out: отвергнуто — слишком поздно, реализует уже потерю.
- Hard VaR-limit: отвергнуто для v0.1 — требует модели распределений;
  вернёмся в v0.2+.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §6
- NYSE Rule 7.12 (Trading Halts Due to Extraordinary Market Volatility)
- See [[0012-4-phase-kelly-sizing]]
