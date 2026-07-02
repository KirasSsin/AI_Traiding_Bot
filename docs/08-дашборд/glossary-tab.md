---
title: "Глоссарий — как пользоваться встроенным словарём"
section: "08-дашборд"
status: filled
money_core: false
updated: 2026-06-26
source_files: src/dashboard_react/src/components/tabs/GlossaryTab.tsx, src/dashboard/glossary_data.py
---

# Глоссарий — как пользоваться встроенным словарём

**TL;DR:** встроенный словарь дашборда объясняет все аббревиатуры и метрики на русском языке; поддерживает поиск по ключевым словам и подсвечивает только те термины, которые актуальны для выбранной стратегии.

## Простыми словами

Представьте, что вы впервые открыли страницу результатов бэктеста и видите: «[[dsr-and-mc|DSR]] ≥ 0.95», «MC p-value ≤ 0.05», «fold OOS/IS Sharpe ≥ 0.7». Как человеку без специальной подготовки понять, что это значит и нужно ли беспокоиться?

Вкладка «Глоссарий» — это встроенный словарь прямо в дашборде. Каждый термин, символ и метрика, которые вы видите на других вкладках, здесь объяснены по-русски, с указанием порогов («при каком значении это хорошо»), и, если есть, со ссылкой на ADR — внутреннее архитектурное решение, объясняющее почему выбран именно этот порог.

Аналогия из жизни: как словарь в конце учебника. Читаете сложный термин — перелистываете в конец — получаете объяснение. Только здесь это работает мгновенно через поиск, и словарь знает, какая стратегия сейчас выбрана, и поэтому «затемняет» неактуальные термины.

Глоссарий — **не технический справочник для программиста**, а инструмент оператора-человека: «[[verdict-and-warnings|почему у этой стратегии FAIL]]?» → открыть глоссарий → найти термин → прочитать объяснение.

## Как это работает у нас

### Источник данных: Python → API → UI

Всё содержимое глоссария живёт в одном Python-файле `src/dashboard/glossary_data.py`. При загрузке вкладки React-компонент вызывает эндпоинт `/api/glossary` (зарегистрирован в `src/dashboard/app.py:304`), который возвращает функцию `get_glossary()` (`glossary_data.py:630`). Ответ содержит три части:

```text
{
  "entries":             { <term>: GlossaryEntry, ... },   # 41 термин
  "strategy_to_metrics": { <preset_id>: [term, ...], ... }, # 6 стратегий
  "sections":            [ "verdict_status", ... ]         # 7 секций в порядке отображения
}
```

Данные жёстко зашиты в Python (не в базе данных) — это осознанное решение (architect C3): глоссарий меняется редко, синхронизация с базой создала бы сложность без выгоды (`glossary_data.py:10-11`).

### Структура термина (GlossaryEntry)

Каждый из 41 термина описывается четырьмя полями (`glossary_data.py:27-31`):

| Поле | Что это |
|------|---------|
| `section` | К какой из 7 секций принадлежит термин |
| `description_ru` | Русское объяснение: что такое, порог, что означает PASS/FAIL |
| `applies_to` | Список пресетов стратегий ИЛИ `["*"]` (все стратегии) |
| `adr_ref` | Ссылка на ADR с обоснованием порога (или `null`) |

### 7 секций глоссария (SECTIONS)

Python определяет ровно 7 секций в строгом порядке отображения (`glossary_data.py:34-42`). UI-файл `GlossaryTab.tsx:16-25` задаёт человекочитаемые названия для каждой. Секции и количество терминов в каждой:

