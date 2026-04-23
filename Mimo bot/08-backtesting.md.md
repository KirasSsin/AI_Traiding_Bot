
# Модуль 8: Бэктестинг и валидация — RE-RUN

> Компактная спецификация методов валидации, модели проскальзывания и анти-паттернов.  
> Основано на Research Indicators.md (Модуль 8) и MVP Roadmap (v0.2).

---

## 1. Топ-3 метода валидации

### 1.1 Walk-Forward Analysis (WFA)

**Назначение:** единственная защита от overfitting на временных рядах. In-sample оптимизация → out-of-sample верификация.

```
Окно 1: Train [bar_1 … bar_252]       → Test [bar_253 … bar_315]
Окно 2: Train [bar_64 … bar_315]      → Test [bar_316 … bar_378]
Окно 3: Train [bar_127 … bar_378]     → Test [bar_379 … bar_441]
…
```

**Параметры:**

| Параметр | Значение | Комментарий |
|---|---|---|
| Train window | **252 bars** (~10.5 дней на 1H) | Достаточно для сезонности |
| Test window | **63 bars** (~2.6 дней на 1H) | ~25% от train |
| Step size | 63 bars (равен test window) | Non-overlapping тест |
| Optimize | Grid search на train | Параметры стратегии |

**Критерий прохождения:**
```
out_of_sample_Sharpe ≥ 0.5 × in_sample_Sharpe
```
Если соотношение ниже — стратегия переобучена.

**Число окон:** минимум **5** (при 252+63×5 = 567 bars). Для BTC 1H это ~24 дня, что допустимо для MVP.

---

### 1.2 Purged K-Fold Cross-Validation (3 splits)

**Назначение:** устранение data leakage через overlapping holding periods. Стандарт López de Prado.

```
Split 1:  Train [████████░░░░░░░░████████]  Test [░░░░░░░░]
Split 2:  Train [░░░░░░░░████████░░░░░░░░]  Test [████████]
Split 3:  Train [████████████████░░░░░░░░]  Test [░░░░░░░░]
                  ↑ purge zone  ↑ embargo zone
```

**Параметры:**

| Параметр | Значение |
|---|---|
| K (splits) | **3** |
| Embargo | **2 × holding_period** bars после тестового окна |
| Purge | Удаление из train всех баров, чьи holding periods пересекаются с test |

**Embargo формула:**
```
embargo_bars = 2 × avg_holding_period

Примеры (1H таймфрейм):
  avg_holding = 4h  → embargo = 8 bars
  avg_holding = 12h → embargo = 24 bars
  avg_holding = 24h → embargo = 48 bars
```

**Критерий прохождения:**
```
mean(Sharpe_1, Sharpe_2, Sharpe_3) ≥ 1.0
std(Sharpe_1, Sharpe_2, Sharpe_3)  ≤ 0.5   (стабильность)
```

Для production (v0.3+): увеличить до **5 splits**.

---

### 1.3 Monte Carlo Permutation Test

**Назначение:** проверка гипотезы «стратегия лучше случайного входа». Статистическая значимость.

**Алгоритм:**
```
1. Посчитать реальный Sharpe_ratio (S_real) на полном наборе
2. Для i = 1 … 1000:
   a. Перемешать порядок сделок (или знаки доходностей)
   b. Посчитать Sharpe_ratio (S_perm_i)
3. p_value = (count(S_perm_i ≥ S_real) + 1) / 1001
```

**Параметры:**

| Параметр | Значение |
|---|---|
| Permutations | **1 000** |
| Null hypothesis | Случайный порядок сделок |
| Alpha | **0.05** |

**Критерий прохождения:**
```
p_value < 0.05   → стратегия статистически значима
S_real > P95(S_perm)  → эквивалентная формулировка
```

**Вариант для доходностей:** перемешиваем знаки (±) лог-доходностей, пересчитываем equity curve. Более строгий тест.

---

## 2. Модель проскальзывания (Slippage Model)

### 2.1 Формула

```
Slippage = κ × σ_bar × √(Q / V_bar)
```

| Переменная | Описание | Источник |
|---|---|---|
| κ | Эмпирическая константа | **0.1** |
| σ_bar | Волатильность текущего бара | ATR(1) или σ_реализованная |
| Q | Размер ордера (в базовой валюте) | Position size из Kelly |
| V_bar | Объём текущего бара | Из OHLCV |

### 2.2 Применение в бэктесте

```python
def apply_slippage(fill_price: float, side: str,
                   order_qty: float, bar_vol: float,
                   bar_atr: float, kappa: float = 0.1) -> float:
    """
    side: 'buy' → slippage увеличивает цену
          'sell' → slippage уменьшает цену
    """
    slippage_pct = kappa * bar_atr * math.sqrt(order_qty / bar_vol)
    if side == 'buy':
        return fill_price * (1 + slippage_pct)
    else:
        return fill_price * (1 - slippage_pct)
```

### 2.3 Проверки адекватности

| Проверка | Порог |
|---|---|
| Slippage < 0.5% от цены | для ликвидных пар (BTC, ETH) |
| Slippage < 2.0% от цены | для менее ликвидных (SOL, AVAX) |
| При Q → 0 slippage → 0 | граничное условие |
| При V → 0 slippage → ∞ | защита: не торговать при объёме < 10% от среднего |

### 2.4 Модель комиссий (справка)

