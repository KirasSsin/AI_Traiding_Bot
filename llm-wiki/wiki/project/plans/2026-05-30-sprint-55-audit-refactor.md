# Sprint 55 — Full-Project Audit + Refactor Implementation Plan

> **For agentic workers:** subagent-driven-development, SEQUENTIAL dispatch per batch (shared-branch parallel = churn, S50/S51 lesson). TDD strict. Per-fix commit. Re-review after.

**Goal:** Fix all 43 adversarially-confirmed defects from the S55 full-project audit (Workflow w1hxvgkoa: 120 agents, 9 dimensions, 2× skeptic-verified each). 2 BLOCKER + 9 HIGH + 15 MEDIUM + 17 LOW.

**Source:** `s55-audit-report.md` (ranked) + `s55-audit-findings-detail.md` (per-finding detail+fix).

**Architecture:** All findings on shipped main (tag alpha.54). Branch `feature/sprint-55-full-audit-refactor`. Fixes grouped into risk-isolated batches; money-path BLOCKERs first, each via TDD RED→GREEN.

---

## Batch 0 — BLOCKERs (money-path, FIRST, opus, sequential)

### TL-01 — live runtime never arms OCO + drops exit signals (BLOCKER)
**Files:** `src/runtime/manager.py:314-358`, `src/execution/coordinator.py:307-312,402,477`.
- Wire entry-fill → `arm_oco(tp,sl,qty)` (LONG_OPEN→OCO_ARMING→OCO_ARMED places TP+SL legs).
- Route FLAT/EXIT signals → `coordinator.flatten(reason)` when LONG_OPEN/OCO_ARMED (manager.py:314 currently drops them).
- Wire `reconcile_arming_ttl` into tick loop.
- TDD: end-to-end test start_bracket→entry-fill→arm_oco places TP+SL; EXIT_FLAT flattens open position. Ref ADR 0020.

### BYBIT-01 — REST vs private-WS connect to DIFFERENT envs (BLOCKER)
**Files:** `src/__main__.py:167`, `src/marketdata/bybit/rest.py:127`, `src/execution/bybit/ws_private.py:76-82`.
- REST → testnet exchange but WS → demo (or vice versa) → order→fill event loop broken (orders on one env, fills never arrive from other).
- Fix: single source-of-truth env/endpoint config; both REST + WS read same `settings.testnet`/demo flag. TDD: assert REST base URL env == WS URL env.

## Batch 1 — HIGH money/execution (opus, sequential)

- **BYBIT-02** emergency flatten attempt-1→2 not idempotent (different orderLinkId) → lost-response double Market Sell. Fix: stable orderLinkId across both attempts (S50 B1 pattern).
- **BYBIT-03** two unrelated BybitAPIError classes → rate-limit-exhaustion + 110072 idempotency escape handler. Fix: unify error class OR catch both.
- **ARCH-02** blocking REST I/O (~15.5s backoff sleep) under nested Coordinator RLock + Reconciler Lock on reconcile path → blocks WS SL-cancel → orphan TP self-fill phantom short. Fix: hoist exchange-fetch OUTSIDE locks (classify is pure), OR bound reconcile retries to 1.
- **TL-02** arm_oco/flatten/reconcile_arming_ttl dead code (= TL-01 confirmation surface; fixed together).

## Batch 2 — HIGH quant/data/security (opus, sequential)

- **QS-1** DSR units mismatch: per-trade candidate Sharpe vs annualized-fold sigma_sr → DSR≈0 false-negative gate (ACTIVE atr_breakout). Fix: align both to same annualization basis. `dsr.py:103,139,150` + callers.
- **DI-01** multi-interval WS gap synthesizes only ONE GAP bar → silent multi-bar hole. Fix: emit one GAP bar per missing interval. `bar_builder.py:53-58,91-109`.
- **DI-02** BarSource.poll() can emit currently-forming (unclosed) bar as is_closed=True → look-ahead live. Fix: drop last in-progress bar. `bar_source.py:66-87`.
- **SEC-S55-01** path traversal: attacker symbol f-string into parquet path, reachable from /api/backtest. Fix: validate symbol against whitelist regex before path join. `src/__main__.py:456`.
- **DASH-01** Kronos RAW_PRETRAIN_LEAKAGE_SUSPECTED renders as failed WFA gate (dispatch checks `=== 'RAW'` only). Fix: add RAW_PRETRAIN_LEAKAGE_SUSPECTED to research-verdict branch. `MetricsTable.tsx:349`, `HistoryTab.tsx`.

## Batch 3 — MEDIUM (sonnet, sequential, grouped)

- **TL-03/TL-04** atr_breakout + volume_breakout streaming exit-priority OPPOSITE to WFA runner (live≠backtest). Fix: align streaming to runner order.
- **ARCH-03** RuntimeManager reads Coordinator._repo private → add public `current_state()` + `step_size` property.
- **DI-03** migration zero-pad inconsistency (FK file runs before referenced table). Fix: rename/renumber (careful — applied migrations).
- **DI-04** Bar model accepts tz-naive datetime. Fix: validator reject naive.
- **DASH-02** MonthlyHeatmap PnL = diff of compounded cumulative % (inflated). Fix: true monthly return.
- **DASH-03** research dispatch bypasses _lock + non-atomic cache write race. Fix: acquire _lock.
- **BYBIT-04** residual flatten orderLinkId=None when bracket_id None. Fix: deterministic fallback id.
- **BYBIT-05** residual flatten qty not step-floored → dust false HALT. Fix: step-floor.
- **TQ-01..06** test-quality: 3 adapter tests load real model / dead skip-guards / no skip-guard / env-assertion pollution / _compute_weights_hash 0 coverage / runner PnL never value-asserted. Fix: skip-guards + value assertions.

## Batch 4 — LOW (sonnet, batched, best-practices)

ARCH-05 (layering inversion __main__ imports), TL-06 (Kronos stateless double-signal), TL-07 (free-form reason strings EMA/MR/donchian), QS-2 (bars_per_year 2190 vs 2191), DI-06+SEC-S55-03+PY-5 (prediction_cache non-atomic write — dedup, one fix), SEC-S55-04 (WS payload %r log redaction), PY-1 (CI ruff threshold 200), PY-2 (config_loader deprecated typing), PY-3 (Wilder _atr dup), PY-4 (root scripts outside CI), TQ-07/08 (kronos win_rate untested + mock drift), DASH-04 (HistoryTab RAW verdict styling), DASH-05 (stale OPTGROUP_ORDER), BYBIT-06 (kline backfill no-progress stall guard).

---

## PHASE 5 gates
pytest GREEN (+ torch-present skip-guards fix the 6 failing) + mypy 0 + reason codes (TL-07 may touch) + frontend lint+tsc+build + ruff.

## PHASE 6 re-review
Re-dispatch affected-dimension reviewers on the diff → confirm fixes + no regressions. Loop until clean.

## PHASE 8 ship
tag v0.1.0-alpha.55.

## Self-Review
- All 43 confirmed → batched B0(2 BLOCKER)/B1(4 HIGH exec)/B2(5 HIGH quant-data-sec-dash)/B3(MEDIUM)/B4(LOW). 12 refuted excluded (see report §6).
- Money-path BLOCKERs first. Sequential dispatch. Each TDD.
- Dedup: DI-06=SEC-S55-03=PY-5 (one prediction_cache atomic-write fix). TL-01=TL-02 (one OCO-wiring fix). PY-5 dup of DI-06.
