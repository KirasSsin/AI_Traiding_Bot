---
title: SPRINT_STATE Archive Part 1 — S33-S46 historical sections
type: archive
tags: [sprint-state, archive, history]
created: 2026-05-11
updated: 2026-05-11
status: archive
sources:
  - llm-wiki/wiki/project/SPRINT_STATE.md (pre-trim 86 KB / 1239 lines snapshot)
  - git commit cbf3328 (last commit before trim a669b72)
---

# SPRINT_STATE Archive — Part 1 (S33-S46)

**Контекст:** SPRINT_STATE.md превышал 25k token Read tool limit (86 KB / 1239 lines), блокировал session-start orient. Per S46 post-ship pattern fix: SPRINT_STATE = current sprint + roadmap (≤ 6 KB). Историю архивируем здесь.

**Index:**
- **Part 1** (this file) — S33 → S46 ship sections
- [[SPRINT_STATE-archive-part-2]] — S5 → S32e ship sections (older history)

**Active state:** [[../SPRINT_STATE]] (current sprint + roadmap only)

**Per-sprint canonical summaries:** `wiki/project/sprints/sprint-NN-<slug>.md` (50 pages)
**Chronological journal:** `wiki/log.md` (append-only)

---

## S46 PHASE 5+6 ✅ COMPLETE → PHASE 8-SHIP 🟡

**Branch:** feature/sprint-46-react-migration

**Текущий статус:** PHASE 5 verify GREEN (pytest 1004p / mypy 0 issues / lint+tsc+build clean / Playwright 3p+1s). PHASE 6 ALL 5 reviewers complete: python-reviewer APPROVE, doc-reviewer APPROVE, architecture-reviewer APPROVE_WITH_CONDITIONS (C1+C2+C4+CC2+CC3 all MET; SPA catch-all → S47), test-engineer APPROVE_WITH_CONCERNS (trade_markers test added commit `51760d4`), frontend-developer APPROVE_WITH_CONCERNS — 1 BLOCKER + 2 HIGH addressed commit `36d6302`:
- BLOCKER MonthlyHeatmap.tsx Rules of Hooks violation fixed (useMemo before guards, eslint-disable removed)
- HIGH WfaFailBanner.tsx setTimeout wrapped в useEffect cleanup
- HIGH EquityChart.tsx useEffect deps split к granular (timestamps + equity_pct + trade_markers)

Total commits: 47. PHASE 5 re-verified post-fixes: lint 0 / tsc 0 / build 235.11 kB / Playwright 3p+1s.

**Следующее действие:** PHASE 8 ship — `superpowers:finishing-a-development-branch` skill → `git push -u origin feature/sprint-46-react-migration` + `gh pr create` + squash-merge after CI green + tag `v0.1.0-alpha.46`.

**Architect binding conditions (ADR pending):**
- C1 (HIGH): Vite `outDir` → `src/dashboard_react/dist/`. FastAPI mounts `dist/`. NO separate Vite dev server в production
- C2 (HIGH): Node.js CI step в `ci.yml` AS PART OF S46 (T21)
- C4 (MEDIUM): `app.py` `TemplateResponse` → `FileResponse(dist/index.html)` (T19)

### Task table

