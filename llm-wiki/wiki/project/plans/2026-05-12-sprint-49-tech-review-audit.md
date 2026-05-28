# Sprint 49 — Full Tech-Review Audit + Fix Implementation Plan

> **For agentic workers:** subagent-driven-development per batch. TDD strict. Per-fix commit.

**Goal:** Полное тех-ревью всей кодовой базы (9 reviewers, opus) → fix всех BLOCKER/HIGH/MEDIUM → best-practices state → ship.

**Architecture:** 9 параллельных domain reviewers прошли весь src/ (14.5k LOC) + react (4.2k) + tests (21.7k). Findings агрегированы, дедуплицированы, ранжированы. Fixes батчами через implementer-субагентов с TDD.

**Tech Stack:** Python 3.12, FastAPI, pybit V5, Pydantic, React 18 + TS, Vitest, Playwright, pytest + Hypothesis.

---

## Audit summary (9 reviewers, all opus, read-only)

| Reviewer | Verdict | BLOCKER | HIGH |
|---|---|---|---|
| architecture | APPROVE_WITH_CONDITIONS | 0 | FillRecorderAdapter lock, backtest_runner god-object |
| security | (1 BLOCKER) | 1 (.env plaintext — chmod done) | path traversal run_id |
| quant-stats | (clean math) | 0 | T6 OOS/IS semantic, block_bootstrap null |
| trading-logic | (clean invariants) | 0 | free-form reason strings |
| data-integrity | (2 BLOCKER) | 2 (WS gap drop, parquet non-atomic) | state_repo halt order, migrations REAL→TEXT |
| python | APPROVE_WITH_CONCERNS | 0 | blocking async handlers |
| bybit-api | (2 BLOCKER) | 2 (duplicate-order, schema guards) | — |
| test-engineer | (79% cov) | 0 | backtest_runner verdict 32%, resume_cb 0% |
| dashboard | (clean) | 0 | path traversal, no response_model |

**Core verdict:** live execution path single-writer invariant holds, math correct (DSR/MC/Kelly/Sortino numpy-verified), look-ahead 6/6 clean, HMAC override excellent, SQL parametrized, no withdraw path. Debt concentrated в dashboard/backtest offline layer + 5 real code BLOCKERs.

---

## BLOCKER fixes (code)

### Task B1: Bybit duplicate-order prevention
**Files:** `src/execution/coordinator.py` (~349, 496), `src/marketdata/bybit/rest.py` (~67)
- flatten/residual `place_order` calls carry no `orderLinkId` + `_retry_with_backoff` auto-retries on rate-limit codes (170005/170222) → second market Sell if code returned after order landed
- Fix: deterministic `orderLinkId` on ALL placements (idempotency key) + don't auto-retry non-idempotent placement calls (only retry idempotent reads)
- TDD: test retry on placement does NOT double-submit; test orderLinkId present + deterministic

### Task B2: Bybit unguarded schema access
**Files:** `src/marketdata/bybit/rest.py:184` (kline poll), `src/execution/bybit/filters.py:29`
- `["result"]["list"][0]` без length/guard → KeyError/IndexError on schema shift or empty list
- Fix: route through existing `_safe_extract_list` guard (adapter.py already uses it)
- TDD: test empty list → graceful, test missing key → typed error not crash

### Task B3: WS-stream gap detection wiring
**Files:** `src/marketdata/pipeline.py:54`
- pipeline calls `process()` not `process_with_gap_fill()` → WS gaps appended contiguously without `DataQuality.GAP` marker → corrupt indicator windows
- `process_with_gap_fill` + `_synth_gap_bar` already exist + unit-tested, just not wired
- Fix: route pipeline через `process_with_gap_fill`, append synthetic GAP bar
- TDD: test gap in stream → GAP-marked synthetic bar emitted

### Task B4: Atomic Parquet write
**Files:** `src/marketdata/storage.py:65`
- `pq.write_table(table, path)` direct write → crash mid-write = corrupt parquet
- Fix: write `.parquet.tmp` then `os.replace(tmp, path)` (pattern from `__main__.py:277`)
- TDD: test temp-then-rename, test partial write doesn't leave corrupt final

### Task B5: .env secrets (DONE chmod + operator action)
- `chmod 600 .env` DONE. Gitignored confirmed (not in git).
- Operator action: rotate testnet creds (exposed by read) + move `RISK_OVERRIDE_HMAC_KEY` off shared .env. Document, не code.

---

## HIGH fixes

### Task H1: Path traversal run_id validation
**Files:** `src/dashboard/backtest_runner.py:1217-1222` (get_run + 740/806/878)
- user `run_id` concatenated unsanitized into path. run_id always sha256[:16].
- Fix: `re.fullmatch(r"[a-f0-9]{16}", run_id)` else 404
- TDD: test traversal payload rejected, valid hash accepted

