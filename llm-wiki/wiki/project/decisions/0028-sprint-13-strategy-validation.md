---
title: 0028. Sprint 13 — Strategy validation (5y backfill + WFA T1-T6 measurement)
type: decision
date: 2026-04-25
sprint: 13
tags: [adr, sprint-13, strategy-validation, t1-t6-gating, backfill, wfa-measurement, dsr-active, multi-sprint-roadmap, mvp-completion]
sources:
  - project/pre-s13-backlog.md
  - project/decisions/0014-walk-forward-train2000-test500.md
  - project/decisions/0015-sign-flip-mc-permutations-n2000.md
  - project/decisions/0016-bybit-spot-supersedes-binance.md
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
  - project/decisions/0027-sprint-12-live-demo-validation.md
  - project/architecture/acceptance-criteria.md
  - project/architecture/migration-plan.md
status: proposed
---

# 0028. Sprint 13 — Strategy validation (5y backfill + WFA T1-T6 measurement)

**Status:** proposed
**Date:** 2026-04-25

## Context

Sprint 13 = first empirical strategy validation на 5y BTCUSDT 1H Bybit Spot data. Pre-S13 attempt aborted (feature branch deleted, see SPRINT_STATE history). User pivoted к "old flow" per migration-plan.md gating sequence.

**Critical context inherited (knowledge preserved, code wiped):** prior S13 attempt measured T1-T6 на existing 2.2y Parquet. Result: HARD_FAIL (T1 Sharpe -44.46, n_trades=20 OOS). Sample size critically low. Hypothesis: bigger sample (5y backfill) gives statistically reliable verdict.

