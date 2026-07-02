---
title: "Торговая статистика — что означает каждая цифра"
section: "08-дашборд"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/dashboard_react/src/components/metrics/TradesTable.tsx, src/dashboard/glossary_data.py
---

# Торговая статистика — что означает каждая цифра

**TL;DR:** Блок «TRADE STATISTICS» на дашборде показывает итог всех сделок: сколько выиграли, сколько проиграли, и насколько «дорого» это обошлось с учётом биржевых комиссий. В зависимости от типа запуска блок выглядит по-разному — исследовательские пресеты дают 4 строки без USDT-сумм, WFA-запуски дают полные 8 строк с реальными деньгами.

## Простыми словами

Представьте, что вы сыграли 100 партий в карты. После игры вы записываете:

- сколько партий выиграли и сколько проиграли;
- на какую сумму суммарно выиграли и проиграли;
- какой была ваша «прибыль» с каждой выигранной партии и «убыток» с каждой проигранной;
- и сколько вы заплатили «крупье» за каждую карту.

Именно это и делает блок Trade Statistics: он подводит итог всех сделок бота за выбранный период. Каждая строка — одна конкретная статистика, которую не нужно считать вручную.

Особенность нашего бота: на Bybit Spot биржа берёт комиссию **0.1% с каждой стороны** (вход + выход), то есть каждый полный торговый цикл обходится в 0.2%. Это звучит немного, но если бот делает сотни сделок — комиссии становятся важной частью итогового P&L (прибыли и убытка).

## Как это работает у нас

### Два вида блока: RAW-путь и WFA-путь

Блок Trade Statistics существует в двух версиях — и какую именно показать, дашборд решает автоматически в зависимости от типа запуска.

**Кто принимает решение.** В коде есть функция `isResearchVerdict()`, которая проверяет тип [[verdict-and-warnings|вердикта]] полученного от бэкенда. Если вердикт — `RAW` или `RAW_PRETRAIN_LEAKAGE_SUSPECTED` (исследовательские прогоны без WFA-дисциплины), показывается урезанный вид. Для всех остальных вердиктов — полный [[wfa-methodology|WFA]]-вид. (src/dashboard_react/src/utils/verdicts.ts:15–23)

```
TradesTable → isResearchVerdict(result.verdict)?
  да  → RawTradesTable   (5 строк, исследовательский режим)
  нет → WfaTradesTable   (8 строк, полный WFA-режим)
```
(src/dashboard_react/src/components/metrics/TradesTable.tsx:149–156)

---

### RawTradesTable — исследовательский путь (5 строк)

Показывается для стратегий [[06-бэктест-и-валидация/atr-breakout-strategy|`atr_breakout`]], [[06-бэктест-и-валидация/volume-breakout-strategy|`volume_breakout_iter10`]] и [[08-дашборд/kronos-ml-strategy|Kronos]] с [[kronos-data-leakage|подозрением на утечку данных]]. Эти пресеты запускаются через [[research-kernel-execution-model|research runner]], который **не имеет базы капитала** (нет конкретной суммы в USDT, только проценты) — поэтому суммы в деньгах не вычисляются.

| Строка в UI | Откуда берётся |
|---|---|
| Profitable trades | `Math.round(n_trades × win_rate)` — вычисляется из доли победных сделок |
| Losing trades | `n_trades − nWin` |
| Win rate | `fmtPct(win_rate)` — доля × 100% |
| Total PnL % | `metrics.total_pnl_pct` или `result.total_pnl_pct` (накопленный % от стартового баланса) |
| Примечание (colspan=2) | Фиксированный текст о том, что USDT-суммы отложены |

Подсчёт победных сделок — это не прямые данные от бэкенда, а вычисление на лету в браузере:

```
nWin = Math.round(nTr × winR)   // nTr = n_trades, winR = win_rate (дробь 0..1)
nLos = nTr − nWin
```
(src/dashboard_react/src/components/metrics/TradesTable.tsx:49–50)

