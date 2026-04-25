---
title: Pre-S11 backlog — brainstorm verdicts trail
type: backlog
tags: [sprint-11, brainstorm, phase-2, verdicts, trader-expert, operator-readiness]
created: 2026-04-25
updated: 2026-04-25
status: open
sources:
  - project/decisions/0016-binance-spot-testnet-mvp.md
  - project/decisions/0022-sprint-8a-live-runtime.md
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
  - project/runbooks/halt-recovery.md
---

# Pre-S11 backlog — PHASE 2 brainstorming trail

## S11 scope (maintainer-locked + trader-confirmed)

**A-first = Operator-readiness sprint** (per Q1 trader CONFIRM). F (Live demo Mainnet) deferred к S12.

S11 deliverables = pre-flight gaps (P0) + operator infrastructure (4 sub-deliverables):

**P0 pre-flight (blocks all live work):**
1. test_risk_flow.py fix (OverrideStore hmac_key kwarg drift since S4)
2. `_cmd_run` DI wiring — close S8a T20 STUB (Coordinator + Reconciler + RuntimeManager + Strategy + RiskManager + WS consumer)
3. WFA CLI subcommand — `python -m src wfa --start ... --end ...`

**Operator-readiness (A scope):**
4. halt-recovery.md priority matrix — extend Quick Reference Table с "On-call escalation chain" column + new "Priority matrix" section на top (Q3 trader REVISE)
5. Log aggregation grep templates — JSON structlog filtering recipes (`runtime.bar_tick`, `data_quality.*`, `halt_log` SQL view)
6. `_cmd_monitor` CLI subcommand — read-only tail FSM state + halt_reason + recent trades + open positions
7. Pre-flight checklist — `wiki/runbooks/pre-flight.md` operator checklist before live start

## S11 PHASE 2 brainstorming verdicts

### Q1 — Sprint scope ordering (F vs A first)

**ROUND 1 verdict:** CONFIRM (trader-expert)

**Decision:** S11 = A (Operator-readiness). F deferred к S12.

**Trader rationale:**
- S9 roadmap aspirational, не binding — predates discovery `_cmd_run` is hard STUB (returns exit 1, prints error)
- Live Mainnet требует bot startable end-to-end → blocked by `_cmd_run` wiring
- ADR 0016 explicit: testnet MVP first, Mainnet после Phase G testnet probes pass
- A-first = architecturally correct sequencing

**ROUND 2:** N/A (CONFIRM).

---

### Q2 — Pre-flight gap closure (bundle vs separate sprint)

**ROUND 1 verdict:** CONFIRM

**Decision:** Bundle as S11 P0 (3 tasks: test_risk_flow + _cmd_run + WFA CLI). Complete BEFORE A-scope deliverables begin.

**Risk noted:** _cmd_run DI wiring complexity may surprise. Plan author MUST do DI feasibility read-pass.

---

### Q3 — A scope: 4 deliverables (halt dashboard + log + monitor CLI + pre-flight)

**ROUND 1 verdict:** REVISE (trader-expert)

**Maintainer original recommendation:** 4 deliverables including separate "halt-recovery dashboard" file.

**Trader chosen option:** Accept 4 deliverables BUT restructure deliverable 1: integrate halt priority matrix INTO existing `halt-recovery.md` (NOT separate file). Add "Priority matrix" section at top + extend Quick Reference Table с "On-call escalation chain" column.

**Trader rationale:**
- `halt-recovery.md` уже имеет Quick Reference Table (19 codes, 5 groups, lines 40-61) с severity tiers
- Separate "dashboard" file = duplicate source of truth, drift risk
- ~20-line wiki edit vs new component page
- Single source of truth principle

**ROUND 2:** NOT triggered. Maintainer accepts (drift prevention rationale technically stronger).

