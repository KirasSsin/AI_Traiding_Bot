
# Агент 19: Управление портфелем (Portfolio Management)

> Глубокий аудит всех методов управления портфелем для крипто-торгового бота.
> Ограничение: **5–7 одновременных пар** (ликвидность).
> Язык реализации: **Rust**.

---

## Содержание

1. [Обзор методов](#1-обзор-методов)
2. [Markowitz Mean-Variance Optimization (MVO)](#2-markowitz-mean-variance-optimization-mvo)
3. [Black-Litterman Model](#3-black-litterman-model)
4. [Risk Parity](#4-risk-parity)
5. [Hierarchical Risk Parity (HRP)](#5-hierarchical-risk-parity-hrp)
6. [Minimum Variance Portfolio](#6-minimum-variance-portfolio)
7. [Maximum Sharpe Portfolio](#7-maximum-sharpe-portfolio)
8. [Equal Weight Portfolio](#8-equal-weight-portfolio)
9. [Inverse Volatility Portfolio](#9-inverse-volatility-portfolio)
10. [Kelly Criterion Portfolio](#10-kelly-criterion-portfolio)
11. [Correlation-based Allocation](#11-correlation-based-allocation)
12. [PCA-based Allocation](#12-pca-based-allocation)
13. [Dynamic Rebalancing](#13-dynamic-rebalancing)
14. [Crypto-Specific: Корреляция для крипты](#14-crypto-specific-корреляция-для-крипты)
15. [Сравнительная таблица](#15-сравнительная-таблица)
16. [Рекомендация: топ 3](#16-рекомендация-топ-3)
17. [Rust-реализация: ядро](#17-rust-реализация-ядро)

---

## 1. Обзор методов

Все методы управления портфелем делятся на несколько категорий:

| Категория | Методы | Сложность | Подходит для крипты |
|---|---|---|---|
| **Оптимизация на ковариации** | Markowitz MVO, Min Variance, Max Sharpe | Высокая | ⚠️ Частично |
| **Bayesian** | Black-Litterman | Очень высокая | ❌ Нет (нет мнений экспертов) |
| **Риск-ориентированные** | Risk Parity, HRP, Inverse Vol | Средняя | ✅ Да |
| **Простые эвристики** | Equal Weight | Низкая | ✅ Да |
| **Размер позиции** | Kelly (Fractional) | Средняя | ✅ Да |
| **Статистические** | PCA-based, Correlation-based | Средняя-Высокая | ⚠️ Частично |
| **Динамические** | Threshold/Calendar Rebalancing | Низкая-Средняя | ✅ Да |

---

## 2. Markowitz Mean-Variance Optimization (MVO)

### Формула

Находим веса **w**, которые минимизируют портфельную дисперсию при заданной целевой доходности:

```
min  w'Σw
 s.t. w'μ = μ_target
      w'1 = 1
      w_i ≥ 0  (long-only)
```

**Решение через метод Лагранжа:**

```
w* = (Σ⁻¹(μ - λ₁·1)) / (1'Σ⁻¹(μ - λ₁·1))
```

Где:
- **w** — вектор весов (N×1)
- **Σ** — ковариационная матрица (N×N)
- **μ** — вектор ожидаемых доходностей (N×1)
- **λ₁** — множитель Лагранжа
- **1** — вектор единиц (N×1)

**Портфельная доходность и дисперсия:**

```
μ_p = w'μ = Σ(w_i · μ_i)
σ²_p = w'Σw = Σᵢ Σⱼ(w_i · w_j · σᵢⱼ)
σ_p = √(w'Σw)
```

### Edge Cases

| Проблема | Описание | Решение |
|---|---|---|
| **Singular covariance matrix** | Σ необратима (коллинеарные активы, N > T) | Ledoit-Wolf shrinkage: Σ_shrunk = (1-α)Σ + α·F, где F = target (diagonal или constant correlation) |
| **Estimation error** | Ошибки в μ и Σ дают нестабильные веса | Регуляризация, resampled efficient frontier, shrinkage estimators |
| **Concentration** | Решение часто даёт угловые портфели (1-2 актива с весом ~100%) | Ограничение w_i ≤ 0.3 (max 30% на актив) |
| **Несовместимость с short** | Long-only ограничение | Quadratic programming (QP) с неравенствами |
| **Overfitting** | На N активах оптимизация N(N+1)/2 параметров ковариации | Shrinkage, factor models (CAPM-based Σ) |

### Оценка для крипты

**Проблема:** Крипто-рынок нестационарен. Ковариационная матрица, посчитанная за 90 дней, может кардинально отличаться от следующих 30 дней. Ожидаемые доходности (μ) — это «ложь» для крипты (мы не знаем будущее).

**Вердикт:** ❌ **Не использовать как primary метод.** Максимум — как компонент для сравнения. Estimation error убивает эффективность.

---

## 3. Black-Litterman Model

### Формула

Комбинирует рыночные равновесные доходности с мнениями инвестора:

```
Приоритет (рыночные веса):  π = δ · Σ · w_mkt

Posterior доходности:  E[R] = [(τΣ)⁻¹ + P'Ω⁻¹P]⁻¹ · [(τΣ)⁻¹π + P'Ω⁻¹Q]

Posterior ковариация:  Σ_BL = Σ + [(τΣ)⁻¹ + P'Ω⁻¹P]⁻¹
```

Где:
- **π** — вектор неявных равновесных избыточных доходностей
- **δ** — коэффициент неприятия риска (~2.5 для рынка)
- **w_mkt** — рыночные капитализационные веса
- **τ** — скаляр неопределённости (~0.05)
- **P** — матрица представлений (K×N)
- **Q** — вектор ожидаемых доходностей по представлениям (K×1)
- **Ω** — диагональная матрица неопределённости представлений: Ω = diag(P(τΣ)P')

### Edge Cases

| Проблема | Решение |
|---|---|
| **Нет w_mkt** (крипта не имеет «капитализационных весов» портфеля) | Использовать equal weight как w_mkt или объём-взвешенные |
| **Нет мнений экспертов** | Не использовать метод — он теряет смысл |
| **Singular Σ** | Shrinkage (как в Markowitz) |
| **Субъективность P и Q** | Автоматизированные views на основе momentum/mean-reversion сигналов |

### Оценка для крипты

**Проблема:** Black-Litterman требует «мнений» (views). Для алгоритмического бота это означает, что нужно автоматически генерировать views из сигналов. Это возможно (например, «BTC вырастет на 5% в следующем месяце с уверенностью 60%»), но добавляет сложность и ещё один источник ошибок.

**Вердикт:** ❌ **Не использовать.** Избыточно сложный, не даёт преимущества над HRP или Risk Parity для алгоритмической торговли.

---

## 4. Risk Parity

### Формула

Цель: каждый актив вносит **равный вклад** в общий риск портфеля.

**Marginal Risk Contribution (MRC):**

```
MRC_i = (Σw)_i / √(w'Σw)

Risk Contribution:  RC_i = w_i · MRC_i

Цель:  RC_i = RC_j  ∀ i,j

Это эквивалентно:  w_i · (Σw)_i = w_j · (Σw)_j
```

**Упрощённая (diagonal) версия** (без учёта корреляций):

```
w_i = (1/σ_i) / Σⱼ(1/σ_j)
```

**Полная версия** (с ковариационной матрицей) — решается итеративно:

```
min  Σᵢ (RC_i - RC_target)²

где RC_target = σ_p / N  (равный вклад)
```

Решение через Sequential Least Squares Programming (SLSQP) или алгоритм Spinu (2013):

```
Инициализация: w⁰ = equal_weight

Итерация k:
  g_i = (Σw^(k))_i / √(w^(k)'Σw^(k))   (MRC_i)
  w^(k+1)_i = w^(k)_i · (target / g_i)^α   (α ∈ [0.5, 1.0])

Повторять до сходимости: ||w^(k+1) - w^(k)|| < ε
```

### Edge Cases

| Проблема | Решение |
|---|---|
| **Singular Σ** | Diagonal approximation (игнорировать корреляции) |
| **Актив с σ ≈ 0** (stablecoin) | w_i → ∞, нужно ограничить max weight = 0.5 |
| **Все активы одинаковой волатильности** | Деградирует до equal weight — это ОК |
| **Отрицательные корреляции** | Полная версия корректно обрабатывает; diagonal — нет |
| **Нестационарность** | Пересчёт каждый период (rolling window) |

### Rust-реализация: Diagonal Risk Parity

```rust
/// Diagonal Risk Parity — простая версия без корреляций.
/// Подходит для MVP и как fallback при singular covariance matrix.
///
/// # Arguments
/// * `volatilities` - слайс годовых волатильностей активов
///
/// # Returns
/// * `Vec<f64>` — веса, суммирующиеся в 1.0
pub fn risk_parity_diagonal(volatilities: &[f64]) -> Vec<f64> {
    let n = volatilities.len();
    assert!(n > 0, "Need at least one asset");
    
    // Обратные волатильности
    let inv_vols: Vec<f64> = volatilities.iter().map(|&v| {
        if v < 1e-10 { 1e10 } else { 1.0 / v }
    }).collect();
    
    let sum_inv: f64 = inv_vols.iter().sum();
    
    inv_vols.iter().map(|&iv| iv / sum_inv).collect()
}

/// Полная Risk Parity с ковариационной матрицей.
/// Использует итеративный алгоритм Spinu (2013).
///
/// # Arguments
/// * `cov` - ковариационная матрица (row-major, n×n)
/// * `n` - количество активов
/// * `max_iter` - максимальное число итераций
/// * `tol` - tolerance для сходимости
///
/// # Returns
/// * `Vec<f64>` — веса Risk Parity
pub fn risk_parity_full(
    cov: &[f64],      // n×n row-major
    n: usize,
    max_iter: usize,
    tol: f64,
) -> Vec<f64> {
    assert_eq!(cov.len(), n * n);
    
    // Инициализация: equal weight
    let mut w: Vec<f64> = vec![1.0 / n as f64; n];
    
    for _iter in 0..max_iter {
        // Σw (матричное умножение)
        let mut sigma_w = vec![0.0; n];
        for i in 0..n {
            for j in 0..n {
                sigma_w[i] += cov[i * n + j] * w[j];
            }
        }
        
        // σ_p = √(w'Σw)
        let sigma_p_sq: f64 = w.iter().zip(sigma_w.iter()).map(|(wi, sw)| wi * sw).sum();
        let sigma_p = sigma_p_sq.sqrt();
        
        if sigma_p < 1e-10 {
            return w; // вырожденный случай
        }
        
        // MRC_i = (Σw)_i / σ_p
        let mrc: Vec<f64> = sigma_w.iter().map(|&sw| sw / sigma_p).collect();
        
        // RC_i = w_i * MRC_i
        let rc: Vec<f64> = w.iter().zip(mrc.iter()).map(|(wi, mi)| wi * mi).collect();
        
        // Target = σ_p / n (равный вклад)
        let target_rc = sigma_p / n as f64;
        
        // Обновление весов: w_new_i = w_i * (target_rc / RC_i)^0.5
        let mut w_new = Vec::with_capacity(n);
        let alpha = 0.5; // damping factor
        
        for i in 0..n {
            let ratio = if rc[i] > 1e-10 { target_rc / rc[i] } else { 1.0 };
            w_new.push(w[i] * ratio.powf(alpha));
        }
        
        // Нормализация
        let sum_w: f64 = w_new.iter().sum();
        for wi in w_new.iter_mut() {
            *wi /= sum_w;
        }
        
        // Проверка сходимости
        let diff: f64 = w_new.iter().zip(w.iter())
            .map(|(a, b)| (a - b).powi(2))
            .sum::<f64>()
            .sqrt();
        
        w = w_new;
        
        if diff < tol {
            break;
        }
    }
    
    w
}
```

---

## 5. Hierarchical Risk Parity (HRP)

### Формула

HRP (López de Prado, 2016) использует иерархическую кластеризацию вместо оптимизации.

**Шаг 1: Квазидиагонализация**

```
1. Вычислить матрицу расстояний: D_ij = √(0.5 * (1 - ρ_ij))
2. Иерархическая кластеризация (Ward linkage)
3. Серийная (quasi-diagonal) переупорядочировка ковариационной матрицы
```

**Шаг 2: Recursive Bisection**

```
procedure HRP(cov, sort_ix):
    weights = ones(N)
    
    // Рекурсивно делим кластеры пополам
    procedure bisect(cluster):
        if |cluster| == 1: return
        
        left  = cluster[0 : |cluster|/2]
        right = cluster[|cluster|/2 : ]
        
        // Вариация каждого подкластера
        var_left  = w_left'  · cov[left,left]  · w_left
        var_right = w_right' · cov[right,right] · w_right
        
        // Аллоцируем пропорционально обратной вариации
        alpha = 1 - var_left / (var_left + var_right)
        
        weights[left]  *= alpha
        weights[right] *= (1 - alpha)
        
        bisect(left)
        bisect(right)
    
    bisect(all_assets)
    return normalize(weights)
```

### Преимущества над Markowitz

| Аспект | Markowitz | HRP |
|---|---|---|
| Singular matrix | ❌ Ломается | ✅ Не требует обращения |
| Estimation error | Катастрофический | Устойчив |
| Concentration | Часто угловой | Диверсифицированный |
| Сложность | O(N³) (обращение) | O(N² log N) (кластеризация) |

### Edge Cases

| Проблема | Решение |
|---|---|
| **Все активы идентичны** (ρ = 1.0) | D = 0, кластеризация вырождена → fallback к equal weight |
| **Недостаточно данных** для корреляции | Minimum window = 2N (где N = кол-во активов) |
| **Одиночный outlier** ломает кластеризацию | Robust correlation (Kendall tau вместо Pearson) |

### Rust-реализация

```rust
use std::collections::HashMap;

/// Hierarchical Risk Parity (HRP) по López de Prado.
///
/// # Arguments
/// * `cov` - ковариационная матрица (row-major, n×n)
/// * `n` - количество активов
///
/// # Returns
/// * `Vec<f64>` — веса HRP, суммирующиеся в 1.0
pub fn hierarchical_risk_parity(cov: &[f64], n: usize) -> Vec<f64> {
    assert_eq!(cov.len(), n * n);
    
    // Шаг 1: Корреляционная матрица
    let corr = covariance_to_correlation(cov, n);
    
    // Шаг 2: Матрица расстояний
    let mut dist = vec![0.0f64; n * n];
    for i in 0..n {
        for j in 0..n {
            dist[i * n + j] = (0.5 * (1.0 - corr[i * n + j])).max(0.0).sqrt();
        }
    }
    
    // Шаг 3: Иерархическая кластеризация (упрощённый single linkage)
    let sort_ix = quasi_diagonalize(&dist, n);
    
    // Шаг 4: Recursive bisection
    let weights = recursive_bisection(cov, n, &sort_ix);
    
    weights
}

/// Конвертация ковариации в корреляцию
fn covariance_to_correlation(cov: &[f64], n: usize) -> Vec<f64> {
    let mut corr = vec![0.0f64; n * n];
    let stds: Vec<f64> = (0..n).map(|i| cov[i * n + i].sqrt()).collect();
    
    for i in 0..n {
        for j in 0..n {
            if stds[i] > 1e-10 && stds[j] > 1e-10 {
                corr[i * n + j] = cov[i * n + j] / (stds[i] * stds[j]);
                // Clamp to [-1, 1]
                corr[i * n + j] = corr[i * n + j].max(-1.0).min(1.0);
            } else {
                corr[i * n + j] = if i == j { 1.0 } else { 0.0 };
            }
        }
    }
    corr
}

/// Quasi-diagonalization: упорядочивает активы так, что похожие рядом.
/// Использует агломеративную кластеризацию.
fn quasi_diagonalize(dist: &[f64], n: usize) -> Vec<usize> {
    if n <= 1 {
        return (0..n).collect();
    }
    
    // Иерархическая кластеризация (min linkage, упрощённая)
    // Для каждой пары (i,j) находим расстояние
    let mut clusters: Vec<Vec<usize>> = (0..n).map(|i| vec![i]).collect();
    
    while clusters.len() > 1 {
        // Найти ближайшие кластеры
        let mut min_dist = f64::MAX;
        let mut min_i = 0;
        let mut min_j = 1;
        
        for i in 0..clusters.len() {
            for j in (i + 1)..clusters.len() {
                // Average linkage distance
                let mut d = 0.0;
                let mut count = 0;
                for &a in &clusters[i] {
                    for &b in &clusters[j] {
                        d += dist[a * n + b];
                        count += 1;
                    }
                }
                d /= count as f64;
                
                if d < min_dist {
                    min_dist = d;
                    min_i = i;
                    min_j = j;
                }
            }
        }
        
        // Объединить кластеры
        let mut merged = clusters[min_i].clone();
        merged.extend(clusters[min_j].clone());
        
        // Удалить в обратном порядке индексов
        if min_i < min_j {
            clusters.remove(min_j);
            clusters.remove(min_i);
        } else {
            clusters.remove(min_i);
            clusters.remove(min_j);
        }
        clusters.push(merged);
    }
    
    clusters.pop().unwrap_or_default()
}

/// Recursive bisection для HRP.
fn recursive_bisection(cov: &[f64], n: usize, sort_ix: &[usize]) -> Vec<f64> {
    let mut weights = vec![1.0f64; n];
    
    // Рекурсивный обход кластеров
    fn bisect(
        cov: &[f64],
        n: usize,
        sort_ix: &[usize],
        weights: &mut [f64],
        start: usize,
        end: usize,
    ) {
        if end - start <= 1 {
            return;
        }
        
        let mid = (start + end) / 2;
        
        // Вариация левой половины
        let left_indices: Vec<usize> = (start..mid).map(|i| sort_ix[i]).collect();
        let right_indices: Vec<usize> = (mid..end).map(|i| sort_ix[i]).collect();
        
        let var_left = cluster_variance(cov, n, &left_indices, weights);
        let var_right = cluster_variance(cov, n, &right_indices, weights);
        
        // Аллокация пропорционально обратной вариации
        let total_var = var_left + var_right;
        let alpha = if total_var > 1e-10 {
            1.0 - var_left / total_var
        } else {
            0.5
        };
        
        // Применить веса
        for &idx in &left_indices {
            weights[idx] *= alpha;
        }
        for &idx in &right_indices {
            weights[idx] *= (1.0 - alpha);
        }
        
        bisect(cov, n, sort_ix, weights, start, mid);
        bisect(cov, n, sort_ix, weights, mid, end);
    }
    
    bisect(cov, n, sort_ix, &mut weights, 0, n);
    
    // Нормализация
    let sum: f64 = weights.iter().sum();
    if sum > 1e-10 {
        for w in weights.iter_mut() {
            *w /= sum;
        }
    }
    
    weights
}

/// Дисперсия кластера (взвешенная)
fn cluster_variance(
    cov: &[f64],
    n: usize,
    indices: &[usize],
    weights: &[f64],
) -> f64 {
    let k = indices.len();
    if k == 0 {
        return 0.0;
    }
    
    // Нормализованные веса внутри кластера
    let w_sum: f64 = indices.iter().map(|&i| weights[i]).sum();
    if w_sum < 1e-10 {
        return 0.0;
    }
    
    let cluster_weights: Vec<f64> = indices.iter()
        .map(|&i| weights[i] / w_sum)
        .collect();
    
    // var = w_c' · Σ_c · w_c
    let mut var = 0.0;
    for (ci, &i) in indices.iter().enumerate() {
        for (cj, &j) in indices.iter().enumerate() {
            var += cluster_weights[ci] * cluster_weights[cj] * cov[i * n + j];
        }
    }
    
    var
}
```

---

## 6. Minimum Variance Portfolio

### Формула

Находим портфель с **минимальной дисперсией** без ограничения на доходность:

```
min  w'Σw
 s.t. w'1 = 1
      w ≥ 0  (long-only)
```

**Аналитическое решение (без long-only):**

```
w* = Σ⁻¹·1 / (1'Σ⁻¹·1)
```

**Long-only версия** — QP (Quadratic Programming):

```
min  0.5 · w'Σw
 s.t. w'1 = 1
      w ≥ 0
```

### Характеристики

- **Склонность к концентрации**: часто даёт вес ~80% на наименее волатильный актив
- **Низкая доходность**: минимизация риска часто означает минимизацию дохода
- **Устойчивость**: лучше Markowitz, но всё равно зависит от Σ

### Edge Cases

| Проблема | Решение |
|---|---|
| **Singular Σ** | Ledoit-Wolf shrinkage |
| **Один актив с σ ≈ 0** | Весь вес на него → ограничить max_weight = 0.4 |
| **Все активы одинаковой vol** | Деградирует до equal weight |

### Rust-реализация

```rust
/// Minimum Variance Portfolio (analytical, без long-only).
/// При singular matrix используется shrinkage.
pub fn minimum_variance(cov: &[f64], n: usize) -> Vec<f64> {
    // Инвертировать ковариационную матрицу
    let inv_cov = invert_matrix(cov, n);
    
    // w = Σ⁻¹·1 / (1'Σ⁻¹·1)
    let mut inv_cov_ones = vec![0.0f64; n];
    for i in 0..n {
        for j in 0..n {
            inv_cov_ones[i] += inv_cov[i * n + j];
        }
    }
    
    let sum: f64 = inv_cov_ones.iter().sum();
    
    if sum.abs() < 1e-10 {
        return vec![1.0 / n as f64; n]; // fallback to equal weight
    }
    
    inv_cov_ones.iter().map(|&x| x / sum).collect()
}

/// Minimum Variance с long-only через простой projected gradient descent.
pub fn minimum_variance_long_only(
    cov: &[f64],
    n: usize,
    max_weight: f64,
    max_iter: usize,
) -> Vec<f64> {
    let mut w = vec![1.0 / n as f64; n];
    let lr = 0.01;
    
    for _ in 0..max_iter {
        // Градиент: ∇ = 2·Σ·w
        let mut grad = vec![0.0f64; n];
        for i in 0..n {
            for j in 0..n {
                grad[i] += 2.0 * cov[i * n + j] * w[j];
            }
        }
        
        // Шаг градиентного спуска
        for i in 0..n {
            w[i] -= lr * grad[i];
        }
        
        // Проекция: w_i ≥ 0, w_i ≤ max_weight
        for wi in w.iter_mut() {
            *wi = wi.max(0.0).min(max_weight);
        }
        
        // Нормализация: Σw = 1
        let sum: f64 = w.iter().sum();
        if sum > 1e-10 {
            for wi in w.iter_mut() {
                *wi /= sum;
            }
        }
    }
    
    w
}

/// Обращение матрицы методом Гаусса-Жордана.
/// Возвращает identity при singular matrix.
fn invert_matrix(mat: &[f64], n: usize) -> Vec<f64> {
    // Расширенная матрица [A | I]
    let mut aug = vec![0.0f64; n * 2 * n];
    for i in 0..n {
        for j in 0..n {
            aug[i * 2 * n + j] = mat[i * n + j];
        }
        aug[i * 2 * n + n + i] = 1.0;
    }
    
    for col in 0..n {
        // Pivot
        let mut max_row = col;
        for row in (col + 1)..n {
            if aug[row * 2 * n + col].abs() > aug[max_row * 2 * n + col].abs() {
                max_row = row;
            }
        }
        
        // Swap
        for j in 0..(2 * n) {
            let tmp = aug[col * 2 * n + j];
            aug[col * 2 * n + j] = aug[max_row * 2 * n + j];
            aug[max_row * 2 * n + j] = tmp;
        }
        
        let pivot = aug[col * 2 * n + col];
        if pivot.abs() < 1e-12 {
            // Singular — return identity
            return (0..n * n).map(|i| if i / n == i % n { 1.0 } else { 0.0 }).collect();
        }
        
        // Normalize row
        for j in 0..(2 * n) {
            aug[col * 2 * n + j] /= pivot;
        }
        
        // Eliminate other rows
        for row in 0..n {
            if row == col { continue; }
            let factor = aug[row * 2 * n + col];
            for j in 0..(2 * n) {
                aug[row * 2 * n + j] -= factor * aug[col * 2 * n + j];
            }
        }
    }
    
    // Извлечь правую часть
    let mut result = vec![0.0f64; n * n];
    for i in 0..n {
        for j in 0..n {
            result[i * n + j] = aug[i * 2 * n + n + j];
        }
    }
    
    result
}
```

---

## 7. Maximum Sharpe Portfolio

### Формула

Находим портфель с **максимальным коэффициентом Шарпа**:

```
max  (w'μ - r_f) / √(w'Σw)
 s.t. w'1 = 1
      w ≥ 0
```

**Аналитическое решение (без long-only, с r_f = 0):**

```
w* = Σ⁻¹μ / (1'Σ⁻¹μ)
```

Это эквивалентно: каждый вес пропорционален «качеству» актива (μ/σ), скорректированной на корреляции.

### Edge Cases

| Проблема | Решение |
|---|---|
| **Singular Σ** | Shrinkage |
| **Все μ ≤ r_f** | Нет положительного Sharpe → fallback к minimum variance |
| **Очень высокий Sharpe на одном активе** | Концентрация → ограничить max_weight |
| **Negative expected returns** | Метод не определён (деление на отрицательное) |

### Оценка для крипты

**Проблема:** Ожидаемая доходность (μ) — самый ненадёжный параметр. На крипте историческая доходность — плохой предиктор будущей.

**Вердикт:** ❌ **Не использовать как primary.** Как secondary — можно (если μ берётся из фундаментальных сигналов, а не исторической средней).

### Rust-реализация

```rust
/// Maximum Sharpe Portfolio (analytical).
pub fn max_sharpe(
    expected_returns: &[f64],
    cov: &[f64],
    n: usize,
    risk_free_rate: f64,
) -> Vec<f64> {
    let inv_cov = invert_matrix(cov, n);
    
    // excess returns
    let excess: Vec<f64> = expected_returns.iter().map(|&r| r - risk_free_rate).collect();
    
    // Σ⁻¹ · (μ - r_f)
    let mut inv_cov_excess = vec![0.0f64; n];
    for i in 0..n {
        for j in 0..n {
            inv_cov_excess[i] += inv_cov[i * n + j] * excess[j];
        }
    }
    
    let sum: f64 = inv_cov_excess.iter().sum();
    
    if sum.abs() < 1e-10 {
        return vec![1.0 / n as f64; n]; // fallback
    }
    
    // w = Σ⁻¹μ / (1'Σ⁻¹μ)
    let mut w: Vec<f64> = inv_cov_excess.iter().map(|&x| x / sum).collect();
    
    // Clamp negative weights (long-only approximation)
    for wi in w.iter_mut() {
        *wi = wi.max(0.0);
    }
    
    // Renormalize
    let total: f64 = w.iter().sum();
    if total > 1e-10 {
        for wi in w.iter_mut() {
            *wi /= total;
        }
    }
    
    w
}
```

---

## 8. Equal Weight Portfolio

### Формула

```
w_i = 1/N  ∀ i

σ²_p = (1/N²) · Σᵢ Σⱼ σᵢⱼ
     = (1/N²) · (Σᵢ σᵢ² + Σᵢ≠ⱼ σᵢⱼ)
     = σ̄²/N + (N-1)/N · σ̄_cov
```

Где σ̄² — средняя дисперсия, σ̄_cov — средняя ковариация.

### Почему Equal Weight хорошо работает

DeMiguel, Garlappi & Uppal (2009) показали: **1/N портфель побеждает оптимизированные портфели** по Sharpe, turnover и certainty-equivalent return в 7 из 11 эмпирических датасетов.

Причины:
1. **Zero estimation error** — не оценивает ни μ, ни Σ
2. **Implicit diversification** — автоматически размазывает риск
3. **Low turnover** — нет ребалансировки параметров

### Edge Cases

| Проблема | Решение |
|---|---|
| **Разная ликвидность активов** | Не учитывается → проблема для крипты (BTC vs малые альты) |
| **Разная волатильность** | BTC (σ ~60%) и USDT (σ ~0.1%) будут иметь одинаковый вес — абсурд | 
| **Невозможность купить дробь** | Для мелких альтов нужно округление |

### Оценка для крипты

**Вердикт:** ⚠️ **Хороший baseline, но не primary.** Не учитывает волатильность, что критично для крипты. Хорош для сравнения (benchmark).

---

## 9. Inverse Volatility Portfolio

### Формула

```
w_i = (1/σᵢ) / Σⱼ(1/σⱼ)

где σᵢ — стандартное отклонение доходности актива i
```

**Расширенная версия** (с half-life decay для более свежих данных):

```
w_i = (1/σᵢ_ewma) / Σⱼ(1/σⱼ_ewma)

σ²_ewma = λ · σ²_prev + (1-λ) · r²_t
λ = exp(-ln(2) / half_life)
```

### Связь с Risk Parity

Inverse Volatility — это **диагональная версия Risk Parity** (без корреляций). При некоррелированных активах (Σ = diag(σᵢ²)) они дают идентичные веса.

### Edge Cases

| Проблема | Решение |
|---|---|
| **Актив с σ ≈ 0** (stablecoin) | w → ∞, clamp max_weight = 0.5 |
| **Коррелированные активы** | Не учитывает → может дать двойной риск на correlated assets |

### Rust-реализация

```rust
/// Inverse Volatility Portfolio.
///
/// # Arguments
/// * `volatilities` - слайс волатильностей (σᵢ)
/// * `max_weight` - максимальный вес на один актив (default: 0.5)
pub fn inverse_volatility(volatilities: &[f64], max_weight: f64) -> Vec<f64> {
    let n = volatilities.len();
    assert!(n > 0);
    
    // 1/σᵢ с защитой от деления на 0
    let mut inv_vol: Vec<f64> = volatilities.iter().map(|&v| {
        if v < 1e-10 { 1e10 } else { 1.0 / v }
    }).collect();
    
    // Clamp max weight
    let raw_sum: f64 = inv_vol.iter().sum();
    for iv in inv_vol.iter_mut() {
        let raw_weight = *iv / raw_sum;
        if raw_weight > max_weight {
            *iv = max_weight / (1.0 - max_weight) * (raw_sum - *iv);
        }
    }
    
    // Renormalize
    let sum: f64 = inv_vol.iter().sum();
    inv_vol.iter().map(|&iv| iv / sum).collect()
}

/// Inverse Volatility с EWMA-волатильностью.
pub fn inverse_volatility_ewma(
    returns: &[Vec<f64>],  // [asset][period]
    half_life: usize,
    max_weight: f64,
) -> Vec<f64> {
    let n = returns.len();
    let lambda = (-(1.0_f64).ln_1p() / half_life as f64).exp();
    // Actually: λ = exp(-ln(2) / half_life) = 2^(-1/half_life)
    let lambda = 2.0_f64.powf(-1.0 / half_life as f64);
    
    let mut ewma_vars = vec![0.0f64; n];
    
    // Инициализация первым значением
    for i in 0..n {
        if !returns[i].is_empty() {
            ewma_vars[i] = returns[i][0].powi(2);
        }
    }
    
    // EWMA обновление
    for t in 1..returns[0].len() {
        for i in 0..n {
            if t < returns[i].len() {
                ewma_vars[i] = lambda * ewma_vars[i] + (1.0 - lambda) * returns[i][t].powi(2);
            }
        }
    }
    
    let vols: Vec<f64> = ewma_vars.iter().map(|&v| v.sqrt()).collect();
    inverse_volatility(&vols, max_weight)
}
```

---

## 10. Kelly Criterion Portfolio

### Формула

**Одиночная ставка (Kelly):**

```
f* = (p · b - q) / b

где:
  f* — оптимальная доля капитала
  p  — вероятность выигрыша
  q  = 1 - p (вероятность проигрыша)
  b  — отношение выигрыша к проигрышу (odds)
```

**Мульти-ассет Kelly:**

```
w* = Σ⁻¹ · μ / (1'Σ⁻¹ · μ)   (тот же, что Maximum Sharpe!)

f* = μ_p / σ²_p = (w'μ) / (w'Σw)
```

**Fractional Kelly (Half-Kelly):**

```
f_half = f* × 0.5
```

### Связь с Maximum Sharpe

Kelly portfolio и Maximum Sharpe portfolio **дают одинаковые пропорции весов** (различаются только масштабом). Kelly определяет и оптимальный leverage.

### Edge Cases

| Проблема | Решение |
|---|---|
| **Negative edge (p·b < q)** | f* < 0 → не торговать |
| **Full Kelly = extreme risk** | Использовать Half-Kelly или Quarter-Kelly |
| **Fat tails (крипта)** | Full Kelly assumes Bernoulli — не применимо |
| **Multiple assets** | Multi-asset Kelly = Max Sharpe (см. выше) |

### Rust-реализация

```rust
/// Single-asset Kelly Criterion.
///
/// # Arguments
/// * `win_rate` — доля прибыльных сделок (0..1)
/// * `avg_win` — средний выигрыш (в процентах, например 0.03 = 3%)
/// * `avg_loss` — средний проигрыш (положительное число, например 0.02 = 2%)
/// * `fraction` — доля Kelly (0.5 для Half-Kelly)
pub fn kelly_single_asset(
    win_rate: f64,
    avg_win: f64,
    avg_loss: f64,
    fraction: f64,
) -> f64 {
    assert!(avg_loss > 0.0, "avg_loss must be positive");
    assert!((0.0..=1.0).contains(&win_rate));
    
    let b = avg_win / avg_loss; // odds ratio
    let q = 1.0 - win_rate;
    
    let kelly = (win_rate * b - q) / b;
    
    // Fractional Kelly
    let f = kelly * fraction;
    
    // Не больше 1.0 (нельзя больше 100% капитала), не меньше 0
    f.max(0.0).min(1.0)
}

/// Multi-asset Kelly (эквивалент Maximum Sharpe).
/// Возвращает оптимальный leverage factor.
pub fn kelly_multi_asset(
    expected_returns: &[f64],
    cov: &[f64],
    n: usize,
    risk_free_rate: f64,
    fraction: f64,
) -> (Vec<f64>, f64) {
    // Оптимальные пропорции (как Max Sharpe)
    let proportions = max_sharpe(expected_returns, cov, n, risk_free_rate);
    
    // Kelly leverage: f = μ_p / σ²_p
    let mut mu_p = 0.0;
    for i in 0..n {
        mu_p += proportions[i] * expected_returns[i];
    }
    mu_p -= risk_free_rate;
    
    let mut sigma2_p = 0.0;
    for i in 0..n {
        for j in 0..n {
            sigma2_p += proportions[i] * proportions[j] * cov[i * n + j];
        }
    }
    
    let leverage = if sigma2_p > 1e-10 {
        (mu_p / sigma2_p * fraction).max(0.0)
    } else {
        0.0
    };
    
    (proportions, leverage)
}
```

---

## 11. Correlation-based Allocation

### Формула

**Принцип:** Выбирать и аллоцировать активы, минимизируя общую корреляцию портфеля.

**Portfolio Diversification Ratio (PDR):**

```
PDR = w'σ / √(w'Σw)

где σ — вектор волатильностей

PDR = 1 → все активы корреляция = 1.0
PDR = √N → все активы некоррелированы
```

**Максимизация PDR:**

```
max  w'σ / √(w'Σw)
 s.t. w'1 = 1
      w ≥ 0
```

**Корреляционный фильтр:**

```
Если corr(A, B) > 0.8 → не открывать обе позиции
                      → или сократить веса вдвое
```

### Edge Cases

| Проблема | Решение |
|---|---|
| **Время-вариантная корреляция** | Rolling window + EWMA |
| **Все пары коррелированы** (крипта в bear market) | Fallback к inverse volatility |
| **Negative корреляция** (BTC vs stablecoin) | Корректно обрабатывается, но может давать leverage |

### Rust-реализация

```rust
/// Максимизация Portfolio Diversification Ratio.
/// Итеративный подход: увеличиваем вес некоррелированных активов.
pub fn correlation_based_allocation(
    cov: &[f64],
    n: usize,
    max_weight: f64,
    max_iter: usize,
) -> Vec<f64> {
    // Волатильности
    let vols: Vec<f64> = (0..n).map(|i| cov[i * n + i].sqrt()).collect();
    
    let mut w = vec![1.0 / n as f64; n];
    let lr = 0.01;
    
    for _ in 0..max_iter {
        // Градиент PDR по w
        // PDR = w'σ / √(w'Σw)
        // ∂PDR/∂w_i = σ_i / √(w'Σw) - (w'σ) · (Σw)_i / (w'Σw)^(3/2)
        
        // w'σ
        let mut w_sigma = 0.0;
        for i in 0..n {
            w_sigma += w[i] * vols[i];
        }
        
        // Σw
        let mut sigma_w = vec![0.0f64; n];
        for i in 0..n {
            for j in 0..n {
                sigma_w[i] += cov[i * n + j] * w[j];
            }
        }
        
        // w'Σw
        let mut w_sigma_w = 0.0;
        for i in 0..n {
            w_sigma_w += w[i] * sigma_w[i];
        }
        let sqrt_wsw = w_sigma_w.sqrt();
        
        if sqrt_wsw < 1e-10 || w_sigma < 1e-10 {
            break;
        }
        
        let denom = w_sigma_w.powf(1.5);
        
        // ∂PDR/∂w_i
        let mut grad = vec![0.0f64; n];
        for i in 0..n {
            grad[i] = vols[i] / sqrt_wsw - w_sigma * sigma_w[i] / denom;
        }
        
        // Gradient ascent (maximize PDR)
        for i in 0..n {
            w[i] += lr * grad[i];
        }
        
        // Project: w ≥ 0, w ≤ max_weight, Σw = 1
        for wi in w.iter_mut() {
            *wi = wi.max(0.0).min(max_weight);
        }
        let sum: f64 = w.iter().sum();
        if sum > 1e-10 {
            for wi in w.iter_mut() {
                *wi /= sum;
            }
        }
    }
    
    w
}

/// Корреляционный фильтр: исключает активы с корреляцией выше порога.
pub fn correlation_filter(
    corr: &[f64],
    n: usize,
    threshold: f64,
) -> Vec<bool> {
    // Строим граф корреляций
    // Greedy: выбираем актив с наибольшей средней некорреляцией,
    // исключаем его коррелированных соседей
    
    let mut included = vec![true; n];
    
    // Считаем среднюю корреляцию каждого актива
    let mut avg_corr = vec![0.0f64; n];
    for i in 0..n {
        for j in 0..n {
            if i != j {
                avg_corr[i] += corr[i * n + j].abs();
            }
        }
        avg_corr[i] /= (n - 1) as f64;
    }
    
    // Сортируем по средней корреляции (ascending = наименее коррелированный первым)
    let mut indices: Vec<usize> = (0..n).collect();
    indices.sort_by(|&a, &b| avg_corr[a].partial_cmp(&avg_corr[b]).unwrap());
    
    let mut selected = vec![false; n];
    
    for &i in &indices {
        if !included[i] { continue; }
        
        // Проверяем, не коррелирован ли с уже выбранным
        let mut dominated = false;
        for j in 0..n {
            if selected[j] && corr[i * n + j] > threshold {
                dominated = true;
                break;
            }
        }
        
        if !dominated {
            selected[i] = true;
        } else {
            included[i] = false;
        }
    }
    
    included
}
```

---

## 12. PCA-based Allocation

### Формула

**Principal Component Analysis на доходностях:**

```
1. R — матрица доходностей (T × N)
2. Центрируем: R_c = R - mean(R)
3. Ковариация: Σ = (1/T) · R_c' · R_c
4. Собственные значения и векторы: Σ · vₖ = λₖ · vₖ
5. λ₁ ≥ λ₂ ≥ ... ≥ λₙ — собственные значения (объяснённая дисперсия)
```

**Использование для аллокации:**

**Вариант 1: Minimum Variance через PCA**

```
w_MVP = vₙ / (1'vₙ)   (последний компонент = минимальная дисперсия)
```

**Вариант 2: Diversification через PC**

```
w_i ∝ 1 / Σₖ (loading_i,k)²    (обратная сумма квадратов нагрузок)
```

**Вариант 3: Risk Allocation по компонентам**

```
Аллоцировать пропорционально PC1 (market factor) vs PC2, PC3 (idiosyncratic)
```

### Edge Cases

| Проблема | Решение |
|---|---|
| **PC1 объясняет >90%** (крипта в bull/bear) | Все активы движутся вместе → PCA бесполезен |
| **Недостаточно наблюдений** (T < N) | Невозможно оценить Σ → использовать shrinkage |
| **Нестабильность PC** | Rolling PCA + проверка стабильности loading vectors |

### Оценка для крипты

**Вердикт:** ⚠️ **Полезен для понимания структуры рынка, но не как primary allocation method.** Если PC1 объясняет >85% (типично для крипты), PCA-based allocation не даёт преимущества над inverse volatility.

### Rust-реализация

```rust
/// PCA-based allocation: минимизация рыночного фактора.
/// Использует power iteration для нахождения последнего PC.
pub fn pca_minimum_variance(cov: &[f64], n: usize) -> Vec<f64> {
    // Находим собственный вектор с наименьшим собственным значением
    // через power iteration на инвертированной матрице (или shift)
    
    // Упрощение: ищем направление минимальной дисперсии
    // через power iteration на (αI - Σ) где α > max eigenvalue
    
    let alpha = estimate_max_eigenvalue(cov, n) * 1.1;
    
    // B = αI - Σ → максимальный собственный вектор B = минимальный Σ
    let mut b = vec![0.0f64; n * n];
    for i in 0..n {
        for j in 0..n {
            b[i * n + j] = if i == j { alpha } else { 0.0 } - cov[i * n + j];
        }
    }
    
    let eigvec = power_iteration(&b, n, 1000, 1e-10);
    
    // w_i = |v_i| (абсолютные значения, т.к. знак произволен)
    let mut w: Vec<f64> = eigvec.iter().map(|&v| v.abs()).collect();
    
    // Нормализация
    let sum: f64 = w.iter().sum();
    if sum > 1e-10 {
        for wi in w.iter_mut() {
            *wi /= sum;
        }
    }
    
    w
}

/// Оценка максимального собственного значения через power iteration.
fn estimate_max_eigenvalue(mat: &[f64], n: usize) -> f64 {
    let eigvec = power_iteration(mat, n, 100, 1e-8);
    
    // λ_max ≈ v'Av / v'v
    let mut av = vec![0.0f64; n];
    for i in 0..n {
        for j in 0..n {
            av[i] += mat[i * n + j] * eigvec[j];
        }
    }
    
    let mut num = 0.0;
    let mut den = 0.0;
    for i in 0..n {
        num += eigvec[i] * av[i];
        den += eigvec[i] * eigvec[i];
    }
    
    if den > 1e-10 { num / den } else { 0.0 }
}

/// Power iteration для нахождения доминирующего собственного вектора.
fn power_iteration(mat: &[f64], n: usize, max_iter: usize, tol: f64) -> Vec<f64> {
    let mut v = vec![1.0 / (n as f64).sqrt(); n];
    
    for _ in 0..max_iter {
        // v_new = A * v
        let mut v_new = vec![0.0f64; n];
        for i in 0..n {
            for j in 0..n {
                v_new[i] += mat[i * n + j] * v[j];
            }
        }
        
        // Нормализация
        let norm: f64 = v_new.iter().map(|&x| x * x).sum::<f64>().sqrt();
        if norm < 1e-15 {
            return v;
        }
        for x in v_new.iter_mut() {
            *x /= norm;
        }
        
        // Проверка сходимости
        let diff: f64 = v_new.iter().zip(v.iter())
            .map(|(a, b)| (a - b).powi(2))
            .sum::<f64>()
            .sqrt();
        
        v = v_new;
        if diff < tol {
            break;
        }
    }
    
    v
}
```

---

## 13. Dynamic Rebalancing

### Методы

#### 13.1 Calendar Rebalancing

```
Ребалансировать в фиксированные интервалы:
- Ежедневно
- Еженедельно
- Ежемесячно

w_target = выбранная стратегия (Risk Parity, HRP, etc.)
w_actual = текущие веса (с учётом изменения цен)

Turnover = Σ|w_actual_i - w_target_i| / 2
```

#### 13.2 Threshold Rebalancing

```
Ребалансировать, если отклонение превышает порог:

|w_actual_i - w_target_i| > threshold  →  ребалансировать

Пороги:
- Conservative: 5%
- Moderate: 10%
- Aggressive: 20%
```

#### 13.3 Volatility-Adjusted Rebalancing

```
Частота ребаланса адаптируется к волатильности:

rebalance_interval = base_interval × (σ_base / σ_current)

Высокая волатильность → чаще ребаланс
Низкая волатильность → реже ребаланс
```

#### 13.4 Cost-Optimized Rebalancing

```
Rebalance если:
  benefit_of_rebalance > transaction_cost × 2

benefit = expected_risk_reduction - current_risk
transaction_cost = commission + slippage + spread
```

### Edge Cases

| Проблема | Решение |
|---|---|
| **Слишком частая ребаланса** → высокие комиссии | Minimum interval (например, 24 часа) |
| **Слишком редкая** → портфель дрейфует | Maximum interval + threshold комбинация |
| **Flash crash** → threshold срабатывает | Cooldown period после ребаланса (min 4 часа) |
| **Slippage при rebalance** | Limit orders, не market; VWAP execution |

### Rust-реализация

```rust
/// Состояние портфеля для принятия решения о ребалансировке.
#[derive(Debug, Clone)]
pub struct PortfolioState {
    pub target_weights: Vec<f64>,   // целевые веса
    pub current_weights: Vec<f64>,  // текущие веса (по рыночной стоимости)
    pub last_rebalance_ts: u64,     // timestamp последней ребалансировки
    pub current_volatility: f64,    // текущая волатильность портфеля
    pub base_volatility: f64,       // базовая (средняя) волатильность
}

/// Конфигурация ребалансировки.
#[derive(Debug, Clone)]
pub struct RebalanceConfig {
    pub threshold: f64,             // порог отклонения (0.05 = 5%)
    pub min_interval_secs: u64,     // минимальный интервал (в секундах)
    pub max_interval_secs: u64,     // максимальный интервал
    pub commission_rate: f64,       // комиссия (0.001 = 0.1%)
    pub min_benefit: f64,           // минимальная выгода для ребаланса
}

/// Результат проверки необходимости ребалансировки.
#[derive(Debug)]
pub enum RebalanceDecision {
    NoRebalance,
    Rebalance {
        target_weights: Vec<f64>,
        estimated_turnover: f64,
        estimated_cost: f64,
    },
}

/// Принятие решения о необходимости ребалансировки.
/// Комбинирует threshold + calendar + cost-optimization.
pub fn should_rebalance(
    state: &PortfolioState,
    config: &RebalanceConfig,
    current_ts: u64,
) -> RebalanceDecision {
    let n = state.target_weights.len();
    assert_eq!(n, state.current_weights.len());
    
    let elapsed = current_ts.saturating_sub(state.last_rebalance_ts);
    
    // 1. Hard minimum interval
    if elapsed < config.min_interval_secs {
        return RebalanceDecision::NoRebalance;
    }
    
    // 2. Проверка отклонения весов
    let mut max_deviation = 0.0f64;
    let mut turnover = 0.0f64;
    
    for i in 0..n {
        let dev = (state.current_weights[i] - state.target_weights[i]).abs();
        max_deviation = max_deviation.max(dev);
        turnover += dev;
    }
    turnover /= 2.0;
    
    // 3. Проверка порога
    let threshold_triggered = max_deviation > config.threshold;
    let max_interval_reached = elapsed >= config.max_interval_secs;
    
    if !threshold_triggered && !max_interval_reached {
        return RebalanceDecision::NoRebalance;
    }
    
    // 4. Cost-benefit analysis
    let estimated_cost = turnover * config.commission_rate * 2.0; // round-trip
    
    // Volatility-adjusted benefit
    let vol_ratio = if state.base_volatility > 1e-10 {
        state.current_volatility / state.base_volatility
    } else {
        1.0
    };
    
    // benefit = risk reduction from rebalancing
    let benefit = max_deviation * vol_ratio;
    
    if benefit < config.min_benefit && !max_interval_reached {
        return RebalanceDecision::NoRebalance;
    }
    
    RebalanceDecision::Rebalance {
        target_weights: state.target_weights.clone(),
        estimated_turnover: turnover,
        estimated_cost,
    }
}

/// Конфигурация по умолчанию для крипты.
impl Default for RebalanceConfig {
    fn default() -> Self {
        Self {
            threshold: 0.10,              // 10% отклонение
            min_interval_secs: 4 * 3600,  // минимум 4 часа
            max_interval_secs: 7 * 24 * 3600, // максимум 7 дней
            commission_rate: 0.001,       // 0.1% taker
            min_benefit: 0.02,            // 2% минимальная выгода
        }
    }
}
```

---

## 14. Crypto-Specific: Корреляция для крипты

### Проблема

Корреляция на крипте **нестационарна**: в bull market все активы коррелированы (ρ ~ 0.8–0.95), в bear market — ещё выше. Статическая корреляционная матрица бесполезна.

### Решения

#### 14.1 Rolling Correlation

```
ρ_AB(t) = corr(r_A[t-W:t], r_B[t-W:t])

W = window size (typical: 30–90 дней для крипты)

Проблема: равные веса всем наблюдениям → лаг при regime change
```

#### 14.2 EWMA Correlation (Exponentially Weighted)

```
Cov_EWMA(t) = λ · Cov_EWMA(t-1) + (1-λ) · r_t · r_t'
ρ_EWMA(t) = Cov_EWMA(t) / (σ_A_EWMA(t) · σ_B_EWMA(t))

λ = 0.94 (RiskMetrics) или 0.97 (для крипты, более медленное затухание)
half_life = -ln(2) / ln(λ)
```

**Rust:**

```rust
/// EWMA covariance matrix estimation.
pub fn ewma_covariance(
    returns: &[Vec<f64>],  // [asset][period]
    lambda: f64,
) -> Vec<f64> {
    let n = returns.len();
    let t = returns[0].len();
    
    // Инициализация: sample covariance
    let mut cov = vec![0.0f64; n * n];
    let init_periods = t.min(20); // используем первые 20 периодов
    
    for i in 0..n {
        for j in 0..n {
            let mut mean_i = 0.0;
            let mut mean_j = 0.0;
            for k in 0..init_periods {
                mean_i += returns[i][k];
                mean_j += returns[j][k];
            }
            mean_i /= init_periods as f64;
            mean_j /= init_periods as f64;
            
            let mut c = 0.0;
            for k in 0..init_periods {
                c += (returns[i][k] - mean_i) * (returns[j][k] - mean_j);
            }
            cov[i * n + j] = c / init_periods as f64;
        }
    }
    
    // EWMA update
    for period in init_periods..t {
        for i in 0..n {
            for j in 0..n {
                cov[i * n + j] = lambda * cov[i * n + j]
                    + (1.0 - lambda) * returns[i][period] * returns[j][period];
            }
        }
    }
    
    cov
}
```

#### 14.3 Dynamic Conditional Correlation (DCC) — Engle (2002)

```
Шаг 1: GARCH(1,1) для каждого актива
  σ²_i(t) = ω_i + α_i · ε²_i(t-1) + β_i · σ²_i(t-1)

Шаг 2: Стандартизованные остатки
  z_i(t) = ε_i(t) / σ_i(t)

Шаг 3: EWMA на z·z'
  Q_t = (1-α-β) · Q̄ + α · z_{t-1} · z'_{t-1} + β · Q_{t-1}

Шаг 4: DCC матрица
  R_t = diag(Q_t)^(-1/2) · Q_t · diag(Q_t)^(-1/2)
```

**Параметры для крипты:**
- α = 0.05 (влияние последнего шока)
- β = 0.90 (.persistence)
- α + β < 1 (stationarity)

**Rust:**

```rust
/// DCC(1,1) estimation для двух активов.
/// Упрощённая версия для N=2 (наиболее частый случай).
pub fn dcc_correlation(
    returns_a: &[f64],
    returns_b: &[f64],
    alpha: f64,
    beta: f64,
) -> Vec<f64> {
    let t = returns_a.len().min(returns_b.len());
    assert!(t > 20);
    
    // Шаг 1: Стандартизация через простую EWMA vol
    let lambda = 0.94;
    let mut var_a = returns_a[0].powi(2);
    let mut var_b = returns_b[0].powi(2);
    
    let mut z_a = vec![0.0f64; t];
    let mut z_b = vec![0.0f64; t];
    
    for i in 0..t {
        var_a = lambda * var_a + (1.0 - lambda) * returns_a[i].powi(2);
        var_b = lambda * var_b + (1.0 - lambda) * returns_b[i].powi(2);
        
        z_a[i] = returns_a[i] / var_a.sqrt().max(1e-10);
        z_b[i] = returns_b[i] / var_b.sqrt().max(1e-10);
    }
    
    // Шаг 2: DCC
    // Q̄ = средняя ковариация z·z' (unconditional)
    let mut q_bar = 0.0;
    let mut q_bar_aa = 0.0;
    let mut q_bar_bb = 0.0;
    for i in 0..t {
        q_bar += z_a[i] * z_b[i];
        q_bar_aa += z_a[i] * z_a[i];
        q_bar_bb += z_b[i] * z_b[i];
    }
    q_bar /= t as f64;
    q_bar_aa /= t as f64;
    q_bar_bb /= t as f64;
    
    // EWMA на Q
    let one_minus_ab = 1.0 - alpha - beta;
    let mut q_ab = q_bar;
    let mut q_aa = q_bar_aa;
    let mut q_bb = q_bar_bb;
    
    let mut correlations = Vec::with_capacity(t);
    
    for i in 0..t {
        q_aa = one_minus_ab * q_bar_aa + alpha * z_a[i].powi(2) + beta * q_aa;
        q_bb = one_minus_ab * q_bar_bb + alpha * z_b[i].powi(2) + beta * q_bb;
        q_ab = one_minus_ab * q_bar + alpha * z_a[i] * z_b[i] + beta * q_ab;
        
        // R_t = Q_t * diag(Q_t)^(-1/2)
        let rho = q_ab / (q_aa.sqrt() * q_bb.sqrt()).max(1e-10);
        correlations.push(rho.max(-1.0).min(1.0));
    }
    
    correlations
}
```

#### 14.4 Сравнение методов корреляции

| Метод | Точность | Скорость | Нестационарность | Рекомендация |
|---|---|---|---|---|
| Rolling Pearson | Средняя | Высокая | ❌ Лаг | Baseline |
| EWMA | Хорошая | Высокая | ⚠️ Частично | ✅ MVP |
| DCC(1,1) | Отличная | Средняя | ✅ Да | ✅ Production |
| Kendall Tau | Устойчивость к outliers | Средняя | ❌ | Для чистки данных |

**Рекомендация:** EWMA для MVP (v0.1-v0.2), DCC для production (v0.3+).

---

## 15. Сравнительная таблица

| Метод | Крипто-пригодность | Сложность | Estimation Error | Concentration | Rebalance Cost | Итого |
|---|---|---|---|---|---|---|
| **Markowitz MVO** | ❌ | Высокая | Катастрофический | Высокая | Средний | 3/10 |
| **Black-Litterman** | ❌ | Очень высокая | Высокий | Средняя | Средний | 2/10 |
| **Risk Parity (full)** | ✅ | Средняя | Низкий | Низкая | Низкий | **8/10** |
| **Risk Parity (diagonal)** | ✅ | Низкая | Минимальный | Низкая | Низкий | **7/10** |
| **HRP** | ✅ | Средняя | Минимальный | Низкая | Низкий | **9/10** |
| **Minimum Variance** | ⚠️ | Средняя | Средний | Высокая | Низкий | 5/10 |
| **Maximum Sharpe** | ❌ | Средняя | Катастрофический | Высокая | Средний | 3/10 |
| **Equal Weight** | ⚠️ | Минимальная | Нулевой | Низкая | Минимальный | 6/10 |
| **Inverse Volatility** | ✅ | Минимальная | Минимальный | Средняя | Низкий | **7/10** |
| **Kelly (Fractional)** | ✅ | Средняя | Средний | Зависит | Низкий | 6/10 |
| **Correlation-based** | ⚠️ | Средняя | Средний | Низкая | Средний | 6/10 |
| **PCA-based** | ⚠️ | Высокая | Средний | Средняя | Средний | 5/10 |

---

## 16. Рекомендация: топ 3

### 🥇 #1: Hierarchical Risk Parity (HRP)

**Почему лучший:**
- Не требует обращения ковариационной матрицы → устойчив к singular Σ
- Не требует оценки ожидаемых доходностей (μ) → нет estimation error
- Автоматически диверсифицирует через кластеризацию
- Учитывает корреляционную структуру (в отличие от diagonal Risk Parity)
- Работает с любым числом активов (5–7 идеально)
- Empirically: HRP ≥ Markowitz по out-of-sample Sharpe (López de Prado, 2016)

**Когда НЕ использовать:**
- Если все активы идентичны (ρ = 1.0) → fallback к inverse volatility

**Для крипты:**
- Использовать Kendall tau вместо Pearson для корреляции (устойчивость к fat tails)
- Rolling window 60-90 дней для ковариационной матрицы
- Пересчёт: еженедельно или при threshold > 10%

### 🥈 #2: Risk Parity (Diagonal — Inverse Volatility)

**Почему второй:**
- Самый простой в реализации и отладке
- Нулевой estimation error (только волатильность, которая оценивается надёжнее корреляции)
- EWMA-волатильность быстро адаптируется к изменению режима
- Diagonal = игнорирует корреляции, что на крипте может быть преимуществом (корреляция нестационарна)
- Perfect fallback для HRP при singular matrix

**Когда использовать вместо HRP:**
- MVP/v0.1 (проще реализовать и отладить)
- Когда корреляционная структура нестабильна
- Как sanity check для HRP

### 🥉 #3: Fractional Kelly (Half-Kelly) + Position Sizing

**Почему третий:**
- Решает другую задачу: не «сколько в каждый актив», а «сколько капитала рисковать»
- Комбинируется с HRP или Risk Parity (HRP даёт пропорции, Kelly даёт масштаб)
- Half-Kelly защищает от чрезмерного leverage на крипте с fat tails
- Уже реализован в risk-модуле бота (см. Research Indicators.md, Модуль 5)

**Использование:**

```
1. HRP → target_weights (пропорции между BTC, ETH, SOL, etc.)
2. Half-Kelly → position_scale (сколько % капитала аллоцировать в портфель)
3. Итого: actual_weight_i = target_weight_i × position_scale
```

### Комбинированная стратегия (production)

```
Аллокация активов:     HRP (с Kendall tau корреляцией)
Fallback:              Inverse Volatility (при singular matrix)
Размер позиции:        Half-Kelly
Ребалансировка:        Threshold (10%) + Max interval (7 дней)
Корреляция:            EWMA (MVP) → DCC (production)
Макс. активов:         5–7
Max weight per asset:  30%
Min weight per asset:  5%
```

---

## 17. Rust-реализация: ядро

### Структуры данных

```rust
/// Конфигурация портфельного менеджера.
#[derive(Debug, Clone)]
pub struct PortfolioConfig {
    /// Метод аллокации
    pub method: AllocationMethod,
    /// Максимальное количество активов
    pub max_assets: usize,
    /// Максимальный вес на один актив
    pub max_weight: f64,
    /// Минимальный вес на один актив (если включён)
    pub min_weight: f64,
    /// Метод оценки корреляции
    pub correlation_method: CorrelationMethod,
    /// Окно для оценки ковариации (в периодах)
    pub covariance_window: usize,
    /// Конфигурация ребалансировки
    pub rebalance: RebalanceConfig,
    /// Доля Kelly для размера позиции
    pub kelly_fraction: f64,
}

#[derive(Debug, Clone, Copy)]
pub enum AllocationMethod {
    HRP,
    RiskParityDiagonal,
    RiskParityFull,
    InverseVolatility,
    MinimumVariance,
    EqualWeight,
}

#[derive(Debug, Clone, Copy)]
pub enum CorrelationMethod {
    Pearson,
    EWMA { lambda: f64 },
    KendallTau,
}

impl Default for PortfolioConfig {
    fn default() -> Self {
        Self {
            method: AllocationMethod::HRP,
            max_assets: 7,
            max_weight: 0.30,
            min_weight: 0.05,
            correlation_method: CorrelationMethod::EWMA { lambda: 0.97 },
            covariance_window: 90,
            rebalance: RebalanceConfig::default(),
            kelly_fraction: 0.5,
        }
    }
}

/// Точка входа: вычисление весов портфеля.
pub fn compute_portfolio_weights(
    returns: &[Vec<f64>],  // [asset][period]
    config: &PortfolioConfig,
) -> Result<Vec<f64>, PortfolioError> {
    let n = returns.len();
    
    if n == 0 {
        return Err(PortfolioError::NoAssets);
    }
    if n > config.max_assets {
        return Err(PortfolioError::TooManyAssets(n, config.max_assets));
    }
    
    // 1. Оценка ковариационной матрицы
    let cov = match config.correlation_method {
        CorrelationMethod::EWMA { lambda } => ewma_covariance(returns, lambda),
        CorrelationMethod::Pearson => sample_covariance(returns),
        CorrelationMethod::KendallTau => kendall_tau_covariance(returns),
    };
    
    // 2. Проверка на singularity
    let is_singular = check_singular(&cov, n);
    
    // 3. Вычисление весов
    let raw_weights = match (config.method, is_singular) {
        // Singular matrix → fallback к простым методам
        (_, true) => {
            let vols = (0..n).map(|i| cov[i * n + i].sqrt()).collect::<Vec<_>>();
            inverse_volatility(&vols, config.max_weight)
        }
        
        (AllocationMethod::HRP, false) => hierarchical_risk_parity(&cov, n),
        (AllocationMethod::RiskParityDiagonal, _) => {
            let vols = (0..n).map(|i| cov[i * n + i].sqrt()).collect::<Vec<_>>();
            risk_parity_diagonal(&vols)
        }
        (AllocationMethod::RiskParityFull, false) => risk_parity_full(&cov, n, 1000, 1e-8),
        (AllocationMethod::InverseVolatility, _) => {
            let vols = (0..n).map(|i| cov[i * n + i].sqrt()).collect::<Vec<_>>();
            inverse_volatility(&vols, config.max_weight)
        }
        (AllocationMethod::MinimumVariance, false) => minimum_variance(&cov, n),
        (AllocationMethod::EqualWeight, _) => vec![1.0 / n as f64; n],
    };
    
    // 4. Clamp weights
    let mut weights = raw_weights;
    for w in weights.iter_mut() {
        *w = w.max(config.min_weight).min(config.max_weight);
    }
    
    // 5. Renormalize
    let sum: f64 = weights.iter().sum();
    if sum > 1e-10 {
        for w in weights.iter_mut() {
            *w /= sum;
        }
    }
    
    // 6. Kelly scaling (если есть данные о доходности)
    let position_scale = compute_kelly_scale(returns, config.kelly_fraction);
    for w in weights.iter_mut() {
        *w *= position_scale;
    }
    
    Ok(weights)
}

/// Вычисление масштаба позиции через Half-Kelly.
fn compute_kelly_scale(returns: &[Vec<f64>], fraction: f64) -> f64 {
    if returns.is_empty() || returns[0].is_empty() {
        return 1.0;
    }
    
    let n = returns.len();
    let t = returns[0].len();
    
    // Средняя доходность портфеля (equal-weighted для оценки)
    let mut mean_return = 0.0;
    let mut var_return = 0.0;
    
    for period in 0..t {
        let mut period_return = 0.0;
        for asset in 0..n {
            if period < returns[asset].len() {
                period_return += returns[asset][period] / n as f64;
            }
        }
        mean_return += period_return;
    }
    mean_return /= t as f64;
    
    for period in 0..t {
        let mut period_return = 0.0;
        for asset in 0..n {
            if period < returns[asset].len() {
                period_return += returns[asset][period] / n as f64;
            }
        }
        var_return += (period_return - mean_return).powi(2);
    }
    var_return /= (t - 1) as f64;
    
    // Kelly leverage = μ / σ²
    if var_return > 1e-10 {
        (mean_return / var_return * fraction).max(0.1).min(1.0)
    } else {
        0.5
    }
}

/// Проверка singularity ковариационной матрицы.
fn check_singular(cov: &[f64], n: usize) -> bool {
    // Быстрая проверка: определитель через LU (упрощённо)
    // Если диагональный элемент очень мал → вероятно singular
    for i in 0..n {
        if cov[i * n + i] < 1e-15 {
            return true;
        }
    }
    
    // Проверка числа обусловленности (упрощённо)
    // cond ≈ max eigenvalue / min eigenvalue
    // Через power iteration
    let max_ev = estimate_max_eigenvalue(cov, n);
    
    // Оценка min через shift
    let alpha = max_ev * 1.01;
    let mut shifted = vec![0.0f64; n * n];
    for i in 0..n {
        for j in 0..n {
            shifted[i * n + j] = if i == j { alpha } else { 0.0 } - cov[i * n + j];
        }
    }
    let max_shifted = estimate_max_eigenvalue(&shifted, n);
    let min_ev = alpha - max_shifted;
    
    if min_ev < 1e-12 {
        return true;
    }
    
    let cond = max_ev / min_ev;
    cond > 1e10 // если число обусловленности > 10^10 → считаем singular
}

/// Ошибки портфельного менеджера.
#[derive(Debug)]
pub enum PortfolioError {
    NoAssets,
    TooManyAssets(usize, usize),  // (requested, max)
    SingularMatrix,
    InsufficientData(usize, usize), // (have, need)
    ConvergenceFailure,
}
```

---

## Итоговая архитектура

```
┌──────────────────────────────────────────────────────┐
│                  Portfolio Manager                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐    ┌──────────────┐                 │
│  │ Correlation  │───▶│ Covariance   │                 │
│  │ Estimator    │    │ Matrix (Σ)   │                 │
│  │ (EWMA/DCC)   │    └──────┬───────┘                 │
│  └─────────────┘           │                         │
│                            ▼                         │
│  ┌──────────────────────────────────────┐            │
│  │         Weight Calculator            │            │
│  │                                      │            │
│  │  ┌────────┐  ┌────────┐  ┌────────┐ │            │
│  │  │  HRP   │  │ InvVol │  │ Equal  │ │            │
│  │  │ (primary)│(fallback)│(baseline)│ │            │
│  │  └────────┘  └────────┘  └────────┘ │            │
│  └──────────────┬───────────────────────┘            │
│                 │                                     │
│                 ▼                                     │
│  ┌──────────────────────────────────────┐            │
│  │        Position Sizer (Kelly)        │            │
│  │  weights × kelly_scale = final       │            │
│  └──────────────┬───────────────────────┘            │
│                 │                                     │
│                 ▼                                     │
│  ┌──────────────────────────────────────┐            │
│  │      Rebalance Controller            │            │
│  │  threshold + calendar + cost-benefit │            │
│  └──────────────────────────────────────┘            │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## References

1. López de Prado, M. (2016). "Building Diversified Portfolios that Outperform Out of Sample." *Journal of Portfolio Management*.
2. DeMiguel, V., Garlappi, L., & Uppal, R. (2009). "Optimal Versus Naive Diversification." *Review of Financial Studies*.
3. Engle, R. (2002). "Dynamic Conditional Correlation." *Journal of Business & Economic Statistics*.
4. Ledoit, O. & Wolf, M. (2004). "A Well-Conditioned Estimator for Large-Dimensional Covariance Matrices." *Journal of Multivariate Analysis*.
5. Spinu, F. (2013). "An Algorithm for Computing Risk Parity Weights." *SSRN*.
6. Kelly, J. L. (1956). "A New Interpretation of Information Rate." *Bell System Technical Journal*.
7. Markowitz, H. (1952). "Portfolio Selection." *Journal of Finance*.

---

*Документ: Агент 19 — Управление портфелем*
*Версия: 1.0*
*Статус: MVP Ready → HRP + Inverse Volatility + Half-Kelly*