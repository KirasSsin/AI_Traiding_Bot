---
title: "Donchian runner: эталонный полный прогон WFA через replay_engine"
section: "06-бэктест-и-валидация"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/backtest/donchian_runner.py, src/signalgen/donchian_strategy.py
---

# Donchian runner: эталонный полный прогон WFA через replay_engine

**TL;DR:** `donchian_runner` — это полный экзаменационный конвейер для стратегии пробоя канала Дончиана: загружает реальные свечи, нарезает их на 5 фолдов обучение/тест, прогоняет бэктест на каждом фолде, применяет пять последовательных ворот (Sharpe, MC, n_eff, T5, DSR) и выдаёт JSON-вердикт PASS/FAIL. Это единственный канонический путь через [[replay-engine-bar-by-bar|replay_engine]] для данной стратегии — без перебора параметров и без возможности подглядеть в результат перед регистрацией.

## Простыми словами

Представьте, что вы хотите убедиться, что ваша торговая система действительно работает, а не просто «угадала» прибыль на тех данных, по которым её создавали.

Экзаменатор устроен так:

1. **Делит исторические данные на учёбу и экзамен.** Как если бы студент учился по задачникам прошлых лет (обучающая часть), а потом сдавал совершенно новые задачи (тестовая часть), которых он ещё не видел.
2. **Делает это пять раз подряд** — пять фолдов (отдельных «сессий»), каждый раз сдвигая окно. Это называется [[walk-forward-analysis|walk-forward analysis (WFA)]] — шагающий вперёд анализ.
3. **Собирает все сделки из тестовых частей** и проверяет их через пять независимых ворот. Чтобы получить PASS, стратегия должна пройти **все пять** — как турникет на стадионе: не сработал один — не войдёшь.
4. **Пишет честный JSON-файл** с результатами и завершает работу с кодом 0 (PASS) или 2 (FAIL), чтобы автоматика CI/CD тоже умела «прочитать» итог.

Что такое пробой [[donchian-channel-indicator|канала Дончиана]] (Donchian breakout)? Трейдер Ричард Дончиан придумал следующее правило: если сегодняшняя цена закрытия выше максимумов за последние N свечей — значит, рынок пробил «потолок» диапазона и, возможно, начинается сильный тренд. Бот входит в длинную позицию именно в этот момент. Как эта же логика работает в live-режиме — на странице [[donchian-breakout-strategy]].

## Как это работает у нас

### Шаг 1. Параметры стратегии ЗАФИКСИРОВАНЫ до запуска

Все числа стратегии определены в `DONCHIAN_LONG_ONLY_PARAMS` и **заблокированы** ADR 0054 — менять их без нового архитектурного решения запрещено. Это называется анти-снупинг: нельзя сначала смотреть результат, а потом подбирать параметры под него. (src/signalgen/donchian_strategy.py:33–39)

```python
DONCHIAN_LONG_ONLY_PARAMS: dict[str, object] = {
    "lookback_n": 20,        # окно входа: смотрим максимум за 20 свечей
    "exit_lookback_n": 10,   # окно выхода: смотрим минимум за 10 свечей
    "atr_period": 14,        # период ATR для расчёта волатильности
    "atr_stop_mult": Decimal("2.0"),  # стоп = вход − 2 × ATR
    "signal_side_mode": "long_only",  # только покупки, никаких шортов
}
```

### Шаг 2. Сборка конфига для движка replay

Функция `_build_strategy_config()` упаковывает зафиксированные параметры в словарь, который понимает `replay_engine`. Здесь же задаётся торговое окружение бэктеста. (src/backtest/donchian_runner.py:55–82)

Важный момент: `tp_atr_mult = 1.0e9` — это «фиктивный» тейк-профит в миллиард раз больше ATR. Фактически он никогда не сработает. Стратегия выходит не по тейк-профиту, а по двум другим условиям: канальному выходу или ATR-стопу (см. ниже).

Параметры торгового окружения:

| Параметр | Значение | Что означает |
|---|---|---|
| `initial_balance` | 10 000 USD | стартовый капитал бэктеста |
| `commission_taker` | 0.001 (0.1%) | комиссия за каждую сделку |
| `slippage` | 0.0005 (0.05%) | проскальзывание при исполнении |
| `position_size_pct` | 10% | размер каждой позиции от капитала |
| `max_drawdown_pct` | 50% | максимальная просадка до принудительной остановки |
| `long_only` | True | запрет на продажу в шорт |

### Шаг 3. Загрузка данных

Функция `load_market_data()` читает исторические свечи BTC/USDT 4-часового таймфрейма из файла `data/BTCUSDT_4h.parquet` — бинарного [[parquet-storage|формата Parquet]], похожего на таблицу Excel, но очень быстрого для машинного чтения. По умолчанию берётся диапазон 2023-01-01 — 2026-04-26. Общий модуль загрузки OHLCV с защитой пути и предполётной проверкой качества описан в [[single-symbol-wfa-and-data-loading]]. (src/backtest/donchian_runner.py:103–115)

### Шаг 4. Разрезание на фолды (WindowSplitter + WalkForwardRunner)

`WindowSplitter` нарезает данные на 5 фолдов с такими окнами по умолчанию: (src/backtest/donchian_runner.py:117–124, src/backtest/walk_forward.py:21–59)

- **train_bars = 1000** — 1000 4-часовых свечей (~166 дней) на обучение
- **test_bars = 250** — 250 свечей (~41 день) на тест — данные, которых стратегия «не видела»
- **embargo_bars = 20** — 20 свечей-«карантина» между обучением и тестом, чтобы исключить утечку данных на границе
- **k_folds = 5** — пять повторений

Минимальный объём данных для запуска: train + embargo + 5 × test = 1000 + 20 + 5 × 250 = **2270 баров**. При нехватке данных — немедленная ошибка с пояснением, какого символа коснулась нехватка. (src/backtest/walk_forward.py:48–53, 105–117)

`WalkForwardRunner.run()` для каждого фолда запускает `run_replay` дважды: сначала на обучающем окне (in-sample, IS), потом на тестовом (out-of-sample, OOS). Затем вычисляет соотношение OOS/IS Sharpe для ворот T6. Важно не путать три разных коэффициента Шарпа в системе — это подробно разбирается в [[wfa-reporter-three-sharpe-series]]. (src/backtest/walk_forward.py:119–141)

### Шаг 5. Логика сигналов стратегии (DonchianBreakoutStrategy)

Класс `DonchianBreakoutStrategy` — статeful: он помнит, открыта ли сейчас позиция и по какой цене был вход. Метод `on_bar()` принимает каждую закрытую свечу и решает: войти, выйти или ничего не делать. (src/signalgen/donchian_strategy.py:91–142)

**Правило входа (LONG):** (src/signalgen/donchian_strategy.py:101–120)

```
close(T) > max(high[T-20 : T])  И  текущая позиция = FLAT
```

Простыми словами: цена сегодня выше максимума за последние 20 свечей, и мы пока не в позиции — входим в покупку.

Срез `highs[-(lookback_n + 1):-1]` **не включает текущий бар** — это намеренно, чтобы не сравнивать цену саму с собой (OHLC-инвариант).

**Правило выхода (FLAT):** выходим, если выполнено хотя бы одно из двух условий: (src/signalgen/donchian_strategy.py:122–140)

1. **Канальный выход:** `close(T) < min(low[T-10 : T])` — цена упала ниже минимума последних 10 свечей. Это «Черепаховый» вариант Дончиана: более узкое окно выхода (10) по сравнению с окном входа (20) даёт позиции «пространство для дыхания».
2. **ATR-стоп:** `close(T) < entry_close - 2.0 × ATR(T)` — цена упала более чем на 2 ATR от цены входа. [[atr-indicator|ATR]] (Average True Range — средний истинный диапазон) измеряет волатильность рынка за последние 14 свечей. Если рынок «дышит» на 500 USD, стоп будет на 1000 USD ниже входа.

