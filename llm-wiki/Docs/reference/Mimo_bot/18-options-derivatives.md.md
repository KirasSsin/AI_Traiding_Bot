# Агент 18: Опционы и деривативы — Полный аудит

> **Статус:** MVP → v0.4 roadmap  
> **Источники данных:** Deribit WebSocket API, Binance Options  
> **Язык реализации:** Rust (ядерные модели), Python (интеграция/бэктест)  
> **Базовый документ:** Xiaomi MiMo Studio Options.md (Specialist 7)

---

## Содержание

1. [Модели ценообразования опционов](#1-модели-ценообразования-опционов)
   - [1.1 Black-Scholes](#11-black-scholes-merton)
   - [1.2 Binomial Tree (CRR)](#12-binomial-tree-crr-cox-ross-rubinstein)
   - [1.3 Monte Carlo — GBM](#13-monte-carlo--gbm-geometric-brownian-motion)
   - [1.4 Monte Carlo — Lévy Jumps (Merton)](#14-monte-carlo--lévy-jumps-merton-model)
2. [Греки — полные формулы](#2-греки--полные-формулы)
3. [Implied Volatility — Newton-Raphson](#3-implied-volatility--newton-raphson)
4. [Volatility Smile / Skew](#4-volatility-smile--skew)
5. [Опционные стратегии](#5-опционные-стратегии)
   - [5.1 Straddle](#51-long-short-straddle)
   - [5.2 Strangle](#52-long-short-strangle)
   - [5.3 Iron Condor](#53-iron-condor)
   - [5.4 Butterfly Spread](#54-butterfly-spread)
   - [5.5 Calendar Spread](#55-calendar-spread)
   - [5.6 Delta-Hedging](#56-дельта-нейтральное-хеджирование)
   - [5.7 Gamma Scalping](#57-gamma-scalping)
6. [Crypto-specific инструменты](#6-crypto-specific-инструменты)
   - [6.1 Deribit опционная экосистема](#61-deribit-опционная-экосистема)
   - [6.2 IV как индикатор](#62-iv-как-индикатор)
   - [6.3 Funding Rate как proxy Put-Call Parity](#63-funding-rate-как-proxy-put-call-parity)
   - [6.4 GEX / VEX / CEX (из Options.md)](#64-gex--vex--cex-из-optionsmd)
   - [6.5 Max Pain & Pinning](#65-max-pain--pinning)
7. [Production edge cases](#7-production-edge-cases)
8. [Итоговая матрица: ВКЛЮЧИТЬ / ОТБРОСИТЬ](#8-итоговая-матрица)
9. [Топ-3 для хеджирования](#9-топ-3-для-хеджирования)
10. [Rust реализации](#10-rust-реализации)
11. [Конфигурация](#11-конфигурация)

---

## 1. Модели ценообразования опционов

### 1.1 Black-Scholes-Merton

#### Формула

```
C(S,t) = S·N(d₁) − K·e^{−r(T−t)}·N(d₂)
P(S,t) = K·e^{−r(T−t)}·N(−d₂) − S·N(−d₁)

d₁ = [ln(S/K) + (r + σ²/2)·(T−t)] / [σ·√(T−t)]
d₂ = d₁ − σ·√(T−t)

где:
  S       — спотовая цена
  K       — страйк
  T−t     — время до экспирации (годы)
  r       — безрисковая ставка (0 для BTC-номинала)
  σ       — implied volatility (годовая)
  N(·)    — CDF стандартного нормального распределения
```

#### Предпосылки vs крипторынок

| Предпосылка | Нарушение на крипте | Поправка |
|---|---|---|
| Логнормальное распределение | Kurtosis BTC ≈ 9.3 (vs 3.0 норм.) | Fat-tail adjustment через jump-diffusion |
| Постоянная σ | Vol clustering, GARCH α+β ≈ 0.97 | Использовать IV из рынка, не историческую |
| Непрерывный рынок | Ликвидность циклична (сессии) | 24/7 формально OK, но vol clustering |
| Определённый r | Нет «безрискового» актива в крипте | r = 0 для BTC-номинала; funding rate для USD |
| Нет транзакций | Комиссии 0.03–0.05%, спреды 0.1–15% | Учитывать в P&L |
| Непрерывный хедж | Flash crash → спреды 2–3% | TWAP для rebalance |

#### Edge Cases

```
T → 0:        C → max(S−K, 0), Greeks → step function
σ → 0:        C → max(S·e^{−qT} − K·e^{−rT}, 0) — intrinsic value
σ → ∞:        C → S (call), P → K·e^{−rT} (put)
S → 0:        C → 0, P → K·e^{−rT}
S → ∞:        C → S − K·e^{−rT}, P → 0
K = S (ATM):  d₁ = (r + σ²/2)·T / (σ·√T), Δ_call ≈ 0.5 + r·√T/(σ·2√π)
```

#### Вердикт

**ВКЛЮЧИТЬ** — industry standard на Deribit. Базовая модель для всех греков. С поправками: r = 0 (BTC), IV из рынка, vol surface для интерполяции.

---

### 1.2 Binomial Tree (CRR — Cox, Ross, Rubinstein)

#### Формула

```
Дерево с N шагами:

  u = e^{σ·√(Δt)}        — up-фактор
  d = 1/u = e^{−σ·√(Δt)} — down-фактор
  p = (e^{r·Δt} − d) / (u − d) — риск-нейтральная вероятность
  Δt = T/N               — шаг по времени

  Цена актива на шаге i (i восхождений, N−i нисхождений):
  S(i,N) = S₀ · u^i · d^{N−i}

  Цена опциона на экспирации (обратная индукция):
  V(i,N) = max(S(i,N) − K, 0)  для колл
  
  На каждом шаге назад:
  V(i,j) = e^{−r·Δt} · [p · V(i+1,j+1) + (1−p) · V(i,j+1)]
  
  С учётом американского опциона (early exercise):
  V(i,j) = max(Intrinsic(i,j), e^{−r·Δt} · [p · V(i+1,j+1) + (1−p) · V(i,j+1)])
```

#### Преимущества перед BS

- Поддерживает **американские опционы** (early exercise) — BS только европейские
- Поддерживает **дивиденды** (discrete dividends)
- Сходится к BS при N → ∞

#### Edge Cases

```
N < 10:     Неточная аппроксимация, oscillation в ценах
N > 500:    Вычислительная сложность O(N²), diminishing returns
Δt → 0:     Сходится к BS (европейский опцион)
Американский put при r > 0: early exercise оптимален глубоко ITM
Дивидендные даты: узлы дерева должны совпадать с датами выплат
```

#### Вердикт

**ВКЛЮЧИТЬ v0.3** — нужен для американских опционов. На Deribit все опционы европейские, но если добавятся американские площадки — необходим. Для MVP BS достаточно.

---

### 1.3 Monte Carlo — GBM (Geometric Brownian Motion)

#### Формула

```
Модель GBM:
  dS = μ·S·dt + σ·S·dW

  Дискретизация (Euler-Maruyama):
  S(t+Δt) = S(t) · exp[(μ − σ²/2)·Δt + σ·√Δt·Z]

  где Z ~ N(0,1) — стандартное нормальное случайное число

Цена европейского колл-опциона:
  C = e^{−rT} · (1/M) · Σ_{j=1}^{M} max(S_T^{(j)} − K, 0)

  где M = число симуляций (typically 100,000–1,000,000)
  S_T^{(j)} — финальная цена в j-й симуляции

Доверительный интервал:
  CI = C̄ ± z_{α/2} · σ_C / √M
  σ_C = std(payoffs) / √M
  Типичная точность при M = 10⁶: ±0.01% от BS-цены
```

#### Greeks через Monte Carlo (pathwise / likelihood ratio)

```
Pathwise Delta (вспоминаемая производная):
  Δ_MC = e^{−rT} · (1/M) · Σ [1_{S_T > K} · S_T / S₀]

Vega (pathwise):
  ν_MC = e^{−rT} · (1/M) · Σ [1_{S_T > K} · S_T · (Z² − 1) · √T / σ]

Gamma (центральная разность):
  Γ_MC ≈ [C(S₀+h) − 2·C(S₀) + C(S₀−h)] / h²
```

#### Edge Cases

```
M < 10,000:   Шум > 1% от цены, непригодно
M > 10⁷:      Вычислительная сложность, diminishing returns
T < 1 день:   Сходимость плохая (мало шагов)
Path-dependent опционы (barrier, asian): MC — единственный метод
Американские опционы: нужен Longstaff-Schwartz (LSM)
```

#### Вердикт

**ВКЛЮЧИТЬ v0.4** — нужен для экзотических опционов (barrier, asian, lookback) и для валидации BS. Не для MVP — BS + binomial достаточно.

---

### 1.4 Monte Carlo — Lévy Jumps (Merton Model)

#### Формула

```
Merton Jump-Diffusion:
  dS/S = (μ − λ·k)·dt + σ·dW + J·dN

  где:
    λ = интенсивность прыжков (jump intensity, среднее число прыжков/год)
    k = E[e^J − 1] — средний размер прыжка (drift adjustment)
    J ~ N(μ_J, σ_J²) — размер прыжка (лог-нормальный)
    dN ~ Poisson(λ·dt) — счётчик прыжков

Цена колл-опциона (Merton, 1976):
  C = Σ_{n=0}^{∞} [e^{−λ'T} · (λ'T)^n / n!] · BS(S, K, T, r_n, σ_n)

  где:
    λ' = λ·(1 + k)
    r_n = r − λ·k + n·ln(1+k)/T
    σ_n = √(σ² + n·σ_J²/T)
    
  Практически: сумма обрезается при n > 20 (вероятность > 20 прыжков за T < 1 год ≈ 0)

Параметры для BTC (эмпирические):
  λ ≈ 3–5 (3–5 прыжков в год)
  μ_J ≈ −0.02 (средний прыжок −2%)
  σ_J ≈ 0.05 (σ прыжков 5%)
```

#### Edge Cases

```
λ → 0:     Сводится к обычному BS (без прыжков)
λ → ∞:     Непрерывные прыжки, σ_effective → ∞
σ_J → 0:   Прыжки фиксированного размера (Poisson-сдвиг)
μ_J < 0:   Чаще падения (crash risk) — типично для крипты
Тяжёлые хвосты: Kurtosis_модели >> 3, хорошо описывает крипту
```

#### Вердикт

**ОТБРОСИТЬ для MVP, ВКЛЮЧИТЬ v0.5** — математически элегантен, но:
1. 5 параметров (μ, σ, λ, μ_J, σ_J) — калибровка нестабильна
2. Deribit не предоставляет данные для калибровки прыжков
3. BS + IV surface покрывают 90% потребностей
4. Стоит добавить если бот будет торговать OTM puts (crash protection)

---

## 2. Греки — полные формулы

Все греки рассчитаны в Options.md (раздел 3). Ниже — сводная таблица с формулами для r = 0 (крипто).

| Greek | Формула (Call, r=0) | Формула (Put, r=0) | Ключевое свойство |
|---|---|---|---|
| **Delta (Δ)** | N(d₁) | N(d₁) − 1 | ∈ (0,1) call, ∈ (−1,0) put |
| **Gamma (Γ)** | N'(d₁) / [S·σ·√T] | **Та же** | Одинакова для call/put |
| **Theta (Θ)** | −S·N'(d₁)·σ / [2·√T·365] | −S·N'(d₁)·σ / [2·√T·365] | Отрицательна для long |
| **Vega (ν)** | S·N'(d₁)·√T / 100 | **Та же** | Одинакова для call/put |
| **Rho (ρ)** | ≈ 0 (BTC-номинал) | ≈ 0 (BTC-номинал) | Не используется в крипте |

### Вторичные греки (из Options.md)

| Greek | Формула | Применение |
|---|---|---|
| **Vanna** | −N'(d₁)·d₂/σ | Чувствительность Δ к изменению σ |
| **Charm** | N'(d₁)·d₂ / [2·(T−t)] | Изменение Δ во времени |
| **Vomma (Volga)** | ν·d₁·d₂/σ | Чувствительность ν к изменению σ |
| **Speed** | −Γ/S · [d₁/(σ√T) + 1] | Третья производная по S |

### Edge Cases всех греков

```
T → 0 (экспирация):
  Γ_ATM → ∞ (gamma explosion)
  Δ → step function (0 или 1)
  ν → 0, Θ → 0 (кроме ATM)
  
S = K (ATM):
  Δ_call ≈ 0.5 (exact при r=0)
  Γ максимальна
  ν максимальна

Deep ITM (S >> K):
  Δ → 1, Γ → 0, ν → 0
  Опцион ведёт себя как базовый актив

Deep OTM (S << K):
  Δ → 0, Γ → 0, ν → 0
  Опцион ≈ worthless
```

---

## 3. Implied Volatility — Newton-Raphson

#### Формула

```
Цель: найти σ* такую, что BS(S, K, T, r, σ*) = Market_Price

Метод Ньютона-Рафсона:
  σ_{n+1} = σ_n − [BS(σ_n) − P_market] / Vega(σ_n)

  где Vega(σ_n) = ∂BS/∂σ = S·N'(d₁)·√T / 100

Алгоритм:
  1. σ₀ = initial guess (ATM: σ₀ = Market_Price × √(2π) / (S·√T))
  2. Повторять:
     price = BS(σ_n)
     vega  = S · norm_pdf(d₁(σ_n)) · √T
     σ_{n+1} = σ_n − (price − P_market) / vega
  3. Пока |σ_{n+1} − σ_n| > ε (ε = 1e−6)
  4. Максимум 100 итераций

Fallback при расхождении:
  Если Newton-Raphson не сходится → Bisection на [0.01, 5.0]
  50 итераций бисекции гарантируют точность до 0.01%
```

#### Edge Cases

```
Deep OTM опцион (P_market ≈ 0):
  IV ≈ 0 (или не определена)
  Newton-Raphson расходится → fallback на bisection
  
Deep ITM опцион:
  IV чувствительна к точности цены (tick size)
  Спред > 1% → IV шумная

P_market < intrinsic:
  Арбитраж! IV не существует (отрицательная)
  Действие: reject опцион как ошибочный

Vega ≈ 0 (T → 0 или deep OTM):
  Деление на ~0 в Newton → расходится
  Использовать только bisection
```

#### Rust реализация

```rust
/// Implied Volatility via Newton-Raphson with bisection fallback
pub fn implied_volatility(
    market_price: f64,
    s: f64,
    k: f64,
    t: f64,
    r: f64,
    is_call: bool,
) -> Result<f64, IvError> {
    // Check arbitrage bound
    let intrinsic = if is_call {
        (s - k * (-r * t).exp()).max(0.0)
    } else {
        (k * (-r * t).exp() - s).max(0.0)
    };
    
    if market_price < intrinsic - 1e-10 {
        return Err(IvError::BelowIntrinsic);
    }
    if market_price < 1e-12 {
        return Ok(0.0); // worthless option
    }
    
    // Initial guess: Brenner-Subrahmanyam for ATM
    let mut sigma = (market_price * (2.0 * std::f64::consts::PI).sqrt()) 
                    / (s * t.sqrt());
    sigma = sigma.max(0.01).min(5.0);
    
    // Newton-Raphson
    for _ in 0..100 {
        let (price, vega) = black_scholes_price_and_vega(s, k, t, r, sigma, is_call);
        let diff = price - market_price;
        
        if diff.abs() < 1e-10 {
            return Ok(sigma);
        }
        
        if vega < 1e-15 {
            break; // Vega too small, fallback to bisection
        }
        
        let new_sigma = sigma - diff / vega;
        
        if new_sigma <= 0.0 || new_sigma > 10.0 {
            break; // Out of bounds, fallback
        }
        
        if (new_sigma - sigma).abs() < 1e-8 {
            return Ok(new_sigma);
        }
        
        sigma = new_sigma;
    }
    
    // Bisection fallback
    let mut lo = 0.001f64;
    let mut hi = 5.0f64;
    
    for _ in 0..100 {
        let mid = (lo + hi) / 2.0;
        let price = black_scholes_price(s, k, t, r, mid, is_call);
        
        if (price - market_price).abs() < 1e-10 {
            return Ok(mid);
        }
        
        if price > market_price {
            hi = mid;
        } else {
            lo = mid;
        }
        
        if hi - lo < 1e-10 {
            return Ok(mid);
        }
    }
    
    Ok((lo + hi) / 2.0)
}

#[derive(Debug)]
pub enum IvError {
    BelowIntrinsic,
    MaxIterations,
    InvalidInput,
}
```

#### Вердикт

**ВКЛЮЧИТЬ** — критический компонент. IV — основа для оценки опционов, построения vol surface, определения «дешёвых/дорогих» опционов.

---

## 4. Volatility Smile / Skew

#### Параметризация SVI (Stochastic Volatility Inspired)

```
w(k) = a + b·{ρ·(k − m) + √[(k − m)² + σ²]}

где:
  k = ln(K/F)     — log-moneyness (лог-страйк к форварду)
  w(k) = IV²·T    — total implied variance
  a ≥ 0           — вертикальный сдвиг
  b > 0           — наклон крыльев
  |ρ| < 1         — skew (ρ < 0 для put skew, ρ > 0 для call skew)
  m               — горизонтальный сдвиг
  σ > 0           — ширина дна smile

IV из SVI:
  σ(k) = √[w(k) / T]
```

#### Crypto-specific: инвертированный skew

```
Акции:  IV(put 25δ) > IV(call 25δ) — put skew (хеджирование портфелей)
Крипта: IV(call 25δ) > IV(put 25δ) в 40–60% случаев — call skew (FOMO)

Risk Reversal 25δ:
  RR₂₅ = IV(call, Δ=25) − IV(put, Δ=−25)
  RR > 0: calls дороже (бычий сентимент)
  RR < 0: puts дороже (медвежий сентимент / crash fear)

Butterfly 25δ:
  BF₂₅ = [IV(call 25δ) + IV(put −25δ)] / 2 − IV_ATM
  BF > 0: smile выпуклый
  BF измеряет кривизну, а не наклон
```

#### Вердикт

**ВКЛЮЧИТЬ** — vol surface через SVI: интерполяция IV для нестандартных страйков, мониторинг skew как sentiment-индикатор. RR₂₅ переход из положительного в отрицательное = сигнал смены сентимента.

---

## 5. Опционные стратегии

### 5.1 Long/Short Straddle

#### Формула

```
Long Straddle:
  Покупка ATM call + ATM put (один страйк K, одна экспирация T)
  
  Payoff = max(S_T − K, 0) + max(K − S_T, 0) = |S_T − K|
  Cost = C(K) + P(K) = 2 × ATM премия
  Breakeven: S_T = K ± (C + P)
  Макс. убыток: C + P (ограничен)
  Макс. прибыль: неограничен (в обе стороны)
  
  Прибыльна если: |S_T − K| > C + P (реализованная вол > implied)

Short Straddle:
  Продажа ATM call + ATM put
  
  Payoff = −|S_T − K|
  Макс. прибыль: C + P (ограничен)
  Макс. убыток: неограничен
  Прибыльна если: |S_T − K| < C + P (реализованная вол < implied)
```

#### Edge Cases

```
Long Straddle + высокая IV:  дорогой вход, нужен большой move
Short Straddle + flash crash: безграничный убыток
Тета-распад: long straddle теряет ~Θ_call + Θ_put в день
Gamma при экспирации: ATM straddle gamma → ∞, хедж невозможен
```

#### Crypto Application

Long straddle перед FOMC/CPI/Major ETF news. Short straddle = variance risk premium harvesting (продажа дорогой implied vol).

#### Вердикт

**ВКЛЮЧИТЬ как secondary стратегия** — long straddle для event-driven торговли (v0.3+). Short straddle НЕ рекомендуется для бота (безграничный убыток, нужен ручной контроль).

---

### 5.2 Long/Short Strangle

#### Формула

```
Long Strangle:
  Покупка OTM call (K_H) + OTM put (K_L), K_L < S < K_H
  
  Payoff = max(S_T − K_H, 0) + max(K_L − S_T, 0)
  Cost = C(K_H) + P(K_L) < Straddle cost (оба OTM)
  Breakeven (верхний): S_T = K_H + C + P
  Breakeven (нижний): S_T = K_L − C − P
  Нужен БОЛЬШИЙ move чем straddle для прибыли

Short Strangle:
  Продажа OTM call + OTM put
  Макс. прибыль: C + P
  Макс. убыток: неограничен (в обе стороны)
  Прибыльна если: K_L < S_T < K_H
```

#### Edge Cases

```
Выбор страйков: обычно 25δ OTM (Δ = ±0.25)
Short strangle + trending market: убытки на одной стороне
  могут превысить прибыль на другой
Комиссии: 4 ноги (2 покупки + 2 продажи при закрытии)
```

#### Вердикт

**ОТБРОСИТЬ** — менее эффективен чем straddle (нужен больший move) или iron condor (ограниченный убыток). Нет преимущества.

---

### 5.3 Iron Condor

#### Формула

```
Iron Condor = Short Strangle + Long Strangle (wings)
  Продать OTM put (K_2) + продать OTM call (K_3)
  Купить дальний OTM put (K_1) + купить дальний OTM call (K_4)
  
  K_1 < K_2 < S < K_3 < K_4

  Payoff:
    S_T < K_1:  Loss = (K_2 − K_1) − net_premium
    K_1 < S_T < K_2: Loss = (K_2 − S_T) − net_premium
    K_2 < S_T < K_3: Profit = net_premium (макс.)
    K_3 < S_T < K_4: Loss = (S_T − K_3) − net_premium
    S_T > K_4:  Loss = (K_4 − K_3) − net_premium

  Макс. прибыль: net_premium = C(K_3) + P(K_2) − C(K_4) − P(K_1)
  Макс. убыток: wing_width − net_premium (ограничен!)
  Win rate: обычно 60–80% (широкий range)
  Return on risk: обычно 15–30%
```

#### Edge Cases

```
Слишком узкий range: комиссии съедают прибыль
Слишком широкий range: низкий return, не стоит риска
IV spike: все ноги теряют (vega отрицательная)
Pin risk при экспирации: цена между страйками → assignment risk
```

#### Crypto Application

Продажа iron condor при высокой IV (после flash crash → IV spike) когда ожидается возврат к mean. High IV = больше премии = больше запас.

#### Вердикт

**ВКЛЮЧИТЬ v0.4** — лучшая стратегия для short vol с ограниченным риском. Использовать при IV > 75-го перцентиля.

---

### 5.4 Butterfly Spread

#### Формула

```
Long Butterfly (ATM):
  Купить call(K−d) + продать 2×call(K) + купить call(K+d)
  
  Payoff:
    |S_T − K| < d:  Profit ≈ d − net_cost (макс.)
    |S_T − K| > d:  Loss → net_cost (ограничен)
    
  Макс. прибыль: d − net_cost
  Макс. убыток: net_cost
  Breakeven: K ± (d − net_cost)

Short Butterfly:
  Зеркальная: продать wings, купить body
  Прибыльна при high volatility (big move)
```

#### Edge Cases

```
d (крылья) слишком узкие: комиссии > прибыль
Комиссии: 4 ноги (3 транзакции minimum на Deribit)
Ликвидность на крайних страйках: спред может быть 5–15%
Pin risk: если S_T ≈ K → максимальная прибыль, но assignment
```

#### Вердикт

**ОТБРОСИТЬ** — слишком узкая зона прибыли для алгоритмической торговли. Iron Condor лучше: шире зона прибыли, тот же limited risk. Butterfly нужен для ручной торговли с точным прогнозом направления.

---

### 5.5 Calendar Spread (Horizontal / Time Spread)

#### Формула

```
Long Calendar Spread:
  Продать ближний call(K, T₁) + купить дальний call(K, T₂), T₂ > T₁

  Payoff на момент T₁:
    Зависит от IV-структуры (term structure)
    Прибыльна если: IV ближнего > IV дальнего (backwardation)
    Или если: S_T₁ ≈ K (theta decay ближнего > дальнего)

  Theta relationship:
    Θ_near > Θ_far (ближний распадается быстрее)
    Net theta = Θ_near − Θ_far > 0 → зарабатываем на распаде

  Vega relationship:
    ν_near < ν_far (дальний более чувствителен к IV)
    Net vega = ν_far − ν_near > 0 → прибыль при росте IV

Short Calendar Spread:
  Зеркальная: купить ближний, продать дальний
  Прибыльна при падении IV или движении S далеко от K
```

#### Crypto-specific: Deribit term structure

```
BTC term structure обычно в contango:
  IV_7д < IV_30д < IV_90д < IV_180д
  
  При flash crash: IV_7д spike > IV_30д (backwardation)
  → Это момент для long calendar: продать дорогую ближнюю IV,
    купить дешёвую дальнюю
```

#### Edge Cases

```
Early exercise: не проблема (Deribit = европейские)
IV term structure инвертируется редко, но при этом — edge
Комиссии: 2 ноги на вход + 2 ноги на закрытие первой ноги + 2 ноги на закрытие второй
Roll risk: вторая нога остаётся открытой после T₁
```

#### Вердикт

**ВКЛЮЧИТЬ v0.4** — calendar spread для торговли IV term structure. Edge: при flash crash покупать календарь (продавать дорогую ближнюю vol). Ограниченный риск.

---

### 5.6 Дельта-нейтральное хеджирование

Полностью описано в Options.md (раздел 10). Ключевые формулы:

```
Хеджное соотношение:
  N_hedge = −Δ_portfolio × N_options

Rebalance условие:
  |Δ_portfolio × S − Delta_hedged × S| > Threshold
  
  Threshold = 0.5–2% от номинала

Расходы на rebalance:
  Cost = Σ |N_hedge_i − N_hedge_{i−1}| × S × commission
```

#### Вердикт

**ВКЛЮЧИТЬ** — критический. Дельта-хедж = основа управления опционным портфелем.

---

### 5.7 Gamma Scalping

#### Формула

```
Gamma Scalping = Long Gamma (long straddle или long options) + Delta-нейтральный хедж

P&L от гамма-сквопа за период Δt:
  P&L_γ ≈ ½ · Γ · (ΔS)² − Θ · Δt

  где:
    Γ = гамма позиции (положительная для long options)
    ΔS = реализованное изменение цены за Δt
    Θ = тета позиции (отрицательная для long options — «плата за гамму»)

  Прибыльна если: ½ · Γ · (ΔS)² > |Θ| · Δt
  Эквивалент: реализованная вол > implied vol

  Условие прибыльности:
    σ_realized > σ_implied
    Т.е. рынок движется больше, чем ожидает опционная премия
```

#### Механика

```
1. Купить ATM straddle (long gamma, long vega, short theta)
2. Поддерживать delta-neutral через rebalance:
   - Цена выросла → Δ стал > 0.5 → продать фьючерсы (снизить Δ до 0)
   - Цена упала → Δ стал < 0.5 → купить фьючерсы (увеличить Δ до 0)
3. Каждый rebalance = покупка дешево, продажа дорого (buy low, sell high)
4. Прибыль от rebalance > тета-распад → профит
```

#### Edge Cases

```
Низкая волатильность: rebalance даёт мало P&L, тета съедает
Flash crash: rebalance невозможен (спреды 2–3%)
Комиссии на rebalance: каждые 15–60 мин × commission
Оптимальная частота rebalance: зависит от λ = commission / (σ·S·√Δt)
```

#### Вердикт

**ВКЛЮЧИТЬ как концепция, НЕ как отдельная стратегия** — gamma scalping = логика long straddle + delta hedging. Отдельной стратегией не нужен.

---

## 6. Crypto-specific инструменты

### 6.1 Deribit опционная экосистема

```
API:      wss://www.deribit.com/ws/api/v2
Каналы:   book.BTC.option, ticker.BTC.option.{instrument}
Данные:   Greeks, OI, IV, Volume в реальном времени
Тип:      Европейские опционы (нет early exercise)
Номинал:  BTC (деноминированы в BTC)
          Некоторые инструменты — USD-номинированные
Контракт: 1 BTC для BTC-опционов
Экспирации: Ежедневные, еженедельные, ежемесячные, квартальные

Комиссии: 0.03% от стоимости базового актива (delivery)
          0.03–0.05% trading fee (maker/taker)
```

### 6.2 IV как индикатор

```
IV30 (30-дневная implied vol):
  - От Deribit DVOL Index или рассчитанная со 30-дневных опционов
  - Типичный диапазон BTC: 40–120% (годовых)
  
  Правила:
  1. IV < Percentile_25 за 90 дней → опционы дёшево → покупать vol
  2. IV > Percentile_75 за 90 дней → опционы дорого → продавать vol  
  3. IV spike > 2σ от средней → ожидать mean-reversion IV
  4. IV trend (растёт 5+ дней) → подтверждение тренда волатильности

Realized Volatility (RV):
  RV_30d = √(252/30) × √[Σ(ln(Sᵢ/Sᵢ₋₁))²]

  Variance Risk Premium:
  VRP = IV² − RV²
  
  Если VRP > 0 (типично): опционы переоценены, short vol прибыльна
  Если VRP < 0 (редко): опционы недооценены, long vol прибыльна

IV/RV Ratio:
  IV/RV > 1.2 → продавать опционы (short vol)
  IV/RV < 0.8 → покупать опционы (long vol)
  IV/RV ≈ 1.0 → нет edge
```

### 6.3 Funding Rate как proxy Put-Call Parity

#### Put-Call Parity

```
Классическая:
  C − P = S − K·e^{−rT}

Для r = 0 (BTC-номинал):
  C − P = S − K

Означает: если знаем цену колл, можем вычислить цен пут и наоборот.
Любое отклонение = арбитраж.
```

#### Funding Rate как proxy

```
Perpetual swap funding rate ≈ cost of carry для крипты

  Если funding > 0: longs платят shorts
    → Cost of carry > 0
    → Эквивалент r > 0
    → C − P < S − K (calls дешевле относительно parity)
    
  Если funding < 0: shorts платят longs
    → Cost of carry < 0  
    → Эквивалент r < 0
    → C − P > S − K (calls дороже)

Практическое применение:
  fair_r = funding_rate × 3 × 365 (8ч funding → годовая ставка)
  
  Пример: funding = +0.05% за 8ч → r_proxy ≈ 55% годовых
  При таком r путы значительно дороже (ρ путов отрицательна и велика)

  Правило: если |C − P − (S − K·e^{−r_proxy·T})| > threshold:
    Обнаружен арбитраж (или ошибка в IV)
    Логировать и использовать для валидации опционных цен
```

#### Вердикт

**ВКЛЮЧИТЬ как валидационный инструмент** — funding rate proxy для put-call parity = способ обнаружить mispricing опционов без лимитного ордербука.

---

### 6.4 GEX / VEX / CEX (из Options.md)

Полностью описаны в Options.md (разделы 4–6). Вердикты:

| Инструмент | Вердикт | Приоритет |
|---|---|---|
| GEX | ВКЛЮЧИТЬ — primary опционный индикатор | Высокий |
| VEX (Vanna) | ВКЛЮЧИТЬ — secondary, pre-event фильтр | Средний |
| CEX (Charm) | ВКЛЮЧИТЬ — только T < 7 дней | Низкий |

---

### 6.5 Max Pain & Pinning

Описано в Options.md (разделы 9, 12). Вердикт: **ВКЛЮЧИТЬ как фильтр экспирации** (Средний приоритет).

---

## 7. Production edge cases

Полностью описаны в Options.md (раздел 14). Ключевые:

| Edge Case | Триггер | Действие |
|---|---|---|
| Funding > 0.15% / 8ч | `abs(funding) > 0.0015` | Блокировка входа |
| Funding > 0.30% / 8ч | `abs(funding) > 0.003` | Закрытие всех позиций |
| Flash crash (wick > 5σ) | `|P − median| > 5×MAD` | Фильтрация тика |
| WS down > 15s | `last_msg_age > 15s` | REST fallback |
| Option pinning (T < 3д) | `|S − K_maxpain| < 2%` | Range-режим |
| Negative GEX | `total_gex < 0` | Расширенные stops |

---

## 8. Итоговая матрица

### ВКЛЮЧИТЬ

| # | Инструмент | Роль | Приоритет | Версия |
|---|---|---|---|---|
| 1 | **Black-Scholes** | Базовая модель ценообразования | Критический | MVP |
| 2 | **Greeks (Δ, Γ, Θ, ν)** | Управление рисками | Критический | MVP |
| 3 | **Implied Volatility (Newton-Raphson)** | Оценка опционов | Критический | MVP |
| 4 | **GEX** | Дилерские потоки, режим рынка | Высокий | v0.2 |
| 5 | **Vol Surface / SVI** | Интерполяция IV, sentiment | Высокий | v0.2 |
| 6 | **Delta-Neutral Hedging** | Управление портфелем | Критический | v0.2 |
| 7 | **IV как индикатор** | VRP, определение дешёвых опционов | Высокий | v0.2 |
| 8 | **Funding Rate → PCP proxy** | Валидация опционных цен | Средний | v0.3 |
| 9 | **Put/Call Ratio** | Sentiment-фильтр | Средний | v0.3 |
| 10 | **Max Pain / Pinning** | Фильтр экспирации | Средний | v0.3 |
| 11 | **Iron Condor** | Short vol с limited risk | Средний | v0.4 |
| 12 | **Calendar Spread** | Торговля IV term structure | Средний | v0.4 |
| 13 | **VEX (Vanna)** | Pre-event фильтр | Средний | v0.4 |
| 14 | **CEX (Charm)** | End-of-day фильтр | Низкий | v0.4 |
| 15 | **Binomial Tree** | Американские опционы | Средний | v0.3 |
| 16 | **Straddle** | Event-driven торговля | Средний | v0.3 |
| 17 | **Variance Risk Premium** | Теоретическая основа short vol | Средний | v0.3 |

### ОТБРОСИТЬ

| # | Инструмент | Причина отклонения |
|---|---|---|
| 1 | **Monte Carlo (GBM)** | Избыточен для европейских опционов (BS аналитически точен). Нужен только для экзотики (barrier, asian) — v0.5 |
| 2 | **Monte Carlo (Lévy Jumps)** | 5 параметров, калибровка нестабильна. Deribit не предоставляет данные для calibration. BS + IV surface покрывают потребности |
| 3 | **Strangle** | Менее эффективен: либо straddle (больше gamma), либо iron condor (limited risk). Нет ниши |
| 4 | **Butterfly Spread** | Слишком узкая зона прибыли для алгоритма. Iron Condor лучше по всем параметрам |
| 5 | **Gamma Scalping** | Не отдельная стратегия, а комбинация long straddle + delta hedge. Покрыто существующими компонентами |
| 6 | **Rho (ρ)** | Равна 0 для BTC-номинала. Не используется |

---

## 9. Топ-3 для хеджирования

Для крипто-бота, торгующего фьючерсами на BTC/ETH:

### #1: OTM Put Hedge (защита длинных позиций)

```
Когда: размер позиции > 5% equity + Total GEX < 0 + IV < P25
Что: купить OTM put с Δ = −0.15 .. −0.25, 30 дней до экспирации
Бюджет: 2–3% от номинала позиции
Edge: страхование от flash crash при «дешёвой» IV
Преимущество перед фиксированным stop-loss: не срабатывает на wicks,
  защищает gap down, не требует мониторинга 24/7
```

### #2: GEX-based Position Sizing (динамический размер позиции)

```
Когда: всегда (мониторинг каждые 5 минут)
Что: 
  Total GEX > 0 (high) → стандартный sizing (стабильный режим)
  Total GEX < 0 (high) → sizing × 0.5 + расширенный stop (нестабильный режим)
  |Total GEX| < P25 → sizing × 0.7 (неопределённый режим)
Edge: адаптация к дилерским потокам без опционных позиций
Преимущество: не требует опционного счёта, работает через Deribit API данные
```

### #3: Calendar Spread при IV Spike (защита от vol crush)

```
Когда: IV_7д spike > IV_30д + 10% (backwardation)
Что: продать ближний опцион (7д) + купить дальний (30д), один страйк
Edge: зарабатывает на normalization IV term structure
Преимущество: limited risk, не зависит от направления цены
```

---

## 10. Rust реализации

### 10.1 Black-Scholes + Greeks

```rust
use std::f64::consts::PI;

/// Standard normal CDF (Abramowitz & Stegun approximation)
pub fn norm_cdf(x: f64) -> f64 {
    if x < -8.0 { return 0.0; }
    if x > 8.0 { return 1.0; }
    
    let a1 = 0.254829592;
    let a2 = -0.284496736;
    let a3 = 1.421413741;
    let a4 = -1.453152027;
    let a5 = 1.061405429;
    let p = 0.3275911;
    
    let sign = if x < 0.0 { -1.0 } else { 1.0 };
    let x = x.abs();
    
    let t = 1.0 / (1.0 + p * x);
    let y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * (-x * x / 2.0).exp();
    
    0.5 * (1.0 + sign * y)
}

/// Standard normal PDF
pub fn norm_pdf(x: f64) -> f64 {
    (-x * x / 2.0).exp() / (2.0 * PI).sqrt()
}

/// Black-Scholes option price
pub fn black_scholes_price(
    s: f64, k: f64, t: f64, r: f64, sigma: f64, is_call: bool,
) -> f64 {
    if t <= 0.0 {
        return if is_call { (s - k).max(0.0) } else { (k - s).max(0.0) };
    }
    let sqrt_t = t.sqrt();
    let d1 = ((s / k).ln() + (r + sigma * sigma / 2.0) * t) / (sigma * sqrt_t);
    let d2 = d1 - sigma * sqrt_t;
    let df = (-r * t).exp();
    
    if is_call {
        s * norm_cdf(d1) - k * df * norm_cdf(d2)
    } else {
        k * df * norm_cdf(-d2) - s * norm_cdf(-d1)
    }
}

/// All Greeks in one call
pub struct Greeks {
    pub price: f64,
    pub delta: f64,
    pub gamma: f64,
    pub theta: f64,
    pub vega: f64,
}

pub fn black_scholes_greeks(
    s: f64, k: f64, t: f64, r: f64, sigma: f64, is_call: bool,
) -> Greeks {
    if t <= 1e-15 {
        let intrinsic = if is_call { (s - k).max(0.0) } else { (k - s).max(0.0) };
        return Greeks {
            price: intrinsic,
            delta: if is_call { if s > k { 1.0 } else { 0.0 } } 
                   else { if s < k { -1.0 } else { 0.0 } },
            gamma: 0.0, theta: 0.0, vega: 0.0,
        };
    }
    
    let sqrt_t = t.sqrt();
    let d1 = ((s / k).ln() + (r + sigma * sigma / 2.0) * t) / (sigma * sqrt_t);
    let d2 = d1 - sigma * sqrt_t;
    let npd1 = norm_pdf(d1);
    let df = (-r * t).exp();
    let nd1 = norm_cdf(d1);
    let nd2 = norm_cdf(d2);
    
    let gamma = npd1 / (s * sigma * sqrt_t);
    let vega = s * npd1 * sqrt_t / 100.0;
    
    if is_call {
        let price = s * nd1 - k * df * nd2;
        let delta = nd1;
        let theta = -(s * npd1 * sigma / (2.0 * sqrt_t) 
                      + r * k * df * nd2) / 365.0;
        Greeks { price, delta, gamma, theta, vega }
    } else {
        let price = k * df * norm_cdf(-d2) - s * norm_cdf(-d1);
        let delta = nd1 - 1.0;
        let theta = -(s * npd1 * sigma / (2.0 * sqrt_t) 
                      - r * k * df * norm_cdf(-d2)) / 365.0;
        Greeks { price, delta, gamma, theta, vega }
    }
}
```

### 10.2 Binomial Tree (CRR)

```rust
/// CRR Binomial Tree — supports American options
pub fn binomial_tree_price(
    s: f64, k: f64, t: f64, r: f64, sigma: f64,
    n_steps: usize, is_call: bool, is_american: bool,
) -> f64 {
    let dt = t / n_steps as f64;
    let u = (sigma * dt.sqrt()).exp();
    let d = 1.0 / u;
    let disc = (-r * dt).exp();
    let p = (disc.recip() - d) / (u - d);
    
    // Asset prices at maturity
    let mut asset = vec![0.0; n_steps + 1];
    for i in 0..=n_steps {
        asset[i] = s * u.powi(i as i32) * d.powi((n_steps - i) as i32);
    }
    
    // Option values at maturity
    let mut opt = vec![0.0; n_steps + 1];
    for i in 0..=n_steps {
        opt[i] = if is_call {
            (asset[i] - k).max(0.0)
        } else {
            (k - asset[i]).max(0.0)
        };
    }
    
    // Backward induction
    for step in (0..n_steps).rev() {
        for i in 0..=step {
            let continuation = disc * (p * opt[i + 1] + (1.0 - p) * opt[i]);
            
            if is_american {
                let intrinsic = if is_call {
                    (s * u.powi(i as i32) * d.powi((step - i) as i32) - k).max(0.0)
                } else {
                    (k - s * u.powi(i as i32) * d.powi((step - i) as i32)).max(0.0)
                };
                opt[i] = continuation.max(intrinsic);
            } else {
                opt[i] = continuation;
            }
        }
    }
    
    opt[0]
}
```

### 10.3 Monte Carlo GBM

```rust
use rand::prelude::*;
use rand_distr::StandardNormal;

/// Monte Carlo pricer for European options under GBM
pub fn monte_carlo_price(
    s: f64, k: f64, t: f64, r: f64, sigma: f64,
    is_call: bool, n_sims: usize, n_steps: usize,
) -> (f64, f64) { // (price, std_error)
    let dt = t / n_steps as f64;
    let drift = (r - 0.5 * sigma * sigma) * dt;
    let diffusion = sigma * dt.sqrt();
    let df = (-r * t).exp();
    
    let mut rng = thread_rng();
    let mut sum = 0.0;
    let mut sum_sq = 0.0;
    
    for _ in 0..n_sims {
        let mut log_s = s.ln();
        for _ in 0..n_steps {
            let z: f64 = rng.sample(StandardNormal);
            log_s += drift + diffusion * z;
        }
        let s_t = log_s.exp();
        let payoff = if is_call {
            (s_t - k).max(0.0)
        } else {
            (k - s_t).max(0.0)
        };
        let pv = df * payoff;
        sum += pv;
        sum_sq += pv * pv;
    }
    
    let mean = sum / n_sims as f64;
    let variance = sum_sq / n_sims as f64 - mean * mean;
    let std_error = (variance / n_sims as f64).sqrt();
    
    (mean, std_error)
}
```

### 10.4 Implied Volatility (Newton-Raphson + Bisection)

```rust
/// Implied volatility via Newton-Raphson with bisection fallback
pub fn implied_volatility(
    market_price: f64, s: f64, k: f64, t: f64, r: f64, is_call: bool,
) -> Result<f64, &'static str> {
    if t <= 0.0 { return Err("T must be positive"); }
    
    let intrinsic = if is_call {
        (s - k * (-r * t).exp()).max(0.0)
    } else {
        (k * (-r * t).exp() - s).max(0.0)
    };
    
    if market_price < intrinsic - 1e-10 { return Err("Below intrinsic"); }
    if market_price < 1e-12 { return Ok(0.0); }
    
    // Brenner-Subrahmanyam initial guess
    let mut sigma = (market_price * (2.0 * PI).sqrt()) / (s * t.sqrt());
    sigma = sigma.clamp(0.001, 5.0);
    
    // Newton-Raphson
    for _ in 0..100 {
        let greeks = black_scholes_greeks(s, k, t, r, sigma, is_call);
        let diff = greeks.price - market_price;
        
        if diff.abs() < 1e-10 { return Ok(sigma); }
        
        let vega_abs = s * norm_pdf(
            ((s / k).ln() + (r + sigma * sigma / 2.0) * t) / (sigma * t.sqrt())
        ) * t.sqrt();
        
        if vega_abs < 1e-15 { break; }
        
        let new_sigma = sigma - diff / vega_abs;
        if new_sigma <= 0.0 || new_sigma > 10.0 { break; }
        if (new_sigma - sigma).abs() < 1e-8 { return Ok(new_sigma); }
        sigma = new_sigma;
    }
    
    // Bisection fallback
    let mut lo = 0.001f64;
    let mut hi = 5.0f64;
    
    for _ in 0..100 {
        let mid = (lo + hi) / 2.0;
        let price = black_scholes_price(s, k, t, r, mid, is_call);
        
        if (price - market_price).abs() < 1e-10 { return Ok(mid); }
        if price > market_price { hi = mid; } else { lo = mid; }
        if hi - lo < 1e-10 { return Ok(mid); }
    }
    
    Ok((lo + hi) / 2.0)
}
```

### 10.5 GEX Calculator

```rust
/// Single option's GEX contribution
pub fn gex_contribution(
    oi: f64, gamma: f64, spot: f64, is_call: bool,
) -> f64 {
    let direction = if is_call { 1.0 } else { -1.0 };
    direction * oi * gamma * spot
}

/// Aggregate GEX by strike
pub fn calculate_gex(
    options: &[(f64, f64, f64, bool)], // (strike, oi, gamma, is_call)
    spot: f64,
) -> (std::collections::BTreeMap<u64, f64>, f64) {
    let mut by_strike: std::collections::BTreeMap<u64, f64> = 
        std::collections::BTreeMap::new();
    
    for &(strike, oi, gamma, is_call) in options {
        let gex = gex_contribution(oi, gamma, spot, is_call);
        let key = (strike * 100.0) as u64;
        *by_strike.entry(key).or_insert(0.0) += gex;
    }
    
    let total_gex: f64 = by_strike.values().sum();
    (by_strike, total_gex)
}
```

### 10.6 Iron Condor

```rust
/// Iron Condor P&L calculation
pub struct IronCondor {
    pub k1: f64, // long put (protection)
    pub k2: f64, // short put
    pub k3: f64, // short call
    pub k4: f64, // long call (protection)
    pub net_premium: f64,
}

impl IronCondor {
    pub fn payoff(&self, s_t: f64) -> f64 {
        let put_long = (self.k1 - s_t).max(0.0);
        let put_short = -(self.k2 - s_t).max(0.0);
        let call_short = -(s_t - self.k3).max(0.0);
        let call_long = (s_t - self.k4).max(0.0);
        
        put_long + put_short + call_short + call_long + self.net_premium
    }
    
    pub fn max_profit(&self) -> f64 { self.net_premium }
    
    pub fn max_loss(&self) -> f64 {
        let wing_put = self.k2 - self.k1;
        let wing_call = self.k4 - self.k3;
        wing_put.min(wing_call) - self.net_premium
    }
    
    pub fn breakeven_lower(&self) -> f64 { self.k2 - self.net_premium }
    pub fn breakeven_upper(&self) -> f64 { self.k3 + self.net_premium }
    
    pub fn win_probability(&self, sigma: f64, t: f64) -> f64 {
        // P(K2 < S_T < K3) under risk-neutral measure
        let d2_lower = ((1.0 / self.k2).ln() + (-0.5 * sigma * sigma) * t) 
                       / (sigma * t.sqrt());
        let d2_upper = ((1.0 / self.k3).ln() + (-0.5 * sigma * sigma) * t) 
                       / (sigma * t.sqrt());
        norm_cdf(d2_upper) - norm_cdf(d2_lower)
    }
}
```

---

## 11. Конфигурация

```yaml
# === Опционы и деривативы ===
options:
  # Источник данных
  exchange: deribit
  ws_url: wss://www.deribit.com/ws/api/v2
  symbols: [BTC, ETH]
  
  # Модель ценообразования
  pricing_model: black_scholes  # black_scholes | binomial | monte_carlo
  risk_free_rate: 0.0           # r = 0 для BTC-номинала
  
  # Implied Volatility
  iv:
    method: newton_raphson
    max_iterations: 100
    tolerance: 1e-8
    bisection_fallback: true
  
  # Vol Surface
  vol_surface:
    model: svi
    calibration_window: 90       # дней
    min_strikes: 5               # минимум для калибровки
  
  # GEX
  gex:
    update_interval_sec: 300     # 5 минут
    high_threshold_pct: 75       # Percentile 75
    low_threshold_pct: 25        # Percentile 25
    lookback_days: 90
  
  # Hedging
  hedge:
    enabled: true
    min_position_pct: 0.05       # хедж только при позиции > 5%
    max_hedge_cost_pct: 0.03     # не более 3% на хедж
    put_delta_range: [-0.25, -0.15]
    expiry_days: 30
    iv_activate_below_pct: 25    # покупать puts при IV < P25
    gex_activate_below: 0        # покупать puts при GEX < 0
  
  # Strategy filters
  filters:
    max_pain:
      enabled: true
      activate_days_before: 3
      pin_threshold_pct: 0.02
    iv_indicator:
      enabled: true
      oversold_pct: 25           # IV < P25 → vol дёшево
      overbought_pct: 75         # IV > P25 → vol дорого
    pcr:
      enabled: true
      extreme_low: 0.4           # contrarian: экстремально низкий PCR → bearish reversal
      extreme_high: 1.5          # contrarian: экстремально высокий PCR → bullish reversal
    funding_pcp:
      enabled: true
      threshold: 0.001           # |C-P-(S-K)| > threshold → mispricing alert

  # Monte Carlo (v0.4+)
  monte_carlo:
    n_simulations: 100_000
    n_steps: 252
    seed: 42
    jump_model: false            # true = Merton jump-diffusion
    jump_lambda: 4.0
    jump_mu: -0.02
    jump_sigma: 0.05
```

---

## Резюме

| Категория | ВКЛЮЧИТЬ | ОТБРОСИТЬ |
|---|---|---|
| **Модели** | Black-Scholes (MVP), Binomial Tree (v0.3), IV Newton-Raphson (MVP) | Monte Carlo GBM (избыточен), Lévy Jumps (калибровка нестабильна) |
| **Греки** | Δ, Γ, Θ, ν (MVP), Vanna/Charm (v0.4) | Rho (≈ 0 в крипте) |
| **Стратегии** | Iron Condor (v0.4), Calendar Spread (v0.4), Straddle (v0.3), Delta-Hedge (v0.2) | Strangle (нет преимуществ), Butterfly (слишком узкий) |
| **Индикаторы** | GEX (v0.2), IV indicator (v0.2), PCR (v0.3), VRP (v0.3), Max Pain (v0.3) | Gamma Scalping (покрыто компонентами) |
| **Crypto-specific** | Deribit API, Funding→PCP proxy, IV surface/SVI, Vol Smile/Skew | — |
| **Hedging (топ-3)** | 1) OTM Put Hedge, 2) GEX-based Sizing, 3) Calendar Spread при IV spike | — |

**Основа аудита:** Options.md (Specialist 7) — критически важный документ, содержащий полные формулы BS, Greeks, GEX/VEX/CEX, SVI, Max Pain, production edge cases и архитектуру выживания. Настоящий документ дополняет его моделями (Binomial, Monte Carlo), опционными стратегиями, crypto-specific индикаторами и Rust-реализациями.

---

*Документ: 18-options-derivatives.md | Агент 18: Опционы и деривативы*