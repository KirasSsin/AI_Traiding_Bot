---
title: 0012. 4-phase Kelly sizing
type: decision
tags: [adr, v0.1, sizing, kelly, risk]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0012. 4-phase Kelly sizing

**Status:** Accepted
**Date:** 2026-04-19

## Context
Full-Kelly на малой выборке (n < 100 сделок) даёт огромные доверительные
интервалы на win-rate/edge: Wilson 95% CI для p=0.55, n=30 — это примерно
[0.37, 0.72]. Использовать точечные оценки как вход в Kelly = практически
гарантировать over-betting и просадку > 50%. Нужна схема, растущая от
фиксированного консервативного размера к Kelly по мере накопления статистики.

## Decision
We will use 4-фазную схему sizing'а как функцию числа закрытых сделок `n`
в стратегии:
- **Phase 1** (`n < 30`): fixed **1%** от equity на сделку.
- **Phase 2** (`30 ≤ n < 100`): fixed **2%**.
- **Phase 3** (`100 ≤ n < 200`): **Quarter-Kelly** (f* · 0.25), hard cap **3%**.
- **Phase 4** (`n ≥ 200`): **Half-Kelly** (f* · 0.5), hard cap **5%**.
f* пересчитывается по rolling-окну последних 200 сделок; win-rate и payoff —
с Wilson lower bound на 95% CI для консервативной оценки.

## Consequences
- (+) Защита от over-betting на малой выборке (Wilson CI диктует phases 1–2).
- (+) Плавный переход к Kelly без "обрыва" в момент n=100.
- (+) Hard caps (3%, 5%) защищают от ошибок калибровки и fat-tails.
- (+) Мягко совместимо с circuit-breaker'ами (L1/L2/L3) — sizing режется
  дополнительно в drawdown.
- (−) Дополнительная state-переменная `n_trades` per-strategy — храним в SQLite.
- (−) Параметры (пороги 30/100/200, caps) требуют явного обоснования в configs.

## Alternatives considered
- Full-Kelly с первого дня: отвергнуто — катастрофа на малой выборке.
- Fixed fractional (e.g. 2% всегда): отвергнуто — оставляет edge на столе
  при зрелой стратегии.
- Непрерывная функция `f(n)`: отвергнуто — сложнее объяснить и проверить.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §5
- Kelly J.L., "A New Interpretation of Information Rate" (1956)
- Thorp E., "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market" (1997)
- Wilson E.B., "Probable Inference, the Law of Succession, and Statistical Inference" (1927)
- See [[0013-circuit-breakers-l1-l2-l3-flash]]