Важно: приоритет выхода — ATR-стоп проверяется внутри `if channel_exit or atr_stop_exit`, и если оба условия выполнены, код выбирает ATR-стоп (`if atr_stop_exit else`). (src/signalgen/donchian_strategy.py:127–133)

Стратегия использует `talib.ATR()` (через обёртку `indicators.atr()`), а не ручной `wilder_atr()`. Это важно: между ними есть расхождение ~1.4% из-за разного способа инициализации, и подмена нарушила бы антиснупинговый контракт ADR 0054. Разница между двумя версиями ATR и каноническая формула Wilder разобраны в [[wilder-atr-and-stops]]. (src/signalgen/indicators.py:67–81)

ATR-стоп фиксируется по цене входа (`entry_close`), а не по текущей цене. Это статичный стоп, а не плавающий (trailing). Подробнее о разнице live/backtest — в [[wilder-atr-and-stops]].

**Нули в полях Signal:** Donchian не использует EMA/ADX/DI/RSI. Поля `ema_fast`, `ema_slow`, `adx_14`, `plus_di_14`, `minus_di_14`, `rsi_14` заполняются нулями — это zero-placeholder, не ошибка данных. (src/signalgen/donchian_strategy.py:153–154)

### Шаг 6. Сбор сделок из фолдов и MC-тест

После прогона всех пяти фолдов код объединяет сделки из всех тестовых окон в один список. Как DataFrame сделок из replay-пути превращается в список `TradeRecord` для статистики — в [[trade-extractor-and-records]]. (src/backtest/donchian_runner.py:143–166)

MC-тест ([[monte-carlo-permutation|Monte Carlo знакопеременная перестановка]]) проверяет: «А может ли такой результат объясниться случайностью?» Алгоритм 2000 раз случайно переворачивает знаки доходностей (+/-), считает статистику и сравнивает с реальной. P-value вычисляется по формуле Phipson & Smyth: (count + 1) / (N + 1) — минимальное возможное значение 1/2001 ≈ 0.0005, чтобы избежать логически невозможного p=0. (src/backtest/donchian_runner.py:127–135, src/backtest/mc_permutation.py:64–67)

Перед отправкой в функцию MC, `net_pnl` делится на 10 000 (начальный баланс): это переводит абсолютные прибыли/убытки в **доли от капитала** — дробные доходности, подходящие для математики знакового теста. (src/backtest/donchian_runner.py:133–134)

### Шаг 7. DSR — смещённый коэффициент Шарпа

DSR ([[dsr-metric|Deflated Sharpe Ratio]] — смещённый коэффициент Шарпа) — это поправка Бейли и Лопес де Прадо (2014). Обычный [[sharpe-sortino-metrics|коэффициент Шарпа]] завышен, если стратегию тестировали много раз и «победил» лучший вариант. DSR штрафует за это.

В `donchian_runner` используется двухуровневая логика выбора стандартного отклонения (sigma_SR): (src/backtest/donchian_runner.py:197–222)

**Ветка CLASS_SCOPED** (если накоплено ≥ 3 записей стратегий класса `"donchian"` в журнале [[cross-trial-log|`data/cross_trial_sharpes.json`]]):

```python
sigma_sr = trial_log.sigma_sr(strategy_class="donchian")  # только donchian-записи
dsr_info = compute_dsr_with_status(
    trades=trades,
    n_trials=5,                              # N_TRIALS_LOCKED — глобальный счётчик всех попыток
    sigma_sr=sigma_sr,
    annualization_factor=math.sqrt(2191),    # de-annualize sigma_sr к per-trade масштабу
)
```

