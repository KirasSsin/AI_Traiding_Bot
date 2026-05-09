---
name: S39 autoresearch iter 10 verdict (updated — operator stop criterion)
description: Trader-expert verdicts on volume_breakout autoresearch — iter 10 (57 PASS) + operator stop criterion change (+100% PnL goal analysis)
type: project
---

# S39 Autoresearch Iter 10 (57 PASS → 213 PASS, 4.51M trials) — Combined Verdict

**Date:** 2026-05-08
**Context (iter 10a, 1.31M trials):** 1310 sweeps × 1000 trials = 1.31M trials. 57 PASS all volume_breakout.
**Context (iter 10b, 4.51M trials):** 45 batches × 1000 trials = 4.51M trials. 213 PASS all volume_breakout (4.72% rate).

## Iter 10a: Q1/Q2/Q3 verdicts (57 PASS, before B&H baseline known)

### Q1: Real edge vs. overfit → REVISE (regime-ambiguous)
Not clean real edge. Not simple noise. Correct characterization: "Volume-confirmed breakout shows structural advantage over tested alternatives within the evaluated regime. Forward applicability unknown." Gate 1 required: compute B&H baseline on held-out.

### Q2: Optimization direction → REVISE (skip grid, go to forward test)
Reject focused grid. 57 PASS already provides well-estimated centroid (L=10, ex=8, vw=12, vm=1.36, ap=14, am=2.58). Forward test with centroid params on post-2026-04-26 data. Research-toy script (option a) correct path.

### Q3: Production readiness → EXPAND (3-gate framework)
Gate 1: B&H baseline. Gate 2: N≥10 forward signals. Gate 3: ADR pre-registration.

---

## Iter 10b: Operator stop criterion change (+100% PnL goal)

**New data (fills Gate 1):** Held-out B&H = -30.14% (BEAR regime CONFIRMED).

### Q1: Is +100% PnL feasible? → CONFIRM (b) — NO, structural ceiling

**Definitively NO.** Three independent layers:
1. Empirical: 4.51M trials, max observed = +20.4%. No approach to +100% anywhere in param space.
2. Physics: Long-only + ATR-stop in -30.14% B&H bear regime. Upward volatility budget ~40-60% total; realistic capture with ATR-stop/exit_lookback ≈ 20-30%. +100% exceeds total regime budget.
3. Trade count: ~15 trades at ~0.9% per-trade = +13.7%. Reaching +100% requires 6.7% per-trade (7× observed mean). ATR stop caps single trade at bear-rally magnitude (~3-8%) minus commission. 6.7% average is above bear-rally capture envelope.

+100% is NOT a matter of finding better params. It is physically impossible given regime + model design.

### Q2: What should operator do? → EXPAND

"NEVER STOP" protocol applies to theoretically reachable criteria. When criterion is physically impossible, continued searching is resource waste, not discipline.

**Recommended operator action (in order):**
1. STOP search immediately (criteria permanently unreachable; additional trials worsen anti-snooping contamination)
2. Recognize research success: 213 PASS with +13.7% mean in -30.14% B&H regime = +43.8% alpha — this IS genuine edge
3. Choose path: (A) forward test per 3-gate framework, (B) request compounded equity curve model, (C) reframe criterion

The "NEVER STOP" rule needs a "criterion feasibility pre-check" gate: verify criterion achievable given regime physics before starting/continuing search.

### Q3: Max achievable PnL? → EXPAND

Empirical ceiling: ~+20-25% (distribution tight, no trial above +20.4% after 4.51M trials). Theoretical ceiling under bear regime physics: ~+30% (generous upper bound). Not +50%, not +100%.

**Critical point for operator:** The backtest PnL metric (sum of per-trade sequential %) is a RESEARCH DISCRIMINATOR, not a dollar-return projector. Under 0.25× Kelly sizing (v0.1 constraint), actual account return from a +13.7% research-metric strategy is materially less than +13.7%. The operator's "$10k → $20k" goal requires an equity curve model, not raw PnL% maximization.

---

## Key escalations for operator

ESC-1 (BLOCKING): What does success mean — statistical alpha identification OR dollar return projection? These require different metrics and success criteria.
ESC-2: Stop sweep now vs. continue (resource decision, operator owns it). Expert recommendation: STOP.

## Cross-cutting patterns to remember

CC-1: Research PnL metric ≠ account return. Never conflate. PASS criterion is for param discrimination only.
CC-2: "NEVER STOP" requires feasibility pre-check. If criterion exceeds regime physics budget, escalate immediately.
CC-3: 4.51M trials with tight distribution = exhaustive exploration done. More trials = anti-snooping damage, not information.
