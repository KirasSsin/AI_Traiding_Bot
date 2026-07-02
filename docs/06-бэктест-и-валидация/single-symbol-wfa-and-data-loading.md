---
title: "Загрузка данных и WFA для одного символа (data_loading)"
section: "06-бэктест-и-валидация"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/backtest/data_loading.py, src/backtest/data_collector.py
---

# Загрузка данных и WFA для одного символа (data_loading)

**TL;DR:** `load_ohlcv` достаёт исторические свечи из файла на диске и проверяет их качество, а `run_wfa_single_symbol` запускает поверх этих данных полный walk-forward анализ с Monte-Carlo тестом — всё вместе это «пусковой механизм» бэктеста для одного торгового символа.

---

## Простыми словами

Прежде чем проверить, работает ли торговая стратегия, нужно решить две задачи:

**Задача 1 — достать данные.** Бот хранит исторические свечи (каждая свеча = цена открытия, максимум, минимум, закрытие и объём за один промежуток времени — час, четыре часа и т.д.) в специальном файле на диске. Этот файл называется [[parquet-storage|Parquet]] — это как Excel-таблица, но сжатая и оптимизированная для быстрого чтения. Функция `load_ohlcv` достаёт нужный файл по имени символа (например, «BTCUSDT») и интервалу, проверяет, не испорчен ли файл, и отдаёт таблицу свечей.

**Задача 2 — запустить бэктест.** Функция `run_wfa_single_symbol` — это высокоуровневая «кнопка запуска» [[walk-forward-analysis|walk-forward анализа]]. Она принимает таблицу свечей, организует их в 5 обучающих+тестовых блоков и прогоняет стратегию по каждому блоку — отдельно обучение, отдельно честная проверка на невиданных данных. По итогу возвращает сделки, оценки по фолдам, полный отчёт и результат [[monte-carlo-permutation|Monte-Carlo теста]].

**Аналогия:** представьте экзаменатора, который перед тем, как начать экзамен, сначала проверяет, что листы с заданиями не повреждены и все страницы на месте (это `load_ohlcv`), а затем проводит испытание в пяти раундах — каждый раз с новыми задачами (это `run_wfa_single_symbol`).

Эти два модуля живут в `src/backtest/data_loading.py` — они перенесены сюда из главного файла `src/__main__.py` специально для правильного разделения ответственности: данные и бэктест-логика должны жить в `src/backtest/`, а не в точке входа программы (это архитектурный принцип ARCH-05, Sprint 55).

---

## Как это работает у нас

### Шаг 1 — Проверка символа: защита от хакерского «обхода пути»

Прежде чем открыть файл на диске, функция `load_ohlcv` проверяет имя символа по строгому белому списку (**allowlist**).

**Почему это важно:** символ вроде `BTCUSDT` подставляется прямо в путь к файлу: `data/BTCUSDT_1h.parquet`. Если злоумышленник передаст в качестве символа строку вида `../../etc/passwd`, бот попытается открыть системный файл паролей — это называется **path traversal (обход пути)**, атака на файловую систему. Именно так взламывают серверы через незащищённые API.

Защита: регулярное выражение (`regex`), **закреплённое** (anchored) с двух сторон — `\A[A-Z0-9]{1,20}\Z`. Якоря `\A` и `\Z` означают «строго от начала до конца строки», без хвостов. Проверка выполняется через `fullmatch` (а не `match` или `search`, которые допускают скрытые хвосты).

```python
_SYMBOL_RE = re.compile(r"\A[A-Z0-9]{1,20}\Z")  # src/backtest/data_loading.py:35

if not _SYMBOL_RE.fullmatch(symbol):             # src/backtest/data_loading.py:54
    raise ValueError(...)
```

Символ длиннее 20 символов, содержащий строчные буквы, спецсимволы или переносы строк — отклоняется немедленно, до любого обращения к файловой системе. (SEC-S55-01, `src/backtest/data_loading.py:29–35`)

---

### Шаг 2 — Маппинг интервала и путь к файлу

После проверки символа функция определяет, какой именно файл нужно открыть. Интервал в минутах/буква преобразуется в текстовый суффикс имени файла:

| Параметр `interval` | Суффикс файла | Путь к файлу |
|---|---|---|
| `"5"` | `5m` | `data/BTCUSDT_5m.parquet` |
| `"15"` | `15m` | `data/BTCUSDT_15m.parquet` |
| `"30"` | `30m` | `data/BTCUSDT_30m.parquet` |
| `"60"` | `1h` | `data/BTCUSDT_1h.parquet` |
| `"120"` | `2h` | `data/BTCUSDT_2h.parquet` |
| `"240"` | `4h` | `data/BTCUSDT_4h.parquet` |
| `"D"` | `1d` | `data/BTCUSDT_1d.parquet` |
| любое другое | `1h` (по умолчанию) | `data/BTCUSDT_1h.parquet` |

(src/backtest/data_loading.py:58–68)

Путь формируется как `f"data/{symbol}_{interval_label}.parquet"` — это уже безопасно, потому что символ проверен на предыдущем шаге.

---

### Шаг 3 — Чтение файла через `data_collector`

Чтение файла делегируется в `load_market_data` из `src/backtest/data_collector.py`. Эта функция — низкоуровневый читатель данных: она умеет читать как Parquet, так и CSV. При сбое Parquet автоматически пробует CSV-запасной путь (**fallback**):

```python
# src/backtest/data_collector.py:85–96
if source == "parquet":
    try:
        df = _read_parquet(parquet_path)
        return _postprocess_df(df, data_cfg)
    except Exception as parquet_exc:
        logger.warning("Parquet load failed (%s). Falling back to CSV source: %s", ...)
        df = _read_csv(csv_path)
        return _postprocess_df(df, data_cfg)
```

После чтения файла данные нормализуются и очищаются:

**`_normalize_columns`** (src/backtest/data_collector.py:12–26) — приводит имена столбцов к строчным буквам, находит столбец со временем (может называться `time` или `timestamp` или быть первым столбцом), преобразует его в тип «дата-время». Проверяет наличие **обязательных колонок OHLCV** (`open`, `high`, `low`, `close`, `volume`) — при отсутствии любой из них поднимает `ValueError`. Числовые столбцы преобразуются к типу `float`.

**OHLCV** — это аббревиатура: Open (цена открытия), High (максимум), Low (минимум), Close (цена закрытия), Volume (объём сделок за период).

```python
REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]  # src/backtest/data_collector.py:8
```

**`_postprocess_df`** (src/backtest/data_collector.py:33–57) — финальная очистка:
1. Удаляет строки с отсутствующими значениями (`dropna`) по столбцам timestamp + OHLCV.
2. Сортирует по времени.
3. Фильтрует по датам `start_date` и `end_date`, переданным в запросе. При этом выравниваются **часовые пояса (tz-выравнивание)**: если временные метки файла хранят информацию о часовом поясе (UTC), строки фильтра тоже переводятся в этот пояс, иначе Python выбросит ошибку при сравнении «наивной» даты с «зонированной».

---

### Шаг 4 — Предполётная проверка качества данных (CC4)

После чтения `load_ohlcv` выполняет **предполётную проверку** (pre-flight check): подсчитывает, сколько строк останется после удаления всех строк с пропущенными значениями (`dropna`).

Правило: **должно остаться не менее 90% строк от исходного числа.**

Если данные в файле повреждены настолько, что более 10% свечей содержат пропуски — бэктест прерывается с явной ошибкой ещё до запуска:

```python
# src/backtest/data_loading.py:87–93
retained_pct = len(df.dropna()) / len(df)
if retained_pct < 0.90:
    raise ValueError(
        f"NaN pre-flight failed for {symbol}: only {retained_pct:.1%} bars retained "
        f"after dropna (threshold >=90%). Likely data quality issue; investigate Parquet."
    )
```

Это защищает от «тихого» запуска бэктеста на испорченных данных: без этой проверки стратегия могла бы «успешно» торговать на пустых или неполных свечах, давая бессмысленные результаты. (Это офлайн-аналог живого [[data-quality-detector|детектора качества данных]], который в реальном времени ловит зависший или испорченный фид биржи.)

---

### Шаг 5 — Конфигурация стратегии по умолчанию (`_default_wfa_config`)

Если запрос на бэктест не указывает свою конфигурацию, используется встроенный дефолт — стратегия [[02-стратегии/mean-reversion-strategy|mean reversion]] (возврат к среднему) с параметрами из ADR 0032:

| Параметр | Значение | Смысл |
|---|---|---|
| `initial_balance` | 10 000.0 | Стартовый капитал (у.е.) |
| `commission_taker` | 0.001 | Комиссия биржи 0.1% за сделку |
| `slippage` | 0.0005 | Проскальзывание 0.05% (цена хуже ожидаемой) |
| `position_size_pct` | 10.0 | Входим 10% от капитала в каждую позицию |
| `max_drawdown_pct` | 50.0 | Максимально допустимая просадка 50% |
| `long_only` | True | Только покупки (шорт не используется) |
| RSI period | 14 | RSI считается по последним 14 барам |
| RSI oversold | 35 | Сигнал на вход: RSI < 35 (актив перепродан) |
| RSI overbought | 65 | Один из сигналов на выход: RSI > 65 |
| BB period | 20 | Полосы Боллинджера по 20 барам |
| BB k | 1.5 | Ширина полос: 1.5 стандартных отклонения |
| ATR sl_mult | 1.5 | Стоп-лосс = 1.5 × ATR от цены входа |
| ATR tp_mult | 3.0 | Тейк-профит = 3.0 × ATR от цены входа |

(src/backtest/data_loading.py:105–122)

Дашборд может переопределить любой из этих параметров через `strategy_config`. Функция `_default_wfa_config` специально выделена в отдельную функцию (ADR 0039, Sprint 25) именно для этого — чтобы переопределение было явным и чистым, а не «скрытым» внутри большой функции.

---

### Шаг 6 — `run_wfa_single_symbol`: организация walk-forward прогона

Это главная «оркестровая» функция. Она собирает все части вместе и возвращает четыре значения: `(trades, fold_sharpes, runner_result, mc_p)`.

```python
# src/backtest/data_loading.py:125–205
def run_wfa_single_symbol(
    *, symbol, df, strategy_config=None,
    bars_per_year=8760,
    train_bars=2000, test_bars=500,
    k_folds=5, embargo_bars=20,
) -> tuple[list, list[float], dict, float]: ...
```

**Шаг 6а — Создание WindowSplitter:**

```python
splitter = WindowSplitter(
    train_bars=train_bars, test_bars=test_bars,
    k_folds=k_folds, embargo_bars=embargo_bars
)
```

`WindowSplitter` — это «менеджер расписания»: он знает, как разрезать всю историю на 5 (по умолчанию) обучающих + тестовых блоков. При дефолтных параметрах нужно минимум **4520 баров** (= 2000 train + 20 embargo + 5 × 500 test).

(src/backtest/walk_forward.py:20–59, расчёт: `train_bars + embargo_bars + k_folds × test_bars`)

**Шаг 6б — Инжекция `bars_per_year` (S27 T1 fix):**

```python
# src/backtest/data_loading.py:155–157
if "bars_per_year" not in config:
    config = dict(config)
    config["bars_per_year"] = bars_per_year  # default 8760 для 1H баров
```

Это исправление бага Sprint 27: движок бэктеста вычисляет метрику [[sharpe-sortino-metrics|Sharpe Ratio]], для чего нужно знать, сколько баров в году. Раньше это число было «вшито» в код как `sqrt(24 × 365)` — то есть всегда 1H, что давало неверный результат для 4H или дневных баров. Теперь `bars_per_year` передаётся явно. Дефолт 8760 = количество часов в году (для 1H интервала).

**Шаг 6в — Запуск `WalkForwardRunner`:**

```python
runner = WalkForwardRunner(splitter=splitter, replay_fn=run_replay)
runner_result = runner.run(df=df, config=config, symbol=symbol)
```

`WalkForwardRunner` прогоняет [[replay-engine-bar-by-bar|`run_replay`]] по каждому из 5 фолдов — сначала на обучающем окне (IS), затем на тестовом (OOS). Для каждого фолда вычисляется [[tstat-oos-is-metrics|соотношение OOS/IS Sharpe]] — чем ближе к 1, тем стратегия устойчивее.

**Шаг 6г — Monte-Carlo тест на совокупных OOS-сделках:**