Почему `annualization_factor=math.sqrt(2191)`? Записи в журнале хранят аннуализированные Sharpe (умноженные на √bars_per_year при расчёте внутри replay_engine). Но `compute_dsr()` считает внутренний Sharpe на «сыром» per-trade уровне. Чтобы они были в одном масштабе, sigma_SR делится на тот же множитель. Это исправление S55 QS-3 (ADR 0071). (src/backtest/donchian_runner.py:207–217, src/analytics/dsr.py:156–157)

**Ветка INSUFFICIENT_CLASS_HISTORY** (< 3 donchian-записей — нет достаточного накопления):

```python
dsr_info = compute_dsr_with_status(trades=trades, n_trials=1)
# n_trials=1 → штраф за множественное тестирование не применяется (честно)
```

Смысл: формула Бейли eq.12 не имеет смысла без sigma_SR (нет данных — нет штрафа, но и нет зачёта). (src/backtest/donchian_runner.py:220–222)

Независимо от ветки, финальный пороговый тест: `dsr_value >= 0.95`. Если не пройден — добавляется в `failed_criteria`. (src/backtest/donchian_runner.py:239–245)

### Шаг 8. Пять конъюнктивных ворот (AND-gates)

Все пять ворот объединены логическим И — PASS только если все пять выполнены. Полное объяснение семейства ворот приёмки и их порогов — в [[acceptance-gates-t1-t6]]. (src/backtest/donchian_runner.py:226–247, src/backtest/walk_forward.py:155–242)

| Ворота | Параметр | Порог | Источник константы |
|---|---|---|---|
| L1 Sharpe per-fold | `SHARPE_THRESHOLD` | ≥ 0.7 | donchian_runner.py:46 |
| L2 MC p-value | `P_THRESHOLD` | ≤ 0.05 | donchian_runner.py:47 |
| L3 n_eff | `N_EFF_THRESHOLD` | ≥ 50 | donchian_runner.py:48 |
| L4 T5 raw floor | `T5_FLOOR` | ≥ 50 | donchian_runner.py:49 |
| L5 DSR | `DSR_THRESHOLD` | ≥ 0.95 | donchian_runner.py:50 |

Ворота L3 и L4 передаются в `evaluate_acceptance_gate()` как опциональные параметры `n_eff_threshold` и `t5_floor` — оба про минимальное число сделок для статистической мощности (см. [[tstat-oos-is-metrics]] о том, почему нужно ≥ 50 сделок). Для одного символа `n_trades_n_eff = n_trades_raw` — корреляционной дефляции нет (один символ — нет межсимвольных корреляций). (src/backtest/donchian_runner.py:232–234)

Ворота L5 (DSR) проверяется **отдельно** после `evaluate_acceptance_gate()` и добавляется к `failed_criteria` вручную — это не ошибка дублирования, а намеренное разделение: DSR требует специальных входных данных (sigma_sr, n_trials), которые `evaluate_acceptance_gate()` не принимает. (src/backtest/donchian_runner.py:238–245)

### Шаг 9. Формирование вердикта и запись JSON

Финальное поле `verdict`: `"PASS"` если `failed_criteria` пуст, иначе `"FAIL"`. Словарь со всеми данными пишется в `data/donchian_backtest_results.json`. Как результаты бэктеста в целом сохраняются в файлы (CSV/JSON/HTML) — в [[reporter-and-artifacts]]. (src/backtest/donchian_runner.py:247, 329)

## Формулы и расчёты

### ATR-стоп

```
stop_price = entry_close − atr_stop_mult × ATR(T)
           = entry_close − 2.0 × ATR(T)
```

Расшифровка: ATR (Average True Range — средний истинный диапазон) — это средний размер ценового движения за 14 свечей. Если ATR = 500 USD, стоп будет на 1000 USD ниже цены входа. Умножитель 2.0 — зафиксирован LOCKED параметром.

Важно: стоп считается от `entry_close` (цена при входе), а не обновляется каждый бар. В бэктесте это статичная цена, она не «тянется» за ростом. (src/signalgen/donchian_strategy.py:124)

### DSR (Deflated Sharpe Ratio)

Формула Бейли и Лопес де Прадо 2014, уравнение 13:

```
DSR = Φ( (SR − SR*) × √(n−1) / √(1 − γ₁·SR + (γ₂−1)/4 · SR²) )
```

Расшифровка:
- `SR` — наш Sharpe (среднее / стандартное отклонение доходностей по сделкам)
- `SR*` — «эталонный» Sharpe с поправкой на то, что мы перебрали N_TRIALS = 5 стратегий
- `γ₁, γ₂` — асимметрия и эксцесс распределения доходностей (неравномерность относительно нормального)
- `n` — число сделок
- `Φ` — функция нормального распределения: DSR интерпретируется как вероятность 0–1

Наш вариант: используется Pearson kurtosis (fisher=False), не excess kurtosis — это прямо соответствует оригинальному уравнению Bailey 2014. (src/analytics/dsr.py:125, 168)

`compute_dsr_with_status()` автоматически возвращает статус: INSUFFICIENT_TRADES (< 10 сделок — DSR=NaN), UNDERPOWERED (10–29 сделок), GATE_ELIGIBLE (≥ 30 сделок). (src/analytics/dsr.py:199–211)

### MC sign-flip p-value

```
p = (count_extreme + 1) / (n_iterations + 1)
```

где `count_extreme` = число из 2000 перестановок, где |mean(permuted)| ≥ |mean(observed)|. Формула Phipson & Smyth (2010) добавляет +1 в числитель и знаменатель — это математически корректно при конечном числе перестановок и исключает невозможное p=0. (src/backtest/mc_permutation.py:64–67)

## Примеры / сценарии

### Сценарий A: PASS (все ворота пройдены)

Представим, что на BTCUSDT 4H за период 2023–2026 стратегия показала:

- 5 из 5 фолдов: OOS/IS Sharpe ≥ 0.7 → L1 пройдена
- MC p-value = 0.0035 ≤ 0.05 → L2 пройдена
- 87 сделок OOS ≥ 50 → L3 и L4 пройдены
- DSR = 0.97 ≥ 0.95 (CLASS_SCOPED с 4 donchian-записями) → L5 пройдена

Результат в JSON:
```json
{
  "verdict": "PASS",
  "failed_criteria": [],
  "dsr": 0.97,
  "dsr_status": "GATE_ELIGIBLE",
  "n_trials_counter": 5
}
```
Код возврата CLI: **0**.

### Сценарий B: FAIL — недостаточно сделок

Если в тестовых окнах набралось только 35 сделок OOS (< 50):

```json
{
  "verdict": "FAIL",
  "failed_criteria": ["n_eff_threshold", "t5_floor"],
  "n_trades_raw": 35
}
```

Почему проваливаются **две** ворота, а не одна? Потому что `N_EFF_THRESHOLD = 50` и `T5_FLOOR = 50` — одинаковые пороги, а для одного символа `n_trades_n_eff = n_trades_raw = 35`. Оба условия нарушены, оба попадают в `failed_criteria`. Порядок: L3 (`n_eff_threshold`) проверяется первым в `evaluate_acceptance_gate()`, L4 (`t5_floor`) — вторым. (src/backtest/walk_forward.py:204–212, src/backtest/donchian_runner.py:48–49)

Код возврата CLI: **2**.

### Сценарий C: FAIL — новая стратегия без истории (INSUFFICIENT_CLASS_HISTORY)

Если в `data/cross_trial_sharpes.json` нет ни одной donchian-записи, `sigma_sr()` возвращает `None`. Код падает в ветку `n_trials=1`:

```json
{
  "dsr_status": "GATE_ELIGIBLE",
  "dsr": 0.91,
  "sigma_sr_cross_trial": null,
  "failed_criteria": ["dsr_threshold"]
}
```

Подробнее о механизме кумулятивной дефляции — в [[deflated-sharpe-ratio]].

### Сценарий D: запуск через CLI

