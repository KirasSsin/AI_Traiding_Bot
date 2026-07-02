---
title: "Вкладка документации — индикаторы, параметры, методология"
section: "08-дашборд"
status: filled
updated: 2026-06-26
money_core: false
source_files: src/dashboard_react/src/components/tabs/DocumentationTab.tsx, src/dashboard_react/src/api/types.ts
---

# Вкладка документации — индикаторы, параметры, методология

**TL;DR:** Вкладка «Documentation» — это встроенный справочник дашборда. Открыв её, вы видите четыре раздела с карточками: какие индикаторы использует бот и что они измеряют, что означают числовые параметры (множители ATR), краткие профили стратегий и описание методологии WFA-тестирования. Все данные читаются из кода и никогда не расходятся с реальным поведением бота.

## Простыми словами

Представьте, что вы открыли торговый автомат, а на его панели есть кнопка «Инструкция». Нажав на неё, вы видите описание всех механизмов: что такое каждая кнопка, какие числа считает машина, по каким правилам она принимает решения. Вкладка Documentation — именно такая «инструкция», вшитая прямо в дашборд.

Это важно потому, что торговый бот использует несколько математических инструментов (называемых **индикаторами** — см. справочник [[technical-indicators]]), параметры-множители для управления риском, а также сложную процедуру проверки стратегий ([[wfa-methodology|WFA]]). Не разобравшись в этих понятиях, сложно осмысленно читать результаты бэктеста. Documentation tab объясняет всё прямо там, не требуя отдельного обучения.

**Что увидит пользователь?** Четыре вертикально расположенных раздела:

1. **INDICATORS** — карточки пяти математических инструментов, которые бот применяет для распознавания рыночных сигналов.
2. **MULTIPLIERS** — карточки числовых параметров, определяющих размер стопов, тейков и позиций.
3. **STRATEGIES** — профили трёх стратегий, испытанных в проекте (с логикой входа/выхода и историческими результатами).
4. **METHODOLOGY** — карточки про WFA, DSR, MC-тест и acceptance criteria (правила приёмки стратегии).

Раздел появляется только если в нём есть хотя бы одна карточка — пустые разделы автоматически скрываются. (src/dashboard_react/src/components/tabs/DocumentationTab.tsx:300–330)

## Как это работает у нас

### Шаг 1. Загрузка данных при открытии вкладки

Когда пользователь переходит на вкладку Documentation, компонент `DocumentationTab` немедленно запрашивает данные у сервера. Это происходит один раз при первом отображении через хук `useEffect`:

```typescript
useEffect(() => {
  let cancelled = false
  api.getDocs()
    .then((data) => { if (!cancelled) setDocs(data) })
    .catch((err) => { ... })
  return () => { cancelled = true }
}, [])
```

(src/dashboard_react/src/components/tabs/DocumentationTab.tsx:262–272)

Флаг `cancelled` нужен для безопасности: если пользователь быстро переключился на другую вкладку до завершения запроса, ответ сервера будет отброшен и не вызовет ошибки в уже удалённом компоненте.

Пока данные загружаются — показывается надпись «Loading documentation...». Если сервер не ответил — «Failed to load documentation». (src/dashboard_react/src/components/tabs/DocumentationTab.tsx:275–292)

### Шаг 2. GET /api/docs → DocsEnvelope

`api.getDocs()` — это просто обёртка над запросом к эндпоинту сервера:

```typescript
getDocs: (): Promise<DocsEnvelope> => request('/api/docs'),
```

(src/dashboard_react/src/api/client.ts:69)

На стороне Python-сервера (FastAPI) маршрут `/api/docs` вызывает функцию `get_documentation()`:

```python
@app.get("/api/docs")
async def get_docs() -> dict[str, object]:
    return get_documentation()
```

(src/dashboard/app.py:283–289)

Функция `get_documentation()` просто возвращает четыре Python-списка, определённых в том же файле:

```python
def get_documentation() -> dict[str, Any]:
    return {
        "indicators": INDICATORS_DOC,
        "multipliers": MULTIPLIERS_DOC,
        "strategies": STRATEGIES_DOC,
        "methodology": METHODOLOGY_DOC,
    }
```

(src/dashboard/backtest_runner.py:838–846)

