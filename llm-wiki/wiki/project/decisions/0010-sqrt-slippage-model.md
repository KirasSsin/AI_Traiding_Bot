---
title: 0010. Square-root impact model for slippage
type: decision
tags: [adr, v0.1, execution, slippage, microstructure]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0010. Square-root impact model for slippage

**Status:** Accepted
**Date:** 2026-04-19

## Context
Backtest без реалистичной модели слиппеджа систематически завышает PnL.
Квадратичная (Q²) модель, упомянутая в одном из ревью, противоречит
эмпирическим данным крупных equity/crypto-датасетов: market impact растёт как
корень из размера относительно ADV, не как квадрат. Для мелких ордеров
(ниже порога) стоимость практически фиксирована и доминируется спредом.

## Decision
We will use piecewise модель слиппеджа:
- **Small orders** (notional < $10k или < 0.01% ADV): fixed **5 bps**.
- **Large orders** (notional > $50k или > 0.1% ADV): **square-root impact**
  `Δp/p = κ · σ · sqrt(Q / V)`, где σ — daily vol, Q — размер ордера,
  V — ADV, κ — калибруется на реальных fills (стартовое значение ~0.1–1).
- Между порогами — линейная интерполяция.

## Consequences
- (+) Соответствует эмпирике (Almgren–Chriss 2000, Almgren et al 2005,
  Donier–Bonart 2015).
- (+) Защищает от "toy alpha" — стратегии на больших размерах наказываются адекватно.
- (+) κ легко перекалибровать per-symbol из execution-логов v0.1.
- (−) Требует ежедневную σ и ADV на символ — добавляем в data-pipeline.
- (−) Возможна недооценка при экстремальных регимах (flash-crash) — прикрыто
  circuit-breaker'ами.
- (0) Для v0.2+ возможен переход на transient/permanent decomposition (Gatheral).

## Alternatives considered
- Quadratic (Q²): отвергнуто — противоречит всем известным эмпирическим исследованиям,
  завышает cost для крупных ордеров на порядки.
- Fixed bps only: отвергнуто — неадекватно для ордеров > 0.1% ADV.
- Linear impact (Q): отвергнуто — недооценивает у больших Q, переоценивает у малых.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §2 item 1
- Almgren R., Chriss N., "Optimal Execution of Portfolio Transactions" (2000)
- Almgren R., Thum C., Hauptmann E., Li H., "Direct Estimation of Equity Market Impact" (2005)
- Donier J., Bonart J., "A Million Metaorder Analysis of Market Impact on the Bitcoin" (2015)
- Gatheral J., "No-Dynamic-Arbitrage and Market Impact" (2010)
