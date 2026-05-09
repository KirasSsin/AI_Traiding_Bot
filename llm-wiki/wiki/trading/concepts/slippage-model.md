---
title: Slippage Model — sqrt + fixed 5 bps
type: concept
tags: [slippage, execution, market-impact, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §2 item 1]
---

# Slippage Model

**TL;DR:** Для v0.1 orders <$10k — fixed 5 bps (консервативный placeholder). Для больших orders — sqrt `κ·σ·√(Q/V)` с κ=0.1 (Almgren, Donier-Bonart). Квадратичная Q²-модель **отвергнута** как эмпирически и теоретически неверная.

## Формулы

### Fixed 5 bps (MVP default)

```
slippage = 5 bps = 0.0005
fill_price = decision_price · (1 + slippage · sign(side))
```

Где `sign(side)` = +1 для BUY, −1 для SELL.

Применяется когда:
- Order notional < $10,000, **или**
- Order qty < 0.1% ADV (average daily volume).

**Почему 5 bps:** эмпирическая верхняя граница для liquid BTC-USDT market orders на Binance при обычной volatility. Консервативен → в реальности чаще меньше, что не вредит backtest результатам.

### Square-root model (v0.2+ / больших orders)

```
slippage = κ · σ · √(Q / V)
```

Где:
- `κ = 0.1` (эмпирический коэффициент, калибруется на 200+ реальных fills).
- `σ` = current volatility (realized over last N bars, e.g., 1 hour).
- `Q` = order quantity в базовой валюте.
- `V` = 1-day rolling volume.

**Применяется при:**
- Order notional > $50,000, **или**
- Order qty > 0.1% ADV.

## Почему sqrt, не Q²

**Empirical evidence (rejects Q²):**
- Almgren, Thum, Hauptmann, Li (2005) — on 700K trades equity data: β ≈ 0.6 для exponent `Q^β`. **Не 2.0**.
- Donier, Bonart (2015) — **1M+ BTC метазаказов**: β ≈ 0.5. Линейно для малых Q, sqrt для больших.
- Gatheral (2010) — **no-arbitrage теорема:** permanent price impact **должен быть линейным** или вогнутым. Quadratic impact нарушает no-arbitrage.

**Интуиция:** если impact = Q², то round-trip (купить Q, продать Q) создаёт quadratic loss независимо от времени. Это означает money pump → арбитражеры эксплуатируют → impact коллапсирует к линейному/sqrt.

**Квадратичная модель в предыдущих спеках** была scratch-guess Qwen и ChatGPT без эмпирического обоснования. Отвергнута.

## Калибровка κ

После 200+ реальных fills:
```
κ_estimated = mean_slippage_bps / (σ · √(Q/V))
```

Сравниваем с теоретическим 0.1 (Almgren). Если emprical κ > 0.2 — пересматриваем execution logic (market orders vs. IOC limit, smart order routing).

## Permanent vs temporary impact

- **Temporary impact** — price return к pre-trade level после исполнения (наш order "затратил" ликвидность).
- **Permanent impact** — structural shift в consensus price (information component).

Для single-symbol bot на 1H таймфрейме разницу обычно игнорируем — оба merge в одну "slippage cost". При L2-strategy (v0.3+) разделение становится важным.

## Backtest implementation

```python
def apply_slippage(decision_price: float, side: str, qty: float, volume: float, sigma: float) -> float:
    notional = qty * decision_price
    if notional < 10_000:
        slippage_bps = 5.0
    elif notional > 50_000 or qty > 0.001 * volume:
        slippage_bps = 10_000 * 0.1 * sigma * (qty / volume) ** 0.5
    else:
        # Hybrid zone $10k-$50k — linear interpolation
        slippage_bps = 5.0 + (notional - 10_000) / 40_000 * 10.0
    sign = 1 if side == "BUY" else -1
    return decision_price * (1 + slippage_bps / 10_000 * sign)
```

## Fee model (complement)

Binance Spot fees (с учётом BNB burn): maker 0.075% (~7.5 bps), taker 0.100% (10 bps). MARKET orders = taker.

Total cost v0.1: `2 × 10 bps (fees) + 5 bps (slippage) = 25 bps per round-trip`.

## Sources

- Almgren, Chriss (2000) "Optimal execution of portfolio transactions" *J. Risk* 3(2):5–39, §1.3–1.5.
- Almgren, Thum, Hauptmann, Li (2005) "Direct estimation of equity market impact" *Risk* 18(7):58–62, §3.2.
- Donier, Bonart (2015) "A million metaorder analysis of market impact on the Bitcoin" *Market Microstructure and Liquidity* 1(2):1550008.
- Gatheral (2010) "No-dynamic-arbitrage and market impact" *Quantitative Finance* 10(7):749–759.
- Kissell (2013) *The Science of Algorithmic Trading and Portfolio Management* Ch.5.

## Related

- [[../../project/architecture/execution-timing]] — slippage применяется в fill simulation.
- [[../../project/decisions/0010-sqrt-slippage-model]] — ADR.

## Реализация

- [[../../project/components/sizing]] — notional от `compute_qty` определяет режим slippage (fixed 5bps vs sqrt)
- [[../../project/components/strategy]] — signal timing (close T → fill open T+1) задаёт точку применения slippage
