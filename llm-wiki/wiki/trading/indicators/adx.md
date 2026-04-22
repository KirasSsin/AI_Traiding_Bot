---
title: ADX (Average Directional Index)
type: indicator
tags: [trading, indicator, trend-strength, adx, wilder]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md, Wilder 1978]
---

# ADX (Average Directional Index)

**TL;DR:** ADX измеряет силу тренда (но не направление) на шкале 0–100; в v0.1 используется как фильтр: торгуем только при ADX > 25.

## Definition
ADX (Average Directional Index) — разработан Уайлдером (Wilder, 1978) для измерения **силы** направленного движения, вне зависимости от его знака. Работает в паре с +DI и −DI (Directional Indicators), которые дают направление.

Расчёт в три шага:

1. True Range (TR) и Directional Movement (+DM, −DM):
```
TR    = max(H − L, |H − C_prev|, |L − C_prev|)
+DM   = (H − H_prev) if (H − H_prev) > (L_prev − L) and > 0 else 0
−DM   = (L_prev − L) if (L_prev − L) > (H − H_prev) and > 0 else 0
```

2. Сглаживание по Уайлдеру (Wilder smoothing) с периодом n:
```
ATR      = Wilder_EMA(TR, n)
+DM_s    = Wilder_EMA(+DM, n)
−DM_s    = Wilder_EMA(−DM, n)
+DI      = 100 · (+DM_s / ATR)
−DI      = 100 · (−DM_s / ATR)
```

3. DX и ADX:
```
DX  = 100 · |+DI − −DI| / (+DI + −DI)
ADX = Wilder_EMA(DX, n)
```

Параметр по умолчанию: **n = 14**.

## Formula variants (важно!)
ADX использует **исключительно Wilder EMA** (α = 1/n):
- Для n = 14: α = 1/14 ≈ 0.0714.
- Эквивалент Classical: Wilder(14) ≈ Classical(27).

Если считать ADX через Classical EMA с n = 14 — результаты **не совпадут** с каноном Уайлдера и с выводом TA-Lib. См. [[./ema]] про разницу вариантов.

## Interpretation
- ADX < 20 — тренда нет, рынок «плоский» (range-bound). Trend-following-сигналы давать опасно.
- 20 ≤ ADX < 25 — слабый/зарождающийся тренд.
- 25 ≤ ADX < 50 — сильный устойчивый тренд (оптимальная зона для trend-following).
- ADX ≥ 50 — очень сильный тренд, но возможна истощённость / близость разворота.
- **ADX не показывает направление** — за это отвечают +DI и −DI (+DI > −DI → bullish bias).
- Растущий ADX = усиление тренда; падающий = ослабление (даже если цена ещё идёт в ту же сторону).

## Role in v0.1 strategy
ADX — **фильтр силы тренда** в стратегии `ema-crossover-adx-rsi`:

- Сигнал EMA-crossover берётся **только если ADX(14) > 25**.
- При ADX ≤ 25 — FLAT (не открываем новые позиции), даже если EMA(12) и EMA(26) пересеклись.
- Направление подтверждается знаком EMA-crossover (ADX сам по себе без DI не даёт направления).

Это отсекает ложные срабатывания crossover в боковиках, где EMA пересекаются часто и хаотично.

## Parameters (v0.1)
- period: **14** (стандарт Wilder)
- variant: **Wilder EMA** (α = 1/14)
- threshold: **ADX > 25** для входа
- source: TR / +DM / −DM из OHLC

## Implementation
- TA-Lib: `ADX(high, low, close, timeperiod=14)` — использует Wilder-сглаживание, совпадает с Уайлдером. Также `PLUS_DI`, `MINUS_DI`.
- Первые ~2·n − 1 = 27 баров на warm-up: первый валидный ADX появляется после двойного сглаживания.
- **Ловушка:** TA-Lib SF bug #87 — в старых версиях инициализация Wilder-seed могла быть неверной; всегда проверять: первое значение сглаженного ряда == SMA первых n точек входного ряда.
- Pandas-реализация через `ewm(alpha=1/n, adjust=False)` не даёт точного Wilder, пока не задан правильный seed (SMA первых n). Лучше брать TA-Lib.

## Related
- [[../strategies/ema-crossover-adx-rsi]] — основная стратегия v0.1
- [[./ema]] — сигнал направления (crossover)
- [[./rsi]] — фильтр перекупленности
- [[./atr]] — использует тот же TR, что и ADX

## Sources
- Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*. Ch. 6 (Directional Movement).
- Kaufman, P. (2013). *Trading Systems and Methods* (5th ed.). Ch. 9.
- TA-Lib documentation: ADX, PLUS_DI, MINUS_DI.
