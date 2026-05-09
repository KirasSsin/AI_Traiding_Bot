---
title: EMA (Exponential Moving Average)
type: indicator
tags: [trading, indicator, trend, ema, moving-average]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md, Wilder 1978]
---

# EMA (Exponential Moving Average)

**TL;DR:** экспоненциальная скользящая средняя — взвешенная средняя цены, где свежие бары имеют больший вес; используется для определения направления тренда.

## Definition
EMA (Exponential Moving Average) — скользящая средняя, в которой веса убывают экспоненциально с удалением в прошлое. В отличие от SMA, реагирует быстрее на свежие данные.

Рекуррентная формула:
```
EMA[t] = α · P[t] + (1 − α) · EMA[t−1]
EMA[0] = SMA(P[0..n−1])   # инициализация: простое среднее первых n баров
```

Параметры по умолчанию в стратегии v0.1: **fast = 12, slow = 26** (наследие MACD-defaults).

## Formula variants (важно!)
В мире есть два варианта EMA-сглаживания, и это критично различать:

- **Classical EMA:** α = 2 / (n + 1)
  - Для n = 12: α = 2/13 ≈ 0.1538
  - Для n = 26: α = 2/27 ≈ 0.0741
  - Используется в EMA-crossover, MACD, обычных trend-индикаторах.

- **Wilder EMA:** α = 1/n
  - Используется внутри ADX, RSI, ATR.
  - См. [[./adx]], [[./rsi]], [[./atr]].

Эквивалентность: **Wilder(n) ≈ Classical(2n − 1)**, то есть Wilder(14) ≈ Classical(27).

В индикаторе EMA из данной страницы используется **Classical** вариант (α = 2/(n+1)).

## Interpretation
- Цена выше EMA → восходящий bias; ниже → нисходящий.
- Наклон EMA = направление локального тренда.
- Пересечение fast-EMA снизу вверх через slow-EMA → bullish crossover (golden cross в краткосрочной версии).
- Пересечение fast сверху вниз через slow → bearish crossover (death cross в краткосрочной версии).
- Lag (запаздывание) ≈ (n − 1) / 2 баров. Для EMA(26) это ~12.5 бара (≈ 12.5 часов на 1H-таймфрейме).
- Чем меньше n — тем быстрее реакция, но больше ложных сигналов (whipsaw).

## Role in v0.1 strategy
EMA — ядро trend-direction сигнала в стратегии `ema-crossover-adx-rsi`:

- **LONG signal:** EMA(12) > EMA(26) (fast выше slow).
- **SHORT signal:** EMA(12) < EMA(26).
- **FLAT:** при смене знака crossover.

EMA-crossover даёт сырой сигнал направления, но подтверждается фильтрами [[./adx]] (сила тренда) и [[./rsi]] (избегаем покупок на перекупленности).

Связь с MACD: `MACD_line = EMA(12) − EMA(26)` — та же логика, но выраженная через разность.

## Parameters (v0.1)
- fast: **12** (стандарт MACD)
- slow: **26** (стандарт MACD)
- variant: Classical (α = 2/(n+1))
- source price: close
- init: SMA первых n баров (seed)

## Implementation
- TA-Lib: `EMA(close, timeperiod=n)` — использует **Classical** формулу.
- pandas: `close.ewm(span=n, adjust=False).mean()` даёт Classical EMA с рекурсивной инициализацией от первого бара (не SMA-seed!). Если нужен SMA-seed — инициализировать вручную.
- **Ловушка (TA-Lib SF bug #87):** в некоторых сборках первое значение EMA может быть посчитано от нулевой базы, а не от SMA первых n — всегда проверять значение EMA[n−1] == SMA(P[0..n−1]).
- На warm-up баров (первые n−1) EMA считается NaN / не определён — не использовать в сигнале.

## Related
- [[../strategies/ema-crossover-adx-rsi]] — основная стратегия v0.1
- [[./adx]] — фильтр силы тренда
- [[./rsi]] — фильтр перекупленности/перепроданности
- [[./atr]] — волатильность для стопов

## Реализация

- [[../../project/components/indicators]] — `ema(close, period, mode="classical"|"wilder")` — TA-Lib wrapper + Wilder fallback
- [[../../project/components/strategy]] — EMA fast/slow crossover is primary entry signal

## Sources
- Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*. Trend Research.
- Kaufman, P. (2013). *Trading Systems and Methods* (5th ed.). Ch. 7.
- Appel, G. (2005). *Technical Analysis: Power Tools for Active Investors*. (MACD / EMA-defaults 12/26.)
- TA-Lib documentation: https://ta-lib.org/
