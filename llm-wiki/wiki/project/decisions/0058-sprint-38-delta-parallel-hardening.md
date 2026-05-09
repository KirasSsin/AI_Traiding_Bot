---
title: ADR 0058 — Sprint 38 δ Parallel Hardening (F2 quant + bybit-api-reviewer + Item #7 + playbook amendments)
type: decision
tags: [adr, sprint-38, delta-parallel, pnl-pct-fix, bybit-api-review, demeter-refactor, playbook-amendments]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - project/decisions/0057-sprint-37-carry-overs-hardening.md
  - project/pre-s38-backlog.md
---

# ADR 0058 — Sprint 38 δ Parallel Hardening

## Status

Accepted (2026-04-27) — implemented в S38 (`feature/sprint-38-delta-parallel-hardening` → tag `v0.1.0-alpha.38`). Paired ADR 0056 amendment 2 (Sharpe pnl_pct semantics, same sprint).

## Context

Post-S37 ROUND 6 consilium (3 agents — trader-expert + trading-logic-reviewer + quant-stats-reviewer) UNANIMOUS Q1 CONSENSUS на (a) δ activate now + S38 sprint runs в parallel.

ROUND 6 surfaced 8 NEW findings (F1-F8) post-S37 production-readiness review. F1 verified closed, F8 deferred. F2-F7 + Item #7 + Items #6/#9 form S38 scope.

Operator approved Path A (δ activate immediately + S38 parallel).

## Decision (5 sub-decisions)

### SD-1 — F2 quant HIGH fix: compute_live_sharpe returns = pnl_pct

`src/analytics/live_trade_reporter.py:62`:

| Variant | Source extraction | Issue |
|---------|-------------------|-------|
| **S37 ORIGINAL** | `[float(r.pnl_quote) for r in records]` | Bias if Kelly sizing varies position sizes — large positions dominate mean/std ratio |
| **S38 AMENDED** | `[float(r.pnl_pct) for r in records]` | Dimensionless returns commensurable across trade sizes |

Rationale (quant-stats-reviewer ROUND 6 F2 HIGH): Sharpe formula `(mean/std) * sqrt(N)` requires returns of comparable magnitude. `pnl_quote` scales с position size; `pnl_pct` normalizes. `dsr.py compute_returns()` correctly uses `pnl_pct`.

MUST land before 12mo TESTNET review uses calibration ratio (live_Sharpe / 2.96).

### SD-2 — F3 bybit-api-reviewer first invocation

bybit-api-reviewer agent dormant since S30 (created для exactly этого moment). δ TESTNET activation = first production-runtime invocation of WS private + REST order placement code path.

S38 T3 dispatches reviewer против:
- `src/execution/coordinator.py`
- `src/execution/bybit/*`

6-axis review: rate limits / order params / WS schema / retCode handling / pagination / HMAC sign.

Output persisted в `llm-wiki/wiki/queries/2026-04-27-bybit-api-reviewer-first-invocation.md`. Severity-triaged findings:
- BLOCKER → S38 hotfix OR S38a sprint
- HIGH → S38 OR pre-s39-backlog
- MEDIUM/LOW → pre-s39-backlog

### SD-3 — Item #7 RiskSharedDeps Demeter refactor

`RuntimeManager` accesses `risk_manager.equity_tracker / trade_repo / state_repo` properties — Law of Demeter violation (S37 T4 architecture-reviewer MEDIUM).

S38 T4 introduces `RiskSharedDeps` NamedTuple bundle:

```python
class RiskSharedDeps(NamedTuple):
    equity_tracker: EquityTracker
    trade_repo: TradeHistoryRepository
    state_repo: StateRepository
```

`RiskManager.shared_deps` property exposes bundle. `RuntimeManager` accepts `shared_deps=` kwarg (preferred path) OR individual kwargs (backward-compat).

**CRITICAL CONSTRAINT** (per ROUND 6 trader-expert + trading-logic-reviewer): DI wiring ONLY — NOT touch `_tick()` body OR `HaltGate.evaluate()`. Smoke-start gate before merge (pytest 897+33 + TESTNET smoke check).

### SD-4 — Playbook amendments (5 NEW gates + UNDERPOWERED + halt-triggered)

`delta-activation-playbook.md` extended:

**Pre-activation gates (F4-F7):**
- F4: Bybit TESTNET API key scope verification (`GET /v5/account/info` + Order write permission)
- F5: No stale `runtime:halt_gate:activation_ts` row check (different HMAC key version → tamper halt)
- F7 Gate 2: SQLite WAL mode + > 1GB disk space confirmation
- F7 Gate 3: Bootstrap → ws_consumer.start ordering invariant doc

**Monitoring section additions:**
- "DSR UNDERPOWERED expected for entire 12mo window" annotation (per quant — small-n regime, NOT failure signal)
- "Halt-triggered immediate review" branch (weekend halt blind spot mitigation)

### SD-5 — 12mo MAINNET-promotion ADR DEFERRED к n=10 milestone

Per quant-stats-reviewer ROUND 6 anti-snooping discipline:
> "Drafting the full ADR now would constitute pre-snooping on a zero-sample distribution. Earliest statistically defensible moment к draft MAINNET promotion criteria is when generate_live_report() can produce non-NaN DSR (n≥10, UNDERPOWERED)."

S38 does NOT draft 12mo MAINNET-promotion ADR. Trigger: first n=10 live trade milestone (likely ~9mo at S22 baseline 13/year). S39+ ADR draft + thresholds locked BEFORE 12mo review date.

## Consequences

### Positive
- F2 fix = correct Sharpe semantics (Kelly sizing variance no longer biases live calibration)
- F3 bybit-api-reviewer first invocation closes long-standing dormant agent gap
- Item #7 Demeter refactor = clean DI architecture (foundation для S39+ scope expansions)
- Playbook amendments = comprehensive operator pre-flight + monitoring guide
- Anti-snooping discipline preserved (12mo MAINNET ADR deferred к data milestone)

### Negative
- F2 fix changes live_sharpe magnitude (pnl_pct typically 0.001-0.05 range vs pnl_quote 50-500 range). Existing test fixtures may need numeric assertion updates.
- Item #7 backward-compat шим period = code complexity (dual DI paths). Cleanup S39+ когда all callers migrated.
- bybit-api-reviewer findings unknown until run — S38 scope могут expand if BLOCKER discovered.

### Neutral
- No FSM canonical count changes (states=16, events=30, transitions=74, reason_codes=50 unchanged)
- δ TESTNET runs production tick path в parallel — S38 development branch isolated
- Playbook docs grow ~60 lines

## Implementation

Per S38 plan (`plans/2026-04-27-sprint-38-delta-parallel-hardening.md`):
- T1 (this commit): ADR 0058 + ADR 0056 amendment 2 paired
- T2: F2 quant HIGH fix (pnl_pct extraction)
- T3: F3 bybit-api-reviewer first invocation
- T4: Item #7 RiskSharedDeps Demeter refactor (DI ONLY + smoke-start gate)
- T5: Items #6 + #9 documentation amendments
- T6: Playbook amendments (5 NEW gates + UNDERPOWERED + halt-triggered)
- T7: Wiki sync + ship

## Follow-ups

**S39+:**
- F8 block_size constant unification (quant LOW)
- 12mo MAINNET-promotion ADR (draft trigger: n=10 first non-NaN DSR)
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios
- bybit-api-reviewer post-activation real-world findings (if any)
- Item #7 backward-compat shim cleanup (когда all callers migrated к shared_deps)

## Related

- ADR 0050-0054 (S33-S35 lineage)
- ADR 0055 (S36 δ activation)
- ADR 0056 (S36 DSR amendment + S37 amendment + S38 amendment 2 paired)
- ADR 0057 (S37 carry-overs hardening)
- ADR 0058 (S38 δ parallel hardening — этот ADR)
- pre-s35-backlog.md / pre-s36-backlog.md / pre-s37-backlog.md / pre-s38-backlog.md
- delta-activation-playbook.md (operator procedure — extended T6)
- Bailey & López de Prado 2014 (DSR + pre-registration discipline)
- Hudson & Urquhart 2021 (small-n statistical reality)
- [[../sprints/sprint-38-delta-parallel-hardening]] — спринт delivery record