| Task | Status | Commit |
|------|--------|--------|
| T1: React infrastructure (Vite + TS strict + ESLint + Prettier) | DONE | b6e1335 |
| T2: Anthropic + cyberpunk design tokens (tokens.css + globals.css) | DONE | 1992a85 |
| T3: App.tsx — tab navigation + Anthropic header (Backtest/Documentation/History) | DONE | 9e78c5d |
| T4: TypeScript types (types.ts) + API client wrapper (client.ts) | DONE | b752010 |
| T5: React hooks — useStrategyInfo (cache) + useWfaFailAck (localStorage ack-gated) | DONE | 3e508e9 |
| T6: ConfigureBacktest form — optgroup grouping + supported_combos gating + App.tsx wired | DONE | fa30413 |
| T7: StrategyDescription component — collapsible block с useStrategyInfo hook + aria-expanded | DONE | 9588f48 |
| T8: VerdictPanel component — three-valued WFA verdict + warnings panel + App.tsx wired | DONE | f91997d |
| T9: EquityChart component — uPlot wrapper + Anthropic orange palette + ResizeObserver | DONE | 8b64be9 |
| T10: DrawdownSubchart component — uPlot subchart + computeDrawdown + CC2 sync key | DONE | 1cfd0aa |
| T11: TradeMarkers — envelope ext (vb+atr runners) + EquityChart scatter overlay (win/loss) | DONE | 553b94c |
| T12: MonthlyHeatmap — calendar grid с PnL по месяцам, intensity-scaled cells | DONE | 549b7bc |
| T13: MetricsTable — TIER 1-6 + DSR + MC + per-fold Sharpe subtable (RAW + WFA paths) | DONE | 96b8dac |
| T14: TradesTable — RAW 5-row + WFA 8-row quote-currency stats (n_winners/pnl/commissions/avg) | DONE | 62ade5b |
| T15: HistoryTab (9-col verdict-colored runs table) + DocumentationTab (indicator/strategy/methodology cards) | DONE | 46bfb63, 23115b6 |
| T16: WfaFailBadge — inline pill badge WFA_FAIL/WFA_FAIL_DATA/FAIL (red/amber) + HistoryTab wiring | DONE | 18959dd |
| T17: WfaFailBanner — ack-gated NON-dismissible banner (full/chip modes) + App.tsx mount above tabs | DONE | 48f7665 |
| T18: Playwright E2E tests (backtest-flow + wfa-fail-ack) | DONE | 1535dbf |
| T19: FastAPI FileResponse integration — app.py → FileResponse(dist/index.html) + StaticFiles /assets/ | DONE | 729a135 |
| T20: Archive vanilla dashboard → src/dashboard_legacy/ (static + templates) | DONE | 3a0eb97 |
| T21: CI/CD + start-bot.sh — Node.js setup + React build step + Playwright (architect C2) | DONE | 1992662 |
| T22: ADR 0066 + ADR 0039 amendment + sprint-46 page + wiki sync | DONE | 24bc36c |

---

## S45 SHIPPED ✅ — WFA recalibration + quant discipline + uniform 3.3y

**Branch:** feature/sprint-45-wfa-recalibration

### Task table

| Task | Status | Commit |
|------|--------|--------|
| T1: Uniform 3.3y data — PARQUET_BY_COMBO BTC 4H → 3.3y file, archive 8.7y binance | DONE | d2612cc |
| T2: ADR 0060/0061 amendments — update locked baselines to 3.3y | DONE | 91b9b2d |
| T3: CrossTrialLog idempotency guard (B1) — upsert on (sprint, symbol) + reset log | DONE | 5efddee |
| T4: n_trials per-strategy fix (C1) — default=1, atr=10, vb=1 | DONE | 553e040 |
| T5: B2 train slice documentation (inline + docstring) | DONE | 553e040 |
| T6: ADR 0014 low-freq tier amendment (4H/D test_bars=250) + tier helper wiring | DONE | cafb6a6 |
| T7: WFA recalibration run — 11 combos с uniform 3.3y window using new tier params | DONE | — |
| T8: ADR 0065 — S45 honest verdict + ESC-1 (a) trigger decision | DONE | — |

**Текущий статус:** T8 DONE. ADR 0065 создан, wiki sync завершён (sprint-45 page + current-state + index + log). Phase=8-ship. Все задачи S45 завершены.

**Следующее действие:** sprint-finish skill → tag v0.1.0-alpha.45 + merge feature/sprint-45-wfa-recalibration → main. Затем S46 brainstorm (honest portfolio close).

### S45 T7 actual verdicts (post-recalibration — input for T8 ADR 0065)

```
combo                                  verdict        DSR        MC_p     n_oos  failed_criteria
-------------------------------------------------------------------------------------------------
atr_breakout_BTCUSDT_15                WFA_FAIL       nan        0.9885   9      n_eff_threshold,t5_floor,sharpe_gate,mc_gate
atr_breakout_BTCUSDT_60                WFA_FAIL       0.1274     0.0220   16     n_eff_threshold,t5_floor,sharpe_gate,dsr_threshold
atr_breakout_BTCUSDT_240               WFA_FAIL       nan        0.6422   7      n_eff_threshold,t5_floor,sharpe_gate,mc_gate
atr_breakout_BTCUSDT_D                 WFA_FAIL_DATA  nan        nan      0      data_volume
atr_breakout_ETHUSDT_15                WFA_FAIL       nan        0.4188   7      n_eff_threshold,t5_floor,sharpe_gate,mc_gate
atr_breakout_ETHUSDT_60                WFA_FAIL       0.0000     0.4088   14     n_eff_threshold,t5_floor,sharpe_gate,mc_gate
atr_breakout_ETHUSDT_240               WFA_FAIL       nan        1.0000   4      n_eff_threshold,t5_floor,sharpe_gate,mc_gate
atr_breakout_SOLUSDT_15                WFA_FAIL       nan        0.9630   7      n_eff_threshold,t5_floor,sharpe_gate,mc_gate
atr_breakout_SOLUSDT_60                WFA_FAIL       0.0000     0.5597   15     n_eff_threshold,t5_floor,sharpe_gate,mc_gate
atr_breakout_SOLUSDT_240               WFA_FAIL       0.0000     0.0605   10     n_eff_threshold,t5_floor,sharpe_gate,mc_gate
volume_breakout_iter10_BTCUSDT_240     WFA_FAIL       0.8508     0.3298   22     n_eff_threshold,t5_floor,sharpe_gate,mc_gate
```

