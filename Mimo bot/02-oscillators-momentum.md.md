
# Модуль 2: Осцилляторы и моментум — Полный аудит

> **Агент 2** | Дата: 2026-04-17
> Назначение: всесторонний аудит всех осцилляторов и индикаторов моментума для ядра крипто-торгового бота.
> Источник: каталог из 779 формул (Research Indicators.md, Модуль 2)

---

## 1. Архитектурная роль осцилляторов

### Тезис: осцилляторы — фильтры, не primary сигналы

| Аргумент | Обоснование |
|---|---|
| **Лаг** | Все осцилляторы — производные от цены. Они не предсказывают, а описывают прошлое. Primary сигнал должен идти от тренда (цена > EMA, ADX > 25). |
| **Перекупленность ≠ продажа** | В сильном тренде RSI может быть > 70 неделями (BTC bull run 2020-2021: RSI > 70 на протяжении месяцев). Продажа по перекупленности = потеря тренда. |
| **Дивергенция — запаздывающий сигнал** | Дивергенция (цена high, RSI lower high) формируется минимум на 2-й экстремум. К моменту формирования 30-50% движения уже пройдено. |
| **Тайминг, не направление** | Осцилляторы дают точку входа внутри тренда (StochRSI выход из зоны перепроданности при бычьем тренде), но не определяют направление. |

### Итоговая сигнальная архитектура

```
PRIMARY (Модуль 1):     EMA кроссовер + ADX > 25 + Supertrend + Kumo
    ↓
ФИЛЬТР 1 (Осцилляторы): RSI не перекуплен (для лонга) / не перепродан (для шорта)
    ↓
ФИЛЬТР 2 (Осцилляторы): StochRSI в зоне входа / Fisher разворот
    ↓
ФИЛЬТР 3 (Дивергенция): MACD или RSI дивергенция как предупреждение
    ↓
ВХОД: когда все фильтры совпадают
```

---

## 2. Полный аудит: все осцилляторы

### 2.1 RSI — Relative Strength Index

| Параметр | Значение |
|---|---|
| **Автор** | J. Welles Wilder Jr., 1978 |
| **Период** | 14 (стандарт Уайлдера) |
| **Диапазон** | 0–100 |
| **Пороги** | < 30 перепродан, > 70 перекуплен |

#### Формула

```
RS = Average Gain / Average Loss  (за N периодов)

Вариант 1 (Wilder's smoothing):
  AvgGain(t) = (AvgGain(t-1) × 13 + Gain(t)) / 14
  AvgLoss(t) = (AvgLoss(t-1) × 13 + Loss(t)) / 14
  
  RSI = 100 - (100 / (1 + RS))

Вариант 2 (Cutler's — без warm-up проблем):
  AvgGain = SMA(Gain, N)
  AvgLoss = SMA(Loss, N)
  RSI = 100 - (100 / (1 + AvgGain/AvgLoss))
```

#### Магические числа
| Число | Источник | Комментарий |
|---|---|---|
| 14 | Уайлдер, эмпирика | ~половина лунного месяца, стандарт с 1978 |
| 30/70 | Уайлдер | Эмпирические пороги, не математически обоснованы |
| 50 | Нейтраль | 50 = RS = 1 (равные gain/loss) |

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Все бары растут | AvgLoss = 0 → RSI = 100 (деление на 0) | Clamp: если AvgLoss == 0, RSI = 100 |
| Все бары падают | AvgGain = 0 → RSI = 0 | Clamp: если AvgGain == 0, RSI = 0 |
| Первые N баров | Wilder smoothing даёт искажённые значения | Использовать SMA первые N баров, затем переключиться |
| Волатильный рынок | RSI «застревает» в зоне 50-70 | Дополнительный фильтр: RSI должен пересечь 50 |

#### Rust оптимизация

```rust
pub struct RSI {
    period: usize,
    avg_gain: f64,
    avg_loss: f64,
    prev_close: f64,
    count: usize,
    first_gains: Vec<f64>,  // для первых N баров
    first_losses: Vec<f64>,
}

impl RSI {
    pub fn new(period: usize) -> Self { /* ... */ }
    
    pub fn update(&mut self, close: f64) -> Option<f64> {
        let change = close - self.prev_close;
        let gain = if change > 0.0 { change } else { 0.0 };
        let loss = if change < 0.0 { -change } else { 0.0 };
        
        self.count += 1;
        
        if self.count <= self.period {
            // Wilder initialization: SMA первых N значений
            self.first_gains.push(gain);
            self.first_losses.push(loss);
            if self.count == self.period {
                self.avg_gain = self.first_gains.iter().sum::<f64>() / self.period as f64;
                self.avg_loss = self.first_losses.iter().sum::<f64>() / self.period as f64;
            }
            self.prev_close = close;
            return None;  // нет готового значения
        }
        
        // Wilder smoothing
        self.avg_gain = (self.avg_gain * (self.period - 1) as f64 + gain) / self.period as f64;
        self.avg_loss = (self.avg_loss * (self.period - 1) as f64 + loss) / self.period as f64;
        
        self.prev_close = close;
        
        if self.avg_loss == 0.0 {
            Some(100.0)
        } else {
            let rs = self.avg_gain / self.avg_loss;
            Some(100.0 - 100.0 / (1.0 + rs))
        }
    }
}
```

**Оптимизация**: O(1) обновление, не пересчитывает историю. Использует `f64` (double precision — достаточно для цен).

---

### 2.2 MACD — Moving Average Convergence Divergence

| Параметр | Значение |
|---|---|
| **Автор** | Gerald Appel, 1979 |
| **Периоды** | Fast=12, Slow=26, Signal=9 |
| **Диапазон** | Неограничен (разница цен) |