**Final accepted decision:** 4 deliverables:
1. `halt-recovery.md` extension (Priority matrix section + escalation column)
2. Log aggregation grep templates → new wiki page `wiki/runbooks/log-grep-templates.md`
3. `_cmd_monitor` CLI subcommand
4. Pre-flight checklist → new wiki page `wiki/runbooks/pre-flight.md`

---

### Q4 — F scope (deferred к S12, params validated)

**ROUND 1 verdict:** CONFIRM (deferred к S12)

**Decision:** When S12 F runs — Bybit demo trading + 48h + $1000 virtual. Real Mainnet money requires `live_trading=True + testnet=False + trading_enabled=True` (3-layer guard per `config.py:158-163`).

**Note для S12 brainstorm:** Add Q "verify Bybit demo trading reconcile event semantics identical к Mainnet" — demo может have different reconcile semantics.

---

### Q5 — DSR empirical calibration timing

**ROUND 1 verdict:** CONFIRM

**Decision:** Defer threshold calibration к S15+ (need ≥30 closed trades, ~50 days @ 1-2 trades/day). Document SPRINT_STATE: "TBD post-empirical fold data, target S15+".

---

### Q6 — test_risk_flow.py fix scope

**ROUND 1 verdict:** CONFIRM

**Decision:** 1-test fix + audit для other S4-era drift. Fixture: `OverrideStore(path=..., hmac_key="test_key_min_32_chars_for_audit_h2_compliance")` (44 chars satisfies 32+ Field min_length).

**Audit:** Check для ADR 0018 security audit drift (HMAC scope, path defaults, override semantics changes S5-S7).

---

### Q7 — Reviewer strategy

**ROUND 1 verdict:** CONFIRM с addition

**Decision:**
- A scope tasks: trading-logic-reviewer + python-reviewer
- Pre-flight `_cmd_run`: **architecture-reviewer MANDATORY** + python-reviewer (per CLAUDE.md trigger cascade — DI pattern + component decomposition + concurrency implications)
- test_risk_flow.py fix: python-reviewer
- WFA CLI: python-reviewer (mostly argparse + delegation)

---

## Cross-cutting concerns (apply в plan)

**C1 — `_cmd_run` wiring real risk item:**
- DI graph: `Settings` → `BybitAdapter` → `Coordinator(adapter, state_repo, reconciler, risk_manager)` → `RuntimeManager(coordinator, bar_source, strategy)`
- Each constructor evolved independently since S8a T20 deferral
- Plan author MUST do DI feasibility read-pass (`coordinator.py` + `runtime/manager.py` + `bar_source.py`) BEFORE locking task count
- If signatures don't match wiring intent → mini-ADR, not just task
- architecture-reviewer mandatory regardless of LoC

**C2 — `_cmd_monitor` strictly read-only:**
- SQL write path в monitoring command running concurrently с live bot → SQLite WAL contention risk
- Implementation: pure SELECT + structlog tail
- NO state mutations (defensive)

**C3 — WFA CLI sequence:**
- WFA CLI distinct from operator-readiness scope
- Useful для S12 F empirical baseline
- Bundle as P0 task НО не block A scope from starting parallel

## Escalation items для user

None. All engineering scope.

## Transition

PHASE 2 complete. SPRINT_STATE → phase=3-planning. Next: PHASE 3 plan write (`superpowers:writing-plans` skill) → trace map + bite-sized TDD tasks. **Required pre-plan step:** DI feasibility read-pass per C1.

## Related

- [[decisions/0016-binance-spot-testnet-mvp]] — testnet MVP gating + Phase G mention
- [[decisions/0022-sprint-8a-live-runtime]] — RuntimeManager origin + T20 STUB deferral
- [[decisions/0025-sprint-10-wfa-dsr-mc]] — WFA + DSR (S10 ship)
- [[runbooks/halt-recovery]] — 19 halt codes, will be extended с Priority matrix
- [[architecture/development-workflow]] — PHASE 2 binding protocol