| Ключ секции | Отображаемое название | Кол-во терминов | Что содержит |
|-------------|----------------------|-----------------|--------------|
| `verdict_status` | Вердикты и символы статуса | 8 | PASS/FAIL/RAW/LEAKAGE вердикты + символы ▸ ✓ ✗ |
| `gate_blocking_metrics` | Gate-blocking metrics | 5 | Метрики, блокирующие PASS: DSR, MC, n_trades, n_eff, fold OOS/IS |
| `informational_metrics` | Informational metrics | 5 | T1-T4, T6 — информационные (не блокируют, но показывают качество) |
| `trade_statistics` | Торговая статистика | 7 | PnL, Win Rate, Profit Factor, комиссии и т.д. |
| `chart_vocabulary` | Графики | 3 | Equity curve, Drawdown, Monthly heatmap |
| `warnings` | Предупреждения | 7 | Коды предупреждений: mc_noise, low_sample, look-ahead bias и т.д. |
| `strategy_presets` | Пресеты стратегий | 6 | Краткое описание каждого из 6 пресетов |

Итого: 41 термин в 7 секциях. (`glossary_data.py:45-439`)

> **Заметка об SECTION_LABELS:** в TSX-файле `SECTION_LABELS` содержит 8 ключей — там дополнительно присутствует `monthly_heatmap: 'Heatmap по месяцам'` (`GlossaryTab.tsx:22`). Но в Python `SECTIONS` этой секции нет: термин `monthly_heatmap` находится внутри секции `chart_vocabulary`. Этот лишний ключ в TSX — «мёртвый» лейбл: он никогда не вызывается, потому что `glossary.sections` (из API) не включает `monthly_heatmap` как отдельную секцию.

### Фильтр по стратегии (T16)

Когда пользователь выбирает стратегию на другой вкладке (например, нажимает «Run backtest» для `ema_crossover_s13`), хук `useStrategyContext` сохраняет выбор в URL-параметр `?strategy=<id>` (`useStrategyContext.ts:6-15`).

Глоссарий читает этот параметр (`GlossaryTab.tsx:32`) и строит множество применимых терминов (`GlossaryTab.tsx:64-72`):

```typescript
const list = glossary.strategy_to_metrics[currentStrategy]
return new Set(list)
```

Если термин входит в это множество — он отображается ярко (`entryApplicable`). Если нет — приглушён (`entryDimmed`). Если стратегия не выбрана (`currentStrategy === null`) — все термины отображаются одинаково без фильтрации.

Граничный случай: если пользователь передал в URL стратегию, которой нет в `strategy_to_metrics` — глоссарий выводит в консоль предупреждение и показывает все термины (защита от опечаток в URL, `GlossaryTab.tsx:67-69`).

### Карта применимости STRATEGY_TO_METRICS_MAP

Соответствие «стратегия → список её терминов» задано вручную в `STRATEGY_TO_METRICS_MAP` (`glossary_data.py:445-627`). Шесть пресетов:

| Пресет | ID |
|--------|----|
| EMA Crossover (S13) | `ema_crossover_s13` |
| Mean Reversion S15 | `mean_reversion_s15` |
| Mean Reversion S17 (relaxed) | `mean_reversion_s17_relaxed` |
| Donchian Breakout S35 | `donchian_breakout_s35` |
| Volume Breakout iter10 | `volume_breakout_iter10` |
| ATR Breakout | `atr_breakout` |

Для первых четырёх пресетов применимы все стандартные метрики (включая `fold_oos_is_sharpe`, `t4_win_rate`, цитаты в USDT). Для `volume_breakout_iter10` и `atr_breakout` — облегчённый набор без `fold_oos_is_sharpe`, `t2_sortino_oos`, `t4_win_rate` и цитат avg_win/avg_loss, зато с `verdict_raw` и `raw_full_period` (`glossary_data.py:578-626`). Это отражает тот факт, что эти два пресета ([[02-стратегии/volume-breakout-strategy|Volume Breakout]] и [[02-стратегии/atr-breakout-strategy|ATR Breakout]]) работают в режиме full-period backtest без [[walk-forward-analysis|WFA]]-дисциплины.

### Поиск (T17)

Поиск работает в реальном времени без перезагрузки страницы. Пользователь вводит текст в поле — React немедленно фильтрует термины по двум полям (`GlossaryTab.tsx:78-87`):

