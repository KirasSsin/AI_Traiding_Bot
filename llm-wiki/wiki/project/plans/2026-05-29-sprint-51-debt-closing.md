# Sprint 51 — Debt Closing Implementation Plan

> **For agentic workers:** subagent-driven-development, sequential dispatch (one debt at a time — shared-file conflict avoidance). TDD strict. Per-debt commit.

**Goal:** Close 6 carry-over debts (3 from S49, 3 from S50) — bugfix sprint, no new features.

**Architecture:** Each debt is independent. D4 (atr_breakout look-ahead) = highest priority (shipped LOCKED code). D1 (dup-order retCode) = pre-mainnet HIGH. D5 needs trader-expert mini-verdict. Rest mechanical.

**Tech Stack:** Python 3.12, pytest, mypy --strict. Branch `feature/sprint-51-debt-closing`.

---

## Debt registry

| # | Debt | Source | Sev | Files |
|---|------|--------|-----|-------|
| D1 | 110072 dup-order retCode → REJECT_DUPLICATE_ORDER, treat success | S49 bybit | HIGH | `src/execution/bybit/errors.py`, `coordinator.py` flatten paths |
| D2 | parquet manifest/partition (SHA-256 + layout doc OR deferred ADR) | S49 data | MED | `src/marketdata/storage.py` |
| D3 | block_bootstrap edge-null docstring + gate-promotion guard | S49 quant | LOW | `src/backtest/mc_permutation.py` |
| D4 | atr_breakout windowed-ATR parity (investigate + maybe fix) | S50 trading | HIGH | `src/signalgen/atr_breakout_strategy.py` |
| D5 | cross_trial pool per-strategy-class scoping (ADR decision) | S50 quant+trader | MED | `src/analytics/cross_trial_log.py` + ADR |
| D6 | supertrend_runner _backtest_single numerical parity test | S50 test | LOW | `tests/unit/test_supertrend_runner.py` |

---

## Task D4: atr_breakout windowed-ATR parity (FIRST — shipped code, opus)

**Investigate:** Does live streaming `on_bar` (windowed `deque(maxlen)` ATR re-seed) diverge from the full-history vectorized ATR that ADR 0064 WFA validated? If WFA used vectorized `strat_atr_breakout` (full-history) but live uses windowed re-seed → live/backtest parity gap on a SHIPPED LOCKED strategy.

**Files:** `src/signalgen/atr_breakout_strategy.py` (~145-200), `scripts/autoresearch_endless.py::strat_atr_breakout`, `src/backtest/atr_breakout_runner.py`.

- [ ] **Step 1: Investigate** — trace which ATR path ADR 0064 WFA/backtest used. Compare streaming windowed-ATR output vs full-history `wilder_atr` (from S50 indicators.py) on same BTC data. Measure divergence magnitude.
- [ ] **Step 2: Decision** — if divergence material (>1% of trades flip): fix streaming to incremental full-history ATR (mirror S50 Supertrend `_update_atr`). If immaterial (warm buffer_size+10 >> atr_period makes re-seed negligible): document as acceptable + ADR note, no code change.
- [ ] **Step 3 (if fix): TDD** — failing test: streaming ATR == full-history `wilder_atr` within 1e-9. Implement incremental ATR. Verify atr_breakout existing tests GREEN + parity restored.
- [ ] **Step 4: ADR note** — amend ADR 0064 (or new ADR) documenting the finding + resolution.
- [ ] **Step 5: Commit** `fix(s51): atr_breakout ATR parity — <fixed incremental | documented acceptable> (D4 S50 carry)`.

## Task D1: 110072 dup-order retCode (opus)

**Files:** `src/execution/bybit/errors.py` (_MAP + ReasonCode), `src/execution/coordinator.py` flatten paths (~368-375 residual, ~481-489 emergency).

- [ ] **Step 1: Failing test** — Bybit retCode 110072 (OrderLinkedID duplicate) currently → UNKNOWN_ERROR → flatten treats as failure → spurious HALT_FLATTEN_FAILED. Test asserts 110072 → treated as success (order already landed = idempotency complete).
- [ ] **Step 2: Implement** — add 110072 → `REJECT_DUPLICATE_ORDER` (new ReasonCode OR existing) in `_MAP`. In flatten paths, catch this code → treat as success (the dedup means the prior submit succeeded). Mirror `adapter.py:260` 110001 already-terminal pattern.
- [ ] **Step 3: Verify** — test GREEN, existing execution tests GREEN, mypy 0. reason codes count if new code added.
- [ ] **Step 4: Commit** `fix(s51): Bybit 110072 dup-order → success in flatten (idempotency complete, no spurious HALT) (D1 S49 carry)`.