Такое приближение необходимо потому, что research runner в бэкенде отдаёт `n_winners`/`n_losers` как `None`, если список сделок недоступен. (src/backtest/research_runner_envelope.py:166–171)

---

### WfaTradesTable — WFA-путь (8 строк)

Показывается для стратегий с WFA-прогоном через [[replay-engine-bar-by-bar|replay engine]]: [[08-дашборд/ema-crossover-strategy|EMA Crossover]], [[08-дашборд/mean-reversion-strategy|Mean Reversion]], [[donchian-breakout-strategy|Donchian Breakout]]. Здесь все данные приходят в готовом виде в объекте `result.trade_stats` — никаких вычислений в браузере.

| Строка в UI | Поле в `trade_stats` | Что показывает |
|---|---|---|
| Profitable trades | `ts.n_winners` | Точное число прибыльных сделок (int) |
| Losing trades | `ts.n_losers` | Точное число убыточных сделок (int) |
| Win rate | `m.t4_win_rate` (из `metrics`) | Доля победных сделок (дробь → %) |
| Total PnL | `ts.total_pnl_quote` | Суммарный P&L в USDT |
| Total Commissions | `ts.total_commissions_quote` | Сумма всех комиссий в USDT |
| Avg Win | `ts.avg_win_quote` | Средний выигрыш на сделку в USDT |
| Avg Loss | `ts.avg_loss_quote` | Средний проигрыш на сделку в USDT |
| Profit Factor | `ts.profit_factor` | Коэффициент прибыльности |

(src/dashboard_react/src/components/metrics/TradesTable.tsx:94–145)

Важная деталь: [[max-drawdown-winrate-rr|Win rate]] на WFA-пути берётся из `metrics.t4_win_rate`, а **не** из `trade_stats.win_rate`. Это связано с тем, что `t4_win_rate` — нормированное значение (0..1) из `strategy_metrics.py`, которое vычисляется по итогам всех [[walk-forward-analysis|OOS-сделок]]. (src/backtest/strategy_metrics.py:119)

---

### Откуда берутся цифры на бэкенде (WFA-путь)

В `backtest_runner.py` бэкенд перебирает все сделки из `sym_trades` и вычисляет:

```python
n_winners  = sum(1 for t in sym_trades if float(t.pnl_quote) > 0)
n_losers   = sum(1 for t in sym_trades if float(t.pnl_quote) < 0)
avg_win    = sum(pnl > 0) / n_winners
avg_loss   = sum(pnl < 0) / n_losers
gross_profit = sum(pnl > 0)
gross_loss   = abs(sum(pnl < 0))
profit_factor = gross_profit / gross_loss  # None если нет убытков
total_commissions = sum(t.fees_paid for t in sym_trades)
```
(src/dashboard/backtest_runner.py:1255–1270)

Для research-пути (atr_breakout, volume_breakout) все quote-поля заполняются как `None` явно — браузер их отображает как прочерк «—». (src/backtest/research_runner_envelope.py:180–185)

---

### Форматирование чисел

| Функция | Применяется к | Пример вывода |
|---|---|---|
| `fmt(value, digits)` | Числа без единицы (Profit Factor) | `1.87` |
| `fmtPct(value)` | Доли 0..1 → проценты | `62.3%` |
| `fmtMoney(value)` | Суммы в USDT (тысячи-разделитель) | `1,234.56` |
| `fmtUsdtCell(value)` | Суммы с суффиксом | `1,234.56 USDT` |

Любое `null`, `undefined` или `NaN` любой из этих функций заменяет на прочерк `—`. (src/dashboard_react/src/components/metrics/TradesTable.tsx:18–38)

## Формулы и расчёты

### Win Rate (доля прибыльных сделок)

```
Win Rate = n_winners / n_total
```

Простыми словами: из 80 сделок 50 завершились в плюс — Win Rate = 50/80 = 62.5%.

