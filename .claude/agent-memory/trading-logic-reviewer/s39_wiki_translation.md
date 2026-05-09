---
name: S39 Wiki Translation Status
description: Language audit of trading wiki pages + component header translation fixes (2026-05-09)
type: project
---

All 13 trading wiki pages under llm-wiki/wiki/trading/ are already fully in Russian.
No translation needed for Task A.

Component pages with English headers fixed (Task B):
- execution-state-machine.md: "Related" → "Связанные", "Concurrency / Lock policy" → "Параллельность / политика блокировок"
- coordinator.md: 11 English headers translated (Definition/Purpose, Public API, Threading lock policy, FSM dispatch invariant, Bootstrap sequencing, Reconcile path, γ Halt persistence, OCO bracket lifecycle, State persistence, Invariants, Related, Open questions, Sources)
- strategy.md: Contract, Entry rule, Exit rule, Invariants, Performance, Related → Russian
- donchian-strategy.md: LOCKED Parameters, Public API, Entry/Exit logic, Known limitations, Related → Russian
- halt-gate.md: Public API, Wiring, Related → Russian
- halt-gate-wireup.md: Wire-up architecture, State persistence, HaltTrigger → ReasonCode mapping, DI surface, Halt resume protocol, Tests, Carry-overs, Related → Russian
- kill-switch-cli.md: Commands, sentinel semantics, Path resolution, Atomic write, File mode, Stale cleanup, RuntimeManager polling, FSM dispatch, Recovery, Why sentinel-file, Tests, Out of scope, Referenced by, Related, Sources → Russian

Reason-codes.md count discrepancy: wiki title says "42" but body counts 45 (correct body count), and ESM page footer says 50 codes (post-S37 with HALT_UNKNOWN_SYMBOL +1, S36 +4, S37 +1 on top of S7 baseline 42). The wiki page title frontmatter says 42 but is stale. The body says 45 and lists 45 correctly for S7 baseline. S36/S37 additions (HALT_S36_* +4, HALT_UNKNOWN_SYMBOL +1) bring total to 50 but are not yet in this wiki page body.

**Why:** IMPORTANT: reason-codes.md wiki page is S7-vintage and was not updated to reflect S36/S37 additions. The ESM footer correctly references 50. This is a wiki sync gap, not a code regression.

**How to apply:** When reviewing reason-codes, trust ESM component page footer (50) and src/risk/reason_codes.py over reason-codes.md wiki page. Flag wiki sync gap when touching either file.