**Summary:** WFA_PASS=0 / WFA_FAIL=10 / WFA_FAIL_DATA=1 (unchanged vs S44 baseline).

**Delta vs S44 baseline:**
- BTCUSDT_240: n_oos 10→7 (fewer trades under new tier params), MC_p 0.6687→0.6422 (similar)
- ETHUSDT_240: n_oos 6→4, MC_p 0.3498→1.0000 (worsened — fewer fold trades)
- SOLUSDT_240: n_oos 20→10, MC_p 0.0525→0.0605 (similar, worse n_oos)
- volume_breakout_iter10 BTCUSDT_240: n_oos 38→22, DSR 0.0000→0.8508 (DSR improved but n_eff/t5 still FAIL)
- All n_eff_threshold + t5_floor + sharpe_gate failures preserved across all 10 combos.

**Cross-trial log (post-S45):** 8 trials (sprint=44 legacy entries from S44 session).

**ESC-1 (a) triggered:** 0/11 PASS. Low-freq tier amendment (ADR 0014) did NOT improve outcomes — n_oos counts dropped further for 4H combos (structural: fewer bars → fewer trades per fold). Honest close for S46 required.

### S45 T6 trade-frequency derivation (anti-snooping pre-commit, для T8 ADR 0065 reference)

Computed на 3.3y window (2023-01-01 → 2026-04-26), uniform per S45 ADR 0065:

| Combo | bars/year | 3.3y trades | trades/500bar | trades/250bar |
|-------|-----------|-------------|---------------|---------------|
| BTCUSDT_15  | 35064 | 245 | 1.06  | 0.53 |
| BTCUSDT_60  |  8766 | 106 | 1.83  | 0.92 |
| BTCUSDT_240 |  2191 |  28 | 1.94  | 0.97 |
| BTCUSDT_D   |   365 |  32 | 13.28 | 6.64 |
| ETHUSDT_15  | 35064 | 240 | 1.04  | 0.52 |
| ETHUSDT_60  |  8766 | 109 | 1.88  | 0.94 |
| ETHUSDT_240 |  2191 |  28 | 1.94  | 0.97 |
| SOLUSDT_15  | 35064 | 230 | 0.99  | 0.50 |
| SOLUSDT_60  |  8766 | 124 | 2.14  | 1.07 |
| SOLUSDT_240 |  2191 |  71 | 4.91  | 2.45 |

**Conclusion:** 4H/D combos fire 1-3 trades per 500-bar OOS fold = structural T5 floor failure. test_bars=250 doubles density к 0.5-1.5/fold ≈ 5-15 trades pooled across 5 folds. Honest second look — но likely T5 fail для ВСЕХ low-freq.

---

## S44 PHASE 4-EXECUTION — WFA retrofit для research presets (atr_breakout + volume_breakout)

**Branch:** feature/sprint-44-wfa-retrofit

### Task table

| Task | Status | Commit |
|------|--------|--------|
| T1: `src/backtest/research_wfa.py` shared helper — WindowSplitter + per-fold backtest_fn + DSR + MC + acceptance gate | DONE | d1f20b6 |
| T2: Wire `atr_breakout_runner` к research_wfa (10 combos) | DONE | 3e8532b |
| T3: Wire `volume_breakout_runner` к research_wfa (1 combo) | DONE | e6d25c9 |
| T4: `build_research_runner_envelope()` accepts `wfa_result: dict | None` kwarg — populates WFA fields when present, RAW sentinels when None | DONE | 59095c7 |
| T5: `backtest_runner.py` dispatch — atr_breakout + volume_breakout call `_run_*_wfa()` first, fall back to RAW on ValueError/FileNotFoundError, rebuild envelope with wfa_result | DONE | 6d051a5 |
| T6: Dashboard contract tests verify WFA verdict (not RAW) — BTC 4H returns WFA_PASS/WFA_FAIL/WFA_FAIL_DATA; BTC 1D → WFA_FAIL_DATA | DONE | 6d051a5 |
| T7+T8: JS verdict class mapping WFA_PASS/WFA_FAIL/WFA_FAIL_DATA + amber `.verdict-fail-data` CSS | DONE | f14870b |
| T9: CrossTrialLog wired к research_wfa + 11 combos run + verdict table captured | DONE | d468854 |
| T10: Preset descriptions updated с S44 WFA verdicts (atr_breakout + volume_breakout_iter10) | DONE | — |
| T11: ADR 0064 created | DONE | — |
| T12: Wiki sync — sprint-44 page + current-state + index + log + SPRINT_STATE phase=8-ship | DONE | — |

