---
title: ADR 0052 — Sprint 34 Acceptance-Criteria Amendment LOCKED (paired hybrid с ADR 0051)
type: decision
tags: [adr, sprint-34, acceptance-criteria-amendment, t5-floor-amendment, n-eff-gate, mc-tightened, locked-pre-registration]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0014-walk-forward-acceptance-thresholds.md
  - project/decisions/0050-sprint-33-trading-restart.md
  - project/decisions/0051-sprint-34-honest-close-v06.md
  - project/architecture/acceptance-criteria.md
  - project/pre-s33-backlog.md (S34 Direction Consilium section)
---

# ADR 0052 — Sprint 34 Acceptance-Criteria Amendment LOCKED

## Status

Accepted (2026-04-27) — implemented в S34 (`feature/sprint-34-honest-close-v06-hybrid` → tag `v0.1.0-alpha.34`). **LOCKED для future resumption** (anti-data-snooping per Bailey & López de Prado 2014).

Hybrid pair с ADR 0051 (6-th honest close v0.6 — A(a) component). This ADR (0052) handles A(b) acceptance-criteria amendment component.

**No measurement run в S34** — amendment locked для future v0.7+ resumption only. Operator written acknowledgment required перед running new measurement.

## Context

Per S34 Direction Consilium (3 agents trader-expert + trading-logic-reviewer + quant-stats-reviewer ROUND 1+2 documented в `pre-s33-backlog.md` S34 section):

**CONSENSUS A(b) primary:** acceptance-criteria amendment с 10-item mandatory pre-commit list. Operator chose hybrid (merge с A(a) honest close per ADR 0051).

### Statistical justification для amendment

S33 demonstrated structural insights:

1. **T5=100 floor от Bailey 2014 generic** — calibrated для traditional academic equity research, не crypto small-sample reality
2. **Hudson & Urquhart 2021 documented crypto sparse-signal reality** — 30-100 trades typical sample size 4H mean-reversion, не deficient by asset-class standard
3. **Multi-symbol expansion empirically falsified S33** — correlation deflation rho≈0.75 BTC/ETH/SOL gives n_eff=26 от n_raw=66. Cannot buy way к T5=100 через correlated-asset expansion.
4. **n_eff (Kish 1965 design effect) NEW threshold mandatory** — raw n insufficient measure для multi-symbol
5. **MC threshold tighten partial compensation** — relaxing T5 floor offset by tightening MC ≤ 0.05 (from 0.10) preserves overall rigor

### Pre-check outcome (S34 T1 per ADR 0051)

S33 data на amended gates **STILL FAILS 4/5** (T5 raw passes, n_eff/MC/T6/DSR fail). Amendment alone insufficient — confirms 6-th honest close justified. Future resumption requires NEW measurement.

## Decision

**Amend acceptance-criteria.md per consilium 10-item pre-commit list.** LOCKED — no further modifications without new ADR + operator written acknowledgment.

### 10-item Pre-Commit List (LOCKED — verbatim per consilium ROUND 2 trader-expert)

1. **T5 floor: 100 → 50** (cite Hudson & Urquhart 2021 crypto sparse-signal reality)
2. **n_eff threshold: ≥ 50** — n_eff applies Kish 1965 design effect correction; raw n does NOT substitute (S33 lesson)
3. **MC threshold: ≤ 0.05** (tightened от 0.10 — partial compensation для T5 floor relaxation)
4. **T6 OOS/IS: ≥ 0.7 UNCHANGED** — independently blocking, not relaxed
5. **acceptance_gate.sharpe_gate_passed: UNCHANGED** — fold-level gates remain at existing thresholds
6. **Operator written acknowledgment:** "Statistical evidence as of v0.6 DOES NOT support live deployment; this amendment reflects crypto-specific sample-size reality (Hudson & Urquhart 2021), not evidence of positive edge"
7. **Strategy params: `MEAN_REVERSION_S17_RELAXED_PARAMS` LOCKED** (no new param search — anti-snooping per Bailey 2014)
8. **Backtest data period:** must extend through full available OHLCV history beyond S33 measurement date
9. **Multi-symbol: n_eff correction mandatory** — rho и Kish factor pre-registered в new measurement ADR
10. **N_trials counter starts ≥ 4** (accumulating prior trials в sigma_SR pooling protocol (a))

### Operator written acknowledgment template

S35+ resumption ADR MUST include verbatim:

> **Operator acknowledgment per ADR 0052 (S34 amendment):**
> 
> Statistical evidence as of v0.6 DOES NOT support live deployment. This amendment reflects crypto-specific sample-size reality (Hudson & Urquhart 2021), not evidence of positive edge. I authorize new measurement sprint с amended acceptance gates (T5 floor 50, n_eff ≥ 50, MC ≤ 0.05, T6 ≥ 0.7 unchanged, DSR ≥ 0.95 unchanged) с full awareness that:
> 
> - 6 prior strategy hypotheses tested across 4.81y BTCUSDT + S15+S33 multi-symbol — все FAIL conjoint
> - Multi-symbol expansion empirically falsified due correlation deflation
> - Hudson & Urquhart 2021 small-sample reality validated 3 times
> - Amendment NOT permission for live deployment without new measurement clearing amended gates

