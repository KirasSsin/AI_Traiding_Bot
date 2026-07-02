---
title: "WFA-отчёт и три разных Шарпа (wfa_reporter)"
section: "06-бэктест-и-валидация"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/backtest/wfa_reporter.py
---

# WFA-отчёт и три разных Шарпа (wfa_reporter)

**TL;DR:** После завершения walk-forward анализа бот собирает итоговый отчёт с помощью `format_wfa_report`. Главная тонкость: в системе три разных числа, которые называются «коэффициент Шарпа» — их нельзя путать. Каждое считается по-своему, используется для разного и живёт в своей колонке отчёта.

## Простыми словами

Представьте, что вы оцениваете работу таксиста тремя разными способами:

1. **По поездкам в час** — сколько клиентов он отвёз за единицу времени (хороший способ для плановиков).
2. **По заработку с каждого клиента** — средняя прибыль со сделки, без привязки к часам (внутренняя бухгалтерия).
3. **По годовому заработку** — «а сколько бы он заработал за год, если бы так работал всегда?» (для красивого отчёта руководству).

Все три числа связаны, но отражают разные стороны одного явления. Если смешать их в одной формуле — получится бессмыслица.

Именно так устроен **коэффициент Шарпа** (Sharpe ratio, см. [[sharpe-sortino-metrics|Sharpe и Sortino]]) — стандартная мера «доходность, делённая на риск». В нашем боте он вычисляется тремя разными способами для трёх разных задач:

| Название | Что считает | Для чего |
|---|---|---|
| **Bar-returns Sharpe** (Шарп по барам) | Доходность каждой свечи (бара), умножено на √8760 для годового масштаба | Ворота OOS/IS: был ли бот лучше на тестовом периоде, чем на обучающем? |
| **Per-trade Sharpe** (Шарп по сделкам) | Средняя доходность сделки / риск сделки, без годовой нормировки | Внутри формулы [[deflated-sharpe-ratio\|DSR (Deflated Sharpe Ratio)]] |
| **Display Sharpe** (отображаемый Шарп) | Per-trade Шарп × √8760 — «приведённый к году» | Показ в отчёте и UI — чтобы числа были читаемы |

**Смешать их нельзя.** Если подставить «Шарп по барам» туда, где ожидается «Шарп по сделкам», DSR рассчитается неверно — настоящая прибыльная стратегия покажет DSR ≈ 0 и будет несправедливо отброшена. Этот баг реально произошёл (Sprint 55, дефект QS-1) и был исправлен. Поэтому три серии хранятся раздельно и помечены явными именами в словаре отчёта.

`format_wfa_report` — единственная функция этого модуля. Она принимает сырые результаты WFA-прогона и склеивает из них финальный словарь, который записывается в JSON и читается дашбордом.

## Как это работает у нас

Функция `format_wfa_report` (src/backtest/wfa_reporter.py:29–104) принимает четыре параметра:

- `runner_result` — результат `WalkForwardRunner.run()`: список фолдов с метриками + агрегат
- `trades_for_dsr` — список [[trade-extractor-and-records|TradeRecord]] (закрытых сделок со всех фолдов) — для вычисления DSR
- `mc_p_value` — p-значение [[monte-carlo-permutation|Monte-Carlo теста]] (уже посчитано снаружи)
- `gate_result` — результат `evaluate_acceptance_gate()` (уже посчитан снаружи)

Опциональный параметр `bars_per_year` (по умолчанию 8760 для 1-часового бара, 35040 для 15-минутного) задаёт аннуализирующий множитель (src/backtest/wfa_reporter.py:26, 35).

Функция выполняет пять шагов:

### Шаг 0 — аннуализирующий коэффициент

```python
annualization_factor = float(np.sqrt(bars_per_year))
```

Для 1H-баров: `√8760 ≈ 93.59`. Для 15M-баров: `√35040 ≈ 187.19`. Этот множитель превращает «доходность за одну свечу» в «годовую доходность» (src/backtest/wfa_reporter.py:50).

### Шаг 1 — Series 1: Bar-returns Sharpe по каждому фолду

```python
bar_returns_sharpe_per_fold = [
    f.get("oos_metrics", {}).get("Sharpe Ratio", 0.0)
    for f in folds
]
```

Просто берёт число, которое уже посчитал `WalkForwardRunner` для каждого OOS-периода (src/backtest/wfa_reporter.py:54–55). Это тот Шарп, который участвует в воротах OOS/IS (ADR 0014): ворота проверяют, не хуже ли тестовый Шарп обучающего. Подробнее об этих воротах — в [[06-бэктест-и-валидация/acceptance-gates-t1-t6]].

