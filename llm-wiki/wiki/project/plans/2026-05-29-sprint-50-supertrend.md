# Sprint 50 — Supertrend Strategy (freqtrade adaptation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD strict. Per-task SPRINT_STATE update. Steps use `- [ ]` checkboxes.

**Goal:** Adapt freqtrade Supertrend → our Bybit Spot streaming bot as hypothesis #10, with anti-snooping discipline (fix autoresearch held-out split, then legit param sweep).

**Architecture:** Stateful streaming `on_bar(bar)->Signal|None` (look-ahead safe). Lazybear Supertrend. Signal-exit + ATR bracket SL. Acceptance via held-out eval → formal 1H WFA (ADR 0014).

**Tech Stack:** Python 3.12, numpy, pytest + Hypothesis. ADR 0067 LOCKED: BTCUSDT 1H, ATR=10/MULT=3.0 sweep center.

---

## File structure

- CREATE `src/signalgen/supertrend_strategy.py` — SupertrendStrategy (T4)
- MODIFY `src/signalgen/indicators.py` — public `wilder_atr()` (T1)
- MODIFY `src/signalgen/atr_breakout_strategy.py` + `volume_breakout_strategy.py` — use shared wilder_atr (T1)
- MODIFY `src/risk/reason_codes.py` — +2 codes 63→65 (T4)
- CREATE `src/backtest/supertrend_runner.py` — WFA runner (T7)
- MODIFY `scripts/autoresearch_endless.py` — held-out split (T3) + strat_supertrend (T6)
- MODIFY `src/dashboard/backtest_runner.py` — preset (T10)
- CREATE tests: `test_wilder_atr.py`, `test_supertrend_strategy.py`, `tests/property/test_supertrend_lookahead.py`, `test_autoresearch_heldout.py`, `test_supertrend_runner.py`

---

## Task 1: CC2 — Extract Wilder ATR to indicators.py (opus)

**Files:** Modify `src/signalgen/indicators.py`, `atr_breakout_strategy.py:262`, `volume_breakout_strategy.py:204`. Test `tests/unit/test_wilder_atr.py`.

- [ ] **Step 1: Write failing test** — `wilder_atr(h,l,c,period)` returns RMA-smoothed ATR, seeds SMA of first `period` TRs, NaN before. Assert matches current `_wilder_atr` output on sample data byte-for-byte.
- [ ] **Step 2: Run fail** (function not defined).
- [ ] **Step 3: Implement** `wilder_atr()` in indicators.py — copy exact logic from atr_breakout_strategy.py:262-278 (TR loop + RMA). Public, typed `(np.ndarray×3, int)->np.ndarray`.
- [ ] **Step 4: Switch both consumers** — atr_breakout_strategy `_wilder_atr` → call `wilder_atr`; volume_breakout `_compute_wilder_atr` → call `wilder_atr`. Keep thin wrapper OR direct.
- [ ] **Step 5: Run** — new test + existing `test_atr_breakout*` + `test_volume_breakout*` all GREEN. mypy --strict clean.
- [ ] **Step 6: Commit** `refactor(s50): extract wilder_atr to indicators.py — shared by atr_breakout + volume_breakout + supertrend (CC2)`. SPRINT_STATE T1 done.

## Task 2: CC3 — Verify N_trials runtime gap (opus)

**Files:** Read `research_wfa.py:255-262`, `donchian_runner.py:190-213`, `atr_breakout_runner.py:497`. Doc finding in plan trace.

- [ ] **Step 1:** Trace how `n_trials=10` + CrossTrialLog.append_trial flows to compute_dsr. Confirm donchian/atr pattern.
- [ ] **Step 2:** Determine if a Supertrend runner following the same pattern wires n_trials correctly OR bypasses (ADR 0059 G5). Write finding to `tests/unit/test_supertrend_runner.py` docstring + ADR 0067 note.
- [ ] **Step 3:** If gap exists → write failing test asserting n_trials reaches DSR; fix in T7 runner. If no gap → document pattern to replicate.
- [ ] **Step 4: Commit** `test(s50): document N_trials runtime wiring for supertrend runner (CC3)`. SPRINT_STATE T2 done.

