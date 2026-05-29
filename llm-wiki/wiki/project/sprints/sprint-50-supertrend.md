---
title: "Sprint 50 — Supertrend (freqtrade adaptation, WFA_FAIL)"
type: sprint
tags: [sprint-50, supertrend, wfa-fail, hypothesis-10, freqtrade, trend-following, lazy-bear, anti-snooping, reason-codes-65, honest-fail]
created: 2026-05-29
updated: 2026-05-29
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0067-sprint-50-supertrend-pre-registration.md
  - llm-wiki/wiki/project/pre-s50-backlog.md
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
---

# Sprint 50 — Supertrend (freqtrade adaptation, WFA_FAIL)

## Обзор

S50 = адаптация стратегии Supertrend из репозитория freqtrade к нашему streaming-боту. Hypothesis #10 (Bailey 2014 N_trials counter). Итог: **WFA_FAIL** — честное завершение.

**Baseline (post-S49):** pytest 1350 / mypy 0 / reason_codes 63.
**Post-S50:** pytest 1412 / mypy 0 / reason_codes **65** (+2 ENTRY_LONG_SUPERTREND + EXIT_FLAT_SUPERTREND_FLIP).

**Вердикт WFA_FAIL:** n_eff=47 < порог 50 (T5 FAIL) + DSR=0.0 (Bailey penalty при n_trials=10, sigma=35.41). Held-out Sharpe=8.08 = bull-beta, не торговое преимущество. Boundary-winner (atr=21/mult=2.0) = красный флаг snooping.

**Стратегия НЕ запущена в production.** Зарегистрирована в dashboard для сравнения (WFA_FAIL пресет с честной разметкой).

## Контекст: scout freqtrade

Operator request: адаптировать стратегию из github.com/freqtrade/freqtrade-strategies.

Step-0 code verification результаты:
- `BbandRsi` (freqtrade) = дубликат нашей `MeanReversionRsiBBStrategy` (S15/S17) → исключён.
- `Supertrend` (@juankysoriano) = ATR-based trend-follower, **новая логика** (grep подтвердил отсутствие в нашем коде). Оригинал = triple-Supertrend с hyperopt → упрощаем к single-Supertrend (anti-snooping, ADR 0067).

## Brainstorm trail (trader-expert ROUND 1+2)

| Вопрос | Вердикт | Binding |
|--------|---------|---------|
| Q1 pure vs ADX-filter | Pure Supertrend #10. ADX-filter = hypothesis #11 DEFER S51. | CONFIRM |
| Q2 exit mechanism | Signal-exit + ATR bracket SL. Без TP (trend-runner). | CONFIRM |
| Q3 1H vs 4H | **REVISE → CONFIRM_REVISE (1H).** 4H = 28 trades/3.3y → T5 floor n≥50 структурно недостижим (прецедент ATRBreakout S44/S45, ADR 0060). 1H = viable. | ROUND 2 binding |
| Q4 params источник | **REVISE → CONFIRM_REVISE (operator OVERRIDE).** autoresearch_endless.py не имел held-out split (grep-verified). Operator: сначала исправить CC4 split, затем легитимный sweep на train-only. | ROUND 2 + operator override |
| Q5 variant | Lazybear stateful streaming + vectorized cross-validation. Locked (иначе cross-val false-positive). | CONFIRM |

**Operator decisions (2026-05-29, binding):**
- Q3: 1H (не 4H) — T5 reachability.
- Q4: fix autoresearch held-out split FIRST, THEN sweep → single held-out eval на winner. Seban defaults (ATR=10/MULT=3.0) становятся центром sweep, не locked values.

## Задачи (T1-T11)

