---
name: S10 brainstorm Round 1 verdicts
description: Binding verdicts for S10 PHASE 2 brainstorm Q1-Q7 — 2026-04-25 (WFA + DSR + MC permutations)
type: project
---

**Date:** 2026-04-25. Sprint S10 brainstorm round 1.

Q1 (WFA window unit bars vs hours): CONFIRM — bars. ADR 0014 explicit, 1H=1bar, YAGNI.

Q2 (DSR acceptance gate third layer): REVISE — DSR gate DEFERRED to reporter/display only (not a hard AND gate). With K=5 folds OOS, typical trade count 10-40 per fold — DSR is high-variance and will over-reject valid strategies. Gate only on ADR 0014 (Sharpe ≥ 0.7) + ADR 0015 (MC p ≤ 0.05). DSR reported alongside as informational metric.

Q3 (MC permutation on return series vs signal series): CONFIRM — return series (pnl_pct sign-flip). Matches ADR 0015 "preserves marginal distributions PnL". No replay re-run required (N=2000 cheap with numpy). Block bootstrap secondary handles autocorrelation.

Q4 (Revive S2 backtest vs new engine): CONFIRM with caveat — revive + extend. But MANDATORY pre-audit: replay_engine Sharpe uses bar-returns annualized sqrt(24*365) — WFA gate needs per-trade Sharpe for DSR. New walk_forward.py must extract trade list per fold, NOT reuse _compute_metrics Sharpe. Separate DSR path from reporter path.

Q5 (per-fill vs per-trade DSR): CONFIRM — per-trade only for S10. Per-fill inflates N artificially (correlated within trade).

Q6 (annualization factor for display Sharpe): REVISE — do NOT derive annualization factor from observed trade frequency (circular, overfits to specific backtest run). For display Sharpe in WFA reporter: use sqrt(365*24) = sqrt(8760) for 1H crypto (24/7 market, consistent with existing replay_engine line 51). ADR 0014 gate (OOS/IS Sharpe ≥ 0.7) MUST use the same factor in both IS and OOS numerically — ratio is what matters, so factor cancels if consistent. Key: document which Sharpe (per-trade vs annualized) is used in the gate, pick one, apply consistently.

Q7 (DSR n_trials > 1 sigma_SR): CONFIRM — implement sigma_SR for WFA aggregate DSR. K=5 folds gives sigma_SR = std(per-fold Sharpe across 5 folds). Use as informational aggregate metric, not a hard gate (per Q2 decision above).

**Critical cross-cutting concern:** replay_engine._compute_metrics() Sharpe (line 51) uses bar-level equity returns * sqrt(24*365). WFA needs per-trade Sharpe for DSR. These are DIFFERENT series. walk_forward.py must produce BOTH: (a) per-trade list for DSR input, (b) equity series for existing Sharpe metric. Do NOT conflate.