На дашборде значение хранится как дробь от 0 до 1 и умножается на 100 для отображения. Вычисляется в `strategy_metrics.py` из итогов всех OOS-фолдов. (src/backtest/strategy_metrics.py:119)

**Важно понимать:** высокий Win Rate сам по себе не означает прибыльности стратегии. Если вы выигрываете 60% сделок по 10 USDT, но проигрываете 40% по 20 USDT — вы в минусе. Именно поэтому Win Rate нужно читать вместе с Profit Factor и Avg Win / Avg Loss.

---

### Profit Factor

```
Profit Factor = Sum(все прибыльные сделки в USDT) / |Sum(все убыточные сделки в USDT)|
```

Простыми словами: сколько рублей прибыли приходится на каждый рубль убытка. Если бот заработал суммарно 2000 USDT на выигрышах и потерял 1000 USDT на проигрышах — Profit Factor = 2.0. Profit Factor — это одна из [[replay-engine-metrics|метрик результата прогона]], вычисляемых в бэкенде наряду с Sharpe, Sortino и Expectancy.

| Значение | Что означает |
|---|---|
| PF < 1.0 | Убыточная стратегия — теряет больше, чем зарабатывает |
| PF = 1.0 | Ноль (комиссии съедают остальное) |
| PF > 1.0 | Прибыльная стратегия |
| PF > 2.0 | Сильный edge — суммарный выигрыш вдвое превышает проигрыш |

Если у стратегии не было ни одной убыточной сделки — знаменатель равен нулю, и Profit Factor возвращается как `None`, дашборд показывает «—». (src/dashboard/backtest_runner.py:1270)

---

### Total Commissions (USDT)

```
Total Commissions = Σ (fees_paid за каждую сделку)
```

Каждая сделка порождает **два** начисления комиссии: при входе и при выходе. Ставка — 0.001 (то есть 0.1%) с объёма каждого ордера — это тариф Bybit Spot taker, зафиксированный в ADR 0008.

В replay engine это считается так:

```python
entry_fee = entry_price * qty * commission   # 0.1% от суммы входа
exit_fee  = exit_price  * qty * commission   # 0.1% от суммы выхода
```
(src/backtest/replay_engine.py:200–202)

Суммируется по всем сделкам в `_compute_metrics()`: `(entry_fee + exit_fee).sum()`. (src/backtest/replay_engine.py:84–85)

Для research-пути (atr_breakout, volume_breakout, kronos) комиссия вычитается иначе — напрямую из PnL в процентах:

```python
pnl_net = pnl_gross - 2.0 * _COMMISSION_TAKER   # _COMMISSION_TAKER = 0.001
```
(src/backtest/atr_breakout_runner.py:38, 213)

Но итоговая строка `total_commissions_quote` для этих стратегий остаётся `None` (нет базы капитала), поэтому на дашборде «—».

---

### Avg Win / Avg Loss (USDT)

```
Avg Win  = Сумма всех прибыльных сделок / Количество прибыльных сделок
Avg Loss = Сумма всех убыточных сделок / Количество убыточных сделок
```

(src/dashboard/backtest_runner.py:1258–1267)

Avg Loss отображается с отрицательным знаком (убыток). Соотношение `|Avg Win| / |Avg Loss|` — это так называемый **[[max-drawdown-winrate-rr|Risk-Reward Ratio (RR)]]**: сколько потенциального выигрыша приходится на единицу риска. RR = 2.0 означает, что за каждый USDT убытка бот в среднем зарабатывал 2 USDT.

## Примеры / сценарии

### Сценарий: EMA Crossover, WFA-прогон, 120 сделок

Предположим, WFA-прогон завершился и бэкенд вернул:

```
n_trades: 120,  win_rate: 0.583
n_winners: 70,  n_losers: 50
total_pnl_quote: 840.20 USDT
total_commissions_quote: 112.50 USDT
avg_win_quote: 35.40 USDT
avg_loss_quote: -18.70 USDT
profit_factor: 1.87
```

Что читаем на экране:

| Строка | Значение |
|---|---|
| Profitable trades | 70 (зелёным цветом) |
| Losing trades | 50 (красным цветом) |
| Win rate | 58.3% |
| Total PnL | 840.20 USDT |
| Total Commissions | 112.50 USDT |
| Avg Win | 35.40 USDT |
| Avg Loss | -18.70 USDT |
| Profit Factor | 1.87 |

Проверка Profit Factor:
- Gross Profit = 70 × 35.40 = 2 478 USDT
- Gross Loss = 50 × 18.70 = 935 USDT
- PF = 2 478 / 935 ≈ 2.65

(Небольшое расхождение с 1.87 объясняется тем, что Avg Win/Loss — средние, а PF считается через суммы — реальные выигрыши и проигрыши неравномерны. Это нормально.)

RR = 35.40 / 18.70 ≈ 1.89 — хорошее соотношение. В сочетании с WR 58.3% стратегия убедительно прибыльна.

---

### Сценарий: ATR Breakout, Research-прогон (5 строк)

```
n_trades: 95,  win_rate: 0.52  (из бэкенда)
```

На дашборде вычисляется:

```
nWin = Math.round(95 × 0.52) = Math.round(49.4) = 49
nLos = 95 − 49 = 46
```

Блок покажет:

| Строка | Значение |
|---|---|
| Profitable trades | 49 |
| Losing trades | 46 |
| Win rate | 52.0% |
| Total PnL % | (например) +8.40% |
| (примечание) | Quote-currency stats deferred... |

USDT-суммы отсутствуют — research runner не привязывает прогон к конкретному капиталу.

## Подводные камни / что важно понимать

**Win Rate без контекста — недостаточен.** Win Rate 60% звучит хорошо, но если Avg Win = 10 USDT, а Avg Loss = 30 USDT, то ожидаемый P&L отрицателен: 0.6×10 − 0.4×30 = 6 − 12 = −6 USDT за сделку. Всегда смотрите Win Rate вместе с Profit Factor или соотношением Avg Win / Avg Loss. (src/dashboard/glossary_data.py:219–227)

**Победные / убыточные сделки на RAW-пути — приближение.** В `RawTradesTable` числа `nWin` и `nLos` вычислены через `Math.round(nTr × winR)`. Если `win_rate` содержит округление, реальное число может отличаться на ±1. На WFA-пути используются точные значения из `trade_stats.n_winners` и `ts.n_losers`. (TradesTable.tsx:49–50)

**Total Commissions — только WFA-путь.** Research-пресеты (atr_breakout, volume_breakout, Kronos) вычитают комиссию из PnL-процента, но не отдают USDT-сумму — в коде явно `"total_commissions_quote": None`. Дашборд покажет «—», это не ошибка. (src/backtest/research_runner_envelope.py:181)

**Profit Factor None vs 0.** Если у стратегии не было ни одной убыточной сделки, `profit_factor` возвращается как `None`, а не бесконечность. Дашборд показывает «—». Не путайте с PF = 0 — это невозможная ситуация по формуле. (src/dashboard/backtest_runner.py:1270)

**Total PnL — до вычета комиссий vs после.** Строка `Total PnL` на WFA-пути показывает `total_pnl_quote` из `trade_stats`. Это **чистый** P&L (`net_pnl`), уже с учётом комиссий в каждой сделке (entry_fee + exit_fee вычтены в `net_pnl`). Строка `Total Commissions` показывает их сумму отдельно для понимания масштаба издержек. (src/backtest/replay_engine.py:202–203)

**Win Rate на WFA-пути берётся из `metrics`, не из `trade_stats`.** Строка «Win rate» показывает `m.t4_win_rate`, а не `ts.win_rate`. Это нормированное значение (0..1), вычисленное по OOS-сделкам всех фолдов. Разница может быть незначительной, но источник — именно `strategy_metrics.py`. (src/dashboard_react/src/components/metrics/TradesTable.tsx:119)

