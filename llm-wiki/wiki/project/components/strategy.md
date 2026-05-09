---
title: signalgen.strategy — EmaCrossoverAdxRsiStrategy
type: component
tags: [component, signalgen, strategy, ema-crossover, adx, rsi, v0.1]
created: 2026-04-22
updated: 2026-04-22
sources:
  - src/signalgen/strategy.py
  - tests/unit/test_strategy.py
  - tests/property/test_lookahead.py
  - wiki/trading/strategies/ema-crossover-adx-rsi.md
  - wiki/project/architecture/execution-timing.md
status: stable
---

# Component: signalgen.strategy

**TL;DR:** `EmaCrossoverAdxRsiStrategy.on_bar(bar: Bar) -> Signal | None` — stateful стратегия с internal rolling buffer; эмитит LONG при cross-up + ADX/+DI/RSI gates; FLAT при signal-flip.

## Контракт

```python
strat = EmaCrossoverAdxRsiStrategy(
    symbol="BTCUSDT",
    ema_fast=12, ema_slow=26,
    adx_period=14, adx_threshold=Decimal("25"),
    rsi_period=14, rsi_oversold=Decimal("30"), rsi_overbought=Decimal("70"),
    atr_period=14,
)
for bar in market_data_stream:
    sig = strat.on_bar(bar)
    if sig is not None:
        event_bus.emit(sig)   # S6
```

`on_bar` возвращает `Signal | None`. None может означать:
- `is_closed=False` (live bar, игнор);
- wrong symbol;
- warm-up не завершён;
- duplicate или out-of-order bar;
- нет crossing/gate-conditions.

## Правило входа (LONG)

Все условия одновременно на close(T):

1. `EMA12[T] > EMA26[T]` AND `EMA12[T-1] ≤ EMA26[T-1]` — cross up.
2. `ADX[T] > adx_threshold` (default 25).
3. `+DI[T] > -DI[T]` — direction confirmation.
4. `RSI[T] < rsi_overbought` (default 70).
5. `current_side == FLAT` (no re-entry без выхода).

Reason code: `ENTRY_LONG_EMA_CROSS_UP`.

## Правило выхода (FLAT — signal flip)

На close(T), если `current_side == LONG`:

- `EMA12[T] < EMA26[T]` AND `-DI[T] > +DI[T]` → FLAT.

Reason code: `EXIT_FLAT_SIGNAL_FLIP`.

*SL/TP и time-stop — в S5 (execution), не здесь.*

## Инварианты (КРИТИЧНЫЕ — проверены тестами + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | Look-ahead-free: signal computed on close(T) only, `signal.generated_at >= bar_close_time` | `src/signalgen/strategy.py::EmaCrossoverAdxRsiStrategy.on_bar` | `tests/property/test_lookahead.py::test_signal_generated_at_ge_bar_close_time` |
| 2 | `is_closed=False` bars discarded BEFORE any computation | `src/signalgen/strategy.py::EmaCrossoverAdxRsiStrategy._append_bar` | `tests/unit/test_strategy.py::test_strategy_skips_non_closed_bars` |
| 3 | Out-of-order / duplicate bars skipped (monotonicity guard) | `src/signalgen/strategy.py::EmaCrossoverAdxRsiStrategy._append_bar` | `tests/unit/test_strategy.py::test_strategy_rejects_out_of_order_bar` |

Additional invariants (not CRITICAL):
- **FSM:** `current_side` ∈ {FLAT, LONG}; транзиции FLAT→LONG (entry), LONG→FLAT (flip). SHORT вне scope v0.1.
- **Buffer size:** `max(ema_slow, 2·adx_period, atr_period, rsi_period) + 5`.
- **Thread-safety:** НЕ thread-safe. Один producer thread.

## Производительность

- Indicator computation пересчитывается на full buffer каждый bar. Для 1H и buffer ≤ 100 баров это <5ms.
- v0.2 refinement: incremental update (хранить последние EMA/ADX-state) — не требуется на 1H.

## Связанные

- [[./indicators]] — consumer (EMA/ADX/RSI/ATR).
- [[../../trading/strategies/ema-crossover-adx-rsi]] — reference rules.
- [[../architecture/execution-timing]] — invariants.
- [[./models]] — Bar (input), Signal (output).
- [[../decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover]] — ADR.
