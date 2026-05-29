---
title: Pre-S50 Backlog — Supertrend strategy adaptation (freqtrade)
type: backlog
tags: [pre-sprint, backlog, s50, supertrend, strategy]
created: 2026-05-29
updated: 2026-05-29
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

## Related
- [[decisions/0014-walk-forward-train2000-test500]] (WFA gates + S45 trade-freq table)
- [[decisions/0059-sprint-39-volume-breakout-pre-registration]] (anti-snooping pattern + G5 N_trials gap)
- [[decisions/0060-sprint-40-atr-breakout-pre-registration]] (4H T5-fail precedent)
- [[SPRINT_STATE]]
