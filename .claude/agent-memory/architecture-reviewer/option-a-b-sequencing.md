---
name: Cheap-test-first sequencing principle (v0.4 + v0.5 confirmed)
description: Cheap falsification must precede expensive construction even when expensive option has stronger academic support. Confirmed twice.
type: project
---

## Pattern (confirmed S19 brainstorm v0.4 + S22 brainstorm v0.5, 2026-04-26)

### v0.4 instance (S19)
Option (A) BTC 15M mean-reversion: APPROVE_WITH_CONDITIONS (3 blockers, 2 sprints).
Option (B) ML XGBoost filter: DEFER until (A) confirms edge.
Rationale: N=59 trades@1H insufficient for CPCV. 15M = ~4× trades = better ML basis. Sequence: A first.

### v0.5 instance (S22)
Option (C) 4H mean-reversion: CONFIRM (1-2 sprints, 100% infrastructure reuse).
Option (A) ML XGBoost: DEFER to v0.6+ (N=59 too small, fold #5 contamination, CPCV 3-5 sprint infrastructure).
Option (B) HMM regime-switch: DEFER (4-6 sprints scope, regime leakage in WFA is hard).
Rationale: 4H cheap test confirms/refutes timeframe-specificity of 1H partial signal before committing to
5-10 sprint ML construction.

**Why:** Scientific sequencing: falsify cheap hypothesis first, validate expensive hypothesis only if cheap one
survives. Same principle as Bailey 2014 pre-registration — avoid post-hoc direction changes.

**How to apply:** In any future brainstorm with a cheap (1-2 sprint) and expensive (5-10 sprint) competing
option: always CONFIRM cheap first if it provides meaningful counterfactual evidence. Exception: if cheap
option is trivially pre-determined to fail (see AND-gate frequency floor concern below).

## Related architectural risk: AND-gate frequency floor interaction

Tight AND-gate (RSI AND BB) at lower timeframe frequencies may make T5 structurally unreachable before
measurement. At 4H, estimated ~15-25 trades total — below T5=100 floor. Recommend offline frequency probe
as mandatory T0 for any timeframe-shift hypothesis. If probe shows T5 unreachable at pre-registered floor,
either relax AND-gate parameters or lower T5 floor (with pre-registration) before committing sprint.
