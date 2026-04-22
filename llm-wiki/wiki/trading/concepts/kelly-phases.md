---
title: Kelly Phases — 4-фазная модель position sizing
type: concept
tags: [position-sizing, kelly, risk, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §5]
---

# Kelly Phases (4-фазная)

**TL;DR:** 4 фазы по количеству накопленных сделок n. В каждой — фиксированный или ограниченный Kelly. Обоснование — Wilson 95% CI на true win-probability p̂, которая определяет минимальный n для отвержения "no edge".

## Формула Kelly (binary)

```
f* = (p · b − q) / b
```

где:
- `p` — вероятность выигрыша,
- `q = 1 − p`,
- `b` — отношение average win / average loss (payoff ratio).

**Стандартная ошибка Kelly fraction:**
```
SE(f*) ≈ (1 + 1/b) · √[p(1−p) / n]
```

При малых n SE велика → Kelly подвержен catastrophic mis-estimation.

## Фазы

| Фаза | n (число сделок) | Размер позиции | 95% Wilson CI на p при p̂=0.55 | Обоснование |
|------|------------------|----------------|-------------------------------|-------------|
| **1** | n < 30 | **Fixed 1%** | [0.374, 0.711] — CI на f* straddles zero | Классическая CLT-граница n=30; невозможно отвергнуть "no edge"; ruin-risk при Kelly катастрофичен |
| **2** | 30 ≤ n < 100 | **Fixed 2%** | при n=100: [0.453, 0.643] | Направление edge становится правдоподобным, но не статзначимо; MacLean–Thorp–Ziemba (2011): "short-term Kelly very risky" |
| **3** | 100 ≤ n < 200 | **Quarter-Kelly, cap 3%** | при n=200: [0.481, 0.616], значим на 90% | SE(p̂) вдвое меньше Phase 1; quarter-Kelly защищает от mis-estimation |
| **4** | n ≥ 200 | **Half-Kelly, cap 5%** | при n=500: [0.507, 0.592], значим на 95% | Соответствует Halls-Moore §13.2: "many traders use half-Kelly"; cap страхует от fat-tails (BTC Student-t d.f.≈4) |

## Почему именно эти пороги

**n=30:** классическая CLT-граница. Ниже этого — Central Limit Theorem слабо применима, binomial CI аномально широкий.

**n=100:** SE(p̂) примерно вдвое меньше, чем при n=30. Direction of edge правдоподобен.

**n=200:** при p̂=0.55 Wilson 95% CI = [0.481, 0.616] — нижняя граница впервые outside 0.5, т.е. можно отвергнуть "no edge" на 95% уровне.

**Wilson CI формула** (Agresti–Coull 1998 variant):
```
CI = [p̂ + z²/(2n) ± z·√(p̂(1−p̂)/n + z²/(4n²))] / (1 + z²/n)
```
где z=1.96 для 95%.

## Capping и почему half-Kelly не full-Kelly

Full-Kelly максимизирует log-growth **при известном p**. Но p — estimated с SE → full-Kelly подвержен:
- **Volatility drag** — при fat-tails actual growth < log-optimal.
- **Model risk** — если p̂ overestimated, f* catastrophically overbet.

Thorp (2006) и MacLean–Thorp–Ziemba (2011) рекомендуют half-Kelly: ~75% оптимального log-growth при 50% volatility-drawdown. Для BTC с fat tails (Student-t d.f.≈4) это стандартная защита.

**Cap 5%** защищает от случаев, когда formula даёт large f* из-за overestimated payoff (b).

## Rebalance cadence

Параметры p, b обновляются **ежедневно** на trailing 3–6 месяцев окне (Halls-Moore §13.2 рекомендация).

```python
# псевдокод
def rebalance_kelly(trade_history, window_days=90):
    recent = trade_history[-window_days*24:]  # 1H bars
    wins = sum(1 for t in recent if t.pnl > 0)
    losses = len(recent) - wins
    p = wins / len(recent)
    avg_win = mean(t.pnl for t in recent if t.pnl > 0)
    avg_loss = abs(mean(t.pnl for t in recent if t.pnl < 0))
    b = avg_win / avg_loss
    f_star = (p * b - (1-p)) / b
    return f_star
```

## Persistence

`trade_count` counter и current phase persist в SQLite `state` table — не сбрасываются при restart. Phase transition — **one-way** в сторону увеличения (нельзя откатиться обратно в Phase 1 кроме regime shift detector).

## Regime shift downgrade

Если KS-test live returns vs backtest даёт p<0.01 (регимный сдвиг) → **revert to Phase 1** (fixed 1%) до накопления 30 новых сделок. См. [[../../project/architecture/risk-register]] S5.

## Implementation skeleton (pseudocode)

```python
def position_fraction(trade_count: int, p_hat: float, b: float) -> float:
    if trade_count < 30:
        return 0.01
    elif trade_count < 100:
        return 0.02
    else:
        f_star = (p_hat * b - (1 - p_hat)) / b
        if trade_count < 200:
            return min(f_star * 0.25, 0.03)   # Quarter-Kelly, cap 3%
        else:
            return min(f_star * 0.5, 0.05)    # Half-Kelly, cap 5%
```

## Sources

- Kelly, J. L. (1956). "A new interpretation of information rate" *BSTJ* 35:917–926.
- Thorp, E. O. (2006). "The Kelly Criterion in Blackjack, Sports Betting and the Stock Market" in *Handbook of Asset and Liability Management*.
- MacLean, L. C., Thorp, E. O., Ziemba, W. T. (2011). *The Kelly Capital Growth Investment Criterion*.
- Halls-Moore (2015) *Successful Algorithmic Trading* Ch.13 §13.2.
- Agresti, A., Coull, B. A. (1998). "Approximate is better than 'exact' for interval estimation of binomial proportions" *Am. Stat.* 52:119–126.

## Related

- [[../strategies/ema-crossover-adx-rsi]] — где Kelly применяется.
- [[circuit-breakers]] — drawdown-level halts.
- [[../../project/decisions/0012-4-phase-kelly-sizing]] — ADR.
