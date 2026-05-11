---
title: Pre-S47 Backlog — tech debt + S46 carry-overs (NO new strategies)
type: backlog
tags: [sprint-47, tech-debt, carry-overs, s46-followup, honest-close]
created: 2026-05-11
updated: 2026-05-11
status: active
sources:
  - llm-wiki/wiki/project/SPRINT_STATE.md
  - llm-wiki/wiki/project/sprints/sprint-46-react-migration.md
  - llm-wiki/wiki/project/decisions/0066-sprint-46-react-migration.md
---

# Pre-S47 Backlog

## Контекст

**S46 SHIPPED** (v0.1.0-alpha.46): React 18 + Anthropic/cyberpunk + honest close UI piece. PHASE 6 5 reviewers complete. Operator binding 2026-05-11: **NO new strategies (Path B excluded)** — focus existing fixes/bugs.

**v0.1 trajectory:** S47 tech debt + carry-overs → S48 honest portfolio close ADR 0067 + v0.1 wrap-up → S49+ MAINNET-promotion ADR (если δ live data есть).

## S47 PHASE 2 Brainstorming Trail

### ROUND 1 (trader-expert)

| Q | Topic | Maintainer rec | Trader R1 verdict | Final |
|---|-------|----------------|-------------------|-------|
| Q1 | Scope priority | (a) PHASE 6 first | **CONFIRM** | (a) locked |
| Q2 | Bundle size | (a) ~14 tasks | **CONFIRM** + cut gate | (a) locked |
| Q3 | Honest close timing | (c) Split | **REVISE** → (b) full defer S48 | → ROUND 2 |
| Q4 | Vitest coverage scope | (b) Top 3 | **CONFIRM** | (b) locked |
| Q5 | M4 security timing | (a) S47 bundle | **REVISE** → (b) defer mainnet | → ROUND 2 |
| Q6 | v0.1 semver | (b) keep alpha | **CONFIRM** | (b) locked |

### ROUND 2 (trader-expert iterative justify on Q3 + Q5 disagreements)

| Q | ROUND 2 verdict | Final option |
|---|----------------|--------------|
| Q3 | **CONFIRM_REVISE** — option (b) full DEFER к S48 | (b) BINDING |
| Q5 | **CONFIRM_REVISE** — option (b) DEFER M4 к mainnet activation gate | (b) BINDING |

#### Q3 ROUND 2 evidence (CONFIRM_REVISE)

**Risks в (c) split (maintainer rec):**
1. Dead code / activation gap creates documentation divergence — ADR 0067 не существует в S47 (S48 deliverable). SPRINT_STATE wiki + code + ADR в трёх различных состояниях simultaneously
2. Monkeypatch test isolation gap real и не closeable в S47 — production scenario (11 real presets с `disabled=True`) never exercised до S48 flag flip

**Failure scenario для (c):** S47 ships infrastructure + 422 logic с `disabled=False`. S48 ADR 0067 scope grows OR delays. Result: dead code lives в `src/` 2+ sprints с zero observable effect. Future readers see `disabled=False` everywhere → conclude field unused → confusion accumulates.

**Why (b) wins:** atomic delivery — ADR 0067 + code enforcement + observable behavior all land same sprint. No intermediate state. Fits S48 estimate 8-10 tasks. No dead code в S47.

#### Q5 ROUND 2 evidence (CONFIRM_REVISE)

**Fresh research:** M4 (`__repr__` redaction) + M3 (isinstance guard) — оба в `src/execution/bybit/ws_private.py`. M1+M2 в `adapter.py` + `errors.py`. "Same-module touch" accurate для M3/M4 pair, но overstated для bundling всех four M-items.

**Risks в (a) bundle (maintainer rec):**
1. Sprint budget consumed для zero-risk-reduction в TESTNET trajectory. Expected value M4 в S47 = P(mainnet v0.1) × cost(api_secret leak) ≈ 0 × N = 0. 2-3h certain cost, benefit speculative
2. Bundling correctness fix (M3) с security hardening (M4) under one PR conflates two review categories — security-auditor over-audits M3 OR bybit-api-reviewer under-audits M4

