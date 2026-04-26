---
name: DSR kurtosis convention bug (Sprint 9)
description: Bailey eq.13 denominator requires total (Pearson) kurtosis gamma4; Fisher=True returns excess (total-3), causing systematic error of +3 in the gamma4-1 term
type: project
---

Bailey & Lopez de Prado (2014) eq.13 denominator:
`sigma^2(SR) = (1 - gamma3*SR + (gamma4-1)/4 * SR^2) / (T-1)`
where gamma4 = TOTAL (Pearson) kurtosis. For Normal: gamma4=3, term=(3-1)/4=0.5, giving the standard Lo (2002) variance formula (1+SR^2/2)/(T-1).

`scipy.stats.kurtosis(bias=False, fisher=True)` returns EXCESS kurtosis = total - 3. Using excess in the formula produces (excess-1)/4 instead of (total-1)/4, a systematic underestimate of the denominator by 3/4 * SR^2.

**Fix:** use `fisher=False` (Pearson/total) OR add +3 to the Fisher result before substituting into eq.13.

**Why:** Confirmed by numerical probe 2026-04-25 — Normal sample gives fisher~0, Pearson~3, diff=3.0 exactly.

**How to apply:** Any future DSR implementation — always verify kurtosis convention. The wiki code snippet in deflated-sharpe-ratio.md uses `gamma_4` without specifying convention; treat as total (Pearson).

**File:** `src/analytics/dsr.py:96` — `kurt = float(stats.kurtosis(finite_returns, bias=False, fisher=True))` is wrong; must be `fisher=False`.
