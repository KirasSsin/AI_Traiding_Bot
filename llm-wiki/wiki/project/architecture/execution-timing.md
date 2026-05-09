---
title: Execution Timing — Signal on close(T) → Fill at open(T+1)
type: architecture
tags: [execution, timing, look-ahead, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §16]
---

# Execution Timing

**TL;DR:** Канонический стандарт — `Signal on close of bar T → order placed at open of bar T+1`. Единственный вариант, не содержащий look-ahead bias **by construction**.

## Принцип

1. На close бара T (WS событие `kline` с `k.x == true`) — пересчитываем индикаторы **только на closed bars ≤ T**.
2. Если strategy эмитит сигнал — выпускаем MARKET (или LIMIT IOC) ордер.
3. Fill происходит по цене, близкой к open бара T+1 (реально — через 1–5 секунд после close(T)).
4. В backtest: `signal[t] = strategy(bars[0..t]); entry_price[t+1] = open[t+1] · (1 + slip_bps·sign/1e4)`.

Задержка 1–5s между close(T) и next-open пренебрежима на 1H (0.03–0.14% от интервала).

## Отвергнутые альтернативы

| Вариант | Почему отвергнут |
|---------|------------------|
| (b) Intra-bar signal + immediate market order | **Текстбуковый look-ahead bias** — использует ещё не закрытый close (Halls-Moore §3.2, Harris) |
| (c) Signal on close + immediate market order | Размывает границу decision/execution; underestimate adverse selection |
| (d) Signal on close + limit at `close ± k·ATR` | Вносит fill-probability uncertainty; **только** как v0.2 refinement после (a) baseline |

## Backtest implementation

```python
# signal computed at close of T, fill at open of T+1 with slippage
signal[t] = strategy(bars[0..t])        # use only closed bars
entry_px[t+1] = open[t+1] * (1 + slip_bps / 1e4 * sign(signal[t]))
pnl[t+1] = signal[t] * (close[t+1] - entry_px[t+1]) / entry_px[t+1] \
         - fee_bps / 1e4 * 2   # entry fee + exit fee
```

**Invariant:** `signal.shift(1) × returns[t+1]` — vectorized form; property test проверяет `signal_ts < fill_ts`.

## Production implementation

```
WS receives kline event with k.x == true (terminal bar message)
│
├── (1) Run strategy(bars[0..T]) → Signal | None
│
├── (2) Within ~1s: submit MARKET order OR LIMIT IOC at close(T) ± tolerance
│          (tolerance ≈ 1 tick или small fraction of ATR — caps slippage)
│
└── (3) On entry-fill event: place OCO bracket (TP + SL) как separate call
```

**Не** запускаем стратегию на каждый intra-bar tick — **только** на `k.x == true`.

## Hard look-ahead-protection invariants (enforced)

Enforced через ACL + property tests + CI gates:

1. **Closed bar only.** Indicator computed только на `Bar` с `closeTime < now`.
2. **Signal.bar_ref.** Signal value object carries `bar_ref.closeTime`. Execution context отказывает в orders с `bar_ref.closeTime > previous_closed_bar.closeTime`.
3. **Backtest shift.** Signals shift ≥1 bar before fill simulation.
4. **Property test.** Asserts `signal_ts < fill_ts` для каждой сделки в audit log.
5. **Integration test.** Feed live WS stream в backtester event-order; result equals vectorized backtest within slippage tolerance.
6. **Freqtrade-style lookahead-analysis regression test** в CI — re-run с signals computed up to each t isolated, compare to full backtest.

## Look-ahead detector (CI gate)

Custom `scripts/lookahead_detector.py --strict`:

- Future-bar poison test: заменяет bar[T+1..] на NaN и проверяет, что signals не меняются.
- Assertions fail → CI rejects PR.

См. [[../../trading/concepts/look-ahead-bias]] для теории.

## Latency бюджет v0.1

| Этап | Target |
|------|--------|
| kline close → indicator update | <100ms |
| indicator → strategy decision | <10ms |
| decision → order submit | <500ms |
| submit → exchange ack | <200ms (p99) |
| **Total tick-to-trade** | **<1s** (p99) |

На 1H таймфрейме это задача тривиальная. Для v0.3 и L2-стратегий (~100ms target) — потребуется Rust-hot-path.

## Sources

- Chan (2013) *Algorithmic Trading* Ch.2.
- Pardo (2008) *The Evaluation and Optimization of Trading Strategies* Ch.4–5.
- Halls-Moore (2015) *Successful Algorithmic Trading* §3.2.
- Freqtrade lookahead-analysis [docs](https://www.freqtrade.io/en/stable/lookahead-analysis/).

## Related

- [[bounded-contexts]] — где timing enforced (Signal Gen + Execution boundary).
- [[../../trading/concepts/look-ahead-bias]] — теория.
- [[../../trading/concepts/slippage-model]] — slippage bps применяется к `entry_px`.
- [[../components/coordinator]] — enforces bar-close-only order submission
- [[../components/bar-poller]] — `BarPoller` поставляет confirmed bars в координатор
- [[../components/bybit-adapter]] — place_order вызывается только после bar close confirm