#### Формула

```
MACD Line     = EMA(Close, 12) - EMA(Close, 26)
Signal Line   = EMA(MACD Line, 9)
Histogram     = MACD Line - Signal Line

Пересечение: MACD > Signal → бычий моментум
Дивергенция: цена high →, MACD high ↓ (медвежья)
```

#### Магические числа
| Число | Источник | Комментарий |
|---|---|---|
| 12/26/9 | Appel, 1979 | Оптимизированы для дневного таймфрейма акций. На 1H крипты можно адаптировать (см. ниже). |

#### Проблема периодов для крипты

Традиционные 12/26/9 разработаны для дневного таймфрейма акций (252 торговых дня/год). На 1H крипты (24/7, 8760 баров/год) эти периоды слишком быстрые:

| Режим | Периоды | Комментарий |
|---|---|---|
| Акции (1D) | 12/26/9 | Стандарт Appel |
| Крипта (1H) | **12/26/9** | Оставлено как MVP — переопределять через config |
| Крипта (1H) оптимизация | 24/52/9 | Пропорциональный масштаб: 12×2=24 (день), 26×2=52 (2.5 дня) |

**Рекомендация**: оставить 12/26/9 как дефолт, но дать в config.yaml возможность переопределения. Walk-forward оптимизация покажет лучшие значения для конкретной пары.

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Молодой рынок | Первые 26 баров: EMA(26) нет данных | Возвращать `None` пока нет 26 баров |
| Flash crash | Один экстремальный бар резко сдвигает обе EMA | MACD Histogram резко отрицательный → ложный сигнал |
| Flat рынок | MACD ≈ 0, много ложных пересечений | Фильтр: |Histogram| > threshold (например, 0.1% от цены) |

#### Rust оптимизация

```rust
pub struct MACD {
    fast_ema: EMA,    // EMA(12)
    slow_ema: EMA,    // EMA(26)
    signal_ema: EMA,  // EMA(9) от MACD Line
}

impl MACD {
    pub fn update(&mut self, close: f64) -> Option<MACDOutput> {
        let fast = self.fast_ema.update(close)?;
        let slow = self.slow_ema.update(close)?;
        
        let macd_line = fast - slow;
        let signal = self.signal_ema.update(macd_line)?;
        let histogram = macd_line - signal;
        
        Some(MACDOutput { macd_line, signal, histogram })
    }
}
```

**Оптимизация**: три EMA, каждый O(1). Не нужно хранить историю.

---

### 2.3 Stochastic Oscillator

| Параметр | Значение |
|---|---|
| **Автор** | George Lane, 1950-е |
| **Периоды** | K=14, D=3 (smoothing) |
| **Диапазон** | 0–100 |
| **Пороги** | < 20 перепродан, > 80 перекуплен |

#### Формула

```
%K = 100 × (Close - Lowest Low(N)) / (Highest High(N) - Lowest Low(N))

%D = SMA(%K, 3)    // сигнальная линия

Где:
  Lowest Low(N)  = минимум Low за N периодов
  Highest High(N) = максимум High за N периодов
```

#### Магические числа
| Число | Источник | Комментарий |
|---|---|---|
| 14 | Lane | Уайлдеровский период |
| 3 | Lane | SMA сглаживание %K → %D |
| 20/80 | Lane | Пороги перекупленности/перепроданности |

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Highest == Lowest (все цены равны) | Деление на 0 | Clamp: Stochastic = 50 |
| Сильный тренд | Stochastic «застревает» в зоне > 80 или < 20 | Не использовать как standalone сигнал; только как фильтр |
| Низкая ликвидность | Один wick создаёт экстремум | Использовать smoothed stochastic (SMA/KD) |

#### Проблема для крипты

Обычный Stochastic использует High-Low диапазон. На крипте с её экстремальными wicks (длинными тенями) High-Low диапазон часто слишком широк → Stochastic нечувствителен. **Stochastic RSI решает эту проблему** (см. 2.4).

**Вердикт**: заменён на Stochastic RSI. Не используется отдельно.

---

### 2.4 Stochastic RSI — ★ ВЫБРАН (Top 3)

| Параметр | Значение |
|---|---|
| **Автор** | Tushar Chande & Stanley Kroll, 1994 |
| **Периоды** | RSI_period=14, Stoch_period=14, K_smooth=3, D_smooth=3 |
| **Диапазон** | 0–100 |
| **Пороги** | < 20 перепродан, > 80 перекуплен |

#### Формула

```
RSI = RSI(Close, 14)

StochRSI_K = (RSI - Lowest RSI(14)) / (Highest RSI(14) - Lowest RSI(14))
StochRSI_K = StochRSI_K × 100                    // масштабирование в 0-100
StochRSI_K = SMA(StochRSI_K_raw, 3)              // сглаживание K
StochRSI_D = SMA(StochRSI_K, 3)                  // сигнальная линия

Сигналы:
  StochRSI < 20 → зона перепроданности (вход лонг в тренде)
  StochRSI > 80 → зона перекупленности (вход шорт в тренде)
  K пересекает D снизу вверх → бычий моментум
  K пересекает D сверху вниз → медвежий моментум
```

#### Магические числа
| Число | Источник | Комментарий |
|---|---|---|
| 14/14/3/3 | Chande & Kroll | Стандартные параметры. RSI_period=Stoch_period=14, оба smooth=3 |

#### Почему выбран, а не обычный Stochastic