### Шаг 2 — Series 2: Per-trade Sharpe (для DSR)

```python
returns = compute_returns(trades_for_dsr, use_log=True)
finite_returns = [r for r in returns if math.isfinite(r)]
if len(finite_returns) >= 2:
    mean = sum(finite_returns) / len(finite_returns)
    var = sum((r - mean) ** 2 for r in finite_returns) / (len(finite_returns) - 1)
    if var > 0:
        per_trade_sharpe = mean / math.sqrt(var)
```

Это ручной расчёт прямо в репортере (src/backtest/wfa_reporter.py:58–66). Берутся все закрытые сделки из всех фолдов, из каждой извлекается логарифмическая доходность `log(1 + pnl_pct)`. Потом: средняя / стандартное отклонение (с поправкой ddof=1). **Нет умножения на √bars_per_year** — это сознательно: per-trade Шарп остаётся в «единицах сделки», чтобы потом корректно войти в формулу DSR.

Если сделок нет, или все доходности одинаковые (вар = 0), результат — `math.nan`.

### Шаг 3 — Series 3: Display Sharpe (для показа)

```python
display_sharpe = (
    per_trade_sharpe * annualization_factor
    if math.isfinite(per_trade_sharpe) else math.nan
)
```

Просто умножает per-trade Шарп на √bars_per_year (src/backtest/wfa_reporter.py:69–71). Это то самое «переводим в годовой масштаб, чтобы было понятно». Именно это число показывается пользователю в дашборде. Если T1 в [[06-бэктест-и-валидация/acceptance-gates-t1-t6]] показывает «годовой Шарп» — он считается по той же схеме.

В словаре отчёта дополнительно записывается `display_sharpe_annualization_factor` — само число √bars_per_year — чтобы позднее можно было проверить, на что умножался per-trade Шарп (src/backtest/wfa_reporter.py:98).

### Шаг 4 — DSR aggregate (агрегатный DSR)

```python
fold_oos_sharpes = aggregate.get("fold_oos_sharpes", [])
if trades_for_dsr and len(fold_oos_sharpes) >= 2:
    sigma_sr = float(np.std(fold_oos_sharpes, ddof=1))
    dsr_aggregate = compute_dsr(
        trades_for_dsr,
        n_trials=len(fold_oos_sharpes),
        sigma_sr=sigma_sr,
        annualization_factor=annualization_factor,
    )
```

Здесь кроется главная тонкость системы (src/backtest/wfa_reporter.py:73–88).

`fold_oos_sharpes` — это список аннуализированных Шарпов по каждому OOS-фолду (bar-returns Sharps, Series 1). Стандартное отклонение этого списка (`sigma_sr`) показывает, насколько разброс результатов от фолда к фолду — нужно для формулы DSR (Bailey & López de Prado, 2014, eq. 12). Число фолдов K становится параметром `n_trials` (множественное тестирование). Родственный механизм накопления Шарпов между разными прогонами — [[cross-trial-log|CrossTrialLog]], откуда берётся `sigma_SR` для DSR по всей истории попыток.

**Проблема единиц (S55 QS-1):** `sigma_sr` вычислен из аннуализированных Шарпов (умноженных на √8760), а внутри `compute_dsr` кандидатный Шарп вычисляется по сделкам — без аннуализации. Если подставить аннуализированный `sigma_sr` прямо в формулу Bailey eq. 12, масштабы не совпадут: SR* вычисляется в «годовых» единицах, а per-trade SR — в «сделочных», которые примерно в √(bars_per_year / mean_holding) ≈ 9× меньше. Разность (SR − SR*) оказывается отрицательной — DSR рухнет к нулю, и реально прибыльная стратегия несправедливо провалит ворота. Именно это происходило до исправления. Поэтому `annualization_factor` передаётся в `compute_dsr` явно: функция делит `sigma_sr` на этот коэффициент, возвращая его к per-trade масштабу (src/analytics/dsr.py:156–157). Подробнее о самой формуле DSR — в [[06-бэктест-и-валидация/deflated-sharpe-ratio]].

Условие `len(fold_oos_sharpes) >= 2` обязательно: при одном фолде стандартное отклонение не определено (ddof=1 даёт деление на 0).

### Шаг 5 — Per-fold DSR (заглушка)