```typescript
if (term.toLowerCase().includes(q) || entry.description_ru.toLowerCase().includes(q)) {
  results.push([term, entry])
}
```

То есть поиск работает и по **ключу термина** (например, `dsr`), и по **русскому описанию** (например, «просадка»). Регистр игнорируется.

Когда поиск активен, отображение переключается в «плоский» режим: все найденные термины показываются в одном блоке «Результаты поиска (N)» вместо разбивки по секциям. Боковое оглавление (sticky TOC) при этом скрывается (`GlossaryTab.tsx:135-148`).

Фильтрация по стратегии работает и в режиме поиска — применимые термины остаются выделенными, неприменимые приглушаются (`GlossaryTab.tsx:153-156`).

### URL-якорь (anchor) для прямого перехода

Якорная ссылка — это способ открыть страницу сразу на конкретном термине. Например, ссылка `http://localhost:5173/?tab=glossary#glossary-dsr` откроет глоссарий и прокрутит до термина `dsr`.

Механизм (`GlossaryTab.tsx:90-103`): после загрузки данных компонент читает `window.location.hash`, проверяет формат `#glossary-{term}`, находит HTML-элемент с `id="glossary-{term}"`, прокручивает к нему (`scrollIntoView`) и добавляет CSS-класс `entryHighlightPulse` на 1500 мс — кратковременную анимацию-подсветку, чтобы пользователь точно заметил нужный термин. Через 1500 мс подсветка убирается.

Каждый термин получает `id="glossary-{term}"` в HTML при рендеринге (`GlossaryTab.tsx:166, 194`), поэтому якоря стабильны.

### Sticky TOC (оглавление)

В левой части вкладки (режим без поиска) находится «Содержание» — список 7 секций. Это обычные `<a href="#section-verdict_status">` ссылки, работающие через браузерную прокрутку. При активации поиска TOC исчезает (нет смысла в навигации по секциям когда показан плоский список, `GlossaryTab.tsx:135`).

### Состояния загрузки

Компонент корректно обрабатывает три состояния (`GlossaryTab.tsx:105-107`):

- **Загружается:** «Загрузка глоссария...»
- **Ошибка API:** «Ошибка: {сообщение об ошибке}»
- **Успешно:** отображение секций с TOC

## Примеры / сценарии

### Сценарий 1: «Что такое DSR?»

Оператор видит на вкладке [[wfa-methodology|WFA]]: «DSR: 0.87 — FAIL». Открывает «Глоссарий», вводит в поиск «dsr». Немедленно появляется:

> **dsr** (gate_blocking_metrics) — ADR 0056  
> Deflated Sharpe Ratio (Bailey & López de Prado 2014). Corrected Sharpe учитывая multiple comparisons + non-normality (skewness + kurtosis). Использует Pearson kurtosis (fisher=False) per ADR 0056. Threshold ≥ 0.95 для PASS (high statistical confidence).  
> Используется в: все стратегии

Теперь оператор понимает: порог 0.95, у стратегии 0.87 — не прошла.

### Сценарий 2: Фильтр по стратегии EMA Crossover

На вкладке «Настройки бэктеста» выбран пресет `ema_crossover_s13`. URL становится `?strategy=ema_crossover_s13`. Пользователь переключается на «Глоссарий». Видит:

- **Ярко выделены** ~30 терминов: все gate-blocking, информационные, торговая статистика, графики, предупреждения, пресет EMA Crossover.
- **Приглушены** (серым): `verdict_pretrain_leakage`, `preset_atr_breakout`, `preset_donchian_breakout_s35` и остальные пресеты.
- В шапке подсказка: «Filter: ema_crossover_s13 — выделены применимые termы».

### Сценарий 3: Прямая ссылка на термин

Другая страница документации хочет послать оператора сразу к объяснению `mc_p_value`. Ссылка: `http://localhost:5173/?tab=glossary#glossary-mc_p_value`. При открытии — автоматически прокручивается к термину, 1.5 секунды он подсвечен пульсирующей анимацией.

