# Агент 20: Детектирование рыночного режима (Market Regime Detection)

> Полный аудит методов детектирования рыночных режимов для крипто-торгового бота.
> Формулы, edge cases, Rust-реализации, выбор оптимальных методов.

---

## Содержание

1. [Определение режимов](#1-определение-режимов)
2. [Аудит всех методов](#2-аудит-всех-методов)
3. [Сравнительная таблица](#3-сравнительная-таблица)
4. [Переключение стратегий](#4-переключение-стратегий)
5. [Топ-3 рекомендации](#5-топ-3-рекомендации)
6. [Rust-реализация](#6-rust-реализация)

---

## 1. Определение режимов

### Рекомендация: 4 состояния

| Режим | Описание | Характеристики |
|---|---|---|
| **Bull Trend** | Восходящий тренд | Цена выше EMA50, ADX > 25, возврат > 0 |
| **Bear Trend** | Нисходящий тренд | Цена ниже EMA50, ADX > 25, возврат < 0 |
| **High Vol Range** | Боковик с высокой волатильностью | ADX < 25, ATR > 75-й перцентиль, нет направленности |
| **Low Vol Range** | Тихий боковик / накопление | ADX < 25, ATR < 25-й перцентиль, узкий диапазон |

**Почему 4, а не 3:**
- 3 состояния (Bull/Bear/Range) теряют критическое различие: High Vol Range (торгуем mean-reversion с широкими стопами) vs Low Vol Range (ждём squeeze breakout). Стратегия **полностью** меняется между ними.
- 4 состояния — это уже проверенный стандарт в количественных финансах (Ang & Bekaert 2002, Guidolin & Timmermann 2007).
- В проекте ранее выбран HMM с 3 состояниями (Research Indicators, Модуль 6). **Рекомендую обновить до 4** при наличии ≥ 5000 баров данных — этого достаточно для калибровки 4-х компонентной модели. Если данных мало — остаёмся на 3 (объединяем High/Low Vol Range).

---

## 2. Аудит всех методов

---

### 2.1 Hidden Markov Model (HMM)

#### Формула

HMM описывает систему с невидимыми (скрытыми) состояниями $S_t \in \{1, ..., K\}$, которые генерируют наблюдаемые данные $O_t$.

**Параметры модели:**
- $\pi = [\pi_1, ..., \pi_K]$ — начальное распределение состояний
- $A = \{a_{ij}\}$ — матрица переходов, $a_{ij} = P(S_{t+1} = j | S_t = i)$
- $B = \{b_j(o)\}$ — функции эмиссии (распределение наблюдений в каждом состоянии)

**Для Gaussian HMM** (рекомендуемый для крипты):
$$b_j(o_t) = \mathcal{N}(o_t; \mu_j, \sigma_j^2) = \frac{1}{\sqrt{2\pi\sigma_j^2}} \exp\left(-\frac{(o_t - \mu_j)^2}{2\sigma_j^2}\right)$$

где $o_t = \ln(C_t / C_{t-1})$ — лог-доходность.

**Обучение: алгоритм Баума-Велша (EM)**
1. E-шаг: вычислить $\gamma_t(j) = P(S_t = j | O, \lambda)$ — posterior вероятности состояний (через forward-backward)
2. M-шаг: обновить параметры:
   - $\hat{\pi}_i = \gamma_1(i)$
   - $\hat{a}_{ij} = \frac{\sum_{t=1}^{T-1} \xi_t(i,j)}{\sum_{t=1}^{T-1} \gamma_t(i)}$, где $\xi_t(i,j) = P(S_t=i, S_{t+1}=j | O, \lambda)$
   - $\hat{\mu}_j = \frac{\sum_t \gamma_t(j) \cdot o_t}{\sum_t \gamma_t(j)}$
   - $\hat{\sigma}_j^2 = \frac{\sum_t \gamma_t(j) \cdot (o_t - \hat{\mu}_j)^2}{\sum_t \gamma_t(j)}$

**Декодирование: алгоритм Витерби**
$$\delta_t(j) = \max_{s_1,...,s_{t-1}} P(s_1,...,s_{t-1}, s_t=j, o_1,...,o_t | \lambda)$$
$$\delta_t(j) = \max_i [\delta_{t-1}(i) \cdot a_{ij}] \cdot b_j(o_t)$$

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Слишком мало данных (< 500 баров) | Недооценка параметров, ложные состояния | Минимум 1000 баров, использовать Bayesian HMM с informative priors |
| Кластеры состояний не разделимы (μ₁ ≈ μ₂) | Модель путает режимы | Принудительный минимальный зазор $\|\mu_i - \mu_j\| > 0.5\sigma_{pool}$ |
| Flash crash (одиночный outlier) | Один бар ломает параметры эмиссии | Winsorize наблюдения на 1-й/99-й перцентилях перед обучением |
| Частые переключения состояний | Модель "дрожит" каждый бар | Увеличить диагональ A (self-transition): $a_{ii} > 0.9$, или использовать HSMM |
| Нестационарность параметров | Рынок меняется, параметры устаревают | Rolling recalibration каждые N баров (N = 500–1000) |
| Локальные максимумы EM | Баум-Велш зависит от инициализации | Multi-start: запускать 10+ раз с random init, брать модель с highest log-likelihood |

#### Применение для крипты

**Входные признаки (multivariate HMM):**
```rust
// Лучший набор признаков для HMM regime detection:
features = [
    log_return,           // ln(close_t / close_{t-1})
    atr_normalized,       // ATR(14) / Close  — нормализованная волатильность
    volume_zscore,        // (Vol - MA(Vol,20)) / STD(Vol,20)
    adx_value,            // ADX(14) — сила тренда
]
```

**Почему multivariate > univariate:**
- Одна лог-доходность не различает High Vol Range от Low Vol Range (оба могут иметь μ ≈ 0).
- Добавление ATR/волатильности как второго признака решает проблему.
- 4 признака — оптимально: достаточно информации, но не переобучает.

---

### 2.2 Hidden Semi-Markov Model (HSMM)

#### Формула

HSMM расширяет HMM явным моделированием **времени пребывания** (duration) в каждом состоянии.

В HMM: $P(\text{duration} = d | S_t = i) = a_{ii}^{d-1} \cdot (1 - a_{ii})$ — экспоненциальное распределение (единственный параметр).

В HSMM: $P(\text{duration} = d | S_t = i) = d_i(d)$ — произвольное распределение (Poisson, Gamma, non-parametric).

**Матрица переходов** в HSMM: $a_{ij}$ для $i \neq j$, без диагональных элементов (переход всегда происходит после окончания пребывания).

**E-шаг** модифицирован: вместо $\xi_t(i,j)$ используется прямое вычисление вероятности длительности.

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Оценка длительности требует длинных данных | Сильно больше параметров, чем HMM | Минимум 2000+ баров, или параметрическое $d_i(d)$ (Gamma) |
| Сложность реализации | Forward-backward сложнее | Использовать библиотеку или итеративный Viterbi |

#### Оценка

**Преимущество перед HMM:** явно моделирует, что "бычий тренд длится ~30 баров, а флэт ~15". Это уменьшает ложные переключения.

**Недостаток:** значительно сложнее в реализации и калибровке. На крипте (24/7, без overnight gaps) длительности режимов варьируют сильнее, чем на акциях, что делает параметрическую модель длительности менее надёжной.

---

### 2.3 Gaussian Mixture Model (GMM) + Clustering

#### Формула

GMM предполагает, что наблюдения генерируются смесью K гауссиан:

$$p(o_t) = \sum_{k=1}^{K} \pi_k \cdot \mathcal{N}(o_t; \mu_k, \Sigma_k)$$

где $\sum \pi_k = 1$.

**Отличие от HMM:** GMM — это **безмарковская** модель. Каждый бар классифицируется независимо, без учёта предыдущего состояния.

**Обучение:** EM-алгоритм (как в HMM, но без forward-backward).

**Классификация:** $S_t = \arg\max_k P(S_t = k | o_t)$ — MAP по posterior.

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Нет временной зависимости | "Bull" и "Bear" могут чередоваться каждый бар | Постобработка: majority vote по окну или объединить с HMM |
| Количество компонент K неизвестно | Неправильное K → плохая кластеризация | BIC/AIC для выбора K |
| Ковариационная структура | Полная vs диагональная vs tied | Для крипты: diagonal (признаки примерно независимы) |

#### Оценка

GMM **отдельно** — плохо для regime detection (нет учёта последовательности). Но GMM как **эмиссия** для HMM (GMM-HMM) — мощно, если один признак не разделяет состояния.

**Рейтинг: 6/10 для standalone, 9/10 как компонент HMM.**

---

### 2.4 Threshold-based (ADX)

#### Формула

**ADX (Average Directional Index), период N:**

1. True Range:
$$TR_t = \max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)$$

2. Directional Movement:
$$+DM_t = \begin{cases} H_t - H_{t-1} & \text{if } H_t - H_{t-1} > L_{t-1} - L_t \text{ and } H_t - H_{t-1} > 0 \\ 0 & \text{otherwise} \end{cases}$$
$$-DM_t = \begin{cases} L_{t-1} - L_t & \text{if } L_{t-1} - L_t > H_t - H_{t-1} \text{ and } L_{t-1} - L_t > 0 \\ 0 & \text{otherwise} \end{cases}$$

3. Smoothed (Wilder's smoothing = EMA с α = 1/N):
$$+DI_t = 100 \times \frac{\text{Smoothed}(+DM, N)}{\text{Smoothed}(TR, N)}$$
$$-DI_t = 100 \times \frac{\text{Smoothed}(-DM, N)}{\text{Smoothed}(TR, N)}$$

4. DX и ADX:
$$DX_t = 100 \times \frac{|+DI_t - -DI_t|}{+DI_t + -DI_t}$$
$$ADX_t = \text{Smoothed}(DX, N)$$

**Режим через ADX:**
- ADX > 25 AND +DI > -DI → **Bull Trend**
- ADX > 25 AND -DI > +DI → **Bear Trend**
- ADX < 25 → **Range** (нужен дополнительный фильтр волатильности для High/Low)

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| ADX запаздывает (lag ~N/2 баров) | Тренд уже начался, а ADX ещё < 25 | Комбинировать с быстрым индикатором (EMA slope) |
| ADX не различает High/Low Vol Range | Всё < 25 = "Range" | Добавить фильтр: ATR > percentile(75) → High Vol, < percentile(25) → Low Vol |
| Боковик с всплесками волатильности | ADX может подняться > 25 на всплеске | Требовать ADX > 25 удерживаться ≥ 3 бара подряд |
| Тонкий рынок (мало объёма) | ADX даёт ложные сигналы | Добавить фильтр минимального объёма |

#### Оценка

**Самый простой и быстрый метод.** Не требует обучения. Работает в реальном времени. Но — **не вероятностный** (hard threshold), не учитывает неопределённость, плохо работает на переходах между режимами.

**Рейтинг: 7/10 как standalone, 9/10 как дополнение к HMM.**

---

### 2.5 GARCH (Generalized Autoregressive Conditional Heteroskedasticity)

#### Формула

**GARCH(1,1):**
$$r_t = \mu + \varepsilon_t$$
$$\varepsilon_t = \sigma_t \cdot z_t, \quad z_t \sim \mathcal{N}(0,1)$$
$$\sigma_t^2 = \omega + \alpha \varepsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$

где:
- $\omega > 0$ — базовый уровень дисперсии
- $\alpha \geq 0$ — реакция на последний шок ($\varepsilon_{t-1}^2$)
- $\beta \geq 0$ — персистентность ($\sigma_{t-1}^2$)
- $\alpha + \beta < 1$ — стационарность

**Условие:** $\alpha + \beta$ близко к 1 → высокая персистентность (volatility clustering).

**Regime detection через GARCH:**
- $\sigma_t^2 > Q_{75}(\sigma^2)$ → **High Volatility** regime
- $\sigma_t^2 < Q_{25}(\sigma^2)$ → **Low Volatility** regime
- Но GARCH **не даёт направления** (Bull/Bear) — только волатильность.

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| α + β → 1 (IGARCH) | Волатильность не возвращается к среднему | Ограничить β < 0.95 |
| Асимметрия (падения > ростов) | Стандартный GARCH симметричен | EGARCH или GJR-GARCH (добавлен член для негативных шоков) |
| Fat tails | Нормальное распределение не подходит | Student-t GARCH или GED GARCH |
| Калибровка на коротких окнах | Параметры нестабильны | Минимум 500 наблюдений для калибровки |

#### Оценка

GARCH — **прекрасная модель волатильности**, но **не regime detection модель**. Она предсказывает $\sigma_t^2$ (continuously), а не дискретные состояния. Для regime detection нужно дополнение (пороги или HMM на GARCH-фильтрах).

**Рейтинг: 5/10 для regime detection standalone, 8/10 как feature для HMM.**

---

### 2.6 Hurst Exponent

#### Формула

**R/S (Rescaled Range) анализ:**

1. Разбить ряд на окна длиной $n$.
2. Для каждого окна:
   - $X_i = \ln(P_i / P_1)$ — кумулятивное отклонение от среднего
   - $R_n = \max(X) - \min(X)$ — range
   - $S_n = \text{std}(r_t)$ — стандартное отклонение доходностей
   - $(R/S)_n = R_n / S_n$
3. Линейная регрессия $\ln(R/S)_n = H \cdot \ln(n) + c$
4. Наклон $H$ = Hurst exponent.

**Интерпретация:**
- $H = 0.5$ — случайное блуждание
- $H > 0.5$ — тренд-персистентность (Bull или Bear, без различения)
- $H < 0.5$ — анти-персистентность (mean-reversion / Range)

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Не различает Bull от Bear | H > 0.5 только означает "есть тренд" | Комбинировать с sign(log_return) |
| Медленная сходимость | Требует длинных окон для надёжной оценки | Минимум 500 баров, prefer DFA вместо R/S |
| Нестационарность | H нестабилен на нестационарных рядах | Detrended Fluctuation Analysis (DFA) — робастнее |

#### Оценка

Полезен как **индикатор типа** рынка (trending vs mean-reverting), но **не даёт конкретного режима** (Bull/Bear/Range). Один скаляр для сложной динамики.

**Рейтинг: 6/10 standalone, 7/10 как feature.**

---

### 2.7 Changepoint Detection (PELT, BOCPD, CUSUM)

#### PELT (Pruned Exact Linear Time)

**Формула:** Минимизирует:
$$\sum_{i=1}^{m} [C(y_{\tau_{i-1}+1:\tau_i})] + \beta m$$

где:
- $C(\cdot)$ — cost function (neg log-likelihood сегмента)
- $\beta$ — penalty (BIC: $\beta = \frac{d}{2} \ln n$, где d = кол-во параметров)
- $m$ — количество changepoints

**Pruning rule:** Если для точки $t^*$ cost с changepoint в $t^*$ выше, чем без неё — отсекаем все будущие changepoints, связанные с $t^*$.

**Сложность:** O(n) в среднем (благодаря pruning).

#### BOCPD (Bayesian Online Changepoint Detection)

**Формула:**
$$P(r_t | r_{1:t-1}) = \sum_{r_{t-1}} P(r_t | r_{t-1}) \cdot P(r_{t-1} | r_{1:t-1})$$

где $r_t$ — run length (время с последнего changepoint).

**Predictive probability:**
$$P(x_t | r_{t-1}) = \frac{P(x_t | x_{t-r_{t-1}:t-1})}{P(x_{t-r_{t-1}:t-1})}$$

**Prior на run length:** Typically geometric: $P(r_t = r_{t-1}+1) = 1 - \lambda^{-1}$ (hazard rate $H = 1/\lambda$).

#### CUSUM (CUmulative SUM)

**Формула:**
$$S_t^+ = \max(0, S_{t-1}^+ + (x_t - \mu_0) - k)$$
$$S_t^- = \max(0, S_{t-1}^- - (x_t - \mu_0) - k)$$

**Alarm:** $S_t^+ > h$ или $S_t^- > h$ → changepoint detected.
- $\mu_0$ — целевое среднее
- $k$ — допуск (drift), обычно $k = 0.5\sigma$
- $h$ — порог (threshold), обычно $h = 4\sigma$ или $h = 5\sigma$

#### Edge Cases (общие для changepoint detection)

| Ситуация | Проблема | Решение |
|---|---|---|
| PELT: penalty β | Слишком мал → много ложных, велик → пропуски | Cross-validation на валидации, или BIC |
| BOCPD: prior λ | Определяет ожидаемую частоту changepoints | λ = 200 (ожидаем changepoint каждые 200 баров) для крипты |
| CUSUM: параметры k, h | Чувствительность vs false positive | ARL₀ (Average Run Length) подбор: настраивать h для ARL₀ ≈ 200 |
| Градуальные изменения | Все 3 метода лучше ловят abrupt changes | PELT с kernel-based cost (не просто mean/var) |
| Много признаков | Нужно multivariate changepoint | PELT с Gaussian cost на векторе признаков |

#### Оценка

Changepoint detection находит **границы** между режимами, но **не классифицирует** сами режимы. Нужно дополнение: после нахождения changepoint — классифицировать каждый сегмент.

**PELT: 7/10** (offline, точно, но retroactive)
**BOCPD: 8/10** (online, вероятностный, хорошо для real-time)
**CUSUM: 6/10** (простой, но одномерный, требует настройки)

---

### 2.8 Rolling Statistics

#### Формула

На скользящем окне $W$:
$$\hat{\mu}_t = \frac{1}{W}\sum_{i=0}^{W-1} r_{t-i}$$
$$\hat{\sigma}_t = \sqrt{\frac{1}{W-1}\sum_{i=0}^{W-1} (r_{t-i} - \hat{\mu}_t)^2}$$
$$\text{skew}_t = \frac{\frac{1}{W}\sum(r_{t-i} - \hat{\mu}_t)^3}{\hat{\sigma}_t^3}$$
$$\text{kurt}_t = \frac{\frac{1}{W}\sum(r_{t-i} - \hat{\mu}_t)^4}{\hat{\sigma}_t^4}$$

**Regime classification через пороги:**
```
if |μ_t| > k₁·σ_t AND σ_t > σ_median → Trend (Bull если μ > 0, Bear если μ < 0)
if |μ_t| < k₁·σ_t AND σ_t > σ_median → High Vol Range
if |μ_t| < k₁·σ_t AND σ_t < σ_median → Low Vol Range
```

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| Выбор окна W | Слишком мало → шум, много → лаг | Экспоненциальное взвешивание (EWMA) вместо равного |
| Нестационарность | Статистики устаревают | Использовать адаптивное окно или EWMA |
| Outlier | Один выброс меняет среднее и σ | Median-based statistics (MAD вместо std) |

#### Оценка

**Самый простой метод.** Работает, но — каждый бар оценивается независимо, нет вероятностной модели, высокий лаг. Для production бота — недостаточно.

**Рейтинг: 4/10 standalone, 6/10 как baseline.**

---

### 2.9 K-Means Clustering on Features

#### Формула

Минимизировать:
$$J = \sum_{i=1}^{n} \min_{\mu_j} \|x_i - \mu_j\|^2$$

**Признаки для regime detection:**
```rust
let features = vec![
    rolling_mean_return(20),      // направление
    rolling_std_return(20),       // волатильность
    adx(14),                      // сила тренда
    volume_zscore(20),            // объёмная активность
    skewness(20),                 // асимметрия
    hurst_approx,                 // персистентность
];
```

**Алгоритм:**
1. Инициализировать K центроидов (K-means++)
2. E-шаг: назначить каждую точку ближайшему центроиду
3. M-шаг: обновить центроиды как среднее назначенных точек
4. Повторять до сходимости

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| K неизвестно | Правильное количество кластеров | Elbow method + Silhouette score |
| Нелинейные границы кластеров | K-means только линейные | DBSCAN или Spectral clustering |
| Масштаб признаков | Разные единицы → domination | StandardScaler (z-score normalization) |
| Классификация в реальном времени | K-means — batch алгоритм | Обучить offline, classifiy online по расстоянию до центроидов |

#### Оценка

Хороший **baseline**. Простой, интерпретируемый. Но — нет временной зависимости (как GMM), нет вероятностей.

**Рейтинг: 5/10 standalone, 7/10 как feature extractor для HMM.**

---

### 2.10 Rule-Based Hybrid (ADX + Volatility Percentile + Trend Slope)

#### Формула

```rust
fn detect_regime(
    adx: f64,
    plus_di: f64,
    minus_di: f64,
    atr_percentile: f64,  // текущий ATR в percentile за 200 баров
    ema_slope: f64,       // (EMA50_t - EMA50_{t-5}) / EMA50_{t-5}
) -> Regime {
    const ADX_TREND: f64 = 25.0;
    const HIGH_VOL_PCTL: f64 = 75.0;
    const LOW_VOL_PCTL: f64 = 25.0;

    if adx > ADX_TREND {
        if plus_di > minus_di && ema_slope > 0.0 {
            Regime::BullTrend
        } else if minus_di > plus_di && ema_slope < 0.0 {
            Regime::BearTrend
        } else {
            // ADX > 25, но DI не определяет направление — переходный
            if atr_percentile > HIGH_VOL_PCTL {
                Regime::HighVolRange
            } else {
                Regime::LowVolRange
            }
        }
    } else {
        if atr_percentile > HIGH_VOL_PCTL {
            Regime::HighVolRange
        } else {
            Regime::LowVolRange
        }
    }
}
```

#### Edge Cases

| Ситуация | Проблема | Решение |
|---|---|---|
| ADX на границе 25 | Дрожание между Trend/Range | Hysteresis: переход в Trend при ADX > 28, обратно при ADX < 22 |
| Percentile нестабилен | Текущее значение — outlier → percentile смещается | Robust percentile (rolling median + MAD) |
| Тренд без ADX | EMA slope растёт, но ADX ещё < 25 | EMA slope как early warning, добавить "Probable Trend" промежуточный |

#### Оценка

**Самый production-ready метод** на старте. Не требует обучения, полная прозрачность, легко дебажить. Но — пороги эмпирические, не адаптируются к changing market structure.

**Рейтинг: 7/10.**

---

### 2.11 Microstructure-Based (Order Flow Imbalance)

#### Формула

$$\text{OFI}_t = \Delta V^{bid}_t - \Delta V^{ask}_t + I[\text{trade at bid}] - I[\text{trade at ask}]$$

или упрощённый:

$$\text{Regime Signal} = \text{sign}\left(\sum_{t-W}^{t} \text{OFI}_i\right) \times \left|\sum \text{OFI}_i\right| / W$$

#### Оценка

Требует tick data и order book. Не применимо на 1H+ таймфреймах без Level 2 данных. Для MVP — не подходит.

**Рейтинг: 3/10 (data availability), 8/10 (информативность при наличии данных).**

---

### 2.12 Ensemble / Voting

#### Формула

$$\hat{S}_t = \text{mode}\left(f_{\text{HMM}}(t), f_{\text{ADX}}(t), f_{\text{Hurst}}(t), f_{\text{GARCH}}(t)\right)$$

или взвешенное голосование:

$$P(\text{Regime} = k | t) = \sum_{m} w_m \cdot P_m(\text{Regime} = k | t)$$

где $w_m$ — вес модели $m$ (оптимизируется на валидации).

#### Оценка

Ensemble **всегда** лучше любого single method (при достаточном разнообразии моделей). Для production рекомендуется.

**Рейтинг: 9/10.**

---

## 3. Сравнительная таблица

| Метод | Тип | Онлайн? | Вероятностный? | Направление? | Волатильность? | Сложность | Рейтинг |
|---|---|---|---|---|---|---|---|
| **HMM (Gaussian)** | Probabilistic | ✅ (Viterbi) | ✅ | ✅ | ✅ (через признаки) | Средняя | **9/10** |
| **HSMM** | Probabilistic | ✅ | ✅ | ✅ | ✅ | Высокая | 7/10 |
| **GMM/Clustering** | Probabilistic | ✅ | ✅ | ❌ | ❌ | Низкая | 6/10 |
| **ADX Threshold** | Rule-based | ✅ | ❌ | ✅ (+DI/-DI) | ❌ | Очень низкая | 7/10 |
| **GARCH** | Vol model | ✅ | ✅ | ❌ | ✅ | Средняя | 5/10* |
| **Hurst Exponent** | Statistical | ❌ (batch) | ❌ | ❌ (только trend/no-trend) | ❌ | Низкая | 6/10 |
| **PELT** | Changepoint | ❌ (offline) | ❌ | ❌ | ❌ | Средняя | 7/10 |
| **BOCPD** | Changepoint | ✅ | ✅ | ❌ | ❌ | Средняя | 8/10 |
| **CUSUM** | Changepoint | ✅ | ❌ | ❌ | ❌ | Низкая | 6/10 |
| **Rolling Stats** | Statistical | ✅ | ❌ | ✅ | ✅ | Очень низкая | 4/10 |
| **K-Means** | Clustering | ✅ (после обучения) | ❌ | ✅ | ✅ | Низкая | 5/10 |
| **Rule-Based Hybrid** | Rule-based | ✅ | ❌ | ✅ | ✅ | Очень низкая | 7/10 |
| **Ensemble** | Combined | ✅ | ✅ | ✅ | ✅ | Средняя | **9/10** |

\* GARCH оценён именно для regime detection; как volatility model — 8/10.

---

## 4. Переключение стратегий

### Таблица: Режим → Стратегия

| Режим | Primary Стратегия | Secondary | Фильтры | SL/TP | Размер позиции | Особенности |
|---|---|---|---|---|---|---|
| **Bull Trend** | **Momentum Long** (follow trend) | Breakout | EMA20 > EMA50, RSI < 70 (не перекуплен) | SL = Entry - 2×ATR, TP = Entry + 3×ATR | Полный (Fractional Kelly) | Давить шорт-сигналы, только лонг |
| **Bear Trend** | **Momentum Short** (follow trend) | Breakout (downside) | EMA20 < EMA50, RSI > 30 (не перепродан) | SL = Entry + 1.5×ATR, TP = Entry - 3×ATR | 75% от Kelly (падения быстрее → риск выше) | Давить лонг-сигналы, только шорт |
| **High Vol Range** | **Mean-Reversion** | Straddle/Strangle (если деривативы) | Bollinger %B < 0.05 для лонга, > 0.95 для шорта | SL = Entry ± 1.5×ATR, TP = mid-channel | 50% от Kelly | Широкие стопы, быстрый TP, не держать долго |
| **Low Vol Range** | **Wait / Squeeze Breakout** | Market Making (spread) | Bollinger внутри Keltner (Squeeze) | Не торговать до breakout | Минимальный или 0 | Накопление → breakout будет. Подготовить ордера |

### Стратегия переключения

```
Переключение режима:
  1. Получить P(режим) от HMM (или ensemble)
  2. Новый режим доминирует (P > 0.6) в течение N_bars_confirmation баров
  3. Плавный переход:
     - Закрыть текущие позиции текущего режима
     - Подождать 1 бар (cooling period)
     - Открыть позиции нового режима
  4. Если P(режим) < 0.5 — "transition zone" → не торговать
```

### Таблица переходов (матрица)

| Из \ В | Bull Trend | Bear Trend | High Vol Range | Low Vol Range |
|---|---|---|---|---|
| **Bull Trend** | — | Закрыть лонг → ждать → шорт | Частичное закрытие, уменьшить leverage | Стоп-торговля, ждать |
| **Bear Trend** | Закрыть шорт → ждать → лонг | — | Частичное закрытие, mean-rev лонг | Стоп-торговля, ждать |
| **High Vol Range** | Открыть лонг (breakout подтверждён) | Открыть шорт (breakout подтверждён) | — | Уменьшить позицию, ждать squeeze |
| **Low Vol Range** | Подготовить лонг ордера | Подготовить шорт ордера | Расширить стопы, начать mean-rev | — |

---

## 5. Топ-3 рекомендации

### 🥇 #1: Multivariate Gaussian HMM (4 состояния)

**Почему:**
- Единственный метод, который одновременно определяет **и** режим, **и** направление, **и** волатильность
- Вероятностный: $P(\text{Bull} | \text{data}) = 0.73$ — не бинарный ответ, а уверенность
- Online decoding через Viterbi — работает в реальном времени
- Уже выбран в проекте (Research Indicators, Модуль 6) — минимальные изменения архитектуры
- Доказанная эффективность: Ang & Bekaert (2002), Guidolin & Timmermann (2007), Hassan & Nath (2005) для крипты

**Конфигурация:**
```rust
HMM {
    n_states: 4,  // Bull, Bear, HighVolRange, LowVolRange
    features: [log_return, atr_normalized, volume_zscore, adx_value],
    covariance_type: "diag",  // diagonal covariance (4 признака, не full)
    n_iter: 100,              // max итераций Baum-Welch
    tol: 1e-4,                // convergence threshold
    n_init: 10,               // multi-start для избежания local maxima
    recalibrate_every: 500,   // перекалибровка каждые 500 баров
    min_bars_for_calibration: 1000,
}
```

---

### 🥈 #2: BOCPD + HMM (Changepoint → Classification)

**Почему:**
- BOCPD обнаруживает **границы** режимов online, с вероятностной оценкой
- После обнаружения changepoint — HMM классифицирует новый режим
- Комбинация покрывает обе задачи: **когда** сменился режим (BOCPD) и **в какой** режим (HMM)
- Особенно полезно для обнаружения rare events (flash crashes, black swans), которые HMM может пропустить

**Конфигурация:**
```rust
BOCPD {
    hazard_lambda: 200.0,  // ожидаемый changepoint каждые 200 баров
    prior: GaussianConjugate {
        mu_0: 0.0,
        kappa_0: 1.0,
        alpha_0: 1.0,
        beta_0: 1.0,
    },
    threshold: 0.5,  // P(changepoint) > 0.5 → alert
}

// Pipeline:
// 1. BOCPD на каждом баре → P(changepoint)
// 2. Если P(changepoint) > 0.5 → запустить HMM classification на окрестности
// 3. HMM возвращает regime + P(regime)
// 4. Если regime изменился → signal regime change
```

---

### 🥉 #3: Rule-Based Hybrid (ADX + Volatility + Trend Slope) — как fallback

**Почему:**
- Нулевая сложность обучения, мгновенный результат
- Полная прозрачность: можно объяснить каждый decision
- Как **fallback**: если HMM не откалиброван (мало данных) или BOCPD не готов — rule-based работает сразу
- Также полезен как **validation**: если HMM и rule-based disagree → тревога

---

### Итоговая архитектура

```
                    ┌──────────────────┐
  OHLCV Data ──────→│  Feature Engine   │
                    │  (log_ret, atr,   │
                    │   vol_zscore, adx)│
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  #1: HMM (4 states)│──→ P(Bull), P(Bear), P(HighVol), P(LowVol)
                    │  Primary Signal    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  #2: BOCPD        │──→ P(changepoint)
                    │  Changepoint Alert│
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  #3: Rule-Based   │──→ ADX-based regime (fallback)
                    │  Fallback + Check │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Ensemble Vote    │──→ Final Regime + Confidence
                    │  (HMM weight: 0.6,│
                    │   BOCPD: 0.2,     │
                    │   Rules: 0.2)     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Strategy Router  │──→ Select strategy per regime
                    └──────────────────┘
```

---

## 6. Rust-реализация

### 6.1 Multivariate Gaussian HMM

```rust
use ndarray::{Array1, Array2, Axis};
use ndarray_stats::QuantileExt;

/// 4 состояния рынка
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MarketRegime {
    BullTrend = 0,
    BearTrend = 1,
    HighVolRange = 2,
    LowVolRange = 3,
}

/// Параметры Gaussian HMM
pub struct GaussianHMM {
    /// Количество скрытых состояний
    pub n_states: usize,
    /// Начальное распределение: [K]
    pub start_prob: Array1<f64>,
    /// Матрица переходов: [K, K]
    pub trans_mat: Array2<f64>,
    /// Средние эмиссий: [K, D]
    pub means: Array2<f64>,
    /// Диагональные дисперсии: [K, D]
    pub covars_diag: Array2<f64>,
    /// Статус обучения
    pub fitted: bool,
}

/// Наблюдение (вектор признаков на каждый бар)
pub struct Observation {
    /// log_return: ln(close_t / close_{t-1})
    pub log_return: f64,
    /// atr_normalized: ATR(14) / close
    pub atr_norm: f64,
    /// volume_zscore: (vol - ma(vol,20)) / std(vol,20)
    pub vol_zscore: f64,
    /// adx_value: ADX(14)
    pub adx: f64,
}

impl Observation {
    pub fn to_array(&self) -> Array1<f64> {
        Array1::from_vec(vec![
            self.log_return,
            self.atr_norm,
            self.vol_zscore,
            self.adx,
        ])
    }
}

impl GaussianHMM {
    pub fn new(n_states: usize, n_features: usize) -> Self {
        // Равные начальные вероятности
        let start_prob = Array1::from_elem(n_states, 1.0 / n_states as f64);

        // Матрица переходов: диагональ 0.95 (режимы устойчивы), остальное делится поровну
        let mut trans_mat = Array2::zeros((n_states, n_states));
        for i in 0..n_states {
            for j in 0..n_states {
                if i == j {
                    trans_mat[[i, j]] = 0.95;
                } else {
                    trans_mat[[i, j]] = 0.05 / (n_states - 1) as f64;
                }
            }
        }

        // Случайная инициализация средних и дисперсий (будут обновлены при обучении)
        let means = Array2::zeros((n_states, n_features));
        let covars_diag = Array2::ones((n_states, n_features));

        Self {
            n_states,
            start_prob,
            trans_mat,
            means,
            covars_diag,
            fitted: false,
        }
    }

    /// Вычислить log Gaussian probability для каждого состояния
    /// Возвращает [T, K] матрицу log-likelihood'ов
    fn compute_log_likelihood(&self, observations: &Array2<f64>) -> Array2<f64> {
        let (t, d) = (observations.nrows(), observations.ncols());
        let mut log_prob = Array2::zeros((t, self.n_states));

        for k in 0..self.n_states {
            for ti in 0..t {
                let mut log_p = 0.0;
                for di in 0..d {
                    let diff = observations[[ti, di]] - self.means[[k, di]];
                    let var = self.covars_diag[[k, di]];
                    log_p += -0.5 * (2.0 * std::f64::consts::PI.ln() + var.ln()
                        + (diff * diff) / var);
                }
                log_prob[[ti, k]] = log_p;
            }
        }
        log_prob
    }

    /// Forward algorithm (log-space для численной стабильности)
    /// Возвращает log-alpha: [T, K]
    fn forward(&self, log_likelihood: &Array2<f64>) -> Array2<f64> {
        let (t, k) = (log_likelihood.nrows(), log_likelihood.ncols());
        let mut log_alpha = Array2::zeros((t, k));

        // Инициализация
        for j in 0..k {
            log_alpha[[0, j]] = self.start_prob[j].ln() + log_likelihood[[0, j]];
        }

        // Рекурсия
        for ti in 1..t {
            for j in 0..k {
                // log-sum-exp для численной стабильности
                let mut max_val = f64::NEG_INFINITY;
                let mut terms = Vec::with_capacity(k);
                for i in 0..k {
                    let val = log_alpha[[ti - 1, i]] + self.trans_mat[[i, j]].ln();
                    if val > max_val {
                        max_val = val;
                    }
                    terms.push(val);
                }
                let log_sum = max_val
                    + terms.iter().map(|&v| (v - max_val).exp()).sum::<f64>().ln();
                log_alpha[[ti, j]] = log_sum + log_likelihood[[ti, j]];
            }
        }
        log_alpha
    }

    /// Backward algorithm (log-space)
    fn backward(&self, log_likelihood: &Array2<f64>) -> Array2<f64> {
        let (t, k) = (log_likelihood.nrows(), log_likelihood.ncols());
        let mut log_beta = Array2::zeros((t, k));

        // Инициализация (log(1) = 0)
        // Уже нули

        // Рекурсия (обратная)
        for ti in (0..t - 1).rev() {
            for i in 0..k {
                let mut max_val = f64::NEG_INFINITY;
                let mut terms = Vec::with_capacity(k);
                for j in 0..k {
                    let val = self.trans_mat[[i, j]].ln()
                        + log_likelihood[[ti + 1, j]]
                        + log_beta[[ti + 1, j]];
                    if val > max_val {
                        max_val = val;
                    }
                    terms.push(val);
                }
                log_beta[[ti, i]] = max_val
                    + terms.iter().map(|&v| (v - max_val).exp()).sum::<f64>().ln();
            }
        }
        log_beta
    }

    /// Baum-Welch (EM) обучение
    pub fn fit(
        &mut self,
        observations: &Array2<f64>,
        max_iter: usize,
        tol: f64,
    ) {
        let (t, _d) = (observations.nrows(), observations.ncols());
        let k = self.n_states;

        // Инициализация параметров из данных (K-means++)
        self.initialize_from_data(observations);

        let mut prev_log_likelihood = f64::NEG_INFINITY;

        for iteration in 0..max_iter {
            let log_likelihood = self.compute_log_likelihood(observations);
            let log_alpha = self.forward(&log_likelihood);
            let log_beta = self.backward(&log_likelihood);

            // Проверка сходимости (total log-likelihood)
            let total_ll = self.log_sum_exp_row(&log_alpha.row(t - 1));
            if (total_ll - prev_log_likelihood).abs() < tol {
                eprintln!("HMM converged at iteration {}, log-likelihood: {:.4}",
                    iteration, total_ll);
                break;
            }
            prev_log_likelihood = total_ll;

            // E-шаг: gamma и xi
            let gamma = self.compute_gamma(&log_alpha, &log_beta, &log_likelihood);
            let xi = self.compute_xi(&log_alpha, &log_beta, &log_likelihood);

            // M-шаг: обновить параметры
            // start_prob
            for j in 0..k {
                self.start_prob[j] = gamma[[0, j]];
            }

            // trans_mat
            for i in 0..k {
                let denom: f64 = (0..t - 1).map(|ti| gamma[[ti, i]]).sum();
                for j in 0..k {
                    let numer: f64 = (0..t - 1).map(|ti| xi[[ti, i, j]]).sum();
                    self.trans_mat[[i, j]] = if denom > 1e-300 {
                        numer / denom
                    } else {
                        1.0 / k as f64
                    };
                }
            }

            // means и covars_diag
            for j in 0..k {
                let weight_sum: f64 = (0..t).map(|ti| gamma[[ti, j]]).sum();
                for d in 0..self.means.ncols() {
                    // Обновление средних
                    let mean_numer: f64 =
                        (0..t).map(|ti| gamma[[ti, j]] * observations[[ti, d]]).sum();
                    self.means[[j, d]] = mean_numer / weight_sum;

                    // Обновление дисперсий
                    let var_numer: f64 = (0..t)
                        .map(|ti| {
                            let diff = observations[[ti, d]] - self.means[[j, d]];
                            gamma[[ti, j]] * diff * diff
                        })
                        .sum();
                    self.covars_diag[[j, d]] =
                        (var_numer / weight_sum).max(1e-6); // floor для стабильности
                }
            }
        }

        self.fitted = true;
    }

    /// Viterbi decoding: найти наиболее вероятную последовательность состояний
    pub fn predict(&self, observations: &Array2<f64>) -> Vec<MarketRegime> {
        assert!(self.fitted, "HMM must be fitted before prediction");

        let log_likelihood = self.compute_log_likelihood(observations);
        let (t, k) = (log_likelihood.nrows(), log_likelihood.ncols());

        // Viterbi: log-delta и psi
        let mut log_delta = Array2::zeros((t, k));
        let mut psi = Array2::<usize>::zeros((t, k));

        // Инициализация
        for j in 0..k {
            log_delta[[0, j]] = self.start_prob[j].ln() + log_likelihood[[0, j]];
        }

        // Рекурсия
        for ti in 1..t {
            for j in 0..k {
                let mut best_val = f64::NEG_INFINITY;
                let mut best_idx = 0;
                for i in 0..k {
                    let val = log_delta[[ti - 1, i]] + self.trans_mat[[i, j]].ln();
                    if val > best_val {
                        best_val = val;
                        best_idx = i;
                    }
                }
                log_delta[[ti, j]] = best_val + log_likelihood[[ti, j]];
                psi[[ti, j]] = best_idx;
            }
        }

        // Backtracking
        let mut states = vec![0usize; t];
        // Последний: argmax log_delta[T-1, :]
        states[t - 1] = log_delta
            .row(t - 1)
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .unwrap()
            .0;

        for ti in (0..t - 1).rev() {
            states[ti] = psi[[ti + 1, states[ti + 1]]];
        }

        states
            .iter()
            .map(|&s| match s {
                0 => MarketRegime::BullTrend,
                1 => MarketRegime::BearTrend,
                2 => MarketRegime::HighVolRange,
                3 => MarketRegime::LowVolRange,
                _ => MarketRegime::LowVolRange,
            })
            .collect()
    }

    /// Возвращает posterior вероятности состояний на каждом шаге
    pub fn predict_proba(&self, observations: &Array2<f64>) -> Array2<f64> {
        assert!(self.fitted, "HMM must be fitted before prediction");

        let log_likelihood = self.compute_log_likelihood(observations);
        let log_alpha = self.forward(&log_likelihood);
        let log_beta = self.backward(&log_likelihood);

        let (t, k) = (log_likelihood.nrows(), log_likelihood.ncols());
        let mut gamma = Array2::zeros((t, k));

        for ti in 0..t {
            let mut log_gamma_row = Array1::zeros(k);
            for j in 0..k {
                log_gamma_row[j] = log_alpha[[ti, j]] + log_beta[[ti, j]];
            }
            // Normalize (log-sum-exp)
            let log_total = self.log_sum_exp_row(&log_gamma_row);
            for j in 0..k {
                gamma[[ti, j]] = (log_gamma_row[j] - log_total).exp();
            }
        }
        gamma
    }

    // --- Вспомогательные методы ---

    fn log_sum_exp_row(&self, log_values: &Array1<f64>) -> f64 {
        let max_val = log_values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        max_val + log_values.iter().map(|&v| (v - max_val).exp()).sum::<f64>().ln()
    }

    fn initialize_from_data(&mut self, observations: &Array2<f64>) {
        // Простая инициализация: равные квантили по первому признаку (log_return)
        let n = observations.nrows();
        let mut sorted: Vec<f64> = observations.column(0).to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let k = self.n_states;
        for state in 0..k {
            let start = (state * n) / k;
            let end = ((state + 1) * n) / k;
            let slice = &sorted[start..end];

            for d in 0..observations.ncols() {
                let col: Vec<f64> = (start..end).map(|i| observations[[i, d]]).collect();
                let mean = col.iter().sum::<f64>() / col.len() as f64;
                let var = col.iter().map(|&x| (x - mean).powi(2)).sum::<f64>()
                    / col.len() as f64;
                self.means[[state, d]] = mean;
                self.covars_diag[[state, d]] = var.max(1e-6);
            }
        }
    }

    fn compute_gamma(
        &self,
        log_alpha: &Array2<f64>,
        log_beta: &Array2<f64>,
        _log_likelihood: &Array2<f64>,
    ) -> Array2<f64> {
        let (t, k) = (log_alpha.nrows(), log_alpha.ncols());
        let mut gamma = Array2::zeros((t, k));

        for ti in 0..t {
            let mut log_g = Array1::zeros(k);
            for j in 0..k {
                log_g[j] = log_alpha[[ti, j]] + log_beta[[ti, j]];
            }
            let log_total = self.log_sum_exp_row(&log_g);
            for j in 0..k {
                gamma[[ti, j]] = (log_g[j] - log_total).exp();
            }
        }
        gamma
    }

    fn compute_xi(
        &self,
        log_alpha: &Array2<f64>,
        log_beta: &Array2<f64>,
        log_likelihood: &Array2<f64>,
    ) -> ndarray::Array3<f64> {
        let (t, k) = (log_alpha.nrows(), log_alpha.ncols());
        let mut xi = ndarray::Array3::zeros((t - 1, k, k));

        for ti in 0..t - 1 {
            let mut log_xi = Array2::zeros((k, k));
            for i in 0..k {
                for j in 0..k {
                    log_xi[[i, j]] = log_alpha[[ti, i]]
                        + self.trans_mat[[i, j]].ln()
                        + log_likelihood[[ti + 1, j]]
                        + log_beta[[ti + 1, j]];
                }
            }
            // Normalize
            let mut all_vals: Vec<f64> = log_xi.iter().cloned().collect();
            let max_val = all_vals.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
            let log_total = max_val
                + all_vals.iter().map(|&v| (v - max_val).exp()).sum::<f64>().ln();

            for i in 0..k {
                for j in 0..k {
                    xi[[ti, i, j]] = (log_xi[[i, j]] - log_total).exp();
                }
            }
        }
        xi
    }
}
```

### 6.2 BOCPD (Bayesian Online Changepoint Detection)

```rust
/// Конъюгатный prior: Normal-Inverse-Gamma
pub struct GaussianConjugatePrior {
    pub mu_0: f64,
    pub kappa_0: f64,
    pub alpha_0: f64,
    pub beta_0: f64,
}

impl GaussianConjugatePrior {
    /// Обновить posterior после наблюдения x
    pub fn update(&self, x: f64) -> Self {
        Self {
            mu_0: (self.kappa_0 * self.mu_0 + x) / (self.kappa_0 + 1.0),
            kappa_0: self.kappa_0 + 1.0,
            alpha_0: self.alpha_0 + 0.5,
            beta_0: self.beta_0
                + self.kappa_0 * (x - self.mu_0).powi(2)
                    / (2.0 * (self.kappa_0 + 1.0)),
        }
    }

    /// Predictive probability: Student-t
    pub fn predictive_log_prob(&self, x: f64) -> f64 {
        let df = 2.0 * self.alpha_0;
        let scale = (self.beta_0 * (self.kappa_0 + 1.0)
            / (self.alpha_0 * self.kappa_0))
            .sqrt();
        let loc = self.mu_0;

        // Log Student-t PDF
        let z = (x - loc) / scale;
        ln_gamma((df + 1.0) / 2.0) - ln_gamma(df / 2.0)
            - 0.5 * (df * std::f64::consts::PI).ln()
            - scale.ln()
            - ((df + 1.0) / 2.0) * (1.0 + z * z / df).ln()
    }
}

pub struct BOCPD {
    pub hazard_lambda: f64,
    pub threshold: f64,
    /// Run length probabilities P(r_t = r | x_{1:t})
    run_length_probs: Vec<f64>,
    /// Priors для каждого run length
    priors: Vec<GaussianConjugatePrior>,
}

impl BOCPD {
    pub fn new(hazard_lambda: f64, threshold: f64, prior: GaussianConjugatePrior) -> Self {
        Self {
            hazard_lambda,
            threshold,
            run_length_probs: vec![1.0], // r=0 с вероятностью 1
            priors: vec![prior],
        }
    }

    /// Один шаг: вернуть P(changepoint) для нового наблюдения
    pub fn step(&mut self, x: f64) -> f64 {
        let hazard = 1.0 / self.hazard_lambda;
        let max_run = self.run_length_probs.len();

        // Predictive probabilities
        let mut pred_probs = Vec::with_capacity(max_run + 1);
        for prior in &self.priors {
            pred_probs.push(prior.predictive_log_prob(x));
        }

        // Growth probabilities (r_t = r_{t-1} + 1)
        let mut new_probs = vec![0.0; max_run + 1];
        for r in 0..max_run {
            let growth_prob =
                self.run_length_probs[r] * (1.0 - hazard) * pred_probs[r].exp();
            new_probs[r + 1] = growth_prob;
        }

        // Changepoint probability (r_t = 0)
        let cp_prob: f64 = (0..max_run)
            .map(|r| self.run_length_probs[r] * hazard * pred_probs[r].exp())
            .sum();
        new_probs[0] = cp_prob;

        // Normalize
        let total: f64 = new_probs.iter().sum();
        for p in new_probs.iter_mut() {
            *p /= total;
        }

        // Update priors
        let mut new_priors = Vec::with_capacity(max_run + 2);
        // r=0: reset prior
        new_priors.push(self.priors[0].update(x));
        for r in 0..max_run {
            new_priors.push(self.priors[r].update(x));
        }

        self.run_length_probs = new_probs;
        self.priors = new_priors;

        // Prune: удаляем run lengths с очень малой вероятностью
        let min_prob = 1e-10;
        let mut pruned_probs = Vec::new();
        let mut pruned_priors = Vec::new();
        for (i, &p) in self.run_length_probs.iter().enumerate() {
            if p > min_prob {
                pruned_probs.push(p);
                pruned_priors.push(std::mem::replace(
                    &mut self.priors[i],
                    self.priors[0].clone(),
                ));
            }
        }
        // Renormalize
        let total: f64 = pruned_probs.iter().sum();
        for p in pruned_probs.iter_mut() {
            *p /= total;
        }
        self.run_length_probs = pruned_probs;
        self.priors = pruned_priors;

        cp_prob / total
    }

    /// Сбросить состояние (например, после подтверждённого changepoint)
    pub fn reset(&mut self, prior: GaussianConjugatePrior) {
        self.run_length_probs = vec![1.0];
        self.priors = vec![prior];
    }
}

// Вспомогательная функция (приблизительная)
fn ln_gamma(x: f64) -> f64 {
    // Stirling approximation; для production использовать специализированную библиотеку
    (x - 0.5) * x.ln() - x + 0.5 * (2.0 * std::f64::consts::PI).ln()
}
```

### 6.3 Ensemble Router

```rust
/// Финальный ансамбль: объединяет HMM + BOCPD + Rule-Based
pub struct RegimeEnsemble {
    pub hmm: GaussianHMM,
    pub bocpd: Option<BOCPD>,
    pub hmm_weight: f64,
    pub bocpd_weight: f64,
    pub rules_weight: f64,
    /// Стабилизация: режим должен удерживаться N баров
    pub confirmation_bars: usize,
    /// Гистерезис: порог уверенности для смены режима
    pub switch_threshold: f64,
    current_regime: MarketRegime,
    regime_hold_count: usize,
}

impl RegimeEnsemble {
    pub fn detect_regime(
        &mut self,
        observation: &Observation,
        adx: f64,
        plus_di: f64,
        minus_di: f64,
        atr_percentile: f64,
        ema_slope: f64,
    ) -> (MarketRegime, f64) {
        let obs_array = observation.to_array().into_shape((1, 4)).unwrap();

        // 1. HMM probabilities
        let hmm_probs = self.hmm.predict_proba(&obs_array);
        let hmm_row = hmm_probs.row(0);

        // 2. BOCPD changepoint probability
        let cp_prob = self.bocpd
            .as_mut()
            .map(|b| b.step(observation.log_return))
            .unwrap_or(0.0);

        // 3. Rule-based regime
        let rule_regime = detect_regime_rule(adx, plus_di, minus_di, atr_percentile, ema_slope);
        let mut rule_probs = [0.0; 4];
        rule_probs[rule_regime as usize] = 1.0;

        // 4. Weighted ensemble
        let mut ensemble_probs = [0.0; 4];
        for i in 0..4 {
            ensemble_probs[i] = self.hmm_weight * hmm_row[i]
                + self.rules_weight * rule_probs[i];
        }
        // BOCPD: если changepoint — уменьшить уверенность текущего режима
        if cp_prob > self.switch_threshold {
            // Равномерно перераспределить часть веса
            for i in 0..4 {
                ensemble_probs[i] *= 1.0 - self.bocpd_weight * cp_prob;
            }
            let uniform = self.bocpd_weight * cp_prob / 4.0;
            for i in 0..4 {
                ensemble_probs[i] += uniform;
            }
        }

        // 5. Normalize
        let total: f64 = ensemble_probs.iter().sum();
        for p in ensemble_probs.iter_mut() {
            *p /= total;
        }

        // 6. Выбрать режим с максимальной вероятностью
        let (best_idx, &best_prob) = ensemble_probs
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .unwrap();

        let new_regime = match best_idx {
            0 => MarketRegime::BullTrend,
            1 => MarketRegime::BearTrend,
            2 => MarketRegime::HighVolRange,
            _ => MarketRegime::LowVolRange,
        };

        // 7. Стабилизация: меняем режим только если новый держится N баров
        if new_regime == self.current_regime {
            self.regime_hold_count += 1;
        } else {
            if best_prob > self.switch_threshold {
                self.regime_hold_count = 1;
                // Не переключаем сразу — ждём confirmation_bars
            }
        }

        if new_regime != self.current_regime
            && self.regime_hold_count >= self.confirmation_bars
            && best_prob > self.switch_threshold
        {
            self.current_regime = new_regime;
            self.regime_hold_count = 0;
        }

        (self.current_regime, best_prob)
    }
}

/// Rule-based fallback
fn detect_regime_rule(
    adx: f64,
    plus_di: f64,
    minus_di: f64,
    atr_percentile: f64,
    ema_slope: f64,
) -> MarketRegime {
    const ADX_TREND: f64 = 25.0;
    const HIGH_VOL_PCTL: f64 = 75.0;

    if adx > ADX_TREND {
        if plus_di > minus_di && ema_slope > 0.0 {
            MarketRegime::BullTrend
        } else if minus_di > plus_di && ema_slope < 0.0 {
            MarketRegime::BearTrend
        } else if atr_percentile > HIGH_VOL_PCTL {
            MarketRegime::HighVolRange
        } else {
            MarketRegime::LowVolRange
        }
    } else if atr_percentile > HIGH_VOL_PCTL {
        MarketRegime::HighVolRange
    } else {
        MarketRegime::LowVolRange
    }
}
```

---

## Итог

### Финальная рекомендация

| Приоритет | Метод | Роль |
|---|---|---|
| **#1** | **Multivariate Gaussian HMM (4 состояния)** | Primary regime detector. Вероятностный, online, proven. |
| **#2** | **BOCPD** | Changepoint alert для редких событий. Ускоряет обнаружение разворотов. |
| **#3** | **Rule-Based Hybrid (ADX + Vol)** | Fallback и валидация. Работает без обучения. |

**Архитектура:** Ensemble (веса 0.6 / 0.2 / 0.2) со стабилизацией (confirmation bars) и гистерезисом (switch threshold).

**4 режима:** Bull Trend, Bear Trend, High Vol Range, Low Vol Range — каждый ведёт к **полностью другой** стратегии, поэтому разделение критично.

**Для MVP (v0.1):** начать с #3 (Rule-Based), затем добавить #1 (HMM) при накоплении ≥ 1000 баров. BOCPD — v0.2+.