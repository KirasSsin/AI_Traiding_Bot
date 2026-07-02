---
title: "Как читать вердикт и предупреждения"
section: "08-дашборд"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/dashboard_react/src/components/metrics/VerdictPanel.tsx, src/dashboard_react/src/utils/verdicts.ts, src/dashboard/backtest_runner.py, src/dashboard/glossary_data.py
---

# Как читать вердикт и предупреждения

**TL;DR:** Дашборд показывает итоговую оценку стратегии одним словом — вердикт. Зелёный PASS означает, что стратегия прошла все строгие проверки. Красный FAIL — провалила хотя бы одну. Оранжевый RAW — исследовательский режим без строгих проверок. Рядом с вердиктом отображаются предупреждения трёх уровней серьёзности.

## Простыми словами

Представьте, что вы сдаёте экзамен из пяти обязательных вопросов. Если отвечаете на все правильно — получаете «зачёт». Если хотя бы один вопрос завален — «незачёт», и вы видите список проваленных вопросов. Иногда экзамен вообще не проводится: например, у вас слишком мало материала для полноценной проверки — тогда выдаётся специальная отметка вместо обычной оценки.

Вердикт — это и есть итоговая оценка, а чипы «FAILED CRITERIA» — список конкретно проваленных вопросов.

Предупреждения — отдельная история. Они не меняют вердикт, но сигнализируют об аномалиях: например, «стратегия слишком хорошо выглядит, возможно это случайность» или «данных мало для надёжной проверки».

## Как это работает у нас

### Семь возможных вердиктов

Все возможные значения вердикта описаны в TypeScript-типе (src/dashboard_react/src/api/types.ts:148):

```text
'WFA_PASS' | 'WFA_FAIL' | 'WFA_FAIL_DATA' | 'PASS' | 'FAIL' | 'RAW' | 'RAW_PRETRAIN_LEAKAGE_SUSPECTED'
```

На практике они делятся на два мира:

**Мир 1 — WFA-вердикты (для research-runners: atr_breakout, volume_breakout, supertrend, kronos).**
Назначаются функцией `run_research_wfa` в src/backtest/research_wfa.py (общий каркас этих прогонов описан в [[research-kernel-execution-model|research-ядре исполнения]]):

| Вердикт | Что означает |
|---|---|
| `WFA_PASS` | Все обязательные критерии пройдены в режиме walk-forward анализа |
| `WFA_FAIL` | Хотя бы один критерий не пройден |
| `WFA_FAIL_DATA` | Данных недостаточно для проведения WFA (меньше минимально необходимого числа баров) |

Строчка присвоения вердикта (src/backtest/research_wfa.py:350):
```python
verdict = "WFA_PASS" if not failed_criteria else "WFA_FAIL"
```

Если данных не хватает — сразу возвращается `WFA_FAIL_DATA` без расчётов (src/backtest/research_wfa.py:162).

**Мир 2 — классические вердикты (для стандартного WFA-пайплайна через `run_wfa_single_symbol` — см. [[single-symbol-wfa-and-data-loading|загрузку данных и WFA для одного символа]]).**
Назначаются функцией `_compute_verdict` в backtest_runner.py:

| Вердикт | Что означает |
|---|---|
| `PASS` | Все gate-blocking критерии пройдены |
| `FAIL` | Хотя бы один gate-blocking критерий не пройден |

Строчка (src/dashboard/backtest_runner.py:367):
```python
verdict = "PASS" if not failed_criteria else "FAIL"
```

**Мир 3 — исследовательские (research) вердикты.**
`RAW` и `RAW_PRETRAIN_LEAKAGE_SUSPECTED` — особый случай. Эти два вердикта вынесены в отдельное множество `RESEARCH_VERDICTS` (src/dashboard_react/src/utils/verdicts.ts:15–18):

```typescript
export const RESEARCH_VERDICTS: ReadonlySet<Verdict> = new Set<Verdict>([
  'RAW',
  'RAW_PRETRAIN_LEAKAGE_SUSPECTED',
])
```

### Что означает RAW и почему он не красный