```python
dsr_per_fold: list[float] = []
for _ in folds:
    dsr_per_fold.append(math.nan)
```

DSR для каждого фолда в отдельности — зарезервированная структура (src/backtest/wfa_reporter.py:91–92). Пока она заполнена `NaN`, потому что для этого нужно преобразовать DataFrame фолда в список `TradeRecord` — задача отложена на будущий спринт. Это не ошибка: поле присутствует в отчёте намеренно, чтобы дашборд и потребители могли строить на нём логику заранее.

### Итоговый словарь отчёта

```python
return {
    "bar_returns_sharpe_per_fold": bar_returns_sharpe_per_fold,  # list[float], Series 1
    "per_trade_sharpe": per_trade_sharpe,                        # float, Series 2
    "display_sharpe": display_sharpe,                            # float, Series 3
    "display_sharpe_annualization_factor": annualization_factor, # float, √bars_per_year
    "dsr_aggregate": dsr_aggregate,                              # float, 0–1
    "dsr_per_fold": dsr_per_fold,                                # list[float], все NaN сейчас
    "mc_p_value": mc_p_value,                                    # float, передан снаружи
    "acceptance_gate": gate_result,                              # dict, передан снаружи
    "k_folds": aggregate.get("k_folds", 0),                     # int, число фолдов
}
```

(src/backtest/wfa_reporter.py:94–104)

## Формулы и расчёты

### Аннуализирующий коэффициент

```text
annualization_factor = √(bars_per_year)

1H бары:  √8760  ≈ 93.59
15M бары: √35040 ≈ 187.19
```

**Что это значит простыми словами:** за год на 1-часовых данных торгуется примерно 8760 баров (24 часа × 365 дней). Чтобы сравнивать стратегии с разных рынков, принято приводить доходность к одному году. Математически корень нужен потому, что стандартное отклонение (знаменатель Шарпа) растёт пропорционально √времени — так работает статистика случайных процессов.

### Три формулы Шарпа

**Series 1 (Bar-returns Sharpe):**
```text
Берётся из oos_metrics["Sharpe Ratio"] каждого фолда — уже аннуализирован
внутри WalkForwardRunner (логика в replay_engine/metrics).
```

**Series 2 (Per-trade Sharpe):**
```text
returns_i = log(1 + pnl_pct_i)   — логарифмическая доходность i-й сделки

per_trade_sharpe = mean(returns) / std(returns, ddof=1)
```

*Что считает:* «в среднем заработали X единиц риска за сделку». Без умножения на √8760. Используется как кандидатный SR в формуле DSR (src/analytics/dsr.py:117).

**Series 3 (Display Sharpe):**
```text
display_sharpe = per_trade_sharpe × √bars_per_year
```

*Что считает:* «если бы сделки шли непрерывно весь год, каким был бы годовой Шарп». Это число для людей, не для формул.

### sigma_sr для DSR aggregate

```text
sigma_sr = std(fold_oos_sharpes, ddof=1)
```

*Что считает:* насколько сильно результаты разнятся от фолда к фолду. Если в одном фолде Шарп = 1.5, в другом = 0.8, в третьем = 1.2, то sigma_sr ≈ 0.36. Высокий sigma_sr говорит: стратегия нестабильна, результат сильно зависит от выбранного периода — это плохо.

Перед подстановкой в `compute_dsr` sigma_sr **делится на annualization_factor** (src/analytics/dsr.py:157), чтобы перейти от «годового» к «per-trade» масштабу:

```text
sigma_sr_per_trade = sigma_sr_annualized / √bars_per_year
```

## Примеры / сценарии

### Сценарий A — нормальный прогон с 5 фолдами

Допустим, WFA прогнал 5 фолдов и получил OOS-Шарпы: `[1.2, 0.9, 1.4, 1.1, 1.3]`. Из 200 сделок суммарно per-trade Шарп = 0.35.

Шаг 1 — bar_returns_sharpe_per_fold = `[1.2, 0.9, 1.4, 1.1, 1.3]`  
Шаг 2 — per_trade_sharpe = `0.35`  
Шаг 3 — display_sharpe = `0.35 × √8760 ≈ 0.35 × 93.59 ≈ 32.76`  
Шаг 4 — sigma_sr = `std([1.2, 0.9, 1.4, 1.1, 1.3], ddof=1) ≈ 0.19`  
        sigma_sr_per_trade = `0.19 / 93.59 ≈ 0.002`  
        dsr_aggregate = результат compute_dsr(trades=200сделок, n_trials=5, sigma_sr=0.002)

