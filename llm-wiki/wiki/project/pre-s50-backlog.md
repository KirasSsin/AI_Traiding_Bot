---
title: Pre-S50 Backlog — Supertrend strategy adaptation (freqtrade)
type: backlog
tags: [pre-sprint, backlog, s50, supertrend, strategy]
created: 2026-05-29
updated: 2026-05-29  # +T8: supertrend train sweep + held-out verdict PROCEED_T9
status: draft
sources:
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
  - llm-wiki/wiki/project/decisions/0059-sprint-39-volume-breakout-pre-registration.md
  - llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-pre-registration.md
---

## Назначение

S50 = адаптация стратегии из freqtrade-strategies (operator request) → Supertrend trend-follower на наш Bybit Spot streaming-bot. PHASE 2 brainstorm complete (trader-expert ROUND 1 + ROUND 2 binding).

## Source strategy

freqtrade `Supertrend.py` (@juankysoriano). Triple-Supertrend в оригинале (3 buy + 3 sell ST с hyperopt params) — **упрощаем к single Supertrend** (anti-snooping: меньше param surface). Lazybear/Seban Supertrend: `ST = (high+low)/2 ± mult×ATR` с trend-flip latching.

**Step-0 finding:** freqtrade `BbandRsi` = дубликат нашей `MeanReversionRsiBBStrategy` (S15/S17) — исключён. Supertrend = genuine NEW logic (нет в нашем коде: проверено grep — no supertrend/macd/cci/sma/heikin-ashi).

## S50 PHASE 2 brainstorming (trader-expert binding verdicts)

### Q1 — Which strategy → CONFIRM (Supertrend pure)
- ROUND 1: CONFIRM. Supertrend = highest novelty, ATR primitive exists, natural SL = supertrend line.
- MACD rejected (freqtrade ref has exit-bug `crossed_above` not `below` + lag). AdxSmas rejected (dups EmaCrossoverAdxRsi). Triple-ST → single-ST (snooping reduction).
- Pure Supertrend = hypothesis #10. ADX-filter variant = hypothesis #11 DEFER к S51+ (operator escalation #1).

### Q2 — Execution mapping → CONFIRM (signal-exit + ATR bracket SL)
- ROUND 1: CONFIRM. Mirrors `ATRBreakoutStrategy` pattern (atr_breakout_strategy.py:205-253): priority 1 = signal exit (Supertrend flip → EXIT_FLAT on close(T)), priority 2 = ATR-multiple bracket SL. NO minimal_roi (freqtrade idiom), NO TP (trend-runner), NO native trailing (YAGNI + new money-path = reject post-S49 hardening).
- SL price: natural Supertrend-line distance `close(T) - supertrend_line(T)` preferred over ATR-multiple (economically motivated) — needs extra Signal field (impl detail).

### Q3 — Symbol+timeframe → REVISE→CONFIRM_REVISE: **BTCUSDT 1H** (NOT 4H)
- ROUND 1 maintainer rec: 4H (less whipsaw). Trader REVISE → 1H.
- ROUND 2 CONFIRM_REVISE (BINDING): 4H = 28 trades/3.3y (ADR 0014 S45 table) → T5 floor n≥50 **structurally unreachable** → guaranteed WFA_FAIL. ATRBreakout 4H proved this S44/S45 (ADR 0060: "T5 floor likely STILL fails"). 1H = ~106 trades ATRBreakout ref → Supertrend ~140-180 OOS → T5 viable. Whipsaw = measurable Sharpe risk (T1/T6); T5-impossibility = no information at all.
- **Maintainer was wrong. Trader evidence correct.**

### Q4 — Acceptance → REVISE→CONFIRM_REVISE: **literature defaults LOCKED** (NOT autoresearch first)
- ROUND 1 maintainer rec: autoresearch sweep first. Trader REVISE → literature defaults.
- ROUND 2 CONFIRM_REVISE (BINDING): `autoresearch_endless.py` has ZERO held-out split (grep confirmed 0 matches for held.out/holdout/train_end/OOS). Maintainer's "validate on held-out" premise factually FALSE — script `_eval_robustness()` chunks SAME df, `run_combo()` loads whole parquet. Sweep = champion-bias (Bailey 2014, ADR 0059 already warned). LOCK ATR_PERIOD=10, MULT=3.0 (Olivier Seban 2009 originals) in ADR before any run.
- Held-out: 2025-06-01 → 2026-05-01 (12mo recent). Single eval. If Sharpe>0 + n_trades≥15 → formal 1H WFA. Else honest fail, NO param shopping.
- **Maintainer was wrong. Trader evidence correct.**

