---
title: "0067. Sprint 50 — Supertrend pre-registration (freqtrade adaptation)"
type: decision
tags: [decision, adr, s50, supertrend, anti-snooping, strategy]
created: 2026-05-29
updated: 2026-05-29
status: proposed
sources:
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
  - llm-wiki/wiki/project/decisions/0059-sprint-39-volume-breakout-pre-registration.md
  - llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-pre-registration.md
  - llm-wiki/wiki/project/pre-s50-backlog.md
---

# 0067. Sprint 50 — Supertrend pre-registration (freqtrade adaptation)

**Status:** proposed
**Date:** 2026-05-29

## Контекст

Operator request: адаптировать стратегию из github.com/freqtrade/freqtrade-strategies к нашему Bybit Spot streaming-боту. Scout репозитория + Step-0 code verification:

- freqtrade `BbandRsi` (RSI<30 + close<lower_BB) = line-for-line дубликат существующей `MeanReversionRsiBBStrategy` (S15/S17) → исключён.
- freqtrade `Supertrend` (@juankysoriano) = ATR-based trend-follower, **genuine NEW logic** (grep подтвердил: нет supertrend/macd/cci/sma/heikin-ashi в нашем коде). Оригинал = triple-Supertrend (3 buy + 3 sell с hyperopt) → упрощаем к single-Supertrend (anti-snooping).

Наш bot: streaming `on_bar(bar) -> Signal | None` (look-ahead prevention via append-before-compute + is_closed + generated_at≥bar_close, property-tested). Execution = bracket/OCO (entry + SL + optional TP). Acceptance = ADR 0014 WFA gates (gate-blocking S49-resolved: T5/DSR/MC/per-fold sharpe_gate/n_eff; T1/T2/T3/T4/T6 informational). Anti-snooping = ADR 0059 LOCKED pre-registration.

## Решение

Pre-register **SupertrendStrategy** как hypothesis #10 (Bailey 2014 N_trials increment — irreversible).

### LOCKED spec

| Параметр | Значение | Источник |
|---|---|---|
| Strategy | SupertrendStrategy (single, long-only Spot) | Q1 CONFIRM |
| Symbol | BTCUSDT | ADR 0059 anti-snooping |
| Timeframe | **1H** | Q3 ROUND 2 binding |
| ATR_PERIOD | 10 | Olivier Seban 2009 default |
| MULTIPLIER | 3.0 | Olivier Seban 2009 default |
| Variant | Lazybear trend-dependent (freqtrade-compatible) | Q5 hidden-risk lock |
| Entry | trend flips bullish (close crosses above supertrend line) | — |
| Exit prio 1 | trend flips bearish → EXIT_FLAT signal на close(T) | Q2 CONFIRM |
| Exit prio 2 | ATR-multiple bracket SL (safety net) | Q2 CONFIRM |
| TP | none (trend-runner) | Q2 CONFIRM |
| Held-out | 2025-06-01 → 2026-05-01, single eval | Q4 ROUND 2 binding |
| Held-out threshold | Sharpe>0 AND n_trades≥15 → proceed formal WFA | Q4 binding |

### Brainstorm verdict trail (trader-expert)

- **Q1 CONFIRM** — Supertrend pure. ADX-filter variant = hypothesis #11 DEFER S51+.
- **Q2 CONFIRM** — signal-exit + ATR bracket SL, no minimal_roi/TP/native-trailing.
- **Q3 REVISE→CONFIRM_REVISE (1H)** — 4H = 28 trades/3.3y → T5 floor n≥50 structurally unreachable → guaranteed WFA_FAIL (ATRBreakout 4H precedent S44/S45 ADR 0060). 1H = T5-viable. Maintainer 4H rec was wrong.
- **Q4 REVISE→CONFIRM_REVISE (literature defaults)** — autoresearch_endless.py has ZERO held-out split (grep-verified) → maintainer "validate on held-out" premise false. Champion-bias (Bailey 2014, ADR 0059 warned). LOCK Seban defaults.
- **Q5 CONFIRM** — stateful streaming (`_supertrend_line` + `_trend_direction`) + vectorized cross-validation. Lazybear variant locked (else cross-val false-positive).

## Последствия

### Прерогативы (prerequisite tasks, BEFORE Supertrend impl)
- **CC2:** вынести Wilder ATR → `indicators.py` public fn. Сейчас дублирован 2× (`atr_breakout_strategy.py:262 _wilder_atr` + `volume_breakout_strategy.py:204 _compute_wilder_atr`). `indicators.py:67 atr()` = talib (НЕ Wilder-exact). Все 3 consumer переходят на одну функцию.
- **CC3:** verify N_trials runtime gap (ADR 0059 G5). research_wfa.py:262 делает `append_trial`, но runner wiring (donchian/atr pattern) надо проверить что Supertrend runner передаёт `n_trials=10` + CrossTrialLog корректно. Иначе DSR inflated.

### Risks
- Whipsaw на 1H → low per-fold Sharpe → возможный WFA_FAIL (но measurable, informative — в отличие от 4H T5-fail).
- Literature defaults могут не подойти BTC → honest WFA_FAIL acceptable (9 prior FAIL прецедентов). NO param shopping после.
- N_trials #10 = permanent Bailey DSR penalty growth.

### Открытые (operator escalation)
1. Pure Supertrend (#10, S50) vs +ADX filter (#11, S51+) — recommend pure first.
2. N_trials=10 irreversible acceptance.

## Related
- [[0014-walk-forward-train2000-test500]] — WFA gates + S45 trade-freq table
- [[0059-sprint-39-volume-breakout-pre-registration]] — anti-snooping pattern + G5 gap
- [[0060-sprint-40-atr-breakout-pre-registration]] — 4H T5-fail precedent
- [[../pre-s50-backlog]] — full brainstorm trail
