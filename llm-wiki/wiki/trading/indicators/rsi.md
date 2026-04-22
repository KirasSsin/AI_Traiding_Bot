---
title: RSI (Relative Strength Index)
type: indicator
tags: [trading, indicator, momentum, oscillator, rsi, wilder]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md, Wilder 1978]
---

# RSI (Relative Strength Index)

**TL;DR:** RSI — momentum-осциллятор 0–100, измеряющий соотношение среднего роста и среднего падения; в v0.1 используется как фильтр перекупленности/перепроданности.

## Definition
RSI (Relative Strength Index), Wilder (1978) — осциллятор, показывающий относительную силу бычьего и медвежьего движения за последние n баров.

Формула:
```
gain[t] = max(C[t] − C[t−1], 0)
loss[t] = max(C[t−1] − C[t], 0)

avg_gain = Wilder_EMA(gain, n)
avg_loss = Wilder_EMA(loss, n)

RS  = avg_gain / avg_loss
RSI = 100 − 100 / (1 + RS)
```

Эквивалентная форма: `RSI = 100 · avg_gain / (avg_gain + avg_loss)`.

Параметр по умолчанию: **n = 14** (канон Уайлдера).

## Formula variants (важно!)
RSI Уайлдера использует **Wilder EMA** (α = 1/n):
- Для n = 14: α = 1/14 ≈ 0.0714.
- Seed: `avg_gain[n−1] = SMA(gain[0..n−1])`, далее рекурсивно.
- Эквивалент Classical: Wilder(14) ≈ Classical(27).

Существует вариант «Cutler's RSI» на обычной SMA вместо Wilder — **не используем** его в v0.1, так как результаты будут отличаться от стандартных. См. [[./ema]] про разницу вариантов.

## Interpretation
- RSI > 70 — перекупленность (overbought), возможен откат.
- RSI < 30 — перепроданность (oversold), возможен отскок.
- RSI ≈ 50 — нейтраль, часто пересечение 50 трактуется как смена momentum-режима.
- **Важно:** в сильном тренде RSI может долго держаться >70 (в бычьем) или <30 (в медвежьем). Механический контр-трендовый вход по RSI в тренде — классическая ошибка.
- Дивергенции (цена обновляет экстремум, RSI — нет) — сигнал ослабления momentum / возможного разворота.
- Failure swings (Уайлдер): RSI-пик в зоне >70 не обновляется, а предыдущий RSI-минимум пробивается вниз → сигнал разворота.

## Role in v0.1 strategy
RSI — **фильтр перекупленности/перепроданности** в стратегии `ema-crossover-adx-rsi`:

- **LONG блокируется, если RSI > 70** (не входим на перекупленности, даже при EMA-crossover + ADX > 25).
- **SHORT блокируется, если RSI < 30** (не входим на перепроданности).
- В зоне 30 ≤ RSI ≤ 70 — сигнал от EMA+ADX пропускается без фильтрации RSI.

Логика: отрезаем «позднюю» часть тренда, где вход уже имеет плохой risk/reward. Не используем RSI как самостоятельный trigger — только как veto-фильтр.

## Parameters (v0.1)
- period: **14** (стандарт Wilder)
- variant: **Wilder EMA** (α = 1/14)
- overbought: **70**
- oversold: **30**
- source price: close

## Implementation
- TA-Lib: `RSI(close, timeperiod=14)` — использует Wilder-сглаживание, совпадает с каноном.
- pandas-вариант: нужно явно задать seed через SMA первых n и дальше `ewm(alpha=1/n, adjust=False)`. «Наивный» `ewm(span=14)` даст Classical, а не Wilder — значения разойдутся.
- Warm-up: первый валидный RSI на баре n (индекс n−1) после заполнения seed.
- **Ловушка (TA-Lib SF bug #87):** проверять, что `avg_gain[n−1]` и `avg_loss[n−1]` равны SMA соответствующих рядов за первые n баров.
- Деление на ноль: если `avg_loss = 0` → RSI = 100 (формально RS → ∞). Обрабатывать в коде.

## Related
- [[../strategies/ema-crossover-adx-rsi]] — основная стратегия v0.1
- [[./ema]] — сигнал направления
- [[./adx]] — фильтр силы тренда
- [[./atr]] — волатильность для стопов

## Sources
- Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*. Ch. 3 (RSI).
- Kaufman, P. (2013). *Trading Systems and Methods* (5th ed.). Ch. 9.
- TA-Lib documentation: RSI.