```bash
.venv/bin/python -m src.backtest.donchian_runner \
  --input data/BTCUSDT_4h.parquet \
  --start 2023-01-01 \
  --end 2026-04-26 \
  --bars-per-year 2191 \
  --wfa-train 1000 \
  --wfa-test 250
```

По умолчанию результат пишется в `data/donchian_backtest_results.json`. Параметры `--wfa-folds 5` и `--wfa-embargo 20` можно не указывать — они уже выставлены по умолчанию. (src/backtest/donchian_runner.py:299–312)

Почему `--bars-per-year 2191`? 4-часовой таймфрейм даёт 6 свечей в сутки × 365.25 = 2191. Это семейство 365.25 (с учётом високосных лет), совпадающее с расчётом в `atr_breakout_runner` (см. [[06-бэктест-и-валидация/atr-breakout-strategy|ATR breakout]]) и `volume_breakout_runner` (см. [[06-бэктест-и-валидация/volume-breakout-strategy|Volume breakout]]). (src/backtest/donchian_runner.py:306)

## Подводные камни / что важно понимать

**1. «Отдельный путь» от research-ядра.** `donchian_runner` использует `replay_engine` (событийный бар-за-баром бэктест) — это канонический production-путь. Research-ядро (`research_wfa`, векторный бэктест) — отдельная система для быстрого исследования. Страница [[research-kernel-execution-model]] описывает разницу.

**2. N_TRIALS_LOCKED = 5 — это глобальный, не per-run счётчик.** Пять попыток накопились за несколько спринтов (S13, S15, S17, S22, S35). Каждый новый прогон donchian_runner НЕ меняет N_TRIALS_LOCKED — этот счётчик меняется только решением нового ADR. (src/backtest/donchian_runner.py:51)

**3. `donchian_runner` не вызывает `append_trial()`.** Он читает журнал `data/cross_trial_sharpes.json` через `CrossTrialLog.sigma_sr()`, но сам не пишет туда новую запись. Это делает `_cmd_wfa` в `research_wfa.py` — команда [[wfa-validation-command|`wfa`]]. Таким образом, donchian_runner — «читатель», а не «писатель» истории испытаний. (src/backtest/donchian_runner.py:197–198)

**4. Зафиксированные параметры — анти-снупинг.** Если вы «улучшите» `lookback_n` с 20 на 15 потому что так получилась лучше статистика — вы нарушаете контракт ADR 0054. Правильный путь: завести новый ADR, обнулить N_TRIALS_LOCKED или зарегистрировать новую стратегию. Смотри [[acceptance-gates-t1-t6]] — там объяснены ворота и их мотивация.

**5. Статичный стоп в бэктесте, плавающий в live.** В бэктесте стоп считается как `entry_close − 2.0 × ATR(T)` при входе и больше не обновляется. В live-режиме `atr_stop_curr` пересчитывается каждый бар. Это намеренное расхождение: бэктест максимально консервативен. Подробнее — в [[wilder-atr-and-stops]].

**6. Порядок проверки ворот влияет на `failed_criteria`.** L3/L4 проверяются первыми в `evaluate_acceptance_gate()`, L1/L2 — после. DSR-ворота (L5) добавляется последней, вне функции. Сами имена (`n_eff_threshold`, `t5_floor`, `sharpe_gate`, `mc_gate`, `dsr_threshold`) — это строки-ключи в `failed_criteria` списке JSON. (src/backtest/walk_forward.py:193–224)

**7. Блок-bootstrap — только диагностика, не ворота.** В `mc_permutation.py` есть функция `block_bootstrap_p_value()`, но она не используется в `donchian_runner`. Единственная MC-ворота — `sign_flip_p_value()`. (src/backtest/mc_permutation.py:70–117)

**8. Минимум данных: 2270 баров.** Если файл parquet содержит меньше — `WalkForwardRunner` поднимает `ValueError` с чётким пояснением. Это не тихий сбой. (src/backtest/walk_forward.py:105–117)

## Связанные документы