`RAW` — это не провал. Это честная пометка: «этот прогон сделан на всей исторической истории без строгого разделения на обучающую и тестовую выборки». Проверки (acceptance gates) при этом не проводятся вовсе.

`RAW_PRETRAIN_LEAKAGE_SUSPECTED` — ещё честнее: [[08-дашборд/kronos-ml-strategy|Kronos]] ML-модель, судя по всему, обучалась на тех же данных BTC, которые мы используем в бэктесте (подробно — [[kronos-data-leakage|почему это подозрение на утечку данных]]). Поэтому результаты могут быть искусственно завышены, и любая «проверка» здесь была бы лишена смысла. Вердикт присваивается жёстко в `_kronos_dispatch` разведочного [[kronos-exploratory-runner|прогона Kronos]] и передаётся через параметр `verdict_override` (src/backtest/research_runner_envelope.py:60, 114).

Функция `isResearchVerdict()` (src/dashboard_react/src/utils/verdicts.ts:21–23) проверяет, попадает ли вердикт в `RESEARCH_VERDICTS`, и если да — UI рендерит сокращённый «исследовательский» вид вместо полного экрана с acceptance-gate метриками. Это предотвращает ситуацию, когда RAW-вердикт ошибочно показывается как «красный провал WFA» (баг DASH-01, закрыт в S55).

### Цветовая палитра

Цвета назначаются функцией `verdictClass()` в VerdictPanel.tsx (src/dashboard_react/src/components/metrics/VerdictPanel.tsx:9–24) и реализованы в VerdictPanel.module.css:

| Вердикт | Цвет | CSS-класс |
|---|---|---|
| `PASS`, `WFA_PASS` | Зелёный (neon success) | `.verdictPass` |
| `RAW`, `RAW_PRETRAIN_LEAKAGE_SUSPECTED` | Оранжевый (Anthropic orange) | `.verdictRaw` |
| `WFA_FAIL_DATA` | Жёлтый (warn) | `.verdictFailData` |
| `FAIL`, `WFA_FAIL` | Красный (danger) | `.verdictFail` |

Важно: зелёный — это не «terminal green», а cyberpunk neon palette согласно ADR 0040 amendment (src/dashboard_react/src/components/metrics/VerdictPanel.tsx:46).

### Как вычисляется вердикт PASS/FAIL: функция `_compute_verdict`

Это ключевая функция (src/dashboard/backtest_runner.py:336–368). Принимает пять аргументов и возвращает список провалившихся критериев + строку вердикта.

```python
def _compute_verdict(
    n_trades: int,
    dsr_pass: bool,
    mc_pass: bool,
    failed_folds: list[int],
    n_eff: int,
) -> tuple[list[str], str]:
```

Пять gate-blocking критериев (все пять должны пройти одновременно):

| Код критерия | Проверка | Порог |
|---|---|---|
| `t5_floor` | Число OOS-сделок | n_trades ≥ 50 |
| `sharpe_gate` | Коэффициент Шарпа OOS/IS по каждому фолду | OOS/IS ≥ 0.7 по каждому фолду |
| `mc_gate` | Тест на случайность (Monte Carlo) | p-value ≤ 0.05 |
| `dsr_threshold` | Дефлированный коэффициент Шарпа | DSR > 0 (dashboard) |
| `n_eff_threshold` | Эффективный размер выборки | n_eff ≥ 50 |

Пороги n_trades и n_eff жёстко закреплены константами (src/dashboard/backtest_runner.py:332–333):
```python
_N_TRADES_FLOOR = 50
_N_EFF_FLOOR = 50
```

Для research-runners (WFA-путь) используются те же числовые пороги, но определены в research_wfa.py (src/backtest/research_wfa.py:37–41):
```python
DSR_THRESHOLD = 0.95   # порог DSR для research-runners
SHARPE_THRESHOLD = 0.7
P_THRESHOLD = 0.05
N_EFF_THRESHOLD = 50
T5_FLOOR = 50
```

**Важное различие:** в dashboard-пути (`_compute_verdict`) критерий [[deflated-sharpe-ratio|DSR]] считается пройденным если `dsr_value > 0` (src/dashboard/backtest_runner.py:1312). В research-WFA-пути критерий строже: DSR ≥ 0.95 (src/backtest/research_wfa.py:37, 342–346).