```python
# src/backtest/data_loading.py:161–170
oos_trades_df = runner_result["aggregate"]["oos_trades_df"]
raw = oos_trades_df["net_pnl"].astype(float).to_numpy()
returns_arr = np.asarray(raw, dtype=float) / 10000.0
mc_p = sign_flip_p_value(returns_arr, n_iterations=2000, seed=42)
```

Если OOS-сделок нет — MC тест возвращает `mc_p = 1.0` (наихудший возможный результат: стратегия не прошла).
Если сделки есть — 2000 раз случайно меняются знаки у PnL (прибыль → убыток и наоборот), подсчитывается, как часто случайная перестановка даёт такой же или лучший результат. Seed=42 делает тест воспроизводимым.

Подробнее про Monte-Carlo: [[monte-carlo-permutation]].

**Шаг 6д — Извлечение трейдов из каждого фолда:**

```python
# src/backtest/data_loading.py:176–204
for fold_data in runner_result["folds"]:
    fold_sharpes.append(fold_data["oos_is_sharpe_ratio"])
    ...
    trades.extend(extract_trade_records(df_normalized, symbol=symbol))
```

Для каждого фолда: берём OOS-трейды, нормализуем имена столбцов (timestamp_open → entry_ts, timestamp_close → exit_ts), выравниваем временные зоны, при необходимости вычисляем `fees_paid` как сумму entry_fee + exit_fee. Затем [[trade-extractor-and-records|`extract_trade_records`]] превращает табличные строки в объекты `TradeRecord`.

**Возвращаемые значения:**
- `trades` — список `TradeRecord` по всем фолдам.
- `fold_sharpes` — список из 5 чисел: OOS/IS Sharpe Ratio по каждому фолду.
- `runner_result` — полный словарь с деталями по каждому фолду + агрегированные OOS-трейды.
- `mc_p` — p-value Monte-Carlo теста (нужен для [[acceptance-gates-t1-t6|ворот приёмки]] L2).

---

### Архитектурный перенос (ARCH-05, Sprint 55)

До Sprint 55 весь код `load_ohlcv` и `run_wfa_single_symbol` жил в `src/__main__.py` — главном файле-«точке входа» программы. Это создавало нарушение слоёв: `src/backtest/` и `src/dashboard/` импортировали приватные функции из верхнего слоя вместо того, чтобы верхний слой использовал нижние. После перемещения в `src/backtest/data_loading.py` зависимости стали правильными.

Для обратной совместимости тестов `src/__main__.py` ре-экспортирует старые имена как алиасы:

```python
# src/__main__.py:27–31
from src.backtest.data_loading import (
    load_ohlcv as _load_ohlcv,
    run_wfa_single_symbol as _run_wfa_single_symbol,
)
```

Старые тесты с `patch("src.__main__._load_ohlcv")` продолжают работать без изменений.

---

## Формулы и расчёты

### Минимальное количество баров для WFA

Чтобы `WindowSplitter` успешно создал `k_folds` фолдов, в таблице данных должно быть не менее:

```text
min_bars = train_bars + embargo_bars + k_folds × test_bars
```

При дефолтных параметрах:

```text
min_bars = 2000 + 20 + 5 × 500 = 4520 баров
```

Для 1H интервала 4520 баров — это примерно 6 месяцев непрерывной истории.

(src/backtest/walk_forward.py:48: `min_required = self.train_bars + self.embargo_bars + self.k_folds * self.test_bars`)

### Раскладка окон по фолдам (дефолт)

Каждый следующий фолд сдвигается на `test_bars` (500) вправо. Обучающее окно всегда длиной 2000 баров, тестовое — 500, между ними 20 баров карантина:

| Фолд | Обучение (IS) | Карантин | Тест (OOS) |
|---|---|---|---|
| 0 | бары 0–1999 | 2000–2019 | 2020–2519 |
| 1 | бары 500–2499 | 2500–2519 | 2520–3019 |
| 2 | бары 1000–2999 | 3000–3019 | 3020–3519 |
| 3 | бары 1500–3499 | 3500–3519 | 3520–4019 |
| 4 | бары 2000–3999 | 4000–4019 | 4020–4519 |

(src/backtest/walk_forward.py:54–58)

---

## Примеры / сценарии

### Сценарий: запуск бэктеста BTCUSDT через дашборд