| Критерий | Stochastic | Stochastic RSI |
|---|---|---|
| **База данных** | High-Low диапазон | RSI (нормализован 0-100) |
| **Чувствительность** | Низкая на крипте (wicks) | Высокая (RSI уже сглажен) |
| **Нормализация** | Нет (зависит от волатильности) | Да (RSI всегда 0-100) |
| **Ложные сигналы** | Меньше (менее чувствителен) | Больше (но компенсируется фильтрами тренда) |

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Все RSI значения одинаковые | Highest == Lowest → деление на 0 | Clamp: 50 |
| RSI = 100 все время | StochRSI = 100 (корректно) | Проверить: если RSI = 100 > 3 баров → аномалия данных |
| Первые 14+14+3+3 баров | Много warm-up | Возвращать `None` пока нет достаточно данных |

#### Rust оптимизация

```rust
pub struct StochasticRSI {
    rsi: RSI,                        // RSI(14)
    stoch_period: usize,             // 14
    k_sma: SMA,                      // SMA(3) для сглаживания K
    d_sma: SMA,                      // SMA(3) для D
    rsi_buffer: VecDeque<f64>,       // кольцевой буфер RSI значений
    min_count: usize,                // 14+14+3+3 = 34 минимум
}

impl StochasticRSI {
    pub fn update(&mut self, close: f64) -> Option<(f64, f64)> {
        let rsi_val = self.rsi.update(close)?;  // None если RSI не готов
        self.rsi_buffer.push_back(rsi_val);
        
        if self.rsi_buffer.len() > self.stoch_period {
            self.rsi_buffer.pop_front();
        }
        
        if self.rsi_buffer.len() < self.stoch_period {
            return None;
        }
        
        let min_rsi = self.rsi_buffer.iter().copied().fold(f64::INFINITY, f64::min);
        let max_rsi = self.rsi_buffer.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        
        let raw_k = if (max_rsi - min_rsi).abs() < f64::EPSILON {
            50.0  // все RSI одинаковые
        } else {
            (rsi_val - min_rsi) / (max_rsi - min_rsi) * 100.0
        };
        
        let k = self.k_sma.update(raw_k)?;
        let d = self.d_sma.update(k)?;
        
        Some((k, d))
    }
}
```

#### Почему Top 3
1. **Высокая чувствительность**: в 2-3 раза чувствительнее обычного RSI → лучше тайминг входа
2. **Чёткие зоны**: 0-100 с порогами 20/80 → легко программируется
3. **Комплементарность с трендом**: StochRSI < 20 + EMA кроссовер бычий = точный вход
4. **Распространённость**: поддерживается на всех биржах, библиотеках, API

---

### 2.5 Fisher Transform — ★ ВЫБРАН (Top 3)

| Параметр | Значение |
|---|---|
| **Автор** | John Ehlers, 2002 |
| **Период** | 9 |
| **Диапазон** | Примерно -3.0 до +3.0 (неограничен теоретически) |
| **Пороги** | Разворот от ±2.0 |

#### Формула

```
Step 1: Нормализация цены в диапазон [0, 1]
  Value = 0.33 × 2 × ((Close - Lowest Low(N)) / (Highest High(N) - Lowest Low(N)) - 0.5)
  + 0.67 × Previous Value
  
  // Value ограничен [-0.99, 0.99] для предотвращения бесконечности

Step 2: Fisher Transform
  Fisher = 0.5 × ln((1 + Value) / (1 - Value)) + 0.5 × Previous Fisher

  Где ln() — натуральный логарифм.

Интерпретация:
  Fisher > +2.0 и начинает падать → медвежий разворот
  Fisher < -2.0 и начинает расти → бычий разворот
  Fisher пересекает Signal → моментум сигнал
```

#### Магические числа
| Число | Источник | Комментарий |
|---|---|---|
| 9 | Ehlers | Эмпирически оптимальный для 1H таймфрейма |
| 0.33 / 0.67 | Ehlers | Сглаживание: 33% нового значения + 67% предыдущего |
| 0.99 | Математика | Ограничение Value для предотвращения ln(0) |

#### Уникальность

Fisher Transform — **единственный** индикатор, который преобразует распределение цен в гауссово. Это даёт:

| Свойство | Выгода |
|---|---|
| **Экстремумы чётко определены** | Разворот от ±2.0 — статистически редкое событие |
| **Нормальное распределение сигнала** | Можно использовать z-score логику |
| **Симметрия** | Бычий и медвежий развороты имеют одинаковую структуру |

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Value → ±1.0 | ln(2/0) = ∞ → бесконечность | Clamp Value в [-0.99, 0.99] |
| Flat рынок | Fisher ≈ 0, нет сигналов | Ожидаемо: нет тренда → нет разворотов |
| Все бары одинаковые | Value = 0, Fisher = 0 | Корректно: нет движения |

#### Rust оптимизация

```rust
pub struct FisherTransform {
    period: usize,
    value: f64,
    fisher: f64,
    high_buffer: VecDeque<f64>,
    low_buffer: VecDeque<f64>,
}

impl FisherTransform {
    pub fn update(&mut self, high: f64, low: f64) -> Option<(f64, f64)> {
        self.high_buffer.push_back(high);
        self.low_buffer.push_back(low);
        
        if self.high_buffer.len() > self.period {
            self.high_buffer.pop_front();
            self.low_buffer.pop_front();
        }
        
        if self.high_buffer.len() < self.period {
            return None;
        }
        
        let min_low = self.low_buffer.iter().copied().fold(f64::INFINITY, f64::min);
        let max_high = self.high_buffer.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        
        let range = max_high - min_low;
        let raw = if range < f64::EPSILON {
            0.0
        } else {
            2.0 * ((high - min_low) / range - 0.5)
        };
        
        // Smoothed value с clamp [-0.999, 0.999]
        self.value = (0.33 * raw + 0.67 * self.value).clamp(-0.999, 0.999);
        
        // Fisher transform
        let fisher_raw = 0.5 * ((1.0 + self.value) / (1.0 - self.value)).ln();
        self.fisher = 0.5 * fisher_raw + 0.5 * self.fisher;
        
        Some((self.fisher, fisher_raw))
    }
}
```

