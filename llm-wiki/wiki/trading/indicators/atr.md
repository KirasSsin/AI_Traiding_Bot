---
title: ATR (Average True Range)
type: indicator
tags: [trading, indicator, volatility, atr, wilder, risk-management]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md, Wilder 1978]
---

# ATR (Average True Range)

**TL;DR:** ATR — мера волатильности в абсолютных ценовых единицах; в v0.1 задаёт размер стоп-лосса, тейк-профита и позиции.

## Definition
ATR (Average True Range), Wilder (1978) — сглаженное среднее истинного диапазона (True Range) за n баров. Показывает типичный размер движения бара с учётом гэпов.

Формула:
```
TR[t] = max(
    H[t] − L[t],
    |H[t] − C[t−1]|,
    |L[t] − C[t−1]|
)

ATR = Wilder_EMA(TR, n)
```

Параметр по умолчанию: **n = 14** (канон Уайлдера).

Диапазон значений: **ATR > 0**, выражается в абсолютных единицах цены (для BTC/USDT — в USDT). Это **не процент** и не нормированная величина.

## Formula variants (важно!)
ATR Уайлдера использует **Wilder EMA** (α = 1/n):
- Для n = 14: α = 1/14 ≈ 0.0714.
- Seed: `ATR[n−1] = SMA(TR[1..n])`, далее рекурсивно.
- Эквивалент Classical: Wilder(14) ≈ Classical(27).

Если посчитать «ATR через Classical EMA(14)» — получим реакцию вдвое быстрее и другой числовой ряд; в v0.1 используем строго Wilder. См. [[./ema]] про разницу вариантов.

## Interpretation
- ATR растёт → волатильность увеличивается (расширение диапазонов, возможные news-события).
- ATR падает → рынок «сжимается», часто предшествует пробою.
- ATR **не имеет зон overbought/oversold** — это чистая мера волатильности, без направления.
- Сравнение ATR между активами требует нормировки: `ATR% = ATR / Close · 100`.
- На 1H BTC/USDT типичный ATR(14) — порядок 0.2–1.0% от цены в зависимости от режима рынка.
- Резкий скачок ATR → сигнал расширить стопы и/или уменьшить позицию.

## Role in v0.1 strategy
ATR — **основа риск-менеджмента** в стратегии `ema-crossover-adx-rsi`. Сам сигнал не формирует, но определяет размер риска:

- **Stop-loss (SL):**
  - LONG: `SL = entry − 1.5 · ATR(14)`
  - SHORT: `SL = entry + 1.5 · ATR(14)`
- **Take-profit (TP) при RR = 2.0:**
  - LONG: `TP = entry + 3.0 · ATR(14)`
  - SHORT: `TP = entry − 3.0 · ATR(14)`
- **Position sizing:**
  - `size = (risk_per_trade · equity) / (1.5 · ATR)`
  - То есть фиксируем максимальный убыток на сделку в деньгах, а волатильность определяет количество контрактов.

Такой подход делает риск однородным между периодами высокой и низкой волатильности — в шторм позиция меньше, в штиль больше.

## Parameters (v0.1)
- period: **14** (стандарт Wilder)
- variant: **Wilder EMA** (α = 1/14)
- SL multiplier (k_sl): **1.5**
- TP multiplier (k_tp): **3.0** (→ RR = 2.0)
- risk_per_trade: задаётся в конфиге риск-менеджмента (например, 0.5–1% equity)
- source: OHLC (нужны H, L, C_prev)

## Implementation
- TA-Lib: `ATR(high, low, close, timeperiod=14)` — использует Wilder-сглаживание, совпадает с каноном.
- Также доступен `TRANGE(high, low, close)` — сырой TR без сглаживания.
- Warm-up: первый валидный ATR на баре n (индекс n−1).
- pandas-вариант: `ewm(alpha=1/n, adjust=False)` по ряду TR с ручной SMA-инициализацией первых n баров.
- **Ловушка (TA-Lib SF bug #87):** проверять seed — `ATR[n−1] == SMA(TR[1..n])`. Первый TR на баре 0 не определён (нет C_prev), поэтому ряд TR начинается с индекса 1.
- Нормализация для cross-symbol сравнения: `ATR_pct = ATR / Close · 100`.

## Related
- [[../strategies/ema-crossover-adx-rsi]] — основная стратегия v0.1
- [[./ema]] — сигнал направления
- [[./adx]] — фильтр силы тренда (использует TR внутри)
- [[./rsi]] — фильтр перекупленности
- [[../risk/position-sizing]] — детали sizing по ATR (если есть)

## Sources
- Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*. Ch. 4 (Volatility & ATR).
- Kaufman, P. (2013). *Trading Systems and Methods* (5th ed.). Ch. 7, 9.
- Van Tharp, K. (2007). *Trade Your Way to Financial Freedom*. (Position sizing по волатильности.)
- TA-Lib documentation: ATR, TRANGE.
