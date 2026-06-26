---
title: "0071. Sprint 55 — _cmd_wfa DSR units fix (sigma_SR из real OOS Sharpe, class-scoped)"
type: decision
tags: [decision, adr, s55, dsr, wfa, quant, units, money-gate]
created: 2026-06-20
updated: 2026-06-26  # S55 QS-3 — donchian_runner:204 follow-up RESOLVED (dead-branch future-proofing)
status: accepted
sources:
  - llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - llm-wiki/wiki/project/decisions/0067-sprint-50-supertrend-pre-registration.md
  - src/__main__.py
  - src/analytics/dsr.py
  - src/backtest/research_wfa.py
  - src/backtest/wfa_reporter.py
  - src/backtest/walk_forward.py
  - src/backtest/donchian_runner.py
---

# 0071. Sprint 55 — _cmd_wfa DSR units fix (sigma_SR из real OOS Sharpe, class-scoped)

**Status:** accepted (ratify: quant-stats-reviewer PHASE 6)
**Date:** 2026-06-20

## Контекст

S55 HIGH QS-1 (`919a55f`) починил units-mismatch DSR в `src/analytics/dsr.py`: добавлен
параметр `annualization_factor`, который де-аннуализирует `sigma_sr` к per-trade шкале
(Bailey & López de Prado 2014 eq.12/13 требуют SR, SR* и sigma_SR на ОДНОЙ частоте).
Подключён в `research_wfa.py:319` и `wfa_reporter.py:82`, где fold-Sharpe'ы — настоящие
аннуализированные OOS Sharpe'ы.

