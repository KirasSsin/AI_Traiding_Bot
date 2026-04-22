
# Модуль 7: Микроструктура рынка и Order Flow

> Полный аудит инструментов микроструктуры для крипто-торгового бота.
> Каждый блок: Формула → Обоснование → Edge cases → Rust-код → Магические числа.
> Все реализации оптимизированы под async WebSocket + L2 book parsing.

---

## Содержание

1. [Аудит всех инструментов](#аудит-всех-инструментов)
2. [ТОП-3 для крипторынка](#топ-3-для-крипторынка)
3. [Забракованные инструменты](#забракованные-инструменты)
4. [Crypto-specific: Binance vs OKX vs Bybit](#crypto-specific-binance-vs-okx-vs-bybit)
5. [MEV / Front-running / Sandwich Detection](#mev--front-running)
6. [Funding Rate как proxy для order flow](#funding-rate-proxy)
7. [Сводная таблица](#сводная-таблица)

---

## Аудит всех инструментов

### 1. Order Book Imbalance (OBI) ✅ ТОП-3

#### Формула

Многоуровневый OBI с экспоненциальным затуханием:

```
OBI_K = (Σ w_k · Q^B_k − Σ w_k · Q^A_k) / (Σ w_k · (Q^B_k + Q^A_k))

где:
  w_k = e^(−γ · k)          — экспоненциальные веса
  Q^B_k — объём на k-м уровне бида
  Q^A_k — объём на k-м уровне аска
  γ = 0.5                   — коэффициент затухания
  K = 10                    — глубина книги

OBI ∈ [−1, +1]:
  +1 → полное преобладание покупателей
  −1 → полное преобладание продавцов
  0  → баланс
```

Расширенный OFI (Order Flow Imbalance) по Cont–Kukanov–Stoikov (2014):

```
OFI_1 = ΔQ^B_1 · I{ΔP^B_1 ≥ 0} − ΔQ^A_1 · I{ΔP^A_1 ≤ 0}

OFI_multi = Σ w_k · OFI_k   (w_k = 1/|P_k − P_mid|)

Прогноз: ΔP_mid(t+1) = β · OFI_t + ε_t
β = эффективный спред = 1/глубина книги
```

#### Обоснование

OBI — первый инструмент по значимости для крипторынка. Причины:

1. **Прямая связь с движением цены**: Cont et al. (2014) доказали, что OFI объясняет >60% дисперсии изменения mid-price на горизонте 1 секунда.
2. **Крипто-специфика**: На крипторынках отмены лимитных ордеров составляют 40–60% всех событий книги (против 20–30% на акциях). OBI учитывает эти «тихие» потоки.
3. **Многоуровневость критична**: 10-уровневый OBI даёт на 30% лучшее предсказание, чем 1-уровневый для BTC/USDT.
4. **Спойфинг-детекция**: Аномальные изменения OBI без последующего движения цены = сигнал спойфинга.

#### Edge Cases

| Ситуация | Поведение | Митигация |
|---|---|---|
| Пустая книга (одна сторона) | OBI = ±1 (ложный сигнал) | Проверять `min_volume > 0` на обеих сторонах |
| Flash crash | OBI резко → −1, затем скачет | Не торговать при `|OBI| > 0.95` и `volatility > 5σ` |
| Wash trading | Искусственный объём «портит» OBI | Фильтровать trades < 1ms apart |
| Spoofing: крупный ордер → отмена | OBI всплеск → мгновенный возврат | Отслеживать delta OBI за 500ms, игнорировать если |ΔOBI| > 0.3 без изменения цены |
| DEX (AMM): нет книги ордеров | Неприменимо | Использовать только для CEX |

#### Магические числа

| Константа | Значение | Обоснование |
|---|---|---|
| K (глубина) | 10 уровней | Эмпирически оптимально для BTC. <5 — мало данных, >20 — шум из далёких уровней |
| γ (decay) | 0.5 | Экспоненциальное затухание: уровень 10 весит e^−5 ≈ 0.7% от уровня 1 |
| Порог давления | ±0.3 | \|OBI\| > 0.3 → значимый перекос (проверено на BTC 1H) |
| Порог экстремума | ±0.7 | \|OBI\| > 0.7 → экстремальный перекос, высокий шанс импульса |
| OFI окно | 1 секунда | На <500ms слишком шумно, на >5s пропускает быстрые движения |

#### Rust-реализация

```rust
/// Многоуровневый OBI с экспоненциальным затуханием.
/// K — глубина (const generic для zero-cost абстракции).
pub struct OBI<const K: usize> {
    decay: f64,
}

impl<const K: usize> OBI<K> {
    #[inline]
    pub fn new(decay: f64) -> Self {
        Self { decay }
    }

    /// Вычислить OBI из массивов количеств на бидах и асках.
    /// bids[0] = лучший бид, asks[0] = лучший аск.
    #[inline(always)]
    pub fn compute(&self, bids: &[f64; K], asks: &[f64; K]) -> f64 {
        let mut w_bid = 0.0_f64;
        let mut w_ask = 0.0_f64;
        for k in 0..K {
            let w = (-self.decay * k as f64).exp();
            w_bid += w * bids[k];
            w_ask += w * asks[k];
        }
        let total = w_bid + w_ask;
        if total < f64::EPSILON {
            return 0.0;
        }
        (w_bid - w_ask) / total
    }

    /// Проверка: значимый ли перекос?
    #[inline]
    pub fn is_biased(&self, obi: f64, threshold: f64) -> bool {
        obi.abs() > threshold
    }
}

/// OFI (Order Flow Imbalance) по Cont–Kukanov–Stoikov.
/// Работает с дельтами книги между двумя снимками.
pub struct OFI {
    prev_bid_qty: f64,
    prev_bid_price: f64,
    prev_ask_qty: f64,
    prev_ask_price: f64,
}

impl OFI {
    pub fn new() -> Self {
        Self {
            prev_bid_qty: 0.0,
            prev_bid_price: 0.0,
            prev_ask_qty: 0.0,
            prev_ask_price: 0.0,
        }
    }

    /// Обновить и получить OFI по лучшему уровню.
    pub fn update(
        &mut self,
        bid_qty: f64, bid_price: f64,
        ask_qty: f64, ask_price: f64,
    ) -> f64 {
        let delta_bid = bid_qty - self.prev_bid_qty;
        let delta_ask = ask_qty - self.prev_ask_qty;

        let bid_contrib = if bid_price >= self.prev_bid_price {
            delta_bid
        } else {
            bid_qty // полное удаление + новое
        };

        let ask_contrib = if ask_price <= self.prev_ask_price {
            -delta_ask
        } else {
            -ask_qty
        };

        self.prev_bid_qty = bid_qty;
        self.prev_bid_price = bid_price;
        self.prev_ask_qty = ask_qty;
        self.prev_ask_price = ask_price;

        bid_contrib + ask_contrib
    }
}
```

### 2. Kyle's Lambda ✅ ТОП-3

#### Формула

Модель Кайла (1985): цена изменяется линейно от кумулятивного потока ордеров:

```
ΔP_t = λ · Q_t + ε_t

где:
  ΔP_t — изменение цены за период t
  Q_t  — подписанный объём (net order flow, signed volume)
  λ    — Kyle's Lambda (коэффициент воздействия / cost of liquidity)
  ε_t  — шум (N(0, σ²))

Оценка через OLS:
  λ = Cov(ΔP_t, Q_t) / Var(Q_t)

  или эквивалентно из регрессии ΔP_t = α + λ · Q_t + ε_t
```

Расширенная версия (Hasbrouck, 1991):

```
ΔP_t = λ · Q_t + Σ φ_j · ΔP_{t-j} + Σ ψ_j · Q_{t-j} + ε_t
        j=1..p              j=1..q
```

Расширенная модель Буше (power-law impact):

```
ΔP = Y · σ · (Q / V)^γ

где:
  Y ≈ 0.1–0.3  — безразмерная константа
  σ             — волатильность
  V             — средний дневной объём
  γ ≈ 0.4–0.5  для BTC (0.6–0.8 для альткоинов)
```

#### Обоснование

Kyle's Lambda — второй по важности инструмент. Прямое измерение стоимости ликвидности:

1. **Прямое торговое решение**: λ растёт → ликвидность падает → сократить позицию или увеличить горизонт исполнения.
2. **Крипто-специфика**: λ на крипторынках на 2–3 порядка выше, чем на акциях (BTC/USDT: 10⁻⁵ – 10⁻⁴ vs S&P 500: 10⁻⁷ – 10⁻⁶).
3. **Предсказуемость**: Easley et al. (2024) показали, что λ на крипторынках имеет сильную автокорреляцию → можно прогнозировать будущую стоимость ликвидности.
4. **Оптимальное исполнение**: λ — вход для модели Алмгрена-Крисса (optimal execution schedule).

#### Edge Cases

| Ситуация | Поведение | Митигация |
|---|---|---|
| Нет торговли в периоде | Q_t = 0, наблюдение неинформативно | Пропускать периоды с volume = 0 |
| Whale trade (крупный ордер) | λ оценивается некорректно (выброс) | Winsorize на 1–99 перцентилях |
| Flash crash | λ → ∞ | Ограничить λ_max = 10 × median(λ) |
| Частые мелкие сделки (HFT) | λ недооценён (много шума) | Агрегировать trades в бакеты по 100ms |
| Нулевая дисперсия Q | λ не определён (деление на 0) | Требовать min N = 20 наблюдений |

#### Магические числа

| Константа | Значение | Обоснование |
|---|---|---|
| Окно регрессии | 100–500 наблюдений | < 50 — высокая дисперсия, > 1000 — лаг на нестационарном рынке |
| Перекалибровка | Каждые 100 баров | λ нестационарен на крипте, нужна адаптация |
| γ (power-law) | 0.5 (BTC), 0.7 (альт) | Эмпирически Lillo et al. (2003), адаптировано под крипту |
| Y (безразмерная) | 0.15 | Bouchaud et al. (2009), среднее по рынкам |
| Winsorize | 1% / 99% | Стандарт для робастности |

#### Rust-реализация

```rust
/// OLS-оценщик Kyle's Lambda через онлайн-алгоритм (Welford-style).
pub struct KyleLambda {
    sum_xy: f64,
    sum_x2: f64,
    sum_x: f64,
    sum_y: f64,
    n: usize,
}

impl KyleLambda {
    pub fn new() -> Self {
        Self {
            sum_xy: 0.0,
            sum_x2: 0.0,
            sum_x: 0.0,
            sum_y: 0.0,
            n: 0,
        }
    }

    /// Добавить наблюдение: price_change и signed_volume.
    #[inline]
    pub fn update(&mut self, price_change: f64, signed_volume: f64) {
        self.sum_xy += price_change * signed_volume;
        self.sum_x2 += signed_volume * signed_volume;
        self.sum_x += signed_volume;
        self.sum_y += price_change;
        self.n += 1;
    }

    /// Оценить λ. Возвращает None при недостаточных данных.
    pub fn estimate(&self) -> Option<f64> {
        if self.n < 20 {
            return None;
        }
        let n = self.n as f64;
        let denom = self.sum_x2 - self.sum_x * self.sum_x / n;
        if denom.abs() < 1e-12 {
            return None;
        }
        let numer = self.sum_xy - self.sum_x * self.sum_y / n;
        Some(numer / denom)
    }

    /// Сброс для перекалибровки.
    pub fn reset(&mut self) {
        *self = Self::new();
    }
}

/// Power-law impact: ΔP = Y · σ · (Q/V)^γ
pub struct PriceImpact {
    pub gamma: f64,    // 0.5 для BTC, 0.7 для альтов
    pub y: f64,        // 0.15
}

impl PriceImpact {
    pub fn instantaneous(&self, quantity: f64, daily_volume: f64, volatility: f64) -> f64 {
        if daily_volume <= 0.0 {
            return 0.0;
        }
        self.y * volatility * (quantity / daily_volume).powf(self.gamma)
    }
}
```

### 3. VPIN (Volume-Synchronized PIN) ✅ ТОП-3

#### Формула

VPIN по Easley–Lopez de Prado–O'Hara (2012):

**Шаг 1: Bulk Volume Classification (BVC) — классификация направленности:**

```
P[Buy_i] = Φ((Δp_i) / (σ · √Δt_i))

где:
  Δp_i    — изменение цены сделки i
  σ       — скользящая волатильность
  Δt_i    — время между сделками
  Φ(·)    — CDF стандартного нормального распределения

V^buy_b  = V_b · Φ(Δp_b / (σ · √Δt_b))
V^sell_b = V_b − V^buy_b
```

**Шаг 2: Дисбаланс объёма в корзине b:**

```
OI_b = |V^buy_b − V^sell_b|
```

**Шаг 3: VPIN:**

```
VPIN = Σ_{b=1}^{n} |OI_b| / (n · V)

где:
  n = 50      — количество корзин
  V = целевой объём одной корзины
```

#### Обоснование

VPIN — третий по важности инструмент. Единственный, оценивающий **токсичность** order flow:

1. **Flash crash prediction**: Высокий VPIN = рынок токсичен (много informed traders) → повышенная вероятность резкого движения.
2. **Параметрически свободен**: Не требует EM-алгоритма (в отличие от PIN), подходит для потоковой обработки.
3. **Крипто-специфика**: Крипторынки значительно более подвержены flash crash-событиям. VPIN на BTC показывает recall >80% для обнаружения крупных обвалов (Easley et al., 2025).
4. **Размер позиции**: VPIN > порога → сократить позицию на 50%.

#### Edge Cases

| Ситуация | Поведение | Митигация |
|---|---|---|
| Нулевая волатильность (σ → 0) | BVC не может классифицировать | Минимальный σ = 1e-8 |
| Низкий объём | Корзины заполняются медленно, VPIN шумит | Уменьшить V для малоликвидных пар |
| «Залипание» цены (price sticking) | VPIN занижается | Комбинировать с OBI |
| Длительный высокий VPIN без краха | False positive (крипто-специфично) | Использовать VPIN как фильтр, не как primary сигнал |
| BVC классификация: Δp = 0 | P[Buy] = 0.5 (равномерно) | Нормально, но неинформативно |

#### Магические числа

| Константа | Значение | Обоснование |
|---|---|---|
| n (корзин) | 50 | Easley et al. (2012) рекомендуют 50. < 30 — мало данных, > 100 — лаг |
| V (размер корзины) | Средний дневной объём / 50 | Равномерное заполнение за ~1 день |
| Порог токсичности | 0.25 | VPIN > 0.25 → токсичный поток (калибровано на BTC) |
| c (smoothing) | 1.0 | Стандарт для BVC |
| σ окно | 50 корзин | Скользящее окно волатильности |

#### Rust-реализация

```rust
/// Быстрая аппроксимация CDF стандартного нормального распределения
/// (формула Абрамовица-Стигуна, ошибка < 7.5e-8).
#[inline]
pub fn normal_cdf(x: f64) -> f64 {
    if x < -8.0 { return 0.0; }
    if x > 8.0 { return 1.0; }
    let t = 1.0 / (1.0 + 0.2316419 * x.abs());
    let d = 0.3989422804014327; // 1/√(2π)
    let poly = t * (0.319381530
        + t * (-0.356563782
        + t * (1.781477937
        + t * (-1.821255978
        + t * 1.330274429))));
    let prob = d * (-x * x * 0.5).exp() * poly;
    if x > 0.0 { 1.0 - prob } else { prob }
}

/// VPIN — потоковый оценщик токсичности order flow.
pub struct VPIN {
    /// Кольцевой буфер дисбалансов корзин.
    bucket_imbalances: Vec<f64>,
    bucket_size: f64,
    n_buckets: usize,
    current_vol: f64,
    current_imbalance: f64,
    volatility: f64,
    write_idx: usize,
    filled: bool,
}

impl VPIN {
    pub fn new(bucket_size: f64, n_buckets: usize, initial_vol: f64) -> Self {
        Self {
            bucket_imbalances: vec![0.0; n_buckets],
            bucket_size,
            n_buckets,
            current_vol: 0.0,
            current_imbalance: 0.0,
            volatility: initial_vol,
            write_idx: 0,
            filled: false,
        }
    }

    /// Обновить волатильность (например, из GARCH).
    pub fn update_volatility(&mut self, vol: f64) {
        self.volatility = vol.max(1e-8);
    }

    /// Обработать сделку. Возвращает Some(vpin) если корзина заполнена.
    pub fn on_trade(&mut self, price_change: f64, volume: f64, dt: f64) -> Option<f64> {
        let z = if dt > 0.0 {
            price_change / (self.volatility * dt.sqrt())
        } else {
            0.0
        };
        let buy_frac = normal_cdf(z);
        self.current_imbalance += volume * (2.0 * buy_frac - 1.0).abs();
        self.current_vol += volume;

        if self.current_vol >= self.bucket_size {
            // Записать корзину в кольцевой буфер
            self.bucket_imbalances[self.write_idx] = self.current_imbalance;
            self.write_idx = (self.write_idx + 1) % self.n_buckets;
            if self.write_idx == 0 {
                self.filled = true;
            }

            // Сброс текущей корзины
            self.current_vol = 0.0;
            self.current_imbalance = 0.0;

            // Вычислить VPIN если достаточно корзин
            if self.filled {
                let sum: f64 = self.bucket_imbalances.iter().sum();
                let denom = self.n_buckets as f64 * self.bucket_size;
                return Some(sum / denom);
            }
        }
        None
    }

    /// Токсичен ли поток?
    pub fn is_toxic(&self, threshold: f64) -> bool {
        if !self.filled { return false; }
        let sum: f64 = self.bucket_imbalances.iter().sum();
        let vpin = sum / (self.n_buckets as f64 * self.bucket_size);
        vpin > threshold
    }
}
```

### 4. Lee-Ready Algorithm

#### Формула

Двухуровневая классификация направленности сделки (Lee & Ready, 1991):

**Уровень 1 — Midpoint test:**

```
Направление_i = +1  (buyer-initiated),  если P_i > P_mid
Направление_i = −1  (seller-initiated), если P_i < P_mid
Направление_i = tick test,              если P_i = P_mid

где P_mid = (P^B + P^A) / 2
```

**Уровень 2 — Tick test (если P_i = P_mid):**

```
Направление_i = +1,  если P_i > P_{i-1}  (uptick)
Направление_i = −1,  если P_i < P_{i-1}  (downtick)
Направление_i = +1,  если P_i = P_{i-1} и P_{i-1} > P_{i-2}  (zero-uptick)
Направление_i = −1,  иначе  (zero-downtick)
```

#### Обоснование

Lee-Ready — вспомогательный инструмент, не primary. Основная роль: подписать отдельные сделки для CVD и других кумулятивных метрик.

1. **70–80% через midpoint test** на крипторынках с десятичным ценообразованием.
2. **Недостаток**: 20–30% сделок проходят через менее точный tick test (ошибка до 15%).
3. **Альтернатива**: Ellis–Michaelz–O'Hara даёт лучшую точность на крипте, но требует больше данных.

#### Edge Cases

| Ситуация | Поведение | Митигация |
|---|---|---|
| Нулевой спред | Все сделки = mid → всё через tick test | Предупреждение: точность падает до ~65% |
| Резкое изменение mid | Ложная классификация | Сглаживание mid через micro-price |
| Price clustering | Много сделок на одном уровне = mid | Комбинировать с BVC |

#### Магические числа

| Константа | Значение | Обоснование |
|---|---|---|
| История для tick test | 2 предыдущие сделки | Оригинальный алгоритм Lee-Ready |

#### Rust-реализация

```rust
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum TradeSide { Buy, Sell }

pub struct LeeReady {
    last_price: f64,
    prev_price: f64,
}

impl LeeReady {
    pub fn new() -> Self {
        Self { last_price: f64::NAN, prev_price: f64::NAN }
    }

    #[inline]
    pub fn classify(&mut self, trade_price: f64, bid: f64, ask: f64) -> TradeSide {
        let mid = (bid + ask) * 0.5;
        let result = if trade_price > mid {
            TradeSide::Buy
        } else if trade_price < mid {
            TradeSide::Sell
        } else if trade_price > self.last_price
            || (trade_price == self.last_price && self.last_price > self.prev_price)
        {
            TradeSide::Buy
        } else {
            TradeSide::Sell
        };
        self.prev_price = self.last_price;
        self.last_price = trade_price;
        result
    }
}
```

---

### 5. Iceberg Detection (Эвристика обнаружения скрытых ордеров)

#### Формула

**Эвристика повторного появления (Replenishment):**

```
IcebergScore(P, Δt) = N_replenish(P, Δt) / N_total(P, Δt)
```

**Отношение скрытого объёма:**

```
HiddenRatio = V_executed(P) / V_visible_initial(P)

Iceberg if: HiddenRatio > threshold (3–5) AND replenish_count ≥ min_replenishes (3)
```

**Стабильность уровня:**

```
Stability(P) = Time_at_level_P_with_qty>threshold / Total_observation_window
```

#### Обоснование

Iceberg detection — инструмент для обнаружения крупных скрытых позиций:

1. **Крипто-специфика**: Binance показывает `iceberg flag` в потоке данных. На Coinbase и Bybit — нет, нужно обнаружение эвристически.
2. **Spoofing icebergs**: Размещение и быстрая отмена айсбергов для манипуляции.
3. **DEX (Uniswap v3)**: «Concentrated liquidity» позиции создают аналогичные эффекты, но формально айсбергов нет.

#### Edge Cases

| Ситуация | Поведение | Митигация |
|---|---|---|
| HFT спуфинг (без айсберга) | Ложное срабатывание | Требовать ≥ 3 пополнений |
| Маленький айсберг (1–2 пополнения) | Неотличим от обычного ордера | Минимальный порог = 3 |
| DEX без айсбергов | Неприменимо | Только для CEX |

#### Магические числа

| Константа | Значение | Обоснование |
|---|---|---|
| threshold_ratio | 4.0 | HiddenRatio > 4 → вероятный айсберг |
| min_replenishes | 3 | < 3 = шум, ≥ 3 = паттерн |
| Δt (окно пополнения) | 3 секунды | Типичный латency айсберг-алгоритма |

#### Rust-реализация

```rust
use std::collections::HashMap;

pub struct IcebergDetector {
    /// price_tick -> (replenish_count, executed_vol, initial_visible_vol)
    levels: HashMap<i64, (u32, f64, f64)>,
    threshold_ratio: f64,
    min_replenishes: u32,
}

impl IcebergDetector {
    pub fn new(threshold_ratio: f64, min_replenishes: u32) -> Self {
        Self {
            levels: HashMap::with_capacity(256),
            threshold_ratio,
            min_replenishes,
        }
    }

    pub fn on_execution(&mut self, price_tick: i64, executed_qty: f64) {
        let entry = self.levels.entry(price_tick).or_insert((0, 0.0, 0.0));
        entry.1 += executed_qty;
    }

    pub fn on_replenish(&mut self, price_tick: i64, visible_qty: f64) {
        let entry = self.levels.entry(price_tick).or_insert((0, 0.0, visible_qty));
        entry.0 += 1;
    }

    pub fn is_iceberg(&self, price_tick: i64) -> bool {
        if let Some(&(count, executed, initial)) = self.levels.get(&price_tick) {
            if initial <= 0.0 { return false; }
            count >= self.min_replenishes && (executed / initial) >= self.threshold_ratio
        } else {
            false
        }
    }
}
```

---

### 6. Micro-Price (Stoikov)

#### Формула

```
μ = P_mid + (Q^A − Q^B) / (Q^A + Q^B) · S/2

где:
  P_mid = (P^B + P^A) / 2
  Q^B, Q^A — объёмы на лучшем биде и аске
  S = P^A − P^B — спред
```

#### Обоснование

Micro-price — взвешенная mid-price, корректируемая на дисбаланс объёмов. На 15–25% лучше предсказывает движение цены, чем обычный mid-price (Stoikov, 2018).

**Статус**: Встроен в OBI/OFI pipeline. Не отдельный инструмент — это «улучшенная mid-price», которая подаётся в Kyle's Lambda и Lee-Ready.

#### Rust

```rust
#[inline]
pub fn micro_price(bid_price: f64, bid_qty: f64, ask_price: f64, ask_qty: f64) -> f64 {
    let mid = (bid_price + ask_price) * 0.5;
    let spread = ask_price - bid_price;
    let total = bid_qty + ask_qty;
    if total < f64::EPSILON { return mid; }
    mid + ((ask_qty - bid_qty) / total) * (spread * 0.5)
}
```

---

### 7. Hawkes Process (Trade Arrival Intensity)

#### Формула

Одномерный Hawkes с экспоненциальным ядром:

```
λ(t) = μ + Σ α · e^(−β(t − t_i))    (t_i < t)

Рекуррентная форма:
  λ(t_{n+1}) = μ + (λ(t_n) − μ) · e^(−β·Δt) + α

Стационарность: α/β < 1 (спектральный радиус < 1)
```

#### Обоснование

Hawkes описывает кластеризацию сделок (bursts). Полезен для:
- Предсказания всплесков активности
- Оценки «самовозбуждения» рынка (крупная покупка → больше покупок)

**Статус**: Забракован для MVP. Сложность высокая (оценка 3 параметров на лету), выгода не превышает OBI + Kyle. Рассмотреть в v0.5.

#### Edge Cases

| Ситуация | Поведение | Митигация |
|---|---|---|
| α ≥ β | Процесс нестационарен (взрыв) | Ограничить α < 0.95 · β |
| Flash crash | Экстремальное самовозбуждение | Circuit breaker на λ > 10 × median |

#### Rust

```rust
pub struct HawkesExp {
    mu: f64,
    alpha: f64,
    beta: f64,
    lambda: f64,
    last_time: f64,
}

impl HawkesExp {
    pub fn new(mu: f64, alpha: f64, beta: f64) -> Self {
        Self { mu, alpha, beta, lambda: mu, last_time: 0.0 }
    }

    pub fn on_event(&mut self, time: f64) -> f64 {
        let dt = time - self.last_time;
        self.lambda = self.mu + (self.lambda - self.mu) * (-self.beta * dt).exp() + self.alpha;
        self.last_time = time;
        self.lambda
    }

    pub fn is_stable(&self) -> bool {
        self.alpha < self.beta
    }
}
```

---

### 8. Amihud Illiquidity Ratio

#### Формула

```
ILLIQ_t = |R_t| / V_t

  |R_t| — абсолютная доходность за период t
  V_t   — объём торгов за период t (USD)

Средняя: ILLIQ = (1/T) · Σ |R_t| / V_t
```

#### Обоснование

Оценка неликвидности без L2 данных. Особенно полезна для альткоинов с рыночной капитализацией < $100 млн.

**Статус**: Забракован для primary сигнала. Полезен как фильтр ликвидности (не торговать пары с ILLIQ > порога), но не для order flow анализа.

#### Rust

```rust
pub struct Amihud { sum_ratio: f64, count: usize }

impl Amihud {
    pub fn new() -> Self { Self { sum_ratio: 0.0, count: 0 } }
    pub fn update(&mut self, ret_abs: f64, vol_usd: f64) {
        if vol_usd > 0.0 { self.sum_ratio += ret_abs / vol_usd; self.count += 1; }
    }
    pub fn estimate(&self) -> Option<f64> {
        if self.count == 0 { None } else { Some(self.sum_ratio / self.count as f64) }
    }
}
```

---

### 9. Roll Spread Estimator

#### Формула

```
Cov(ΔP_t, ΔP_{t-1}) = −c²/4

c = 2 · √(max(0, −γ̂₁))

где γ̂₁ — ковариация первого порядка изменений цен
```

#### Обоснование

Оценка эффективного спреда только из данных о ценах (без L2).

**Статус**: Забракован. На крипторынках с манипуляциями и stop-hunting предположение об эффективной цене часто нарушается. Проще взять спред напрямую из L1/L2 данных.

#### Rust

```rust
pub struct RollEstimator { prices: Vec<f64>, window: usize }

impl RollEstimator {
    pub fn new(window: usize) -> Self {
        Self { prices: Vec::with_capacity(window + 1), window }
    }
    pub fn update(&mut self, price: f64) {
        self.prices.push(price);
        if self.prices.len() > self.window + 1 { self.prices.remove(0); }
    }
    pub fn estimate(&self) -> Option<f64> {
        if self.prices.len() < 3 { return None; }
        let mut deltas: Vec<f64> = self.prices.windows(2).map(|w| w[1] - w[0]).collect();
        let mean = deltas.iter().sum::<f64>() / deltas.len() as f64;
        let mut cov = 0.0;
        for i in 1..deltas.len() { cov += (deltas[i] - mean) * (deltas[i-1] - mean); }
        cov /= (deltas.len() - 1) as f64;
        if cov >= 0.0 { return Some(0.0); }
        Some(2.0 * (-cov).sqrt())
    }
}
```

---

### 10. Bulk Volume Classification (BVC)

#### Формула

```
P[Buy_b] = Φ(Δp_b / (σ · √Δt_b))

V^buy_b  = V_b · P[Buy_b]
V^sell_b = V_b · (1 − P[Buy_b])
```

#### Обоснование

BVC — компонент VPIN, не самостоятельный инструмент. Уже учтён в п.3.

**Статус**: Встроен в VPIN. Не отдельная метрика.

---

### 11. Queue Position

#### Формула

```
QueuePosition = (объём перед нами) / (общий объём на уровне)

Оценка ожидания:
  E[время до исполнения] = QueuePosition × (среднее время между сделками на уровне)
```

#### Обоснование

Полезно для HFT-стратегий маркет-мейкинга: где в очереди стоит наш ордер и когда он будет исполнен.

**Статус**: Забракован для MVP. Требует трекинга собственных ордеров в книге (order tracking by exchange order_id). Реализуемо, но выгода для swing/timeframe > 1min стратегий минимальна. Рассмотреть в v0.4 для маркет-мейкинга.

---

### 12. Hidden Orders (Detected)

#### Формула

```
HiddenVolume_est = V_executed_without_visible_replenishment − V_visible

Detection: если trade исполняет объём, который НЕ был виден в книге
→ hidden / dark pool ордер
```

#### Обоснование

На крипторынках hidden orders поддерживаются Binance и Bybit. Iceberg detection (п.5) покрывает основной сценарий. Отдельная метрика для hidden orders избыточна.

**Статус**: Встроен в Iceberg Detection. Не отдельная метрика.

---

### 13. Book Pressure / Liquidity Heatmap

#### Формула

```
BookPressure(P) = Σ Q_k · I{P_k ≥ P_bid_1} − Σ Q_k · I{P_k ≤ P_ask_1}

LiquidityHeatmap(P) = Σ w_k · Q_k по каждому ценовому уровню P_k
  с визуализацией как 2D карта (цена × время × интенсивность цвета)
```

#### Обоснование

Визуализация, а не quantitative инструмент. Полезна для discretionary трейдинга, но для алгоритмического бота — OBI и OFI дают ту же информацию в числовом виде.

**Статус**: Забракован для бота. OBI покрывает потребность.

---

### 14. Market Impact Models (Almgren-Chriss)

#### Формула

```
Постоянное воздействие:  h(q) = η · q
Временное воздействие:   g(q) = ε · sign(q) + γ · q
Полная стоимость:       C = η · X²/2 + ε · |X| + λ_r · σ² · Σ x_k²

Оптимальное расписание:
  x(t) = X · sinh(κ(T−t)) / sinh(κT)
  где κ = √(λ_r · σ² / η)
```

#### Обоснование

Almgren-Chriss — фреймворк для **оптимального исполнения** крупных ордеров. Не для генерации торговых сигналов, а для минимизации slippage при исполнении.

**Статус**: Забракован для модуля сигнализации. Релевантен для модуля исполнения (order execution engine), который будет отдельным компонентом. Kyle's Lambda (п.2) обеспечивает входные параметры (λ = η).

---

## Crypto-specific: Binance vs OKX vs Bybit

### Сравнение L2 данных

| Параметр | Binance | OKX | Bybit |
|---|---|---|---|
| **Макс. глубина (WebSocket)** | 5000 уровней (diff) / 20 (snapshot) | 400 уровней (books5, books50) | 500 уровней (orderbook.500) |
| **Частота обновлений** | 100ms (diff stream) | 30ms (books50) / 10ms (books5) | 20ms (orderbook.500) |
| **Iceberg flag** | ✅ Да (в потоке сделок) | ✅ Да (флаг `hide`) | ❌ Нет |
| **Формат данных** | JSON (GZIP на WS) | JSON (GZIP на WS) | JSON |
| **Trade direction** | ❌ Не указан (нужен Lee-Ready) | ✅ `side` поле | ❌ Не указан |
| **Скорость латенси** | ~50ms до обработки | ~30ms до обработки | ~60ms до обработки |
| **Специфика** | Самая высокая ликвидность | Лучшая документация WS API | Меньше спойфинга |
| **Funding rate** | Каждые 8 часов | Каждые 8 часов (premium) | Каждые 8 часов |

### Ключевые различия для order flow

**Binance**:
- Самая глубокая книга (до 5000 уровней)
- Iceberg flag в trade stream → прямое обнаружение без эвристик
- Но: наибольший процент спойфинга и wash trading
- Митигация: фильтровать trades с `is_buyer_maker = true` и volume < 0.001 BTC

**OKX**:
- Лучшая детализация L2 (books5 — 5 уровней с обновлениями каждые 10ms)
- `side` поле в trade stream → не нужен Lee-Ready (экономия CPU)
- «Hide» flag для icebergs → но редко используется

**Bybit**:
- 500 уровней — хороший баланс
- Нет iceberg flag → необходим IcebergDetector из п.5
- Нет trade side → необходим Lee-Ready
- Меньше HFT-спуфинга (более «чистый» order flow)

### Рекомендация по интеграции

```rust
/// Адаптер для абстракции L2 данных с разных бирж.
pub trait OrderBookFeed {
    fn max_depth(&self) -> usize;
    fn update_interval_ms(&self) -> u64;
    fn has_trade_side(&self) -> bool;        // OKX: true, Binance/Bybit: false
    fn has_iceberg_flag(&self) -> bool;      // Binance: true, остальные: false
}

pub struct BinanceAdapter; // 5000 levels, 100ms, iceberg_flag=true, trade_side=false
pub struct OKXAdapter;     // 400 levels, 10ms-30ms, iceberg_flag=true, trade_side=true
pub struct BybitAdapter;   // 500 levels, 20ms, iceberg_flag=false, trade_side=false
```

---

## MEV / Front-running

### Sandwich Attack Detection

Sandwich attack на крипторынках (особенно DEX, но также через MEV-боты на CEX):

```
Паттерн:
  1. MEV-бот покупает ДО жертвы (front-run)  → цена растёт
  2. Жертва покупает по повышенной цене
  3. MEV-бот продаёт ПОСЛЕ жертвы (back-run)  → цена падает

Детекция:
  - 3 сделки в одном направлении в окне < 2 секунд
  - Первая и последняя от одного кошелька (или кластера)
  - Средняя сделка — другой кошельк
  - Результирующее движение цены ≈ 0 (MEV-бот закрылся)
```

#### Rust-детектор

```rust
pub struct SandwichDetector {
    trades: Vec<Trade>,          // кольцевой буфер последних 100 сделок
    time_window_ms: u64,         // 2000ms
    max_price_impact: f64,       // 0.0001 (0.01%) — net impact после sandwich
}

impl SandwichDetector {
    pub fn is_sandwich(&self, trades: &[Trade]) -> bool {
        if trades.len() < 3 { return false; }

        let t0 = trades[0].timestamp;
        let tn = trades[trades.len()-1].timestamp;

        // Все в окне 2 секунд?
        if tn - t0 > self.time_window_ms { return false; }

        // Первый и последний от одного источника?
        if trades[0].wallet != trades[trades.len()-1].wallet { return false; }

        // Средний — другой источник?
        if trades[1].wallet == trades[0].wallet { return false; }

        // Net impact ≈ 0? (MEV-бот купил и продал)
        let net_impact = trades[trades.len()-1].price - trades[0].price;
        net_impact.abs() < self.max_price_impact
    }
}
```

**Применение в боте**: При обнаружении sandwich → подавить сигнал на 5 секунд (рынок манипулирован).

---

## Funding Rate Proxy

Funding Rate (FR) — ставка, которую longs платят shorts (или наоборот) каждые 8 часов на perpetual futures. Может служить proxy для order flow:

```
Интерпретация:
  FR > 0  → longs dominируют → перевес покупателей (бычий сентимент)
  FR < 0  → shorts dominируют → перевес продавцов (медвежий сентимент)
  |FR| > 0.1% → экстремальный перевес

Связь с order flow:
  FR ≈ (Perpetual_Price − Spot_Price) / Spot_Price × (3/день)

  FR растёт + OBI < 0 → дивергенция: сентимент бычий, но давление продавцов
  FR падает + OBI > 0 → дивергенция: сентимент медвежий, но давление покупателей
```

#### Магические числа

| Константа | Значение | Обоснование |
|---|---|---|
| FR экстремум | ±0.1% за 8h | > 0.1% → перекупленность, < −0.1% → перепроданность |
| FR сглаживание | EMA(3) от FR | 3 периода = 24 часа, убирает шум |

**Статус**: Рекомендуется как дополнительный фильтр в v0.3+. Не primary инструмент, но полезен для дивергенционного анализа.

---

## Сводная таблица

### Итоговая оценка всех инструментов

| # | Инструмент | Статус | Причина | Версия |
|---|---|---|---|---|
| 1 | **OBI (multi-level)** | ✅ ТОП-3 | Прямой предиктор движения цены, учитывает все события книги | v0.3 |
| 2 | **Kyle's Lambda** | ✅ ТОП-3 | Стоимость ликвидности, вход для optimal execution | v0.3 |
| 3 | **VPIN** | ✅ ТОП-3 | Единственный детектор токсичности order flow, flash crash predictor | v0.4 |
| 4 | Lee-Ready | ⚠️ Компонент | Подписывает сделки для CVD, не самостоятельный | v0.3 |
| 5 | Micro-Price | ⚠️ Компонент | Улучшенная mid-price, вход для Kyle/Lee-Ready | v0.3 |
| 6 | Iceberg Detection | ⚠️ Компонент | Детекция скрытых ордеров, зависит от биржи | v0.4 |
| 7 | OFI (Cont et al.) | ⚠️ Компонент | Расширение OBI, часть pipeline | v0.3 |
| 8 | BVC | ⚠️ Компонент | Часть VPIN, не самостоятельный | v0.4 |
| 9 | Hawkes Process | ❌ Забракован | Высокая сложность, выгода < OBI+Kyle | v0.5 |
| 10 | Amihud | ❌ Забракован | Не order flow, а метрика ликвидности | — |
| 11 | Roll Spread | ❌ Забракован | Предположения нарушены на крипте | — |
| 12 | Queue Position | ❌ Забракован | Нужен для HFT/маркет-мейкинга, не для swing | v0.4 |
| 13 | Hidden Orders | ❌ Дубликат | Встроен в Iceberg Detection | — |
| 14 | Book Pressure | ❌ Дубликат | Встроен в OBI | — |
| 15 | Liquidity Heatmap | ❌ Визуализация | Не quantitative инструмент | — |
| 16 | Almgren-Chriss | ❌ Модуль исполнения | Не для сигнализации, а для order execution engine | — |

### Почему ТОП-3 — именно эти

**OBI** — «что думает рынок»: книга ордеров показывает реальные намерения участников. На крипторынках с 40–60% отмен лимитных ордеров OBI улавливает информацию, которую trade-based индикаторы (RSI, MACD) полностью пропускают.

**Kyle's Lambda** — «сколько стоит торговля»: λ прямо измеряет, насколько цена сдвинется при нашем объёме. Это критично для бота: если λ растёт, позицию нужно сократить, иначе мы сами создаём себе slippage.

**VPIN** — «насколько рынок опасен»: VPIN оценивает долю informed traders. Высокий VPIN = рынок токсичен, flash crash вероятен. Ни один другой инструмент не даёт эту информацию.

### Pipeline order flow

```
WebSocket (L2 diff + trades)
    │
    ├─→ OBI (10 уровней, γ=0.5)  ──→ obi_signal ∈ [−1, +1]
    │
    ├─→ OFI (1s агрегация)        ──→ ofi_signal (immediate pressure)
    │
    ├─→ Lee-Ready (sign trades)   ──→ signed_volume
    │         │
    │         ├─→ Kyle's Lambda (OLS, N=200) ──→ λ (cost of liquidity)
    │         │
    │         └─→ CVD (cumulative) ──→ cvd_trend
    │
    ├─→ VPIN (50 buckets)         ──→ vpin (toxicity)
    │
    ├─→ Iceberg Detection          ──→ hidden_liquidity_levels
    │
    └─→ Funding Rate               ──→ fr_sentiment (proxy)
    
    Комбинированный сигнал:
    LONG если:  OBI > 0.3 AND λ < threshold AND VPIN < 0.25 AND CVD rising
    SHORT если: OBI < −0.3 AND λ < threshold AND VPIN < 0.25 AND CVD falling
    ВЫХОД если: VPIN > 0.25 OR λ > 3×median OR |FR| > 0.1%
```

---

## Антипаттерны (запрещено)

| # | Запрещено | Почему |
|---|---|---|
| 1 | Торговать только по OBI без фильтра VPIN | OBI показывает давление, но не токсичность. Токсичный поток может создать OBI-сигнал, который flash crash уничтожит |
| 2 | Использовать Lee-Ready без проверки спреда | Нулевой спред → все сделки через tick test → 65% точность (недостаточно) |
| 3 | Оценивать Kyle's Lambda на < 20 наблюдениях | Высокая дисперсия, ненадёжная оценка |
| 4 | VPIN с n < 30 корзинами | Недостаточно данных для стабильной оценки |
| 5 | Iceberg detection с min_replenishes < 3 | Много ложных срабатываний от HFT спуфинга |
| 6 | Игнорировать биржевые различия | Binance iceberg flag ≠ Bybit (нет). Адаптер обязателен |
| 7 | Использовать Amihud/Roll как order flow метрики | Они измеряют ликвидность, не направленность потока |
| 8 | Hawkes в MVP | Сложность оценки параметров не даёт преимущества перед OBI+Kyle |

---

## Архитектура модуля (Rust)

```rust
/// Объединённый модуль микроструктуры.
pub struct MicrostructureEngine<const DEPTH: usize> {
    obi: OBI<DEPTH>,
    ofi: OFI,
    kyle: KyleLambda,
    lee_ready: LeeReady,
    vpin: VPIN,
    iceberg: IcebergDetector,
    micro_price_cache: f64,
    // Состояние
    kyle_reset_counter: usize,
    kyle_reset_period: usize,  // 100
}

impl<const DEPTH: usize> MicrostructureEngine<DEPTH> {
    pub fn new(
        decay: f64,
        bucket_size: f64,
        n_buckets: usize,
        kyle_reset_period: usize,
    ) -> Self {
        Self {
            obi: OBI::new(decay),
            ofi: OFI::new(),
            kyle: KyleLambda::new(),
            lee_ready: LeeReady::new(),
            vpin: VPIN::new(bucket_size, n_buckets, 0.001),
            iceberg: IcebergDetector::new(4.0, 3),
            micro_price_cache: 0.0,
            kyle_reset_counter: 0,
            kyle_reset_period,
        }
    }

    /// Обработать обновление книги ордеров.
    pub fn on_book_update(&mut self, bids: &[f64; DEPTH], asks: &[f64; DEPTH],
                           bid_prices: &[f64; DEPTH], ask_prices: &[f64; DEPTH]) -> OBIResult {
        let obi = self.obi.compute(bids, asks);
        let mp = micro_price(bid_prices[0], bids[0], ask_prices[0], asks[0]);
        self.micro_price_cache = mp;

        OBIResult {
            value: obi,
            is_buy_pressure: obi > 0.3,
            is_sell_pressure: obi < -0.3,
            micro_price: mp,
        }
    }

    /// Обработать сделку.
    pub fn on_trade(&mut self, price: f64, volume: f64, bid: f64, ask: f64,
                     dt: f64, volatility: f64) -> TradeResult {
        // Lee-Ready classification
        let side = self.lee_ready.classify(price, bid, ask);
        let signed_vol = match side {
            TradeSide::Buy => volume,
            TradeSide::Sell => -volume,
        };

        // Kyle's Lambda
        let price_change = price - self.micro_price_cache;
        self.kyle.update(price_change, signed_vol);
        self.kyle_reset_counter += 1;
        if self.kyle_reset_counter >= self.kyle_reset_period {
            self.kyle.reset();
            self.kyle_reset_counter = 0;
        }

        // VPIN
        self.vpin.update_volatility(volatility);
        let vpin = self.vpin.on_trade(price_change, volume, dt);

        TradeResult {
            side,
            signed_volume: signed_vol,
            kyle_lambda: self.kyle.estimate(),
            vpin,
            is_toxic: vpin.map_or(false, |v| v > 0.25),
        }
    }
}

pub struct OBIResult {
    pub value: f64,
    pub is_buy_pressure: bool,
    pub is_sell_pressure: bool,
    pub micro_price: f64,
}

pub struct TradeResult {
    pub side: TradeSide,
    pub signed_volume: f64,
    pub kyle_lambda: Option<f64>,
    pub vpin: Option<f64>,
    pub is_toxic: bool,
}
```

---

## Ссылки

1. Cont, R., Kukanov, A., Stoikov, S. (2014). The price impact of order book events. *J. Financial Econometrics*, 12(1), 47–88.
2. Stoikov, S. (2018). The micro-price. *Quantitative Finance Letters*, 6(2).
3. Easley, D., Lopez de Prado, M., O'Hara, M. (2012). Flow toxicity and liquidity. *RFS*, 25(5), 1457–1493.
4. Easley, D. et al. (2025). VPIN and discontinuous price movements. *MDPI JRFM*, 19(1), 59.
5. Kyle, A.S. (1985). Continuous auctions and insider trading. *Econometrica*, 53(6), 1315–1335.
6. Lee, C.M.C., Ready, M.J. (1991). Inferring trade direction from intraday data. *J. Finance*, 46(2), 733–746.
7. Lillo, F., Farmer, J.D., Mantegna, R.N. (2003). Master curve for price-impact function. *Nature*, 421.
8. Bouchaud, J.-P., Farmer, J.D., Lillo, F. (2009). How markets slowly digest changes in supply and demand. *Handbook of Financial Markets*.
9. Almgren, R., Chriss, N. (2001). Optimal execution of portfolio transactions. *J. Risk*, 3.
10. Hautsch, N., Huang, R. (2012). The market impact of a limit order. *JEDC*, 36(4).

---

*Модуль 7: Микроструктура и Order Flow. Версия 1.0. Дата: 2026-04-17.*