Критерии T1/T2/T3/T4/T6 ([[sharpe-sortino-metrics|Sharpe, Sortino]], [[max-drawdown-winrate-rr|просадка, win rate]], [[tstat-oos-is-metrics|OOS/IS ratio]]) — **только информационные**. Они отображаются в MetricsTable, но не влияют на вердикт (src/dashboard/backtest_runner.py:1300–1302). Полный разбор порогов и логики приёмки — в [[acceptance-gates-t1-t6|воротах приёмки T1–T6]].

### Чипы FAILED CRITERIA

Если `failed_criteria` не пустой, под строкой вердикта появляется строка с чипами (src/dashboard_react/src/components/metrics/VerdictPanel.tsx:59–68):

```tsx
{failed_criteria.length > 0 && (
  <div className={styles.failedRow}>
    <span className={styles.failedLabel}>FAILED CRITERIA:</span>
    {failed_criteria.map((criterion) => (
      <span key={criterion} className={styles.chip}>
        {criterion.toUpperCase()}
      </span>
    ))}
  </div>
)}
```

Каждый чип — красный прямоугольник с кодом критерия заглавными буквами (например, `T5_FLOOR`, `MC_GATE`, `DSR_THRESHOLD`). Нажав на чип, можно перейти в [[glossary-tab|GlossaryTab]], где объясняется что именно означает этот критерий. Сами коды критериев сопоставляются с записями глоссария через `STRATEGY_TO_METRICS_MAP` (src/dashboard/glossary_data.py:445–627).

### Панель предупреждений

Если массив `warnings` не пустой — под блоком вердикта появляется панель (src/dashboard_react/src/components/metrics/VerdictPanel.tsx:72–88). Каждое предупреждение содержит три поля: уровень, код и сообщение.

Три уровня серьёзности:

| Уровень | Иконка | Цвет | CSS-класс |
|---|---|---|---|
| `high` | ⚠ | Красный | `.warnHigh` |
| `warn` | ▲ | Оранжевый/жёлтый | `.warnMid` |
| `info` | i | Голубой | `.warnInfo` |

Иконки и классы назначаются через объект `WARNING_ICON` и функцию `warningRowClass()` (src/dashboard_react/src/components/metrics/VerdictPanel.tsx:27–43).

## Формулы и расчёты

Подробные формулы WFA, DSR и Monte Carlo — в [[wfa-methodology]] и [[dsr-and-mc]]. Здесь описывается только то, что непосредственно влияет на вердикт в UI.

**Как вычисляется `dsr_pass` в dashboard-пути** (src/dashboard/backtest_runner.py:1312):

```python
dsr_pass = nan_safe(dsr_value) is not None and dsr_value > 0
```

Простыми словами: DSR считается пройденным, если он вычислен (не NaN) и положительный. Это мягче порога 0.95 из research_wfa.py — специально для dashboard-маршрута.

**Порог Sortino-anomaly guard** (src/dashboard/backtest_runner.py:1247–1252): если |[[sharpe-sortino-metrics|Sortino]]| > 50 при числе сделок < 100, значение заменяется на None и добавляется предупреждение `sortino_anomaly` уровня `info`. Это защита от артефактов малой выборки.

## Примеры / сценарии

### Сценарий 1: стратегия провалила MC-тест

Запускаем [[08-дашборд/ema-crossover-strategy|EMA Crossover]]. После WFA получаем: n_trades=87 (≥50 OK), все фолды прошли, DSR=0.15 (>0 OK), но [[mc-permutation-test|MC]] p=0.12 (>0.05 — провал). Результат в UI:

```text
▸ FINAL VERDICT
FAIL
FAILED CRITERIA: MC_GATE

WARNINGS
⚠  mc_noise    MC permutation p=0.120 > 0.10 — returns indistinguishable от random.
```

Цвет вердикта — красный. Один чип. Одно предупреждение уровня `high` (потому что p > 0.10 — ещё хуже порога 0.05).

