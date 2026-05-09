---
title: signalgen.indicators — TA-Lib wrappers
type: component
tags: [component, signalgen, indicators, ta-lib, ema, adx, rsi, atr]
created: 2026-04-22
updated: 2026-04-22
sources:
  - src/signalgen/indicators.py
  - tests/unit/test_indicators.py
  - wiki/project/decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover.md
status: stable
---

# Component: signalgen.indicators

**TL;DR:** Тонкие stateless-обёртки над TA-Lib для EMA/ADX/±DI/RSI/ATR; numpy in/out; Classical EMA (α=2/(n+1)) для crossover + Wilder (α=1/n) для oscillators per ADR 0011.

## Публичный API

| Function | Signature | Smoothing | Returns |
|----------|-----------|-----------|---------|
| `ema` | `(close, period, mode="classical")` | classical или wilder | 1-D float; NaN на warm-up |
| `rsi` | `(close, period=14)` | Wilder (TA-Lib default) | [0, 100]; NaN на warm-up |
| `atr` | `(high, low, close, period=14)` | Wilder | ≥ 0; NaN на warm-up |
| `adx` | `(high, low, close, period=14)` | Wilder double-smooth | [0, 100]; warm-up ≈ 2n−1 |
| `plus_di` | `(high, low, close, period=14)` | Wilder | [0, 100] |
| `minus_di` | `(high, low, close, period=14)` | Wilder | [0, 100] |

Все функции — pure (no state), numpy-first. Валидация через `_validate_hlc` (shape + period>=2).

## Примечания

- TA-Lib `EMA` имеет исторический bug (SF #87) — проверяем `EMA[period-1] == SMA(close[0..period-1])` в unit-tests.
- `ema(..., mode="wilder")` — собственная реализация (TA-Lib native EMA не поддерживает Wilder), seed = SMA(close[0..period-1]), recurrence α=1/period.
- `atr`, `rsi`, `adx`, `plus_di`, `minus_di` — прямые делегаты `talib.*` (Wilder by default).

## Связанные

- [[../decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover]] — ADR: почему 2 режима.
- [[./strategy]] — основной live consumer.
- [[./backtest-harness]] — backtest indicators module (`src/backtest/indicators.py`) — отдельный batch-вариант
- [[../../trading/indicators/ema]] — EMA theory + classical vs Wilder variants
- [[../sprints/sprint-03-strategy-port]] — sprint where indicators component was created
- [[../decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover]] — governing ADR (already linked above)
- [[../../trading/indicators/adx]] — ADX theory + Wilder double-smooth
- [[../../trading/indicators/rsi]] — RSI theory + Wilder smoothing
- [[../../trading/indicators/atr]] — ATR theory + Wilder EMA on TR