## Task 3: CC4 — autoresearch held-out split (opus, operator Q4 override)

**Files:** Modify `scripts/autoresearch_endless.py`. Test `tests/unit/test_autoresearch_heldout.py`.

- [ ] **Step 1: Write failing test** — `load_train_slice(df)` excludes held-out range 2025-06-01→2026-05-01; `eval_heldout(combo, df)` evaluates ONLY held-out range; sweep loop never sees held-out rows.
- [ ] **Step 2: Run fail.**
- [ ] **Step 3: Implement** — physical date split: `HELDOUT_START=2025-06-01`, `HELDOUT_END=2026-05-01` constants. `run_combo()` loads parquet then slices to train (`< HELDOUT_START`). New `eval_heldout_once(winner_combo)` single-call evaluates held-out slice. Sweep loop reads train-only.
- [ ] **Step 4: Run** — test GREEN, existing autoresearch tests GREEN.
- [ ] **Step 5: Commit** `feat(s50): autoresearch held-out split — train/held-out physical separation prevents champion-bias (CC4 operator Q4)`. SPRINT_STATE T3 done.

## Task 4: SupertrendStrategy streaming impl (opus)

**Files:** Create `src/signalgen/supertrend_strategy.py`. Modify `reason_codes.py` (+2). Test `tests/unit/test_supertrend_strategy.py`.

- [ ] **Step 1: Add reason codes** — `ENTRY_LONG_SUPERTREND`, `EXIT_FLAT_SUPERTREND_FLIP` to ReasonCode (63→65). Test enum count = 65, no dup values.
- [ ] **Step 2: Write failing tests** — entry on trend flip bullish; exit on trend flip bearish; warmup NaN until ATR_PERIOD; no signal mid-trend; Lazybear latch (line monotonic within trend).
- [ ] **Step 3: Run fail.**
- [ ] **Step 4: Implement** SupertrendStrategy. on_bar streaming. Instance attrs `_supertrend_line: float|None`, `_trend_direction: Literal["BULL","BEAR"]|None`. Uses `wilder_atr` (T1). Lazybear: `basic_ub=(h+l)/2+mult*atr`, `basic_lb=(h+l)/2-mult*atr`, final bands with trend-dependent clamp, trend flip when close crosses. Warmup seed: bars<ATR_PERIOD→None; first warm: line=basic_ub, trend=BEAR (conservative). Entry ENTRY_LONG_SUPERTREND on BEAR→BULL; exit EXIT_FLAT_SUPERTREND_FLIP on BULL→BEAR. append-bar-before-compute, is_closed gate, generated_at≥bar_close.
- [ ] **Step 5: Run** GREEN. mypy clean.
- [ ] **Step 6: Commit** `feat(s50): SupertrendStrategy streaming (Lazybear) + 2 reason codes (T4 hypothesis #10)`. SPRINT_STATE T4 done.

## Task 5: Look-ahead property test + vectorized cross-validation (opus)

**Files:** Create `tests/property/test_supertrend_lookahead.py`. Extend `test_lookahead.py`.

- [ ] **Step 1: Write reference vectorized Lazybear Supertrend** (batch numpy, in test file) — the freqtrade-style whole-array calc.
- [ ] **Step 2: Cross-validation test** — feed same BTC bars through streaming on_bar AND vectorized ref; assert trend direction + line match at every bar within float tol (1e-9). This proves no look-ahead + formula parity.
- [ ] **Step 3: Hypothesis property test** — for random OHLC series, streaming output deterministic + no future-bar dependency (shuffle-future invariance).
- [ ] **Step 4: Run** GREEN. Add to property marker.
- [ ] **Step 5: Commit** `test(s50): supertrend look-ahead property + vectorized cross-validation (T5)`. SPRINT_STATE T5 done.

## Task 6: autoresearch strat_supertrend (sonnet)

**Files:** Modify `scripts/autoresearch_endless.py`.

