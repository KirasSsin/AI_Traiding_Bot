---
title: EMA-crossover + ADX + RSI (v0.1)
type: strategy
tags: [trend-following, ema-crossover, v0.1, btc-usdt, 1h]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md, Docs/MVP + ALL PROJECT/Full Project.md]
---

# EMA-crossover + ADX + RSI

**TL;DR:** Trend-following стратегия v0.1: вход по EMA(12)×EMA(26) crossover, фильтр по ADX(14) и RSI(14), защита через ATR-based SL/TP в OCO bracket.

## Market

- **Символ:** BTC/USDT
- **Venue:** Binance Spot
- **Таймфрейм:** 1H
- **Position side:** LONG / FLAT (spot, без шортов)

## Индикаторы

| Индикатор | Параметр | Тип сглаживания | Назначение |
|-----------|----------|-----------------|------------|
| EMA fast | 12 | **Classical** α=2/13≈0.154 | Направление тренда |
| EMA slow | 26 | **Classical** α=2/27≈0.074 | Референс тренда |
| ADX | 14 | **Wilder** α=1/14≈0.0714 | Сила тренда (филтр) |
| +DI / −DI | 14 | **Wilder** | Направление (филтр подтверждения) |
| RSI | 14 | **Wilder** | Overbought/oversold (филтр) |
| ATR | 14 | **Wilder** | Volatility (для SL/TP + sizing) |

Детали: [[../indicators/ema]], [[../indicators/adx]], [[../indicators/rsi]], [[../indicators/atr]]. ADR: [[../../project/decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover]].

## Entry rules

**LONG (market buy) при закрытии бара T, если ВСЕ условия:**

1. **Crossover:** `EMA12[T] > EMA26[T]` и `EMA12[T-1] ≤ EMA26[T-1]` (cross up в этом баре).
2. **Trend strength:** `ADX[T] > 25`.
3. **Direction confirmation:** `+DI[T] > -DI[T]`.
4. **No overbought:** `RSI[T] < 70`.
5. **Risk checks pass** (Risk context — см. [[../../project/architecture/bounded-contexts]]).

Если bar T не удовлетворяет — FLAT (без нового entry).

## Exit rules

Exit происходит через OCO bracket (выставляется сразу после entry fill):

- **Take Profit (TP):** `entry_price + 3.0 · ATR[T_entry]` (реализует RR ≈ 2.0).
- **Stop Loss (SL):** `entry_price − 1.5 · ATR[T_entry]`.

**Signal flip exit:** если на close бара T открыта LONG позиция и `EMA12[T] < EMA26[T]` и `+DI[T] < -DI[T]` — force exit (market) независимо от OCO.

**Time stop (опционально, v0.1+):** если позиция открыта > 48 баров (2 дня) и P&L ≈ 0 ± 0.5·ATR — market exit.

## Position sizing

Через Kelly-фазу (см. [[../concepts/kelly-phases]]):
- Phase 1 (n<30): fixed 1% equity
- Phase 2 (30≤n<100): fixed 2% equity
- Phase 3 (100≤n<200): Quarter-Kelly, cap 3%
- Phase 4 (n≥200): Half-Kelly, cap 5%

`qty = (position_fraction · equity) / (1.5 · ATR)` — размер в базовой валюте такой, что при срабатывании SL потеря = `position_fraction · equity`.

## Key invariants

1. **Signal на close, fill на open(T+1).** См. [[../../project/architecture/execution-timing]].
2. **Один signal на bar.** Duplicates → `REJECT_DUPLICATE_SIGNAL`.
3. **OCO обязателен** при каждом entry. Без brackets — reject.
4. **ATR freeze.** `ATR[T_entry]` фиксируется при entry; SL/TP не двигаются при update ATR.
5. **Closed bar only.** Не используем intra-bar values для indicator input.

## Hyperparameters (v0.1 defaults)

| Параметр | Значение | Источник |
|----------|----------|----------|
| ema_fast | 12 | MACD стандарт |
| ema_slow | 26 | MACD стандарт |
| adx_period | 14 | Wilder (1978) |
| rsi_period | 14 | Wilder (1978) |
| atr_period | 14 | Wilder (1978) |
| adx_threshold | 25 | Wilder "trending market" |
| rsi_overbought | 70 | Wilder "caution zone" |
| rsi_oversold | 30 | Wilder |
| sl_atr_multiplier | 1.5 | conservative default |
| tp_atr_multiplier | 3.0 | RR ≈ 2.0 |
| time_stop_bars | 48 | 2 days × 24h |

**Важно:** эти параметры должны быть **не** оптимизированы на full-sample — иначе data snooping. v0.1 использует textbook defaults Wilder + MACD; optimization в рамках Walk-Forward CV (см. [[../concepts/walk-forward-validation]]).

## Expected metrics (из backtest)

Per MVP-спеку (§10, OOS criteria):
- Sharpe OOS: ≥1.0 (target, не guaranteed)
- Sortino OOS: ≥1.5
- MaxDD: <25%
- Win rate: 45% @ RR=2.0
- n trades/year: ~100–250 (2–5 trades/week)

Hudson & Urquhart (2021) показывают, что простые MA-правила на BTC после 2017 демонстрируют **отрицательный OOS Sharpe**. Это означает: target ≥1.0 — это аспирация, не baseline. Если backtest даёт Sharpe 2+ без DSR-correction — **suspicious** (overfit).

## Известные слабости

1. **Whipsaws.** В sideways-market EMA crossovers генерируют много false signals. ADX>25 частично фильтрует, но не полностью.
2. **Lagging entries.** EMA crossovers догоняют тренд; вход позже пика impulse.
3. **Late exits.** ATR-based TP может закрыть позицию до окончания тренда, или держать в flat-зоне.
4. **Regime dependency.** Работает в трендовые периоды; проигрывает в mean-reverting.
5. **Fixed SL/TP multiples.** Не адаптивны к режиму (ранг vs trending).

## Roadmap улучшений (v0.2+)

- Trailing stop после 2·ATR profit (chandelier stop).
- Pyramid entries (scale in on re-crossings).
- Volume filter (reject signal если `volume < 0.5 · SMA(volume, 20)`).
- Regime-adaptive thresholds (ADX-threshold via HMM state).
- Multi-timeframe confirmation (4H HTF trend).

## Related

- [[../../project/architecture/overview]] — MVP overview.
- [[../../project/architecture/execution-timing]] — timing discipline.
- [[../concepts/kelly-phases]] — position sizing.
- [[../concepts/walk-forward-validation]] — OOS validation.
- [[../concepts/circuit-breakers]] — drawdown halts.

## Реализация

- [[../../project/components/strategy]] — `EmaCrossoverAdxRsiStrategy.on_bar()` — production live implementation
- [[../../project/components/indicators]] — TA-Lib EMA/ADX/RSI/ATR wrappers consumed by strategy
- [[../../project/components/backtest-harness]] — `src/backtest/indicators.py` + `replay_engine.run_replay()` — backtest variant

## Sources

- Wilder (1978) *New Concepts in Technical Trading Systems*.
- MACD by Appel (1979) — стандартные параметры 12/26.
- Hudson & Urquhart (2021) "Technical trading and cryptocurrencies" *Annals of OR* 297:191–220.
- Chan (2013) *Algorithmic Trading* Ch.2, 6.
