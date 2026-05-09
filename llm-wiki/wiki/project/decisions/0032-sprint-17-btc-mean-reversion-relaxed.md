---
title: 0032. Sprint 17 — BTC-only mean-reversion relaxed (RSI 35/65 + BB 1.5σ), MVP retry hypothesis #3
type: decision
date: 2026-04-26
sprint: 17
tags: [adr, sprint-17, btc-only-mvp, mean-reversion-relaxed, hypothesis-3, t5-failthrough, n-trials-fresh]
sources:
  - project/pre-s17-backlog.md
  - project/decisions/0031-sprint-16-honest-close-v02.md
  - project/decisions/0030-sprint-15-mean-reversion-multi-symbol.md
  - project/sprints/sprint-15-mean-reversion-multi-symbol.md
  - project/architecture/acceptance-criteria.md
  - project/decisions/0016-bybit-spot-supersedes-binance.md
status: accepted
---

# 0032. Sprint 17 — BTC-only mean-reversion relaxed, MVP retry hypothesis #3

**Status:** accepted
**Date:** 2026-04-26

## Контекст

S16 closed v0.2 honest (PR #24, tag `v0.1.0-alpha.16`). User clarification 2026-04-26: "торговать будем в mvp только btc/usdt" — MVP scope = BTCUSDT only per ADR 0016 + ADR 0004 original.

S17 = continue к MVP DONE с new strategy hypothesis #3 (после S13 EMA crossover + S15 mean-reversion multi-symbol — both FAIL).

**N_trials=1 fresh baseline confirmed:** `data/cross_trial_sharpes.json = {"trials": []}` (S16 T6 archival completed). DSR gate at n_trials=1 reverts к single-trial formula (Bailey eq. 12, sigma_SR = cross-fold std of single WFA run). -44.46 anchor gone.

S17 PHASE 2 brainstorm — single direction question delegated к trader-expert per user directive "пусть агенты сами и решат".

**Q1 trader EXPAND verdict:** option (a) BTC-only mean-reversion с relaxed thresholds = least-bad surviving option, с 3 mandatory amendments.

## Решение

### S17 scope: BTC-only mean-reversion relaxed (1 sprint)

**Strategy hypothesis #3 (pre-registered binding):**

```
LONG entry: RSI(14) < 35 AND close < lower_BB(20, 1.5σ)
EXIT:       RSI(14) > 65 OR close > upper_BB(20, 1.5σ) OR ATR(14) trailing stop hit

Symbol: BTCUSDT only (per ADR 0016 + MVP scope user-confirmed 2026-04-26)
Timeframe: 1H (per ADR 0005, не amended)
Venue: Bybit Spot
WFA params: K=5, train=2000, test=500, embargo=20 (per ADR 0014, unchanged)
N_trials accumulator: fresh start (S16 T6 reset confirmed)
```

### 3 mandatory amendments (per trader EXPAND, BINDING)

**Amendment 1 — Pre-registered parameters BINDING:**

RSI thresholds 35/65 + BB(20, 1.5σ) locked BEFORE WFA measurement. NO post-result tuning. NO operator override. Same entry/exit AND-gate logic as S15 — only thresholds changed.

**Amendment 2 — DROP variance cap:**

S15 maintainer recommendation included "drop fold sharpe < -10" variance cap. Trader analysis: -10 was reverse-engineered from S15 ETH outlier (-188.65). BTC-only worst fold sharpe в S15 ≈ -7 — cap нечего к trigger. P-hacking red flag for external audit. **DROPPED entirely** (BTC-only sparse signals, не нужна outlier protection).

**Amendment 3 — T5 count failthrough clause:**

If OOS trades < 100 → **VERDICT = FAIL declared on T5 count alone**, t_stat skipped, S18 = honest close v0.1 (3 hypotheses tested, documented).

Clean binary outcome:
- **Pass T5 floor (n≥100):** measure t_stat + DSR + remaining T1-T6 → if all PASS, MVP strategy criteria DONE → continue к S1-S6 system-level criteria + Mainnet pilot
- **Fail T5 floor (n<100):** S18 = honest close v0.1 (sprint-18 documents 3 hypotheses negative result as publishable-quality scientific contribution)

NO "tune one more time" pressure if T5 count is 80-99. Operator pre-commits per ESC-2.

### Frequency math (trader-verified, expected outcome)

BTC S15 baseline: 44 trades / 2500 OOS bars = 1.76% signal rate (RSI 30/70 + BB 2σ AND-gated).

Threshold relaxation multipliers:
- BB(20, 1.5σ) one-sided tail = 3.34% vs 2σ = 2.27% → **1.47× raw**
- RSI<35 vs RSI<30 → **~1.17× raw**
- AND-gate joint multiplier (positive correlation between RSI extreme + BB breach) = **1.4-1.7× actual** (NOT 2-3× independent)
- **Expected BTC trades: 44 × 1.55 ≈ 68. Conservative 66, optimistic 88.**
- **T5 floor 100 = uncertain to unreachable.** Honest pre-registration acknowledges may FAIL.

### S17 deliverables

**T1: ADR 0032 (this document)** — accepted, status final.

**T2: indicators.py config update** — verify mean_reversion branch accepts `rsi.oversold/overbought` + `bb.period/k` cfg params (already implemented S15 T6, just update defaults для S17).

**T3: _run_wfa_single_symbol config update** — set `rsi.oversold=35`, `rsi.overbought=65`, `bb.k=1.5` в WFA config dict.

**T4: Measurement run** — `python -m src wfa --symbol BTCUSDT --start 2021-07-02 --end 2026-04-26` (single-symbol, NOT --symbols).

**T5: Sprint-17 page + ADR + wiki sync** — current-state.md + index.md + log.md + SPRINT_STATE updates.

**T6: PHASE 8 ship** — sprint-finish: tag `v0.1.0-alpha.17`. PR #25.

### Cross-cutting concerns (binding)

- **CC1 (T5 frequency uncertainty):** Honest pre-registration. ADR + sprint-17 page document expected 66-88 trades (T5 floor 100 borderline). Failthrough clause first-class outcome.
- **CC2 (Variance cap dropped):** Audit-clean. ADR explicitly notes -10 threshold was ETH-pathology-derived и не applies к BTC-only.
- **CC3 (ATR regime filter unsuitable):** Document к prevent future re-proposal — regime filters frequency-reducing, contraindicated для sparse signal sets.
- **CC4 (Honest close v0.1 if FAIL):** S18 docs-only sprint mirrors S14/S16 pattern. 3 hypotheses tested → publishable-quality negative result.
- **CC5 (Tag semantics):** `v0.1.0-alpha.17` = MVP retry attempt #3 marker. NOT MVP DONE даже на PASS (system-level S1-S6 + Mainnet validation остаются — separate sprints).
- **CC6 (No spec amendment):** acceptance-criteria.md T1-T6 thresholds preserved.
- **CC7 (Multi-symbol infrastructure preserved):** S15 T1 load_recent symbol filter + T5 --symbols CLI = post-MVP scope, не used в S17 BTC-only measurement (single --symbol).

## Последствия

**Plus:**
- Cheapest test (1 sprint, reuses S15 infrastructure 100%)
- Fresh N_trials=1 DSR baseline (no -44.46 anchor penalty)
- BTC +1.75 / p=0.197 strongest observed signal as starting point
- BINDING pre-registration eliminates p-hacking risk
- T5 failthrough = clean honest-close path if FAIL → 3 hypotheses negative = stronger scientific contribution
- Dropped variance cap = audit-clean

**Minus:**
- T5 count может fail (66-88 expected vs 100 floor) — honest acknowledgment
- Relaxed thresholds = more noise per-trade → mean_pnl/std_pnl may shrink → t_stat may stay <2 even при T5 PASS
- Single-symbol = no aggregation buffer (S15 multi-symbol added 60+ trades from ETH/SOL but added noise)
- 3rd hypothesis attempt = diminishing returns argument, может show "trying same family thrice"

**v0.4+ carry-overs (если S17 PASS, MVP DONE pursued):**

If S17 strategy criteria PASS (T1-T6 + DSR + PBO):
- **S18+: System-level S1-S6 measurement** — Uptime ≥99.5% (30+ days live), WS reconnect p99<5s (production measurement), P&L recon ≥99.99%, Dashboard p95<2s (NEED dashboard built — currently не impl), Config hot-reload (NEED implementation), Zero API key leaks (NEED gitleaks/trufflehog в CI)
- **S20+: Mainnet pilot Phase 1** (Kelly 1% fixed)
- **S25+: Live trading data accumulation** для Kelly phase progression (1→2→3→4)

If S17 strategy criteria FAIL:
- **S18: Honest close v0.1** (docs-only sprint mirroring S14/S16 pattern). Project freeze as "infrastructure complete + 3 strategy hypotheses tested negative — publishable scientific contribution".

All previous carry-overs preserved (S12+S13+S14+S15+S16, 12+ items): F live demo Mainnet, FillRecorderAdapter Layer 2, 3-way endpoint enum, halt_log INSERT order, find_by_order_id ORDER BY, component pages updates, quant-stats deferred concerns, 48h Bybit demo, Q3 15M architectural blockers, multi-symbol live runtime, capital allocation cross-symbol caps.

## Связанные документы

- [[../pre-s17-backlog]] — PHASE 2 trader EXPAND verdict (option a с amendments)
- [[0031-sprint-16-honest-close-v02]] — S16 v0.2 honest close + CC2 cross_trial archival policy + CC1 BTC institutional knowledge
- [[0030-sprint-15-mean-reversion-multi-symbol]] — S15 multi-symbol infrastructure (preserved post-MVP)
- [[../sprints/sprint-15-mean-reversion-multi-symbol]] — S15 BTC alone +1.75 signal observed
- [[../sprints/sprint-16-honest-close-v02]] — S16 final v0.2 close
- [[0016-bybit-spot-supersedes-binance]] — venue + BTC-only original scope
- [[0014-walk-forward-train2000-test500]] — WFA params unchanged
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)

## Поправки

- (none yet)