#### Почему Top 3
1. **Уникальная математика**: ни один другой индикатор не даёт гауссово распределение
2. **Чёткие разворотные сигналы**: ±2.0 — статистически значимые экстремумы
3. **Низкий лаг**: Ehlers оптимизировал для минимизации задержки
4. **Комплементарность**: Fisher разворот + StochRSI выход из зоны = сильный тайминг

---

### 2.6 CCI — Commodity Channel Index — ★ ВЫБРАН (Top 3)

| Параметр | Значение |
|---|---|
| **Автор** | Donald Lambert, 1980 |
| **Период** | 20 |
| **Диапазон** | Неограничен (обычно -200 до +200) |
| **Пороги** | > 100 перекуплен, < -100 перепродан |

#### Формула

```
Step 1: Typical Price
  TP = (High + Low + Close) / 3

Step 2: SMA(TP, 20)
  SMA_TP = SMA(TP, 20)

Step 3: Mean Deviation
  MD = Σ|TP(i) - SMA_TP| / 20

Step 4: CCI
  CCI = (TP - SMA_TP) / (0.015 × MD)

Где 0.015 — масштабная константа.
```

#### Магические числа
| Число | Источник | Комментарий |
|---|---|---|
| 20 | Lambert | ~торговый день на 1H |
| 0.015 | Lambert | Масштабная константа: ~70-80% значений CCI попадают в диапазон [-100, +100] при этом множителе |
| 100/-100 | Lambert | Пороги: CCI > 100 означает цена на > 1 MAD от среднего |

#### Почему выбран, а не отброшен

CCI даёт информацию, **комплементарную** RSI:

| Индикатор | Что измеряет | Слабость |
|---|---|---|
| **RSI** | Силу движения (gain vs loss) | Не учитывает отклонение от среднего |
| **CCI** | Отклонение от среднего (price vs SMA) | Не учитывает направление движения |

Вместе: RSI показывает «как сильно движение», CCI показывает «насколько далеко от нормы».

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Mean Deviation = 0 (все TP одинаковые) | Деление на 0 | Clamp: CCI = 0 |
| Экстремальный бар | CCI = ±500+ | Clamp в [-500, 500] для предотвращения overflow |
| Недостаточно данных | Первые 20 баров | Возвращать `None` |

#### Rust оптимизация

```rust
pub struct CCI {
    period: usize,
    tp_sma: SMA,
    md_buffer: VecDeque<f64>,
    md_sum: f64,
}

impl CCI {
    pub fn update(&mut self, high: f64, low: f64, close: f64) -> Option<f64> {
        let tp = (high + low + close) / 3.0;
        let sma_tp = self.tp_sma.update(tp)?;
        
        // Mean deviation (rolling)
        self.md_buffer.push_back((tp - sma_tp).abs());
        self.md_sum += (tp - sma_tp).abs();
        
        if self.md_buffer.len() > self.period {
            self.md_sum -= self.md_buffer.pop_front().unwrap();
        }
        
        if self.md_buffer.len() < self.period {
            return None;
        }
        
        let md = self.md_sum / self.period as f64;
        
        if md < f64::EPSILON {
            return Some(0.0);
        }
        
        Some((tp - sma_tp) / (0.015 * md))
    }
}
```

#### Почему Top 3
1. **Комплементарность с RSI**: измеряет другой аспект (отклонение vs сила)
2. **Чёткие пороги**: ±100 — статистически обоснованный уровень
3. **Дивергенции**: CCI дивергенция часто более надёжна, чем RSI (из-за типичной цены)
4. **Тренд-подтверждение**: CCI > 100 продолжительное время = сильный тренд

---

### 2.7 Williams %R

| Параметр | Значение |
|---|---|
| **Автор** | Larry Williams, 1973 |
| **Период** | 14 |
| **Диапазон** | -100 до 0 |
| **Пороги** | < -80 перепродан, > -20 перекуплен |

#### Формула

```
%R = (Highest High(14) - Close) / (Highest High(14) - Lowest Low(14)) × (-100)

Или эквивалентно:
%R = -(Stochastic)     // инвертированный Stochastic
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Инвертированный Stochastic** | Математически идентичен Stochastic, только шкала от -100 до 0 вместо 0-100. Не даёт новой информации. |
| **Те же проблемы** | Те же wick-sensitivity проблемы, что и у Stochastic |
| **Менее распространён** | Stochastic более распространён в библиотеках и API |
| **Заменён на Stochastic RSI** | StochRSI решает все проблемы Williams %R |

---

### 2.8 Awesome Oscillator

| Параметр | Значение |
|---|---|
| **Автор** | Bill Williams |
| **Периоды** | SMA(5) - SMA(34) от Median Price |
| **Диапазон** | Неограничен |

#### Формула

```
Median Price = (High + Low) / 2
AO = SMA(Median Price, 5) - SMA(Median Price, 34)

