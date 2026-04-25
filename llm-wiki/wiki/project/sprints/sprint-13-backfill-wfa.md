---
title: Sprint 13 — Backfill 5y + WFA T1-T6 measurement
type: sprint
tags: [sprint-13, backfill, wfa, t1-t6-measurement, strategy-validation, mvp-gating]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0028-sprint-13-strategy-validation.md
  - project/plans/2026-04-25-sprint-13-backfill-wfa.md
  - project/pre-s13-backlog.md
---

# Sprint 13 — Backfill 5y + WFA T1-T6 measurement

## Overview

First empirical strategy validation. Backfilled 4.81y BTCUSDT 1H Bybit Spot data (42098 bars, 2021-07-03 → 2026-04-25 — Bybit data starts 2021-07-02, ESC-2 fallback per ADR 0028 floor 3.5y MET, 5y target NOT MET). Ran WFA T1-T6 measurement + DSR + MC.

**Verdict: FAIL** (4/6 criteria failed). Per Q7 ESC-1=c defer pattern: operator decides next sprint scope at S15 (case-by-case).

**Critical finding:** Sample size NOT data-span-bounded. Strategy fires ~1 trade per 10 days regardless of 2.2y vs 4.8y data span — same 20 OOS trades. T5 n_trades floor (>=100) unreachable without strategy revision.

## Plan / ADR links

- ADR: [[../decisions/0028-sprint-13-strategy-validation]]
- Plan: [[../plans/2026-04-25-sprint-13-backfill-wfa]]
- Backlog: [[../pre-s13-backlog]]

## Deliverables

8 TDD tasks, 12 commits squash-merged:

- T1 (d8e6930): Bybit data availability probe — earliest 1H BTCUSDT = 2021-07-02
- T2 (59ef6fc + 4a1b56b): _cmd_backfill wire к BybitRESTClient.get_klines + Parquet write (snappy + atomic)
- (21604af): get_klines pagination bug fix — walk backward для Bybit V5 end-anchored API
- T3 (33ad6c5): Backfill execution — 42098 bars, 4.81y span
- T4 (e4439e1): _load_ohlcv NaN pre-flight assertion (CC4)
- T5 (a2f1e07): trade_extractor (DataFrame → TradeRecord, closes S10/S12 carry-over)
- T6 (5908682 + 1f7124a): strategy_metrics T1-T6 extraction + BLOCKER fix (T3 MaxDD initial_capital)
- T7 (eb83650): Wire S13 measurement в _cmd_wfa + verdict report
- T8 (this commit): PHASE 8 wiki sync

## FSM growth

NONE. S13 = backtest analytics + data infra. Counts unchanged (16/30/74/45).

## Reason codes growth

NONE.

## Tests / quality

- pytest unit: 712 passed (689 baseline + 23 new across T2/T4/T5/T6 + 1 pagination fix test)
- pytest integration: existing OK
- mypy --strict src/: clean (~70 source files)
- ruff: clean on touched files
- Q7-S12 zero-migration preserved: `git diff main..HEAD -- migrations/` empty

## Backfill artifact

- File: `data/BTCUSDT_1h.parquet` (snappy, atomic write via tmp+rename)
- Period: 2021-07-03 → 2026-04-25
- Rows: 42098
- Span: 1756 days = 4.81 years
- ADR 0028 ESC-2 status: floor 3.5y MET, target 5y NOT MET (Bybit data starts 2021-07-02)
- Backup preserved: `data/BTCUSDT_1h.parquet.s2-backup` (S2-era 2.2y baseline)

## Verdict result (T7 measurement)

**FAIL** — 4/6 T1-T6 criteria failed.

| Criterion | Threshold | Measured | Status |
|-----------|-----------|----------|--------|
| T1 Sharpe OOS | >= 1.0 | -44.46 | FAIL |
| T2 Sortino OOS | >= 1.5 | -101.38 | FAIL |
| T3 MaxDD | < 25% | 1.27% | PASS |
| T4 Win rate (RR=0.797) | >=45% при RR>=1.5 | 30% | FAIL (RR < 1.5) |
| T5 Mean PnL + t-stat + n | n >= 100 OOS | n=20 | FAIL (sample too small) |
| T6 OOS/IS Sharpe ratio | >= 0.7 | 1.136 | PASS |
| DSR (informational S13) | > 0 | 0.0445 (N_trials=1) | PASS marginal |
| MC p-value (gate) | <= 0.05 | 0.048 | PASS borderline |

