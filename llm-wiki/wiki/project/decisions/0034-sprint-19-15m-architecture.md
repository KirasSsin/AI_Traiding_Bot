---
title: 0034. Sprint 19 — BTC 15M architectural sprint (v0.4 prep, 7 amendments)
type: decision
date: 2026-04-26
sprint: 19
tags: [adr, sprint-19, v0.4-direction-A, btc-15m, mean-reversion, architectural-sprint, t5-floor-150, annualization-fix, heal-max-bars-refactor]
sources:
  - project/pre-s19-backlog.md
  - project/decisions/0033-sprint-18-honest-close-v01.md
  - project/decisions/0032-sprint-17-btc-mean-reversion-relaxed.md
  - project/decisions/0021-sprint-7-resilience.md
  - project/decisions/0014-walk-forward-train2000-test500.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0034. Sprint 19 — BTC 15M architectural sprint (v0.4 direction A)

**Status:** accepted
**Date:** 2026-04-26

## Context

S18 closed v0.1 FINAL honest (PR #26, tag `v0.1.0-alpha.18`). 3 hypotheses tested. S17 partial signal evidence preserved (MC p=0.01 on 59 BTC trades — first genuine signal в проекте).

User directive 2026-04-26: "Зайди с этими вопросами в агентов трейдеров, пусть они проведут дискуссию и выберут" → trader-expert + architecture-reviewer joint dispatch для v0.4 direction selection.

S19 PHASE 2 verdict (joint):
- **Trader EXPAND → CONFIRM (A)** с 4 amendments + 2 ESCs
- **Architecture APPROVE_WITH_CONDITIONS (A)** с 3 mandatory conditions
- **Convergence:** Option (A) BTC 15M mean-reversion, **2 sprints** (S19 architectural + S20 measurement)

ESC resolutions (autonomous mode per "пусть они выберут"):
- ESC-1 (continue vs pause): CONTINUE Option (A) — 2 sprints cheap, S17 evidence justifies test
- ESC-2 (T5 floor 15M): RAISE к 150 trades — simpler than autocorrelation-corrected t-stat, scales appropriately

## Decision

### S19 scope: BTC 15M architectural sprint (preparation для S20 measurement)

**S19 = architectural prep ONLY. NO measurement run.** S20 = WFA measurement sprint follows.

### 7 combined amendments (4 trader + 3 architecture, ALL BINDING)

**Architecture Conditions (3 mandatory, structural blockers):**

**Condition A1** — `rest.py:66-67` interval_map KeyError fix + single-dict refactor.
- Trader-flagged: KeyError on "15" prevents 15M backfill.
- Architecture-recommended: consolidate dual `interval_map` + `interval_ms` к single `intervals: dict[str, tuple[str, int]]` к prevent future TF drift.
- Status: ✅ APPLIED (commit incoming).

**Condition A2** — `config.py:97-102` heal_max_age semantic refactor → `heal_max_bars: int | None`.
- Trader-flagged: production safety bug (3600s = 4 bars at 15M = silent stale-fill acceptance).
- Architecture-recommended: keep Settings pure value store, derive seconds at bootstrap (`_cmd_run` + `_cmd_reconcile_only`).
- Backward-compat: `heal_max_bars=None` falls back к legacy `heal_max_age_seconds` field.
- Default `heal_max_bars=1` matches pre-S19 1H semantic but applies к any interval.
- Operator migration: explicit `HEAL_MAX_AGE_SECONDS` в `.env` без `HEAL_MAX_BARS=null` set → silent legacy behavior preserved.
- Status: ✅ APPLIED.

**Condition A3 (HIGH)** — `sqrt(8760)` annualization parameterization (3 files: strategy_metrics.py + wfa_reporter.py + vector_backtest.py).
- Trader-flagged + architecture-confirmed: 2× UNDERSTIMATE risk at 15M = false-FAIL на strategy с real edge.
- Architecture-recommended: parameterize `bars_per_year` arg (default 8760 = backward-compat 1H, caller passes 35040 для 15M).
- Wired в `_cmd_wfa --interval 15` → `bars_per_year=35040` automatic.
- Status: ✅ APPLIED.

**Trader Amendments (4 mandatory, scientific discipline):**

**T-Amendment 1** — T5 floor для 15M = **150 trades** (ESC-2 resolution).
- Rationale: 15M frequency increase = 4x trades; T5 floor 100 trivially exceeded. Scaling floor к 150 = ~31 trades/year (vs S13 EMA 4/year baseline) maintains information-density requirement.
- BINDING for S20 measurement: if OOS trades < 150 → VERDICT FAIL declared on T5 count alone.

**T-Amendment 2** — Fold concentration pre-registration.
- S20 verdict criteria must include: "If fold #5 (or any single fold) is sole profitable fold (removing it yields aggregate OOS Sharpe < 0), classified as REGIME CONCENTRATION — conditional PASS at best, T6 OOS/IS ratio = primary overfit detector."
- Prevents same fold #5 outlier problem from S17 silently determining S20 verdict.

**T-Amendment 3** — 15M data depth pre-condition.
- VERIFIED: Bybit BTC 15M data starts ≥ 2021-07-15 (~4.78y available, ~167K bars expected).
- T6 backfill confirms actual count в S19 commit.

**T-Amendment 4** — heal_max_age production safety.
- Encompassed by Condition A2 (architecture-recommended `heal_max_bars`).

### S19 deliverables (architectural sprint)

| Task | Status | Description |
|------|--------|-------------|
| T0 | ✅ DONE | Bybit 15M data depth verification (≥ 2021-07-15) |
| T1 | ✅ DONE | ADR 0034 (this document) |
| T2 | ✅ DONE | rest.py interval_map fix + single-dict refactor (Condition A1) |
| T3 | ✅ DONE | config.py heal_max_bars semantic refactor + bootstrap wiring (Condition A2) |
| T4 | ✅ DONE | Annualization factor parameterization (Condition A3 — 3 files) + CLI --interval arg |
| T5 | ✅ DONE | WFA params validation — KEEP ADR 0014 defaults (test=500 bars at 15M = ~5.2 days adequate per architecture) |
| T6 | pending | 15M backfill BTCUSDT (~167K bars expected) — running |
| T7 | pending | sprint-19 page + wiki sync |
| T8 | pending | PHASE 8 ship (PR + tag v0.1.0-alpha.19) |

### S20 (next sprint, measurement, BINDING per S19 amendments)

**Pre-registered configuration:**
```
Strategy: MeanReversionRsiBBStrategy (S15 ADR 0030)
Symbol: BTCUSDT only (per ADR 0016 + user 2026-04-26 MVP scope)
Interval: 15M
RSI: 35/65 (S17 relaxed — preserved для consistency)
BB: (20, 1.5σ) — S17 relaxed preserved
WFA params: K=5, train=2000, test=500, embargo=20 (ADR 0014 unchanged — re-evaluate post-measurement если OOS folds insufficient stable)
N_trials: 1 (fresh baseline, n_trials=1 single-trial DSR formula)
T5 floor: 150 trades (T-Amendment 1 BINDING)
```

**Verdict criteria (BINDING):**
- T5 < 150 trades → FAIL on count alone, t_stat skipped
- T5 ≥ 150 → measure t_stat + DSR + remaining T1-T6
- Fold concentration check (T-Amendment 2): if single fold drives positive aggregate → conditional PASS
- All T1-T6 + DSR + MC pass conjoint → MVP DONE strategy criteria → continue к S21+ S1-S6 system criteria + Mainnet pilot
- FAIL → S21 = honest close v0.4 (4 hypotheses tested = even stronger publishable scientific contribution)

### Cross-cutting concerns (binding)

- **CC1 (S20 MC + DSR fresh baseline)**: cross_trial_sharpes.json reset к [] after S18 archival. S20 = trial #1 fresh start (single-trial DSR formula).
- **CC2 (Fold concentration carry-over)**: pre-registered T-Amendment 2 — S20 verdict criteria include outlier check.
- **CC3 (heal_max_bars operator migration)**: ADR 0034 documents public config field change. Operators with explicit `HEAL_MAX_AGE_SECONDS=N` в `.env` get backward-compat (heal_max_bars defaults к legacy seconds derivation when field is None — actual behavior here uses default 1 bar). For operators wanting legacy seconds, set `HEAL_MAX_BARS=null` AND `HEAL_MAX_AGE_SECONDS=N` explicitly.
- **CC4 (DSR cross-trial dormant)**: per architecture concern 5 — single-hypothesis S20, no cross-trial sigma_SR needed. If multi-sub-hypothesis testing introduced → activate Bailey eq. 13 (5-sprint deferred carry-over from S14 Q2 REVISE).
- **CC5 (Tag semantics)**: `v0.1.0-alpha.19` = architectural sprint marker (NOT measurement, NOT MVP DONE).
- **CC6 (No spec amendment)**: acceptance-criteria.md T1-T6 thresholds preserved. T5 floor 150 = S20-specific pre-registration per Bailey 2014 multi-testing discipline (T5 spec says "n≥100 OOS trades" — 150 is stricter, не violates).
- **CC7 (Hudson & Urquhart 2021 noise risk)**: 15M mean-reversion may degrade per academic prior. S20 measurement is empirical test — direction может invalidate. Honest acknowledgment.

## Consequences

**Plus:**
- 4 critical bugs/anti-patterns fixed in single architectural sprint (interval_map + heal_max_age + annualization × 3 files)
- Single-dict `intervals` refactor prevents future TF drift
- `heal_max_bars` semantic refactor unlocks any timeframe (post-MVP 15M / 4H / 5M)
- Annualization parameterization unlocks correct Sharpe reporting at any timeframe
- S20 measurement infrastructure-ready (single command: `python -m src wfa --symbol BTCUSDT --interval 15 --start 2021-07-15 --end 2026-04-26`)
- 7 amendments BINDING + pre-registered = audit-clean per Bailey 2014
- T5 floor 150 honest scaling vs мechanical carry-forward
- Reuses 100% S17 strategy infrastructure (MeanReversionRsiBBStrategy + cfg dispatch)

**Minus:**
- Architectural sprint without measurement = 1 sprint без direct verdict outcome
- Bybit 15M data start 2021-07-15 vs 1H 2021-07-02 = ~13 days less coverage (negligible)
- Hudson & Urquhart 2021 academic prior negative (mean-reversion degrades sub-hourly) — empirical risk
- 5 sprint deferred DSR cross-trial gap (S14 Q2 REVISE) remains — dormant if S20 single-hypothesis, activates если retry

**v0.4+ carry-overs (anticipated):**

If S20 PASS:
- S21+: System-level S1-S6 measurement (Uptime ≥99.5%, WS reconnect, P&L recon, Dashboard p95<2s, Config hot-reload, Zero secrets leaks)
- S22+: Mainnet pilot Phase 1 (Kelly 1% fixed)
- S25+: Live trading data accumulation для Kelly phase progression

If S20 FAIL:
- S21: Honest close v0.4 (docs-only, mirrors S14/S16/S18 pattern, 4 hypotheses tested = scientific contribution)
- v0.5 options: Hybrid ML XGBoost (Option B reconsidered с 15M base signal data), regime-switch HMM, project pause

All previous carry-overs preserved (S12-S18, 14+ items).

## Related

- [[../pre-s19-backlog]] — PHASE 2 joint trader+architecture verdicts trail
- [[0033-sprint-18-honest-close-v01]] — S18 v0.1 FINAL honest close (predecessor)
- [[0032-sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal evidence (MC p=0.01)
- [[0021-sprint-7-resilience]] — heal_max_age_seconds origin (ADR superseded by Condition A2 semantic refactor)
- [[0014-walk-forward-train2000-test500]] — WFA params (preserved для 15M, re-evaluate post-S20)
- [[0030-sprint-15-mean-reversion-multi-symbol]] — MeanReversionRsiBBStrategy + indicators.py mean_reversion branch (reused 100%)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable, T5 floor 150 = S20 pre-registration)

## Amendments

- (none yet)