1. Пользователь заходит на страницу «Запуск бэктеста» в дашборде и вводит: символ `BTCUSDT`, период с `2023-01-01` по `2024-12-31`, интервал `1h`.

2. Дашборд вызывает `load_ohlcv(symbol="BTCUSDT", start="2023-01-01", end="2024-12-31", interval="60")`.

3. `load_ohlcv` проверяет: `BTCUSDT` соответствует `\A[A-Z0-9]{1,20}\Z` — ОК.

4. Маппинг: `"60"` → `"1h"`, путь: `data/BTCUSDT_1h.parquet`.

5. `load_market_data` читает Parquet, нормализует колонки, обрезает по датам, выравнивает UTC.

6. `load_ohlcv` подсчитывает: 17 520 строк загружено, 17 508 выжили после `dropna` — это 99.9%, порог ≥ 90% пройден.

7. Вызывается `run_wfa_single_symbol(symbol="BTCUSDT", df=df, ...)`.

8. `WindowSplitter` проверяет: 17 520 баров >> 4 520 минимальных — ОК, создаёт 5 фолдов.

9. `WalkForwardRunner` прогоняет `run_replay` 10 раз (по 2 раза на каждый фолд: IS + OOS).

10. Monte-Carlo: 2000 перестановок знаков PnL, seed=42 → `mc_p = 0.031`.

11. Трейды из всех 5 фолдов собираются в единый список, нормализуются временные зоны.

12. Возвращаются `(trades, fold_sharpes, runner_result, mc_p=0.031)` → дашборд строит отчёт.

### Сценарий: символ с подозрительным именем

Пользователь пытается запустить бэктест с символом `../../etc/passwd`:

```python
load_ohlcv(symbol="../../etc/passwd", start="2024-01-01", end="2024-12-31")
# ValueError: Invalid symbol '../../etc/passwd': expected 1-20 uppercase alphanumeric chars (e.g. BTCUSDT)
```

Файловая система не затронута — ошибка возникает до любого обращения к диску.

### Сценарий: испорченный Parquet-файл

Файл `data/BTCUSDT_1h.parquet` повреждён — 15% строк содержат `NaN` в колонке `close`.

После чтения: 10 000 строк загружено, 8 500 осталось после `dropna` — это 85%, ниже порога 90%.

```text
ValueError: NaN pre-flight failed for BTCUSDT: only 85.0% bars retained after dropna
(threshold >=90%). Likely data quality issue; investigate Parquet.
```

Бэктест прерывается немедленно с ясным сообщением.

---

## Подводные камни / что важно понимать

**1. Parquet нужно наполнить заранее.** Файлы `data/<SYMBOL>_<interval>.parquet` создаются отдельной [[data-backfill-command|командой `python -m src backfill --symbol <X>`]]. Если файла нет — `load_ohlcv` выбросит `FileNotFoundError` с подсказкой, какую команду запустить. Данные не скачиваются автоматически при запуске бэктеста.

**2. Fallback CSV работает молча.** Если Parquet не читается (повреждён, неверная версия), `load_market_data` автоматически пробует CSV-файл (`data/BTCUSDT_1h.csv`). Это записывается в лог, но пользователь не видит предупреждения в UI. Если CSV тоже отсутствует — падает с ошибкой.

**3. Порог 90% — не строгая очистка.** Предполётная проверка (CC4) проверяет качество файла в целом, но не гарантирует полное отсутствие `NaN`. `_postprocess_df` уже удалил строки с `NaN` по ключевым колонкам. Предполётная проверка — второй, независимый уровень: она сигнализирует, если удалено слишком много строк (>10%).

**4. `bars_per_year` влияет на Sharpe Ratio.** При использовании 4H баров нужно передать `bars_per_year=2190` (= 8760 / 4). Если этого не сделать и оставить дефолт 8760 — Sharpe Ratio будет завышен примерно в 2 раза, что даст ложное ощущение хорошей стратегии. Дашборд передаёт правильное значение автоматически.

**5. Минимум 4520 баров — жёсткое требование.** Если истории меньше (новый символ, недавно листинговался на бирже), `WindowSplitter` выбросит ошибку с именем символа и точным подсчётом нехватки баров (S33 T4). Никакого «молчаливого» пропуска фолдов нет.