**Стратегия и её индикаторы (что прогоняется):**
- [[donchian-breakout-strategy]] — логика on_bar стратегии в live-режиме (угол 02: как стратегия работает в реальном времени)
- [[donchian-channel-indicator]] — сам индикатор: скользящий максимум/минимум за N свечей, на котором строится пробой
- [[atr-indicator]] — что такое True Range и ATR, из которого считается ATR-стоп 2.0×
- [[wilder-atr-and-stops]] — каноническая формула Wilder ATR и почему talib.ATR() vs wilder_atr() дают расхождение ~1.4%
- [[technical-indicators]] — справочник: что вычисляет каждый индикатор (EMA/RSI/ATR/ADX/BB)
- [[indicators-and-signals]] — как из индикаторов рождается решение о входе/выходе

**Механизм исполнения (как считается бэктест):**
- [[replay-engine-bar-by-bar]] — движок, который выполняет посделочный бэктест внутри каждого фолда (предпосылка)
- [[replay-engine-metrics]] — где считается исходный Шарп и прочие метрики до поправок
- [[trade-extractor-and-records]] — как DataFrame сделок превращается в TradeRecord для DSR
- [[bar-model]] — структура свечи OHLCV и правила валидации (вход движка)
- [[parquet-storage]] — формат Parquet и целостность файла с историческими свечами
- [[single-symbol-wfa-and-data-loading]] — загрузка OHLCV одного символа + предполётная проверка качества

**Валидация: WFA и ворота приёмки (для чего всё это):**
- [[walk-forward-analysis]] — принцип WFA и WindowSplitter подробно
- [[acceptance-gates-t1-t6]] — объяснение каждого из шести ворот T1-T6 и их порогов
- [[wfa-reporter-three-sharpe-series]] — три РАЗНЫХ коэффициента Шарпа (IS, OOS, OOS/IS) и что каждый значит
- [[what-is-backtest-overview]] — что такое бэктест и карта всего раздела 06

**Статистические метрики ворот:**
- [[deflated-sharpe-ratio]] — математика DSR, sigma_SR и N_trials (близнец в разделе валидации)
- [[dsr-metric]] — технический близнец DSR в разделе 03 (формула Bailey, kurtosis, статусы)
- [[sharpe-sortino-metrics]] — базовый коэффициент Шарпа, который DSR корректирует (ворота L1)
- [[cross-trial-log]] — журнал sigma_SR и история Sharpe по всем прогонам (вход ветки CLASS_SCOPED)
- [[monte-carlo-permutation]] — знаковый тест и формула Phipson & Smyth (ворота L2)
- [[mc-permutation-test]] — тот же MC-тест в разделе 03 (что такое permutation test)
- [[tstat-oos-is-metrics]] — t-статистика и почему нужно ≥ 50 сделок (ворота L3 n_eff / L4 T5)

**Применение и CLI:**
- [[wfa-validation-command]] — команда `wfa` (`_cmd_wfa`), которая пишет запись в журнал испытаний (donchian_runner только читает)
- [[reporter-and-artifacts]] — запись результатов прогона в файлы (CSV/JSON/HTML)

**Альтернативные и контрастные модели исполнения:**
- [[research-kernel-execution-model]] — ВТОРАЯ система (`_backtest_single`), которую используют ДРУГИЕ пробои; Donchian идёт через replay_engine (контраст)
- [[vector-backtest-fast-approximation]] — быстрый безцикловый движок для грубой оценки (контраст bar-by-bar)
- [[06-бэктест-и-валидация/atr-breakout-strategy]] — стратегия-сосед: тот же bars_per_year=2191, но research-ядро
- [[06-бэктест-и-валидация/volume-breakout-strategy]] — стратегия-сосед: пробой канала + подтверждение объёмом
- [[kronos-exploratory-runner]] — контраст: разведочный прогон БЕЗ ворот (donchian_runner — с пятью воротами)

За техническими деталями двухуровневого скоупинга sigma_SR → `llm-wiki/wiki/project/components/cross-trial-log.md`
