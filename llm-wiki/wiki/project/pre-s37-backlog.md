---
title: Pre-S37 Backlog — S36 carry-overs
type: backlog
tags: [backlog, sprint-37, carry-overs, halt-gate, dsr, security, ru]
created: 2026-04-27
updated: 2026-04-27
status: open
sources:
  - project/sprints/sprint-36-delta-activation.md
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
---

# Pre-S37 Backlog — S36 Carry-overs

Этот файл перечисляет carry-over items из Sprint 36 (T4 + T6 reviewer findings + δ activation operator items). Закрывается → удаляется в S37.

## Source

S36 ROUND 4 consilium binding completed. 19 commits / 63 NEW tests / pytest 871+33 / mypy 0 / canonical 16/30/74/49.

Carry-overs не блокировали S36 ship — deferred per reviewer severity assessment. 2 security HIGH items require S37 attention BEFORE any production deployment consideration.

## Items

### Security (HIGH — review before any MAINNET consideration)

**Item 1: Symbol whitelist + startup banner**
- Source: T2 security-auditor reviewer, HIGH
- Description: When `s35_demo_active=True`, bot should display startup banner listing approved symbols and validate incoming trade symbols against explicit whitelist. Currently warning + skip behavior.
- File: `src/runtime/manager.py` + `src/platform/config.py`
- Action: Add `DEMO_APPROVED_SYMBOLS: list[str]` setting + startup validation + operator-visible banner

**Item 2: Symbol fail-closed semantic**
- Source: T4 security-auditor reviewer, HIGH
- Description: `_check_halt_gate()` currently warns and skips on unknown symbol. Should fail-closed (halt) on unrecognized symbol to prevent silent bypass.
- File: `src/runtime/manager.py`
- Action: Change warn+skip → halt с HALT_S36_CONSECUTIVE_LOSSES or new HALT_UNKNOWN_SYMBOL

**Item 3: activation_ts integrity hardening**
- Source: T4 security-auditor reviewer, HIGH
- Description: SQLite `runtime:halt_gate:activation_ts` has no tamper-detection. Rollback of activation_ts would reset multiday HWM window.
- File: `src/execution/state_repo.py`
- Action: Add config_hash or HMAC signature to activation_ts record per ADR 0018 pattern

### Trading Logic (MEDIUM — address in S37)

**Item 4: Clock injection в `_check_halt_gate`**
- Source: T4 trading-logic-reviewer, C2
- Description: `_check_halt_gate()` uses `datetime.now(UTC)` wall-clock directly — non-deterministic в property tests. Hard to test time-based scenarios (months_since_last_trade).
- File: `src/runtime/manager.py`
- Action: Inject `clock: Callable[[], datetime]` parameter (default=datetime.now) per S8a clock pattern

**Item 5: coordinator.symbol public property**
- Source: T4 trading-logic-reviewer, C3
- Description: `_check_halt_gate()` accesses `getattr(self._coordinator, "_symbol", None)` — private attribute leak. Should use public property.
- File: `src/execution/coordinator.py` + `src/runtime/manager.py`
- Action: Add `Coordinator.symbol` public property + update wire-up call

**Item 6: months_since integer truncation documented**
- Source: T4 trading-logic-reviewer, C4
- Description: `months_since = (now - last_trade_ts).days // 30` uses integer truncation (29 days = 0 months). ADR 0055 SD-3 silent assumption.
- File: ADR 0055 or new ADR
- Action: Document truncation behavior explicitly в ADR 0055 amendment or S37 ADR. Confirm operator intends truncation vs rounding.

### Architecture (LOW — S37+ refactor)

**Item 7: RiskSharedDeps refactor**
- Source: T4 architecture-reviewer, MEDIUM
- Description: RuntimeManager accesses `risk_manager.equity_tracker / trade_repo / state_repo` properties directly — Law of Demeter violation. Should use shared bundle object.
- File: `src/risk/manager.py` + `src/runtime/manager.py`
- Action: Introduce `RiskSharedDeps` dataclass or `SharedRiskInfra` bundle. Pass as single DI arg.