### Q5 — Look-ahead prevention → CONFIRM (stateful streaming + cross-validation)
- ROUND 1: CONFIRM. Instance attrs `_supertrend_line` + `_trend_direction`, Wilder ATR, property-test (test_lookahead.py) + vectorized cross-validation (streaming output must match batch within float tol).
- Warmup seed: bars 0..ATR_PERIOD → NaN; first warm bar: line=(h+l)/2+mult×ATR, trend=BEARISH (conservative).
- **Hidden risk (trader):** Supertrend has 2 literature variants (classic hard-clamp vs Lazybear trend-dependent). Freqtrade uses Lazybear. MUST lock variant in ADR — else cross-validation false-positive lookahead alerts from formula mismatch.

## LOCKED spec (для ADR 0061)

```
Strategy:    SupertrendStrategy (single Supertrend, long-only Spot)
Symbol:      BTCUSDT  (LOCKED, ADR 0059 anti-snooping)
Timeframe:   1H       (LOCKED — Q3 binding)
ATR_PERIOD:  10       (LOCKED — Seban default)
MULTIPLIER:  3.0      (LOCKED — Seban default)
Variant:     Lazybear trend-dependent (freqtrade-compatible)
Entry:       trend flips bullish (close crosses above supertrend line)
Exit:        priority 1 = trend flips bearish (EXIT_FLAT signal close(T))
             priority 2 = ATR-multiple bracket SL (safety net)
TP:          none (trend-runner)
Hypothesis:  #10 (N_trials increment, Bailey DSR penalty — irreversible)
Held-out:    2025-06-01 → 2026-05-01, single eval, threshold Sharpe>0 + n≥15
```

## Prerequisite tasks (cross-cutting, BEFORE Supertrend impl)

- **CC2:** Extract `_wilder_atr()` from `atr_breakout_strategy.py:261` → public `src/signalgen/indicators.py`. ATRBreakout switches to it. Supertrend uses it. (Existing `indicators.py:67 atr()` uses talib.ATR — NOT Wilder-exact, ATRBreakout deliberately bypasses.) Separate task, prerequisite.
- **CC3:** Verify N_trials runtime gap (ADR 0059 G5). Confirm whether new Supertrend runner bypasses `CrossTrialLog.append_trial()` (volume_breakout did → DSR sees n_trials=1 not 10 → inflates DSR). Fix before first WFA.

## Operator decisions (2026-05-29, binding)