### Сценарий 2: стратегия прошла все проверки

```text
▸ FINAL VERDICT
PASS
```

Нет чипов, нет предупреждений (или только `info`-уровень). Цвет — зелёный.

### Сценарий 3: ATR Breakout в режиме RAW

```text
▸ FINAL VERDICT
RAW

WARNINGS
⚠  raw_full_period    Acceptance gate skipped — WFA retrofit pending S43.
                       Displayed PnL is full-period training number, NOT OOS-validated.
▲  subperiod_robustness    Robustness: 3/5 sub-periods positive.
```

Цвет — оранжевый, не красный. Нет чипов FAILED CRITERIA (потому что gate не проводился — см. [[breakout-strategies|пробойные стратегии]], которые пока идут через research-путь). Предупреждение `raw_full_period` уровня `high` всегда добавляется в `build_research_runner_envelope` [[research-kernel-execution-model|research-ядра]] (src/backtest/research_runner_envelope.py:77–86).

### Сценарий 4: Kronos — RAW_PRETRAIN_LEAKAGE_SUSPECTED

```text
▸ FINAL VERDICT
RAW_PRETRAIN_LEAKAGE_SUSPECTED

WARNINGS
⚠  pretrain_leakage    Kronos pretrained on history possibly overlapping backtest period —
                        WFA OOS invalid, exploratory only, NOT a gate.
```

Предупреждение `pretrain_leakage` подставляется вместо `raw_full_period` (src/backtest/research_runner_envelope.py:114–126). Цвет — оранжевый. UI рендерит сокращённый исследовательский вид без acceptance-gate метрик.

### Сценарий 5: WFA_FAIL_DATA (мало данных)

Пользователь выбрал BTCUSDT 1D за три месяца (≈90 баров). Это меньше минимального порога (src/backtest/research_wfa.py:160–182):

```text
▸ FINAL VERDICT
WFA_FAIL_DATA
FAILED CRITERIA: DATA_VOLUME
```

Цвет — жёлтый. Означает «данных физически недостаточно для проведения WFA», а не «стратегия плохая».

## Подводные камни / что важно понимать

**RAW ≠ FAIL.** Самая частая ошибка — воспринимать оранжевый RAW как провал. Это исследовательский режим: проверок не было, вывод о качестве стратегии делать рано. Именно поэтому цвет оранжевый, а не красный.

**Два разных порога DSR.** В dashboard-пути (`_compute_verdict`) вердикт учитывает только знак DSR (>0). В research-WFA-пути порог жёстче: DSR ≥ 0.95. Если смотрите на числовое значение DSR в MetricsTable и оно, скажем, 0.4 — по dashboard-логике это PASS по DSR-критерию, но по research-логике это FAIL. Сравнивайте вердикт с путём исполнения, а не только с числом.

**T1–T6 информационные, не блокирующие.** [[sharpe-sortino-metrics|Sharpe]] OOS может быть 0.3 (ниже порога 1.0), но если все пять gate-blocking критериев пройдены — вердикт всё равно PASS. Блокируют вердикт только: `t5_floor`, `sharpe_gate`, [[monte-carlo-permutation|`mc_gate`]], [[deflated-sharpe-ratio|`dsr_threshold`]], `n_eff_threshold`. Как эти пять ворот соотносятся с полным набором T1–T6 — см. [[metrics-table-tiers|таблицу метрик]].

**WFA_FAIL_DATA ≠ стратегия плохая.** Жёлтый вердикт означает только нехватку исторических данных. Расширьте диапазон дат или выберите более мелкий таймфрейм (5M/15M дают больше баров за тот же период) прямо в [[run-backtest-form|форме запуска бэктеста]].

**Предупреждения появляются и при PASS.** Если стратегия прошла, но [[sharpe-sortino-metrics|Sharpe]] OOS > 3.0, добавляется предупреждение `overfit_sharpe` уровня `high` (src/dashboard/backtest_runner.py:1326–1333). Это сигнал подозрения на переобучение — стратегия слишком хорошо выглядит на истории, чтобы быть правдой (та же логика, что и за поправкой в [[dsr-and-mc|DSR]]).