**Текущий статус:** T10+T11+T12 done. Wiki sync complete. Phase=8-ship. Next: tag v0.1.0-alpha.44 + PR merge.

**Следующее действие:** PHASE 8 ship — tag v0.1.0-alpha.44 + PR + merge.

### S44 actual verdicts (T9 run — input for T11 ADR 0064)

```
strategy                  sym      tf   verdict        DSR        MC_p     n_trades failed
----------------------------------------------------------------------------------------------------
atr_breakout              BTCUSDT  15   WFA_FAIL       nan        0.9885   9        n_eff_threshold,t5_floor,sharp
atr_breakout              BTCUSDT  60   WFA_FAIL       0.1274     0.0220   16       n_eff_threshold,t5_floor,sharp
atr_breakout              BTCUSDT  240  WFA_FAIL       0.0000     0.6687   10       n_eff_threshold,t5_floor,sharp
atr_breakout              BTCUSDT  D    WFA_FAIL_DATA  nan        nan      0        data_volume
atr_breakout              ETHUSDT  15   WFA_FAIL       nan        0.4188   7        n_eff_threshold,t5_floor,sharp
atr_breakout              ETHUSDT  60   WFA_FAIL       0.0000     0.4088   14       n_eff_threshold,t5_floor,sharp
atr_breakout              ETHUSDT  240  WFA_FAIL       nan        0.3498   6        n_eff_threshold,t5_floor,sharp
atr_breakout              SOLUSDT  15   WFA_FAIL       nan        0.9630   7        n_eff_threshold,t5_floor,sharp
atr_breakout              SOLUSDT  60   WFA_FAIL       0.0000     0.5597   15       n_eff_threshold,t5_floor,sharp
atr_breakout              SOLUSDT  240  WFA_FAIL       0.0000     0.0525   20       n_eff_threshold,t5_floor,sharp
volume_breakout_iter10    BTCUSDT  240  WFA_FAIL       0.0000     0.1994   38       n_eff_threshold,t5_floor,sharp
```

Cross-trial log: 10 trials appended (sprint=44). All combos WFA_FAIL (trade count too low for n_eff/t5 thresholds). BTCUSDT 1D → WFA_FAIL_DATA (data_volume insufficient). Note: dashboard presets use best autoresearch params per combo — params vary (atr_period 9/14/21, atr_breakout_mult 1.5/2.0/2.5/3.0).

### Phase tracking

| Phase | Status |
|-------|--------|
| 1-orient | done |
| 2-brainstorm | done |
| 3-plan | done |
| 4-execution | done (T1-T12 all done) |
| 5-verify | done |
| 6-review | done |
| 7-sync | done |
| 8-ship | in_progress |
| 9-close | pending |

---

## S43 PHASE 8-SHIP — UI polish (preset rename + descriptions + equity chart)

**Branch:** feature/sprint-43-ui-polish

### Task table

| Task | Status | Commit |
|------|--------|--------|
| T1: Rename preset labels + add description + optgroup to STRATEGY_PRESETS | DONE | def07e4 |
| T2: Expose description + optgroup via /api/strategies + /api/strategy/{id}/info | DONE | 27d57af |
| T3 (equity_curve): envelope adds equity_curve parallel arrays для uPlot | DONE | 6baba47 |
| T4 (equity_timestamps): atr_breakout_runner passes df timestamps to envelope | DONE | d926cd8 |
| T5 (equity_timestamps): volume_breakout_runner passes df timestamps to envelope | DONE | 0dceae0 |
| T6: Vendor uPlot (uPlot.iife.min.js + uPlot.min.css) в static/vendor/ | DONE | — |
| T7: Template — strategy description block + equity chart panel + uPlot script | DONE | dfd8500 |
| T8+T9+T10: JS optgroup dropdown + description block + uPlot equity chart | DONE | 5f5bc79 |
| T11: CSS — description styling + uPlot terminal overrides | DONE | — |
| T12: Wiki sync — ADR 0063 + sprint-43 + current-state/index/log/SPRINT_STATE | DONE | — |

