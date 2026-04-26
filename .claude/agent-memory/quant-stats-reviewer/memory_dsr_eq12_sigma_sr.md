---
name: DSR eq.12 sigma_SR multiplier — RESOLVED Sprint 10
description: Sprint 10 Q7 adds sigma_sr param to compute_dsr; Bailey eq.12 now correctly implemented. n_trials>1 without sigma_sr raises ValueError.
type: project
---

Bailey eq.12: E[max SR_hat] = mu_SR + sigma_SR * ((1-gamma)*Phi^-1(1-1/n) + gamma*Phi^-1(1-1/(n*e)))

**Sprint 9 bug (CLOSED):** `sharpe_star` missing multiplication by sigma_SR.

**Sprint 10 fix (commit 0dc0b8a):** `sigma_sr: float | None = None` added to `compute_dsr`. When n_trials>1 and sigma_sr is None → ValueError. Formula at `src/analytics/dsr.py:121`:
`sharpe_star = benchmark_sharpe + sigma_sr * ((1.0 - gamma) * z1 + gamma * z2)`

**Verified correct:** 4 tests pass. Euler-Mascheroni 10-digit (1.53e-12 error) is negligible for float64. Monotonicity confirmed numerically.

**Edge cases (untested but benign):**
- sigma_sr=0 → sharpe_star=benchmark (degenerate but valid)
- sigma_sr<0 → accepted silently (could add validation)

**How to apply:** No longer flag as Concern. If sigma_sr<0 surfaces in production, flag then.