**Autoscale WFA снижает надёжность.** Если данных 300–4519 баров (меньше ADR 0014 дефолта 4520), параметры [[walk-forward-analysis|WFA]] автоматически масштабируются вниз и добавляется предупреждение `wfa_autoscale` уровня `warn` (src/dashboard/backtest_runner.py:1441–1453). Метрики на урезанных окнах шумнее.

**Для Kronos вердикт жёстко зафиксирован.** Независимо от числа сделок и значений метрик, вердикт всегда `RAW_PRETRAIN_LEAKAGE_SUSPECTED` — это зашито в `_kronos_dispatch` через `verdict_override=VERDICT_RAW_PRETRAIN_LEAKAGE` (src/backtest/research_runner_envelope.py:17–20, 114).

## Связанные документы

**Соседние вкладки дашборда (та же панель результата):**
- [[dashboard-overview]] — общий обзор дашборда: где на экране находится VerdictPanel и как он связан с остальными блоками
- [[metrics-table-tiers]] — T1–T6 метрики: информационные (не блокируют) и gate-blocking, из которых складывается вердикт
- [[fail-analysis-tab]] — детальный разбор проваленных критериев с объяснениями (появляется при FAIL)
- [[glossary-tab]] — словарь всех кодов критериев и предупреждений (расшифровка чипов FAILED CRITERIA)
- [[run-backtest-form]] — форма запуска: её параметры (символ, даты, таймфрейм) определяют, будет ли вердикт WFA_FAIL_DATA
- [[dsr-and-mc]] — дашборд-объяснение DSR и Monte Carlo p-value, которые блокируют вердикт
- [[wfa-methodology]] — дашборд-объяснение walk-forward анализа (WFA) и того, как устроены фолды

**Пять gate-blocking критериев (что именно проверяет каждый порог):**
- [[acceptance-gates-t1-t6]] — канонический разбор ворот T1–T6, пороги и логика итогового PASS/FAIL
- [[deflated-sharpe-ratio]] — критерий `dsr_threshold`: два разных порога (≥0.95 в research-пути, >0 в dashboard-пути)
- [[dsr-metric]] — техническая глубина DSR (poправка Шарпа на множественные проверки)
- [[monte-carlo-permutation]] — критерий `mc_gate`: тест перестановок (p ≤ 0.05)
- [[mc-permutation-test]] — техническая глубина Monte Carlo permutation
- [[tstat-oos-is-metrics]] — критерий `t5_floor` (n_trades ≥ 50) и T6 (OOS/IS Sharpe за `sharpe_gate`)
- [[sharpe-sortino-metrics]] — Sharpe/Sortino за `sharpe_gate` и источник предупреждений `overfit_sharpe` / `sortino_anomaly`
- [[max-drawdown-winrate-rr]] — информационные T3/T4 (просадка, win rate), которые отображаются, но не блокируют

**WFA-контекст (откуда берутся числа вердикта):**
- [[walk-forward-analysis]] — фолды и OOS-выборки, на которых считаются gate-критерии; источник `wfa_autoscale`
- [[single-symbol-wfa-and-data-loading]] — путь классических вердиктов (`run_wfa_single_symbol`) и порог минимума баров (WFA_FAIL_DATA)
- [[wfa-reporter-three-sharpe-series]] — три разных «Шарпа» в системе: почему сравнивать вердикт нужно с путём исполнения, а не только с числом

**RAW и исследовательские вердикты (почему не красный):**
- [[research-kernel-execution-model]] — `build_research_runner_envelope`, `verdict_override` и предупреждение `raw_full_period`
- [[kronos-exploratory-runner]] — разведочный прогон Kronos, который жёстко присваивает RAW_PRETRAIN_LEAKAGE_SUSPECTED
- [[kronos-data-leakage]] — почему Kronos помечен подозрением на утечку данных (обоснование вердикта)
- [[kronos-ml-strategy]] — почему Kronos всегда получает RAW_PRETRAIN_LEAKAGE_SUSPECTED

За техническими деталями: llm-wiki/wiki/project/components/dashboard.md