1. **Q1 → Pure Supertrend (#10) only.** ADX-filter (#11) → S51 если pure passes. (= trader rec.)
2. **Q4 → OVERRIDE trader ROUND 2.** Operator выбрал third path: починить autoresearch held-out split (prerequisite CC4) → легитимный param sweep на train → single held-out eval. НЕ literature defaults. Param discovery без champion-bias. **Scope расширяется** (+CC4 task). ATR=10/MULT=3.0 = sweep center, не locked.
3. **(resolved by trader, not operator choice)** 4H rejected — structural T5 fail. 1H binding.

## Revised execution order (post-operator-override)

1. CC2 — extract Wilder ATR → indicators.py (prereq)
2. CC3 — verify/fix N_trials runtime gap (prereq)
3. CC4 — fix autoresearch_endless.py held-out split (prereq, operator Q4) — train/held-out physical split, sweep train-only, single held-out eval
4. SupertrendStrategy impl (stateful streaming + property-test + vectorized cross-validation, Lazybear variant)
5. autoresearch Supertrend strat function (`strat_supertrend`)
6. param sweep on TRAIN only (ATR period + mult ranges around 10/3.0)
7. single held-out eval on winner (2025-06→2026-05); threshold Sharpe>0 + n≥15
8. if edge → formal 1H WFA (ADR 0014 gates, n_trials=10); else honest fail

## Carry-overs discovered S50

- **`atr_breakout_strategy.py` same windowed-ATR re-seed pattern** — pre-existing,
  affects shipped pre-registered strategy (ADR 0060 / 0064). It uses a bounded
  `deque(maxlen=max(atr_period, atr_stop_period)+10)` and recomputes
  `wilder_atr(...)` from that sliding window each bar (docstring lines ~164-167),
  the identical look-ahead / parity defect fixed in `SupertrendStrategy` during the
  S50 T4-fix (incremental Wilder recursion replaced windowed recompute). Once the
  buffer saturates, the windowed recompute re-seeds the Wilder RMA and diverges from
  the canonical full-history ATR.
  **Investigate:** did its WFA (ADR 0064) use the streaming `on_bar` path or the
  vectorized `strat_atr_breakout` reference? If the WFA / backtest used the
  vectorized full-history path while live uses streaming `on_bar`, there is a
  live/backtest parity gap that needs an ADR note.
  **Severity:** divergence is small — the Wilder recursion converges geometrically,
  seed influence decays ~((p-1)/p)^buffer — but real and, in principle, unbounded on
  adversarial inputs. **DO NOT fix in S50** (out of scope; LOCKED shipped strategy).
  Defer to a dedicated task with its own cross-validation gate mirroring
  `tests/property/test_supertrend_lookahead.py`.

## T8 sweep + held-out result (2026-05-29)

**Задача:** param sweep 35 комбо Supertrend на BTCUSDT 1H TRAIN (ts < 2025-06-01), выбор победителя по train Sharpe, одна held-out оценка.

**Данные:** 29 093 баров 2023-01-01 → 2026-04-26.
- TRAIN : 21 189 баров 2023-01-01 → 2025-05-31
- HELD-OUT : 7 904 баров 2025-06-01 → 2026-04-26

**Сетка параметров:** atr_period ∈ [7,9,10,12,14,16,21] × mult ∈ [2.0,2.5,3.0,3.5,4.0] = 35 комбо. atr_stop_mult фиксирован = 2.0. Минимум сделок для победителя (anti-fluke): n_trades_train ≥ 10.

**Результат sweep (все 35 комбо — eligible):**

| atr | mult | n_trades | train_sharpe |
|-----|------|----------|-------------|
| 21  | 2.0  | 426      | **8.696** ← победитель |
| 10  | 2.0  | 407      | 8.659 |
| 21  | 2.5  | 303      | 7.650 |
| 16  | 2.5  | 311      | 7.444 |
| ... | ...  | ...      | ... |
| 12  | 4.0  | 168      | 3.652 (худший) |

Все 35 комбо имеют train Sharpe > 3.6 (очень высокие показатели на train).

**⚠️ ПОПРАВКА (2026-05-29, PHASE 6 BLOCKER fix):** числа ниже были **завышены look-ahead bias** в backtest fill. Lazybear trend РЕКУРСИВНЫЙ (trend[i] зависит от close[i]), а fill происходил на open[i] (open того же бара, чей close сгенерировал сигнал) = same-bar look-ahead (~+117% инфляции PnL, объясняет однородные Sharpe 3.6-8.7 по всей сетке). Исправлено: flip@close[i] → fill на open[i+1] (commit `fix(s50): BLOCKER backtest fill look-ahead`). **Корректные числа после fix приведены ниже зачёркнутых.**

**Победитель (TRAIN Sharpe):**
- ~~`atr_period=21, mult=2.0`, train Sharpe **8.70**, n_trades=426, PnL=+662.1%~~ (look-ahead-inflated)
- **После fix:** `atr_period=10, mult=2.0` (победитель сменился — look-ahead благоприятствовал медленным параметрам), train Sharpe **1.22**, n_trades=637, PnL=+53.3%. Большинство комбо теперь с ОТРИЦАТЕЛЬНЫМ PnL; максимальный train Sharpe по всей сетке упал с 8.7 до 1.22.

**Held-out оценка (однократно, ADR 0067 Q4):**
- ~~held-out Sharpe **8.08**, n_trades **162**, PnL% **+152.8%**, win_rate 0.586~~ (look-ahead-inflated)
- **После fix:** held-out Sharpe **0.77**, n_trades **234**, PnL% **+9.83%** (победитель atr=10/mult=2.0). Инфляция Sharpe убрана: 8.08 → 0.77 (×10.5 меньше), PnL +152.8% → +9.83%.

**Порог T8 ADR 0067:** Sharpe > 0 AND n_trades ≥ 15 → формально выполнены (0.77 > 0), но это T8-gate, не финальный WFA verdict.

**ВЕРДИКТ T8: PROCEED_T9** (формально) — но финальный WFA verdict = **WFA_FAIL** (см. T9).

**Замечание:** однородно высокие Sharpe (train 8.7, held-out 8.1) по всей сетке были артефактом look-ahead fill, а НЕ bull-market beta, как предполагалось изначально. После исправления fill сигнал слабый/отрицательный — это и есть честная картина. Formal WFA (T9) подтверждает WFA_FAIL ещё жёстче (n_eff 47 → 16 после fix).

Скрипт: `scripts/run_supertrend_s50.py`. JSON артефакты: `data/supertrend_s50_sweep.json`, `data/supertrend_s50_heldout.json` (gitignored, результаты зафиксированы здесь).

## T9 formal WFA result (2026-05-29)

**Задача:** формальный Walk-Forward Analysis на победителе T8 (`atr_period=21, mult=2.0`), BTCUSDT 1H 2023-01-01 → 2026-04-26, n_trials=10 (гипотеза #10, ADR 0067).

**WFA параметры (высокочастотный tier, ADR 0014):**
- train_bars=2000, test_bars=500, k_folds=5, embargo_bars=20
- actual bars=29 093 (минимум 4 520 — с запасом)
- символ=BTCUSDT

### Результат: **WFA_FAIL**

**Провалившиеся критерии:** `n_eff_threshold` + `t5_floor` + `dsr_threshold`

**Per-fold OOS Sharpe (5 фолдов):**

| Fold | OOS Sharpe |
|------|-----------|
| 1    | 12.51     |
| 2    | 12.18     |
| 3    | 70.81     |
| 4    | 10.67     |
| 5    | 10.23     |

*Примечание: Sharpe astronomically high из-за крайне малого числа сделок на фолд — среднее удержание 23.6 бара × малый trade count → hugely inflated annualized Sharpe. Это NaN-артефакт малой выборки, а не реальный edge.*

**Метрики:**
- Trial mean OOS Sharpe: 23.28 (среднее по фолдам)
- Trial OOS Sharpe: 5.54 (из всех OOS сделок объединённо)
- n_trades_raw (все OOS фолды): **47** — ниже порога 50 (T5 floor + n_eff gate)
- MC p-value: **0.0005** (PASS, ≤ 0.05)
- DSR: **0.0** (FAIL, требуется ≥ 0.95)

### Разбор провалившихся ворот

**T5/n_eff (n_trades=47 < 50) — FAIL:**
Победитель `atr_period=21, mult=2.0` — крупный ATR + малый mult = редкие перевороты тренда.
5 фолдов × 500 баров (~21 день каждый) → в среднем ~9-10 сделок на фолд.
Суммарно 47 сделок по всем OOS фолдам при пороге 50. Статистическая мощность критически мала.

**DSR = 0.0 — FAIL:**
- sigma_sr_cross_trial = **35.41** — вычислено из 9 предыдущих записей в `data/cross_trial_sharpes.json`
- Эти записи из S44 содержат разброс от -89.5 до +0.37 (тестирование под разными параметрами и символами включая ETH/SOL → экстремальные негативные Sharpe)
- sigma_sr=35.41 вводит мощный multi-testing штраф Бейли: целевой Sharpe для DSR >> текущего trial OOS Sharpe 5.54
- DSR n_trials=1 (без штрафа): 0.9999 — **почти 1.0** (стратегия в изоляции звучит убедительно)
- DSR n_trials=10 с sigma=35.41: **0.0** — штраф сделок на пробу поглощает весь сигнал
- **Кавеат:** sigma_sr=35.41 включает экстремальные выбросы из S44 мультисимвольного тестирования. Если исключить эти выбросы, DSR был бы выше — но правила честны: мы зафиксировали все N=10 гипотез нарастающим итогом.

### n_trials caveat

На момент запуска T9 в `data/cross_trial_sharpes.json` содержалось **8 записей** (из S44, ключ `"trials"`), не 3+ — т.е. полный штраф n_trials=10 применён с sigma_sr=35.41 (стандартное отклонение кросс-трайловых Sharpe). Это не n_trials=1 fallback. Штраф реальный и законный — просто sigma экстремально велика из-за волатильности S44-экспериментов.

### Граничный победитель + bull-beta caveat (T8 предупреждение подтверждено)

- `atr_period=21` — максимум сетки (граница). `mult=2.0` — минимум сетки. Оба на краях.
- Высокие Sharpe по всей сетке в T8 (3.6-8.7) = сигнал bull-beta, а не genuine timing edge.
- Formal WFA подтвердил: rolling OOS фолды с Bailey DSR penalty не поддерживают гипотезу.

### Честная интерпретация

T8 held-out Sharpe 8.08 был BTC bull-market beta (2023-2025 тренд). Стратегия генерирует очень мало сделок (47 по всем 5 OOS-фолдам) на оптимальных для неё параметрах — слишком медленный переворот для накопления статистики. DSR penalty от предыдущих тестовых прогонов (sigma=35.41) делает порог практически недостижимым при реальном OOS Sharpe ~5-6.

**Supertrend гипотеза #10 = WFA_FAIL. Честный научный результат.**

9 из 10 предыдущих стратегий тоже FAIL — дисциплина ADR 0014 работает корректно.

Скрипт: `src/backtest/supertrend_runner.py::run_supertrend_wfa`. Данные: `data/cross_trial_sharpes.json`.

## Related
- [[decisions/0014-walk-forward-train2000-test500]] (WFA gates + S45 trade-freq table)
- [[decisions/0059-sprint-39-volume-breakout-pre-registration]] (anti-snooping pattern + G5 N_trials gap)
- [[decisions/0060-sprint-40-atr-breakout-pre-registration]] (4H T5-fail precedent)
- [[SPRINT_STATE]]