- [ ] **Step 1:** Add `strat_supertrend(df, atr_period, mult)` vectorized (matches T5 reference). Register in COMBOS.
- [ ] **Step 2:** Verify output matches T5 reference impl. Commit `feat(s50): strat_supertrend in autoresearch (T6)`. SPRINT_STATE T6 done.

## Task 7: supertrend_runner WFA (sonnet)

**Files:** Create `src/backtest/supertrend_runner.py`. Test `test_supertrend_runner.py`.

- [ ] **Step 1: Write failing test** — runner produces WFA verdict dict, n_trials=10 wired (per T2), CrossTrialLog appended.
- [ ] **Step 2: Implement** mirroring `atr_breakout_runner.py`. WFA loop ADR 0014. n_trials=10.
- [ ] **Step 3: Run** GREEN. Commit `feat(s50): supertrend_runner WFA + n_trials=10 (T7)`. SPRINT_STATE T7 done.

## Task 8: Param sweep TRAIN + single held-out eval (sonnet)

- [ ] **Step 1:** Run sweep ATR_PERIOD∈[7,21], MULT∈[2.0,4.0] on TRAIN slice (T3). Pick winner by train Sharpe.
- [ ] **Step 2:** `eval_heldout_once(winner)` — single eval on 2025-06→2026-05.
- [ ] **Step 3:** Document result in sprint page. If Sharpe>0 AND n≥15 → T9. Else honest-fail doc + skip T9.
- [ ] **Step 4: Commit** `research(s50): supertrend sweep winner + held-out eval (T8)`. SPRINT_STATE T8 done + decision recorded.

## Task 9 (conditional): Formal 1H WFA (sonnet)

- [ ] Only if T8 held-out passes. Run formal WFA winner params, n_trials=10, ADR 0014 gates. Honest verdict. Commit `research(s50): supertrend formal 1H WFA verdict (T9)`. SPRINT_STATE T9 done.

## Task 10: Dashboard preset (sonnet)

**Files:** Modify `src/dashboard/backtest_runner.py` STRATEGY_PRESETS.

- [ ] Add `supertrend` preset: locked BTCUSDT 1H, type=supertrend, RU description, optgroup Тренд. Test preset loads. Commit `feat(s50): supertrend dashboard preset (T10)`. SPRINT_STATE T10 done.

## Task 11: Wiki sync (sonnet)

**Files:** Create `sprints/sprint-50-supertrend.md`. Modify index/log/current-state. ADR 0067 proposed→accepted.

- [ ] sprint-50 page + index Sprints entry + log ship + current-state (reason codes 63→65, strategies +1, sprint pages +1). Commit `docs(s50): wiki sync (T11)`. SPRINT_STATE T11 done + phase=5-verify.

---

## PHASE 5 gates
pytest GREEN + mypy --strict 0 + reason codes 65 + look-ahead property + vectorized cross-validation match + lint+tsc+build (T10 preset).

## PHASE 6 reviewers (parallel)
trading-logic (look-ahead/FSM/exit) + quant-stats (Supertrend formula + WFA + DSR n_trials) + python + architecture (wilder_atr extract + autoresearch refactor) + data-integrity (held-out split) + test-engineer (property + cross-val coverage) + trader-expert (WFA verdict).

## PHASE 8 ship
tag v0.1.0-alpha.50.

## Self-Review
- Spec coverage: 8-step execution order (backlog) → T1-T11 mapped. CC2=T1, CC3=T2, CC4=T3, impl=T4, look-ahead=T5, sweep infra=T6, runner=T7, sweep run=T8, WFA=T9.
- Type consistency: `wilder_atr` signature shared T1; ReasonCode +2 T4 used T4/T7; SupertrendStrategy Signal protocol reuse.
- Cross-task deps: T1 before T4/T7 (ATR), T2 before T7 (n_trials), T3 before T8 (held-out), T4 before T5/T6 (impl before cross-val), T8 before T9 (conditional).
- Operator override honored: Q4 = sweep (T3+T6+T8) not literature defaults.