Сигналы:
  AO > 0 → бычий моментум
  AO < 0 → медвежий моментум
  AO пересекает 0 → сигнал
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Нет пороговых зон** | AO — «голый» осциллятор без зон перекупленности. Нельзя программно определить «слишком много» |
| **Слишком прост** | Это просто разница двух SMA. Никакой нормализации, никакого сглаживания |
| **Дублирует MACD** | MACD = EMA_fast - EMA_slow с сигнальной линией. AO = SMA_fast - SMA_slow без сигнальной. MACD строго лучше |
| **Магические числа 5/34** | Нет обоснования для этих периодов. Фибоначчи? Совпадение? |

---

### 2.9 TSI — True Strength Index

| Параметр | Значение |
|---|---|
| **Автор** | William Blau, 1991 |
| **Периоды** | Double-smoothed: 25 и 13 |
| **Диапазон** | -100 до +100 |

#### Формула

```
PC = Close - Close(1)                    // Price Change
PCDS = EMA(EMA(PC, 25), 13)             // Double Smoothed PC
APCDS = EMA(EMA(|PC|, 25), 13)          // Double Smoothed |PC|

TSI = 100 × PCDS / APCDS
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Двойное сглаживание = лаг** | 2-уровневое EMA даёт значительную задержку. Fisher Transform даёт более чёткие развороты с меньшим лагом |
| **Нет уникальной информации** | TSI измеряет тот же моментум, что и MACD, но с бо́льшим лагом |
| **Пороги нестандартизированы** | В отличие от RSI (30/70), нет общепринятых порогов для TSI |
| **Fisher Transform лучше** | Для разворотов Fisher даёт гауссово распределение с чёткими экстремумами |

---

### 2.10 Elliott Wave Oscillator

| Параметр | Значение |
|---|---|
| **Периоды** | SMA(5) - SMA(35) от Close |

#### Формула

```
EWO = SMA(Close, 5) - SMA(Close, 35)

// В сущности тот же Awesome Oscillator, но от Close вместо Median Price
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Субъективен** | Назван в честь волн Эллиотта, но формула — обычная разница средних. «Волны» Эллиотта субъективны и не программируемы |
| **Дублирует AO** | Тот же расчёт, другой источник цены |
| **Нет порогов** | Как и AO — «голый» осциллятор |
| **5/35 без обоснования** | Магические числа без эмпирического обоснования |

---

### 2.11 DeMarker

| Параметр | Значение |
|---|---|
| **Автор** | Tom DeMark |
| **Период** | 14 |
| **Диапазон** | 0–1 |
| **Пороги** | < 0.3 перепродан, > 0.7 перекуплен |

#### Формула

```
DeMax(i) = if High(i) > High(i-1) then High(i) - High(i-1) else 0
DeMin(i) = if Low(i) < Low(i-1) then Low(i-1) - Low(i) else 0

DeMarker = SMA(DeMax, 14) / (SMA(DeMax, 14) + SMA(DeMin, 14))
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Информативно беден** | Использует только High/Low изменение, игнорирует Close и объём |
| **Лаг** | SMA-сглаживание даёт лаг |
| **RSI лучше** | RSI использует Close (более репрезентативно), имеет более обоснованные пороги |
| **Нет уникального применения** | Нет сценария, где DeMarker лучше RSI |

---

### 2.12 Price Oscillator (PPO)

| Параметр | Значение |
|---|---|
| **Периоды** | Fast=12, Slow=26 |
| **Диапазон** | Процентный (неограничен) |

#### Формула

```
PPO = ((EMA_fast - EMA_slow) / EMA_slow) × 100

// В отличие от MACD, PPO нормализован процентом → сравним между активами
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Дублирует MACD** | Та же логика (EMA_fast - EMA_slow), но в процентах |
| **MACD имеет сигнальную линию** | MACD добавляет EMA от себя (сигнальная линия + гистограмма), PPO — нет |
| **Единственный плюс не нужен** | Процентная нормализация полезна для сравнения активов, но бот торгует одну пару (BTC/USDT) |
| **Оставлен в документе** | Research Indicators.md упоминает PPO как альтернативу MACD, но выбирает MACD |

---

### 2.13 KST — Know Sure Thing

| Параметр | Значение |
|---|---|
| **Автор** | Martin Pring |
| **Периоды** | 4 ROC с периодами 10, 15, 20, 30, каждая со своим SMA |

#### Формула

```
ROC1 = ROC(Close, 10),  smoothed by SMA(ROC1, 10),  weight = 1
ROC2 = ROC(Close, 15),  smoothed by SMA(ROC2, 10),  weight = 2
ROC3 = ROC(Close, 20),  smoothed by SMA(ROC3, 10),  weight = 3
ROC4 = ROC(Close, 30),  smoothed by SMA(ROC4, 15),  weight = 4

KST = (ROC1×1 + ROC2×2 + ROC3×3 + ROC4×4) / 10
Signal = SMA(KST, 9)
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Чрезмерная сложность** | 4 периода ROC + 4 SMA + веса + сигнальная линия = 13 параметров |
| **Масса магических чисел** | 10/15/20/30 для ROC, 10/10/10/15 для SMA, веса 1/2/3/4, сигнал 9 — ни одно не обосновано |
| **Переобучение** | Столько параметров → высокий риск overfitting |
| **MACD делает то же проще** | MACD = EMA_fast - EMA_slow + сигнальная. Достаточно для моментума |

---

### 2.14 Coppock Curve

| Параметр | Значение |
|---|---|
| **Автор** | Edwin Coppock, 1962 |
| **Периоды** | WMA(ROC(14) + ROC(11), 10) |

#### Формула

```
Coppock = WMA(ROC(Close, 14) + ROC(Close, 11), 10)