**Важно:** это не база данных и не файл конфигурации — все данные вшиты в код Python в виде Python-списков словарей. Они меняются только при обновлении кода.

### Шаг 3. Структура ответа — DocsEnvelope

Ответ сервера соответствует TypeScript-интерфейсу `DocsEnvelope`:

```typescript
export interface DocsEnvelope {
  indicators: IndicatorDoc[]
  multipliers: MultiplierDoc[]
  strategies: StrategyDoc[]
  methodology: MethodologyDoc[]
}
```

(src/dashboard_react/src/api/types.ts:141–146)

Четыре параллельных массива — по одному на каждый раздел вкладки.

### Шаг 4. Рендер четырёх разделов

После получения данных компонент отрисовывает разделы по шаблону «если массив не пустой — показать»:

```tsx
{d.indicators.length > 0 && (
  <DocSection title="INDICATORS">
    {d.indicators.map((ind) => <IndicatorCard key={ind.name} ind={ind} />)}
  </DocSection>
)}
```

(src/dashboard_react/src/components/tabs/DocumentationTab.tsx:300–306)

Аналогично для MULTIPLIERS (строки 308–313), STRATEGIES (315–322), METHODOLOGY (324–330). Каждый раздел — обёртка `DocSection`, внутри которой `cardsGrid` — сетка карточек. (строки 241–254)

---

### Раздел INDICATORS — карточки индикаторов

**Индикатор** — это математическая формула, которая считает производную величину из исторических цен и объёмов. Сам по себе индикатор ничего не торгует; он даёт «сигнал», который стратегия уже использует для принятия решений.

Каждая карточка описывается интерфейсом `IndicatorDoc`:

```typescript
export interface IndicatorDoc {
  name: string          // короткое имя: "RSI", "ATR" и т.д.
  full_name: string     // полное название
  category: string      // тип: "Momentum oscillator", "Volatility" и т.д.
  author: string        // кто придумал и когда
  description: string   // HTML-описание (может содержать <strong>, <em>)
  formula: string       // текстовое представление формулы
  range: string         // диапазон возможных значений
  interpretation: string[] // список смысловых интерпретаций
  params_in_strategies: Record<string, string> // параметры индикатора в НАШИХ стратегиях
  source: string        // библиографическая ссылка
}
```

(src/dashboard_react/src/api/types.ts:89–100)

В коде задано **5 индикаторов** (src/dashboard/backtest_runner.py:457–587) — у каждого есть отдельная страница-справочник: [[ema-rsi-indicators|EMA и RSI]], [[bollinger-bands-indicator|Bollinger Bands]], [[atr-indicator|ATR]], [[adx-indicator|ADX]]:

| Индикатор | Полное название | Категория | Автор |
|-----------|----------------|-----------|-------|
| RSI | Relative Strength Index | Momentum oscillator | J. Welles Wilder Jr. (1978) |
| BB | Bollinger Bands | Volatility envelope | John Bollinger (1980s) |
| EMA | Exponential Moving Average | Trend / smoothing | Classical (1960s) |
| ATR | Average True Range | Volatility | J. Welles Wilder Jr. (1978) |
| ADX | Average Directional Index | Trend strength (NOT directional) | J. Welles Wilder Jr. (1978) |

**Что видит пользователь в карточке?** Компонент `IndicatorCard` отображает:
- Шапку: короткое имя + полное название + категория-«чип» в правом углу.
- Автора.
- Описание (HTML) — может содержать форматирование.
- Формулу в отдельном блоке `formulaBlock`.
- Range (диапазон значений).
- Список интерпретаций (если есть) в виде `<ul>`.
- Таблицу «Параметры в стратегиях» (если объект `params_in_strategies` не пустой).
- Источник (библиография) внизу.

(src/dashboard_react/src/components/tabs/DocumentationTab.tsx:22–69)

**Про поле `source` — нюанс:** в интерфейсе `IndicatorDoc` в `types.ts` поле `source` объявлено (строка 99), компонент его отображает (строка 67), и Python-данные его включают (например, для RSI: `"source": "Wilder, J.W. (1978) New Concepts in Technical Trading Systems"`). Это библиографическая ссылка для тех, кто хочет изучить первоисточник.

---

### Раздел MULTIPLIERS — карточки параметров