**Failure scenario для (a):** M4 audited narrowly to `BybitPrivateWSConsumer.__repr__` only. `Settings` class (also holds api_key/secret via pydantic-settings) has own repr с possible exposure — secondary leak path goes unaudited because brief said "M4 = ws_private.py fix". Full `__repr__` audit requires reviewing ALL credential-holding classes.

**Why (b) wins:** defer until mainnet activation ADR formally gates it. Audit scope unambiguous (all credential-holding classes), real risk reduction (real keys at stake), then-current codebase audited. Zero waste S47.

### Cross-cutting concerns

- **CC1** Q3 defer removes ~2 tasks из S47 → backfill с one S37/S38 long-standing tech debt item (Item #10 boundary scenarios OR Item #7 RiskSharedDeps shim cleanup) — НЕ honest-close infrastructure (circular dependency)
- **CC2** Q5 PHASE 6 scope clarification — security-auditor brief MUST explicitly state: "M1-M3 only. M4 `__repr__` redaction OUT OF SCOPE until mainnet-activation ADR"
- **CC3** `backtest-flow.spec.ts` E2E stub (S46 SKIPPED) lands в S47 INDEPENDENTLY of Q3 — Playwright `page.route('/api/backtest', ...)` mock fixture, exercises existing 422 enforcement (locked_symbol, supported_combos)
- **CC4** MonthlyHeatmap `eslint-disable react-hooks/rules-of-hooks` — separate S47 linting task, NOT bundled с RTL test batch (1-line fix)

## S47 Scope (locked)

### In-scope (~16 tasks target с cut gate — operator surfaced 3 NEW items 2026-05-11 → swap MonthlyHeatmap eslint + Item #7/#10 к S48 to maintain budget)

#### Bucket A — S46 PHASE 6 carry-overs (~5 tasks)

1. **Vitest + RTL infra setup** — config + RTL setup + sample test файл + CI integration
2. **Vitest unit test #1: `computeDrawdown` property tests** — fast-check invariants (drawdown ≤ 0, peak monotonic non-decreasing)
3. **Vitest unit test #2: `useWfaFailAck` hook unit tests** — localStorage state machine + 3-distinct-day dedup + chip downgrade
4. **Vitest unit test #3: `MetricsTable` threshold tests** — Bailey 2014 + ADR 0014 color encoding (T1-T6 thresholds + RAW path)
5. **`backtest-flow.spec.ts` E2E activate** — `page.route('/api/backtest', ...)` mock fixture, verify VerdictPanel render

(MonthlyHeatmap eslint cleanup deferred к S48 — cosmetic only, BLOCKER fix S46 already addressed similar pattern)

#### Bucket B — Architect MEDIUM (~3 tasks)

7. **SPA catch-all FastAPI route** — `@app.get("/{path:path}")` fallback (architect MEDIUM — нужно если React Router added в future)
8. **React asset HTTP cache headers** — `Cache-Control: public, immutable, max-age=31536000` для `assets/*.{hash}.*`; `no-cache` для `index.html` (python-reviewer MEDIUM)
9. **MetricsTable T5 vanilla bug parity cleanup** — fix `undefined < 100 → false → PASS` к correct FAIL semantics. ADR-style note documented

#### Bucket C — Tech debt M1-M3 (~3 tasks)

10. **M1 retCode taxonomy** — extend bybit retCode enum (10001 / 110001 / 170131) в `adapter.py` / `errors.py`
11. **M2 pybit response shape defensive guards** — replace direct dict access с `.get()` + KeyError catch
12. **M3 WS data isinstance check** — `ws_private.py` isinstance guard against pybit V3 dict shape regression

#### Bucket D — S44 reviewer follow-ups + S45 quant (~1 task)

13. **DSR ∈ [0,1] property test + n_trials assert + sprint int/str type test** — bundled trio (test-engineer C2 + S45 quant follow-ups)

#### Bucket E — Operator Q7 UI validation surfaced (NEW 2026-05-11) (~3 tasks)

14. **BUG: trade_stats empty values для research presets (atr_breakout / volume_breakout)** — root cause: `research_runner_envelope.py:151` emits minimal trade_stats (только `n_trades` + `win_rate`); replay engine path emits полный (n_winners / n_losers / total_pnl_quote / etc). When research preset gets WFA verdict, TradesTable Path B (WFA) renders `—` для missing fields. **Fix:** extend `research_runner_envelope.build_research_runner_envelope()` к accept optional `trades_list` param + derive `n_winners` / `n_losers` from pnl signs + compute `total_pnl_pct` etc. Quote-currency fields (USDT amounts) require synthetic capital basis — emit `None` gracefully OR document как "research path = pct only, replay path = USDT". TradesTable Path B render `—` остаётся для quote fields когда null.

15. **FEATURE: EquityChart cursor crosshair + balance tooltip on hover** — operator request: горизонтальное движение курсором показывает actual balance (cumulative equity %). uPlot already supports `cursor.show: true` + `cursor.points` natively; currently `legend: { show: false }` hides values. **Implementation:** enable cursor crosshair с x-axis snap, render small floating tooltip с `Date: <ts>` + `Equity: +X.XX%` (Anthropic orange accent, glass-morphism style, JetBrains Mono). Verify sync с DrawdownSubchart cursor (already syncKey-shared per CC2) — drawdown tooltip shows `DD: -X.XX%` simultaneously.

16. **FEATURE: Fail Analysis tab — per-strategy detailed WHY-failed breakdown** — operator request: для FAILED strategies create separate tab/view с пошаговым разбором каждого WFA fold + каждого TIER 1-T6 criterion + каждого gate decision. **Scope (S47 minimum viable):** new tab `<FailAnalysisTab>` визуализирует existing envelope data — per-fold sharpe ratios (already в `result.fold_sharpe_ratios`), failed_folds list, failed_criteria, per-TIER threshold vs actual с PASS/FAIL chip. **Out-of-scope (defer S48):** new backend data exposure (e.g. per-fold trades drilldown, per-trade marker reasons, sub-period robustness chart). Если operator wants deeper drilldown — separate S48 task для backend envelope ext.

#### Out-of-scope to S47 (per ROUND 2 verdicts + operator scope balance)

- **Honest close code piece** (preset `disabled: bool` + 422 reject) → **S48 atomic с ADR 0067**
- **M4 `__repr__` security redaction** → **DEFER к mainnet-activation ADR (S49+)**
- **Vitest tests #4 (computeMonthlyData) + #5 (VerdictPanel)** → S48 (per Q4)
- **A11y polish (tablist ARIA + contrast)** → S48
- **README npm install note** → S48 docs leftover
- **F8 block_size constant unification** → S48 leftover
- **Item #10 OR Item #7 (S37/S38 long-standing tech debt)** → **S48** (CC1 backfill no longer needed — Bucket E filled slack)
- **MonthlyHeatmap eslint cleanup** → **S48** (cosmetic, not blocking; was Bucket A item #5 — remove from S47 to make room for Bucket E)
- **Fail Analysis backend data exposure** (per-fold trades drilldown) → **S48 OR later** depending operator priority

#### Cut gate (per Q2)

Если Vitest infra setup overruns its allocated slot — defer test files #2-#3 к S48 rather than expanding S47 ceiling. NEVER expand >16 tasks.

### PHASE 6 reviewer matrix S47

- **python-reviewer** — FastAPI SPA catch-all + cache headers + M2 dict guards + envelope trade_stats extension (T14 BUG fix)
- **trading-logic-reviewer** — MetricsTable T5 cleanup (threshold semantics) + Fail Analysis tab data correctness (T16)
- **quant-stats-reviewer** — DSR property test + n_trials assert + Bailey threshold tests
- **bybit-api-reviewer** — M1+M2+M3 (retCode taxonomy + response shape + WS isinstance)
- **security-auditor** — **SCOPED к M1-M3 only per CC2**, M4 explicit OUT OF SCOPE
- **frontend-developer** — Vitest+RTL setup + 3 React tests + E2E activate + EquityChart cursor (T15) + Fail Analysis tab (T16) + TradesTable rendering for new envelope fields (T14)
- **test-engineer** — coverage adequacy + property test design (DSR + computeDrawdown invariants) + envelope trade_stats schema test
- **data-integrity-reviewer** — envelope schema extension (T14) — research_runner_envelope optional `trades_list` param + derive logic invariants
- **doc-reviewer** — sprint-47 page + ADR (если новый)

NO architecture-reviewer (no major stack/refactor changes). NO dashboard-reviewer (superseded by frontend-developer per S46).

## Escalations к operator

### ESC-1 — S48 v0.1 semver "what does done mean?"

Trader-expert ROUND 1 surfaced. Specific question: given 0/11 WFA_FAIL, what is v0.1 completion milestone?

Options:
- (a) `alpha.N` indefinitely — honest, но no clear close
- (b) `v0.1.0` = infrastructure milestone с honest-close README disclaimer (требует ADR 0067)
- (c) Archive repo с no `v0.1.0` tag

Trader expert recommendation: option (b) paired с ADR 0067, но operator MUST explicitly choose. **Raise в S48 brainstorm as first question — НЕ S47 decision.**

### Q7 (operator manual action) — S46 UI validation ✅ DONE 2026-05-11

Operator surfaced 3 items via manual UI test:
1. BUG: trade_stats block empty values для research presets → **T14 added**
2. FEATURE: EquityChart cursor crosshair + balance tooltip on hover → **T15 added**
3. FEATURE: Fail Analysis tab — per-strategy WHY-failed breakdown → **T16 added**

Aesthetic Anthropic/cyberpunk: implicit confirm (no tweaks listed). Bucket E created.

## Files identified для edit (PHASE 3 plan input)

CREATE:
- `src/dashboard_react/vitest.config.ts`
- `src/dashboard_react/src/setupTests.ts` (RTL setup)
- `src/dashboard_react/src/components/__tests__/MetricsTable.test.tsx`
- `src/dashboard_react/src/components/__tests__/computeDrawdown.test.ts`
- `src/dashboard_react/src/hooks/__tests__/useWfaFailAck.test.ts`
- `tests/unit/test_dsr_property.py` (если не уже exists)
- `src/dashboard_react/src/components/FailAnalysisTab.tsx` (T16)
- `src/dashboard_react/src/components/FailAnalysisTab.module.css` (T16)

MODIFY:
- `src/dashboard/app.py` — SPA catch-all route + cache headers
- `src/dashboard_react/src/components/MetricsTable.tsx` — T5 bug fix
- `src/dashboard_react/tests/e2e/backtest-flow.spec.ts` — activate с mock fixture
- `src/execution/bybit/adapter.py` — M1 retCode taxonomy
- `src/execution/bybit/errors.py` — M1 retCode taxonomy
- `src/execution/bybit/ws_private.py` — M3 isinstance guard (M4 EXPLICITLY EXCLUDED)
- `src/backtest/research_runner_envelope.py` — T14 trade_stats extension (optional `trades_list` param + derive n_winners/n_losers/total_pnl_pct)
- `src/backtest/volume_breakout_runner.py` — T14 pass `trades_list` к envelope
- `src/backtest/atr_breakout_runner.py` — T14 pass `trades_list` к envelope
- `src/dashboard_react/src/api/types.ts` — T14 extend `TradeStats` interface (n_winners/n_losers optional, total_pnl_pct field)
- `src/dashboard_react/src/components/TradesTable.tsx` — T14 graceful render when quote fields missing (research path)
- `src/dashboard_react/src/components/EquityChart.tsx` — T15 enable cursor crosshair + custom tooltip
- `src/dashboard_react/src/components/EquityChart.module.css` — T15 tooltip styles
- `src/dashboard_react/src/components/DrawdownSubchart.tsx` — T15 mirror cursor enable (sync key уже shared)
- `src/dashboard_react/src/App.tsx` — T16 wire FailAnalysisTab conditional render когда verdict ∈ {WFA_FAIL, WFA_FAIL_DATA, FAIL}
- `.github/workflows/ci.yml` — Vitest step add

CREATE wiki:
- `llm-wiki/wiki/project/sprints/sprint-47-tech-debt-carryovers.md` (PHASE 8)

MODIFY wiki:
- `llm-wiki/wiki/project/architecture/current-state.md` — header + counts (S46 → S47)
- `llm-wiki/wiki/index.md` — sprint-47 entry
- `llm-wiki/wiki/log.md` — S47 sprint-end entry

## Next phase

PHASE 3 — `superpowers:writing-plans` skill creates `2026-05-11-sprint-47-tech-debt-carryovers.md`. **AFTER operator confirms ESC-1 deferred (don't decide now) AND Q7 operator manual UI validation done.** Auto-invoke `superpowers:subagent-driven-development` после plan saved (per kit override S45).