### Сценарий 4: Volume Breakout — ограниченный набор

При выбранном `volume_breakout_iter10` в глоссарии приглушены `fold_oos_is_sharpe`, `t2_sortino_oos`, `t4_win_rate`, `avg_win_quote`, `avg_loss_quote`. Это потому что [[02-стратегии/volume-breakout-strategy|Volume Breakout]] работает как research-пресет (full-period, не WFA), поэтому эти метрики для него неактуальны — их попросту нет в его результатах. Зато ярко выделены `verdict_raw` и `raw_full_period`, предупреждающие об отсутствии WFA-дисциплины.

## Подводные камни / что важно понимать

**SECTION_LABELS vs SECTIONS — мелкое расхождение.** В TSX-файле `SECTION_LABELS` содержит 8 ключей, включая `monthly_heatmap`. В Python `SECTIONS` — только 7 элементов. Раздел `monthly_heatmap` в SECTION_LABELS никогда не используется как отдельная секция — термин `monthly_heatmap` (описание тепловой карты) лежит в секции `chart_vocabulary`. Ключ `monthly_heatmap` в SECTION_LABELS — исторический артефакт (`GlossaryTab.tsx:22`).

**Карта STRATEGY_TO_METRICS_MAP не синхронизируется автоматически.** Это ручной список (architect C3 BINDING). Если добавить новый пресет стратегии в код, но не добавить его в `STRATEGY_TO_METRICS_MAP`, при выборе этой стратегии все термины будут «приглушены», и в консоли появится предупреждение (`GlossaryTab.tsx:67-69`). Если добавляется новый пресет — нужно руками добавить его запись в `STRATEGY_TO_METRICS_MAP` (`glossary_data.py:445`).

**Применимость `applies_to` в GlossaryEntry и в STRATEGY_TO_METRICS_MAP — два разных механизма.** `applies_to` в каждом термине — метаданные «декларативно для каких стратегий этот термин актуален». `STRATEGY_TO_METRICS_MAP` — операционная карта «какие термины подсвечивать при выбранном пресете». UI использует только карту (`glossary.strategy_to_metrics`), а не поле `applies_to` напрямую для фильтрации (`GlossaryTab.tsx:64-72`).

**Описания терминов — сжатые, не учебник.** `description_ru` рассчитаны на человека, который уже видел термин на другой вкладке и хочет быстро вспомнить порог и смысл. Для полного объяснения [[deflated-sharpe-ratio|DSR]], [[monte-carlo-permutation|MC]], [[walk-forward-analysis|WFA]] и [[acceptance-gates-t1-t6|ворот приёмки T1-T6]] — смотрите соответствующие разделы документации (ссылки ниже).

**Поиск работает только по двум полям:** ключу термина и `description_ru`. По полю `adr_ref` поиск не работает: ввод «ADR 0056» найдёт совпадение только если эти слова есть в описании, а не в поле `adr_ref`.

**Kronos / `verdict_pretrain_leakage`.** Этот вердикт специфичен для стратегии [[kronos-ml-strategy|Kronos]] и помечен ADR 0068. В `STRATEGY_TO_METRICS_MAP` для `kronos` записи нет (версия v0.1 не включает kronos в список фронтенд-пресетов). Поэтому термин `verdict_pretrain_leakage` всегда отображается без фильтрации (при любой выбранной стратегии он будет «приглушён» — его нет ни в одной карте) (`glossary_data.py:84-95`).

## Связанные документы

Дашборд (соседние вкладки, чьи термины объясняет глоссарий):

