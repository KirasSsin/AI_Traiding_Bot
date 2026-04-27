---
title: ADR 0055 — Sprint 36 δ TESTNET Activation (HaltGate Wire-up + B1 Critical Fix)
type: decision
tags: [adr, sprint-36, testnet-activation, halt-gate-wireup, b1-critical-fix, hybrid-duration, n-trials-freeze, mainnet-defer]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/decisions/0053-sprint-35-testnet-live-demo.md
  - project/pre-s36-backlog.md
---

## Status

Accepted (2026-04-27) — implemented в S36 (`feature/sprint-36-delta-activation` → tag `v0.1.0-alpha.36`). Paired ADR 0056 (DSR sigma_SR amendment, same sprint).

## Context

Post-S35 ROUND 4 consilium (3 agents — trader-expert + trading-logic-reviewer + quant-stats-reviewer + ROUND 2 trader-expert binding на Q4) CONSENSUS on (b) δ TESTNET activate. α Donchian FAIL conjoint (S35), direction CLOSED. δ infrastructure ready (HaltGate + 5 settings + MAINNET-exclusion DOUBLE-LOCKED) но UNWIRED.

7 strategy hypotheses tested cumulative — все FAIL conjoint. S22 best evidence (DSR=0.996, MC p=0.018 post-S33 fix) — supports forward path despite small-n reality.

Pre-s36-backlog.md ROUND 1+2 trail documents 5 questions Q1-Q5 + 7 binding pre-commitments + critical findings (B1 + B2 + B3 + N_trials freeze).

## Decision (8 sub-decisions)

### SD-1 — Hybrid duration option (H) verbatim per ROUND 2 trader-expert BINDING

> δ TESTNET runs indefinitely until ONE event fires:
> (a) HaltGate trigger (DD/loss streak/no-trade timeout — ADR 0053 unchanged)
> (b) PASS gates achieved (n≥50 + ADR 0052/0053 conjoint)
> (c) 12mo calendar = **MAINNET-promotion gate, NOT shutdown.** Если n<50 на review → "underpowered informational" + TESTNET continues unless operator halts. MAINNET locked.
> No 6mo interim checkpoint (conflicts с ADR 0053 line 62 6mo no-trade halt).

Rationale: ROUND 1 had 3-way split (12mo+6mo / single event / n-gate 36mo). ROUND 2 trader-expert CHANGED → hybrid (H). Critical finding: ADR 0053 line 62 already commits "≥ 6 months без n ≥ 30 closed trades → halt". 6mo interim checkpoint redundant + conflicting authority + snooping vector.

### SD-2 — B1 CRITICAL fix mandate

`MEAN_REVERSION_S17_RELAXED_PARAMS` LOCKED params MUST be wired к live path BEFORE day-1 trade. Currently:
- `MeanReversionRsiBBStrategy.__init__` uses `bb_k=2.0` default (LOCKED dict spec `bb_std_mult=1.5`)
- `Settings.strategy_rsi_oversold=30/overbought=70` defaults (LOCKED 35/65)
- `src/__main__.py:124-131` passes Settings defaults, ignores LOCKED constant

Pre-commit #7 from pre-s35-backlog.md silently violated. Must fix в S36 T2.

Implementation: rename `bb_k` → `bb_std_mult` constructor param, add `and_gate_required` constructor param, add `from_locked_s17_params()` classmethod factory, conditional wire-up в `__main__.py` когда `s35_demo_active=True`.

### SD-3 — Multiday DD definition

multiday_dd = HWM since `s35_demo_active=True` activation timestamp. Persistence: SQLite `equity_snapshots` table extended OR new `s35_activation_log` row.

Activation timestamp persisted на first run with `s35_demo_active=True`. Restart safety: read on subsequent runs from SQLite, не Settings (env vars могут change без code change).

multiday_dd computation: `(hwm_since_activation - current_total) / hwm_since_activation`. Returns 0 если current >= hwm.

### SD-4 — HaltTrigger → ReasonCode mapping table

| HaltTrigger | ReasonCode |
|-------------|------------|
| `DD_INTRADAY` | `HALT_S36_DD_INTRADAY` |
| `DD_MULTIDAY` | `HALT_S36_DD_MULTIDAY` |
| `CONSECUTIVE_LOSSES` | `HALT_S36_CONSECUTIVE_LOSSES` |
| `NO_TRADE_TIMEOUT` | `HALT_S36_NO_TRADE_TIMEOUT` |

Distinct codes (NOT reused HALT_DRAWDOWN_L*/HALT_FLASH_CRASH) preserve audit-log attribution per trading-logic-reviewer ROUND 1 verdict. Canonical reason codes count: 45→49.

### SD-5 — HaltGate halt resume protocol

HaltGate-triggered halt requires operator review. NO HMAC override path (OverrideStore не applies к HaltGate halts — see trading-logic C5 from ROUND 1).

Resume mechanism: manual FSM reset через `--reconcile-only` CLI subcommand OR SPRINT_STATE update (operator decision). Operator MUST document review findings в halt_log audit trail entry.

Rationale: HaltGate triggers are pre-committed gates (DD/streaks/timeout) — automated resume would violate anti-snooping discipline. Operator review = honest acknowledgment.

### SD-6 — Adapted gates methodology для live data

Per quant-stats-reviewer ROUND 1 verbatim:

1. **Live Sharpe estimator** — computed on per-TradeRecord returns (NOT bar-level WFA equity). Annualized via `sqrt(bars_per_year / avg_bars_per_trade)`.
2. **T6 OOS/IS replacement** — live/synthetic calibration ratio = `live_Sharpe / S22_synthetic_Sharpe`. Pre-registered S22 benchmark (constant in code, NOT runtime-mutable).
3. **MC gating** — sign-flip iff n≥20 trades; block-bootstrap iff n≥40 trades. Below threshold → MC reported as `"MC_INSUFFICIENT_N"` flag.
4. **DSR thresholds** per ADR 0056:
   - n_trades < 10 → DSR=NaN, status=`INSUFFICIENT_TRADES`
   - 10 ≤ n_trades < 30 → DSR computed, status=`UNDERPOWERED`
   - n_trades ≥ 30 → DSR computed, status=`GATE_ELIGIBLE`

### SD-7 — N_trials FREEZE at 7 для δ live demo

δ uses `MeanReversionRsiBBStrategy` с `MEAN_REVERSION_S17_RELAXED_PARAMS` = same hypothesis as S22 (re-evaluation, not new strategy search). Bailey 2014 multi-testing penalty applies к hypothesis search, NOT к forward evaluation of pre-registered strategy.

`DELTA_N_TRIALS_LOCKED = 7` constant в `src/analytics/live_trade_reporter.py` с verbatim enumeration comment:

```python
# Cumulative mean-reversion family hypothesis count (ADR 0055 SD-7):
# S13 EMA crossover, S15 mean-reversion strict, S17 mean-reversion relaxed,
# S20 mean-reversion 15M, S22 mean-reversion 4H, S33 multi-symbol mean-reversion,
# S35 Donchian breakout. δ TESTNET = S22 hypothesis re-evaluation (frozen).
DELTA_N_TRIALS_LOCKED: int = 7
```

### SD-8 — MAINNET promotion criteria DEFERRED к S37+

Pre-commit MAINNET thresholds сейчас = premature без TESTNET data context. After 12mo TESTNET review (per SD-1 option (c)), operator decides:

- (i) S37+ ADR pre-registers MAINNET promotion criteria (n≥X / Sharpe≥Y / etc) verbatim
- (ii) MAINNET deferred indefinitely (TESTNET continues OR β pause)

MAINNET-exclusion invariant remains DOUBLE-LOCKED (live_trading + testnet flag + validate_assignment) — no MAINNET path until S37+ ADR explicitly opens it.

Operator acknowledgment template для S37+ ADR (verbatim per ADR 0052):

> "Statistical evidence as of v0.7 [TESTNET data results]; this MAINNET promotion reflects [evidence summary]. I authorize MAINNET activation с pre-committed acceptance gates [criteria]. No fresh hypothesis search."

## Consequences

### Positive
- Forward path locked (anti-snooping) — operator has clear next step
- B1 critical fix prevents silent S15-noise params под δ activation
- 4 NEW ReasonCodes preserve audit-log attribution
- Hybrid duration option (H) honors all 3 reviewer concerns без введения 36mo abandonment risk
- N_trials freeze correct per Bailey 2014 (no spurious DSR penalty for re-evaluation)

### Negative
- 12mo TESTNET review may be statistically inconclusive (n≈13 expected at S22 baseline rate ~13/year). MAINNET-promotion conversation deferred indefinitely possible.
- HaltGate-triggered halt = manual operator review (no automated resume) — operational overhead
- N_trials=7 freeze may be challenged in future audits if rigorous reviewer counts re-evaluation as new trial

### Neutral
- No code regression — all ADR 0053 commitments preserved
- canonical FSM counts unchanged (16/30/74) — only reason codes 45→49

## Implementation

Per S36 plan (`plans/2026-04-27-sprint-36-delta-activation.md`):
- T1 (this commit): ADR 0055 + ADR 0056 paired
- T2: B1 fix + factory + conditional wire-up
- T3: 4 state-source methods
- T4: HaltGate wire-up в RuntimeManager._tick
- T5: ReasonCode +4 HALT_S36_*
- T6: DSR sigma_SR refactor (ADR 0056 implementation)
- T7: Live trade reporter
- T8: Wiki sync

## Follow-ups

**Operator action когда δ activates:**
1. Write `s35_demo_active=True` env var в production .env
2. Restart bot — first run records activation timestamp в SQLite
3. Monitor halt_log + SQLite trade_history weekly
4. At 12mo + n<50: choose continue OR halt OR S37+ ADR for MAINNET discussion
5. At halt trigger: operator review halt_log, decide manual FSM reset OR honest close S37+

## Related

- ADR 0050 (S33 Trading Restart)
- ADR 0051 (S34 6-th honest close v0.6)
- ADR 0052 (S34 acceptance-criteria amendment LOCKED)
- ADR 0053 (S35 δ TESTNET activation — paired predecessor)
- ADR 0054 (S35 α Donchian pre-registration — direction CLOSED)
- ADR 0056 (this — DSR sigma_SR amendment, paired)
- pre-s36-backlog.md ROUND 4 consilium trail
- Bailey & López de Prado 2014 (DSR + pre-registration discipline)
- Hudson & Urquhart 2021 (heavy-tail t-stat critique + crypto sparse-signal reality)