**Multiplier** (множитель) — это числовой параметр, который задаёт поведение бота. Название «множитель» идёт от того, что большинство из них умножают [[atr-indicator|ATR]] (меру волатильности), чтобы получить расстояние до стопа или тейка — механика этого расчёта разобрана в [[wilder-atr-and-stops]].

Аналогия: если ATR — это «типичный дневной шаг цены», то SL multiplier = 1.5 означает «мы готовы потерять полтора таких шага, прежде чем выйти из сделки».

Интерфейс:

```typescript
export interface MultiplierDoc {
  name: string
  id: string          // технический ключ: "sl_atr_mult", "tp_atr_mult" и т.д.
  default: number | string  // значение по умолчанию
  description: string // HTML
  tradeoff: string    // HTML — описание компромисса
}
```

(src/dashboard_react/src/api/types.ts:102–108)

В коде задано **6 параметров** (src/dashboard/backtest_runner.py:588–652):

| Параметр | id | Значение по умолчанию | Суть |
|----------|----|-----------------------|------|
| SL multiplier (Stop Loss) | `sl_atr_mult` | 1.5 | Выходим при убытке в 1.5×ATR от точки входа |
| TP multiplier (Take Profit) | `tp_atr_mult` | 3.0 | Берём прибыль при 3.0×ATR от точки входа |
| Position size % | `position_size_pct` | 10.0 | Каждая сделка = 10% от доступного баланса |
| Commission rate (taker) | `commission_taker` | 0.001 | 0.1% комиссия Bybit на каждое исполнение |
| Slippage allowance | `slippage` | 0.0005 | 0.05% поправка на проскальзывание |
| Max drawdown halt | `max_drawdown_pct` | 50.0 | Бэктест останавливается при просадке > 50% |

**Примечание про carточку:** компонент `MultiplierCard` показывает имя, id в тэге `<code>`, default, описание (HTML) и блок «Tradeoff» (HTML). Комментарий в коде говорит, что полный диапазон и таблица impact не реализованы (TODO S47). (src/dashboard_react/src/components/tabs/DocumentationTab.tsx:93)

**Стоп-лосс (SL, Stop-Loss)** — автоматический приказ закрыть позицию, если цена ушла против нас на заданное расстояние. Защита от больших потерь; расстояние задаётся через SL-множитель ATR (см. [[wilder-atr-and-stops]]).

**Тейк-профит (TP, Take-Profit)** — автоматический приказ закрыть позицию при достижении целевой прибыли.

**Acceptance gate (ворота приёмки)** — порог, которому должна соответствовать стратегия, чтобы пройти валидацию. Подробнее — в разделе METHODOLOGY ниже и на странице [[acceptance-gates-t1-t6]].

Параметр `position_size_pct` (доля баланса на сделку) в live-режиме — лишь верхняя граница: реальный размер позиции бот вычисляет по формуле Келли, см. [[position-sizing-kelly]]. Параметр `max_drawdown_pct` = 50% относится только к остановке бэктеста; в live за просадкой следят [[circuit-breakers-drawdown-flash|автоматические предохранители]].

---

### Раздел STRATEGIES — карточки стратегий

**Стратегия** — это набор правил: когда входить, когда выходить, какие индикаторы использовать. Карточка в Documentation tab — это краткий профиль: не полная техническая документация стратегии (она находится в [[02-стратегии/README|разделе 02-стратегии]]), а сводка по ключевым полям для быстрого понимания.

Интерфейс:

```typescript
export interface StrategyDoc {
  category: string      // тип стратегии: "Trend-following", "Mean-reversion" и т.д.
  name: string
  tagline: string       // HTML — краткий слоган
  entry_logic: string   // HTML — когда входим
  exit_logic: string    // HTML — когда выходим
  historical_results: string // HTML — что получилось в тестах
  best_for: string      // HTML — при каких условиях рынка работает
  indicators_used: string[]  // список индикаторов
  key_params: Record<string, string | number> // ключевые параметры
  academic_reference: string // первоисточники из академической литературы
}
```

(src/dashboard_react/src/api/types.ts:110–121)

В коде задано **3 стратегии** (src/dashboard/backtest_runner.py:654–748) — у каждой есть подробная страница: [[ema-crossover-strategy]] и [[mean-reversion-strategy]] (S15 и S17):