S12 shipped (PR #20, tag `v0.1.0-alpha.12`). 33min Bybit demo validation surfaced `_cmd_monitor` SQL bug → hot-fix `562d385` shipped on main.

PHASE 2 brainstorming verdicts (`pre-s13-backlog.md`):
- Q1 CONFIRM: backtest re-attempt first (NOT 48h validation first)
- Q2 EXPAND: conditional split based на Bybit data availability check
- Q3 CONFIRM: Bybit only, document gap
- Q4 REVISE-FACTUAL: tiered 5y target, floor 3.5y (spec inconsistency caught: acceptance-criteria.md "5 лет" vs migration-plan.md "2y")
- Q5 CONFIRM: DSR active S13, PBO defer S15+
- Q6 CONFIRM: 48h validation decoupled (parallel operator track)
- Q7 REVISE → user REJECTED, defer pattern preserved (case-by-case decision at S15)
- Q8 CONFIRM: skip dashboard (per "without S13-introduced" user direction)

User binding decisions (ESCs):
- **ESC-1 (Q7):** Defer pattern preserved (REJECT trader pre-commit framework). Per user verbatim: "subagent трейдер сориентирует если что". Risk acknowledged: unbounded N_trials degrades DSR over iterations.
- **ESC-2 (Q4):** Tiered 5y accepted. Target 5y, fallback к max-available-floor-3.5y. PHASE 3 step 1 = REST API probe earliest Bybit Spot 1H BTCUSDT timestamp.

## Decision

### S13 scope (single-deliverable per kit "1 sprint = 1 ADR")

**S13 = Backfill 5y data + WFA T1-T6 measurement on max-available Bybit Spot data.**

T1 (PHASE 3 step 1): **Bybit data availability probe** (REST `/v5/market/kline category=spot symbol=BTCUSDT interval=60 limit=1 start=<earliest target>`). Determines actual span. Если < 3.5y → escalate user (ESC-2 fallback).

T2: Wire `_cmd_backfill` (currently STUB delegate per __main__.py:170) к BybitRESTClient paginated kline + data_collector Parquet write.

T3: Run backfill для max-available period. Output: `data/BTCUSDT_1h.parquet` extended.

T4: NaN pre-flight assertion в `_load_ohlcv` (CC4 from prior S13 attempt — December warmup risk).

T5: Per-fold trade extraction (DataFrame → TradeRecord) для DSR. Closes S10 + S12 carry-over (`trades_for_dsr=[]` placeholder removed).

T6: T1-T6 metrics computation (extend wfa_reporter с per-criterion extraction).

T7: Verdict report (CLI JSON + sprint page documentation): PASS / PARTIAL FAIL / HARD FAIL per T1-T6 + DSR > 0 (Q5 CONFIRMED active S13).

T8: Sprint page + counts sync + ADR accept (PHASE 8).

### Multi-sprint roadmap (anticipated, не binding upfront)

| Sprint | Scope | Type | Calendar |
|--------|-------|------|----------|
| **S13** | Backfill 5y + WFA T1-T6 measurement (this sprint) | sprint (TDD + ADR) | 1 sprint |
| **S14** | DSR threshold calibration + per-fold convert (closes S10/S12 carry-overs) | sprint | 1 sprint |
| **S15** | Strategy gating verdict + decision (PASS → S16 plan, FAIL → revision OR abandon) | sprint | 1 sprint |
| **S16-S19** | Mainnet pilot Kelly Phase 1→4 progression | calendar-gated monitoring | 6-12 months |
| **S20** | 30d uptime test + MVP DONE acceptance review | sprint | 1 sprint |

**Calendar honesty:** S13-S15 = 1-2 weeks; S16-S19 = 6-12 months (dependent на trade frequency); S20 = 1 sprint final review. Total: ~6-13 months calendar к MVP DONE.

### DSR gate active S13 (Q5 CONFIRM)

DSR > 0 per acceptance-criteria.md gating step 4 (footnote 2 added per CC4 reconciliation). N_trials=1 для S13 first measurement. N_trials increments per subsequent re-measurement (S14+ если PARTIAL FAIL → tuning iter).

### PBO gate deferred S15+ (Q5 CONFIRM)

PBO requires MCS framework (~3 sprints scope) — defer post-MVP per acceptance-criteria.md footnote 3.

### 48h validation decoupled (Q6 CONFIRM)

48h Bybit demo validation runs as parallel operator background activity. NOT block sprint code cadence. Per S12 ADR 0027 T3-T4: infrastructure verification only (FSM/reconcile/WS), не strategy edge. Operator can run when convenient.

### Spec reconciliation (CC4 — already amended)

`acceptance-criteria.md` gating step 1 amended с footnotes:
- ¹ 5y aspirational, floor 3.5y (Bybit data availability dependent)
- ² DSR active S13+ (N_trials tracking required)
- ³ PBO deferred S15+ (MCS framework needed)

Reconciles inconsistency между acceptance-criteria.md "5 лет" + migration-plan.md "2y".

### Cross-cutting concerns (binding)

- **CC1 (N_trials tracking infrastructure):** Each measurement attempt increments N_trials. S13 = N_trials=1. Future tuning iter = N_trials=2. Track explicitly в sprint pages + DSR computation.
- **CC2 (Bybit data availability — single biggest unknown):** PHASE 3 step 1 REST API probe BEFORE any backfill code. Result drives Q2 split decision + Q4 target span.
- **CC3 (Spec PBO gate documentation):** S13 measurement uses T1-T6 + DSR only; PBO formally deferred с rationale в ADR + acceptance-criteria.md footnote.
- **CC4 (Spec doc reconciliation — DONE):** acceptance-criteria.md amended с footnotes resolving 5y vs 2y inconsistency.

### Reviewer matrix

- T1 (data availability probe): inline (operator REST call, no code change)
- T2 (backfill wire): python-reviewer + data-integrity-reviewer (Bybit pagination + Parquet write)
- T3 (run backfill): operator action (no code review)
- T4 (NaN pre-flight): python-reviewer (similar к prior S13 attempt T1)
- T5 (trade extractor): quant-stats-reviewer MANDATORY (DSR pipeline correctness)
- T6 (T1-T6 metrics): quant-stats-reviewer MANDATORY (formula correctness per acceptance-criteria.md)
- T7 (verdict report): inline + maintainer
- T8 (PHASE 8 wiki sync): sprint-finish skill

## Consequences

**Plus:**
- First empirical T1-T6 measurement on statistically adequate sample (≥3.5y, target 5y)
- Bybit Spot venue consistency preserved (per ADR 0016)
- DSR gate active с N_trials tracking начато
- Spec inconsistency reconciled (CC4 — 5y vs 2y resolved)
- 48h validation decoupled — не блокирует code sprint
- Roadmap explicit с calendar honesty (6-13 months к MVP DONE)

**Minus:**
- ESC-1 defer pattern accepted = risk unbounded N_trials degradation (acknowledged, операtor must track)
- Bybit may not provide 5y → fallback к 3.5y (still adequate per ADR 0014 math, но less than spec aspiration)
- Bear-regime gap (2022 may not be в Bybit Spot history if launched later) — verdict may не stress-test ranging market
- HARD FAIL on 5y measurement = strong "no edge" verdict, project may approach abandonment branch
- Mainnet pilot calendar 6-12 months untested — could exhaust user motivation OR market regime

**S14 carry-overs (anticipated):**
- DSR threshold calibration (S15+ per S11 Q5 — needs ≥30 empirical trades, depends на S13 outcome)
- Per-fold trade extraction follow-ups (если S13 measurement surfaces edge cases)
- 48h validation report processing (if operator runs in S13 timeframe)

## Related

- [[../pre-s13-backlog]] — PHASE 2 verdicts trail с trader source claims verified (CC1)
- [[0027-sprint-12-live-demo-validation]] — predecessor sprint (operator infrastructure consumed)
- [[0014-walk-forward-train2000-test500]] — WFA params (K=5, train=2000, test=500)
- [[0015-sign-flip-mc-permutations-n2000]] — MC permutations
- [[0016-bybit-spot-supersedes-binance]] — venue policy (Q3 binding)
- [[0025-sprint-10-wfa-dsr-mc]] — WFA + DSR + MC implementation
- [[../architecture/acceptance-criteria]] — 12 gating criteria (amended footnotes per CC4)
- [[../architecture/migration-plan]] — original 10-sprint roadmap (deviated, S13-S20 corrected herein)

## Amendments

- (none yet)
