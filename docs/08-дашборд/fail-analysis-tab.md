---
title: "Детальный разбор провала стратегии"
section: "08-дашборд"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/dashboard_react/src/components/shared/FailAnalysisTab.tsx, src/dashboard/strategy_descriptions.py, src/dashboard/wfa_criterion_explanations.py
---

# Детальный разбор провала стратегии

**TL;DR:** Вкладка «FailAnalysisTab» появляется автоматически, когда стратегия не прошла проверку — и объясняет человеческим языком: что именно не так, какие критерии сломались и где конкретно в прогоне по временным периодам всё пошло не так.

---

## Простыми словами

Представьте, что вы наняли сотрудника и поставили ему испытательный срок. Через три месяца он провалил итоговую аттестацию. Хороший HR-отдел не просто скажет «не прошёл» — он составит детальный отчёт: по каким пунктам завалил, где именно допустил ошибки, и что за человек вообще (его биография и логика).

Именно это и делает вкладка «Детальный разбор провала стратегии». Она появляется только тогда, когда стратегия получила вердикт **WFA_FAIL**, **WFA_FAIL_DATA** или **FAIL** — то есть не прошла строгую проверку walk-forward (о самой системе проверки — в [[acceptance-gates-t1-t6]]). Как читается сам вердикт до раскрытия детального разбора — в [[verdict-and-warnings]].

Вкладка состоит из трёх частей:

1. **Кто такая эта стратегия** — полное описание: как она принимает решения о входе и выходе, для какого рынка создавалась, какой результат показала раньше и почему провалилась сейчас.
2. **Какие критерии прошла, какие нет** — наглядный список из 10 критериев с зелёными галочками и красными крестами.
3. **Разбор по временным окнам** — таблица с результатами каждого отдельного «испытания» (фолда), чтобы понять: проблема была везде или только в отдельных периодах.

---

## Как это работает у нас

### Когда вкладка появляется

В `App.tsx` определён набор «плохих» вердиктов:

```typescript
const FAILED_VERDICTS = new Set<Verdict>(['WFA_FAIL', 'WFA_FAIL_DATA', 'FAIL'])
```

Вкладка рендерится только если:

```typescript
{result && FAILED_VERDICTS.has(result.verdict) && (
  <FailAnalysisTab result={result} />
)}
```

(src/dashboard_react/src/App.tsx:17, 91-93)

Вкладка находится внутри вкладки «01 BACKTEST», между таблицей метрик и таблицей сделок — после того как видны все числа, читатель видит объяснение. При вердикте **WFA_PASS** или **PASS** вкладка не появляется вовсе.

### Как загружается описание стратегии (Секция 1)

При монтировании компонента запускается `useEffect`, который делает запрос к API:

```typescript
api.getStrategyExplanation(result.request.strategy_id)
```

(src/dashboard_react/src/components/shared/FailAnalysisTab.tsx:59)

API-вызов идёт на `GET /api/strategy_explanation/{preset_id}`. Бэкенд (`src/dashboard/app.py:291-297`) берёт текст из словаря `STRATEGY_DESCRIPTIONS_RU` по ключу `preset_id` и возвращает JSON `{"preset_id": "...", "description_ru": "..."}`.

Текст описания разбивается на абзацы по `\n\n` и рендерится с поддержкой **жирного текста**: функция `renderBoldMarkdown()` разбивает строку по маркерам `**...**` и оборачивает выделенные части в `<strong>` — без использования небезопасного `dangerouslySetInnerHTML`. (src/dashboard_react/src/components/shared/FailAnalysisTab.tsx:39-44, 97-99)

Пока данные грузятся — показывается «Загрузка детального разбора...». Если запрос завершился ошибкой — «Ошибка загрузки: {сообщение об ошибке}».

### Описания стратегий: что внутри

Все тексты хранятся в `STRATEGY_DESCRIPTIONS_RU` (src/dashboard/strategy_descriptions.py:14). Для каждого пресета есть шесть смысловых блоков:

