---
name: S11 brainstorm Round 1 verdicts
description: Binding verdicts for S11 PHASE 2 brainstorm Q1-Q7 — 2026-04-25 (scope ordering, pre-flight, operator-readiness)
type: project
---

**Date:** 2026-04-25. Sprint S11 brainstorm round 1.

Q1 (scope ordering F vs A): CONFIRM — A-first (Operator-readiness). _cmd_run STUB = bot literally unrunnable. Cannot do live demo without fixing it first. Pre-flight gaps (Q2) are blocking prerequisites for both F and A. But A scope (monitoring CLI + pre-flight checklist + structured log filtering + halt-code priority index) is the correct target after pre-flight fixed. Live Mainnet = S12.

Q2 (pre-flight gap bundle vs separate sprint): CONFIRM — bundle within S11. test_risk_flow.py + _cmd_run DI wiring + WFA CLI = prerequisite for ANY live or operator use. ~1-2 days work. Bundling as S11 P0 before A scope tasks is correct sequencing.

Q3 (A scope definition — 4 deliverables): REVISE — scope is correct BUT add explicit scope exclusion: "monitoring" means CLI monitor subcommand + structured log grep templates, NOT a web UI or external alerting. The 4-deliverable list is right. One refinement: halt priority index should be built INTO halt-recovery.md as a new section (not a separate file), preserving single source of truth.

Q4 (F scope — demo trading params): CONFIRM with caution flag. Bybit demo trading = correct venue. 48h = correct duration. BUT: verify demo trading reconcile semantics are identical to Mainnet before enabling. The _cmd_run wiring in Q2 is prerequisite — cannot run F without it. Defer F to S12 per Q1.

Q5 (DSR calibration timing): CONFIRM — defer. N too small from any short demo run. Need 50+ live trades. S15+ realistic.

Q6 (test_risk_flow.py fix scope): CONFIRM — inline fixture fix only. Read original test intent from commit 5b872a6, add hmac_key="test_key_min_32_chars_for_audit_h2_compliance" (32+ chars per OverrideStore min_length validation in config.py). Audit for OTHER drift in that test file before calling done.

Q7 (reviewer strategy): CONFIRM — per-scope reviewers. A scope: trading-logic (halt semantics) + python (CLI). Pre-flight: python + data-integrity. architecture-reviewer warranted for _cmd_run DI wiring (cross-module DI pattern = architecture-reviewer trigger per llm-wiki/CLAUDE.md trigger cascade).

**Critical cross-cutting:** _cmd_run DI wiring is the true S11 bottleneck. It requires architecture-reviewer (cross-module DI + concurrency model) and trading-logic-reviewer (bootstrap sequencing per ADR 0021). Estimate effort before committing to A scope task count.

**S12 scope:** F (Live demo Mainnet 48h) = S12 after A complete.