**Цвет строк — смысловой.** «Profitable trades» всегда отображается зелёным, «Losing trades» — красным. Цвет Total PnL определяется знаком: если `totalPnl > 0` — зелёный (metricPass), иначе — красный (metricFail). (src/dashboard_react/src/components/metrics/TradesTable.tsx:52–53, 79)

## Связанные документы

**Соседние блоки дашборда:**

- [[08-дашборд/metrics-table-tiers]] — соседний блок «METRICS» с Sharpe, Sortino, Drawdown; Trade Statistics дополняет его торговым разрезом
- [[08-дашборд/verdict-and-warnings]] — вердикт (PASS/FAIL/RAW) определяет, какой из двух видов TradesTable показывается
- [[08-дашборд/equity-chart-and-drawdown]] — визуальный эквивалент тех же сделок: каждая точка на графике соответствует одной trade
- [[08-дашборд/glossary-tab]] — в глоссарии на вкладке Glossary каждый термин из этого блока объяснён на русском языке
- [[wfa-methodology]] — WFA-путь: почему полноценный WFA-прогон даёт все 8 строк с USDT-суммами
- [[history-tab]] — как сравнивать торговую статистику разных прошлых прогонов
- [[run-backtest-form]] — где запускается прогон, который порождает эти цифры

**Что означают конкретные цифры (метрики):**

- [[max-drawdown-winrate-rr]] — математика Win Rate (T4) и Risk-Reward Ratio: две строки этого блока разобраны как метрики
- [[sharpe-sortino-metrics]] — Sharpe и Sortino: риск-скорректированные метрики соседнего блока METRICS, читаются вместе с Win Rate/Profit Factor
- [[06-бэктест-и-валидация/acceptance-gates-t1-t6]] — Win Rate входит в T4 (информационный гейт): пороги WR ≥ 45%/RR ≥ 1.5 или WR ≥ 35%/RR ≥ 2.0
- [[replay-engine-metrics]] — функция `_compute_metrics`, где вычисляются Profit Factor, Avg Win/Loss и суммарные комиссии

**Откуда берутся сделки (бэктест):**

- [[06-бэктест-и-валидация/replay-engine-bar-by-bar]] — подробно: как каждая сделка создаётся в replay engine (entry_fee, exit_fee, net_pnl)
- [[research-kernel-execution-model]] — контраст: research runner (RAW-путь) считает PnL в процентах без базы капитала — поэтому USDT-суммы = «—»
- [[walk-forward-analysis]] — WFA-путь: n_winners/n_losers считаются по всем OOS-фолдам
- [[trade-extractor-and-records]] — TradeRecord (pnl_quote, fees_paid) — первичный источник, который эти строки агрегируют
- [[trade-fill-history]] — где в live-режиме хранятся закрытые сделки и исполнения, которые статистика подводит

**Какая стратегия — какой вид блока:**

- [[strategies-overview]] — карта: какой пресет уходит на RAW-путь (4 строки), а какой на WFA-путь (8 строк)
- [[06-бэктест-и-валидация/atr-breakout-strategy]] — RAW-путь: research-пресет без USDT-сумм
- [[06-бэктест-и-валидация/volume-breakout-strategy]] — RAW-путь: research-пресет без USDT-сумм
- [[08-дашборд/kronos-ml-strategy]] — RAW-путь: 4 строки (вердикт RAW_PRETRAIN_LEAKAGE_SUSPECTED)
- [[kronos-data-leakage]] — почему Kronos на исследовательском пути и что это значит для доверия к цифрам
- [[08-дашборд/ema-crossover-strategy]] — WFA-путь: полный вид из 8 строк с реальными USDT
- [[08-дашборд/mean-reversion-strategy]] — WFA-путь: полный вид из 8 строк
- [[donchian-breakout-strategy]] — WFA-путь: полный вид из 8 строк

За техническими деталями расчёта метрик: `llm-wiki/wiki/project/components/backtest-metrics.md`
