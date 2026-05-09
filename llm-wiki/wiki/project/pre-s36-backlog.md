---
title: Pre-S36 Backlog — v0.7+ Direction Consilium ROUND 4 BINDING
type: backlog
tags: [pre-sprint, sprint-36, v07-direction, consilium-round-4, binding, testnet-activation, halt-gate-wireup, dsr-amendment, ru]
created: 2026-04-27
updated: 2026-04-27
status: active
sources:
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/decisions/0053-sprint-35-testnet-live-demo.md
  - project/decisions/0054-sprint-35-donchian-pre-registration.md
  - project/pre-s35-backlog.md
  - project/sprints/sprint-35-testnet-donchian-risk.md
---

# Pre-S36 Backlog — v0.7+ Direction Consilium ROUND 4

## Context

Post-S35 ship (v0.1.0-alpha.35). Operator directive: 3-agent consilium ROUND 4 на v0.7+ direction. Verdict BINDING per "как они скажут так и будем кодить".

S35 outcomes:
- ζ refactor: ✅ shipped
- δ TESTNET infrastructure: ✅ ready, NOT activated
- α Donchian: ❌ FAIL conjoint (n=21<<50, Sharpe=-0.95) → direction CLOSED per ADR 0054 pre-commit #8

7 strategy hypotheses tested cumulative — все FAIL conjoint. S22 best evidence (DSR=0.996, MC p=0.018 post-S33 fix).

## ROUND 1 verdicts (3 agents parallel)

### Q1 — v0.7+ direction primary

| Agent | Verdict | Note |
|-------|---------|------|
| trader-expert | **CONFIRM (b) δ activate** | ROUND 3 binding + S22 evidence + α/γ closed |
| trading-logic-reviewer | **CONFIRM (b)** + 2 BLOCKERS | B1 + B2 must resolve before day-1 trade |
| quant-stats-reviewer | **CONFIRM (b)** | S22 statistically defensible |

**CONSENSUS: (b) δ TESTNET activate.**

### Q2 — S36 scope

| Agent | Verdict |
|-------|---------|
| trader-expert | CONFIRM min viable + DSR ADR; ReasonCode mapping blocking |
| trading-logic-reviewer | 6-task minimum (T1 ADR + T2 param fix + T3 state methods + T4 wire-up + T5 ReasonCode + T6 tests) |
| quant-stats-reviewer | CONFIRM DSR amendment P0 + adapted gates methodology |

**CONSENSUS: scope expands к ~8-10 tasks (см. final S36 task list ниже).**

### Q3 sub-A (DSR sigma_SR amendment timing)

| Agent | Verdict |
|-------|---------|
| trader-expert | **CONFIRM pre-commit S36** (DSR=NaN + dsr_status flag когда N_cross_trial < 2) |
| quant-stats-reviewer | **CONFIRM pre-commit S36** (DSR=NaN когда N_cross_trial < 3 — stricter) |

**ACCEPT quant's stricter N≥3 threshold** (df=2 minimum для valid sigma_SR pooling per Bailey 2014).

### Q3 sub-B (ReasonCode enum extension)

| Agent | Verdict |
|-------|---------|
| trading-logic-reviewer | **REVISE → +4 NEW codes** (HALT_S36_DD_INTRADAY / DD_MULTIDAY / CONSECUTIVE_LOSSES / NO_TRADE_TIMEOUT). Reason: semantic differ от CB codes + audit log pollution. 45→49 codes. |

**ACCEPT** — domain reviewer authority on FSM/reason codes.

### Q4 — TESTNET duration commitment (3-WAY SPLIT → ROUND 2)

| Agent | ROUND 1 verdict |
|-------|-----------------|
| Maintainer | 12mo + 6mo interim checkpoint |
| trader-expert | REVISE — halt-or-12mo single review event |
| trading-logic-reviewer | 12mo + 6mo interim checkpoint |
| quant-stats-reviewer | REVISE — n-gate primary (n≥50 OR 36mo) |

**ROUND 2 trader-expert BINDING verdict: CHANGED → hybrid option (H)**

Critical discovery: ADR 0053 line 62 already commits "≥ 6 months без n ≥ 30 closed trades → halt + S36 honest close". Maintainer's 6mo interim checkpoint = **conflicting authority** + snooping vector. Quant's 36mo timeout still не guarantee n≥50 (~39 trades projected) + operator abandonment risk.

**BINDING verdict text (verbatim для S36 ADR 0055):**