| Блок | Что объясняет |
|---|---|
| Логика входа (LONG) | Какие условия должны выполниться одновременно, чтобы бот открыл позицию |
| Логика выхода | При каких событиях позиция закрывается (обратный сигнал / ATR-стоп / тейк-профит) |
| Параметры | Конкретные числа — периоды, множители, пороги — и что они означают |
| Целевой режим рынка | При каком характере рынка стратегия должна работать (тренд / боковик) |
| Исторический контекст | Кто придумал алгоритм, когда, на чём тестировался |
| Вердикт | Конкретный результат нашего бэктеста: что сломалось и почему |

Поддерживаемые пресеты (ключи словаря): `ema_crossover_s13`, `mean_reversion_s15`, `mean_reversion_s17_relaxed`, `donchian_breakout_s35`, `volume_breakout_iter10`, `atr_breakout`. Если в запросе придёт неизвестный `preset_id`, функция `get_strategy_description()` вернёт `None`, и бэкенд ответит 404. (src/dashboard/strategy_descriptions.py:156-158)

### Список критериев: chip-список (Секция 2)

В компоненте зашит канонический список всех 10 критериев:

```typescript
const ALL_CRITERIA = [
  // Gate-blocking (блокирующие)
  't5_floor', 'sharpe_gate', 'mc_gate', 'dsr_threshold', 'n_eff_threshold',
  // Informational (информационные)
  't1', 't2', 't3', 't4', 't6',
]
```

(src/dashboard_react/src/components/shared/FailAnalysisTab.tsx:17-22)

Для каждого критерия из `ALL_CRITERIA` компонент ищет его имя в массиве `result.failed_criteria` (который приходит из бэкенда — это список строк, например `["t5_floor", "mc_gate"]`). Если критерий есть в списке провалившихся — на него вешается красный чип «✗ Провален», если нет — зелёный «✓ Пройден». (src/dashboard_react/src/components/shared/FailAnalysisTab.tsx:107-120)

Рядом с каждым критерием есть ссылка `→ glossary`, которая ведёт во [[glossary-tab|вкладку «04 GLOSSARY»]] с якорем `#glossary-{critId}`. Ссылка не открывает новую страницу — она меняет URL-параметр внутри того же SPA.

Человеко-читаемые названия критериев:

| Ключ в коде | Что отображается |
|---|---|
| `t5_floor` | T5 · Trade count (gate-blocking) |
| `sharpe_gate` | Fold OOS/IS Sharpe (gate-blocking) |
| `mc_gate` | Monte Carlo p-value (gate-blocking) |
| `dsr_threshold` | DSR (gate-blocking) |
| `n_eff_threshold` | Effective sample size (gate-blocking) |
| `t1` | T1 · Sharpe OOS (informational) |
| `t2` | T2 · Sortino OOS (informational) |
| `t3` | T3 · Max Drawdown (informational) |
| `t4` | T4 · Win Rate (informational) |
| `t6` | T6 · OOS/IS Sharpe ratio (informational) |

(src/dashboard_react/src/components/shared/FailAnalysisTab.tsx:24-35)

### Разбор по фолдам (Секция 3)

Фолд — это один временной период внутри walk-forward анализа. Например, если история разбита на 5 фолдов, каждый фолд — это тренировочный кусок + тестовый кусок. Подробно о механике WFA — в [[walk-forward-analysis]] (в дашборд-версии — [[wfa-methodology]]).

Секция 3 появляется только если `result.fold_sharpe_ratios` не пустой массив:

```typescript
{folds.length > 0 && (
  <section>…таблица…</section>
)}
```

(src/dashboard_react/src/components/shared/FailAnalysisTab.tsx:124)

В таблице для каждого фолда показаны:
- **Фолд** — порядковый номер (начиная с 0)
- **OOS/IS Sharpe** — отношение коэффициента Шарпа на тестовом периоде к коэффициенту на тренировочном. Близко к 1.0 — хорошо (стратегия не «переобучилась»). Ниже 0.7 — фолд провален. Ниже 0 — стратегия в тестовом периоде теряла деньги, когда на тренировочном зарабатывала (классический признак переобучения).
- **Статус** — один из трёх вариантов: `✓ ≥ 0.7` (пройден), `⚠ low` (ниже порога, но не помечен как failed), `✗ < 0.7 (фолд failed)`.

