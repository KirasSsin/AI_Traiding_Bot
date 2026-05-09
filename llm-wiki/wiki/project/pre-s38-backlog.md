---
title: Pre-S38 Backlog — v0.7+ Direction Consilium ROUND 6 BINDING
type: backlog
tags: [pre-sprint, sprint-38, v07-direction, consilium-round-6, binding, delta-activation, ru]
created: 2026-04-27
updated: 2026-04-27
status: active
sources:
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - project/decisions/0057-sprint-37-carry-overs-hardening.md
  - project/sprints/sprint-37-carry-overs-hardening.md
  - project/components/delta-activation-playbook.md
---

# Pre-S38 Backlog — v0.7+ Direction Consilium ROUND 6

## Контекст

Post-S37 ship (v0.1.0-alpha.37). δ TESTNET production-ready (S36 wired + S37 hardened security). Operator playbook ready. 6 critical carry-overs CLOSED.

3-agent ROUND 6 консилиум на δ activate timing + S38 parallel scope.

## ROUND 6 verdicts (3 agents parallel)

| Q | trader R1 | trading-logic R1 | quant-stats R1 | Final |
|---|-----------|------------------|----------------|-------|
| Q1 δ activate timing | **CONFIRM (a)** | **CONFIRM (a)** | **CONFIRM (a)** | ✅ **(a) δ activate now** |
| Q2 monitoring cadence | REVISE — weekly + T+4h gate | CONFIRM weekly + halt-triggered immediate | Weekly operational + monthly statistical | Weekly per playbook + halt-triggered immediate review + T+4h smoke check + monthly statistical (compute_dsr) |
| Q3 S38 parallel scope | CONFIRM Item #7 + #6/#9 docs (DI only) | CONFIRM (b) docs + Item #7 (smoke-start gate) | YES Items 6+9 + pnl_quote→pnl_pct HIGH | EXPANDED: Item #7 + #6 + #9 + pnl_quote fix + bybit-api-reviewer + tamper handling verify |
| Q4 operator pre-activation | CONFIRM playbook + Item 10 (stale activation_ts) | REVISE — add 3 gates (API key + WAL + bootstrap order) | Adequate + UNDERPOWERED annotation | EXPANDED checklist (5 NEW gates + UNDERPOWERED expected note) |

**NO ROUND 2 needed** — Q1 unanimous CONSENSUS, Q2-Q4 amendment-style REVISEs (same option, additions).

## NEW critical findings (cross-cutting)

### F1 (trader CC1) — VERIFIED CLOSED S37 T3
"manager.py tamper handling missing" → trader concern **INVALID**. S37 T3 implementer wrapped `state_repo.get_signed` в `try/except ValueError` at `src/runtime/manager.py:166-177` per ADR 0057 SD-4. Tamper raises → halt fail-closed (HALT_UNKNOWN_SYMBOL) + bot exit. Trader missed implementation detail.

### F2 (quant-stats HIGH) — `pnl_quote` vs `pnl_pct` в `compute_live_sharpe()`
`src/analytics/live_trade_reporter.py:62`:
```python
returns = [float(r.pnl_quote) for r in records]  # absolute P&L (quote currency)
```

Sharpe formula requires dimensionless returns. If Kelly sizing varies position sizes → trades с larger sizes dominate mean/std ratio artificially. `dsr.py` correctly uses `pnl_pct` via `compute_returns()`. **Live reporter inconsistent с DSR own return extraction.** Must fix BEFORE 12mo review uses calibration ratio.

### F3 (trading-logic C1) — bybit-api-reviewer first invocation overdue
Reviewer agent dormant since S30. Never invoked в production-runtime context. δ TESTNET activation = first real WS private + REST order placement under production code path. Recommend invocation против `src/execution/coordinator.py` + `src/execution/bybit/` BEFORE first order fires.

### F4 (trading-logic Gate 1) — Bybit TESTNET API key scope verification
Pre-activation manual check: `GET /v5/account/info` + confirm `POST /v5/order/create` reachable. Read-only key → `retCode=10003` permission denied → unhandled error path. Operator manual check, not sprint task.

### F5 (trader Item 10) — stale activation_ts check
Operator должен verify SQLite `state` table has no stale `runtime:halt_gate:activation_ts` row from prior aborted activation (different HMAC key version → tamper halt on first tick).

### F6 (quant-stats playbook) — "UNDERPOWERED expected, не failure" annotation
12mo TESTNET expected DSR_UNDERPOWERED throughout (n=13 < 30 GATE_ELIGIBLE). Operator risk: misread as failure signal → premature shutdown. Playbook annotation needed.

### F7 (trading-logic Gate 2+3) — WAL disk space + bootstrap ordering doc
- Gate 2: confirm disk > 1GB before activation (halt_log accumulates rows)
- Gate 3: document bootstrap → ws_consumer.start ordering invariant

