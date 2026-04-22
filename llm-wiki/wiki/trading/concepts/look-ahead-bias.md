---
title: Look-Ahead Bias — защита и детектирование
type: concept
tags: [backtest, look-ahead, bias, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §16]
---

# Look-Ahead Bias

**TL;DR:** Indicator использует данные, не доступные в момент decision. Самая опасная и тихая ошибка в algo-trading. Защита — in-code invariants + CI gate + property tests + integration test.

## Канонические формы bias

1. **Intra-bar leakage.** Indicator computed на `close[T]`, но decision делается **до** close(T) (использует будущий close).
2. **Label leakage в CV.** Label `return[t+k]` в train-fold пересекает test-fold — модель учится видеть будущее.
3. **Look-ahead в data pipeline.** `shift(-1)` вместо `shift(1)` — классический pandas-баг.
4. **Info bar boundary.** Session-aware feature использует `high[T]` для сигнала в bar T (high может быть позднее close в intra-day).
5. **Fundamentals release.** Использование earning report в backtest **до** public announcement date.

## Для BTC 1H типичные ошибки

- Использование `close[T]` в стратегии, принимающей решение в момент intra-bar T.
- `signal = (close > ema)` without `.shift(1)` — leakage на vectorized backtest.
- Computing ATR на `high[T]` / `low[T]` внутри бара, когда они ещё не финализированы.
- Seed исторических баров через REST в момент, когда `isClosed=false` для last bar.

## Защита (6 invariants)

См. [[../../project/architecture/execution-timing]] "Hard look-ahead-protection invariants":

1. **Closed bar only.** Indicator computed только на `Bar.closeTime < now`.
2. **Signal.bar_ref.** Signal carries `bar_ref.closeTime`; Execution отказывает в orders с `bar_ref.closeTime > previous_closed_bar.closeTime`.
3. **Backtest shift.** Signals shift ≥1 bar before fill simulation (`signal.shift(1) · returns[t+1]`).
4. **Property test.** Asserts `signal_ts < fill_ts` для каждой сделки в audit log.
5. **Integration test.** Feed live WS stream в backtester event-order; result equals vectorized backtest within slippage tolerance.
6. **Freqtrade-style regression test** в CI — re-run с signals computed up to each t isolated, compare to full backtest.

## Look-ahead detector (CI gate)

Custom script `scripts/lookahead_detector.py`:

```python
def poison_future_bars(bars, T):
    """Replace bars[T+1:] with NaN."""
    poisoned = bars.copy()
    poisoned.iloc[T+1:] = float('nan')
    return poisoned

def test_no_lookahead():
    bars = load_fixture()
    T = len(bars) // 2
    signal_full = strategy(bars)
    signal_poisoned = strategy(poison_future_bars(bars, T))
    # Signal at t <= T must not change when future is removed
    assert (signal_full.iloc[:T] == signal_poisoned.iloc[:T]).all()
```

Fail → CI rejects PR.

## Hypothesis-based property tests

```python
from hypothesis import given, strategies as st

@given(bars=bar_strategy(min_size=100, max_size=10000))
def test_signal_time_before_fill_time(bars):
    trades = run_strategy_and_record_trades(bars)
    for trade in trades:
        assert trade.signal_ts < trade.fill_ts, \
            f"Look-ahead at trade {trade.id}: signal_ts={trade.signal_ts} >= fill_ts={trade.fill_ts}"
```

## Hidden forms (что часто пропускают)

1. **Normalization via global stats.** `bars['z_close'] = (bars['close'] - bars['close'].mean()) / bars['close'].std()` использует будущие средние.
   Fix: rolling statistics.
2. **Signal smoothing с centred MA.** `rolling(window=10).mean(center=True)` использует будущие bars.
   Fix: `center=False` (default).
3. **Fit model on full data.** XGBoost / HMM fit на full period, затем apply to "past" periods — leakage через fit.
   Fix: refit each CV fold.
4. **Survivorship in universe.** Symbol включён в universe **только** потому что он существует в present. Для BTC-only не проблема, но при multi-symbol (v0.3+) — делистеные тикеры должны быть в universe.

## Почему важно формализовать

Look-ahead даёт **catastrophically inflated Sharpe** (2×–10×), но его легко не заметить: code looks reasonable, backtest profit looks convincing. Live performance — negative edge.

"Holy grail backtest" (Sharpe 5+) — почти **гарантированно** содержит look-ahead bias или data snooping. DSR correction на alone не spasает.

## Sources

- Chan (2013) *Algorithmic Trading* Ch.2.
- Pardo (2008) *Evaluation and Optimization of Trading Strategies* Ch.3.
- Halls-Moore (2015) *Successful Algorithmic Trading* §3.2.
- Freqtrade [lookahead-analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/).
- López de Prado (2018) *AFML* Ch.7 §7.4 — purge and embargo.

## Related

- [[../../project/architecture/execution-timing]] — production discipline.
- [[walk-forward-validation]] — embargo для CV.
- [[monte-carlo-permutations]] — sanity check.