Цветовое кодирование определяется так (src/dashboard_react/src/components/shared/FailAnalysisTab.tsx:137-148):

```typescript
const isFailed = failedFolds.has(i)            // индекс фолда есть в failed_folds?
const cls = isFailed
  ? styles.foldFail                            // красный
  : s >= 0.7
  ? styles.foldPass                            // зелёный
  : styles.foldWarn                            // жёлтый (s < 0.7, но не в failed_folds)
```

Порог **0.7** — это стандартный порог L1 gate из `evaluate_acceptance_gate()` в walk_forward.py:

```python
sharpe_threshold: float = 0.7   # default
```

(src/backtest/walk_forward.py:159)

---

## Что значат критерии: gate-blocking vs informational

Важное разграничение: не все критерии одинаково важны для вердикта.

### Блокирующие (gate-blocking) — провал любого из них = FAIL

| Критерий | Что проверяет | Порог | Откуда |
|---|---|---|---|
| `t5_floor` | Минимальное количество сделок в OOS | n ≥ 50 | walk_forward.py:211; ADR 0014 §S44 |
| `sharpe_gate` | [[tstat-oos-is-metrics\|OOS/IS Sharpe]] каждого фолда ≥ 0.7 | ratio ≥ 0.7 | walk_forward.py:196-198; ADR 0014 §T6 |
| `mc_gate` | [[monte-carlo-permutation\|Monte Carlo p-value]] ≤ 0.05 | p ≤ 0.05 | walk_forward.py:199; ADR 0015 |
| `dsr_threshold` | [[deflated-sharpe-ratio\|DSR (Deflated Sharpe Ratio)]] ≥ 0.95 | DSR ≥ 0.95 | dsr.py; ADR 0056 |
| `n_eff_threshold` | Эффективный размер выборки ≥ 50 | n_eff ≥ 50 | walk_forward.py:205-207; ADR 0052 |

### Информационные — провал НЕ блокирует вердикт, но показывает проблему

| Критерий | Что проверяет | Порог для PASS |
|---|---|---|
| `t1` | [[sharpe-sortino-metrics\|Коэффициент Шарпа]] (OOS, аннуализированный) | ≥ 1.0 |
| `t2` | [[sharpe-sortino-metrics\|Коэффициент Сортино]] (только просадки в знаменателе) | ≥ 1.5 |
| `t3` | [[max-drawdown-winrate-rr\|Максимальная просадка]] (peak-to-trough) | < 25% |
| `t4` | [[max-drawdown-winrate-rr\|Процент прибыльных сделок]] + среднее соотношение прибыли к убытку | (WR ≥ 45% AND RR ≥ 1.5) ИЛИ (WR ≥ 35% AND RR ≥ 2.0) |
| `t6` | Среднее [[tstat-oos-is-metrics\|OOS/IS Sharpe]] по всем фолдам | ≥ 0.7 |

Подробные формулы T1-T6 и DSR — в [[acceptance-gates-t1-t6]] (функция-за-функцией из `strategy_metrics.py` и `dsr.py`). Отдельные метрики по темам: [[sharpe-sortino-metrics|Sharpe/Sortino]] (T1/T2), [[max-drawdown-winrate-rr|MaxDD/Win Rate/RR]] (T3/T4), [[tstat-oos-is-metrics|T-статистика и OOS/IS Sharpe]] (T5/T6). В дашборде та же таблица разобрана в [[metrics-table-tiers]]. Здесь — только угол «как читать в UI».

---

## Примеры / сценарии

### Сценарий А: EMA Crossover (ema_crossover_s13)

Пользователь нажимает «Запустить бэктест» для стратегии [[08-дашборд/ema-crossover-strategy|EMA Crossover]]. Приходит ответ с `verdict: "FAIL"`.

Что появится на экране:

**Секция 1** — текст из `STRATEGY_DESCRIPTIONS_RU["ema_crossover_s13"]`:
> «EMA Crossover (S13 baseline) — классическая trend-following стратегия… Вердикт S13: FAIL conjoint, T1=−44.46 OOS Sharpe на BTC 1H. Стратегия систематически проигрывает…»

(src/dashboard/strategy_descriptions.py:16-35)