> δ TESTNET duration is indefinite — runs until one of following events fires, whichever first:
>
> (a) HALT criteria trigger (HaltGate): DD ≥ -20% intraday, DD ≥ -15% multi-day, ≥ 5 consecutive losses, OR ≥ 6 months без n ≥ 30 closed trades → halt + honest close (ADR 0053 pre-committed, unchanged).
>
> (b) PASS gates achieved: n ≥ 50 trades AND all pre-committed gates satisfied (ADR 0052/0053) → operator review для MAINNET promotion eligibility.
>
> (c) 12-month calendar gate (ADR 0053 pre-commit #1): operator reviews TESTNET evidence после 12 months of live operation. **MAINNET-promotion prerequisite, NOT TESTNET shutdown trigger.** Если n < 50 на 12-month review, DSR/MC reported as "underpowered — informational only" и TESTNET continues unless operator elects halt. MAINNET remains LOCKED.
>
> No separate 6-month interim checkpoint introduced. ADR 0053's 6-month no-trade halt criterion provides operational early-exit mechanism для low-signal environments.

### Q5 — MAINNET promotion criteria

| Agent | Verdict |
|-------|---------|
| trader-expert | CONFIRM defer + n≥30 floor pre-commit now |
| trading-logic-reviewer | CONFIRM defer к S36 ADR (новая sub-decision в ADR 0055) |
| quant-stats-reviewer | REVISE — adapted gates methodology в S36 ADR |

**MERGE: defer mainnet thresholds к S37+ + S36 ADR includes:**
- Live-data Sharpe estimator (TradeRecord-level, не bar-level WFA)
- T6 OOS/IS replaced by live/synthetic calibration ratio (live_Sharpe / S22_synthetic_Sharpe ≥ 0.7)
- MC gating (sign-flip iff n≥20, block-bootstrap iff n≥40)
- DSR underpowered flag когда n<30
- n≥30 floor для any gate evaluation (informational reporting only ниже)

## CRITICAL findings

### B1 (trading-logic-reviewer CRITICAL BLOCKER)

`MEAN_REVERSION_S17_RELAXED_PARAMS` NOT wired к live path. `MeanReversionRsiBBStrategy.__init__` uses `bb_k=2.0` default (LOCKED params spec `bb_std_mult=1.5`). `Settings.strategy_rsi_oversold=30/overbought=70` defaults (LOCKED 35/65). `src/__main__.py:124-131` passes Settings defaults, ignores LOCKED constant.

**Pre-commit #7 from pre-s35-backlog.md silently violated при δ activation.** δ would run S15-noise params, не S22-validated S17-relaxed.

**MUST FIX в S36 BEFORE day-1 trade.**

### B2 (trading-logic-reviewer)

HaltGate.evaluate() never called в live path. `EquityTracker` lacks `intraday_dd_pct()` + `hwm_since(ts)`. `TradeHistoryRepository` lacks `consecutive_losses(symbol)` + `last_trade_ts(symbol)`. Multiday DD definition ambiguous (rolling 24h? since-activation HWM? since-last-trade?) — must be formally defined в S36 ADR.

### B3 (trading-logic-reviewer)

HaltTrigger → ReasonCode mapping doesn't exist. Need 4 new HALT_S36_* codes + property test extension + reason-codes.md wiki update.

### Quant N_trials counter discrepancy

`N_TRIALS_LOCKED = 5` в `donchian_runner.py` references S13/S15/S17/S22/S35 (5 strategy attempts including Donchian). For δ live demo, correct count = cumulative mean-reversion-family trials (S13 EMA + S15/S17/S20/S22/S33 mean-reversion + S35 Donchian = 7 cumulative). δ uses S22-validated params = same hypothesis re-evaluation, **N_trials FREEZES at 7** (no increment per Bailey 2014 multi-testing logic).

S36 must define `DELTA_N_TRIALS_LOCKED = 7` explicit с enumeration comment.

### DSR sigma_SR amendment (verbatim text per quant-stats-reviewer)

```
sigma_SR sourcing hierarchy (binding):

1. PREFERRED: cross-trial log >= 3 entries → sigma_SR = stdev(all_oos_sharpes), n_trials = len(entries)
2. DEGENERATE (1-2 entries): sigma_SR = NaN, DSR computed с n_trials=1, report "DSR_UNDERPOWERED — informational only. n_trials < 3"
3. INADMISSIBLE FALLBACK (REMOVED): per-fold Sharpe stdev as sigma_SR proxy. Confounds within-trial noise с cross-trial selection variability. Previously donchian_runner.py:191-193 — REMOVED в S36.

n_trades thresholds для DSR reporting:
- n_trades < 10: DSR = NaN (variance undefined)
- 10 <= n_trades < 30: DSR computed, flagged "UNDERPOWERED"
- n_trades >= 30: DSR standard computation, gate-eligible

Variable rename: `aggregate_oos_sharpe` (donchian_runner.py:171) → `trial_mean_fold_oos_sharpe` (clarifies arithmetic mean of fold OOS Sharpes, not pooled OOS Sharpe)
```

## S36 task list (consilium-merged)

| T | Task | Domain | LoC est |
|---|------|--------|---------|
| T1 | ADR 0055 — δ activation (multiday DD definition + HaltGate→ReasonCode mapping + resume protocol + DSR sigma_SR sourcing protocol + N_trials freeze + adapted gates methodology + duration commitment hybrid option H + mainnet promotion criteria deferred sub-decision) | docs | ADR ~250 lines |
| T2 | **CRITICAL FIX B1**: wire MEAN_REVERSION_S17_RELAXED_PARAMS к live path. Add `bb_std_mult` + `and_gate_required` к `MeanReversionRsiBBStrategy.__init__`. Update `src/__main__.py` к pass LOCKED params когда `s35_demo_active=True`. Tests verify live runtime uses LOCKED не Settings defaults. | code | ~80 LoC + 3 tests |
| T3 | Build state-source methods. `EquityTracker.intraday_dd_pct(now)` + `EquityTracker.hwm_since(since_ts)` + `TradeHistoryRepository.consecutive_losses(symbol)` + `TradeHistoryRepository.last_trade_ts(symbol)`. | code | ~150 LoC + 8 tests |
| T4 | HaltGate wire-up в `RuntimeManager._tick` (or new `_check_halt_gate()` method). Called once per bar когда `s35_demo_active=True`. HaltTrigger → ReasonCode → `Coordinator.request_halt()`. | code | ~80 LoC + 4 integration tests |
| T5 | ReasonCode enum extend +4 (HALT_S36_DD_INTRADAY / DD_MULTIDAY / CONSECUTIVE_LOSSES / NO_TRADE_TIMEOUT). Update `_REQUEST_HALT_CODES` allowlist. Update reason-codes.md wiki. Canonical count 45→49. | code+wiki | ~30 LoC + property test update |
| T6 | DSR sigma_SR ADR amendment + code refactor. Remove inadmissible per-fold stdev fallback. Add DSR=NaN logic для N_cross_trial<3. Rename `aggregate_oos_sharpe` → `trial_mean_fold_oos_sharpe`. Add UNDERPOWERED flag для 10≤n<30. | code+ADR | ~60 LoC + 5 tests |
| T7 | Live-data adapted reporter (T6 carry-over from S33+ live demo path). Live Sharpe estimator on TradeRecord list. Live/synthetic calibration ratio (live_Sharpe/S22_synthetic_Sharpe). MC gated на n≥20/n≥40. | code | ~120 LoC + 4 tests |
| T8 | sprint-36 page + 2 components (live-trade-ledger + halt-gate-wireup) + index/counts (54→55 ADRs + 39→40 sprints + 45→47 components) + log + SPRINT_STATE close | docs | wiki sync |

**Total: ~520 LoC + 24 tests + 1 ADR + 1 ADR amendment + 2 component pages.**

КУ forecast: ~10-15h (significantly larger than S35's ~5h — δ activation = production code changes vs S35's mostly infrastructure-without-wireup).

## Pre-commitments (S36 BINDING per ROUND 1+2 consilium)

1. **B1 CRITICAL fix**: MEAN_REVERSION_S17_RELAXED_PARAMS LOCKED params wired к live path BEFORE day-1 trade
2. **DSR sigma_SR sourcing protocol** per quant verbatim text (N≥3 PREFERRED, NaN+UNDERPOWERED для 1-2, FALLBACK REMOVED)
3. **N_trials freeze at 7** для δ live demo (S22 hypothesis re-evaluation, no increment)
4. **Adapted gates methodology** для live data (live Sharpe estimator + calibration ratio + MC gating)
5. **Hybrid duration option (H)**: HaltGate operational + n≥50 PASS gate + 12mo MAINNET-promotion gate (NOT TESTNET shutdown). 36mo NOT pre-committed. Underpowered flag для n<50.
6. **No 6mo interim checkpoint** (would conflict с ADR 0053 6mo no-trade halt criterion)
7. **MAINNET promotion criteria DEFERRED к S37+** post-12mo TESTNET review
8. **ReasonCode enum +4 HALT_S36_*** (45→49 canonical)

## Carry-overs к S37+

- MAINNET promotion criteria pre-commit (post-12mo TESTNET data)
- Donchian reason codes к ReasonCode enum (если α revival)
- Channel exit replay path (если α revival)
- t-stat heavy-tail correction (Hudson&Urquhart 2021 — CC-E)
- bybit-api-reviewer first real-world validation (S36 = TESTNET activation = first real bybit-api invocation under δ flag)

## Failure branch

Если в течение S36 execution:
- B1 fix reveals deeper strategy/Settings architectural debt → BLOCKED, escalate operator
- HaltGate wire-up uncovers FSM transition gaps → BLOCKED, escalate operator
- ADR 0053 contradictions found → BLOCKED, requires ADR 0053 supersession (new ADR)

## Related

- ADR 0050 (S33 Trading Restart)
- ADR 0051 (S34 6-th honest close v0.6)
- ADR 0052 (S34 acceptance-criteria amendment LOCKED)
- ADR 0053 (S35 δ TESTNET activation)
- ADR 0054 (S35 α Donchian pre-registration — direction CLOSED)
- pre-s35-backlog.md (ROUND 3 binding)
- Bailey & López de Prado 2014 (DSR + pre-registration discipline)
- Hudson & Urquhart 2021 (heavy-tail t-stat critique + crypto sparse-signal reality)
- Kish 1965 (design effect)
- [[decisions/0055-sprint-36-delta-activation]] — Sprint 36 ADR (δ activation)
- [[decisions/0056-sprint-36-dsr-sigma-sr-amendment]] — Sprint 36 ADR (DSR amendment)
- [[sprints/sprint-36-delta-activation]] — Sprint 36 page