**6. Аргументы только keyword-only.** Все параметры `load_ohlcv` и `run_wfa_single_symbol` принимаются только как `symbol=...`, `start=...` — нельзя передать позиционно. Это снижает риск перепутать порядок аргументов.

**7. Алиасы `_load_ohlcv` / `_run_wfa_single_symbol` в `__main__` — только для тестов.** Они не являются публичным API. Правильное место вызова — `src.backtest.data_loading`. Алиасы существуют только для того, чтобы старые тесты с `patch("src.__main__._load_ohlcv")` продолжали работать без переписывания.

---

## Связанные документы

**Обзор / вход в тему:**
- [[what-is-backtest-overview]] — что такое бэктест и карта всего раздела 06; эта страница — «пусковой механизм» описанного там процесса
- [[wfa-validation-command]] — CLI-команда `wfa`: тот же WFA-путь для одного символа, только запускается из терминала, а не из дашборда

**Прямой конвейер (что вызывает и что выдаёт):**
- [[walk-forward-analysis]] — подробная механика WindowSplitter + WalkForwardRunner: как строятся фолды, что такое IS/OOS, карантин
- [[replay-engine-bar-by-bar]] — `run_replay`, который вызывается внутри WalkForwardRunner для каждого фолда
- [[replay-engine-metrics]] — какие метрики считает `run_replay` по каждому фолду и складывает в `runner_result`
- [[trade-extractor-and-records]] — `extract_trade_records`: как трейды из DataFrame превращаются в `TradeRecord`
- [[wfa-reporter-three-sharpe-series]] — три РАЗНЫХ Шарпа внутри `runner_result` (fold OOS/IS, aggregate OOS, DSR-Sharpe) и как их не перепутать

**Данные (предпосылка загрузки):**
- [[parquet-storage]] — как Parquet-файлы создаются командой `backfill` и что в них хранится; их читает `load_ohlcv`
- [[data-backfill-command]] — команда `backfill`, которая наполняет `data/<SYMBOL>_<interval>.parquet` до запуска бэктеста
- [[data-quality-detector]] — живой аналог предполётной NaN-проверки (CC4): офлайн-порог 90% здесь vs. real-time детектор зависшего/испорченного фида

**Статистическая валидация (куда идут `fold_sharpes` и `mc_p`):**
- [[acceptance-gates-t1-t6]] — куда идут `fold_sharpes` и `mc_p` после этой функции: ворота L1–L4 + DSR
- [[monte-carlo-permutation]] — как работает `sign_flip_p_value`, что означает mc_p и порог ≤ 0.05
- [[deflated-sharpe-ratio]] — извлечённые `TradeRecord` идут дальше в DSR — поправку Шарпа на многократные попытки
- [[tstat-oos-is-metrics]] — `fold_sharpes` = OOS/IS Sharpe по фолдам: метрика устойчивости и почему нужно ≥50 сделок
- [[sharpe-sortino-metrics]] — базовый Sharpe Ratio, на который влияет параметр `bars_per_year` (баг S27)

**Дефолтная стратегия / применение:**
- [[02-стратегии/mean-reversion-strategy]] — стратегия из `_default_wfa_config` (RSI + Bollinger Bands + ATR-стопы), которая гоняется при отсутствии `strategy_config`
- [[run-backtest-form]] — форма дашборда, которая и вызывает `load_ohlcv` + `run_wfa_single_symbol` с введёнными пользователем параметрами

**Контрастные / альтернативные модели бэктеста:**
- [[donchian-runner-and-reference-run]] — эталонный полный WFA-прогон через тот же replay_engine (готовая обёртка-раннер vs. эта generic-функция для любого символа)
- [[research-kernel-execution-model]] — ВТОРАЯ система исполнения (`_backtest_single`) для стратегий-пробоев, которая обходит replay_engine — прямой контраст модели PnL
- [[vector-backtest-fast-approximation]] — быстрый безцикловый движок для грубой оценки: контраст полному честному WFA
- [[kronos-exploratory-runner]] — разведочный прогон ML-стратегии Kronos БЕЗ ворот приёмки — контраст полному WFA с воротами

За техническими деталями архитектурного переноса: `llm-wiki/wiki/project/components/backtest-runner.md`