Где WMA = Weighted Moving Average (больший вес последним данным)
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Создан для месячных данных** | Coppock разработан для определения дна медвежьего рынка на МЕСЯЧНЫХ данных акций. На 1H крипте — бессмысленно |
| **11/14 — магические числа** | Coppock сам сказал, что взял 11 и 14 как «время скорби» в религии |
| **Только для дна рынка** | Не даёт сигналов перекупленности или разворота сверху |
| **WMA без обоснования** | Почему WMA, а не EMA? |

---

### 2.15 Chande Momentum Oscillator

| Параметр | Значение |
|---|---|
| **Автор** | Tushar Chande, 1994 |
| **Период** | 14 |
| **Диапазон** | -100 до +100 |
| **Пороги** | > 50 перекуплен, < -50 перепродан |

#### Формула

```
CMO = ((Sum Gain - Sum Loss) / (Sum Gain + Sum Loss)) × 100

Где:
  Sum Gain = Σ max(0, Close(i) - Close(i-1)) за N периодов
  Sum Loss = Σ max(0, Close(i-1) - Close(i)) за N периодов
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **RSI с другой формулой** | RSI = Gain/(Gain+Loss) × 100, CMO = (Gain-Loss)/(Gain+Loss) × 100. Математически связаны: CMO = 2×RSI - 100 |
| **Нет преимущества** | CMO не имеет дополнительной информации по сравнению с RSI |
| **RSI более распространён** | Больше документации, библиотек, примеров |
| **Те же пороги** | CMO 50 = RSI 50 (нейтраль), CMO 75 = RSI 87.5. Корреляция 1.0 по сути |

---

### 2.16 Elder Ray Index

| Параметр | Значение |
|---|---|
| **Автор** | Alexander Elder |
| **Период** | EMA(13) как базовая линия |

#### Формула

```
Bull Power = High - EMA(13)
Bear Power = Low - EMA(13)

Сигналы:
  Bull Power > 0 AND Bear Power > 0 → бычий тренд
  Bull Power < 0 AND Bear Power < 0 → медвежий тренд
  Bull Power > 0 AND Bear Power < 0 → консолидация
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Просто High/Low - EMA** | Никакой нормализации, никакого сглаживания |
| **Нет порогов** | Что значит «слишком много Bull Power»? Нет зон перекупленности |
| **Дублирует трендовые индикаторы** | Цена > EMA → тренд уже определён модулем 1 |
| **Неинформативен** | Bull Power и Bear Power всегда разного знака (High > Low) → «консолидация» не определяется |

---

### 2.17 Momentum (Rate of Change)

#### Формула

```
Momentum = Close - Close(N)
ROC = ((Close - Close(N)) / Close(N)) × 100
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Сырой индикатор** | Просто разница цен. Нет нормализации, нет сглаживания |
| **Дублирует MACD** | MACD = EMA_fast - EMA_slow — тот же моментум, но сглаженный |
| **Используется как компонент** | ROC входит в KST, но не как standalone |

---

### 2.18 Aroon Indicator

#### Формула

```
Aroon Up = ((N - периодов с максимума) / N) × 100
Aroon Down = ((N - периодов с минимума) / N) × 100

// Aroon Up = 100 если максимум был на последнем баре
// Aroon Down = 100 если минимум был на последнем баре
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Нечувствителен** | Aroon зависит от положения экстремума, а не от силы движения. Цена может резко двигаться, но Aroon не покажет |
| **Дублирует ADX** | ADX определяет силу тренда точнее. Aroon = «сколько баров назад был экстремум» |
| **Нет порогов перекупленности** | Только 100 (максимум/минимум на последнем баре) |

---

### 2.19 DPO — Detrended Price Oscillator

#### Формула

```
DPO = Close(N/2 + 1) - SMA(N)

// Сдвигает SMA назад на N/2+1 и вычитает из цены
// Убирает тренд, показывает циклы
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Look-ahead bias** | Формула использует SMA(N/2+1), который сдвинут назад → в реальном времени недоступен без задержки |
| **Циклический анализ не нужен** | Для торговли нужны моментум и развороты, не циклы |
| **Нет порогов** | Нет зон перекупленности/перепроданности |

---

### 2.20 Vortex Indicator

#### Формула

```
VM+ = |High(i) - Low(i-1)|
VM- = |Low(i) - High(i-1)|