### NOT permitted без new ADR

- ❌ Lower T5 below 50
- ❌ Drop n_eff threshold
- ❌ Loosen MC threshold above 0.05
- ❌ Lower T6 below 0.7
- ❌ Lower DSR below 0.95
- ❌ New strategy params без new ADR с pre-registration
- ❌ Reuse S17/S22/S33 results as "PASS" под amended spec (anti-snooping — new measurement mandatory)

## Engineering Implementation

Per S34 T4 (paired commit):
- `src/backtest/walk_forward.py` `evaluate_acceptance_gate()` extended с optional kwargs:
  - `n_trades_raw: int | None`
  - `n_trades_n_eff: int | None`
  - `n_eff_threshold: int | None`
  - `t5_floor: int | None`
  - `mc_threshold: float = 0.10` (default v0.5 — overridable к 0.05 per S34)
- Backward-compat: existing callers без new args continue working (defaults к v0.5 behavior)
- New tests: `tests/unit/test_acceptance_gate_amendment.py` (5 tests verifying amended thresholds)

## acceptance-criteria.md Update

Add amendment section (paired commit):

```markdown
## S34 Amendment (LOCKED ADR 0052 — pending operator acknowledgment for v0.7+ resumption)

| Threshold | v0.5 (original) | v0.7+ (amended LOCKED) |
|-----------|----------------|-----------------------|
| T5 n_trades raw floor | 100 | 50 |
| T5 n_eff threshold (NEW) | N/A | ≥ 50 (Kish 1965 mandatory) |
| MC p-value threshold | ≤ 0.10 | ≤ 0.05 (tightened) |
| T6 OOS/IS Sharpe ratio | ≥ 0.7 | ≥ 0.7 UNCHANGED |
| DSR | ≥ 0.95 | ≥ 0.95 UNCHANGED |
| acceptance_gate.sharpe_gate_passed | per-fold strict | UNCHANGED |
```

## Consequences

### Positive

1. **Forward path locked** — operator может resume v0.7+ без brainstorm-init repeat (amendment pre-registered)
2. **Anti-snooping discipline preserved** — amendment LOCKED ДО measurement, не post-hoc
3. **Hudson & Urquhart 2021 cited explicitly** — academic justification documented
4. **n_eff threshold NEW** — closes correlation-deflation loophole (S33 insight)
5. **MC tightened** — overall rigor preserved despite T5 relaxation
6. **Operator acknowledgment template** — writes statistical reality в record на resumption time

### Negative

1. **Amendment может never be used** — operator может choose pause indefinitely (ADR 0051 Option (a))
2. **Pre-check показал S33 fails amended** — even amended spec не unlock S33 data. Resumption requires new measurement.
3. **n_trials counter ≥ 4** — future DSR penalty severely raised (Bailey 2014). Future PASS будет statistically harder.

### Neutral

1. No code regression — `evaluate_acceptance_gate()` backward-compat
2. No production behavior change — amendment LOCKED, не active until operator acknowledges + new measurement
3. Pattern continues precedent: pre-registered ADR ДО measurement (S33 ADR 0050 pre-committed failure branch worked correctly)

## Implementation

Paired commits per S34 T3 + T4:
- T3 (this commit): ADR 0052 + acceptance-criteria.md amendment section
- T4 (next): `src/backtest/walk_forward.py` `evaluate_acceptance_gate()` extended + tests

## Follow-ups

**Operator action когда resuming (S35+):**
1. Decide direction (per ADR 0051 v0.7+ options)
2. Если choose (b) new measurement с amended spec:
   - Write operator acknowledgment template verbatim в S35+ ADR
   - Extend OHLCV data beyond S33 measurement date
   - Pre-register multi-symbol rho + Kish factor (если multi-symbol)
   - Run new measurement sprint с amended gates LOCKED here
   - n_trials counter starts ≥ 4 (per Item #10)
3. Если choose other path: новый ADR с pre-registered hypothesis (anti-snooping)

## Related

- ADR 0014 (WFA acceptance thresholds — ORIGINAL spec amended here)
- ADR 0050 (S33 Trading Restart — pre-committed failure branch trigger source)
- ADR 0051 (S34 6-th honest close v0.6 — paired hybrid)
- ADR 0052 (this — acceptance-criteria amendment LOCKED)
- pre-s33-backlog.md S34 Direction Consilium section
- Bailey & López de Prado 2014 (DSR + pre-registration discipline + N_trials penalty)
- Hudson & Urquhart 2021 (heavy-tail t-stat critique + crypto sparse-signal reality — T5 amendment justification)
- Kish 1965 (design effect для clustered samples — n_eff threshold)