| Стратегия | Категория | Вердикт |
|-----------|-----------|---------|
| EMA crossover (S13 baseline) | Trend-following | FAIL (T1=−44.46 OOS Sharpe) |
| Mean-reversion S15 original (RSI 30/70 + BB 2.0σ) | Mean-reversion | FAIL T6+MC+DSR |
| Mean-reversion S17 relaxed (RSI 35/65 + BB 1.5σ) | Mean-reversion (relaxed) | PASS T1-T5+DSR+MC, FAIL T5 sample floor |

**Что видит пользователь в карточке?** Компонент `StrategyCard` отображает:
- Категорию, название и tagline (HTML).
- Основную часть: Entry logic, Exit logic, Historical results, Best for — всё как HTML.
- Боковую панель (aside): «фишки» используемых индикаторов, таблицу ключевых параметров, академическую ссылку.

(src/dashboard_react/src/components/tabs/DocumentationTab.tsx:100–165)

**Замечание об объёме:** здесь представлены только три стратегии из тех, что были протестированы в проекте. Пробойные стратегии Donchian Breakout, Volume Breakout и ATR-Adaptive Breakout (все три — на странице [[breakout-strategies]]) описаны в `STRATEGY_DESCRIPTIONS_RU` (src/dashboard/strategy_descriptions.py:14–153) — это детализированные RU-описания для вкладки Fail Analysis, но не для Documentation tab. Экспериментальная ML-стратегия [[kronos-ml-strategy]] в Documentation tab также не вынесена. Если в `STRATEGIES_DOC` их нет, значит их карточки туда не добавлены. Полную карту всех семи стратегий даёт [[strategies-overview]].

Чтобы понять стратегии глубже — читайте [[02-стратегии/README|раздел 02-стратегии]] (live-логика on_bar) и [[06-бэктест-и-валидация/README|раздел 06-бэктест-и-валидация]] (как они проходили бэктест).

---

### Раздел METHODOLOGY — карточки методологии

Методология — это «правила игры»: как именно бот проверяет, работает ли стратегия, и по каким критериям выносит вердикт. Без понимания этого раздела результаты бэктеста (DSR=0.996, MC p=0.018, T6 ≥ 0.7) — просто набор чисел. Те же четыре темы разобраны в контексте чтения результатов на вкладках [[wfa-methodology]], [[dsr-and-mc]] и [[metrics-table-tiers]].

Интерфейс:

```typescript
export interface MethodologyDoc {
  name?: string
  purpose?: string
  source?: string
  description?: string   // HTML
  formula?: string
  params?: string        // HTML
  interpretation?: string[]
  criteria?: MethodologyCriteria[]
}

export interface MethodologyCriteria {
  id: string       // "T1", "T2", ..., "T6"
  metric: string   // что измеряет
  threshold: string // порог прохождения
  note: string     // HTML — дополнительное пояснение
}
```

(src/dashboard_react/src/api/types.ts:123–139)

Все поля опциональны (`?`) — карточка адаптируется к тому, что есть. Компонент `MethodologyCard` показывает только непустые секции. (src/dashboard_react/src/components/tabs/DocumentationTab.tsx:170–237)

В коде задано **4 карточки методологии** (src/dashboard/backtest_runner.py:750–837):

#### 1. Walk-Forward Analysis (WFA)

**Что это:** способ честной проверки стратегии. Вместо того чтобы обучить стратегию на всех исторических данных и сказать «она хороша», WFA делит данные на K=5 последовательных фрагментов (фолдов). На каждом фолде стратегия «обучается» на одном периоде и тестируется на следующем (out-of-sample). Это имитирует реальную работу: мы никогда не знаем будущего.

Параметры нашей WFA: K=5 фолдов, train=2000 баров, test=500 баров, embargo=20 баров (промежуток между train и test, чтобы информация не «перетекала»). Источник: ADR 0014.

Подробно: [[06-бэктест-и-валидация/walk-forward-analysis]].

#### 2. Deflated Sharpe Ratio (DSR)

**Что это:** поправка к коэффициенту Шарпа за «накрученность». Если вы протестируете 100 случайных стратегий, хотя бы одна случайно покажет красивый Sharpe — не потому что она хороша, а по теории вероятностей. DSR учитывает, сколько стратегий было проверено (N_trials), и «штрафует» наблюдаемый Sharpe пропорционально этому числу.

