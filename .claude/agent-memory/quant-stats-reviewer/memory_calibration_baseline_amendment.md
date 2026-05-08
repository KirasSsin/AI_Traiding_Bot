---
name: S22 calibration baseline 6.17 vs 2.96
description: S22_SYNTHETIC_SHARPE=6.17 is extreme-value aggregate (fold concentration); mean fold=2.96 is more robust central-tendency estimate. ADR 0057 amendment recommended.
type: project
---

S22_SYNTHETIC_SHARPE in `src/analytics/live_trade_reporter.py:28` is set to 6.17 — the aggregate S22 WFA Sharpe. This is an extreme-value estimate driven by small-n fold concentration (K=5 folds, 62 total trades). The code comment at line 27 already acknowledges 2.96 as the mean fold Sharpe alternative.

**Why:** Calibration ratio = live_Sharpe / 6.17. At n=13 (expected 12mo δ trades), the ratio is statistically noisy with SE ~0.31/6.17 ≈ 0.05. Using 6.17 denominator produces pessimistic ratios (e.g., live=1.8 → ratio=0.29 vs. 0.61 against 2.96). Ratio is informational only at UNDERPOWERED status, but operator communication effect is real.

**How to apply:** When reviewing live_trade_reporter.py or any calibration ratio report, note that 6.17 baseline likely understates calibration. ADR 0057 amendment proposal: substitute 2.96 (mean fold OOS Sharpe per S22 WFA). This is a methodology correction (central tendency vs. extreme-value), NOT a data-driven post-hoc pick — 2.96 computed from synthetic WFA in S22. 0.7 pass threshold unchanged.

Historical record: S22 aggregate Sharpe 6.17 preserved in sprint-22 page. S37 consilium ROUND 5 voted RECOMMEND AMENDMENT.
