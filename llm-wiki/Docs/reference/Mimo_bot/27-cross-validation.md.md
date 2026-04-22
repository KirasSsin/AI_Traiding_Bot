
# Агент 27: Кросс-валидация и защита от переобучения (Cross-Validation & Overfitting)

> Модуль оценки надёжности торговых стратегий для крипто-бота.
> Полный каталог методов валидации, anti-patterns, формулы, edge cases, Rust-реализации.
> Crypto-specific адаптации для 24/7 рынка.

---

## Содержание

1. [Введение и классификация методов](#1-введение)
2. [Методы кросс-валидации — полный каталог](#2-методы-кросс-валидации)
3. [Anti-patterns: look-ahead bias, data snooping, multiple testing](#3-anti-patterns)
4. [Deflated Sharpe Ratio и PBO](#4-deflated-sharpe-ratio-и-pbo)
5. [Crypto-specific адаптации](#5-crypto-specific-адаптации)
6. [Параметры по умолчанию](#6-параметры-по-умолчанию)
7. [Rust-реализации](#7-rust-реализации)

---

## 1. Введение

### 1.1 Зачем кросс-валидация в трейдинге

Классическая ML кросс-валидация (K-Fold, LOO) **не работает** для финансовых временных рядов из-за:

- **Look-ahead bias** — обучение на будущих данных
- **Non-stationarity** — распределение доходностей меняется со временем
- **Serial correlation** — соседние наблюдения зависимы
- **Label overlap** — метки соседних баров могут совпадать из-за embargo

### 1.2 Классификация методов

```
Валидация временных рядов
├── Walk-Forward (Expanding/Sliding)
│   ├── Classic Walk-Forward
│   ├── Anchored Walk-Forward
│   └── Walk-Forward Analysis (WFA)
├── Purged K-Fold (PKFCV)
│   ├── Standard Purged K-Fold
│   ├── Purged K-Fold с Embargo
│   └── Combinatorial Purged CV (CCV)
├── Blocked Time Series Split (BTSCV)
├── Nested Cross-Validation
│   ├── Nested K-Fold
│   └── Nested Walk-Forward
├── Bootstrap Methods
│   ├── Stationary Bootstrap
│   ├── Moving Block Bootstrap
│   └── Politis-White Bootstrap
├── Monte Carlo Methods
│   ├── Monte Carlo CV
│   ├── Random Subsampling (Hold-out)
│   └── Synthetic Data Validation
├── Jackknife
│   ├── Delete-d Jackknife
│   └── Weighted Jackknife
└── Leave-One-Out (LOO) — [только для малых выборок]
```

### 1.3 Критерии выбора метода

| Критерий | Рекомендация |
|----------|-------------|
| Оценка OOS производительности | Walk-Forward |
| Оценка stability стратегии | Purged K-Fold / CCV |
| Оценка перебора параметров | Nested CV |
| Оценка устойчивости к шуму | Bootstrap / Monte Carlo |
| Малая выборка (< 1000 баров) | Jackknife / LOO |

---

## 2. Методы кросс-валидации

### 2.1 Time Series Split (TSS)

#### Формула

Для K фолдов, i-й фолд (i = 1, ..., K):

$$\text{Train}_i = [0, \lfloor T \cdot \frac{i}{K+1} \rfloor), \quad \text{Test}_i = [\lfloor T \cdot \frac{i}{K+1} \rfloor, \lfloor T \cdot \frac{i+1}{K+1} \rfloor)$$

#### Edge Cases
- **K ≥ N** → каждый фолд содержит < 2 наблюдений, невозможно обучить модель
- **K = 1** → обычный train/test split без валидации
- **Слишком большой train/test ratio** → тестовая выборка слишком мала для репрезентативной оценки

#### Ограничения
- **Не учитывает serial correlation** — соседние тестовые наблюдения зависят от train
- **Не защищает от look-ahead bias** при label overlap
- **Нет embargo** — информация "просачивается" через границы

#### Применение в крипто
- Подходит как **базовая проверка** перед переходом к Purged K-Fold
- Хорошо для **визуализации** стабильности стратегии во времени

---

### 2.2 Walk-Forward (Expanding Window)

#### Формула

```
Параметры:
  T       — общее количество наблюдений
  T_train — начальный размер тренировочного окна
  T_test  — размер тестового окна (шаг)
  α       — коэффициент расширения (0 = sliding, 1 = expanding)

Для i-й итерации (i = 0, 1, ..., K-1):
  Начало train:  0                      (expanding) или i·T_test (sliding)
  Конец train:   T_train + i·T_test     (expanding) или T_train + i·T_test (sliding)
  Начало test:   T_train + i·T_test
  Конец test:    T_train + (i+1)·T_test

  K = ⌊(T - T_train) / T_test⌋
```

#### Визуализация

```
Expanding Window (α = 1):
|===== TRAIN =====|== TEST ==|
|========= TRAIN =========|== TEST ==|
|============= TRAIN ============|== TEST ==|

Sliding Window (α = 0):
          |===== TRAIN =====|== TEST ==|
                    |===== TRAIN =====|== TEST ==|
                              |===== TRAIN =====|== TEST ==|
```

#### Edge Cases
- **T_test = 0** → невозможно оценить
- **T_train слишком мал** → модель недообучена
- **T_test слишком велик** → мало итераций, высокая дисперсия оценки
- **T_train + K·T_test > T** → последний фолд укорочен

#### Рекомендуемые параметры для крипто
```
train_ratio = 0.8        (T_train / T)
T_test = T · (1 - 0.8) / K   где K ≥ 5
Embargo = 2 × holding_period
```

#### Преимущества
- Имитирует реальный процесс торговли (обучение на прошлом, тестирование на будущем)
- Expanding window сохранает все исторические данные
- Sliding window адаптируется к non-stationarity

---

### 2.3 Purged K-Fold Cross-Validation (PKFCV)

#### Формула

```
Параметры:
  n_splits = 5       (по умолчанию)
  embargo = 2·H      (где H = holding_period в барах)
  purge = H           (период пуржа вокруг train)

Для i-й комбинации (i = 0, ..., n_splits-1):
  1. Определи Test fold: бары с индексами [i·⌊N/n_splits⌋, (i+1)·⌊N/n_splits⌋)
  2. Train = все бары MINUS Test
  3. Purge: удали из Train все бары в окне [test_start - purge, test_end + purge]
  4. Embargo: удали из Train все бары в окне [test_end, test_end + embargo]

  Purged_Train = Train \ {Purge_window} \ {Embargo_window}
```

#### Визуализация

```
Fold 0: [==== PURGE ====| TRAIN |== PURGE + EMBARGO ==| TEST |==== TRAIN ====]
Fold 1: [==== TRAIN ====|== PURGE + EMBARGO ==| TEST |==== TRAIN |== PURGE ==]
Fold 2: [== PURGE ==| TRAIN |== PURGE + EMBARGO ==| TEST |==== TRAIN ====]
...
```

#### Математическое обоснование

Embargo предотвращает утечку информации через **информационную зависимость**:

$$\text{I}(\text{Train}; \text{Test} | \text{Embargo}) \approx 0$$

где I — взаимная информация. Embargo гарантирует, что наблюдения в тестовой выборке не имеют значимой корреляции с последними наблюдениями тренировочной.

#### Edge Cases
- **embargo > test_fold_size** → train становится значительно меньше, возможен недообученный байас
- **embargo > T/n_splits** → полный overlap фолдов
- **Короткий holding_period → embargo ≈ 0** → PKFCV вырождается в обычный K-Fold
- **n_splits = 2** → минимальная валидация, высокий variance

#### Рекомендуемые параметры для крипто
```rust
const N_SPLITS: usize = 5;
const EMBARGO_MULTIPLIER: f64 = 2.0;  // embargo = 2 * holding_period
const PURGE_MULTIPLIER: f64 = 1.0;    // purge = holding_period

fn compute_embargo(holding_period: usize) -> usize {
    (holding_period as f64 * EMBARGO_MULTIPLIER).ceil() as usize
}
```

---

### 2.4 Combinatorial Purged Cross-Validation (CCV)

#### Формула

```
Генерация всех C(n_splits, test_groups) комбинаций:

  n_splits = 5
  test_groups = 1  (каждый фолд тестируется один раз)

  Итерация i: Test = fold_i, Train = остальные фолды (с purge + embargo)

  n_splits = 5, test_groups = 2:
  Итерация i: Test = fold_i ∪ fold_j, Train = остальные (с purge + embargo)
  Количество комбинаций: C(5,2) = 10
```

#### Математическое обоснование

CCV оценивает **Combinatorial Purged Sharpe Ratio**:

$$\hat{SR}_{CCV} = \frac{1}{C} \sum_{c=1}^{C} SR_c$$

где C = C(n_splits, test_groups) — количество комбинаций, а $SR_c$ — Sharpe Ratio на комбинации c.

#### Преимущества над PKFCV
- Оценивает **не только среднее**, но и **распределение** Sharpe Ratio
- Выявляет нестабильность стратегии при разных комбинациях
- Даёт более **консервативную** оценку

#### Edge Cases
- **test_groups = n_splits** → все фолды в тесте, нет обучающих данных
- **Большое n_splits** → экспоненциальный рост числа комбинаций
- **C(n_splits, test_groups) > 1000** → вычислительно дорого, рекомендуется сэмплирование

---

### 2.5 Nested Cross-Validation

#### Формула

```
Внешний цикл (оценка общей производительности):
  Для каждого outer_fold i:
    Outer_Train = все данные MINUS outer_test[i]
    Outer_Test = fold_i

    Внутренний цикл (подбор гиперпараметров):
      Для каждого inner_fold j:
        Inner_Train = Outer_Train MINUS inner_test[j]
        Inner_Test = inner_test[j]
        Обучи модель с гиперпараметрами θ_j на Inner_Train
        Оцени на Inner_Test
      Выбери лучшие θ* по результатам inner folds

    Обучи модель с θ* на Outer_Train
    Оцени на Outer_Test

  Оценка = среднее Outer_Test результатов
```

#### Зачем Nested
- **Внешний цикл** — оценка общей производительности (unbiased)
- **Внутренний цикл** — подбор гиперпараметров (biased, но контролируется)
- Без nested — оценка **завышена** из-за подгонки гиперпараметров

#### Edge Cases
- **Мало данных** → каждый inner fold слишком мал
- **Слишком много гиперпараметров** → inner цикл переобучается
- **Один inner fold** → вырождается в hold-out

---

### 2.6 Blocked Time Series Split (BTSCV)

#### Формула

```
Параметры:
  n_splits     = 5
  block_size   = T / n_splits
  gap          = holding_period  (разрыв между train и test)

Для i-го фолда:
  Test_block = i-й блок [i·block_size, (i+1)·block_size)
  Train_blocks = все остальные блоки (кроме соседних, если gap > 0)

  Если gap > 0:
    Исключи из Train: [test_start - gap, test_end + gap]
```

#### Преимущества
- Простота реализации
- Нет look-ahead bias (при правильном gap)
- Хорошо работает при **равномерной** волатильности

#### Ограничения
- Не учитывает **неравномерную** зависимость между блоками
- Меньше данных для обучения (каждый фолд теряет один блок)
- Gap не адаптируется к динамической волатильности

---

### 2.7 Bootstrap Methods

#### 2.7.1 Stationary Bootstrap

```
Параметры:
  p = 1/expected_block_length  (вероятность "сброса" блока)

Алгоритм:
  1. Выбери случайный начальный индекс s ∈ [0, N)
  2. Генерируй блоки:
     - С вероятностью p: начни новый блок из случайного индекса
     - Иначе: продолжи текущий блок
  3. Повторяй до заполнения N наблюдений
  4. Обучи модель на bootstrap-выборке
  5. Оцени на OOB (out-of-bag) наблюдениях
```

#### 2.7.2 Moving Block Bootstrap

```
Параметры:
  L = длина блока

Алгоритм:
  1. Раздели данные на перекрывающиеся блоки длины L
  2. Случайно выбери ⌈N/L⌉ блоков с возвращением
  3. Склей блоки в bootstrap-выборку
  4. Обучи модель, оцени на OOB
```

#### Математическое обоснование

Стационарный bootstrap воспроизводит **автокорреляцию** временного ряда:

$$\hat{f}^*(x) = \frac{1}{N} \sum_{i=1}^{N} \sum_{t=1}^{T} I(X_t^* \in B_i) \cdot w_t$$

где $X_t^*$ — bootstrap-выборка, $B_i$ — i-й блок, $w_t$ — вес.

#### Edge Cases
- **p → 0** (expected_block_length → ∞) → каждый блок = весь ряд, нет randomization
- **p → 1** (expected_block_length → 1) → IID bootstrap, не учитывает autocorrelation
- **L > N/2** → слишком мало блоков, плохая аппроксимация
- **OOB наблюдений мало** → ненадёжная оценка

---

### 2.8 Monte Carlo Cross-Validation (MCCV)

#### Формула

```
Параметры:
  n_iterations = 1000  (количество итераций)
  test_size = 0.2      (доля тестовой выборки)

Для каждой итерации i:
  1. Случайно выбери test_indices = random.sample(N, ⌊N·test_size⌋)
  2. Train = все наблюдения MINUS test_indices
  3. Обучи модель на Train, оцени на Test
  4. Сохрани метрику M_i

Оценка: mean(M_1, ..., M_n_iterations)
Дисперсия: var(M_1, ..., M_n_iterations)
```

#### Crypto-specific адаптация
Для временных рядов вместо случайного выбора:
```
  1. Случайно выбери начальную точку t₀ ∈ [0, N - test_size·N]
  2. Test = [t₀, t₀ + ⌊N·test_size⌋)
  3. Train = [0, t₀)  (с purge и embargo)
```

---

### 2.9 Leave-One-Out (LOO)

#### Формула

$$\hat{\theta}_{(-i)} = \arg\min_\theta \sum_{j \neq i} L(y_j, f(x_j; \theta))$$

Для каждого i = 1, ..., N:
- Train = все наблюдения кроме i-го
- Test = i-е наблюдение
- Обучи модель, получи $\hat{\theta}_{(-i)}$
- Оцени на i-м наблюдении

#### Jackknife Influence Function (JIF)

$$\text{JIF}_i = N \cdot \hat{\theta} - (N-1) \cdot \hat{\theta}_{(-i)}$$

#### Edge Cases
- **N > 10000** → вычислительно нереально (N обучений)
- **Высокий variance** → оценка на одном наблюдении шумная
- **Serial correlation** → i-е наблюдение коррелировано с соседними в train

#### Применение
- Только для **очень малых** выборок (< 100)
- Оценка **влияния** отдельных наблюдений (JIF)
- Диагностика **выбросов**

---

### 2.10 Jackknife (Delete-d)

#### Формула

$$\hat{\theta}_{J} = \frac{1}{C(N,d)} \sum_{S \subset [N], |S|=d} \hat{\theta}_{(-S)}$$

где C(N,d) = C(N,d) — количество подмножеств размера d.

#### Псевдовалиансы

$$\hat{\theta}_{J}^* = N \cdot \hat{\theta} - (N-d) \cdot \frac{1}{C(N,d)} \sum_{S} \hat{\theta}_{(-S)}$$

#### Edge Cases
- **d = N** → невозможно
- **d = 1** → стандартный Jackknife
- **d = N/2** → максимальный bias reduction, но высокий variance

---

## 3. Anti-patterns

### 3.1 Look-Ahead Bias

#### Определение
Использование информации из будущего при обучении модели или принятии торговых решений.

#### Проявления в крипто
1. **Использование закрытия текущего бара** для сигнала на этом же баре
2. **Label = sign(r_{t+1})** — метка зависит от будущего
3. **Feature normalization** на всём датасете (train + test)
4. **Target leakage** — feature содержит информацию о таргете

#### Защита
```rust
// Правильно: feature на момент t, label = результат на t+H
fn create_labels(prices: &[f64], holding_period: usize) -> Vec<f64> {
    prices.windows(holding_period + 1)
        .map(|w| (w[holding_period] - w[0]) / w[0])
        .collect()
}

// Неправильно: использование будущих данных
fn create_labels_wrong(prices: &[f64]) -> Vec<f64> {
    prices.windows(2)
        .map(|w| (w[1] - w[0]) / w[0])  // w[1] = будущая цена!
        .collect()
}
```

#### Feature normalization — правильный подход
```rust
// Train statistics only
let train_mean = train_data.iter().sum::<f64>() / train_data.len() as f64;
let train_std = (train_data.iter()
    .map(|x| (x - train_mean).powi(2))
    .sum::<f64>() / train_data.len() as f64).sqrt();

// Normalize ВСЕ данные train statistics
let normalized_test: Vec<f64> = test_data.iter()
    .map(|x| (x - train_mean) / train_std)
    .collect();
```

---

### 3.2 Data Snooping (Data Dredging)

#### Определение
Повторное использование одних и тех же данных для тестирования множества гипотез без коррекции.

#### Пример
```
Тест 1: RSI < 30 → покупка. p-value = 0.03 ✓
Тест 2: MACD crossover → покупка. p-value = 0.08 ✗
Тест 3: Bollinger Squeeze → покупка. p-value = 0.04 ✓
...
(100 тестов) → ~5 ложных срабатываний при α = 0.05
```

#### Защита: Multiple Testing Correction

##### Bonferroni Correction

$$\alpha_{adj} = \frac{\alpha}{m}$$

где m = количество тестов, α = исходный уровень значимости.

**Пример**: α = 0.05, m = 20 → α_adj = 0.0025

##### Holm-Bonferroni Correction

```
1. Упорядочи p-values: p_(1) ≤ p_(2) ≤ ... ≤ p_(m)
2. Для i-го теста:
   α_i = α / (m - i + 1)
3. Если p_(i) > α_i → отвергни все H_j для j ≥ i
```

**Пример** (α = 0.05, m = 4):
```
p-values: [0.01, 0.02, 0.03, 0.04]
i=1: α_1 = 0.05/4 = 0.0125 → 0.01 < 0.0125 ✓
i=2: α_2 = 0.05/3 = 0.0167 → 0.02 > 0.0167 ✗ (остановка)
→ Только 1-й тест значим
```

##### Benjamini-Hochberg (FDR)

```
1. Упорядочи p-values: p_(1) ≤ p_(2) ≤ ... ≤ p_(m)
2. Для i-го теста:
   α_i = (i/m) · α
3. Найди наибольшее k: p_(k) ≤ α_k
4. Отвергни H_1, ..., H_k
```

##### Sidák Correction

$$\alpha_{adj} = 1 - (1 - \alpha)^{1/m}$$

При больших m: $\alpha_{adj} \approx \alpha / m$ (≈ Bonferroni)

---

### 3.3 Selection Bias under Multiple Testing

#### 3.3.1 SPA Test (Superior Predictive Ability)

Тест Хансена (2005) для проверки, что лучшая модель **статистически** лучше базовой.

#### Формула

$$\text{SPA} = \max_{k=1,...,m} \frac{\bar{d}_k}{\hat{\sigma}_k}$$

где:
- $\bar{d}_k = \frac{1}{T} \sum_{t=1}^{T} (L_{k,t} - L_{0,t})$ — средняя разница потерь модели k и базовой
- $\hat{\sigma}_k$ — стандартная ошибка $\bar{d}_k$

**Bootstrap процедура**:
1. Генерируй B bootstrap-выборки
2. Для каждой bootstrap-выборки вычисли $\text{SPA}^*_b$
3. p-value = $\frac{1}{B} \sum_{b=1}^{B} I(\text{SPA}^*_b \geq \text{SPA})$

#### 3.3.2 Reality Check (RC) of White (2000)

Более ранняя версия SPA. **Проблема**: чувствителен к плохим моделям в пуле (они "размывают" тест).

$$\text{RC} = \sqrt{T} \cdot \max_{k=1,...,m} \frac{\bar{d}_k}{\hat{\sigma}_k}$$

**Решение**: Используйте **Superior Predictive Ability (SPA)** вместо RC.

#### 3.3.3 Stepwise SPA

```
1. Оцени SPA для всех m моделей
2. Удали модель с наибольшим p-value
3. Повтори до тех пор, пока все оставшиеся модели значимы
```

---

### 3.4 Deflated Sharpe Ratio (DSR)

#### Формула

$$\text{DSR} = \frac{\hat{SR} - E[SR^*]}{\sqrt{\text{Var}(SR^*)}}$$

где:
- $\hat{SR}$ — наблюденный Sharpe Ratio
- $E[SR^*]$ — ожидаемый SR при случайном выборе
- $\text{Var}(SR^*)$ — дисперсия SR при множественном тестировании

#### Вычисление

$$E[SR^*] = \sqrt{\frac{2}{T}} \cdot \Psi^{-1}\left(1 - \frac{1}{m}\right)$$

где $\Psi^{-1}$ — обратная функция стандартного нормального распределения, T — количество наблюдений, m — количество протестированных стратегий.

$$\text{Var}(SR^*) = \frac{1}{T} \left(1 + (\gamma_3^2 + \frac{\gamma_4 - 3}{4}) \cdot SR^2\right)$$

где $\gamma_3$ — асимметрия, $\gamma_4$ — эксцесс доходностей.

#### Edge Cases
- **m = 1** → DSR = SR (нет deflation)
- **m → ∞** → E[SR*] → ∞, DSR → 0 (любой SR "не значим")
- **T < 30** → ненадёжная оценка variance
- **γ₄ < 3** (platykurtic) → уменьшает variance, DSR завышается

---

### 3.5 Probability of Backtest Overfitting (PBO)

#### Формула

$$\text{PBO} = P\left(\hat{\theta}_{test} < \hat{\theta}_{train}\right)$$

где $\hat{\theta}_{test}$ — производительность на тестовой выборке, $\hat{\theta}_{train}$ — на тренировочной.

#### Процедура (Bailey, Borwein, López de Prado, 2014)

```
1. Раздели данные на N фолдов с purging
2. Для каждого фолда i:
   a. Обучи модель на фолдах кроме i (train)
   b. Оцени на фолде i (test)
   c. Сохрани rank производительности на train и test
3. Вычисли logit:
   L = log(rank_test / rank_train)
4. PBO = доля случаев, когда L < 0
```

#### Альтернативная формула через Sharpe Ratio

$$\text{PBO} \approx \Phi\left(\frac{\mu_{train} - \mu_{test}}{\sigma_{test}}\right)$$

где $\mu_{train}$, $\mu_{test}$ — средние Sharpe Ratios, $\sigma_{test}$ — стандартное отклонение тестовых SR.

#### Интерпретация

| PBO | Интерпретация |
|-----|--------------|
| < 0.3 | Хорошая стратегия, низкий риск overfitting |
| 0.3–0.5 | Умеренный риск, требуется дополнительная проверка |
| 0.5–0.7 | Высокий риск, стратегия вероятно overfitted |
| > 0.7 | Критический overfitting, отклонить стратегию |

#### Edge Cases
- **Один фолд** → PBO = 0 или 1 (бессмысленно)
- **Все фолды дают одинаковый train rank** → undefined logit
- **rank_train = 0** → деление на ноль

---

## 4. Deflated Sharpe Ratio и PBO

### 4.1 Комплексная оценка

```
Pipeline оценки стратегии:

1. Walk-Forward валидация → получаем OOS Sharpe Ratios
2. DSR → корректируем SR на множественное тестирование
3. PBO → оцениваем вероятность overfitting
4. SPA test → проверяем статистическую значимость vs базовая

Стратегия проходит, если:
  - DSR > 0 (с учётом deflation)
  - PBO < 0.5
  - SPA p-value < 0.05
  - Все три условия одновременно
```

### 4.2 Комбинированная метрика

$$\text{Strategy\_Score} = w_1 \cdot \text{DSR} + w_2 \cdot (1 - \text{PBO}) + w_3 \cdot (1 - \text{SPA\_p})$$

Рекомендуемые веса: $w_1 = 0.5$, $w_2 = 0.3$, $w_3 = 0.2$

---

## 5. Crypto-specific адаптации

### 5.1 24/7 рынок — нет overnight gap

#### Проблема
На традиционных рынках embargo = 1 ночь (overnight gap). В крипто рынок работает 24/7, поэтому:

- **Embargo в барах**, а не в днях
- Embargo = 2 × holding_period (в барах)
- Нет "ночного" разрыва → зависимость между соседними барами **выше**

#### Решение
```rust
/// Вычисляет embargo в барах для 24/7 крипто рынка.
///
/// Поскольку крипто торгуется 24/7 без overnight gap,
/// embargo выражается в количестве баров, а не в торговых днях.
///
/// # Аргументы
/// * `holding_period` — период удержания позиции в барах
///
/// # Возвращаемое значение
/// Embargo в барах (округлённый вверх)
fn compute_crypto_embargo(holding_period: usize) -> usize {
    // 2x holding period для крипто из-за:
    // 1. Высокая autocorrelation (нет overnight gap для "reset")
    // 2. Ликвидность меняется непрерывно
    // 3. События (listing, delisting) могут влиять на несколько баров
    (holding_period as f64 * 2.0).ceil() as usize
}
```

### 5.2 Halving Events и Non-Stationarity

#### Проблема
Bitcoin halving каждые ~4 года создаёт **структурные breaks** в данных:

- 2012-11: 50 → 25 BTC
- 2016-07: 25 → 12.5 BTC
- 2020-05: 12.5 → 6.25 BTC
- 2024-04: 6.25 → 3.125 BTC

#### Влияние на валидацию
- Train на pre-halving данных → модель не знает post-halving regime
- Распределение доходностей **меняется** после halving
- Embargo должен учитывать halving как **структурный break**

#### Решение

```rust
/// Даты halving events (Unix timestamps)
const HALVING_EVENTS: &[i64] = &[
    1352937600,  // 2012-11-28
    1468713600,  // 2016-07-17
    1589241600,  // 2020-05-12
    1713484800,  // 2024-04-19
];

/// Проверяет, содержит ли фолд halving event
fn fold_contains_halving(
    fold_start: i64,
    fold_end: i64,
    embargo_days: i64,
) -> bool {
    let embargo_secs = embargo_days * 86400;
    HALVING_EVENTS.iter().any(|&h| {
        h >= fold_start - embargo_secs && h <= fold_end + embargo_secs
    })
}

/// Расширяет embargo вокруг halving events
fn expand_embargo_for_halvings(
    train_ranges: &[(i64, i64)],
    test_range: (i64, i64),
    base_embargo: i64,
) -> Vec<(i64, i64)> {
    let mut expanded = train_ranges.to_vec();
    for &halving in HALVING_EVENTS {
        if halving >= test_range.0 - base_embargo && halving <= test_range.1 + base_embargo {
            // Расширяем embargo вокруг halving до 30 дней
            let halving_embargo = 30 * 86400;
            expanded = expanded.iter()
                .filter(|&&(s, e)| {
                    !(halving - halving_embargo <= e && halving + halving_embargo >= s)
                })
                .copied()
                .collect();
        }
    }
    expanded
}
```

### 5.3 Ликвидность и Slippage в валидации

#### Проблема
Backtest без учёта slippage завышает производительность. Slippage в крипто **нестационарна**.

#### Решение
```rust
/// Расчёт slippage-aware Sharpe Ratio
fn sharpe_with_slippage(
    returns: &[f64],
    slippage_model: &SlippageModel,
) -> f64 {
    let net_returns: Vec<f64> = returns.iter()
        .map(|&r| r - slippage_model.estimate(r))
        .collect();
    let mean = net_returns.iter().sum::<f64>() / net_returns.len() as f64;
    let std = (net_returns.iter()
        .map(|&x| (x - mean).powi(2))
        .sum::<f64>() / net_returns.len() as f64).sqrt();
    if std == 0.0 { 0.0 } else { mean / std * (net_returns.len() as f64).sqrt() }
}
```

---

## 6. Параметры по умолчанию

### 6.1 Purged K-Fold

```rust
/// Параметры Purged K-Fold для крипто
pub struct PurgedKFoldParams {
    pub n_splits: usize,           // = 5
    pub embargo_multiplier: f64,   // = 2.0 (embargo = 2 * holding_period)
    pub purge_multiplier: f64,     // = 1.0 (purge = holding_period)
    pub min_train_size: usize,     // = 100 (минимум баров для обучения)
    pub min_test_size: usize,      // = 20 (минимум баров для теста)
}

impl Default for PurgedKFoldParams {
    fn default() -> Self {
        Self {
            n_splits: 5,
            embargo_multiplier: 2.0,
            purge_multiplier: 1.0,
            min_train_size: 100,
            min_test_size: 20,
        }
    }
}
```

### 6.2 Walk-Forward

```rust
/// Параметры Walk-Forward для крипто
pub struct WalkForwardParams {
    pub train_ratio: f64,          // = 0.8
    pub n_test_bars: usize,        // = 0 (auto: (1 - train_ratio) * N / n_folds)
    pub min_train_bars: usize,     // = 100
    pub expanding: bool,           // = true (expanding window)
    pub embargo_bars: usize,       // = 0 (auto: 2 * holding_period)
}

impl Default for WalkForwardParams {
    fn default() -> Self {
        Self {
            train_ratio: 0.8,
            n_test_bars: 0,
            min_train_bars: 100,
            expanding: true,
            embargo_bars: 0,
        }
    }
}
```

### 6.3 Combinatorial Purged CV

```rust
/// Параметры Combinatorial Purged CV
pub struct CombinatorialPurgedCVParams {
    pub n_splits: usize,           // = 5
    pub test_groups: usize,        // = 1 (количество фолдов в тестовой выборке)
    pub max_combinations: usize,   // = 100 (максимум комбинаций для оценки)
    pub embargo_multiplier: f64,   // = 2.0
}

impl Default for CombinatorialPurgedCVParams {
    fn default() -> Self {
        Self {
            n_splits: 5,
            test_groups: 1,
            max_combinations: 100,
            embargo_multiplier: 2.0,
        }
    }
}
```

---

## 7. Rust-реализации

### 7.1 Purged K-Fold Cross-Validation

```rust
use std::ops::Range;

/// Purged K-Fold Cross-Validation для временных рядов.
///
/// Реализует K-Fold с purge и embargo для предотвращения
/// look-ahead bias и data leakage в финансовых данных.
pub struct PurgedKFoldCV {
    n_splits: usize,
    embargo: usize,
    purge: usize,
}

/// Диапазон наблюдений (полуоткрытый интервал)
type ObservationRange = Range<usize>;

/// Результат одного фолда кросс-валидации
#[derive(Debug, Clone)]
pub struct CVFold {
    pub train_indices: Vec<usize>,
    pub test_indices: Vec<usize>,
    pub fold_id: usize,
}

impl PurgedKFoldCV {
    /// Создаёт новый Purged K-Fold валидатор.
    ///
    /// # Аргументы
    /// * `n_splits` — количество фолдов (≥ 2)
    /// * `embargo` — количество баров embargo после тестового окна
    /// * `purge` — количество баров purge перед тестовым окном
    ///
    /// # Паника
    /// Паникует при n_splits < 2
    pub fn new(n_splits: usize, embargo: usize, purge: usize) -> Self {
        assert!(n_splits >= 2, "n_splits must be >= 2");
        Self { n_splits, embargo, purge }
    }

    /// Генерирует фолды для N наблюдений.
    ///
    /// # Аргументы
    /// * `n_samples` — общее количество наблюдений
    ///
    /// # Возвращаемое значение
    /// Вектор CVFold с train и test индексами
    pub fn split(&self, n_samples: usize) -> Vec<CVFold> {
        let fold_size = n_samples / self.n_splits;
        let mut folds = Vec::with_capacity(self.n_splits);

        for i in 0..self.n_splits {
            let test_start = i * fold_size;
            let test_end = if i == self.n_splits - 1 {
                n_samples
            } else {
                (i + 1) * fold_size
            };

            // Test indices
            let test_indices: Vec<usize> = (test_start..test_end).collect();

            // Train indices с purge и embargo
            let train_indices: Vec<usize> = (0..n_samples)
                .filter(|&idx| {
                    // Исключи test fold
                    if idx >= test_start && idx < test_end {
                        return false;
                    }
                    // Purge: удали наблюдения до test_start
                    if idx >= test_start.saturating_sub(self.purge) && idx < test_start {
                        return false;
                    }
                    // Embargo: удали наблюдения после test_end
                    if idx >= test_end && idx < test_end + self.embargo {
                        return false;
                    }
                    true
                })
                .collect();

            // Проверка минимального размера
            if train_indices.len() >= 2 && test_indices.len() >= 1 {
                folds.push(CVFold {
                    train_indices,
                    test_indices,
                    fold_id: i,
                });
            }
        }
        folds
    }
}
```

### 7.2 Walk-Forward Validation

```rust
/// Walk-Forward валидация с expanding/sliding окном.
pub struct WalkForwardCV {
    train_ratio: f64,
    n_test_bars: usize,
    expanding: bool,
    embargo_bars: usize,
}

/// Результат Walk-Forward итерации
#[derive(Debug, Clone)]
pub struct WFFold {
    pub train_range: ObservationRange,
    pub test_range: ObservationRange,
    pub fold_id: usize,
}

impl WalkForwardCV {
    /// Создаёт новый Walk-Forward валидатор.
    ///
    /// # Аргументы
    /// * `train_ratio` — доля данных для начального обучения (0.0, 1.0)
    /// * `n_test_bars` — количество баров в тестовом окне (0 = auto)
    /// * `expanding` — true = expanding window, false = sliding
    /// * `embargo_bars` — embargo в барах (0 = auto)
    pub fn new(
        train_ratio: f64,
        n_test_bars: usize,
        expanding: bool,
        embargo_bars: usize,
    ) -> Self {
        assert!(train_ratio > 0.0 && train_ratio < 1.0);
        Self { train_ratio, n_test_bars, expanding, embargo_bars }
    }

    /// Генерирует фолды Walk-Forward.
    pub fn split(&self, n_samples: usize) -> Vec<WFFold> {
        let initial_train_size = (n_samples as f64 * self.train_ratio) as usize;
        let test_size = if self.n_test_bars > 0 {
            self.n_test_bars
        } else {
            // Auto: ~5 фолдов
            ((n_samples - initial_train_size) / 5).max(1)
        };

        let mut folds = Vec::new();
        let mut fold_id = 0;
        let mut current_pos = initial_train_size;

        while current_pos + test_size <= n_samples {
            let train_start = if self.expanding {
                0 // Expanding: всё до текущей позиции
            } else {
                // Sliding: окно фиксированного размера
                current_pos.saturating_sub(initial_train_size)
            };

            let train_end = current_pos;
            let test_start = current_pos;
            let test_end = (current_pos + test_size).min(n_samples);

            // Применяем embargo к train
            let embargo = if self.embargo_bars > 0 {
                self.embargo_bars
            } else {
                // Auto: 2 * holding_period (оценка ~5 баров)
                10
            };

            let effective_train_end = train_end.saturating_sub(embargo);

            if effective_train_end > train_start {
                folds.push(WFFold {
                    train_range: train_start..effective_train_end,
                    test_range: test_start..test_end,
                    fold_id,
                });
            }

            current_pos += test_size;
            fold_id += 1;
        }
        folds
    }
}
```

### 7.3 Combinatorial Purged CV

```rust
/// Combinatorial Purged Cross-Validation.
///
/// Генерирует все C(n_splits, test_groups) комбинаций
/// для оценки стабильности стратегии.
pub struct CombinatorialPurgedCV {
    n_splits: usize,
    test_groups: usize,
    embargo: usize,
    max_combinations: usize,
}

impl CombinatorialPurgedCV {
    pub fn new(
        n_splits: usize,
        test_groups: usize,
        embargo: usize,
        max_combinations: usize,
    ) -> Self {
        assert!(test_groups < n_splits);
        Self { n_splits, test_groups, embargo, max_combinations }
    }

    /// Вычисляет биномиальный коэффициент C(n, k).
    fn binomial(n: usize, k: usize) -> usize {
        if k > n { return 0; }
        if k == 0 || k == n { return 1; }
        let k = k.min(n - k);
        let mut result = 1usize;
        for i in 0..k {
            result = result * (n - i) / (i + 1);
        }
        result
    }

    /// Генерирует все комбинации C(n_splits, test_groups) индексов.
    fn combinations(&self) -> Vec<Vec<usize>> {
        let n = self.n_splits;
        let k = self.test_groups;
        let total = Self::binomial(n, k);

        if total > self.max_combinations {
            // Сэмплируем случайные комбинации
            return self.sample_combinations(n, k, self.max_combinations);
        }

        let mut result = Vec::with_capacity(total);
        let mut current = (0..k).collect::<Vec<_>>();
        loop {
            result.push(current.clone());
            // Генерируем следующую комбинацию
            let mut i = k;
            while i > 0 {
                i -= 1;
                if current[i] < n - k + i {
                    current[i] += 1;
                    for j in i + 1..k {
                        current[j] = current[j - 1] + 1;
                    }
                    break;
                }
            }
            if i == 0 { break; }
        }
        result
    }

    /// Сэмплирует случайные комбинации.
    fn sample_combinations(
        &self,
        n: usize,
        k: usize,
        max: usize,
    ) -> Vec<Vec<usize>> {
        use std::collections::HashSet;
        let mut result = Vec::with_capacity(max);
        let mut seen = HashSet::new();
        // Простая детерминированная генерация для reproducibility
        for start in 0..n {
            let mut combo = Vec::with_capacity(k);
            let mut pos = start;
            for _ in 0..k {
                combo.push(pos % n);
                pos += n / k + 1;
            }
            combo.sort();
            combo.dedup();
            if combo.len() == k && seen.insert(combo.clone()) {
                result.push(combo);
                if result.len() >= max { break; }
            }
        }
        result
    }

    /// Генерирует фолды для N наблюдений.
    pub fn split(&self, n_samples: usize) -> Vec<Vec<CVFold>> {
        let fold_size = n_samples / self.n_splits;
        let combinations = self.combinations();

        combinations.into_iter().map(|test_fold_indices| {
            let test_indices: Vec<usize> = test_fold_indices.iter()
                .flat_map(|&fold_idx| {
                    let start = fold_idx * fold_size;
                    let end = if fold_idx == self.n_splits - 1 {
                        n_samples
                    } else {
                        (fold_idx + 1) * fold_size
                    };
                    start..end
                })
                .collect();

            // Train = все кроме test + purge + embargo
            let train_indices: Vec<usize> = (0..n_samples)
                .filter(|&idx| {
                    if test_indices.contains(&idx) {
                        return false;
                    }
                    // Проверяем embargo вокруг каждого test фолда
                    for &fold_idx in &test_fold_indices {
                        let test_end = if fold_idx == self.n_splits - 1 {
                            n_samples
                        } else {
                            (fold_idx + 1) * fold_size
                        };
                        if idx >= test_end && idx < test_end + self.embargo {
                            return false;
                        }
                    }
                    true
                })
                .collect();

            vec![CVFold {
                train_indices,
                test_indices,
                fold_id: 0,
            }]
        }).collect()
    }
}
```

### 7.4 Deflated Sharpe Ratio

```rust
/// Вычисляет Deflated Sharpe Ratio.
///
/// DSR корректирует наблюденный Sharpe Ratio на множественное
/// тестирование и распределение доходностей.
pub struct DeflatedSharpeRatio;

impl DeflatedSharpeRatio {
    /// Вычисляет DSR.
    ///
    /// # Аргументы
    /// * `observed_sr` — наблюденный Sharpe Ratio
    /// * `n_observations` — количество наблюдений (T)
    /// * `n_strategies` — количество протестированных стратегий (m)
    /// * `skewness` — асимметрия доходностей (γ₃)
    /// * `kurtosis` — эксцесс доходностей (γ₄)
    ///
    /// # Возвращаемое значение
    /// DSR как f64. Значение > 0 означает значимый SR после коррекции.
    pub fn compute(
        observed_sr: f64,
        n_observations: usize,
        n_strategies: usize,
        skewness: f64,
        kurtosis: f64,
    ) -> f64 {
        let t = n_observations as f64;
        let m = n_strategies.max(1) as f64;

        // E[SR*]: ожидаемый SR при случайном выборе
        // Используем приближение через нормальное распределение
        let expected_sr = if m > 1.0 {
            // Ψ⁻¹(1 - 1/m) через inverse normal CDF приближение
            let p = 1.0 - 1.0 / m;
            Self::inverse_normal_cdf(p) * (2.0 / t).sqrt()
        } else {
            0.0
        };

        // Var(SR*): дисперсия SR при множественном тестировании
        let variance_sr = (1.0 / t) * (
            1.0 + (skewness.powi(2) + (kurtosis - 3.0) / 4.0) * observed_sr.powi(2)
        );

        let std_sr = variance_sr.sqrt();

        if std_sr == 0.0 {
            return 0.0;
        }

        // DSR = (SR - E[SR*]) / sqrt(Var[SR*])
        (observed_sr - expected_sr) / std_sr
    }

    /// Приближение обратной функции нормального распределения.
    ///
    /// Использует алгоритм Abramowitz & Stegun 26.2.23.
    fn inverse_normal_cdf(p: f64) -> f64 {
        if p <= 0.0 { return f64::NEG_INFINITY; }
        if p >= 1.0 { return f64::INFINITY; }
        if p == 0.5 { return 0.0; }

        let sign = if p < 0.5 { -1.0 } else { 1.0 };
        let p = if p < 0.5 { p } else { 1.0 - p };

        let t = (-2.0 * p.ln()).sqrt();
        let c0 = 2.515517;
        let c1 = 0.802853;
        let c2 = 0.010328;
        let d1 = 1.432788;
        let d2 = 0.189269;
        let d3 = 0.001308;

        sign * (t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t))
    }
}
```

### 7.5 Probability of Backtest Overfitting (PBO)

```rust
/// Вычисляет Probability of Backtest Overfitting (PBO).
pub struct PBOCalculator;

impl PBOCalculator {
    /// Вычисляет PBO через rank-based метод.
    ///
    /// # Аргументы
    /// * `train_scores` — производительность на train для каждого фолда
    /// * `test_scores` — производительность на test для каждого фолда
    ///
    /// # Возвращаемое значение
    /// PBO в диапазоне [0.0, 1.0]. Значение > 0.5 указывает на overfitting.
    pub fn compute(
        train_scores: &[f64],
        test_scores: &[f64],
    ) -> f64 {
        assert_eq!(train_scores.len(), test_scores.len());
        let n = train_scores.len();

        if n < 2 {
            return 0.5; // Недостаточно данных
        }

        // Вычисляем ranks
        let train_ranks = Self::compute_ranks(train_scores);
        let test_ranks = Self::compute_ranks(test_scores);

        // Считаем logit и долю случаев, когда train_rank > test_rank
        let mut overfitting_count = 0;
        let mut total_comparisons = 0;

        for i in 0..n {
            for j in (i + 1)..n {
                total_comparisons += 1;
                // Если на train модель i лучше j, но на test хуже
                if train_ranks[i] < train_ranks[j] && test_ranks[i] > test_ranks[j] {
                    overfitting_count += 1;
                }
                if train_ranks[j] < train_ranks[i] && test_ranks[j] > test_ranks[i] {
                    overfitting_count += 1;
                }
            }
        }

        if total_comparisons == 0 {
            return 0.5;
        }

        overfitting_count as f64 / total_comparisons as f64
    }

    /// Вычисляет ранги (1-indexed, средний ранг при ties).
    fn compute_ranks(scores: &[f64]) -> Vec<f64> {
        let n = scores.len();
        let mut indexed: Vec<(f64, usize)> = scores.iter()
            .enumerate()
            .map(|(i, &s)| (s, i))
            .collect();

        // Сортируем по убыванию (лучший score = ранг 1)
        indexed.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());

        let mut ranks = vec![0.0; n];
        let mut i = 0;
        while i < n {
            let mut j = i;
            // Находим ties
            while j < n && indexed[j].0 == indexed[i].0 {
                j += 1;
            }
            // Средний ранг для ties
            let avg_rank = (i + j + 1) as f64 / 2.0;
            for k in i..j {
                ranks[indexed[k].1] = avg_rank;
            }
            i = j;
        }
        ranks
    }
}
```

### 7.6 SPA Test (Superior Predictive Ability)

```rust
/// Superior Predictive Ability тест (Hansen, 2005).
pub struct SPATest {
    n_bootstrap: usize,
}

impl SPATest {
    pub fn new(n_bootstrap: usize) -> Self {
        Self { n_bootstrap }
    }

    /// Вычисляет SPA статистику.
    ///
    /// # Аргументы
    /// * `loss_differences` — матрица [T × m] разниц потерь модели k и базовой
    ///
    /// # Возвращаемое значение
    /// p-value SPA теста
    pub fn test(&self, loss_differences: &[Vec<f64>]) -> f64 {
        let t = loss_differences.len();
        let m = loss_differences[0].len();

        // Средние разницы потерь
        let mean_diffs: Vec<f64> = (0..m).map(|k| {
            loss_differences.iter().map(|row| row[k]).sum::<f64>() / t as f64
        }).collect();

        // Стандартные ошибки
        let std_errors: Vec<f64> = (0..m).map(|k| {
            let mean = mean_diffs[k];
            let var = loss_differences.iter()
                .map(|row| (row[k] - mean).powi(2))
                .sum::<f64>() / t as f64;
            var.sqrt()
        }).collect();

        // SPA статистика
        let spa_stat = (0..m)
            .map(|k| {
                if std_errors[k] == 0.0 { 0.0 }
                else { mean_diffs[k] / std_errors[k] }
            })
            .fold(f64::NEG_INFINITY, f64::max);

        // Bootstrap p-value
        let mut exceed_count = 0;
        for _ in 0..self.n_bootstrap {
            // Генерируем bootstrap-выборку (stationary bootstrap)
            let p_reset = 0.1; // expected block length = 10
            let mut bootstrap_diffs = Vec::with_capacity(t);
            let mut pos = rand_idx(t);
            for _ in 0..t {
                if rand_f64() < p_reset {
                    pos = rand_idx(t);
                }
                bootstrap_diffs.push(loss_differences[pos].clone());
                pos = (pos + 1) % t;
            }

            // Центрируем
            let boot_means: Vec<f64> = (0..m).map(|k| {
                bootstrap_diffs.iter().map(|row| row[k]).sum::<f64>() / t as f64
            }).collect();

            let centered: Vec<Vec<f64>> = bootstrap_diffs.iter().map(|row| {
                row.iter().enumerate().map(|(k, &v)| v - boot_means[k]).collect()
            }).collect();

            // SPA для bootstrap-выборки
            let boot_mean_diffs: Vec<f64> = (0..m).map(|k| {
                centered.iter().map(|row| row[k]).sum::<f64>() / t as f64
            }).collect();

            let boot_std_errors: Vec<f64> = (0..m).map(|k| {
                let mean = boot_mean_diffs[k];
                let var = centered.iter()
                    .map(|row| (row[k] - mean).powi(2))
                    .sum::<f64>() / t as f64;
                var.sqrt()
            }).collect();

            let boot_spa = (0..m)
                .map(|k| {
                    if boot_std_errors[k] == 0.0 { 0.0 }
                    else { boot_mean_diffs[k] / boot_std_errors[k] }
                })
                .fold(f64::NEG_INFINITY, f64::max);

            if boot_spa >= spa_stat {
                exceed_count += 1;
            }
        }

        exceed_count as f64 / self.n_bootstrap as f64
    }
}

// Вспомогательные функции (заглушки для примера)
fn rand_idx(n: usize) -> usize {
    // В реальной реализации использовать rand crate
    0
}
fn rand_f64() -> f64 {
    0.5
}
```

---

## Сводная таблица методов

| Метод | Look-ahead bias | Serial correlation | Non-stationarity | Crypto-adapted | Вычислительная сложность |
|-------|:-:|:-:|:-:|:-:|---|
| Time Series Split | ❌ | ❌ | ❌ | ❌ | O(N) |
| Walk-Forward | ✅ | ⚠️ | ⚠️ | ✅ | O(K·N) |
| Purged K-Fold | ✅ | ✅ | ❌ | ✅ | O(K·N) |
| Combinatorial Purged CV | ✅ | ✅ | ❌ | ✅ | O(C(n,k)·N) |
| Nested CV | ✅ | ❌ | ❌ | ❌ | O(K²·N) |
| Blocked TS Split | ✅ | ⚠️ | ❌ | ❌ | O(K·N) |
| Stationary Bootstrap | ✅ | ✅ | ❌ | ⚠️ | O(B·N) |
| Moving Block Bootstrap | ✅ | ✅ | ❌ | ⚠️ | O(B·N) |
| Monte Carlo CV | ⚠️ | ❌ | ❌ | ⚠️ | O(I·N) |
| LOO | ❌ | ❌ | ❌ | ❌ | O(N²) |
| Jackknife | ❌ | ❌ | ❌ | ❌ | O(N²) |

✅ = решает проблему, ⚠️ = частично, ❌ = не решает

---

## Рекомендации по выбору

### Primary: Walk-Forward + Purged K-Fold
- **Walk-Forward** для оценки OOS производительности
- **Purged K-Fold** для оценки стабильности
- Embargo = 2 × holding_period (для крипто 24/7)

### Secondary: Combinatorial Purged CV
- Для глубокой оценки стабильности
- test_groups = 1, max_combinations = 100

### Anti-pattern защита
- **Bonferroni/Holm** для множественного тестирования
- **DSR** для коррекции Sharpe Ratio
- **PBO** для оценки overfitting probability
- **SPA test** для проверки superiority vs базовой

### Crypto-specific
- Embargo в барах, не в днях
- Halving-aware embargo (расширение до 30 дней)
- Slippage-aware метрики
- 24/7 market considerations

---

*Документ создан агентом 27 (Cross-Validation & Overfitting) для проекта «Криптовалютный торговый бот».*
*Версия: 1.0 | Дата: 2026-04-17*