DSR ≥ 0.95 = высокая уверенность, что результат не случаен после всех поправок.

Карточка содержит формулу (Bailey & López de Prado 2014, eq. 13), которая в UI отображается в блоке `formulaBlock`. (src/dashboard_react/src/components/tabs/DocumentationTab.tsx:187–189)

Подробно: [[03-индикаторы-и-расчёты/dsr-metric]] и [[06-бэктест-и-валидация/deflated-sharpe-ratio]].

#### 3. MC Permutation Test (sign-flip)

**Что это:** статистический тест «могли ли мы получить такой же результат случайно?». Бот берёт реальные доходности по каждой сделке и 2000 раз случайно переворачивает их знаки (+/-). Если случайные перестановки часто дают такой же или лучший средний результат — значит, стратегия статистически неотличима от случайного угадывания.

p < 0.05 = статистически значимый результат (по стандарту науки — 5% вероятность ошибки).

Карточка содержит список интерпретаций (3 пункта) — он отображается через `meth.interpretation.map(...)`. (src/dashboard_react/src/components/tabs/DocumentationTab.tsx:197–205)

Подробно: [[03-индикаторы-и-расчёты/mc-permutation-test]] и [[06-бэктест-и-валидация/monte-carlo-permutation]].

#### 4. Acceptance Criteria T1-T6

**Что это:** шесть предварительно зарегистрированных критериев, которые стратегия ОБЯЗАНА пройти одновременно, чтобы получить вердикт PASS. Нельзя пройти «пять из шести» — нужны все шесть («conjoint» = одновременно).

В карточке задана таблица `criteria` (6 записей `MethodologyCriteria`), которая отображается как `<table>` в разделе «Criteria»:

| ID | Метрика | Порог | Пояснение |
|----|---------|-------|-----------|
| T1 | Sharpe OOS (annualized) | ≥ 1.0 | > 3.0 = почти наверняка overfit |
| T2 | Sortino OOS | ≥ 1.5 | Trend-following с positive skew должен иметь Sortino > Sharpe |
| T3 | Max Drawdown | < 25% | < 10% suspicious; trend-following BTC исторически 15–30% |
| T4 | Win rate × RR | ≥45%@RR≥1.5 OR ≥35%@RR≥2.0 | Trend-following 35–50%; > 65% suspicious |
| T5 | Mean expectancy + t-stat | > 0 + t-stat > 2.0 + n ≥ 100 | n ≥ 100 = минимум для t-test validity |
| T6 | OOS/IS Sharpe ratio | ≥ 0.7 | Главный детектор переобучения — деградация > 30% красный флаг |

(src/dashboard/backtest_runner.py:790–837)

Каждая метрика в этой таблице имеет свою страницу-справочник: T1/T2 — [[sharpe-sortino-metrics|Sharpe и Sortino]], T3/T4 — [[max-drawdown-winrate-rr|MaxDD, Win Rate и Risk-Reward]], T5/T6 — [[tstat-oos-is-metrics|t-статистика и OOS/IS Sharpe]].

**Замечание:** порог T5 в таблице `METHODOLOGY_DOC` указан как `n ≥ 100` (оригинальный порог). Поправка S34 (ADR 0052) снизила floor до 50 в коде gate, но карточка в `METHODOLOGY_DOC` не обновлялась — она отражает первоначальный acceptance_criteria.md. В `wfa_criterion_explanations.py` (строка 185) порог описан как «≥ 100 [original] OR ≥ 50 [S34 amended floor]». Текущий hard gate в коде: `T5_FLOOR = 50`.

Подробно: [[06-бэктест-и-валидация/acceptance-gates-t1-t6]].

---

### HTML-поля и безопасность

Несколько полей в данных содержат HTML-разметку: description, entry_logic, exit_logic, historical_results, best_for, tagline, tradeoff, params, note. React по умолчанию экранирует всё, что вставляется через `{}`, поэтому для этих полей используется `dangerouslySetInnerHTML={{ __html: value }}`.

Это намеренно и безопасно в нашем случае: HTML создаётся Python-разработчиками в коде (`backtest_runner.py`, `wfa_criterion_explanations.py`), а не приходит от пользователя. Комментарий в коде явно это фиксирует:

```
// XSS-safety note: HTML fields come from server-side authored dicts
// (not user input) — dangerouslySetInnerHTML is intentional.
```

(src/dashboard_react/src/components/tabs/DocumentationTab.tsx:4–6)

Простые текстовые поля (`name`, `id`, `default`, `category`) вставляются через `{}` и автоматически экранируются React.

## Примеры / сценарии

### Сценарий: читаем карточку RSI

Пользователь открывает Documentation tab → видит раздел INDICATORS → первая карточка RSI.

**Что отображается:**
- Шапка: «RSI» / «Relative Strength Index» / чип «Momentum oscillator»
- Автор: «J. Welles Wilder Jr. (1978)»
- Описание (HTML): «Oscillator момента, измеряющий силу... В нашем боте используется Wilder smoothing (α=1/n), не classical EMA. Стандартный period = 14 баров.»
- Формула: «RSI = 100 − [100 / (1 + RS)] где RS = avg_gain / avg_loss за period»
- Range: «0 — 100»
- Interpretation: 4 пункта (RSI < 30 — oversold; RSI > 70 — overbought; RSI 30–70 — neutral zone; Threshold relaxation...)
- Параметры в стратегиях: таблица из 3 строк (period=14; oversold=30 или 35; overbought=65 или 68 или 70)
- Источник: «Wilder, J.W. (1978) New Concepts in Technical Trading Systems»

**Почему параметры перечислены несколькими вариантами?** Потому что разные стратегии используют RSI с разными порогами: S15 классическая (30/70), S17 relaxed (35/65), EMA crossover (overbought=68).

### Сценарий: читаем карточку T6 в Acceptance Criteria

Пользователь видит в карточке «Acceptance Criteria T1-T6» → строку T6 → «OOS/IS Sharpe ratio» → «≥ 0.7» → пояснение «Главный детектор переобучения — деградация > 30% красный флаг».

Теперь, глядя на результат бэктеста на вкладке Backtest и видя «T6 fail», пользователь понимает: OOS Sharpe оказался менее 70% от IS Sharpe хотя бы на одном фолде. Это значит — стратегия «обучилась под прошлое» и не переносится на будущие данные.

### Сценарий: SL multiplier — что значит default 1.5?

Карточка «SL multiplier (Stop Loss)» показывает: `sl_atr_mult` · default = 1.5.

Если ATR(14) в данный момент = $500 (типичный дневной шаг BTC), то стоп-лосс размещается на $750 ниже цены входа (500 × 1.5 = 750). Это значит: при движении против нас на $750 бот автоматически закрывает позицию, ограничивая потерю. «Tradeoff»: узкий стоп = много мелких потерь; широкий стоп = редкие, но крупные потери.

## Подводные камни / что важно понимать

**1. Documentation tab — статичная вкладка (нет live-данных).** В отличие от вкладки Metrics или EquityChart, здесь всегда показывается одна и та же документация, захардкоженная в Python-коде. Обновляется только при деплое новой версии бота. (src/dashboard/backtest_runner.py:457–846)

**2. Три стратегии в STRATEGIES — не полный список проекта.** В `backtest_runner.py::STRATEGIES_DOC` описаны только EMA crossover, Mean-reversion S15, Mean-reversion S17 relaxed. Donchian Breakout, Volume Breakout и ATR-Adaptive Breakout имеют детализированные описания в `strategy_descriptions.py` (для вкладки Fail Analysis), но в Documentation tab не вынесены.

**3. Порог T5 в карточке «Acceptance Criteria» — устарел.** Карточка в `METHODOLOGY_DOC` (строка 824) показывает `n ≥ 100` — это оригинальный порог из acceptance-criteria.md. Поправка S34 (ADR 0052) снизила его до 50 в коде gate (`T5_FLOOR = 50`). Если видите «n ≥ 100» в Documentation tab и «n ≥ 50» в Fail Analysis — это не противоречие, а временная рассинхронизация карточки с кодом.

**4. HTML-поля — серверный контент.** Поля description, entry_logic, exit_logic, tradeoff, note могут содержать форматирование (жирный, курсив). Это не пользовательский ввод, а текст от разработчика. `dangerouslySetInnerHTML` безопасен именно потому, что источник — серверный Python-код.