Итоговый отчёт содержит все эти числа в именованных полях, плюс mc_p_value, acceptance_gate и k_folds=5.

### Сценарий B — один фолд: DSR aggregate не считается

Если фолдов только 1, `fold_oos_sharpes` содержит один элемент, условие `len(fold_oos_sharpes) >= 2` не выполняется, и `dsr_aggregate = math.nan`. Это нормально — стандартное отклонение от одного числа не определено.

### Сценарий C — нет сделок: все Шарпы NaN

Если `trades_for_dsr = []`, то:
- per_trade_sharpe = `math.nan` (условие `if trades_for_dsr` ложно)
- display_sharpe = `math.nan` (нет конечного per_trade_sharpe)
- dsr_aggregate = `math.nan` (условие `if trades_for_dsr and ...` ложно)

Отчёт всё равно формируется — с NaN в этих полях.

### Сценарий D — что было до исправления QS-1 (для понимания проблемы)

*Гипотетический пример по схеме из тест-файла tests/unit/test_dsr_units_scale.py.*

До Sprint 55 `compute_dsr` вызывался без `annualization_factor`. Рассмотрим типичную ситуацию: 8 запусков WFA, sigma_sr (стандартное отклонение аннуализированных Шарпов) = 0.6. Per-trade Шарп «настоящей» прибыльной стратегии ≈ 0.50.

Bailey eq. 12 вычисляет «порог» SR*:

```text
SR* = 0 + 0.6 × ((1 − γ) × z1 + γ × z2) ≈ 0.875
```

Разность `SR − SR* = 0.50 − 0.875 = −0.375` — отрицательная, что сразу даёт DSR ≈ 0. Стратегия с реальным преимуществом показывает «нулевую надёжность» — ложноотрицательный провал ворот.

Ошибка в том, что SR* вычислен в аннуализированных единицах (sigma_sr = 0.6 — это разброс годовых Шарпов), а per-trade SR (0.50) — в единицах сделки, которые примерно в √(bars_per_year / mean_holding) ≈ 9.36× меньше годовых. То есть SR* завышен относительно per-trade SR.

После исправления sigma_sr делится на `annualization_factor` = √8760 ≈ 93.59 перед eq. 12 (src/analytics/dsr.py:156–157):
```text
sigma_sr_per_trade = 0.6 / 93.59 ≈ 0.00641
SR* = 0 + 0.00641 × (...) ≈ 0.009
SR − SR* = 0.50 − 0.009 = +0.491  → DSR > 0.95
```

Важно: коэффициент 9.36 (≈ √(8760/100)) — это другой путь кода ([[research-kernel-execution-model|research-ядро исполнения]]). Он живёт в `research_wfa.py:321` и делит на среднее число баров в сделке (100 — плейсхолдер). В `wfa_reporter.py` делитель строго равен √bars_per_year ≈ 93.59 (src/backtest/wfa_reporter.py:50, src/analytics/dsr.py:156–157). Промежуточные числа сильно различаются (0.00641 против 0.064), но качественный вывод один и тот же: DSR > 0.95, стратегия проходит ворота.

Тест `test_single_scale_allows_genuine_edge_to_pass_gate` (tests/unit/test_dsr_units_scale.py:89–103) воспроизводит этот сценарий и проверяет DSR > 0.95 после исправления.

## Подводные камни / что важно понимать

**1. Три Шарпа — три разных числа.** Нельзя сравнивать bar-returns Sharpe одного прогона с display Sharpe другого. Всегда уточняйте, какой именно Шарп вы смотрите. В отчёте они хранятся под разными ключами именно поэтому.

**2. Display Sharpe — только для людей, не для ворота.** Функция `evaluate_acceptance_gate` содержит четыре именованных ворота: L1 ([[tstat-oos-is-metrics|OOS/IS Шарп ≥ 0.7]]), L2 (MC p-value ≤ 0.05), L3 (n_eff порог), L4 (минимум сделок T5) (src/backtest/walk_forward.py:174–178). DSR проверяется отдельно — вне этой функции — в `research_wfa.py:342–348` и добавляется к `failed_criteria` вручную (никакого L5 не существует). Display Sharpe (Series 3) не участвует ни в одном из этих проверок — он существует, чтобы человек мог оценить масштаб числа в привычных «годовых» единицах.

**3. dsr_per_fold = всегда NaN сейчас.** Поле зарезервировано. Если вы читаете отчёт и видите там список NaN — это не ошибка прогона, а незаполненный placeholder (src/backtest/wfa_reporter.py:91–92).

