---
name: n_eff asymptote theorem (Kish 1965) — multi-symbol expansion cannot solve T5
description: Kish 1965 design effect produces a hard asymptote for n_eff as k symbols grows; at rho=0.75 and 22 trades/symbol the asymptote is 29.3, permanently below T5=100. Proven S33 consilium 2026-04-27.
type: project
---

**Theorem (derived S33 Direction Consilium):**

n_eff asymptote as k -> infinity = n_per_symbol / rho

Where:
- n_per_symbol = average trades per symbol per period
- rho = average inter-symbol return correlation
- Kish 1965: DE = 1 + (k-1)*rho → n_eff = n_per * k / DE

**S33 values:**
- n_per = 22 trades/symbol (BTC+ETH+SOL average over 4.81y)
- rho = 0.75 (BTC-ETH), 0.70 (BTC-SOL)
- Asymptote (rho=0.75) = 22/0.75 = 29.3 (BELOW T5=100 permanently)
- Asymptote (rho=0.50, mixed asset classes) = 22/0.50 = 44.0 (still below T5=100)

**Implication:** Adding any number of correlated crypto symbols cannot raise n_eff above
n_per/rho. To make n_eff >= 100 reachable:
- Need n_per >= 100 * rho = 75 trades/symbol at rho=0.75
- Current 4H mean-reversion: 4.6 trades/year → 75 trades requires 16x signal frequency
- IMPOSSIBLE within 4H mean-reversion strategy class

**How to apply:** Any future multi-symbol expansion proposal — check if n_per/rho >= T5.
If not, expansion path is structurally infeasible regardless of symbol count.

**A(b) amendment implication:** Lowering T5 to 50 does NOT help — n_eff=26 < 30 < 50.
The amendment would need T5 <= 26 which is post-hoc rationalization (Bailey 2014 S.6).

**Why:** S33 T5 demonstrated empirically; asymptote formula proved the general case.
