---
title: 0033. Sprint 18 — v0.1 honest close (3 strategy hypotheses tested across 4.81y BTC)
type: decision
date: 2026-04-26
sprint: 18
tags: [adr, sprint-18, honest-close-v01, no-edge-conjoint, mvp-incomplete, hypothesis-3-tested, partial-signal-evidence, n-trials-archival-final]
sources:
  - project/decisions/0032-sprint-17-btc-mean-reversion-relaxed.md
  - project/decisions/0031-sprint-16-honest-close-v02.md
  - project/decisions/0029-sprint-14-honest-close.md
  - project/sprints/sprint-17-btc-mean-reversion-relaxed.md
  - project/sprints/sprint-15-mean-reversion-multi-symbol.md
  - project/sprints/sprint-13-backfill-wfa.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0033. Sprint 18 — v0.1 honest close (3 strategy hypotheses tested)

**Status:** accepted
**Date:** 2026-04-26

## Контекст

S17 shipped (PR #25, tag `v0.1.0-alpha.17`). Verdict FAIL — T5 count only (59 trades < 100 floor). 5/6 strategy criteria PASS + DSR=1.0 + MC p=0.01 statistically significant = **first time positive direction observed по most criteria одновременно**.

Per ADR 0032 amendment 3 BINDING (pre-registered before S17 measurement):
> "If OOS trades < 100 → VERDICT FAIL declared on T5 count alone, t_stat skipped, S18 = honest close v0.1 (3 hypotheses tested, documented)."

S18 = pre-committed honest close, no new brainstorm needed. Pattern mirrors S14 ADR 0029 + S16 ADR 0031 (docs-only sprints).

## Решение

### S18 scope: v0.1 honest close ship

**v0.1 final status declaration:**

- **Infrastructure: ✅ COMPLETE** — 16 FSM states / 30 events / 74 transitions / 45 reason codes / 38 component pages / 33 ADRs / 20 sprint pages / WFA + DSR + MC + cross-trial log + multi-symbol CLI + 3 strategy classes wired
- **Strategy validation: ❌ NEGATIVE conjoint × 3 hypotheses** —
  | # | Hypothesis | Sprint | OOS Trades | Pass criteria | Verdict |
  |---|-----------|--------|-----------|--------------|---------|
  | 1 | EMA(12)×(26) + ADX(14) + RSI(14) + ATR(14) на 1H BTCUSDT | S13 (4.81y) | 20 | T3 only | FAIL (T1+T2+T4+T5) |
  | 2 | Mean-reversion RSI<30 AND close<lower_BB(20, 2σ) на 1H × 3 symbols BTC+ETH+SOL | S15 | 108 | T1+T2+T3+T4 (T5 floor reached) | FAIL (T6+MC+DSR) |
  | 3 | Mean-reversion RSI<35 AND close<lower_BB(20, 1.5σ) на 1H BTCUSDT relaxed | S17 | 59 | T1+T2+T3+T4+T6+DSR+MC | FAIL (T5 count only) |
- **MVP DONE per acceptance-criteria.md: NOT achieved conjoint** (no single hypothesis passed T1-T6 + DSR conjointly)
- **Mainnet exposure: 0** (Bybit demo 33min only since S12)
- **Tag: `v0.1.0-alpha.18`** = v0.1 final honest close marker

### Critical scientific finding (S17 institutional knowledge)

**Mean-reversion RSI+BB AND-gated trigger на BTC produces statistically significant signal** (S17 MC p=0.01 + DSR=1.0 + T1=25.99 + 5/6 criteria PASS на 59 OOS trades). **Sample size insufficient** на 1H BTC alone.

Strategy edge IS real but observable only с aggregation: multi-symbol (S15 partial — но noise dilution) OR higher-frequency timeframe (15M deferred per Q3 architectural blockers).

Single-symbol BTC 1H mean-reversion RSI+BB ≈ ~60-70 OOS trades / 4.81y maximum (frequency structural limit per S17 actual + S15 BTC alone 44 trades empirical baselines).

### S18 deliverables (docs-only)

**T1: ADR 0033 (this document)** — accepted, status final.

**T2: sprint-18-honest-close-v01 page** — canonical v0.1 final close summary с:
- Final v0.1 status declaration (3 hypotheses tested negative conjoint)
- All measurement results trail (S13 + S15 + S17 aggregated)
- S17 partial signal evidence preserved (institutional knowledge для v0.4+)
- Cross-trial log archival policy (mirror S16 CC2)
- All carry-overs preserved (12+ items)

**T3: cross_trial_sharpes archival**:
```bash
mv data/cross_trial_sharpes.json data/cross_trial_sharpes_v0.1-final.json
echo '{"trials": []}' > data/cross_trial_sharpes.json  # v0.4 fresh baseline
```

**T4: Wiki sync** — current-state.md + index.md updated к "v0.1 closed honest" + counts (ADR 32→33, sprint pages 19→20).

**T5: log.md sprint-end entry** — chronological closure event.

**T6: SPRINT_STATE → between-sprints с post-v0.1-honest-close status** — operator decides v0.4 future direction.

**T7: PHASE 8 ship** — sprint-finish: tag `v0.1.0-alpha.18` (v0.1 final honest close marker).

### NO new code, NO measurement re-run

Per pre-committed ADR 0032 amendment 3: S18 = documentation + archival policy. Zero code changes. Q7-S12 zero-migration constraint preserved trivially.

### Cross-cutting concerns (binding)

- **CC1 (S17 partial signal preserved для v0.4+):** MC p=0.01 + DSR=1.0 + T1=25.99 на 59 BTC trades = strongest evidence project produced. ADR 0033 must document это institutional knowledge: future v0.4 hypothesis space с этим signal в mind = mean-reversion variant, NOT trend-following.
- **CC2 (cross_trial_sharpes archival policy — BINDING, mirrors S16 CC2):** v0.4 fresh hypothesis MUST archive `data/cross_trial_sharpes.json` (containing `[{sprint:17, oos_sharpe:0.712}]`) к `data/cross_trial_sharpes_v0.1-final.json` + reset `data/cross_trial_sharpes.json` к `{"trials": []}`. Without this policy, future sprint inherits S17 anchor — partial signal evidence biases new hypothesis testing. Implemented в S18 T3.
- **CC3 (Frequency structural limit documented):** Single-symbol BTC 1H mean-reversion RSI+BB AND-gated = ~60-70 OOS trades / 4.81y maximum (S15 baseline 44 + S17 relaxed 59). T5 floor 100 NOT reachable without (a) higher-frequency timeframe (15M = 4x = 240+ trades estimate), (b) multi-symbol aggregation (out of MVP scope per user 2026-04-26), OR (c) different signal class (trend-following = lower frequency, не помогает). Future MVP-DONE attempts must address frequency dimension.
- **CC4 (Q3 15M architectural blockers preserved final):** Per S16 CC6 + S15 architecture-reviewer: `src/marketdata/bybit/rest.py:66-67` interval_map KeyError + `src/platform/config.py:97-102` heal_max_age_seconds 1H coupling (production safety bug at 15M). 2 sprints architectural cost preserved для potential v0.4 revival.
- **CC5 (Tag semantics):** `v0.1.0-alpha.18` = v0.1 FINAL honest close marker, NOT MVP DONE. v0.1.0 (drop alpha) reserved для actual T1-T6 + DSR + MC PASS conjoint achievement (not currently feasible per single-symbol frequency limit).
- **CC6 (No spec amendment):** acceptance-criteria.md NOT modified. T1-T6 thresholds stand. v0.1 honest close acknowledges thresholds не met conjoint для chosen strategies + timeframe + venue + symbol scope.
- **CC7 (Multi-symbol infrastructure preserved post-MVP):** S15 T1 load_recent symbol filter + T5 --symbols CLI + MeanReversionRsiBBStrategy = preserved для potential post-MVP v0.4+ revival (out of MVP scope per user 2026-04-26 BTC-only constraint).

### Future direction options (deferred к operator, NO commitment)

Per S17 institutional knowledge — partial signal evidence shifts probability landscape:

**(v0.4-A) BTC 15M mean-reversion** — addresses frequency floor structural limit. Q3 architectural blockers documented (interval_map + heal_max_age production safety refactor). Cost: 2 sprints (1 architecture + 1 measurement). **Strongest viable path** given S17 evidence (mean-reversion regime works, just sample-bound).

**(v0.4-B) Hybrid mean-reversion + ML filter** — S15 ADR 0030 deferred ML к v0.3+ on basis "no partial signal evidence". S17 PROVIDES partial signal evidence (MC p=0.01). Reconsider XGBoost classifier на BTC mean-reversion features. Cost: 5-10 sprints (CPCV framework new, feature engineering, model registry). High infrastructure cost, but academically supported по S17 evidence.

**(v0.4-C) Multi-symbol revival** — out of MVP scope per user 2026-04-26 ("торговать будем в mvp только btc/usdt"). Could be reconsidered post-MVP if MVP-DONE achieved on BTC-only first. Infrastructure preserved (S15).

**(v0.4-D) Different timeframe — 4H** — lower frequency than 1H, не addresses T5 floor structural limit. Не recommended per S17 evidence (mean-reversion signal already weak в high-frequency regime).

**(v0.4-E) Project pause** — close current branch, freeze repo as "v0.1 final honest close marker — infrastructure complete + 3 strategy hypotheses tested + 1 partial signal observed". Reactivate if новый candidate emerges.

**Operator decides if/when. No commitment from S18.**

## Последствия

**Plus:**
- Honest closure based on 3 empirical measurements (S13 + S15 + S17 across 4.81y BTC Bybit Spot 1H)
- 19 sprints infrastructure preserved + reusable для future MVP-DONE attempts (with frequency-dimension address)
- DSR cross-trial accumulator broken cleanly via archival policy (mirrors S16 pattern)
- S17 partial signal evidence (MC p=0.01) = institutional knowledge для v0.4 hypothesis selection
- Pre-committed honest close (per ADR 0032 amendment 3) — clean failthrough execution, no p-hacking pressure
- Q3 15M architectural blockers documented для potential future revival
- 0 capital exposure (no Mainnet)
- Pattern reuse от S14 ADR 0029 + S16 ADR 0031 (proven 3rd honest close в проекте)

**Minus:**
- "MVP DONE" не achieved conjoint per acceptance-criteria.md spec (no spec amendment)
- 3 strategy hypotheses (EMA crossover + multi-symbol mean-reversion + BTC-only mean-reversion relaxed) empirically rejected на conjoint T1-T6 + DSR + MC
- All S12-S17 carry-overs unaddressed (12+ items remain open)
- No live trading validation beyond 33min S12 demo
- Q3 15M architectural fixes deferred (interval_map, heal_max_age production safety)
- ML XGBoost framework deferred (CPCV pipeline new infrastructure)

**v0.4+ carry-overs preserved (anticipated):**

All previous + new from S17:
- F live demo Mainnet validation actual run (operator-driven, not run since S12)
- FillRecorderAdapter Layer 2 schema link (entry_signal_id к execution_state migration)
- 3-way endpoint enum (DEMO/TESTNET/MAINNET) — Q6 future fix
- T2 review C3 init_db dual-conn comment (S11 carry-over)
- DSR per-fold DataFrame→TradeRecord conversion (S10 informational)
- DSR threshold calibration (S15+ per S11 Q5)
- halt_log INSERT order swap в `_set_halt` (PRE-EXISTING)
- find_by_order_id ORDER BY explicit (T1 reviewer follow-up)
- fill-history.md / bybit-adapter.md / ws-private-consumer.md component page updates
- T2/T5/T6 quant-stats deferred concerns (Sortino formula docs, sqrt(8760) frequency-agnostic, boundary tests)
- 48h Bybit demo validation (operator-driven)
- Q3 15M architectural blockers (interval_map + heal_max_age — preserved per CC4)
- Multi-symbol live runtime fan-out (S15 deferred — `_cmd_run` kept single-symbol)
- Capital allocation cross-symbol exposure caps (S15 deferred — out of MVP per user)
- **NEW S17 carry-over:** S17 fold #5 sharpe 3.50 outlier — strategy edge concentrated в few periods, concerning для production stability
- **NEW S18 carry-over:** S17 partial signal evidence (MC p=0.01) — institutional knowledge для v0.4 hypothesis selection: mean-reversion variant, NOT trend-following

## Связанные документы

- [[../pre-s17-backlog]] — S17 PHASE 2 trader EXPAND verdict (option a с amendments)
- [[0032-sprint-17-btc-mean-reversion-relaxed]] — S17 ADR (T5 failthrough clause triggered)
- [[0031-sprint-16-honest-close-v02]] — S16 v0.2 honest close (precedent + cross_trial archival pattern)
- [[0030-sprint-15-mean-reversion-multi-symbol]] — S15 ADR (multi-symbol infrastructure)
- [[0029-sprint-14-honest-close]] — S14 v0.1 first honest close attempt (precedent pattern)
- [[0028-sprint-13-strategy-validation]] — S13 ADR (-44.46 anchor)
- [[../sprints/sprint-17-btc-mean-reversion-relaxed]] — S17 measurement results
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable, not amended)
- [[../architecture/migration-plan]] — original roadmap (closed final at S18)
- [[../sprints/sprint-18-honest-close-v01]] — спринт delivery record

## Поправки

- (none yet)