**4. bars_per_year зависит от интервала данных.** При 1H-баре передаётся 8760, при 15M — 35040 (src/backtest/wfa_reporter.py:25–26). Если вызвать с неверным `bars_per_year`, display Sharpe и sigma_sr будут несогласованы с тем, что ожидает дашборд. Параметр всегда должен соответствовать интервалу исходных данных.

**5. format_wfa_report — только для replay-пути.** Функция обслуживает `WalkForwardRunner` (`src/__main__.py:37–38`). Research-путь (`run_research_wfa` в `research_wfa.py`) формирует свой отчёт по-другому и не использует этот модуль. Подробнее о двух путях WFA — в [[06-бэктест-и-валидация/walk-forward-analysis]].

**6. mc_p_value и acceptance_gate функция не считает.** Они вычисляются снаружи (MC-тест и evaluate_acceptance_gate) и просто копируются в словарь отчёта. format_wfa_report — это «сборщик», а не «вычислитель» всего.

## Связанные документы

**Внутри раздела 06 (пайплайн бэктеста и валидации):**

- [[deflated-sharpe-ratio]] — как устроена формула DSR изнутри: eq. 12 (поправка на N попыток), eq. 13 (финальный DSR), Pearson kurtosis, sigma_sr
- [[acceptance-gates-t1-t6]] — bar-returns Sharpe Series 1 используется для ворот OOS/IS; display Sharpe Series 3 соответствует T1 (годовой per-trade Шарп)
- [[walk-forward-analysis]] — откуда берётся `runner_result` и `fold_oos_sharpes`; два пути WFA (replay vs research)
- [[monte-carlo-permutation]] — откуда берётся `mc_p_value` перед передачей в format_wfa_report
- [[trade-extractor-and-records]] — откуда берётся `trades_for_dsr` (список TradeRecord со всех фолдов)
- [[reporter-and-artifacts]] — что происходит с итоговым словарём отчёта после format_wfa_report (запись JSON, артефакты)
- [[single-symbol-wfa-and-data-loading]] — загрузка данных и WFA для одного символа: питает `WalkForwardRunner`, чей результат сюда приходит
- [[donchian-runner-and-reference-run]] — эталонный полный WFA-прогон через replay_engine, который в итоге вызывает format_wfa_report
- [[replay-engine-metrics]] — где вычисляется Series 1 (bar-returns Sharpe из `oos_metrics["Sharpe Ratio"]`), который репортер только берёт готовым
- [[research-kernel-execution-model]] — контраст: ВТОРОЙ путь WFA (research_wfa), где делитель 9.36 вместо √bars_per_year; свой отчёт, не использует этот модуль

**Метрики (раздел 03) — три Шарпа и DSR по отдельности:**

- [[sharpe-sortino-metrics]] — что вообще такое коэффициент Шарпа как метрика (T1/T2), из которого растут все три серии здесь
- [[dsr-metric]] — DSR как метрика качества (0–1), которую агрегат из Шага 4 наполняет; тот же units-fix QS-1
- [[cross-trial-log]] — журнал OOS-Шарпов по всем прогонам: источник `sigma_SR` и `n_trials` для DSR через историю попыток
- [[tstat-oos-is-metrics]] — OOS/IS Sharpe (T6, ворота L1) = именно Series 1, bar-returns Sharpe, которую собирает репортер
- [[mc-permutation-test]] — тест перестановок, дающий `mc_p_value` (метрика-детализация к [[monte-carlo-permutation]])

**Дашборд (раздел 08) — потребители словаря отчёта:**

- [[dsr-and-mc]] — как дашборд показывает DSR и Monte Carlo из полей `dsr_aggregate` и `mc_p_value` этого отчёта
- [[wfa-methodology]] — как дашборд объясняет WFA нетехническому читателю (фолды, train/test), поверх этих же данных
- [[metrics-table-tiers]] — таблица T1–T6, где display Sharpe (Series 3) отображается как годовой Шарп T1
- [[verdict-and-warnings]] — как из `acceptance_gate` и DSR формируется итоговый вердикт PASS/FAIL/WFA_FAIL

**Запуск (раздел 01):**

- [[wfa-validation-command]] — команда `wfa`, с которой стартует весь прогон, чей итог собирает format_wfa_report

За техническими деталями формулы DSR (Bailey eq. 12/13, QS-1 units fix): `llm-wiki/wiki/project/components/dsr.md`