**Секция 2** — chip-список. Если `failed_criteria = ["t5_floor", "mc_gate", "sharpe_gate"]`, то три критерия получат красный чип «✗ Провален», остальные семь — зелёный «✓ Пройден».

**Секция 3** — таблица фолдов не появится, если `fold_sharpe_ratios = []` (простой FAIL без WFA).

---

### Сценарий Б: ATR Breakout (WFA_FAIL_DATA)

Для [[atr-breakout-strategy|`atr_breakout`]] на BTCUSDT 1D приходит `verdict: "WFA_FAIL_DATA"`. Это означает, что данных недостаточно для проведения walk-forward: 1212 баров против минимально необходимых 4520 (train=2000 + test=500 × 5 фолдов + embargo). (src/dashboard/strategy_descriptions.py:147)

Текст в Секции 1 объяснит именно это. В Секции 2 появится критерий `t5_floor` с красным чипом — потому что при `WFA_FAIL_DATA` тест на количество сделок тоже не выполнен. Секция 3 будет пустой: если WFA не смог отработать из-за нехватки данных, массив `fold_sharpe_ratios` вернётся пустым.

---

### Сценарий В: Volume Breakout (WFA_FAIL с подробной таблицей фолдов)

Для [[volume-breakout-strategy|`volume_breakout_iter10`]] приходит WFA_FAIL с `fold_sharpe_ratios = [1.23, 0.85, 0.41, 0.62, 0.18]` и `failed_folds = [2, 4]`.

Таблица фолдов будет выглядеть примерно так:

| Фолд | OOS/IS Sharpe | Статус |
|---|---|---|
| #0 | 1.2300 | ✓ ≥ 0.7 |
| #1 | 0.8500 | ✓ ≥ 0.7 |
| #2 | 0.4100 | ✗ < 0.7 (фолд failed) |
| #3 | 0.6200 | ⚠ low |
| #4 | 0.1800 | ✗ < 0.7 (фолд failed) |

Фолды #2 и #4 — красные. Фолд #3 — жёлтый (ниже 0.7, но не вошёл в `failed_folds` по логике бэкенда). Этот разбор помогает понять: стратегия нестабильна — в одних периодах она работает (фолды #0, #1), в других разрушается (фолды #2, #4).

---

## Подводные камни / что важно понимать

**1. Чип «✓ Пройден» у информационного критерия — не значит «всё хорошо».**
Список ALL_CRITERIA включает и блокирующие, и информационные критерии в один ряд. Если `t1`, `t2`, `t3`, `t4`, `t6` все зелёные, но `sharpe_gate` красный — стратегия всё равно провалена. Определяющие — только блокирующие (gate-blocking).

**2. Секция 3 (фолды) появляется только при WFA-пути.**
Если стратегия прошла простой бэктест без walk-forward (вердикт `FAIL` вместо `WFA_FAIL`) — массив `fold_sharpe_ratios` будет пустым и таблица не покажется. Это не баг — это корректное поведение.

**3. «✗ Провален» vs «⚠ low» у фолдов — разные источники.**
`failed_folds` — список, который формирует бэкенд в `evaluate_acceptance_gate()`. Там фолд падает в `failed_folds`, если его OOS/IS Sharpe ниже порога 0.7. Жёлтый статус `⚠ low` назначается фронтендом: если фолд не в `failed_folds`, но его значение всё равно ниже 0.7 — это жёлтый. Такой сценарий возможен при нестандартном вызове evaluate_acceptance_gate с другим `sharpe_threshold`. (src/backtest/walk_forward.py:159, 193-198)

**4. DSR — блокирующий по названию чипа, но информационный по коду.**
В UI критерий `dsr_threshold` помечен как `(gate-blocking)`. Однако в комментарии к `wfa_criterion_explanations.py` и в docstring `walk_forward.py` указано: «DSR is computed and reported (informational) but NOT в gate decision». На практике отдельные runner'ы (например, [[donchian-runner-and-reference-run|donchian_runner.py]]) могут добавлять `dsr_threshold` в `failed_criteria` локально. Вопрос о том, когда именно DSR блокирует — в [[deflated-sharpe-ratio]] (в дашборд-версии — [[dsr-and-mc]]).