| Задача | Commit | Суть | Итог |
|--------|--------|------|------|
| **T1** CC2 Wilder ATR extract | `db66ca7` | `wilder_atr()` в `src/signalgen/indicators.py`. `atr_breakout_strategy._wilder_atr` delegates. `volume_breakout` untouched (LOCKED ADR 0059). 3 parity tests. | DONE |
| **T2** CC3 N_trials wiring | `6d8f7ad` | Верификация: `run_research_wfa(n_trials=10)` pattern правильный (эталон — atr_breakout). Gap = penalty только при ≥3 cross-trial sharpes. T7 обязан использовать `run_research_wfa`, НЕ inline DSR. | DONE |
| **T3** CC4 held-out split | `2fc2cb7` | `split_train_heldout()` + `eval_heldout_once()` + HELDOUT_START/END в `scripts/autoresearch_endless.py`. Sweep теперь train-only (ts < 2025-06-01). Anti-champion-bias. 5 new tests. | DONE |
| **T4** SupertrendStrategy | `0d10eac` + guards | `src/signalgen/supertrend_strategy.py`. Lazybear streaming: stateful `_supertrend_line` + `_trend_direction`. LOCKED params (atr_period=10, mult=3.0). Reason codes 63→65. Look-ahead-safe (is_closed + OOO/dedup + wilder_atr). 18 new tests. | DONE |
| **T5** Look-ahead property + cross-validation | `287dd47` | `tests/property/test_supertrend_lookahead.py`. Поймала look-ahead баг: streaming пересчитывал ATR из bounded deque (re-seed при насыщении → diff ~0.18). **Fix:** incremental Wilder ATR recursion `_update_atr` O(1) → bit-exact (0.0 diff). | DONE — баг найден + исправлен |
| **T6** strat_supertrend | — | `src/research/strat_supertrend.py` (или аналог). Интеграция с research flow. | DONE |
| **T7** supertrend_runner | `eaa65a9` | `src/backtest/supertrend_runner.py`. Pattern: `run_research_wfa(n_trials=10)` (аналог atr_breakout, НЕ inline DSR). BTCUSDT 1H / high-freq tier / sprint_tag="S50". 8+3 unit tests. | DONE |
| **T8** sweep + held-out eval | — | Autoresearch sweep на train (< 2025-06-01). Winner: atr=21/mult=2.0. Held-out eval: Sharpe=8.08, n_trades≥15 → PROCEED к formal WFA. | DONE — PROCEED (held-out threshold met) |
| **T9** formal WFA | — | `run_research_wfa(n_trials=10)`. Результат: **WFA_FAIL**. n_eff=47<50 (T5 FAIL), DSR=0.0 (Bailey penalty, sigma=35.41), MC p=0.0005 (PASS). n_trades_raw=47. | DONE — WFA_FAIL |
| **T10** dashboard preset | `056312d` | `supertrend` зарегистрирован в `STRATEGY_PRESETS`. BTCUSDT 1H locked, optgroup="Тренд", честная разметка WFA_FAIL. 7 new tests. pytest 1412/25 skip. | DONE |
| **T11** wiki sync | — | sprint-50 page + index + log + current-state + ADR 0067 accepted. | DONE |

## WFA_FAIL: детальный разбор

### Формальные ворота (ADR 0014, S49-resolved gate-blocking)

| Критерий | Результат | Gate-blocking? |
|----------|-----------|---------------|
| T5 n_trades_raw ≥ 50 | **47 < 50 — FAIL** | ДА |
| DSR ≥ 0.95 | **0.0 — FAIL** | ДА |
| MC p-value ≤ 0.05 | 0.0005 — PASS | ДА |
| n_eff ≥ 50 | **47 < 50 — FAIL** | ДА |
| Per-fold sharpe_gate | — | ДА |

**2 gate-blocking fails** (T5 + DSR/n_eff). WFA_FAIL вердикт детерминирован.

### Почему DSR = 0.0?