### Quant-Stats (LOW — test coverage gaps)

**Item 8: DSR boundary tests n=10 + n=30**
- Source: T6 quant-stats-reviewer, C2
- Description: ADR 0056 defines thresholds at n=10 (INSUFFICIENT_TRADES boundary) and n=30 (GATE_ELIGIBLE boundary). Off-by-one tests missing.
- File: `tests/unit/test_dsr_status_thresholds.py`
- Action: Add parametrized tests: n=9 → INSUFFICIENT, n=10 → UNDERPOWERED, n=29 → UNDERPOWERED, n=30 → GATE_ELIGIBLE

**Item 9: trial_mean_fold_oos_sharpe vs pooled trade-level Sharpe**
- Source: T6 quant-stats-reviewer, C3
- Description: S36 introduced `trial_mean_fold_oos_sharpe` (mean of WFA fold OOS Sharpes) vs live reporter's per-trade annualized Sharpe. Semantic distinction not formally documented in ADR.
- File: ADR 0056 or new DSR ADR amendment
- Action: Add section "Sharpe computation semantics" distinguishing fold-level vs trade-level vs cross-trial

### Operational (LOW — extended test scenarios)

**Item 10: DD_MULTIDAY + NO_TRADE_TIMEOUT extended scenarios**
- Source: T4 integration tests, 1 test each currently
- Description: DD_MULTIDAY and NO_TRADE_TIMEOUT each have 1 integration test (happy path trigger). Additional edge cases not covered: partial DD (below threshold), borderline timeout (29 days vs 30 days).
- File: `tests/integration/test_halt_gate_wireup.py`
- Action: Add 2-3 parametrized tests per trigger type covering boundary conditions

## ADR 0055 SD-8: MAINNET promotion criteria

Per ADR 0055 SD-8, MAINNET promotion criteria are DEFERRED к S37+. Items that gate MAINNET consideration:
- Security Items 1-3 above RESOLVED
- n >= 50 PASS criterion met (ADR 0055 SD-1 hybrid option H)
- 12 month TESTNET operational period completed
- Operator acknowledgment template per ADR 0052 format

**Default behavior:** `s35_demo_active=False` (TESTNET bypass). Operator action required: set `S35_DEMO_ACTIVE=true` в .env и restart.

## Priority для S37 brainstorm

Recommended priority order per risk:
1. Security Items 1-3 (before any MAINNET discussion)
2. Quant Item 8 (boundary tests — cheap, prevents future ADR drift)
3. Trading-logic Items 4-5 (clock injection + public property — clean code)
4. Architecture Item 7 (Demeter refactor — medium effort)
5. Items 6, 9, 10 (documentation + extended tests — low urgency)

## Related

- [[sprints/sprint-36-delta-activation]] — source sprint
- [[decisions/0055-sprint-36-delta-activation]] — ADR 0055 SD-8 MAINNET deferral
- [[decisions/0056-sprint-36-dsr-sigma-sr-amendment]] — ADR 0056 DSR thresholds
- [[components/halt-gate-wireup]] — primary carry-over source
- [[components/live-trade-reporter]] — quant carry-overs source

---

## ROUND 5 Consilium BINDING (S37 PHASE 2 brainstorm)

3-agent consilium (trader-expert + trading-logic-reviewer + quant-stats-reviewer) parallel ROUND 1 → CONSENSUS, no ROUND 2 needed.

### Verdict table

| Q | Question | Vote | Final |
|---|----------|------|-------|
| Q1 | v0.7+ ordering | 3× CONFIRM (c) | **(c) S37 carry-overs sprint first** |
| Q2 | S37 scope | 3× EXPAND | **6+1+amendments expanded scope** |
| Q3 | δ activate timing | 3× CONFIRM immediate | **Immediately post-S37 ship** |
| Q4 | Operator playbook | 3× CONFIRM | **Dedicated page** wiki/project/components/delta-activation-playbook.md |