**5. Описание стратегии загружается асинхронно — при медленной сети будет задержка.**
Если API-сервер не запущен или недоступен, появится «Ошибка загрузки: …» вместо описания. Данные о `failed_criteria` и `fold_sharpe_ratios` приходят сразу в теле основного ответа и задержки не имеют.

**6. Имена критериев в UI фиксированы в коде фронтенда.**
Если бэкенд добавит новый критерий, не попавший в `HUMAN_READABLE`, UI покажет сырой ключ вместо человеко-читаемого названия: `HUMAN_READABLE[critId] ?? critId`. Это предусмотрено как fallback. (src/dashboard_react/src/components/shared/FailAnalysisTab.tsx:114)

---

## Связанные документы

**Ворота и WFA (что именно проверяется):**
- [[acceptance-gates-t1-t6]] — полная логика L1-L4 gate cascade и формулы всех 10 критериев (t5_floor, sharpe_gate, mc_gate, dsr_threshold, n_eff_threshold + T1-T6) из кода
- [[walk-forward-analysis]] — что такое фолды, как строится WFA, откуда берётся OOS/IS Sharpe (источник Секции 3)
- [[deflated-sharpe-ratio]] — формула DSR (Bailey & López de Prado 2014) функция-за-функцией; критерий `dsr_threshold`
- [[monte-carlo-permutation]] — механика sign-flip теста и почему порог p ≤ 0.05; критерий `mc_gate`

**Отдельные метрики (по темам, из chip-списка):**
- [[sharpe-sortino-metrics]] — T1/T2: коэффициенты Шарпа и Сортино, аннуализация
- [[max-drawdown-winrate-rr]] — T3/T4: максимальная просадка, win rate и risk-reward
- [[tstat-oos-is-metrics]] — T5/T6 + sharpe_gate: t-статистика, минимум 50 сделок, отношение OOS/IS Sharpe (ключ Секции 3)

**Дашборд — соседние вкладки/панели:**
- [[verdict-and-warnings]] — как читать сам вердикт (WFA_FAIL / WFA_FAIL_DATA / FAIL), который включает эту вкладку
- [[metrics-table-tiers]] — таблица метрик T1-T6 в UI: gate-blocking vs informational (та же дихотомия, что в chip-списке)
- [[dsr-and-mc]] — DSR и Monte Carlo для нетехнического читателя (дашборд-версия статистических ворот)
- [[wfa-methodology]] — суть WFA в дашборде: train/test, фолды (дашборд-версия walk-forward)
- [[glossary-tab]] — вкладка глоссария, на которую ведут ссылки `→ glossary` из chip-списка
- [[run-backtest-form]] — форма запуска, из которой приходит `verdict` и запускается эта вкладка
- [[dashboard-overview]] — общий обзор дашборда и место вкладки FailAnalysisTab среди других
- [[history-tab]] — история прошлых прогонов: там сохраняются те же вердикты и наборы `failed_criteria`

**Стратегии, чьи описания рендерит Секция 1:**
- [[strategies-overview]] — карта всех 7 стратегий (источник текстов `STRATEGY_DESCRIPTIONS_RU`)
- [[08-дашборд/ema-crossover-strategy]] — стратегия из Сценария А (FAIL)
- [[atr-breakout-strategy]] — стратегия из Сценария Б (WFA_FAIL_DATA)
- [[volume-breakout-strategy]] — стратегия из Сценария В (WFA_FAIL по фолдам)
- [[breakout-strategies]] — обзор пробойных стратегий (Donchian / Volume / ATR)
- [[08-дашборд/mean-reversion-strategy]] — ещё один поддерживаемый пресет (mean_reversion_s15/s17_relaxed)
- [[08-дашборд/kronos-ml-strategy]] — ML-стратегия с особым вердиктом RAW_PRETRAIN_LEAKAGE (контраст: у неё свой путь без ворот)

**Runner, добавляющий dsr_threshold локально:**
- [[donchian-runner-and-reference-run]] — эталонный WFA-прогон, который может помечать `dsr_threshold` в `failed_criteria`

За техническими деталями WFA-оркестратора: `llm-wiki/wiki/project/components/walk-forward.md`