**Failed criteria:** [t1, t2, t4, t5]
**N_trials:** 1 (per CC1 — first measurement, no parameter search)

## Wiki updates

- 2 NEW component pages: trade-extractor + strategy-metrics
- 1 NEW ADR (0028 — status: accepted)
- 1 NEW sprint page (this)
- 1 NEW plan: 2026-04-25-sprint-13-backfill-wfa.md
- 1 NEW backlog: pre-s13-backlog.md
- Modified: src/__main__.py (_cmd_backfill wire + _load_ohlcv NaN preflight + _cmd_wfa T1-T6 wiring), src/marketdata/bybit/rest.py (pagination fix), acceptance-criteria.md (footnotes 1+2+3 reconciliation)
- current-state.md (TL;DR post-S13, ADR 27->28, sprint pages 14->15, components 36->38)
- index.md (sprint-13 + ADR 0028 + 2 component pages)
- mental-map.md (+2 component rows)

## Open issues для S14+

**Per Q7 ESC-1=c defer: operator decides at S15 case-by-case.** Possible paths:

(a) **Strategy revision** (option per ESC-1 if user authorizes pivot) — different strategy family (mean-reversion / regime-switch / ML-driven). Each revision = new N_trials count (multi-testing penalty grows).

(b) **Honest "no edge" close** — accept HARD FAIL pattern across 2 measurements (2.2y prior + 4.8y current). Document EMA crossover на 1H BTC = no measurable edge. Ship v0.1 as infrastructure-validation milestone.

(c) **Multi-symbol backfill** — try ETHUSDT, SOLUSDT etc. для doubled signal frequency, но venue scope expansion (not v0.1 baseline).

(d) **Tighten signal frequency** — relax indicator thresholds (lower ADX, wider RSI bounds) to fire more signals, но look-ahead через researcher risk.

S13 carry-overs (independent of pivot decision):
- S12 carry-overs unaddressed (FillRecorderAdapter Layer 2, 3-way endpoint enum, init_db dual-conn comment, etc.)
- DSR threshold calibration deferred S15+ per S11 Q5 (need >=30 trades — currently 20)
- T2 quant-stats concerns: notional dead code (cosmetic), fees_paid NaN edge case
- T6 quant-stats concerns: Sortino formula non-canonical (defer wiki documentation), sqrt(8760) per-trade frequency-agnostic
- 48h Bybit demo validation operator-driven (not run since S12)

## Key decisions

- **Q1 CONFIRM** (backtest re-attempt first, NOT 48h validation first)
- **Q2 EXPAND** -> folded backfill+measurement single sprint (Bybit pagination + WFA + verdict)
- **Q3 CONFIRM** (Bybit Spot only, no Binance fallback per ADR 0016)
- **Q4 REVISE-FACTUAL** (tiered 5y target, floor 3.5y — spec inconsistency caught)
- **Q5 CONFIRM** (DSR active S13 N_trials=1, PBO defer S15+)
- **Q6 CONFIRM** (48h validation decoupled, operator parallel track)
- **Q7 REVISE -> user REJECTED** — defer pattern preserved (case-by-case at S15)
- **Q8 CONFIRM** (skip dashboard wire, CLI JSON only)
- **ESC-1=c** (defer HARD FAIL decision к S15)
- **ESC-2** (tiered 5y, max-available Bybit, floor 3.5y — actual 4.81y MET)
- **Spec reconciliation (CC4):** acceptance-criteria.md amended с footnotes 1+2+3 (5y aspirational, DSR active, PBO deferred)

## Related

- [[../decisions/0028-sprint-13-strategy-validation]] — Sprint 13 ADR
- [[../plans/2026-04-25-sprint-13-backfill-wfa]] — Sprint 13 implementation plan
- [[../pre-s13-backlog]] — PHASE 2 verdicts trail
- [[../decisions/0027-sprint-12-live-demo-validation]] — predecessor sprint
- [[../decisions/0014-walk-forward-train2000-test500]] — WFA params
- [[../decisions/0016-bybit-spot-supersedes-binance]] — venue policy
- [[../components/trade-extractor]] — NEW (T5)
- [[../components/strategy-metrics]] — NEW (T6)
- [[../architecture/acceptance-criteria]] — 12 gating criteria (amended footnotes)