- [[dashboard-overview]] — общая архитектура дашборда и навигация между вкладками (глоссарий — одна из вкладок)
- [[documentation-tab]] — соседняя справочная вкладка: карточки индикаторов, параметры, методология (парная роль «встроенного знания»)
- [[metrics-table-tiers]] — таблица метрик T1-T6: gate-blocking vs информационные — глоссарий описывает те же метрики кратко
- [[verdict-and-warnings]] — расшифровка вердиктов (PASS/FAIL/RAW/WFA_FAIL) и предупреждений — секции `verdict_status` и `warnings` глоссария
- [[dsr-and-mc]] — DSR и Monte Carlo в дашборде — секция `gate_blocking_metrics` глоссария
- [[wfa-methodology]] — Walk-Forward Analysis в дашборде: fold OOS/IS Sharpe — понятия из секции gate-blocking
- [[equity-chart-and-drawdown]] — графики equity curve и drawdown — секция `chart_vocabulary` глоссария
- [[monthly-heatmap]] — тепловая карта по месяцам — термин `monthly_heatmap` из секции `chart_vocabulary`
- [[trade-statistics]] — торговая статистика (win rate, profit factor, PnL) — секция `trade_statistics` глоссария
- [[run-backtest-form]] — форма запуска бэктеста: выбор пресета здесь пишет `?strategy=<id>` в URL, по которому глоссарий фильтрует термины
- [[caching-and-security]] — технический фундамент дашборда (кеш, run_id, безопасность запросов)

Стратегии-пресеты (секция `strategy_presets` — глоссарий подсвечивает термины по выбранной стратегии):

- [[strategies-overview]] — карта всех 7 стратегий: соответствует секции `strategy_presets`
- [[ema-crossover-strategy]] — пресет `ema_crossover_s13`
- [[mean-reversion-strategy]] — пресеты `mean_reversion_s15` и `mean_reversion_s17_relaxed`
- [[breakout-strategies]] — пресеты `donchian_breakout_s35`, `volume_breakout_iter10`, `atr_breakout`
- [[02-стратегии/volume-breakout-strategy]] — облегчённый набор метрик (research-режим, без WFA) — граничный случай фильтра
- [[02-стратегии/atr-breakout-strategy]] — облегчённый набор метрик (research-режим, без WFA) — граничный случай фильтра
- [[kronos-ml-strategy]] — вердикт `verdict_pretrain_leakage` специфичен для Kronos; в карте пресетов Kronos нет (всегда приглушён)

Глубокие объяснения терминов (глоссарий даёт сжатую версию — здесь полная):

- [[deflated-sharpe-ratio]] — DSR: формула, смысл, порог ≥ 0.95, почему Pearson kurtosis (ADR 0056)
- [[monte-carlo-permutation]] — MC permutation test: sign-flip, block_size=20, порог p ≤ 0.05
- [[acceptance-gates-t1-t6]] — полное описание ворот приёмки T1-T6 + DSR + MC с формулами и логикой вердикта
- [[walk-forward-analysis]] — что такое WFA, fold, OOS/IS Sharpe — понятия из gate-blocking метрик
- [[dsr-metric]] — DSR со стороны кода/метрик (`compute_t1_t6_metrics`), sigma_SR, множественные проверки
- [[mc-permutation-test]] — Monte-Carlo со стороны кода/метрик: как считается p-value
- [[sharpe-sortino-metrics]] — Sharpe и Sortino: базовые метрики доходности с поправкой на риск
- [[tstat-oos-is-metrics]] — T-статистика и OOS/IS Sharpe: значимость и устойчивость (fold OOS/IS порог)
- [[max-drawdown-winrate-rr]] — MaxDD, Win Rate, Risk-Reward — термины секций `informational_metrics` и `trade_statistics`
- [[cross-trial-log]] — история Sharpe по всем прогонам (нужна для sigma_SR в DSR)

Словарь терминов вне дашборда:

- [[glossary-entry]] — входная страница словаря терминов всей документации: понятийный «двойник» этого встроенного словаря

За техническими деталями: `llm-wiki/wiki/project/components/glossary.md` (если существует) или `llm-wiki/wiki/project/plans/` по S48 T5-T6.