```
Commission = fill_price × qty × fee_rate

fee_rate = 0.001  (0.1% taker, Binance)
Total_cost = Slippage + Commission
```

---

## 3. Анти-паттерны и защита

### 3.1 Look-Ahead Bias Detection

**Определение:** использование данных из будущего при принятии решения на текущем баре.

**Автоматические проверки:**

| # | Проверка | Метод |
|---|---|---|
| 1 | Индикатор на bar[t] использует только данные ≤ t | Unit test: сравнить output при полном и обрезанном массиве |
| 2 | SL/TP выставляются на bar[t+1], не t | Лог: ордер создан → следующий бар → fill |
| 3 | Цена исполнения = close bar[t+1], не high/low bar[t] | Execution simulator: fill на next open |
| 4 | Нет использования future volatility для текущего SL | Code review: ATR(14) отстаёт на 14 баров |

**Тест-детектор:**
```python
def detect_lookahead(strategy_fn, data: pd.DataFrame) -> bool:
    """Если результат меняется при замене bar[t+1:] на NaN — есть look-ahead."""
    full_result = strategy_fn(data)
    for t in range(len(data)):
        masked = data.copy()
        masked.iloc[t+1:] = np.nan
        truncated_result = strategy_fn(masked)
        if not np.allclose(full_result.iloc[:t+1],
                           truncated_result.iloc[:t+1], equal_nan=True):
            return True  # обнаружен look-ahead
    return False
```

### 3.2 Data Snooping

**Определение:** множественное тестирование на одном наборе данных без коррекции.

**Защита:**

| Мера | Описание |
|---|---|
| Bonferroni correction | alpha_adj = alpha / N_strategies |
| Minimum track record | ≥ **30 сделок** для статистической значимости |
| Deflated Sharpe Ratio | отложен до v0.5 (требует оценку N_tested) |
| Out-of-sample only | Финальная оценка **только** на held-out данных |
| Unique datasets | Разные периоды для генерации идей и финального теста |

### 3.3 Прочие анти-паттерны

| # | Анти-паттерн | Защита |
|---|---|---|
| 1 | Survivorship bias | Включать delisted пары в бэктест |
| 2 | Ignoring fees | Всегда применять commission + slippage |
| 3 | Overfitting params | Walk-forward: out-sample Sharpe ≥ 0.5 × in-sample |
| 4 | Curve fitting | Purged K-Fold: стабильность Sharpe по splits |
| 5 | Short backtest period | Минимум **1 полный рыночный цикл** (bull+bear) |
| 6 | Ignoring regime change | HMM regime detection (v0.3) |
| 7 | Fixed position size | Fractional Kelly, адаптивный sizing |
| 8 | No transaction costs impact | Profit Factor пересчитывается после costs |

---

## 4. Конфигурация (validation section)

```yaml
validation:
  # Walk-Forward
  walk_forward:
    train_bars: 252
    test_bars: 63
    step_bars: 63
    min_splits: 5
    pass_threshold: 0.5   # out_sample / in_sample Sharpe

  # Purged K-Fold
  purged_kfold:
    n_splits: 3
    embargo_multiplier: 2  # × avg_holding_period
    min_train_pct: 0.5

  # Monte Carlo
  monte_carlo:
    n_permutations: 1000
    alpha: 0.05
    method: "sign_flip"    # или "trade_shuffle"

  # Slippage
  slippage:
    model: "sqrt"
    kappa: 0.1
    min_volume_pct: 0.1   # не торговать если volume < 10% от среднего

  # Общие
  min_trades: 30
  min_sharpe: 1.0
  max_drawdown: 0.25
```

---

## 5. Пайплайн валидации (порядок выполнения)

```
1. Event-Driven Backtest
   └─→ полный проход, нет look-ahead
       └─→ базовые метрики (Sharpe, MaxDD, PF)

2. Walk-Forward Analysis (5+ splits)
   └─→ in-sample оптимизация
   └─→ out-of-sample проверка
       └─→ ratio ≥ 0.5?

3. Purged K-Fold (3 splits)
   └─→ purge + embargo
       └─→ стабильность Sharpe по splits?

4. Monte Carlo Permutation (1000 iter)
   └─→ p-value < 0.05?
       └─→ S_real > P95?

5. Anti-pattern Audit
   └─→ look-ahead detector
   └─→ snooping correction
       └─→ PASS / FAIL

6. Final Report
   └─→ все проверки пройдены → стратегия допущена к paper trading
   └─→ любая проверка failed → брак, доработка
```

---

## 6. Минимальные пороги для прохождения

| Метрика | Порог | Комментарий |
|---|---|---|
| Sharpe Ratio | ≥ **1.0** | Risk-adjusted |
| Sortino Ratio | ≥ **1.5** | Downside only |
| Max Drawdown | < **25%** | От депозита |
| Profit Factor | > **1.5** | После costs |
| Win Rate | > **45%** | При R:R = 1:1.5 |
| Num Trades | ≥ **30** | Статистическая значимость |
| WFA ratio | ≥ **0.5** | Out/In sample |
| KFold Sharpe std | ≤ **0.5** | Стабильность |
| MC p-value | < **0.05** | Статистическая значимость |
| Risk of Ruin | < **5%** | Half-Kelly |

---

*Документ: output/08-backtesting.md | Модуль 8 | RE-RUN*