Bailey DSR penalty (2014): при n_trials=10 (hypothesis #10) и sigma_sr=35.41 (cross-trial Sharpe std), Expected Maximum Sharpe Ratio (EMSR) настолько высокий, что реальный OOS Sharpe не преодолевает порог. DSR=0.0 = полная дисквалификация — результат целиком объясняется овербором параметров.

### Held-out = bull-beta, не торговое преимущество

Winner: atr=21/mult=2.0 (boundary параметры sweep grid). Held-out период 2025-06-01 → 2026-05-01 = выраженный бычий рынок BTC. Supertrend trend-follower показывает Sharpe=8.08 на бычьем рынке = trivial bull-beta (любая long-only стратегия даёт высокий Sharpe в таком режиме). Это не торговое преимущество.

### Boundary-winner = snooping red flag

`atr=21/mult=2.0` — оба на границе sweep grid. Boundary winner = алгоритм хочет выйти за диапазон. Если бы sweep был шире, winner сдвинулся бы. Это классический red flag snooping (Bailey 2014 предупреждает об этом паттерне).

## Ключевые выводы (institutional knowledge)

1. **Held-out высокий Sharpe ≠ edge, если bull-market.** Held-out PASS (Sharpe=8.08) может создать ложное впечатление. Formal WFA обязателен и корректно отклоняет через DSR.

2. **Boundary-winner sweep = snooping сигнал.** Sweep grid должен быть достаточно широким. Если winner на границе — это методологический red flag, а не успех.

3. **Bailey DSR penalty при n_trials=10 (sigma=35.41) корректно убивает инфлированный DSR.** N_trials counter работает как задумано — чем больше испытаний, тем сложнее выжить.

4. **T5 incremental-ATR look-ahead баг пойман cross-validation = победа методологии.** Streaming пересчитывал ATR из bounded `deque` (re-seed Wilder RMA при насыщении → расхождение с full-history ATR ~0.18). Cross-validation выявила это и заставила исправить инкрементальную рекурсию `_update_atr`. Это методологическая победа: look-ahead guard работает.

5. **Hypothesis #10 честно закрыта.** 10-й WFA_FAIL подряд. Consistent с прецедентами S13-S23 + S33-S45. Честная документация дороже кажущегося успеха.

## Переиспользуемая инфраструктура

Хотя стратегия провалила WFA, инфраструктура осталась в кодовой базе как многоразовая:

- **`wilder_atr()` в `indicators.py`** — общая реализация Wilder RMA ATR (shared между supertrend + atr_breakout). Устраняет дублирование 3 разных реализаций.
- **held-out split** в `autoresearch_endless.py` — anti-champion-bias корректный sweep (исправлен в T3, важный precedent).
- **`supertrend_runner.py`** — runner pattern для trend-follower стратегий (reusable template).
- **`SupertrendStrategy`** — streaming Lazybear с правильной инкрементальной ATR — reusable component.
- **`tests/property/test_supertrend_lookahead.py`** — cross-validation methodology (portable к другим стратегиям).

## Gates (post-S50)

| Инструмент | Результат | Дельта |
|-----------|----------|--------|
| pytest unit | **1412 passed, 25 skipped** | +62 vs 1350 baseline |
| mypy --strict | **0 errors** | unchanged |
| ruff lint | **clean** | — |
| Reason codes | **65** | +2 vs 63 baseline |

**Стратегия НЕ production-ready.** Dashboard preset зарегистрирован с WFA_FAIL маркировкой.

## Перенос S51

- **atr_breakout windowed-ATR баг (pre-existing, LOCKED):** `atr_breakout_strategy.py` имеет идентичный bounded-deque паттерн (look-ahead уязвимость). Был известен до S50. Стратегия LOCKED (shipped S40/S44/S45/ADR 0060) → defer S51. Добавлен в `pre-s50-backlog.md` carry-forward.
- **ADX-filter Supertrend — hypothesis #11:** деферирован per operator Q1. Следующий кандидат S51 (если operator выберет).

## Связанные

- [[../decisions/0067-sprint-50-supertrend-pre-registration]] — ADR 0067 LOCKED spec + brainstorm trail + исход WFA_FAIL (обновлён S50)
- [[../decisions/0014-walk-forward-train2000-test500]] — WFA gates (T5/DSR/MC/n_eff gate-blocking, S49-resolved)
- [[../decisions/0059-sprint-39-volume-breakout-pre-registration]] — anti-snooping pattern (N_trials counter)
- [[../decisions/0060-sprint-40-atr-breakout-pre-registration]] — 4H T5-fail прецедент (почему Q3 выбрал 1H)
- [[sprint-49-tech-review-audit]] — предыдущий спринт (S49)
- [[../pre-s50-backlog]] — полный brainstorm trail + CC2/CC3/CC4 prerequisites