### F8 (quant-stats LOW) — block_size constant inconsistency
`_MC_BLOCK_SIZE=20` (live_trade_reporter.py) vs `block_size=30` default (mc_permutation.py). Both within ADR 0015 [20, 50] range. Maintenance hygiene only — caller-supplied wins.

## S38 task structure (consilium-merged 7 tasks)

| T | Task | Track | LoC est |
|---|------|-------|---------|
| T1 | ADR 0058 — S38 carry-overs + ADR 0056 amendment 2 (Sharpe semantics + pnl_quote→pnl_pct) | docs | ~120 lines |
| T2 | **F2 quant HIGH fix**: `compute_live_sharpe` returns = `pnl_pct` (NOT `pnl_quote`) + test verifies | code | ~30 LoC + 3 tests |
| T3 | **F3 bybit-api-reviewer** first invocation против `src/execution/coordinator.py` + `src/execution/bybit/` | review | doc deliverable |
| T4 | Item #7 RiskSharedDeps Demeter refactor (DI wiring ONLY, NOT touch _tick body) + smoke-start gate | code | ~80 LoC + 4 tests |
| T5 | Items #6 + #9 documentation amendments (months_since truncation + Sharpe semantics) | docs | ~50 lines |
| T6 | Playbook amendments — F4 (API key scope) + F5 (stale activation_ts check) + F6 (UNDERPOWERED expected) + F7 (WAL/bootstrap) + halt-triggered immediate review + monthly statistical | docs | ~60 lines |
| T7 | sprint-38 + counts (57→58 ADRs / 41→42 sprints / 48→48 components — no NEW component) + sync | wiki | wiki sync |

**Total: ~110 LoC + 7 NEW tests + 1 ADR + 1 amendment + multiple doc updates. Forecast ~6-8h.**

Items deferred к S39+:
- F8 block_size constant unification (low priority)
- 12mo MAINNET-promotion ADR (per ADR 0055 SD-8 timing — quant recommends draft at n=10, not pre-data)
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios (accumulate naturally as live edge cases)

## S38 critical pre-commitments (BINDING per ROUND 6 consilium)

1. **δ activate timing**: operator decides — can activate **NOW** (parallel с S38) OR after S38 ship (~6-8h delay)
2. **F2 pnl_quote → pnl_pct**: MUST fix before 12mo review uses calibration ratio
3. **Item #7 RiskSharedDeps**: DI wiring ONLY, NOT touch `_tick()` body OR `HaltGate.evaluate()`
4. **Smoke-start gate**: Item #7 PR must pass `pytest 897 unit + 33 integration` + TESTNET smoke-start verification before merge
5. **F3 bybit-api-reviewer**: invocation BEFORE first real order fires (operator timing)
6. **Playbook amendments T6**: include 5 NEW gates (F4-F7 + UNDERPOWERED + halt-triggered)
7. **No 12mo MAINNET-promotion ADR**: defer к n=10 milestone (anti-snooping per quant)

## Operator action paths (post-consilium)

### Path A — δ activate immediately + S38 parallel (RECOMMENDED per consilium)
1. Operator sets `S35_DEMO_ACTIVE=true` per playbook 5-step procedure
2. S38 sprint runs в parallel (T1-T7) — code touches NOT live runtime tick path
3. F2 pnl_quote→pnl_pct fix shipped before 12mo review milestone (no urgency immediate)
4. F3 bybit-api-reviewer dispatched within first week (before first real order ideally)

### Path B — S38 ship first, δ activate post-ship
1. S38 sprint completes T1-T7 (~6-8h)
2. Operator sets `S35_DEMO_ACTIVE=true` после tag v0.1.0-alpha.38
3. Adds ~2-4 weeks delay (S38 cycle) — 1 trade sample lost (S22 baseline)

**3 agents prefer Path A (δ activate now, S38 parallel) — quant explicit "no quant case for delay".**

## Carry-overs к S39+

- F8 block_size constant unification
- 12mo MAINNET-promotion ADR (draft trigger: n=10 first non-NaN DSR)
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios (accumulate edge cases)
- bybit-api-reviewer post-activation real-world findings (если any)

## Related

- ADR 0055 (S36 δ activation)
- ADR 0056 (S36 DSR amendment + S37 amendment)
- ADR 0057 (S37 carry-overs hardening)
- ADR 0058 (S38 follow-up — этот sprint, paired ADR 0056 amendment 2)
- pre-s35-backlog.md (ROUND 3 binding)
- pre-s36-backlog.md (ROUND 4 binding)
- pre-s37-backlog.md (ROUND 5 binding)
- delta-activation-playbook.md (operator procedure)
- Bailey & López de Prado 2014 (DSR + pre-registration discipline)
- [[decisions/0058-sprint-38-delta-parallel-hardening]] — Sprint 38 ADR
- [[sprints/sprint-38-delta-parallel-hardening]] — Sprint 38 page