VI+ = SMA(VM+, N) / SMA(TR, N)
VI- = SMA(VM-, N) / SMA(TR, N)
```

#### Вердикт: ЗАБРАКОВАН

| Причина | Объяснение |
|---|---|
| **Дублирует ADX + DI** | VI+ и VI- — по сути +DI и -DI Уайлдера, пересчитанные |
| **Сложнее** | Больше вычислений при той же информации |
| **Менее распространён** | Меньше библиотечной поддержки |

---

### 2.21 Ультра-осцилляторы (MFI, CMF, DPO-варианты)

#### MFI — Money Flow Index

```
MFI = 100 - 100 / (1 + Money Flow Ratio)
Money Flow Ratio = Σ(Positive MF) / Σ(Negative MF)
MF = Typical Price × Volume
```

**Вердикт**: уже выбран в Модуле 4 (объёмные индикаторы) как RSI + объём. Не дублировать в модуле осцилляторов.

#### CMF — Chaikin Money Flow

```
CMF = Σ(MF Volume × ((Close-Low)-(High-Close))/(High-Low)) / Σ(Volume)
```

**Вердикт**: ЗАБРАКОВАН. MFI имеет чёткие пороги (0-100), CMF — нет. MFI строго лучше.

#### ADX Oscillator / DI Oscillator

**Вердикт**: дублирует ADX из модуля тренда. Не используется.

---

## 3. Сводная таблица: все осцилляторы

| # | Индикатор | Статус | Причина |
|---|---|---|---|
| 1 | **RSI (14)** | ✅ ОСТАВЛЕН | Базовый стандарт. Подтверждение входа. Не Top 3, но используется как фильтр |
| 2 | **MACD (12,26,9)** | ✅ ОСТАВЛЕН | Моментум + кроссовер + дивергенция. Двойная функция |
| 3 | **Stochastic RSI** | ⭐ **TOP 3** | Чувствительный тайминг. Зоны 20/80. Лучший для входа |
| 4 | **Fisher Transform** | ⭐ **TOP 3** | Уникальная гауссова трансформация. Чёткие развороты ±2.0 |
| 5 | **CCI (20)** | ⭐ **TOP 3** | Комплементарен RSI (отклонение vs сила). Пороги ±100 |
| 6 | Williams %R | ❌ | Инвертированный Stochastic. Нет нового |
| 7 | Awesome Oscillator | ❌ | Нет порогов. Дублирует MACD |
| 8 | TSI | ❌ | Двойной лаг. Fisher лучше |
| 9 | Elliott Wave | ❌ | Субъективен. Дублирует AO |
| 10 | DeMarker | ❌ | Информативно беден. RSI лучше |
| 11 | Price Oscillator (PPO) | ❌ | Дублирует MACD. Нет сигнальной линии |
| 12 | KST | ❌ | 13 параметров. Переобучение |
| 13 | Coppock Curve | ❌ | Для месячных данных. На 1H крипте бессмысленно |
| 14 | Chande MO | ❌ | CMO = 2×RSI - 100. Полная избыточность |
| 15 | Elder Ray | ❌ | Нет нормализации, нет порогов |
| 16 | Momentum / ROC | ❌ | Сырой индикатор. Компонент, не standalone |
| 17 | Aroon | ❌ | Нечувствителен. Дублирует ADX |
| 18 | DPO | ❌ | Look-ahead bias. Нет порогов |
| 19 | Vortex | ❌ | Дублирует ADX+DI. Сложнее |
| 20 | MFI | ↔️ Модуль 4 | Уже в объёмных. Не дублировать |
| 21 | CMF | ❌ | MFI лучше (пороги 0-100) |
| 22 | Обычный Stochastic | ❌ | Заменён на Stochastic RSI |

---

## 4. Финальный выбор: Топ 3 + базовые фильтры

### ⭐ Top 3 (primary осцилляторы для бота)

| # | Индикатор | Роль в системе | Пороги | Конфиг |
|---|---|---|---|---|
| 1 | **Stochastic RSI** | Тайминг входа: выход из зоны перепроданности в бычьем тренде | < 20 / > 80 | `stoch_rsi_period: 14, k_smooth: 3, d_smooth: 3` |
| 2 | **Fisher Transform** | Разворотный сигнал: поворот от ±2.0 | ±2.0 | `fisher_period: 9` |
| 3 | **CCI (20)** | Отклонение от среднего: дополнение к RSI | ±100 | `cci_period: 20` |

### 📊 Базовые фильтры (оставлены, но не primary)

| Индикатор | Роль | Конфиг |
|---|---|---|
| **RSI (14)** | Общий фильтр: не входить если перекуплен/перепродан | `rsi_period: 14, overbought: 70, oversold: 30` |
| **MACD (12,26,9)** | Моментум + дивергенция: гистограмма как подтверждение | `macd_fast: 12, macd_slow: 26, macd_signal: 9` |

### 🔗 Конфликты и решения

| Конфликт | Решение |
|---|---|
| StochRSI < 20 (buy) но RSI > 70 (overbought) | **RSI имеет приоритет**. StochRSI показывает локальный моментум, RSI — общий. Если RSI > 70, не покупать |
| Fisher разворот вверх, но CCI < -100 и падает | **Fisher имеет приоритет** для разворотов. CCI подтверждает тренд, Fisher — экстремум |
| MACD histogram > 0, но StochRSI > 80 | **StochRSI предупреждает** о локальной перекупленности. Не входить, ждать откат |
| Все 3 Top дают противоречивые сигналы | **Не торговать**. Система требует консенсуса ≥ 2 из 3 |

### 📐 Сигнальная логика (полная)

```
LONG ВХОД:
  PRIMARY:   EMA20 > EMA50 AND ADX > 25 AND Цена > Supertrend AND Цена > Kumo
  ФИЛЬТР 1:  RSI(14) < 70                          // не перекуплен
  ФИЛЬТР 2:  StochRSI < 20 ИЛИ StochRSI K > D      // зона перепроданности или моментум разворот
  ФИЛЬТР 3:  Fisher < 2.0                           // не в экстремуме перекупленности
  ФИЛЬТР 4:  CCI > -100                             // не в зоне перепроданности
  
SHORT ВХОД:
  PRIMARY:   EMA20 < EMA50 AND ADX > 25 AND Цена < Supertrend AND Цена < Kumo
  ФИЛЬТР 1:  RSI(14) > 30                           // не перепродан
  ФИЛЬТР 2:  StochRSI > 80 ИЛИ StochRSI K < D      // зона перекупленности или моментум разворот
  ФИЛЬТР 3:  Fisher > -2.0                          // не в экстремуме перепроданности
  ФИЛЬТР 4:  CCI < 100                              // не в зоне перекупленности

ВЫХОД / REVERSE:
  - Fisher разворот от ±2.0 (Fisher поворачивает вниз от +2.0 → выход из лонга)
  - StochRSI из зоны входа в противоположную зону
  - MACD histogram flip (бычий → медвежий)
  - SL/TP по ATR
  - SAR flip (из модуля тренда)