### Task H2: FastAPI Pydantic response_model + blocking handlers
**Files:** `src/dashboard/app.py`
- No response_model on /api/* → contract drift; 5 handlers `async def` with blocking sync calls → event-loop starvation
- Fix: add response_model to /api/backtest + /api/runs/{run_id}; convert blocking handlers `async def`→`def` (Starlette auto-threadpool)
- Add Pydantic date-format validation на start/end + sanitize `str(exc)`→`"fetch_failed"` (account_service.py:111)
- TDD: test response schema matches, test invalid date → 422

### Task H3: account_service TTL cache
**Files:** `src/dashboard/account_service.py`
- per-request adapter construction + no rate-limit guard
- Fix: module-level adapter reuse + 5s TTL cache on balance
- TDD: test 2 calls within TTL → 1 Bybit fetch

### Task H4: state_repo halt write-ahead order
**Files:** `src/execution/state_repo.py:129-145`
- halt_log INSERT must precede execution_state UPDATE per ADR 0021 SD-5
- Fix: reorder INSERT above UPDATE (same txn)
- TDD: test audit row written before state change

### Task H5: FillRecorderAdapter thread-safety
**Files:** `src/risk/fill_recorder_adapter.py`
- on_fill_event runs on WS thread, no lock on shared SQLite repos → latent corruption when S13+ insert wires live
- Fix: inject lock OR thread-safe queue drained on main thread
- TDD: test concurrent fill+main write doesn't corrupt

### Task H6: Free-form reason strings → ReasonCode
**Files:** `src/signalgen/strategy.py` (142,155), `mean_reversion_strategy.py` (173,182), `donchian_strategy.py` (118,128), `src/risk/reason_codes.py`
- EMA/meanrev/donchian entry/exit strings not in 56-enum → RiskManager.assess fallback → strategy attribution lost
- Fix: register strings as ReasonCode members (ADR amendment) — preferred over typing Signal.reason (avoids circular dep per S1 incident)
- TDD: test each strategy reason resolves to enum, no fallback

### Task H7: migrations REAL→TEXT money columns
**Files:** new `migrations/00N_money_text.sql`
- orders/fills/positions money cols are REAL (float precision loss) — latent, no writers yet
- Fix: NEW migration redefining as TEXT (do NOT edit 001_initial.sql)
- TDD: test migration applies, money round-trips as Decimal-TEXT

### Task H8: backtest_runner verdict extraction + test
**Files:** `src/dashboard/backtest_runner.py:1019-1048`, new `tests/unit/test_backtest_runner_verdict.py`
- verdict logic at 32% cov, buried in 430-line run_backtest
- Fix: extract `_compute_verdict(metrics, n_trades, dsr_pass)` pure helper + parametrized test (pins T1-T6 + T3 contract per trader-expert verdict)
- TDD: parametrized criterion-status tests

### Task H9: resume_cb unit tests
**Files:** new `tests/unit/test_resume_cb.py`
- `src/risk/resume_cb.py` 0% unit cov (only integration), risk-critical
- Fix: unit tests for resume-eligibility + halt-state transitions
- TDD: test eligible/ineligible resume paths

### Task H10: T3 semantic alignment (BLOCKED on trader-expert verdict)
- Canonical acceptance-criteria.md says ALL T1-T6 gating. S48 MetricsTable split T1/T2/T3/T4/T6 → informational. Conflict.
- trader-expert dispatched → CONFIRM/REVISE binding. Align UI (option A) OR backend (option b/c) per verdict.

---

## MEDIUM fixes

- M1: `final_balance_quote` compound not additive (backtest_runner.py:1142)
- M2: useStrategyContext multi-instance sync via custom event (useStrategyContext.ts:33)
- M3: 8 unjustified `except Exception` → narrow type OR log+`# noqa: BLE001` reason
- M4: block_bootstrap_p_value docstring warning (not edge-null, don't promote to gate)
- M5: trial_oos_sharpe/compute_live_sharpe hardcoded holding (100/12) → derive OR rename
- M6: RunRecord backward-compat load-time `assert len(timestamps)==len(equity_pct)`
- M7: MonthlyHeatmap return math (inter-month gap dropped)
- M8: nan_safe unit test + ReasonCode 39/56 coverage test + register `property` marker

## LOW fixes (best-practices cleanup)

- L1: ruff --fix 4 auto-fixable (bracket.py I001/SIM108/RET504, reconciler.py ARG002)
- L2: dead `StrategyDescription.tsx` remove
- L3: App.tsx import order
- L4: reconciler binary-path `!=` dust tolerance (reconciler.py:127)
- L5: coordinator `_adapter._filters` private reach (Coordinator.current_state accessor)
- L6: bars_per_year unify 365.25 family (8766/2191)
- L7: WS payload `%r` redaction (bundle with M4 mainnet)
- L8: f-string logging vector_backtest.py:80
- L9: quant docs — T6 LOCKED-params semantic note in ADR 0014

---

## Execution batches (subagent-driven, sequential — TDD)

- BATCH 1 (BLOCKER bybit): B1 + B2
- BATCH 2 (BLOCKER data): B3 + B4
- BATCH 3 (HIGH exec/data): H4 + H5 + H7
- BATCH 4 (HIGH dashboard/python): H1 + H2 + H3 + M2
- BATCH 5 (HIGH trading): H6 + H8 + H10 (after trader-expert)
- BATCH 6 (HIGH test): H9 + M8
- BATCH 7 (MEDIUM): M1 + M3 + M4 + M5 + M6 + M7
- BATCH 8 (LOW cleanup): L1-L9
- BATCH 9: frontend (L2 + L3 + MonthlyHeatmap)

## Verify gates (PHASE 5)
pytest + mypy --strict + Vitest + Playwright + lint + tsc + build — ALL GREEN.

## Post-fix RE-REVIEW (PHASE 6 second pass)
Re-dispatch reviewers on the diff → catch regressions introduced by fixes. Loop until clean.

## Ship (PHASE 8)
PR + CI green + squash-merge + tag v0.1.0-alpha.49.