**Текущий статус:** T12 done. Все задачи DONE. Следующее действие: PHASE 8 ship (tag v0.1.0-alpha.43 + PR merge).

### Phase tracking

| Phase | Status |
|-------|--------|
| 1-orient | done |
| 2-brainstorm | done |
| 3-plan | done |
| 4-execution | done |
| 5-verify | done |
| 6-review | done |
| 7-sync | done |
| 8-ship | in_progress |
| 9-close | pending |

---

## S42 PHASE 7-SYNC — ATR breakout hardening (dashboard contract envelope)

**Phase:** 7-sync  
**Branch:** feature/sprint-42-atr-breakout-hardening  
**in_progress:** PHASE 6 reviewers next, then PHASE 8 ship

**T7 status:** verified-no-change — `.warn-high/.warn-mid/.warn-info` CSS classes уже exist в `dashboard.css` lines 466-471. Envelope chips render автоматически через existing warnings-panel JS loop. No code edits required.

**T8 status:** done — full pytest sweep:
- Unit: 946 passed (+41 vs pre-S42 baseline 905)
- Integration: 52 passed (+19 vs pre-S42 baseline 33)
- mypy --strict src/: 0 errors на 84 source files (+5 modified/new)
- Stale preset_id refs in tests/integration/test_atr_breakout_dashboard_contract.py — correct usage (verifies removal в `test_old_atr_breakout_preset_ids_removed`).

**Completed tasks:**
- T1: `src/backtest/research_runner_envelope.py` + `tests/unit/test_research_runner_envelope.py` — DONE (commit fe49e39)
  - 5/6 tests pass. 1 test (`test_envelope_subperiod_robustness_3_of_5_emits_warn_chip`) has data inconsistency:
    equity_curve `[0,50,30,60,50,45]` gives 2/5 positives (not 3/5) under delta-from-previous algorithm.
    Needs operator decision: fix test curve OR adjust algorithm.
- T2: `src/backtest/atr_breakout_runner.py` wired to envelope + `tests/integration/test_atr_breakout_dashboard_contract.py` — DONE (commit 383e67b)
  - 5/5 new contract tests PASS. 8/8 baseline floor tests PASS (PnL unchanged). mypy 0 errors.
- T3: `src/backtest/volume_breakout_runner.py` wired to envelope + `tests/integration/test_volume_breakout_dashboard_contract.py` — DONE (commit 0ade871)
  - 4/4 new contract tests PASS. 29/29 total volume_breakout tests PASS. mypy 0 errors.
- T4: `src/dashboard/backtest_runner.py` — 10 atr_breakout_* presets → 1 unified `atr_breakout` preset — DONE (commit 5046d10)
  - STRATEGY_PRESETS: 10 old preset_ids removed; unified `atr_breakout` с `supported_combos` (10 combos) registered.
  - Dispatch atr_breakout: envelope merge (17-key base dict) not 4-key cherry-pick.
  - Dispatch volume_breakout: same envelope merge fix.
  - 23/23 new contract tests PASS. 24/24 baseline/multi-combo/unit tests PASS. mypy 0 errors.
- T5: `src/dashboard/app.py` — `GET /api/strategy/{id}/info` endpoint + `supported_combos` enforcement в `POST /api/backtest` — DONE (commit efd4201)
  - 6/6 new tests PASS. 16/16 existing dashboard tests PASS (no regressions). mypy 0 errors.
  - Invalid combos (e.g. BTCUSDT/5m) rejected 422. Valid combos (BTCUSDT/240) pass gate.
  - Legacy presets without `supported_combos` return empty list — backward-compatible.
- T6: `src/dashboard/static/dashboard.js` + `dashboard.css` — JS defensive guards + applyComboGates — DONE (commit 9be78fe)
  - API constant `strategyInfo` added. `applyComboGates()` greys out invalid sym/TF combos for atr_breakout.
  - Defensive `??` / `?.` guards in `renderResult` — prevents crash on missing `r.request`, `r.bars_per_year`, `r.failed_criteria`.
  - `.verdict-raw` CSS class added (amber #f0a000 for RAW verdict).
  - Smoke test: `/api/strategy/atr_breakout/info` returns 10 `supported_combos`. Backtest returns `verdict: RAW` with all envelope keys present.

**T9 status:** done — ADR 0062 created, 0060+0061 marked superseded.
**T10 status:** done — sprint-42 page + current-state.md + index.md + log.md + atr-breakout-strategy component updated.

**Next action:** PHASE 6 — domain reviewer dispatch (trading-logic / quant-stats / doc-reviewer), then PHASE 8 ship (tag v0.1.0-alpha.42 + PR merge).

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