ДИВЕРГЕНЦИЯ (предупреждение о развороте):
  - Цена: новый high, RSI: lower high → медвежья дивергенция
  - Цена: новый low, RSI: higher low → бычья дивергенция
  - Цена: новый high, MACD histogram: lower high → медвежья
  - Дивергенция → снижение размера позиции на 50%, не полный разворот
```

---

## 5. Rust архитектура

### Trait: Oscillator

```rust
pub trait Oscillator {
    type Output;
    
    /// Обновить индикатор новым баром. Возвращает None если нет достаточных данных.
    fn update(&mut self, bar: &OHLCV) -> Option<Self.Output>;
    
    /// Минимальное количество баров для warm-up
    fn warmup_period(&self) -> usize;
    
    /// Текущее значение (без обновления)
    fn current(&self) -> Option<Self.Output>;
}
```

### Реализации

```rust
pub struct OscillatorSet {
    pub rsi: RSI,                    // 14
    pub macd: MACD,                  // 12, 26, 9
    pub stoch_rsi: StochasticRSI,    // 14, 14, 3, 3
    pub fisher: FisherTransform,     // 9
    pub cci: CCI,                    // 20
}

impl OscillatorSet {
    pub fn new(config: &OscillatorConfig) -> Self {
        Self {
            rsi: RSI::new(config.rsi_period),
            macd: MACD::new(config.macd_fast, config.macd_slow, config.macd_signal),
            stoch_rsi: StochasticRSI::new(
                config.stoch_rsi_period,
                config.stoch_rsi_period,
                config.stoch_rsi_smooth_k,
                config.stoch_rsi_smooth_d,
            ),
            fisher: FisherTransform::new(config.fisher_period),
            cci: CCI::new(config.cci_period),
        }
    }
    
    pub fn update(&mut self, bar: &OHLCV) -> OscillatorSignals {
        let rsi = self.rsi.update(bar.close);
        let macd = self.macd.update(bar.close);
        let stoch_rsi = self.stoch_rsi.update(bar.close);
        let fisher = self.fisher.update(bar.high, bar.low);
        let cci = self.cci.update(bar.high, bar.low, bar.close);
        
        OscillatorSignals { rsi, macd, stoch_rsi, fisher, cci }
    }
}

#[derive(Debug, Clone)]
pub struct OscillatorSignals {
    pub rsi: Option<f64>,
    pub macd: Option<MACDOutput>,
    pub stoch_rsi: Option<(f64, f64)>,  // (K, D)
    pub fisher: Option<(f64, f64)>,     // (Fisher, Signal)
    pub cci: Option<f64>,
}

impl OscillatorSignals {
    pub fn is_overbought(&self, config: &OscillatorConfig) -> bool {
        self.rsi.map_or(false, |r| r > config.rsi_overbought)
    }
    
    pub fn is_oversold(&self, config: &OscillatorConfig) -> bool {
        self.rsi.map_or(false, |r| r < config.rsi_oversold)
    }
    
    pub fn long_timing_signal(&self) -> Option<f64> {
        // StochRSI выход из перепроданности
        let stoch_buy = self.stoch_rsi.and_then(|(k, d)| {
            if k < 20.0 && k > d { Some(1.0) } else { None }
        });
        
        // Fisher разворот снизу
        let fisher_buy = self.fisher.and_then(|(f, _)| {
            if f < -1.5 { Some(1.0) } else { None }
        });
        
        match (stoch_buy, fisher_buy) {
            (Some(_), Some(_)) => Some(1.0),  // оба
            (Some(_), None) | (None, Some(_)) => Some(0.5),  // один
            (None, None) => None,
        }
    }
}
```

### Вычислительная сложность

| Индикатор | Обновление | Память | Примечание |
|---|---|---|---|
| RSI | O(1) | O(1) | Wilder smoothing |
| MACD | O(1) | O(1) | 3 EMA |
| Stochastic RSI | O(1) | O(N) | Ring buffer RSI значений |
| Fisher Transform | O(1) | O(N) | Ring buffer High/Low |
| CCI | O(1) | O(N) | Ring buffer TP для MD |
| **Итого** | **O(1)** | **O(N)** | **N = max период (~26)** |

---

## 6. Итоговые выводы

### Главный принцип

> **Осцилляторы — фильтры тайминга, не генераторы направления.**
> Напределение направления → Модуль 1 (тренд).
> Оптимизация точки входа → Модуль 2 (осцилляторы).

### Три ключевых свойства хорошего осциллятора для крипты

1. **Нормализация**: фиксированный диапазон (0-100 или чёткие экстремумы) → программные пороги
2. **Низкий лаг**: крипта движется быстро, лаг = потеря прибыли
3. **Комплементарность**: каждый осциллятор должен измерять РАЗНЫЙ аспект моментума

### Что отбрасывало большинство кандидатов

| Причина отбрасывания | Количество |
|---|---|
| Дублирует RSI или MACD | 7 (Williams %R, Chande MO, TSI, PPO, Momentum, CMF, AO/EWO) |
| Нет пороговых зон | 4 (AO, Elder Ray, DPO, Momentum) |
| Слишком много магических чисел / переобучение | 2 (KST, Coppock) |
| Субъективен / не программируем | 1 (Elliott Wave) |
| Заменён лучшей версией | 2 (Stochastic → StochRSI, DeMarker → RSI) |
| Дублирует трендовый индикатор | 2 (Aroon → ADX, Vortex → ADX+DI) |

---

*Документ: 02-oscillators-momentum.md | Агент 2 | 2026-04-17*