### Cross-cutting EXPAND (Q2)

Original maintainer: 6 items (security 1-3 + trading-logic 4-5 + quant 8). Consilium expanded:

1. **NEW ReasonCode HALT_UNKNOWN_SYMBOL** (trader + trading-logic CONSENSUS) — reusing existing code destroys halt_log attribution. Canonical 49 → **50**.
2. **Calibration baseline amendment** (quant) — `S22_SYNTHETIC_SHARPE = 6.17` (extreme T1 aggregate) → use mean fold Sharpe = 2.96 (more conservative). Update `src/analytics/live_trade_reporter.py:28`.
3. **ADR 0056 amendment** (quant C3) — document trial_mean_fold_oos_sharpe vs pooled trade-level Sharpe semantic distinction.

### S37 task structure (consilium-merged 8 tasks)

| T | Task | Domain | LoC est |
|---|------|--------|---------|
| T1 | ADR 0057 — S37 carry-overs sprint scope + ADR 0056 amendment (calibration baseline + Sharpe semantics doc) | docs anti-snooping | ~150 lines |
| T2 | Security #1+#2 — symbol whitelist + fail-closed (HALT_UNKNOWN_SYMBOL ReasonCode +1, 49→50) + startup banner | code | ~150 LoC + 5 tests |
| T3 | Security #3 — activation_ts integrity HMAC signature per ADR 0018 pattern | code | ~80 LoC + 4 tests |
| T4 | Trading-logic #4 — clock injection в `_check_halt_gate` (testability per S8a precedent) | code | ~50 LoC + 3 tests |
| T5 | Trading-logic #5 — coordinator.symbol public property (replace `_symbol` private leak) | code | ~30 LoC + 2 tests |
| T6 | Quant #8 — DSR boundary tests n=10 + n=30 (parametrized) | tests | ~30 LoC + 4 tests |
| T7 | Operator playbook — `wiki/project/components/delta-activation-playbook.md` (step-by-step δ activate + DSR status interpretation guide + halt_log monitoring) | docs | ~80 lines |
| T8 | sprint-37 + counts (49→50 reason codes / 56→57 ADRs / 40→41 sprints / 47→48 components) + sync | wiki | wiki sync |

**Total: ~340 LoC + 18 NEW tests + 1 ADR + 1 ADR amendment + 1 component page. Forecast ~8-10h.**

Items 6+7+9+10 deferred к S38+:
- #6 months_since truncation doc (low urgency)
- #7 RiskSharedDeps refactor (medium effort, defer post δ activation feedback)
- #9 trial_mean_fold_oos_sharpe doc (covered partially в T1 ADR amendment)
- #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios (accumulate как regression tests)

### S37 critical pre-commitments BINDING

1. HALT_UNKNOWN_SYMBOL distinct ReasonCode (NOT reuse existing) per audit-log attribution rule
2. Calibration baseline amendment к S22 mean fold Sharpe = 2.96 (more conservative)
3. activation_ts HMAC integrity per ADR 0018 pattern
4. δ activate immediately post-S37 ship (no observation gap)
5. Operator playbook page mandatory (not just ADR references)
6. Items 6+7+9+10 explicitly DEFERRED к S38+ (NOT silently dropped)

### NO ROUND 2 needed

All 3 agents REVISE same direction (EXPAND scope) — convergent enhancement, не disagreement. No REVISE-disagreement triggering iterative justify loop per brainstorm-init Step 5.

### S38 path (post-S37 + δ activation)

- δ TESTNET running, accumulating data
- S38 = architecture refactor (Item #7 RiskSharedDeps Demeter) + extended test coverage (#6, #9, #10)
- S38+ = monitor δ data, prepare 12mo MAINNET-promotion review per ADR 0055 SD-8