Follow-up: применить тот же fix к `src/__main__.py::_cmd_wfa` (subcommand `python -m src wfa`).
**Наивный "parity"-патч здесь НЕВЕРЕН и ОПАСЕН** — расследование (2026-06-20) показало, что
премиса (fold-значения = аннуализированные Sharpe'ы) для этого пути НЕ держится:

1. `_cmd_wfa` — это subcommand `wfa` (S17 mean-reversion через `WalkForwardRunner` +
   `run_replay`), НЕ donchian. `all_fold_sharpes` накапливает `fold_data["oos_is_sharpe_ratio"]`
   = `oos_sharpe / is_sharpe` (`walk_forward.py:130`). Оба Sharpe'а получают ОДИН и тот же
   множитель `sqrt(bars_per_year)` (`replay_engine.py:62-66`) → он СОКРАЩАЕТСЯ → `all_fold_sharpes`
   = безразмерные OOS/IS отношения масштаба ~O(1), а НЕ Sharpe'ы.
2. `aggregate_oos_sharpe` = mean этих отношений → `sigma_sr_value = stdev(...)` = stdev отношений.
   `compute_dsr` внутренне считает per-trade un-annualized candidate Sharpe (`dsr.py:117`).
   Подача stdev-отношений как sigma_SR — это смешение units/семантики (отношение — вообще не Sharpe).
3. **Наивный патч инвертировал бы дефект в FALSE POSITIVE money-gate:** `annualization_factor =
   sqrt(bars_per_year)≈93.6` поделил бы и без того ratio-масштабную sigma_SR ещё на ~94 →
   sigma_SR ~94× мала → `sharpe_star≈benchmark` → DSR РАЗДУТ → gate пропускает overfit-стратегии.
   Неверное направление.
4. **Shared-log unit collision:** `__main__.py:843` пишет `aggregate_oos_sharpe` (отношение,
   `strategy_class="unknown"`) в `data/cross_trial_sharpes.json` — ТОТ ЖЕ файл, который
   research-путь (`research_wfa.py:270`) заполняет настоящими аннуализированными OOS Sharpe'ами
   (магнитуда ~ −44…−89). `_cmd_wfa` читает GLOBAL pool через `get_oos_sharpes()` (все классы) →
   sigma_SR смешивает alien-классы (S51 D5 это запретил для research/donchian, но `_cmd_wfa`
   остался на СТАРОМ pre-S51-D5 паттерне `stdev(pre_existing + [trial])`). Это та же причина,
   что ADR 0067 описал как `sigma_sr≈34 → sharpe_star≈54 = unbeatable bar`.

Аудит on-disk `data/cross_trial_sharpes.json` (2026-06-20): 9 записей, ВСЕ — настоящие
аннуализированные research-Sharpe'ы (atr_breakout/supertrend/volume_breakout). Записей-отношений
от `_cmd_wfa` пока НЕТ (subcommand `wfa` ещё не персистил в этой схеме) → collision **латентна**,
historical cleanup не требуется. Первый же `wfa`-run внёс бы ratio-запись и испортил бы sigma_SR
для ОБОИХ путей.

## Опции

- **A. Наивный parity (`annualization_factor=sqrt(bars_per_year)` поверх ratio-sigma).** ОТВЕРГНУТО —
  инвертирует дефект в false-positive money-gate (см. Контекст п.3).
- **B. Только units (ratio→real OOS Sharpe + annualization_factor), GLOBAL pool сохранён.** Частично —
  чинит ratio-collision, но оставляет cross-class контаминацию sigma_SR (S51 D5 нарушение).
- **C (ВЫБРАНО). Полное выравнивание:** real annualized OOS Sharpe + class-scoped sigma_SR +
  namespaced strategy_class + annualization_factor. Чинит units, collision И применяет S51 D5,
  пропущенный в этом пути. DRY (зеркалит уже отревьюенные паттерны). **Две разные blessed-провенансы:**
  class-scoping (`sigma_sr(strategy_class=)`) зеркалит `donchian_runner` + `research_wfa` (S51 D5);
  de-annualization (`annualization_factor`) зеркалит `wfa_reporter` + `research_wfa` (S55 QS-1).
  ВНИМАНИЕ (quant PHASE 6): `donchian_runner` НЕ передаёт `annualization_factor` — у него тот же
  латентный QS-1 mismatch, он blessed ТОЛЬКО как class-scoping-образец, НЕ как de-annualization.

## Решение

`_cmd_wfa` приводится к паттерну: class-scoping как в `donchian_runner.py` / `research_wfa.py`,
de-annualization как в `wfa_reporter.py` / `research_wfa.py`:

1. **Канонический sigma_SR-вход = настоящий аннуализированный OOS Sharpe per fold.** Использовать
   `runner_result["aggregate"]["fold_oos_sharpes"]` (`walk_forward.py:149` = `oos_metrics["Sharpe Ratio"]`,
   аннуализирован `sqrt(bars_per_year)`), НЕ `oos_is_sharpe_ratio`. Новый аккумулятор
   `all_fold_oos_sharpes` отдельно от `all_fold_sharpes` (отношения), который ПРАВИЛЬНО остаётся
   входом acceptance-gate + T6 (они ratio-based по дизайну ADR 0014/0015 — НЕ трогаем).
2. **De-annualize sigma_SR через `annualization_factor = sqrt(bars_per_year)`** (wfa_reporter
   parity — идентичная provenance bar-returns Sharpe'ов из `replay_engine`). Lo (2002) eq.13
   per-trade denom НЕ тронут (option B из S55 QS-1). Остаточный bar-vs-trade residual — second-order,
   как принял quant-stats S55.
3. **Class-scoped sigma_SR + namespaced strategy_class `"wfa_meanrev"`** (`_default_wfa_config` =
   `type: "mean_reversion"`, S17 RSI 35/65 + BB 1.5σ). `trial_log.sigma_sr(strategy_class="wfa_meanrev")`
   (ADR 0056 hierarchy: <3 within-class → NaN/None → fallback `n_trials=1`). N_trials = GLOBAL
   `trial_log.n_trials()` (Bailey eq.12 breadth, все классы — как раньше).
4. **Collision resolved:** `_cmd_wfa` пишет настоящий аннуализированный OOS Sharpe (тот же unit,
   что research) под `strategy_class="wfa_meanrev"` → больше не отравляет research class-scoped
   sigma_SR и наоборот. Persist ДО чтения sigma (candidate включён в variance pool, Bailey eq.13 —
   ordering как research_wfa).
5. `compute_dsr` (`src/analytics/dsr.py`) — БЕЗ изменений (только call-site).

## Последствия

- **Money-gate корректность:** sigma_SR теперь на согласованной частоте, без ratio-семантики и без
  cross-class контаминации. Устранён риск false-positive (опция A) и false-negative (cross-class
  inflation как ADR 0067).
- **Поведенческое изменение:** свежий класс `"wfa_meanrev"` стартует с 0 within-class записей →
  sigma_SR NaN → DSR на `n_trials=1` (нет multiple-testing penalty), пока класс не накопит ≥3
  честных trial'а (ADR 0056). Это КОРРЕКТНОЕ поведение — прежний GLOBAL-pool penalty был
  статистически невалиден (mean-reversion наказывался variance'ом atr_breakout).
- **TDD:** RED-тест доказывает units-inconsistency (persisted aggregate = real OOS Sharpe mean,
  НЕ ratio mean; `strategy_class="wfa_meanrev"`, НЕ "unknown"; `annualization_factor=sqrt(bars_per_year)`
  передан). GREEN после выравнивания.
- **Out-of-scope (сохранено):** S51 D5 scope orthogonal; `compute_dsr` internals; acceptance-gate +
  T6 ratio-входы. mean_holding в этом пути не измеряется (research-trades без bar-индексов) — как и
  research_wfa, используется nominal sqrt(bars_per_year)-фактор.
- **Follow-up (quant PHASE 6 находка) — РЕШЕНО S55 QS-3:** `donchian_runner.py:204` вызывал
  `compute_dsr_with_status` БЕЗ `annualization_factor`. Fix: добавлен `annualization_factor=
  math.sqrt(bars_per_year)` (wfa_reporter parity — для будущего donchian-writer provenance =
  real annualized OOS Sharpe). quant-stats-reviewer APPROVE (PHASE 6). TDD: `test_donchian_dsr_units.py`.
  **Уточнение (quant re-adjudication):** это НЕ просто латентный mismatch, а **DEAD branch** —
  ни один call-site в `src/` не пишет `strategy_class="donchian"` в `cross_trial_sharpes.json`
  (writers: `_cmd_wfa`→`"wfa_meanrev"`, `research_wfa`→`"atr_breakout"/"supertrend"/...`),
  поэтому `sigma_sr("donchian")` сейчас всегда None → CLASS_SCOPED-ветка недостижима. Fix корректен
  как future-proofing. donchian's локальный `trial_mean_fold_oos_sharpe` = OOS/IS RATIO
  (`oos_is_sharpe_ratio`, walk_forward:130), используется ТОЛЬКО как `math.isnan` reachability-guard —
  НЕ pool-вход. **Будущий donchian-writer ОБЯЗАН** персистить `fold_data["oos_metrics"]["Sharpe Ratio"]`
  (настоящий аннуализированный OOS Sharpe), НЕ локальный ratio `fold_sharpes` (иначе ratio-collision
  как у `_cmd_wfa` до этого ADR). Commit S55 QS-3.
- **Authority:** quant-stats-reviewer ратифицирует направление (PHASE 6, money/strategy gate).

## Связанные документы

- [[0056-sprint-36-dsr-sigma-sr-amendment]] — sigma_SR sourcing hierarchy (N≥3/1-2/0) + S51 D5 class-scoping
- [[0067-sprint-50-supertrend-pre-registration]] — описал cross-class sigma_SR contamination (sigma_sr≈34)