**5. TODO S47: multiplier cards не полные.** Компонент `MultiplierCard` имеет комментарий `TODO S47 — full vanilla parity for multipliers details (range, impact table)` (строка 93). Это значит, что у карточек параметров пока нет таблицы диапазонов и таблицы влияния — они появятся в будущем.

**6. Данные загружаются каждый раз при первом показе вкладки.** Кэш на стороне клиента отсутствует — при каждом открытии вкладки делается запрос к серверу. Поскольку данные статичны, это нормально по производительности, но стоит иметь в виду при отладке (нужен сервер).

## Связанные документы

Вкладка Documentation — встроенный справочник, поэтому она пересекается почти со всеми разделами доков. Ниже связи сгруппированы по её четырём секциям плюс контекст дашборда.

**Секция INDICATORS — страницы-справочники индикаторов:**
- [[ema-rsi-indicators]] — EMA и RSI: карточки EMA и RSI в этой секции описывают эти же формулы
- [[atr-indicator]] — ATR: индикатор, на котором построены все множители SL/TP
- [[bollinger-bands-indicator]] — Bollinger Bands: карточка BB в секции INDICATORS
- [[adx-indicator]] — ADX: карточка ADX (сила тренда, не направление)
- [[technical-indicators]] — общий справочник по всем пяти индикаторам (02-стратегии): математика и назначение

**Секция MULTIPLIERS — расчёт стопов и размера позиции:**
- [[wilder-atr-and-stops]] — как ATR-множители превращаются в реальные уровни стоп-лосса и тейк-профита
- [[position-sizing-kelly]] — реальный размер позиции в live считается по Келли; `position_size_pct` — лишь верхняя граница
- [[circuit-breakers-drawdown-flash]] — `max_drawdown_pct` в бэктесте vs. автоматические предохранители просадки в live

**Секция STRATEGIES — профили стратегий:**
- [[ema-crossover-strategy]] — EMA crossover (S13 baseline): карточка стратегии в этой секции
- [[mean-reversion-strategy]] — Mean-reversion S15 и S17: две карточки mean-reversion в этой секции
- [[breakout-strategies]] — Donchian/Volume/ATR breakout: упомянуты, но в Documentation tab карточек не имеют
- [[kronos-ml-strategy]] — Kronos ML: тоже вне Documentation tab, но часть проекта
- [[strategies-overview]] — карта всех семи стратегий проекта

**Секция METHODOLOGY — как проверяется стратегия:**
- [[walk-forward-analysis]] — полное описание WFA: как разбиваются фолды, что значат параметры train/test/embargo
- [[acceptance-gates-t1-t6]] — детальная механика каждого из шести gate с реальными числами и кодом
- [[dsr-metric]] — как считается DSR и почему используется fisher=False (Pearson kurtosis)
- [[deflated-sharpe-ratio]] — DSR в контексте бэктест-пайплайна: поправка на множественные попытки
- [[mc-permutation-test]] — sign-flip тест: seed=42, +1 в знаменателе (p = (count+1)/(N+1))
- [[monte-carlo-permutation]] — MC-тест перестановок в контексте бэктест-валидации
- [[sharpe-sortino-metrics]] — метрики T1/T2 из таблицы Acceptance Criteria
- [[max-drawdown-winrate-rr]] — метрики T3/T4 из таблицы Acceptance Criteria
- [[tstat-oos-is-metrics]] — метрики T5/T6 (t-статистика и OOS/IS Sharpe) из таблицы

**Контекст дашборда — соседние вкладки:**
- [[dashboard-overview]] — обзор всего дашборда и списка вкладок, включая Documentation
- [[glossary-tab]] — вкладка-близнец: тоже встроенный справочник терминов внутри дашборда
- [[fail-analysis-tab]] — другая вкладка, где детализированные описания стратегий из strategy_descriptions.py отображаются в контексте конкретного провала
- [[wfa-methodology]] — те же карточки методологии в контексте понимания результатов бэктеста
- [[dsr-and-mc]] — DSR и MC в контексте чтения вердикта на вкладке результатов
- [[metrics-table-tiers]] — таблица метрик T1-T6 в контексте вкладки Backtest
- [[verdict-and-warnings]] — как вердикт PASS/FAIL/RAW появляется после прохождения через эти самые criteria

За техническими деталями реализации WFA-pipe смотри: `llm-wiki/wiki/project/components/wfa.md`.
