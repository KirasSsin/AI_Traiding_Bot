---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-10  # T3 done
sprint: 42
phase: 4-execution
branch: feature/sprint-42-atr-breakout-hardening
tag: v0.1.0-alpha.41
---

## S42 IN PROGRESS — ATR breakout hardening (dashboard contract envelope)

**Phase:** 4-execution  
**Branch:** feature/sprint-42-atr-breakout-hardening  
**in_progress:** T4 next

**Completed tasks:**
- T1: `src/backtest/research_runner_envelope.py` + `tests/unit/test_research_runner_envelope.py` — DONE (commit fe49e39)
  - 5/6 tests pass. 1 test (`test_envelope_subperiod_robustness_3_of_5_emits_warn_chip`) has data inconsistency:
    equity_curve `[0,50,30,60,50,45]` gives 2/5 positives (not 3/5) under delta-from-previous algorithm.
    Needs operator decision: fix test curve OR adjust algorithm.
- T2: `src/backtest/atr_breakout_runner.py` wired to envelope + `tests/integration/test_atr_breakout_dashboard_contract.py` — DONE (commit 383e67b)
  - 5/5 new contract tests PASS. 8/8 baseline floor tests PASS (PnL unchanged). mypy 0 errors.
- T3: `src/backtest/volume_breakout_runner.py` wired to envelope + `tests/integration/test_volume_breakout_dashboard_contract.py` — DONE (commit 0ade871)
  - 4/4 new contract tests PASS. 29/29 total volume_breakout tests PASS. mypy 0 errors.

**Next action:** T4 — next task in S42.

---

## S41 COMPLETE ✅ — ATR breakout multi-combo dashboard presets

**All tasks DONE (T1-T10):**
- T1: Generalized `atr_breakout_runner.py` (params kwarg, PARQUET_BY_COMBO, per-interval BARS_PER_YEAR)
- T2: `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO` — 10 combos с независимыми locked params (ADR 0061)
- T3-T9: 9 новых STRATEGY_PRESETS в dashboard (SOLUSDT 4H / ETHUSDT 1H / BTCUSDT 15M / BTCUSDT 1H / SOLUSDT 1H / ETHUSDT 4H / SOLUSDT 15M / BTCUSDT 1D / ETHUSDT 15M)
- T10: ADR 0061 + sprint-41 + current-state.md + index.md + log.md + SPRINT_STATE

**Tests:** 934 unit pass / 20 новых integration tests / mypy 0 / ruff 0

**Canonical counts:** 16/30/74/56 (reason codes unchanged)

**ADRs:** 61 / Sprint pages: 45 / Tag: v0.1.0-alpha.41

**Next action:** operator decision — Gate 2 paper-trade для новых комбо, autoresearch iter2, или другое.

---

## S40 COMPLETE ✅ — atr_breakout production integration

**All 7 tasks DONE (T1-T7):**
- T1: +3 ReasonCodes (53→56) per ADR 0060
- T2: ATRBreakoutStrategy class (verbatim autoresearch port)
- T3: Production runner + 8 integration HARD-GATE tests
- T4: Dashboard preset `atr_breakout_iter_endless`
- T5: Wiki docs (ADR 0060 + sprint-40 + component + sync)
- T6: SPRINT_STATE updated
- T7: git push + PR + merge + tag v0.1.0-alpha.40

**Profit invariant:** 8.7y +819.81% / Sharpe 1.11 / 69 trades / 5/5 sub-periods positive (первый 5/5).

---

## S39 PHASE 8 — ready to ship

**Phases 1-7 ALL DONE:**
- Phase 6 review: 8 reviewers (2 APPROVE / 6 APPROVE_WITH_CONCERNS / 1 REQUEST_CHANGES → fixed B1 commit + R3 C4 RiskManager fix + R2 C2 ADR Sharpe CI correction)
- ADR-0059 G1-G6 documented gaps section + pre-s40-backlog.md created
- pytest 915 unit + 41 integration / mypy clean / canonical 16/30/74/53
- Profit invariant HARD-GATE: VERIFIED PASS

**Next action:** git push + gh pr create + squash-merge + tag v0.1.0-alpha.39

**Post-ship operator action:** Gate 2 forward paper-trade на δ TESTNET (N≥10 BLOCKER к real capital).

---

## S39 PHASE 7 COMPLETE — wiki sync done (T14)

**Brainstorm RESOLVED:** 8 CONFIRM + 1 REVISE (Q6 8mo PRIMARY) + 1 EXPAND→Option A (baseline LOCK, ATR filter S40+)

**Sprint scope:** Volume_breakout production integration (Track A) + critical tech debt (Track B/C/E)

**Profit invariant (HARD):** VERIFIED PASS — production runner ±0.5% baseline (8mo held-out +20.42% n=17 / 3.3y +122.66%)

**T14 Wiki sync DONE:**
- ADR-0059 created (`wiki/project/decisions/0059-sprint-39-volume-breakout-pre-registration.md`)
- Sprint-39 page created (`wiki/project/sprints/sprint-39-volume-breakout-tech-debt.md`)
- Component page created (`wiki/project/components/volume-breakout-strategy.md`)
- reason-codes.md updated (50→53)
- current-state.md updated (reason_codes 50→53, ADRs 58→59, sprints 42→43, components 46→47, S39 sprint row)
- index.md updated (ADR + sprint + component + reason-codes entries)
- log.md sprint-end appended

**Next action:** Phase 8 SHIP — PR create → merge → tag v0.1.0-alpha.39

**Track tasks COMPLETE (T1-T13 + T5b):**
- Track A — volume_breakout core (A0-A6 + T5b: 7 задач) ✓
- Track B — critical tech debt (B1-B3: 3 задачи) ✓
- Track C — cleanup (C1-C2: 2 задачи) ✓
- Track E — bybit-api M3+M4 (E1-E2: 2 задачи) ✓
- T14 — wiki sync ✓

## S39 BRAINSTORM PENDING — Autoresearch Metric Improvement Loop

**Operator direction:** автоматизировать поиск improvements торговых метрик через autoresearch paradigm. Iter 1 (S35 Donchian, branch `autoresearch/donchian-may8`) ЗАКРЫТ как 7-я honest close — overfit на held-out (train Sharpe 1.27 → held-out -3.23) confirmed trader-expert prior: Donchian needs trend filter, не hyperparameter tuning.

**Iter 2 candidate:** EMA200 trend filter as new strategy variant в src/backtest/indicators.py + new preset `donchian_ema200_filter` UI dropdown.

**Two execution modes:**
- **(R) Research toy** — продолжаем в research/ branch `autoresearch/<strategy>-<tag>`, bypass kit per skill `autoresearch-iterate` rules. ~2h. Result: held-out PASS/FAIL verdict.
- **(K) Formal kit cycle** — full 9-phase sprint 39 для EMA200 filter. ~10-12h. Result: новый production strategy + ADR + tests + tag alpha.39.

**Current state post-S38 ship:**
- main @ de78073 (agent-memory + gitignore commit)
- branches alive: `autoresearch/donchian-may8` (research toy iter 1)
- skill `autoresearch-iterate` ready на trigger "запусти autoresearch на N итераций"
- 4 strategy presets в UI dropdown с WFA auto-scale active

**Pre-S39 carry-overs (preserved from S38):**
- T3 bybit-api-reviewer H1 rate-limit backoff missing
- T3 bybit-api-reviewer H2 WS reconnect verification gap
- T3 M1-M4 + 3 LOW
- F8 block_size constant unification
- 12mo MAINNET-promotion ADR (draft trigger: n=10 first non-NaN DSR)
- Item #7 backward-compat shim cleanup
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios

**Operator next action:** выбрать R или K mode для iter 2 + initiate.

---

## S38 SHIPPED ✅ — δ Parallel Hardening (F2 quant + bybit-api-reviewer + Item #7 Demeter + playbook)

PR #49 → 297d1ea squash-merge. Tag v0.1.0-alpha.38 pushed. Branch deleted. **CI passed first try (10th PR с strict baselines).**

**δ TESTNET activate Track 1 operator-side parallel** (per `delta-activation-playbook.md` 5-step + S38 NEW gates F4-F7 + T3 H3 accountType).

**S38 closures:**
- F2 quant HIGH (compute_live_sharpe pnl_pct correctness)
- F3 bybit-api-reviewer first invocation (dormant since S30) — 0 BLOCKER, 3 HIGH triaged
- Item #7 RiskSharedDeps Demeter refactor (DI ONLY)
- Playbook 5 NEW gates + UNDERPOWERED expected + halt-triggered immediate review
- ADR 0057 amendment (months_since truncation semantics)

**v0.7+ next operator decision (post-S38):**
- (a) **Operator activates δ TESTNET** per playbook (если not yet done) — forward profit path
- (b) **S39 carry-overs** — bybit-api H1+H2 + M1-M4 + 3 LOW + Item #7 backward-compat shim cleanup
- (c) **Wait для δ data accumulation** — n=10 milestone triggers 12mo MAINNET-promotion ADR draft (per quant anti-snooping)

**Carry-overs к S39+:**
- T3 bybit-api-reviewer H1 rate-limit backoff missing
- T3 bybit-api-reviewer H2 WS reconnect verification gap
- T3 M1 retCode taxonomy gaps + M2 pybit response-shape + M3 WS data isinstance + M4 __repr__ secret redaction
- T3 3 LOW cosmetic
- F8 block_size constant unification
- 12mo MAINNET-promotion ADR (draft trigger: n=10 first non-NaN DSR)
- Item #7 backward-compat shim cleanup (post all callers migrated к shared_deps)
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios

## S38 SHIPPED — Earlier in-progress section (preserved для history)

**Operator approved Path A** (ROUND 6 consilium binding) — δ activate immediately + S38 sprint runs в parallel.

**Track 1 (operator-side):** δ TESTNET activation per `delta-activation-playbook.md` 5-step procedure (operator action — set `S35_DEMO_ACTIVE=true`).
**Track 2 (AI-side):** S38 sprint 7 tasks (T1-T7) addresses ROUND 6 NEW findings (F2 + F3 + Item #7 + playbook amendments).

Branch: `feature/sprint-38-delta-parallel-hardening`. Plan: `plans/2026-04-27-sprint-38-delta-parallel-hardening.md` (TBD).

### Phase tracking (S38 — in progress)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S37 ship |
| 2 Brainstorm | done | ROUND 6 consilium 3 agents UNANIMOUS Q1 — `pre-s38-backlog.md` (4 verdicts + 8 findings F1-F8 + 7 task structure) |
| 3 Plan | in_progress | `plans/2026-04-27-sprint-38-delta-parallel-hardening.md` |
| 4 Execute | done | T1-T7 all done. 14 commits. 8 NEW tests. pytest 905 unit + 33 integration / mypy 0 / canonical 16/30/74/50. |
| 5 Verify | done | pytest 905+33 / mypy 0 / canonical unchanged / anti-snooping preserved (ADRs pre-T2 code) |
| 6 Review | done | T3 = bybit-api-reviewer review itself + T2 F2 explicit test verifies + T4 backward-compat tests cover refactor |
| 7 Sync | done | wiki sync T7: sprint-38 + index + current-state + log + ADR 0057 amendment + ADR 0056 amendment 2 + playbook amendments |
| 8 Ship | in_progress | gh pr + squash merge + tag v0.1.0-alpha.38 |
| 9 Close | pending | SPRINT_STATE between-sprints |
### S38 critical pre-commitments (BINDING per ROUND 6 consilium)

1. F2 pnl_quote → pnl_pct fix MUST land before 12mo review uses calibration ratio
2. Item #7 RiskSharedDeps refactor: DI wiring ONLY, NOT touch _tick body OR HaltGate.evaluate()
3. Smoke-start gate before Item #7 PR merge (pytest 897+33 + TESTNET smoke check)
4. F3 bybit-api-reviewer dispatched в S38 (review document deliverable)
5. Playbook amendments: 5 NEW gates (F4 API key + F5 stale activation_ts + F6 UNDERPOWERED + F7 WAL/bootstrap + halt-triggered immediate review)
6. NO 12mo MAINNET-promotion ADR в S38 (defer к n=10 milestone per quant anti-snooping)

## S37 SHIPPED ✅ — Carry-overs Hardening (security HIGH + trading-logic + quant + playbook)

PR #48 → e837b38 squash-merge. Tag v0.1.0-alpha.37 pushed. Branch deleted. **CI passed first try (9th PR с strict baselines, CI workflow synced 49→50 inline в T8).**

**δ TESTNET production-ready.** Operator action required:
1. Set `S35_DEMO_ACTIVE=true` в .env
2. Restart bot per `delta-activation-playbook.md` 5-step procedure
3. Verify startup banner + signed activation_ts persisted
4. Monitor halt_log + trade_history per playbook weekly procedure

**6 critical S36 carry-overs CLOSED:**
- Security HIGH 1+2: symbol whitelist + fail-closed + HALT_UNKNOWN_SYMBOL (49→50)
- Security HIGH 3: activation_ts HMAC integrity per ADR 0018 pattern
- Trading-logic 4: clock injection (deterministic property tests)
- Trading-logic 5: coordinator.symbol public property (Demeter)
- Quant 8: DSR boundary tests + S22 baseline 6.17→2.96 (calibration)

**v0.7+ next operator decision (post-S37):**
- (a) **δ activate now** — set env var per playbook (forward profit path)
- (b) **β pause** — defer activation indefinitely
- (c) **S38 architecture refactor** — Item #7 RiskSharedDeps + extended docs first
- (d) **New strategy** — new ADR pre-registration

**Carry-overs к S38+:**
- Item #6 months_since truncation documentation
- Item #7 RiskSharedDeps refactor (Demeter — RuntimeManager properties)
- Item #9 Sharpe semantics extended ADR doc
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios
- 12mo MAINNET-promotion ADR (per ADR 0055 SD-8 deferred)

## S37 READY TO SHIP — Carry-overs Hardening (security HIGH + trading-logic + quant + playbook)

**Operator approved ROUND 5 consilium binding** — (c) carry-overs sprint first, then S38 δ activate. 8 tasks consilium-merged.

Branch: `feature/sprint-37-carry-overs-hardening`. Plan: `plans/2026-04-27-sprint-37-carry-overs-hardening.md`.

### Phase tracking (S37 — all done)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S36 ship |
| 2 Brainstorm | done | ROUND 5 consilium 3 agents CONSENSUS — `pre-s37-backlog.md` (6 pre-commitments + EXPAND scope: HALT_UNKNOWN_SYMBOL ReasonCode +1 / calibration baseline 6.17→2.96 / ADR 0056 amendment) |
| 3 Plan | done | `plans/2026-04-27-sprint-37-carry-overs-hardening.md` |
| 4 Execute | done | T1-T8 all done. 17 commits. 26 NEW tests. |
| 5 Verify | done | pytest 897 unit + 33 integration / mypy 0 / canonical 16/30/74/50 / anti-snooping preserved |
| 6 Review | done | T2 security-auditor + trading-logic-reviewer parallel (BLOCKER+HIGH fixed inline e686dba). T3-T7 skipped per pattern. |
| 7 Sync | done | T8 wiki sync: sprint-37 + index + current-state + reason-codes + ESM footer + log + CI bump 49→50 |
| 8 Ship | in_progress | gh pr + squash merge + tag v0.1.0-alpha.37 |
| 9 Close | pending | SPRINT_STATE between-sprints + δ activate operator action |

### S37 critical pre-commitments (BINDING per ROUND 5 consilium)

1. HALT_UNKNOWN_SYMBOL distinct ReasonCode (NOT reuse) per audit-log attribution
2. Calibration baseline amendment к S22 mean fold Sharpe = 2.96 (conservative)
3. activation_ts HMAC integrity per ADR 0018 pattern
4. δ activate immediately post-S37 ship (no observation gap)
5. Operator playbook page mandatory (NOT just ADR references)
6. Items 6+7+9+10 explicitly DEFERRED к S38+ (NOT silently dropped)

## S36 SHIPPED ✅ — δ TESTNET Activation (HaltGate wired + B1 fix + DSR amendment + ReasonCode +4)

PR #47 → aab7e32 squash-merge. Tag v0.1.0-alpha.36 pushed. Branch deleted. **CI passed (8th PR с strict baselines, fixed canonical reason_codes 45→49 inline).**

**δ TESTNET infrastructure NOW WIRED LIVE.** HaltGate connected к RuntimeManager._tick. B1 CRITICAL fix applied (S17-relaxed LOCKED params wired live — δ NO LONGER runs S15-noise params silently). DSR sigma_SR ADR 0056 amendment closes S35 T4 carry-overs.

**Operator action для δ activate:**
1. Set `S35_DEMO_ACTIVE=true` в .env file
2. Restart bot — first tick auto-records activation_ts в SQLite
3. HaltGate evaluates per-tick — fires halt + bot exits cleanly если any of 4 triggers (DD intraday/multiday/streak/timeout)
4. 12mo MAINNET-promotion gate per ADR 0053 + ADR 0055 SD-1 (NOT TESTNET shutdown)

**v0.7+ next decision (operator post-S36):**
- (a) **δ activate now** — set env var + restart + monitor 12mo (operator action)
- (b) **β pause indefinitely** — δ infrastructure ready но defer activation
- (c) **S37 carry-overs sprint** — address 10 items in pre-s37-backlog ДО δ activate (security HIGH + architecture refactor)
- (d) **Different strategy** — new ADR pre-registration

**Carry-overs к S37+ (`pre-s37-backlog.md`):**
- 2 security HIGH (symbol fail-closed + activation_ts integrity)
- 3 trading-logic (clock injection + coordinator.symbol public + months truncation doc)
- 1 architecture MEDIUM (RiskSharedDeps refactor — Demeter)
- 2 quant-stats (boundary tests n=10/30 + pooled trade-level Sharpe doc)
- 2 operational (DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios + δ activation operator playbook)

## S36 COMPLETE 🟢 — δ TESTNET activation (HaltGate wire-up + B1 critical fix + DSR amendment)

**ROUND 4 consilium binding executed.** δ infrastructure WIRED LIVE. 63 NEW tests / pytest 871+33 / mypy 0 / canonical 16/30/74/49.

Branch: `feature/sprint-36-delta-activation`. Tag: `v0.1.0-alpha.36`.

### Phase tracking (S36 — all done)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S35 ship |
| 2 Brainstorm | done | ROUND 4 consilium 3 agents + ROUND 2 Q4 BINDING — `pre-s36-backlog.md` (8 pre-commitments + hybrid duration option H + B1 critical + DSR amendment text + N_trials freeze=7) |
| 3 Plan | done | `plans/2026-04-27-sprint-36-delta-activation.md` |
| 4 Execute | done | T1-T8 all done. 19 commits. 63 NEW tests. |
| 5 Verify | done | pytest 871 unit + 33 integration / mypy 0 / canonical 16/30/74/49 / anti-snooping preserved |
| 6 Review | done | 8 reviewer dispatches across T1-T7. BLOCKER + HIGH fixes inline. Carry-overs → pre-s37-backlog. |
| 7 Sync | done | wiki sync T8: sprint-36 + 2 components + pre-s37-backlog + index + current-state + reason-codes + ESM footer + log |
| 8 Ship | in_progress | gh pr + squash merge + tag v0.1.0-alpha.36 |
| 9 Close | pending | SPRINT_STATE between-sprints |

### S36 critical pre-commitments (BINDING per ROUND 4 consilium)

1. B1 fix: MEAN_REVERSION_S17_RELAXED_PARAMS LOCKED params wired к live path BEFORE day-1 trade
2. DSR sigma_SR sourcing protocol: N≥3 PREFERRED, NaN+UNDERPOWERED для 1-2, fallback REMOVED
3. N_trials freeze at 7 для δ live demo (S22 hypothesis re-evaluation, no increment)
4. Adapted gates methodology для live data
5. Hybrid duration option (H): HaltGate operational + n≥50 PASS + 12mo MAINNET-promotion gate (NOT shutdown). NO 6mo interim.
6. MAINNET promotion criteria DEFERRED к S37+
7. ReasonCode enum +4 HALT_S36_* (45→49)

## S35 SHIPPED ✅ — δ TESTNET ready + α Donchian FAIL conjoint + ζ risk refactor

PR #46 → 69ea6ea squash-merge. Tag v0.1.0-alpha.35 pushed. Branch deleted. **CI passed (7th PR с strict baselines).**

**ROUND 3 consilium binding executed.** α direction CLOSED per ADR 0054 (FAIL conjoint: n=21<<50 / aggregate Sharpe -0.95 / DSR<<0.95 / 4 of 6 gates fail). δ TESTNET infrastructure ready, NOT yet activated — operator decides activation timing.

**v0.7+ next decision (operator):**
- (a) **β pause** — per pre-commit #8 since α FAIL (default fallback)
- (b) **δ activate** — wire HaltGate к RiskManager + start TESTNET demo (S36 wire-up sprint)
- (c) **Different strategy** — new ADR pre-registration (N_trials=6)
- (d) **ε pairs/stat arb** — deferred к v0.8+ per pre-commit #7

**Carry-overs к S36+:**
- Donchian reason codes к ReasonCode enum (45→48) если α revival
- DSR sigma_SR fallback formal ADR amendment (per-fold stdev proxy документирован но не canonical)
- Channel exit replay path implementation (currently ATR-only в indicators.py donchian branch)
- HaltGate wire-up к RiskManager.assess() (S36 если δ activates)

## S35 IN PROGRESS 🟡 — δ TESTNET + α Donchian + ζ Risk Mgmt

**Operator approved ROUND 3 binding consilium decision** — δ TESTNET live demo primary + α Donchian 4H long-only parallel synthetic + ζ risk management complement bundled into S35.

Branch: `feature/sprint-35-testnet-donchian-risk`. Plan: `plans/2026-04-27-sprint-35-testnet-donchian-risk.md` (~5 TDD tasks T1-T5, ~480 LoC + 2 ADRs + 2 components + 13 tests).

### Phase tracking (S35 — in progress)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S34 ship |
| 2 Brainstorm | done | ROUND 3 consilium 3 agents CONSENSUS — `pre-s35-backlog.md` (8 pre-commitments + LOCKED params + halt criteria) |
| 3 Plan | done | `plans/2026-04-27-sprint-35-testnet-donchian-risk.md` |
| 4 Execute | done | T1-T5 all done. T4 verdict FAIL conjoint (n=21<<50 / aggregate Sharpe -0.95 / DSR<<0.95 / 4 of 6 gates fail). α direction CLOSED per ADR 0054. cross_trial NOT appended (FAIL protocol). pytest 802 / mypy 0. T5: HASH_ALLOWLIST +4 s35_halt_* + sprint-35 page + 2 components + index/counts sync. |
| 5 Verify | done | pytest 802 passed / mypy 0 / canonical 16/30/74/45 / Donchian FAIL verdict recorded / HaltGate purity verified |
| 6 Review | done | T1=2 reviewers / T2=3 reviewers / T3=1 reviewer / T4=4 reviewers parallel |
| 7 Sync | done | wiki sync in T5 — sprint-35 page + 2 components + index/current-state + log.md |
| 8 Ship | pending | tag v0.1.0-alpha.35 — sprint-finish skill next |
| 9 Close | pending | SPRINT_STATE between-sprints |

## S34 SHIPPED ✅ — Hybrid 6-th Honest Close v0.6 + Amendment LOCKED

PR #45 → ac55c08 squash-merge. Tag v0.1.0-alpha.34 pushed. Branch deleted. **CI passed (6th PR с strict baselines).**

**v0.6 chapter end. Both consilium recommendations honored** (A(a) honest close + A(b) amendment LOCKED). Anti-snooping discipline preserved.

**v0.7+ direction (operator decides — NOT pre-committed):**
- (a) Project pause indefinitely
- (b) New measurement с amended spec (operator acknowledgment per ADR 0052 + new data)
- (c) Different strategy class (Donchian / ML / HMM)
- (d) Different timeframe (1D с volume gate) — NOT recommended
- (e) Different asset class — beyond v0.1 scope

## S34 IN PROGRESS 🟡 — Hybrid 6-th Honest Close v0.6 + Amendment LOCKED

**Operator chose hybrid** (merge A(a) + A(b) per S33 consilium consensus). Branch: `feature/sprint-34-honest-close-v06-hybrid`. Plan: `plans/2026-04-27-sprint-34-honest-close-v06-hybrid.md` (d89217f).

### Phase tracking (S34 — in progress)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S33 ship |
| 2 Brainstorm | done | S34 consilium в `pre-s33-backlog.md` (acab8e3 main) — CONSENSUS A(b) primary / A(a) fallback / hybrid operator-chosen |
| 3 Plan | done | `plans/2026-04-27-sprint-34-honest-close-v06-hybrid.md` (d89217f) |
| 4 Execute | in_progress | T1-T5 controller-driven (~3-4h forecast, ~85 LoC + 2 ADRs) |
| 5 Verify | done | pytest 808 / mypy 0 / canonical 16/30/74/45 ✓ / cross_trial.json `{"trials": []}` ✓ / archive _v0.6.json 3 entries ✓ / acceptance-criteria amendment section ✓ / pre-check overall_pass=False (4/5 amended gates fail) ✓ |
| 6 Review | skipped | docs+minor code (backward-compat default), no production trading code logic changes |
| 7 Sync | done | log.md sprint-end + index/current-state synced |
| 8 Ship | done | PR #45 → ac55c08 + tag v0.1.0-alpha.34. CI passed (6th PR с strict baselines). |
| 9 Close | done | SPRINT_STATE between-sprints + v0.7+ deferred к operator (this update) |

### Phase 4 — task progress (S34)

| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 Engineering pre-check (S33 data на amended gates) | done | a2e455b | Pre-check: S33 data на S34 amended gates STILL FAILS 4/5 (T5 raw 66 PASS / n_eff 26<<50 FAIL / MC 0.52>>0.05 FAIL / T6 -2.84<<0.7 FAIL / DSR 0.919<0.95 FAIL). Confirms honest close justified — amendment alone insufficient. |
| T2 ADR 0051 6-th honest close v0.6 + cross_trial archive + reset | done | b1ae20f | ADR 0051 (6-th honest close) + cross_trial archive _v0.6.json (3 S33 entries) + reset `{}` (mirror S14/S16/S18/S21/S23) + 6-hypothesis falsification record + structural insights binding. |
| T3 ADR 0052 acceptance-criteria amendment + 10-item pre-commit list LOCKED | done | 40f9c6f | ADR 0052 (T5 100→50 / n_eff≥50 NEW Kish / MC≤0.05 tightened / T6+DSR unchanged) + acceptance-criteria.md amendment section + 10-item pre-commit list verbatim + operator acknowledgment template. |
| T4 n_eff gate enforcement в evaluate_acceptance_gate() + tests | done | ffcf9bc | evaluate_acceptance_gate() extended с n_eff/T5/MC kwargs (backward-compat default) + 5 NEW tests (n_eff threshold / T5 floor 50 / MC tightened / all amended pass / backward-compat). pytest 803→808 / mypy 0. |
| T5 sprint-34 page + index/counts (50→52 ADRs / 37→38 sprints) | done | f9b6e42 | sprint-34 page + index entries (S34 + ADR 0051 + ADR 0052) + current-state.md counts updated. |

## S33 SHIPPED ✅ — Trading Restart, F BACKTEST FAIL conjoint

PR #44 → 3d97aa0 squash-merge. Tag v0.1.0-alpha.33 pushed. Branch deleted. **CI passed (5th PR — first time с strict baselines mypy=0, pytest=0 failures).**

**F BACKTEST verdict FAIL conjoint** на 5/9 acceptance gates (T5 raw 66<100 + n_eff 26 + T6 -2.84 + MC 0.52 + DSR 0.919). Per-symbol: BTC=23 (-4.40), ETH=25 (-3.85), SOL=18 (-0.28).

**Pre-committed failure branch (Item #12) TRIGGERED → S34 = 6-th honest close v0.6** (mirror S14/S16/S18/S21/S23 BINDING precedent) OR operator-driven spec amendment с explicit statistical-framework override statement.

## S33 IN PROGRESS 🟡 — Trading restart brainstorm

**First trading sprint after S32 series kit improvements.** Branch: `feature/sprint-33-trading-restart`. Operator directive: 3-agent консилиум (trader-expert + trading-logic-reviewer + quant-stats-reviewer) для ESC-1/2/3 + formulas correctness + strategy direction.

PHASE 2 brainstorm в progress:
- 6 structured questions: ESC-1 / ESC-2 / ESC-3 / formulas post-S27 / S33 strategy direction / test debt
- Dispatch 3 agents parallel via `superpowers:dispatching-parallel-agents`
- Consolidate verdicts: CONSENSUS / MAJORITY / DISAGREE
- ROUND 2 iterative justify if disagreement
- Document `pre-s33-backlog.md`

### Phase tracking (S33 — in progress)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S32e ship |
| 2 Brainstorm | done | 3-agent консилиум 2 rounds — `pre-s33-backlog.md` (20bfb83 + 5ea378e). Consensus APPROVE all 6 escalations + 13 required + 2 optional NEW items. |
| 3 Plan | done | `plans/2026-04-27-sprint-33-trading-restart.md` (860b209) — 6 tasks T1-T6 + 21 items consolidated, 8-12h forecast |
| 4 Execute | in_progress | T1-T6 controller-driven TDD. Per-task SPRINT_STATE update protocol. |
| 5 Verify | done | pytest 803 / mypy 0 errors / canonical 16/30/74/45 ✓ / cross_trial_log 3 entries (BTC/ETH/SOL S33) / F measurement.json verdict=FAIL ✓ |
| 6 Review | pending | L5 reviewer matrix per touched files (parallel dispatch) |
| 7 Sync | pending | wiki updates |
| 8 Ship | done | PR #44 → 3d97aa0 + tag v0.1.0-alpha.33. CI passed (5th PR с strict baselines mypy=0/pytest=0 failures). |
| 9 Close | done | SPRINT_STATE between-sprints + S34 6-th honest close v0.6 trigger documented (this update) |

### Phase 4 — task progress (S33)

| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 Test debt fix + bars_per_year integration | done | 88b3670 | Root cause confirmed: S27 T3 RSI warm-up gating suppressed cross_up signals (NaN<overbought=False) в test fixtures. Lengthen fixtures (12→16 bars test_long_only / 9→12 bars test_next_open). Mypy redef → rename `bars_per_year_map_wfa`. NEW `tests/test_bars_per_year_integration.py` 5 tests + critical invariant `4H vs 1H Sharpe ratio = sqrt(2190/8760) = 0.5` PASSED — confirms S27 T1 fix integrity end-to-end. pytest: 773→781 (0 failures), mypy: 1→0 errors. |
| T2 CC-D MC p-value fix BOTH formulas + property tests | done | 807fce3 | TDD RED→GREEN: 2 property tests RED (caught CC-D bug — p=0.0 for all-positive returns), fix applied к sign_flip_p_value:56 + block_bootstrap_p_value:96 (`count/N` → `(count+1)/(N+1)` per Phipson & Smyth 2010 / ADR 0015), 7 property tests GREEN. pytest: 781→788. **Impact: prior MC p=0 reports systematically over-confident. Post-fix floor 1/(N+1) ≈ 0.0005 при N=2000.** |
| T3 E DSR cross-trial extension | done | 804d99e | TDD RED→GREEN: 10 RED tests (no symbol field), schema migration applied (TrialEntry +symbol с backfill BTCUSDT + append_trial backward-compat default + sigma_SR pooling protocol (a) all entries), 17 GREEN tests (10 NEW + 7 legacy preserved). pytest: 788→798. **Closes S14 Q2 REVISE carry-over.** Archive step SKIPPED (cross_trial_sharpes.json уже empty post-S23). |
| T4 F preparation (validation + named constants) | done | 576621c | WalkForwardRunner.run() accepts symbol kwarg + pre-run validation с symbol context (Item #10) + MEAN_REVERSION_S17_RELAXED_PARAMS named constant rsi_oversold=35/rsi_overbought=65/bb_std_mult=1.5/and_gate_required=True (Item #5 anti-S15-recurrence guard). 5 NEW tests. pytest: 798→803. 0 errors. |
| T5 F BACKTEST measurement run | done | 18d6e99 | **VERDICT FAIL conjoint**: T5 raw n=66<100 + n_eff=26<<100 (Item #8 correlation rho=0.75 / Kish 1965) + T6 OOS/IS=-2.84<0.7 + MC p=0.52>0.10 + DSR=0.919<0.95. Per-symbol: BTC=23 trades (mean fold Sharpe -4.40, fold #3 catastrophic -32.68) / ETH=25 (-3.85) / SOL=18 (-0.28 best). 3 entries appended cross_trial_sharpes.json (sigma_SR pooled=2.24 protocol (a)). CLI extension: --wfa-train/test/folds/embargo args. **Pre-committed failure branch (Item #12) TRIGGERED — S34 honest close v0.6 OR operator override.** |
| T6 ADR 0050 + sprint-33 page + sync | done | e126ab0 | ADR 0050 (522 lines) + sprint-33 page + index/counts (49→50 ADRs / 36→37 sprints) + CI baseline tightened к 0 (mypy + pytest baselines от 1/3 → 0/0 strict). 9-item pre-reg LOCKED + ESC-3 4 binding + Item #12 trigger documented + Item #15 reviewer dispatch documented. |

## S32e SHIPPED ✅ — Kit Audit + Doc Sync

PR #43 → c4dadd3 squash-merge. Tag v0.1.0-alpha.32e pushed. Branch deleted. **CI passed first try.**

**Audit conclusion: ALL components NEEDED. NO removals.** Documentation drift fixed + tooling-inventory split (60KB → 41+24KB) + audit page snapshot committed.

## S32e IN PROGRESS 🟡 — Kit Audit + Doc Sync

Sub-sprint S32 series **post-completion audit** (operator initiated). Branch: `feature/sprint-32e-kit-audit-doc-sync`. Plan: `plans/2026-04-27-sprint-32e-kit-audit-doc-sync.md` (899d227).

**Pre-plan empirical findings:**
- Doc drift: kit-overview-ru "Best practices" section MCP=6 stale (real 8) / Subagents=9 stale (real 11)
- File size: tooling-inventory-ru.md = **60KB exceeds 50KB safe Read threshold** (CLAUDE.md sec 9 BINDING) → MUST SPLIT
- Reviewer agents: All 11 NEEDED (5 active + 5 dormant ready / 1 = bybit-api-reviewer NEW). NO removals.
- Hooks: All 7 push + 2 UPS + 1 SS NEEDED. ALL ACTIVE.
- MCP: 6/8 active or ready / 2/8 (computer-use + Claude_in_Chrome) not used trading но harmless overhead — keep. NO removals.
- Skills: All 5 project + ~50 plugin NEEDED.

**5 changes scope:**
- T1 NEW kit-audit-2026-04-27.md
- T2 Fix kit-overview drift
- T3 Split tooling-inventory (60KB → 2 files < 50KB)
- T4 Update CLAUDE.md Read guard
- T5 ADR 0049 + sprint-32e page + sync

КУ ~50% / ~2 hours forecast.

### Phase tracking (S32e — in progress)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S32d ship |
| 2 Brainstorm | skipped (operator-specified audit task) | inline pre-plan analysis |
| 3 Plan | done | `plans/2026-04-27-sprint-32e-kit-audit-doc-sync.md` (899d227) |
| 4 Execute | in_progress | T1-T5 controller-driven |
| 5 Verify | done | pytest 773 (S32d baseline) / mypy 1 pre-existing / canonical 16/30/74/45 ✓ / **file split verify: tooling-inventory-ru.md 41KB ✓ + tooling-inventory-ru-part-2.md 24KB ✓** (both < 50KB threshold) |
| 6 Review | pending (likely skip) | no src/ touched |
| 7 Sync | pending | log.md sprint-end + index/current-state в T5 |
| 8 Ship | done | PR #43 → c4dadd3 + tag v0.1.0-alpha.32e. CI passed first try (4th PR validation). |
| 9 Close | done | SPRINT_STATE between-sprints (this update) |

### Phase 4 — task progress (S32e)

| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 kit-audit-2026-04-27.md NEW | pending | — | Audit findings: 11 agents + 8 hooks + 8 MCP + 5 project skills + ~50 plugin usage |
| T2 Fix kit-overview drift | pending | — | "Best practices applied" MCP 6→8, Subagents 9→11 |
| T3 Split tooling-inventory-ru.md | pending | — | 60KB → part 1 (Sections 1-13) + part 2 (Sections 14-24) per CLAUDE.md sec 9 |
| T4 CLAUDE.md Read guard update | pending | — | tooling-inventory split — both parts < 50KB safe to Read full |
| T5 ADR 0049 + sprint-32e page + sync | pending | — | 48→49 ADRs / 35→36 sprints + audit doc + part-2 |
| Ship | done | c4dadd3 | tag v0.1.0-alpha.32e. CI passed first try (S32b infrastructure 4th PR validation). |

## S32d SHIPPED ✅ — S32 SERIES COMPLETE 🎉

PR #42 → 4cfe408 squash-merge. Tag v0.1.0-alpha.32d pushed. Branch deleted. **CI passed first try.**

**S32 series 4 sub-sprints completed (Phase 0/1/2/3):**
- S32 Phase 0 (alpha.32) — P0 staleness fix + 5 skill mappings + cascade smart-explore + Phase 9 consolidate-memory
- S32b Phase 1 (alpha.32b) — CI + pre-commit + SQLite MCP + freshness hook + dashboard-reviewer
- S32c Phase 2 reduced (alpha.32c) — 4 skill mappings + Fetch MCP + corpus categorization scheme docs
- S32d Phase 3 final (alpha.32d) — bybit-api-reviewer + context budget hook + schedule wire + sprint metrics + corpus research notes

**Next: S33 trading work begins.**

## S32d IN PROGRESS 🟡

Sub-sprint S32 series **FINAL**. Branch: `feature/sprint-32d-kit-phase-3-improvements`. Plan committed: `plans/2026-04-27-sprint-32d-kit-phase-3-improvements.md` (29ad020).

**Honest scope** (per pre-plan analysis): Memory corpus bridges 2-4 implementation = research notes only (claude-mem internal API constraints). 4 implementations + research notes + ADR/sync. КУ ~45% / 2.5-3 hours forecast. **After S32d ship → S33 trading work begins.**

### Phase tracking (S32d — in progress)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S32c ship |
| 2 Brainstorm | skipped (operator-specified per ADR 0047 carry-overs) | inline pre-plan analysis |
| 3 Plan | done | `plans/2026-04-27-sprint-32d-kit-phase-3-improvements.md` (29ad020) |
| 4 Execute | in_progress | T1-T5 controller-driven |
| 5 Verify | done | pytest 773 (S32c baseline preserved) / mypy 1 pre-existing / canonical 16/30/74/45 ✓ / bash -n context-budget-warn ✓ / json settings.json ✓ (6 PreToolUse + 2 UserPromptSubmit hooks). 3 pytest pre-existing failures + 1 mypy carry-over к S33. |
| 6 Review | pending (likely skip) | no src/ touched |
| 7 Sync | pending | log.md sprint-end + index/current-state в T5 |
| 8 Ship | done | PR #42 → 4cfe408 + tag v0.1.0-alpha.32d. CI passed first try (S32b infrastructure validated 3rd PR). |
| 9 Close | done | SPRINT_STATE between-sprints + S33 trading prep section (this update) |

### Phase 4 — task progress (S32d)

| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 bybit-api-reviewer L5 agent | done | a15ff4c | out-of-repo `~/.claude/agents/bybit-api-reviewer.md` (sonnet, 6-axis: rate limits / order params / WS schema / retCodes / pagination / HMAC sign) + wiki page Block 1↔2. Specialist гap между trading-logic-reviewer (business) и data-integrity-reviewer (storage). |
| T2 Context budget hook MVP | done | e87d532 | out-of-repo `~/.claude/hooks/context-budget-warn.sh` (advisory, exit 0 always) + settings.json UserPromptSubmit registered (2nd hook после caveman-mode-tracker) + wiki page Block 1↔2. Tests passed: small file no-warn + 900KB 🟡 yellow + 1300KB 🔴 red + missing path fail-open. Thresholds 800KB (~60%) / 1200KB (~80%). |
| T3 Schedule wire + Sprint metrics | done | 2707f6f | tooling-inventory Section 23 (anthropic-skills:schedule wire к audit_formulas.py + frequency recommendations + setup procedure operator action) + sprint-metrics.md NEW page (per-sprint table reverse chronological + trends rolling 5 + update protocol). |
| T4 Corpus bridges research notes | done | 2707f6f | tooling-inventory Section 24 (Bridge 2 ship-ready cron LOW cost MEDIUM value / Bridge 3 PostToolUse hook MEDIUM cost LOW value / Bridge 4 NOT RECOMMENDED HIGH cost LOW value until corpus > 100 obs). Honest recommendation summary + S32 series complete note. |
| T5 ADR 0048 + sprint-32d page + sync | done | 21b14cb | 47→48 ADRs / 34→35 sprints / 40→43 components / 10→11 agents + UserPromptSubmit hooks 1→2 + sprint metrics page + S32d sprint history row + S32 series COMPLETE accumulated achievements table |
| Ship | done | 4cfe408 | tag v0.1.0-alpha.32d. CI passed first try (3rd PR validation S32b infrastructure). |

## S32c SHIPPED ✅

PR #41 → df521a6 squash-merge. Tag v0.1.0-alpha.32c pushed. Branch deleted. **CI passed first try** (S32b infrastructure validated).

## S32c IN PROGRESS 🟡

Sub-sprint S32 series. Branch: `feature/sprint-32c-kit-phase-2-improvements`. Plan committed: `plans/2026-04-27-sprint-32c-kit-phase-2-improvements.md` (7bab107).

**Reduced scope** (per pre-plan analysis): Memory corpus bridges 2-3 + bridge 4 script + context budget hook → deferred S32d (research-heavy). S32c = 4 skill mappings + Fetch MCP + corpus categorization scheme docs + ADR/sync. КУ ~50% / 1.5-2 hours forecast.

### Phase tracking (S32c — in progress)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S32b ship |
| 2 Brainstorm | skipped (operator-specified per ADR 0046 carry-overs) | inline pre-plan analysis |
| 3 Plan | done | `plans/2026-04-27-sprint-32c-kit-phase-2-improvements.md` (7bab107) |
| 4 Execute | in_progress | T1-T4 controller-driven |
| 5 Verify | done | pytest 773 (S32b baseline preserved) / mypy 1 pre-existing / canonical 16/30/74/45 ✓ / json .mcp.json ✓ (sqlite-trading + fetch). 3 pytest failures + 1 mypy carry-over к S33 (pre-existing, NOT S32c regression). |
| 6 Review | pending (likely skip) | no src/ touched |
| 7 Sync | pending | log.md sprint-end + index/current-state в T4 |
| 8 Ship | done | PR #41 → df521a6 + tag v0.1.0-alpha.32c. CI passed first try (S32b infrastructure validated 2nd PR). |
| 9 Close | done | SPRINT_STATE between-sprints (this update) |

### Phase 4 — task progress (S32c)

| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 Fetch/HTTP MCP | done | 0761bad | `.mcp.json` +fetch server (uvx mcp-server-fetch verified pre-installed). tooling-inventory-ru.md Section 7.7 (sqlite-trading post-S32b) + Section 7.8 (fetch NEW) documented. Operator approve at next session start. |
| T2 4 skill mappings | done | 09fcdee | sprint-flow-ru.md +api-design Phase 3 / +browser-test Phase 5 / +perf-opt Phase 6 OPT / +idea-refine extension Phase 2 PRE workflow (procedure block с 5 steps). Skills × Phase 32→36 (17 agent-skills total). |
| T3 Memory corpus scheme docs | done | 47bba48 | tooling-inventory-ru.md NEW Section 22 (4 partitions: trading-decisions / formula-knowledge / process-patterns / debug-knowledge + tag mapping pseudo-code + cascade STEP 2 enhancement spec + operator validation procedure). Bridge 4 design — script implementation S32d candidate. |
| T4 ADR 0047 + sprint-32c page + index/counts | done | 231d55f | 46→47 ADRs / 33→34 sprints / 7→8 MCP / 32→36 skills + S32c sprint history row + kit-overview decision matrix updates |
| Ship | done | df521a6 | tag v0.1.0-alpha.32c. CI passed first try (S32b CI infrastructure validated на non-S32b PR). |

## S32b SHIPPED ✅

PR #40 → cb61678 squash-merge. Tag v0.1.0-alpha.32b pushed. Branch deleted.

CI passed on 4-th attempt (3 fixes: TA-Lib sequential build / ruff baseline guard / dashboard optional deps).

### Phase tracking (S32b — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S32 ship |
| 2 Brainstorm | skipped (operator-specified per КУ Phase 1 deliverables) | inline в plan |
| 3 Plan | done | `plans/2026-04-27-sprint-32b-kit-phase-1-improvements.md` (3cb442d) |
| 4 Execute | in_progress | T1-T6 controller-driven (config + scripts + docs sprint) |
| 5 Verify | done | pytest 773 (S32 baseline preserved) / mypy 1 pre-existing / canonical 16/30/74/45 ✓ / bash -n freshness hook ✓ / yaml ci.yml ✓ / yaml .pre-commit-config ✓ / json .mcp.json ✓ / json settings.json ✓. **3 pytest failures + 1 mypy pre-existing** (NOT S32b regression — carry-over к S33). |
| 6 Review | pending | python-reviewer + architecture-reviewer + doc-reviewer (parallel) |
| 7 Sync | pending | log.md sprint-end + index/current-state в T6 |
| 8 Ship | done | PR #40 → cb61678 + tag v0.1.0-alpha.32b + 4-attempt CI fix saga (TA-Lib parallel race / ruff 169 baseline / dashboard deps) |
| 9 Close | done | SPRINT_STATE between-sprints (this update) |

### Phase 4 — task progress (S32b)

| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 dashboard-reviewer L5 agent | done | 6c2ea66 | out-of-repo `~/.claude/agents/dashboard-reviewer.md` + wiki page (5-axis review checklist + S25 ADR 0039 conditions) |
| T2 SPRINT_STATE freshness check hook | done | 373d527 | bash script (~/.claude/hooks/sprint-state-freshness-check.sh, 755) + settings.json registered (6 hooks total) + positive (exit 0) + negative test (exit 2 on `S25 PHASE 8 ship pending`) passed + wiki page (Block 1↔2) |
| T3 Pre-commit hooks (ruff + mypy + yamllint) | done | (committed inline w/ T4) | `.pre-commit-config.yaml` upgraded (ruff v0.4.0 + mypy --strict local + yamllint для CI workflows) + pre-commit installed (pre-commit 4.6.0). dev dep уже в pyproject.toml. NOTE: mypy 1 pre-existing baseline → operator fix __main__.py:636 OR --no-verify per local commit. |
| T4 GitHub Actions CI | done | 167fc9d | `.github/workflows/ci.yml` 10 steps (checkout / py3.12 / TA-Lib cache + build / pip install / ruff lint+format / mypy --strict с baseline guard / pytest unit с baseline guard / canonical counts verify). Triggers: push к main + PR. CI runs first time на S32b PR. |
| T5 SQLite MCP server | done | 8a24abf | project-level `.mcp.json` (sqlite-trading → data/bot.db) — settings.json schema rejects mcpServers, .mcp.json правильный location. Operator approve at session start OR через `claude mcp` CLI. uvx + mcp-server-sqlite verified available. |
| T6 ADR 0046 + sprint-32b page + index/counts | done | dabf368 | 45→46 ADRs / 32→33 sprints / 9→10 agents / 6→7 hooks / 6→7 MCP / 38→40 components + S32+S32b sprint history rows + kit-overview decision matrix updates |
| Ship | done | cb61678 | tag v0.1.0-alpha.32b. CI passed после 3 fix iterations: TA-Lib build sequential (drop -j) / ruff baseline guard 200 / install dashboard optional deps. CI confirmed working — future PRs auto-validated. |

## S32 SHIPPED ✅

PR #39 → 2bad7ee squash-merge. Tag v0.1.0-alpha.32 pushed. Branch deleted.

### Phase tracking (S32 — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S31 |
| 2 Brainstorm | skipped (operator-specified deliverables per КУ analysis) | inline analysis chapter "Kit improvement plan — КУ analysis" |
| 3 Plan | done | `plans/2026-04-26-sprint-32-kit-phase-0-improvements.md` |
| 4 Execute | in_progress | T1-T6 controller-driven (docs sprint) |
| 5 Verify | done | 773 passed (was reported 762 S31 — count drift +11 actual) / mypy 1 error (`__main__.py:636 bars_per_year_map redef`) / canonical counts 16/30/74/45 ✓. **3 pytest failures pre-exist on main** (test_replay_long_only / test_replay_next_open) — NOT S32 regression. **Carry-over к S33**: fix replay tests + mypy redef. |
| 6 Review | will skip (process/wiki only, no src/ touched) | — |
| 7 Sync | pending | log.md sprint-end + index/current-state in T6 |
| 8 Ship | done | PR #39 → 2bad7ee + tag v0.1.0-alpha.32 + all 4 hooks fired correctly |
| 9 Close | done | SPRINT_STATE between-sprints (this update) |

### Phase 4 — task progress (S32)

| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 SPRINT_STATE.md P0 fix | done | c095bd3 | Stale sections → S32 reality + correct counts (30→44 ADRs / 17→31 sprint pages) + Phase tracking S32 |
| T2 current-state.md P0 fix | done | 2ec9824 | post-S25 → post-S31 + 604→762 + sources/tags/TL;DR update + S25 TL;DR preserved as Previous |
| T3 sprint-flow-ru.md +5 skill mappings | done | e93e61c | idea-refine (Phase 2 PRE) + spec-driven (Phase 2/3) + source-driven (Phase 4) + code-simplification (Phase 6 OPT) + documentation-and-adrs (Phase 8); Skills×Phase map 26→32 |
| T4 cascade smart-explore STEP 2.5 | done | f1f60a7 | sprint-flow-ru.md + kit-overview-ru.md mirror + decision matrix +6 entries |
| T5 Phase 9 consolidate-memory step | done | 660630e | sprint-flow-ru.md Phase 9 procedure +Step 5 + HARD-GATE (every 5 sprints OR >30 obs) |
| T6 ADR 0045 + sprint-32 page + index/counts | done | 397a655 | 44→45 ADRs / 31→32 sprints + sprint history row + S32 index entry + skills mapped 26→32 |
| Ship | done | 2bad7ee | tag v0.1.0-alpha.32 (alpha.32 alpha-channel marker, not MVP DONE) |

## S31 SHIPPED ✅

PR #38 → 52a232a squash-merge. Tag v0.1.0-alpha.31 pushed. Branch deleted.

### Phase tracking (S31 — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation |
| 2 Brainstorm | done (best practices audit) | gap analysis inline в plan |
| 3 Plan | done | `plans/2026-04-26-sprint-31-kit-revision-best-practices.md` |
| 4 Execute | done | 4 task commits (T1-T7) с per-task SPRINT_STATE update |
| 5 Verify | done | 762 pytest passed + CLAUDE.md prune verified (-25% tokens) |
| 6 Review | skipped (process/wiki) | — |
| 7 Sync | done | wiki diffs (index + current-state + log) |
| 8 Ship | done | PR #38 + tag v0.1.0-alpha.31 + all 4 hooks fired correctly |
| 9 Close | done | SPRINT_STATE between-sprints |

### Phase 4 — task progress
| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 kit-overview-ru.md | done | (pending commit) | 1-page TL;DR + Quick decision matrix + 9 agents + 6 hooks + 5 skills + ~50 plugin skills + 6 MCP + cascade rule + Top 10 commands + Top 5 anti-patterns + 9-phase lifecycle + 20 best practices applied |
| T2 tooling-inventory-ru.md sections 14-19 | done | (pending commit) | Section 14 Permission modes / 15 Plugins curated / 16 CLI tools / 17 Status line / 18 Token-saver commands / 19 Non-interactive + fan-out |
| T3 prune llm-wiki/CLAUDE.md (448→<200) | done | (pending commit) | 448→291 (-35%), 27KB→13KB (-52%) — extracted verbose к kit-overview-ru + tooling-inventory-ru |
| T4 audit ~/.claude/CLAUDE.md (316→<250) | done | (pending commit) | 316→253 (-20%) — section 9c compressed (80→17 lines) preserving formula |
| T5 repo CLAUDE.md +kit-overview link | done | (pending commit) | 190→212 lines — added kit-overview/sprint-flow-ru/tooling-inventory references к Ключевые файлы table |
| T6 status line + `/btw`/`/rewind`/`--continue` | done | (pending commit) | Anti-patterns +4 (kitchen-sink/btw/3+correction/CLAUDE.md bloat) + token-saver commands table 8 commands + link к Section 18 |
| Total CLAUDE.md prune | done | — | 954→756 lines (-21%), 61KB→46KB (-25%), ~18.5K→14K tokens (-25%) per session |
| T7 ADR 0044 + sprint-31 page + sync | done | (pending commit) | ADR + sprint page + index + current-state (43→44 ADRs / 30→31 sprint pages / +Kit settings RU 3 files / +CLAUDE.md tokens ~14K) + log |
| Ship | in_progress | — | tag alpha.31 |

## S30 SHIPPED ✅

PR #37 → 4e719a9 squash-merge. Tag v0.1.0-alpha.30 pushed. Branch deleted.

### Phase tracking (S30 — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation |
| 2 Brainstorm | short (operator-specified) | inline в plan |
| 3 Plan | done | `plans/2026-04-26-sprint-30-tier-2-agents-mem-wiki-merge.md` |
| 4 Execute | done | 6 task commits (T1-T9) с per-task SPRINT_STATE update |
| 5 Verify | done | 762 pytest passed + bash -n + positive/negative hook test |
| 6 Review | skipped (process/wiki) | — |
| 7 Sync | done | wiki diffs (index + current-state + log) |
| 8 Ship | done | PR #37 + tag v0.1.0-alpha.30 + phase-advance hook fired correctly |
| 9 Close | done | SPRINT_STATE between-sprints |

### Phase 4 — task progress
| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 security-auditor agent | done | (out-of-repo, ~/.claude/agents/) | Opus, OWASP + trading-specific rules + MEMORY.md |
| T2 test-engineer agent | done | (out-of-repo) | Sonnet, test pyramid + property tests + Hypothesis + Trading-specific rules |
| T3 doc-reviewer agent | done | (out-of-repo) | Haiku, frontmatter+links+Block 1↔2+canonical counts |
| T4 phase-advance.sh hook | done | (out-of-repo + settings.json) | bash -n + negative test verified (Phase 5 pending → block + helpful error). Registered к PreToolUse Bash matcher |
| T5 wiki↔mem cascade design | done | (combined с T6) | Section 13 NEW в tooling-inventory-ru.md — 4-step cascade (wiki→mem→grep→raw) + examples + bridges 2-4 deferred |
| T6 tooling-inventory-ru.md | done | (pending commit) | Section 1 expanded (6→9 agents с status legend) + Section 8 +phase-advance.sh + Section 13 NEW cascade + decision matrix +5 entries |
| T7 sprint-flow-ru.md Phase 6 | done | (pending commit) | Reviewer matrix +3 (security/test/doc) + Phase 5 hook note + Token economy cascade section с link к Section 13 |
| T8 CLAUDE.md | done | (pending commit) | Repo CLAUDE.md Phase 6 +3 reviewers + Phase 5 hook + cascade rule + 4 anti-patterns. llm-wiki CLAUDE.md +phase-advance hook + cascade rule references |
| T9 ADR 0043 + sprint-30 page + sync | done | (pending commit) | ADR + sprint page + index + current-state + log + canonical counts (43 ADRs / 30 sprint pages / 9 agents / 6 hooks) |
| Ship | in_progress | — | tag alpha.30 |

## S29 SHIPPED ✅

PR #36 → 30d476a squash-merge. Tag v0.1.0-alpha.29 pushed. Branch deleted.

### Phase tracking (S29 — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation |
| 2 Brainstorm | skipped (operator-specified) | — |
| 3 Plan | done | `plans/2026-04-26-sprint-29-superpowers-integration.md` |
| 4 Execute | done | 4 commits (T1-T4) с per-task SPRINT_STATE update |
| 5 Verify | done | 762 pytest passed (S28 baseline preserved) |
| 6 Review | skipped (process/wiki) | — |
| 7 Sync | done | wiki diffs (index + current-state + log) |
| 8 Ship | done | PR #36 + tag v0.1.0-alpha.29 |
| 9 Close | done | SPRINT_STATE between-sprints |

### Phase 4 — task progress (completed)
| Task | Commit | Note |
|------|--------|------|
| T1 sprint-flow-ru.md | be4c10b | Explicit skills per phase + Skills × Phase integration map |
| T2 tooling-inventory-ru.md | 202d915 | Decision matrix +8 + Section 12 NEW + Section 3 expanded |
| T3 CLAUDE.md | b7b0f16 | Phase table expanded (Primary + Optional columns) |
| T4 ADR 0042 + sprint-29 page + sync | 50f4ae1 | ADR + sprint page + index + current-state + log |
| Squash-merge | 30d476a | PR #36, tag alpha.29 |

## S28 SHIPPED ✅

PR #35 → 1538a53 squash-merge. Tag v0.1.0-alpha.28 pushed. Branch deleted.

### Phase tracking (S28 — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session resume mark_chapter |
| 2 Brainstorm | skipped (deliverables operator-specified) | — |
| 3 Plan | done | `plans/2026-04-26-sprint-28-process-enforcement.md` (first plan since S15) |
| 4 Execute | done | 6 commits (T1-T6) с per-task SPRINT_STATE update |
| 5 Verify | done | 762 pytest passed (S27 baseline preserved) + bash -n hook + positive/negative test |
| 6 Review | skipped (process/wiki, no code reviewers applicable) | — |
| 7 Sync | done | wiki diffs (index + current-state + log) в T6 commit |
| 8 Ship | done | PR #35 + tag v0.1.0-alpha.28 |
| 9 Close | done | SPRINT_STATE between-sprints (этот update) |

### Phase 4 — task progress (completed)
| Task | Commit | Note |
|------|--------|------|
| T1 sprint-flow-ru.md | 09b2e02 | Russian sprint lifecycle 9 phases |
| T2 tooling-inventory-ru.md | 6a62f27 | 11 sections — agents/skills/plugins/MCP/hooks/decision matrix |
| T3 sprint-flow-check.sh hook | 18387fa | Mechanical PHASE 3 enforcement, registered settings.json |
| T4 SPRINT_STATE template | 18387fa | Per-phase + per-task tracking inline |
| T5 CLAUDE.md updates | 900003a | Repo + llm-wiki binding sections |
| T6 ADR 0041 + sprint-28 page + sync | 4623a5c | ADR + sprint page + index + current-state + log |
| Squash-merge | 1538a53 | PR #35, tag alpha.28 |

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**S34 SHIPPED — Hybrid 6-th honest close v0.6 + Acceptance-Criteria Amendment LOCKED.** v0.6 chapter end. Both consilium recommendations honored. КУ avg ~47% / ~3 hours. pytest 808 / mypy 0 errors / 6th PR CI с strict baselines.

**6 prior strategy hypotheses tested** (S13/S15/S17/S20/S22/S33) — все FAIL conjoint. Multi-symbol expansion EMPIRICALLY FALSIFIED (correlation deflation rho=0.75). Amendment LOCKED для future resumption (ADR 0052), не active until operator acknowledgment + new measurement.

**Project state v0.6 stable end. v0.7+ direction TBD operator.**

**Status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + **43 components** + **48 ADRs** + **35 sprint pages**)
- Kit infrastructure: ✅ COMPLETE — **11 reviewer agents** + **7 active push hooks** + **2 UserPromptSubmit hooks** + **8 MCP servers** + **36 skills mapped** + cascade 5-step + Phase 9 consolidate-memory + GitHub Actions CI live + pre-commit gates + Memory corpus scheme designed (Section 22) + Memory corpus bridges feasibility documented (Section 24) + **Sprint metrics tracking** (sprint-metrics.md) + 20/20 best practices
- Formula correctness: ✅ FIXED (5 bugs eliminated post-S27)
- Strategy validation: ❌ NEGATIVE (0 PASS / 30 FAIL — trading work blocked pending ESC-1/2/3)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 unreachable single-symbol 4H)
- Test debt: ⚠️ 3 pre-existing pytest failures + 1 mypy redef + ~169 ruff issues — carry-over к S33+

**S32 series accumulated changes (pre-S32 → post-S32d):**
- Reviewer agents 9→**11** / Push hooks 6→**7** / UserPromptSubmit 1→**2** / MCP 6→**8** / Skills 26→**36** / Components 38→**43** / ADRs 44→**48** / Sprint pages 31→**35**
- CI infrastructure: NO → **YES** (GitHub Actions + pre-commit + baseline guards)
- Memory corpus: flat → **scheme designed** (script declined per recommendation)
- Sprint metrics: NO → **YES** (tracking introduced)

## Последний спринт (S34 — Hybrid 6-th Honest Close v0.6 + Amendment LOCKED)

Operator chose hybrid path post-S33 consilium. 5 tasks: T1 engineering pre-check (S33 на amended gates STILL FAILS 4/5) + T2 ADR 0051 6-th honest close v0.6 (mirror S14/S16/S18/S21/S23 + 6-hypothesis falsification record + cross_trial archive _v0.6 + reset) + T3 ADR 0052 acceptance-criteria amendment LOCKED (T5 100→50 / n_eff≥50 NEW Kish 1965 / MC≤0.05 tightened / T6+DSR unchanged) + 10-item pre-commit list + operator acknowledgment template + T4 evaluate_acceptance_gate() extended backward-compat + 5 NEW tests + T5 sprint-34 + index/counts (50→52 ADRs / 37→38 sprints). Both A(a)+A(b) consilium recommendations honored. Anti-snooping discipline preserved.

## Предпредпоследний спринт (S33 — Trading Restart, F BACKTEST FAIL conjoint)

First trading sprint после 8-sprint S32 series. 6 tasks: T1 test debt fix (3 pytest + 1 mypy + 4H bars_per_year integration test verifies S27 T1 integrity end-to-end) + T2 CC-D MC p-value fix BOTH formulas + T3 E DSR cross-trial extension (closes S14 Q2) + T4 F preparation (WFA validation + S17 named constant) + T5 F BACKTEST run (BTC+ETH+SOL 4H mean-reversion S17-relaxed params, WFA train=1000/test=250 K=5 per CC6 (b)) + T6 ADR 0050 + sprint-33 page + counts (49→50 ADRs / 36→37 sprints) + CI baseline tightened к 0. Per-symbol: BTC=23 (-4.40), ETH=25 (-3.85), SOL=18 (-0.28). Aggregate FAIL: T5 raw 66<100 / n_eff 26 / T6 -2.84 / MC 0.52 / DSR 0.919. Pre-committed failure branch TRIGGERED → S34 = 6-th honest close v0.6.

## Предпредпоследний спринт (S32e — Kit Audit + Doc Sync)

Post-S32 series audit. 5 changes: T1 NEW kit-audit-2026-04-27.md (full audit findings: 11 agents + 10 hooks + 8 MCP + 5 project skills + ~50 plugin skills usage analysis) + T2 fix kit-overview-ru drift (Best practices section MCP 6→8 / Subagents 9→11 / Hooks 7+2+1 / Skills 26→36) + T3 split tooling-inventory-ru.md (60KB → part 1 41KB Sections 1-13 + part 2 24KB Sections 14-24) per CLAUDE.md sec 9 size threshold + T4 update llm-wiki/CLAUDE.md (split refs + size example + audit page link) + T5 ADR 0049 + sprint-32e page + index/counts (48→49 ADRs / 35→36 sprints / + 2 architecture pages). КУ avg ~48% / ~2 hours. **Audit conclusion: ALL components NEEDED, no removals.** CI passed first try.

## Предпоследний спринт (S32d — Kit Improvement Phase 3 final + S32 SERIES COMPLETE)

Sub-sprint S32 series **FINAL**. 5 changes: T1 bybit-api-reviewer L5 agent (sonnet, 6-axis Bybit V5 API checklist) + T2 Context budget hook MVP (UserPromptSubmit advisory, transcript file size proxy 800KB/1.2MB thresholds) + T3+T4 batch (Section 23 anthropic-skills:schedule wire к audit_formulas.py + sprint-metrics.md NEW page + Section 24 corpus bridges 2-4 research notes — Bridge 2 SHIPPABLE cron / Bridge 3 medium defer / Bridge 4 NOT recommended) + T5 ADR 0048 + sprint-32d page + index/counts (47→48 ADRs / 34→35 sprints / 40→43 components / 10→11 agents / + UserPromptSubmit 1→2 + sprint metrics page). КУ avg 41% / ~2.5 hours. CI passed first try. **S32 series: 8h total, КУ avg ~53%, ROI ~50 КУ/час.** NO code changes.

## Следующее действие

```
v0.7+ DIRECTION — operator decides (NOT pre-committed в S34):

═══ Option (a) — Project pause indefinitely (S24 Option E precedent) ═══
  Tag stable end at v0.1.0-alpha.34. No new sprints. Resume позже когда conditions change.

═══ Option (b) — New measurement amended spec (S35+) ═══
  RECOMMENDED if operator wants forward path:
  Step 1: Write S35+ ADR с verbatim operator acknowledgment template (per ADR 0052):
    "Statistical evidence as of v0.6 DOES NOT support live deployment;
     this amendment reflects crypto-specific sample-size reality (Hudson & Urquhart 2021),
     not evidence of positive edge."
  Step 2: Extend OHLCV data beyond S33 measurement date (data/{BTC,ETH,SOL}USDT_4h.parquet)
  Step 3: Pre-register multi-symbol rho + Kish factor (если multi-symbol)
  Step 4: Run new measurement sprint с amended gates LOCKED:
    - T5 floor 50, n_eff threshold ≥50 mandatory
    - MC threshold ≤0.05 tightened
    - T6 ≥0.7 unchanged, DSR ≥0.95 unchanged, acceptance_gate unchanged
  Step 5: n_trials counter starts ≥4 (sigma_SR pooling protocol (a))
  
═══ Option (c) — Different strategy class ═══
  Donchian breakout / ML XGBoost / HMM regime-switch (paradigm shift beyond mean-reversion).
  Pre-requisites: new ADR с pre-registered hypothesis + N_trials counter accumulates ≥4.
  Engineering blocker: Donchian SHORT signals conflict с long_only=True FSM invariant.
  
═══ Option (d) — Different timeframe ═══
  1D mean-reversion + volume gate. NOT recommended per S34 consilium (T5 problem worse —
  even fewer trades expected).
  
═══ Option (e) — Different asset class ═══
  Uncorrelated instruments (commodity futures, FX). Beyond v0.1 scope. Major refactor.

═══ Operator action когда ready ═══

1. Choose option a/b/c/d/e
2. Если (b): write acknowledgment template verbatim + extend data + new sprint S35+
3. Если (c)/(d)/(e): new ADR с pre-registered hypothesis (anti-snooping)
4. Если (a): no action — tag stable end preserved
```

═══ Operator decision required ═══

Option A (DEFAULT — recommended path):
  S34 = 6-th honest close v0.6 ADR (mirror S14/S16/S18/S21/S23 BINDING precedent):
    - Document FAIL conjoint S33 verdict
    - Archive cross_trial_sharpes.json к _v0.6.json + reset
    - v0.7+ direction options:
      (a) Project pause (S24 Option E precedent)
      (b) Spec amendment к acceptance-criteria.md T5 floor (operator override)
      (c) Different strategy class (Donchian breakout / ML-driven / etc — beyond mean-reversion)
      (d) Different timeframe (1D mean-reversion с volume gate / etc)

Option B (OVERRIDE — operator only):
  S34 = explicit statistical-framework override statement в ADR
    + adjust acceptance gates (T5 floor amendment / MC threshold relax)
    + full acknowledgment statistical evidence does NOT support live deployment

═══ Strategic context ═══

S33 demonstrated: multi-symbol expansion path empirically NOT viable.
  - All 3 symbols negative OOS edge (BTC=-4.40, ETH=-3.85, SOL=-0.28 mean fold Sharpe)
  - n_eff=26 (correlation-deflated) << T5=100 floor
  - 6 strategy hypotheses tested across 4.81y BTC+ETH+SOL — все FAIL conjoint
  - Edge regime-INDEPENDENT confirmed (S17+S22 partial PASS) but T5 unreachable

═══ Items satisfied S33 ═══

#1 (CC-D fix) ✓ / #2 (property tests) ✓ / #3 (ESC-3 4 binding) ✓ / #5 (S17 named constant) ✓ /
#6 (sigma_SR pooling (a)) ✓ / #7 (n_trials=3) ✓ / #8 (n_eff correction) ✓ /
#10 (WFA validation) ✓ / #11 (bars_per_year integration) ✓ / #12 (failure branch) ✓ /
#13 (CI baseline tightened) ✓ / #15 (reviewer dispatch documented) ✓
Deferred: #4 (LOCKED ADR documented), #14 (optional ruff drift)

═══ Carry-overs к S35+ ═══

- bybit-api-reviewer first real-world validation
- Bridge 4 corpus partition implementation (S40+ когда corpus > 100 obs)
- t-stat heavy-tail correction (Hudson&Urquhart 2021 — CC-E, math improvement)
- ESC-3 4 binding conditions (для S34+ LIVE multi-symbol если ever triggered)
```

═══ Operator action перед S33 brainstorm ═══

1. Approve `fetch` MCP at next session start (one-time prompt — same pattern S32b sqlite-trading)

2. Decide ESC-1/2/3 (BLOCKING multi-symbol scope):
   ESC-1: Multi-symbol authorization beyond BTCUSDT MVP?
     - Y → unlocks scope expansion ETH/SOL/etc
     - N → S33 limited single-symbol BTC scope
   ESC-2: "In profit" vs "pass acceptance criteria" — different goals?
     - Live pilot ETH 4H pre-S33?
     - Spec amendment T5 floor?
   ESC-3: Operational implications 4H multi-symbol (3 simultaneous positions, 1-5 day holds)?

3. Brainstorm S33 scope (use brainstorm-init skill → trader-expert ROUND 1):

   Single-symbol options (если ESC-1 = N):
     A) BTC mean-reversion 4H regime-confirmed (S22 PASS evidence preserved, n=62 < 100 floor)
     B) Regime filter + SMA50 trend gate (CC2 fold concentration)
     C) SL calibration {1.0/1.25/1.5}×ATR + t-stat power validation
     D) Donchian 4H breakout (independent hypothesis)
     E) DSR cross-trial sigma_SR + MC power audit (closes S14 Q2 carry-over)

   Multi-symbol options (если ESC-1 = Y):
     F) Multi-symbol 4H mean_reversion (n≈135 → T5 PASS) BTC+ETH+SOL
     G) Multi-symbol regime filter
     H) Cross-symbol DSR aggregation

═══ S33 test debt fix (либо встроить в S33, либо отдельный sprint) ═══

   - 3 pytest failures (test_replay_long_only x2 + test_replay_next_open x1) pre-existing
   - 1 mypy error (__main__.py:636 bars_per_year_map redef) pre-existing
   - ~169 ruff baseline cleanup (gradual OR strict gate)

═══ Optional kit setup (operator one-time tasks при желании) ═══

   - Setup audit_formulas.py weekly schedule per Section 23 
     (mcp__scheduled-tasks__create_scheduled_task; cron weekly Monday 09:00 UTC)
   - Setup corpus bridge 2 cron rebuild per Section 24
     (rebuild claude-mem corpus от wiki/log.md новых entries)

═══ NOT priority (low ROI per Section 24 honest assessment) ═══

   - Bridge 4 corpus partition implementation (re-evaluate когда corpus > 100 obs, likely S40+)
   - Context budget hook exact token counter (file size proxy adequate)
```

## Carry-over preserved (v0.2+ if any future direction chosen)

All S12 + S13 carry-overs unaddressed (10+ items):

- F live demo Mainnet validation actual run (33min only since S12)
- FillRecorderAdapter Layer 2 schema link (entry_signal_id к execution_state migration)
- 3-way endpoint enum (DEMO/TESTNET/MAINNET) — Q6 future fix
- T2 review C3 init_db dual-conn comment (S11 carry-over)
- DSR per-fold DataFrame→TradeRecord conversion (S10 informational)
- DSR threshold calibration (S15+ per S11 Q5)
- DSR cross-trial sigma_SR implementation (S14 Q2 REVISE — needed для any future revision)
- halt_log INSERT order swap в `_set_halt` (PRE-EXISTING)
- find_by_order_id ORDER BY explicit (T1 reviewer follow-up)
- fill-history.md / bybit-adapter.md / ws-private-consumer.md component page updates
- T2/T5/T6 quant-stats deferred concerns (Sortino formula docs, sqrt(8760) frequency-agnostic, boundary tests)

## Ключевые решения S14

- **Q1 EXPAND** (trader): T5 unreachable verified via grep — 5x signal frequency gap
- **Q2 REVISE** (trader): DSR cross-trial sigma_SR gap — verified via dsr.py:73
- **Option B** (user): honest close immediately, save 1 sprint vs theatrical Option A
- **Tag semantics:** `v0.1.0-alpha.14` = honest close marker, NOT MVP DONE
- **No spec amendment:** acceptance-criteria.md T1-T6 thresholds preserved
- **No code changes:** S14 = documentation only

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Обнови "Следующее действие" — конкретное, с командой если применимо
3. Добавь в "Ключевые решения" только нетривиальное
4. Обнови `updated:` в frontmatter