## Task D3: block_bootstrap edge-null guard (sonnet)

**Files:** `src/backtest/mc_permutation.py` `block_bootstrap_p_value`.

- [ ] **Step 1:** Add docstring warning — resample-with-replacement is NOT an edge-significance null (measures sampling variability, not edge vs no-edge). sign_flip is the gate; block_bootstrap is informational secondary only.
- [ ] **Step 2:** Add a guard/comment preventing accidental gate-promotion (e.g. a module constant `_BLOCK_BOOTSTRAP_IS_GATE = False` + assert in any gate-eval path, OR clear docstring contract). Keep minimal.
- [ ] **Step 3: Commit** `docs(s51): block_bootstrap edge-null warning + gate-promotion guard (D3 S49 carry)`.

## Task D5: cross_trial pool scoping (trader-expert verdict THEN impl, opus)

**Files:** `src/analytics/cross_trial_log.py` + new/amended ADR.

- [ ] **Step 1: trader-expert mini-verdict** — should DSR cross-trial pool be per-strategy-class (atr_breakout pool ≠ supertrend pool ≠ mean_reversion pool) OR global? Mixing S44 ATR multi-symbol (sigma 34) with S50 Supertrend over-penalizes. But Bailey N_trials is per-hypothesis-family — what's the family boundary? Binding verdict.
- [ ] **Step 2: Implement** per verdict — likely add `strategy_class` field to TrialEntry + `sigma_sr(strategy_class=...)` scoped filter. Migrate existing 9 entries with backfilled class tags.
- [ ] **Step 3: TDD** — test scoped sigma_sr isolates classes. Existing cross_trial tests GREEN.
- [ ] **Step 4: ADR** documenting pool-scoping decision.
- [ ] **Step 5: Commit** `feat(s51): cross_trial pool per-strategy-class scoping (D5 S50 carry, trader-expert verdict)`.

## Task D6: supertrend_runner _backtest_single parity test (sonnet)

**Files:** `tests/unit/test_supertrend_runner.py`.

- [ ] **Step 1:** Add parity test — `_backtest_single` PnL/trades vs streaming SupertrendStrategy on same series (mirror T6 strat parity but for the runner's vectorized kernel — the 3rd unverified copy per test-engineer).
- [ ] **Step 2: Verify** GREEN. Commit `test(s51): supertrend_runner _backtest_single numerical parity vs streaming (D6 S50 carry)`.

## Task D2: parquet manifest (sonnet, LAST — may defer)

**Files:** `src/marketdata/storage.py`.

- [ ] **Step 1: Decision** — full SHA-256 manifest + Hive partition = scope-heavy. Per YAGNI (read-only OLAP, single-user): implement minimal SHA-256 sidecar manifest on write OR document flat-layout-is-intentional in storage component page + ADR note "manifest deferred until multi-writer".
- [ ] **Step 2:** Whichever — minimal manifest (write `.sha256` sidecar) OR doc-only deferral. Operator-lean: doc deferral unless cheap.
- [ ] **Step 3: Commit** `<feat|docs>(s51): parquet manifest <minimal sidecar | documented deferral> (D2 S49 carry)`.

---

## PHASE 5 gates
pytest GREEN + mypy --strict 0 + reason codes (D1 may +1) + lint.

## PHASE 6 reviewers (parallel, post-impl)
bybit-api (D1) + trading-logic (D4 parity) + quant-stats (D3 + D5) + data-integrity (D2) + python + test-engineer.

## PHASE 8 ship
tag v0.1.0-alpha.51.

## Self-Review
- Coverage: all 6 debts → D1-D6 tasks. D4 first (shipped-code risk), D2 last (may defer).
- Sequential dispatch mandatory (this session had parallel-agent shared-file conflicts).
- D5 needs trader-expert before impl (judgment).
- D4 may be doc-only if divergence immaterial (buffer_size+10 warm).
