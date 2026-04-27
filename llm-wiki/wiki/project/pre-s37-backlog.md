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
