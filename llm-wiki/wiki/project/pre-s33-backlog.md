---
title: Pre-S33 Backlog — 3-agent консилиум verdicts (PHASE 2 brainstorm)
type: backlog
tags: [pre-s33, brainstorm, consilium, trader-expert, trading-logic-reviewer, quant-stats-reviewer, esc-1, esc-2, esc-3, multi-symbol, formulas]
created: 2026-04-27
updated: 2026-04-27
status: open
sources:
  - project/SPRINT_STATE.md
  - project/decisions/0048-sprint-32d-kit-phase-3-improvements.md
  - project/sprints/sprint-32e-kit-audit-doc-sync.md
  - project/sprints/sprint-23-honest-close-v05.md
  - project/sprints/sprint-22-4h-test.md
  - project/sprints/sprint-27-formula-bug-fixes.md
---

# Pre-S33 Backlog — 3-agent Consilium Verdicts

> **Operator directive:** "задай 3 агентам трейдерам, пусть они между собой проведут brainstorming и консилиумом решат как исправить формулы и все расчёты, чтобы выйти в плюс"
>
> **3 agents dispatched parallel** via `superpowers:dispatching-parallel-agents`:
> - `trader-expert` (sonnet effort:max) — trading domain / business / market reality
> - `trading-logic-reviewer` (sonnet) — engineering / FSM / reason codes / look-ahead
> - `quant-stats-reviewer` (sonnet effort:max) — math / statistical validity / DSR / MC

## Summary table — 6 questions × 3 verdicts

| # | Question | trader-expert | trading-logic | quant-stats | **Consensus / Synthesis** |
|---|----------|---------------|---------------|-------------|--------------------------|
| Q1 | Multi-symbol authorization (ESC-1) | EXPAND→CONFIRM A с 4 binding | **REVISE → single-symbol** (engineering blockers) | CONFIRM A с DSR schema prereq | **DISAGREE** → BACKTEST F multi-symbol OK (zero new code, S15 path), LIVE deferred к S34 (650-850 LoC infra) |
| Q2 | "In profit" vs T1-T6 (ESC-2) | **REVISE → strict T1-T6** (S15 precedent) | CONFIRM C (both, de facto) | CONFIRM C (in-profit redundant если T1 PASS) | **MAJORITY C (2 of 3)** с trader caveat — "in profit" = operational checklist post-T1-T6 PASS, NOT alternative gate |
| Q3 | 4H 3 simultaneous (ESC-3) | CONFIRM B с binding | **REVISE → defer S34** (same blockers Q1) | EXPAND — correlation-adjusted risk model needed | **DISAGREE** → BACKTEST 3 simultaneous OK, LIVE deferred к S34. Quant correlation concerns documented. |
| Q4 | Formulas correctness post-S27 | EXPAND — CC6 4H WFA window unaddressed | CONFIRM A (look-ahead intact) | EXPAND — 2 surviving issues (t-stat heavy-tail + MC p-value formula) | **A confirmed для existing formulas + 3 NEW gaps surfaced:** CC6 WFA 4H window / t-stat heavy-tail correction / MC p-value `(count+1)/(N+1)` per ADR 0015 |
| Q5 | S33 strategy direction | **REVISE → F only** (B → S34 sequencing) | **REVISE → B+C single-symbol** (F blocked) | **REVISE → E first then F+B** (DSR cross-trial prereq) | **3-WAY DISAGREE** → Synthesis: (1) E first (DSR cross-trial impl + MC p-value fix + cross_trial_log symbol field) (2) F backtest only (multi-symbol BTC+ETH+SOL) (3) Skip B/C → S34+ |
| Q6 | Test debt fix в S33 | CONFIRM A — read tracebacks first | CONFIRM A — root cause = fixture broken by S27 calc change (~65 LoC tests + 2 LoC src) | CONFIRM A — critical, may invalidate bars_per_year path | **CONSENSUS A** — fix 3 pytest + 1 mypy в начале S33. Investigate root cause перед проведением S33 measurement. |

---

## Detailed verdicts по question

### Q1 — Multi-symbol authorization (ESC-1)

**trader-expert (EXPAND→CONFIRM-A с 4 binding conditions):**
> "Multi-symbol BTC+ETH+SOL = only viable path к T5 reachability. Single-symbol structurally closed (3 timeframes empirically: 1H=59, 15M=73, 4H=62 trades). ESC-1 = 'attempt T5 via only known path versus close project.'"
> 
> Binding conditions: (1) S17-relaxed params (RSI 35/65, BB 1.5σ) NOT S15 (RSI 30/70, BB 2σ — MC p=0.998 noise); (2) per-symbol independent WFA fold gate; (3) CC6 pre-registration WFA 4H window; (4) correlated DD documentation (BTC/ETH/SOL r=0.90+ tail).

**trading-logic-reviewer (REVISE → single-symbol BTC):**
> "Multi-symbol live = 650-850 LoC architectural pre-work blocked. 4 specific FSM blockers:
> 1. SQLite WAL concurrency (3 Coordinators share connection)
> 2. `find_by_order_id` no symbol filter (defense-in-depth gap)
> 3. RiskManager assumes full equity = 1 position (3× over-allocation risk если 3 signals fire simultaneously)
> 4. Halt cascade isolation undefined (BTC halt не halts ETH/SOL)
> 
> Multi-symbol BACKTEST = trivial (zero code). LIVE = blocked. Capital over-allocation = real-money blocker."

**quant-stats-reviewer (CONFIRM A с REQUIRED prerequisite):**
> "T5=100 floor + Hudson&Urquhart 2021 → multi-symbol mathematically necessary.
> 
> Hidden math risk: BTC-ETH ~0.85 / BTC-SOL ~0.70 / ETH-SOL ~0.75 correlation. Effective n_eff ≈ 90-120 (after correlation deflation), не 135-180 raw. t-stat denominator understated by `sqrt(1+(m-1)*rho)` ≈ 1.6×.
> 
> **REQUIRED prerequisite:** `cross_trial_log.py::TrialEntry` schema has no `symbol` field. Multi-symbol DSR computation ambiguous today. Must add `symbol: str` field OR document n_trials=1 limitation."

**SYNTHESIS:**
- Trader + Quant agree: multi-symbol mathematically necessary
- Engineering: live blocked, backtest fine
- **Resolution:** S33 = multi-symbol BACKTEST measurement (validate F mathematically). Live deployment + Kelly capital-split + orchestration → S34 infra sprint. Both perspectives served.
- All 3 binding conditions от trader + DSR schema prereq от quant must be pre-registered.

### Q2 — "In profit" vs T1-T6 (ESC-2)

**trader-expert (REVISE → strict T1-T6 only):**
> "S15 demonstrated dual criteria failure mode: aggregate PnL positive, ETH 4H pnl=+404 post-S27, но MC p=0.998 = noise. Live deployment без MC validation = gambling. 'In profit' gate без MC/DSR = survivorship bias."

**trading-logic-reviewer (CONFIRM C):**
> "T1-T6 = research-only (WFA outputs). Zero hits в `src/` для T1/acceptance/threshold values — pure human-readable gates. Runtime CB layer (L1 15% / L2 22% / L3 30%) covers drawdown protection. Split research strict / live soft = de facto architecture, no new code needed."

**quant-stats-reviewer (CONFIRM C):**
> "'In profit' = trivially weak gate (luck possible на small sample). T1-T6 калиброваны catch this. Combination не weakens stats — adds operational sanity. Strategy passing T1-T6 with negative PnL = logical impossibility (T1 Sharpe ≥ 1.0 requires positive mean). 'In profit' redundant when T1 PASS — but adds clarity."

**SYNTHESIS:**
- 2 of 3 CONFIRM C
- **Trader concern valid:** S15 precedent — "in profit" without MC = survivorship
- **Resolution:** C with caveat — "in profit" = operational checklist POST T1-T6 PASS (live deployment pre-flight), NOT parallel/alternative statistical gate. Document trader concern в ADR.

### Q3 — 4H 3 simultaneous positions (ESC-3)

**trader-expert (CONFIRM B с binding):**
> "Signal frequency 4H = ~6 bars/day, ~20 signals/year/symbol. Concurrent 3 positions unlikely в practice. Capital 1/3 each per Kelly already supports.
> 
> Binding: (1) operator explicit 100% capital exposure ack during concurrent LONG signals, CB primary protection; (2) multi-symbol data quality detector verification (S9 REST-vs-REST gap detection across symbols)."

**trading-logic-reviewer (REVISE → defer S34):**
> "Same blockers как Q1. Single-symbol FSM per Coordinator. RiskManager assumes 1 position. 3 concurrent positions без capital-split logic = 3× over-allocation. WS subscriptions OK (all symbols on one private connection per Bybit V5). Reconciler `find_by_order_id` already per-symbol parameter — OK. **Capital allocation = critical gap.** Estimate: ~500 LoC infrastructure pre-work."

**quant-stats-reviewer (EXPAND — correlation-adjusted needed):**
> "3 simultaneous = NOT 3× single-position risk = 3× CORRELATED risk. Joint crash scenario (BTC -15%, ETH -18%, SOL -25%) = all 3 long simultaneously losing. Kelly per-symbol fraction independent, no correlation matrix.
> 
> Portfolio σ ≈ σ_symbol × sqrt(1 + 2×0.75×0.67) ≈ 1.30 × σ_symbol → 30% higher actual risk than naive view. L1 CB (15% DD) triggered faster.
> 
> Equal 1/3 capital allocation assumes equal risk — но BTC ниже realized vol чем SOL. Risk-weighted (1/ATR_symbol) better risk parity."

**SYNTHESIS:**
- Same engineering vs strategy disagreement как Q1
- Quant adds correlation matrix requirement
- **Resolution:** S33 backtest 3 simultaneous OK (zero code). Live в S34 c (a) Kelly capital-split + (b) correlation matrix + (c) operator pre-approval correlated DD.

### Q4 — Formulas correctness post-S27

**trader-expert (EXPAND — CC6 unaddressed):**
> "Formulas correct per S27 TDD + sweep. **HOWEVER CC6 (WFA 4H window) unresolved** — train=2000 bars at 4H = 333 days/fold, exhausts 2023 entirely для IS folds, leaves only 2024-2026 (~1.3y OOS). 135-trade estimate для multi-symbol F assumes 3.3y OOS — may be optimistic. Pre-register либо ADR 0014 default (1.3y OOS, document limit) либо amendment (train=1000/test=250). MUST decide перед S33 measurement."

**trading-logic-reviewer (CONFIRM A):**
> "S27 fixes verified. Look-ahead invariants intact:
> - `strategy.py:61-72` rejects `bar.is_closed=False`, deduplicates by `close_time`
> - `mean_reversion_strategy.py:72-78` same pattern
> - `backtest/indicators.py:92-93` `shift(1)` correct, не look-ahead
> - `replay_engine.py` signal-on-close → fill-at-next-open (line 248)
> 
> Zero `src/signalgen/` или `src/backtest/` files touched S28-S32e. No new code concerns."

**quant-stats-reviewer (EXPAND — 2 surviving issues):**
> "S27 5 fixes mathematically valid as implemented. **TWO surviving open issues:**
> 
> 1. **t-stat assumes Normal/IID returns** — `strategy_metrics.py:118` uses `mean / (std/sqrt(n))`. Hudson & Urquhart 2021: crypto returns heavy tails (excess kurtosis 5-15 для 4H BTC). Critical value adjusted: `t_adj ≈ t × sqrt(1 + γ₄/4)` — γ₄=5 → `t_adj ≈ t × 1.37`. Reported t=2.5 → adjusted t≈1.8 (below threshold). NO kurtosis correction в strategy_metrics.py.
> 
> 2. **MC p-value formula violates ADR 0015** — `mc_permutation.py:56` returns `count_extreme / n_iterations`. ADR 0015 specifies `(count+1)/(N+1)`. Current produces p=0 when no permutation extreme — logically impossible с finite permutations. Pre-existing issue, не S27 introduced."

**SYNTHESIS:**
- A confirmed для существующих formulas
- **3 NEW gaps surfaced:**
  - **CC6** (trader) — WFA 4H window pre-registration BLOCKING S33 measurement
  - **t-stat heavy-tail correction** (quant) — Hudson&Urquhart 2021 binding
  - **MC p-value formula** (quant) — ADR 0015 violation, MUST FIX перед S33 measurement

### Q5 — S33 strategy direction

**trader-expert (REVISE → F only):**
> "Multi-symbol 4H (F) с S17-relaxed params для S33. Regime filter (B) → S34 conditional на F results.
> 
> S27 Q4 plan установил sequencing: 'S28=Multi-symbol 4H = FOUNDATION / S29=Regime filter.' Combining F+B = hypothesis modification risk on top структурного extension. Regime filter уменьшит trade frequency (already sparse ~20/year/symbol), risk n falling below T5 floor.
> 
> Conditional B trigger: только если post-measurement fold audit показывает catastrophic concentration ≈ S20 fold #2 (-185.21).
> 
> **Pre-spec:** S17-relaxed params (RSI 35/65, BB 1.5σ) explicitly named в S33 ADR."

**trading-logic-reviewer (REVISE → B+C single-symbol):**
> "F blocked engineering (Q1/Q3 blockers). B+C = minimal risk path:
> - **B (SMA50 trend gate)** = ~45 LoC prod (15 indicators + 30 strategy filter) + ~80 LoC tests. No FSM changes. Contained.
> - **C (SL calibration)** = 0 LoC prod (parameter sweep WFA only).
> - **D (Donchian)** = +280 LoC, новый strategy class. Risk: SHORT signals conflict с long_only invariant.
> - **E** = research only.
> - **F live** = blocked 650-850 LoC.
> 
> **Recommended scope:** B+C single-symbol BTC. Multi-symbol F → S34 infra sprint."

**quant-stats-reviewer (REVISE → E first then F+B):**
> "Sequence matters: F+B без E creates measurement problem. Multi-symbol = 3 symbols × 1 OOS Sharpe each. `cross_trial_log` schema stores ONE oos_sharpe per sprint — multi-symbol case ambiguous. `n_trials=1` forced → DSR multi-testing penalty silently dropped → inflated DSR.
> 
> **Minimum E work перед F:**
> 1. Add `symbol: str` field к `TrialEntry` TypedDict
> 2. Adjust `sigma_sr()` to compute across (sprint, symbol) pairs
> 3. Decide pooling protocol
> 
> Small schema + math change. Skipping = methodologically undefined для multi-symbol DSR.
> 
> C (SL calibration) — n≈20/group power ~0.3-0.4 too low. Defer until n≥100/config."

**SYNTHESIS — major 3-way disagreement requires careful synthesis:**
- Trader: F (T5 push primary)
- Engineering: B+C (live-safe, contained code)
- Quant: E first, then F+B (math prerequisites)

**Compromise scope для S33:**

| Action | Rationale | Source |
|--------|-----------|--------|
| **1. Fix Q6 test debt + Q4 MC p-value** | Prerequisite math correctness | All 3 agents |
| **2. Implement E (DSR cross-trial)** — add `symbol: str` field, adjust `sigma_sr()` | Required для proper multi-symbol DSR | Quant |
| **3. F backtest measurement** — multi-symbol BTC+ETH+SOL 4H mean-reversion с S17-relaxed params (RSI 35/65, BB 1.5σ) | Closes T5 unreachability mathematically | Trader+Quant |
| **4. SKIP B (regime filter)** → S34 conditional на F results | Sequencing per S27 Q4 plan, не scope creep | Trader |
| **5. SKIP C (SL calibration)** → S35+ когда n≥100/config | Power too low | Quant |
| **6. SKIP live multi-symbol infra** → S34 dedicated sprint | Capital-split + orchestration = 650-850 LoC | Engineering |

S33 = backtest measurement sprint (zero new live code). Live deployment в S34.

### Q6 — Test debt fix в S33

**trader-expert (CONFIRM A):**
> "Fix 3 pytest + 1 mypy в начале S33. Failing tests obscure regression detection. **Important:** read failure tracebacks ПЕРЕД writing fixes. S27 T2/T3 changes (Sortino + RSI/ATR warm-up) modified replay_engine behavior — 'failures' may be test assertions that не были updated к reflect now-correct behavior, NOT code regressions. Fix mypy redef в same commit как S33 multi-symbol __main__.py changes."

**trading-logic-reviewer (CONFIRM A — root cause analysis):**
> "Likely root cause: `calculate_indicators` использует pandas `ewm(span=fast, adjust=False)` — needs minimum `fast+1` bars to show crossover. С `fast=2, slow=3` на 12-bar series + `shift(1)` line 92 = test produces zero `signal=1` events. **Test fixture broken by calculation change, NOT logic regression.** Fix = adjust fixture (longer series) OR adjust assertion.
> 
> mypy `bars_per_year_map` line 564 vs 636 — different function scopes. Either rename `bars_per_year_map_wfa` (2 lines) или `# type: ignore[no-redef]`. 1 LoC.
> 
> Estimate: ~65 LoC tests + 2 LoC src. Under 2 hours."

**quant-stats-reviewer (CONFIRM A — math implications):**
> "Test failures math-relevant. S27 T1 fix `bars_per_year` parameterization propagates через all replay-based metrics. Failing replay test indicates: (a) bars_per_year broke fixture hardcoded 4H, OR (b) test expects sqrt(8760) и engine passes different value. Either case = annualization factor inconsistent в test path → directly impacts reported Sharpe в 30-experiment sweep.
> 
> **If tests passing correct bars_per_year но formula wrong, 0/30 FAIL verdict may be based на miscalculated Sharpe.** Must confirm перед interpreting S33 results.
> 
> mypy `bars_per_year_map redef` likely consequence S27 T1 refactor — needs investigation для potential silent double-assignment."

**CONSENSUS A** — fix critical в начале S33. **Quant raises critical concern:** test failures may invalidate bars_per_year annualization path → S27 30-experiment sweep verdict trustworthy ONLY если replay tests confirm correct annualization. Investigate root cause first, не just patch.

---

## Cross-cutting concerns (CC)

**CC-A (от trader):** CC6 WFA 4H window = structural blocker не в original brief. train=2000 bars at 4H consumes nearly full year per IS fold, leaves only 1.3y OOS. 135-trade estimate для F rests на assumption 3.3y OOS. Affects Q1+Q4+Q5. MUST appear в S33 ADR pre-registration.

**CC-B (от trader):** Q2 REVISE makes Q3 CONFIRM more internally consistent. Если "in profit" accepted secondary live gate, correlated 3-simultaneous-loss scenario could satisfy "CB halted appropriately" while operator "in profit" on 1 symbol. Strict T1-T6 = gate set перед live deployment.

**CC-C (от trader):** S17-relaxed params (RSI 35/65, BB 1.5σ) MUST be explicitly named в S33 ADR. Three separate verdicts (Q1 binding #1, Q5 pre-spec, CC-C) require same pre-registration. Single most important anti-S15-recurrence safeguard.

**CC-D (NEW от quant):** MC p-value formula `(count+1)/(N+1)` per ADR 0015. Currently `count_extreme / n_iterations` produces p=0 when no permutation extreme — logically impossible с finite permutations. Pre-existing issue. **MUST fix перед S33 measurement** (otherwise reported MC p-values invalid).

**CC-E (NEW от quant):** t-stat heavy-tail correction. crypto excess kurtosis 5-15 → standard t-stat overconfident на small samples. `t_adj ≈ t × 1.37` для γ₄=5. Reported t=2.5 → adjusted t≈1.8. NO correction в `strategy_metrics.py`. Long-term concern, не blocking S33 (документировать risk).

**CC-F (NEW от quant):** `cross_trial_log.py::TrialEntry` schema has no `symbol` field. Multi-symbol DSR computation currently ambiguous. MUST add field перед F multi-symbol.

---

## ⚠️ Operator escalation items

Per `brainstorm-init` skill protocol — operator decides только product/regulatory/business choices:

### ESC-1 — Multi-symbol authorization (DECISION REQUIRED)

**Question для operator:** Authorize S33 BACKTEST measurement BTC+ETH+SOL multi-symbol 4H mean-reversion (zero new live code, validates F mathematically)? Live deployment infrastructure → S34 separate sprint.

**Recommended:** ✅ YES — backtest only. Engineering blockers reside в live deployment (Kelly capital-split + orchestration), не backtest.

**Если NO:** Per S24 Option E project pause — single-symbol BTC structurally closed (S22 binding insight T5=100 unreachable).

### ESC-2 — Acceptance gate semantics (CLARIFICATION)

**Question:** Confirm "in profit" = operational checklist POST T1-T6 PASS (live deployment pre-flight), NOT alternative/parallel statistical gate?

**Recommended:** ✅ YES (Option C with trader caveat). Documents в S33 ADR "Operator overrides" section if alternative.

### ESC-3 — 4H concurrent positions risk (ACK REQUIRED)

**Question:** Pre-approve 100% capital exposure during concurrent BTC+ETH+SOL LONG signals в S34 LIVE deployment? L1/L2/L3 circuit breakers = primary correlated-drawdown protection.

**Recommended:** ✅ YES с binding conditions:
- Operator explicit ack
- Quant correlation matrix added к risk/manager.py
- Multi-symbol data quality detector verification

### CC6 — WFA 4H window pre-registration (NEW BLOCKER)

**Question:** Choose WFA window для 4H multi-symbol:
- (a) Keep ADR 0014 defaults (train=2000/test=500 bars, accept 1.3y OOS, document limit)
- (b) Amend ADR 0014 для 4H-specific window (train=1000/test=250 bars, ~3.3y OOS)

**Both defensible.** Decision MUST happen перед sprint begins, не после seeing results (anti-data-snooping).

### CC-D — MC p-value formula fix (TRIVIAL FIX)

**Action:** Fix `src/backtest/mc_permutation.py:56` `count/N` → `(count+1)/(N+1)` per ADR 0015. **Operator confirms ADR 0015 binding (likely yes, just needs commit).**

### Q5 strategy direction — final synthesis

**Recommended S33 scope** (operator approve OR adjust):

1. **Fix test debt** (Q6): 3 pytest + 1 mypy. Investigate root cause first.
2. **Fix MC p-value formula** (CC-D): trivial 1-line fix per ADR 0015.
3. **Implement E** (DSR cross-trial extension): add `symbol: str` field к TrialEntry, adjust `sigma_sr()`.
4. **F backtest measurement**: multi-symbol BTC+ETH+SOL 4H mean-reversion, S17-relaxed params (RSI 35/65 + BB 1.5σ AND-gated).
5. **SKIP B/C** → S34/S35+.
6. **SKIP live multi-symbol infra** → S34 dedicated sprint.

КУ estimate S33: ~50% / ~6-10 hours (включая test debt fix + E impl + F measurement + ADR + sync).

---

## ROUND 2 evaluation

Per `brainstorm-init` BINDING protocol: ROUND 2 invoked **только** на REVISE-disagreement где chosen option ≠ maintainer recommendation.

| Q | Maintainer recommendation | Verdict | ROUND 2? |
|---|--------------------------|---------|----------|
| Q1 | A multi-symbol | trader EXPAND→A / eng REVISE→single-symbol / quant CONFIRM A с prereq | ⚠️ Engineering REVISE conflicts с trader+quant. **Resolution via synthesis** (backtest vs live split) — no ROUND 2 needed (engineering concern valid + addressed in synthesis). |
| Q2 | C both | trader REVISE→A strict / eng CONFIRM C / quant CONFIRM C | ⚠️ Trader minority REVISE. **Resolution via caveat** (operational checklist post-T1-T6, не parallel gate) — addresses S15 precedent concern. No ROUND 2 needed if operator confirms semantics. |
| Q3 | B 3 simultaneous | trader CONFIRM B / eng REVISE→S34 / quant EXPAND | Same pattern как Q1. Resolution via backtest/live split. |
| Q4 | A no further fixes | trader EXPAND CC6 / eng CONFIRM A / quant EXPAND 2 issues | EXPAND verdicts surface NEW gaps, не disagree с A. Action: address surfaced gaps. |
| Q5 | F+B | All 3 REVISE с **different options** (F / B+C / E first) | **3-way disagreement.** Synthesis = staged plan (E→F backtest, defer B/C). **Operator must approve synthesis OR pick alternative.** |
| Q6 | A fix critical | All 3 CONFIRM A | No disagreement. |

**ROUND 2 trigger assessment:** Q1+Q3 disagreements resolved via backtest/live scope split (engineering concern accommodated). Q5 = operator decision на synthesis vs alternatives. Q2 = caveat documents trader concern. **ROUND 2 not invoked** — synthesis path acceptable to all 3 agents.

**If operator REJECTS synthesis Q5 (e.g., wants live multi-symbol в S33):** ROUND 2 dispatched к engineering для re-evaluation (forced multi-symbol live с infrastructure shortcuts? OR force trader/quant accept single-symbol?).

---

## Carry-overs (preserved для S34+)

- **Live multi-symbol infrastructure** (650-850 LoC): Kelly capital-split + Coordinator orchestration + WAL retry + halt cascade isolation
- **B regime filter SMA50** (S34 conditional): if F results show fold concentration ≥ S20 fold #2 (-185.21)
- **C SL calibration** (S35+): when n ≥ 100/configuration
- **t-stat heavy-tail correction** (CC-E): Hudson&Urquhart 2021 — long-term math improvement
- **bybit-api-reviewer first invocation** validation (S33+ Bybit-touching code)
- **5 dormant L5 reviewers validation** (parallel dispatch S33 first code task)

---

---

## ROUND 2 — Consilium consolidated (2026-04-27)

Operator delegated escalation decisions BACK к 3 agents. ROUND 2 vote + brainstorm extras dispatched parallel.

### Vote summary (all 6 items APPROVED unanimously)

| Item | trader | trading-logic | quant-stats | Consensus |
|------|--------|---------------|-------------|-----------|
| ESC-1 BACKTEST F | APPROVE | APPROVE | APPROVE | ✅ APPROVE |
| ESC-2 in-profit checklist | APPROVE | APPROVE | APPROVE +amend | ✅ APPROVE — explicit POST T1-T6, never parallel bypass |
| ESC-3 S34 LIVE binding | APPROVE +amend (halt-cascade isolation 4th condition) | APPROVE +caveat | APPROVE +math condition (correlation matrix) | ✅ APPROVE + **4 binding conditions:** operator ack + Kelly capital-split + correlation matrix + halt-cascade isolation |
| CC6 WFA 4H window | (b) | (b) | (b) | ✅ **(b) train=1000/test=250 ~3.3y OOS** (OOS/IS ratio preserved 0.25, ADR 0014 gate unchanged) |
| CC-D MC p-value fix | APPROVE | APPROVE +property test | APPROVE +extends к block_bootstrap line 96 | ✅ APPROVE + **scope extension:** fix BOTH `sign_flip_p_value:56` + `block_bootstrap_p_value:96` (same bug) |
| Q5 synth | APPROVE +amend (pooling protocol pre-spec) | APPROVE | APPROVE | ✅ APPROVE |

### Final positions

- trader: **CONFIRM_REVISE** (Round 1 stands) + 2 amendments (ESC-3 4th condition + Q5 pooling pre-spec)
- trading-logic: **CONFIRM_REVISE** + UPGRADE ESC-1/3 vote от REVISE→APPROVE (backtest/live split addresses engineering concern)
- quant-stats: **CONFIRM_REVISE** + 1 clarification (CC6 explicit (b) vote)

### 13 REQUIRED additions для S33 scope (consolidated после dedup)

1. **CC-D extended scope** — fix MC p-value `count/N` → `(count+1)/(N+1)` per ADR 0015 в BOTH `sign_flip_p_value:56` AND `block_bootstrap_p_value:96` (same bug, both lines)
2. **Property test для MC invariants** — Hypothesis-based: `mc_p_value > 0` always, `1/(N+1) ≤ p ≤ 1`, monotonic в `count_extreme`. Catches CC-D regression. ~30 LoC.
3. **ESC-3 4th binding condition:** halt-cascade isolation specification (BTC halt → ETH/SOL behavior). Uncovered by capital-split / CB layer.
4. **Pre-registration checklist 9-item locked list** для S33 ADR ДО measurement: (1) exact param set RSI 35/65 BB 1.5σ no further tuning / (2) WFA train=1000/test=250 / (3) embargo 20 bars / (4) OOS gate OOS/IS ≥ 0.7 / (5) symbols BTC+ETH+SOL no additions / (6) MC p ≤ 0.05 two-tailed / (7) DSR ≥ 0.95 / (8) n_trials counting protocol / (9) sigma_SR pooling protocol
5. **S17-relaxed params named constant** (anti-S15-recurrence guard) — `MEAN_REVERSION_S17_RELAXED_PARAMS` defined в S33 ADR + referenced в code, не copy-paste от S15 (RSI 30/70 BB 2σ MC p=0.998 noise)
6. **DSR pooling protocol pre-spec** (Item Q5 amend от trader+quant): (a) pool all (sprint, symbol) pairs as independent trials → n_trials=3 per multi-symbol sprint OR (b) treat sprint as 1 trial с aggregate OOS Sharpe → n_trials=1. **Recommend (a)** per quant — methodologically more honest. Lock в S33 ADR.
7. **n_trials counter rule** (related к #6): if (a), `cross_trial_log` adds 3 entries per S33 sprint (BTC + ETH + SOL each separate trial)
8. **n_eff correction в reporting** — report raw n + n_eff = n / (1 + (m-1)*rho) where m=3, rho≈0.75 → n_eff ≈ n/2.5. Document raw vs effective в S33 measurement output. T-stat denominator should use n_eff per Kish 1965 design effect correction.
9. **TrialEntry schema migration guard** — backfill default `symbol="BTCUSDT"` для existing pre-S33 entries, OR archive `cross_trial_sharpes.json` к `_v0.5-final.json` + reset (mirror S16/S18/S21/S23). +5 LoC src defensive get + 10 LoC tests.
10. **WFA fold coverage pre-run validation** — assert `len(ohlcv_df) >= (train_bars + test_bars) * n_folds` per symbol перед sweep starts. SOL Bybit listing date may give fewer 4H bars чем BTC — silent fold-skip risk. +20 LoC src + 15 LoC tests.
11. **bars_per_year annualization path verification test** — 4H-specific assertion `bars_per_year(interval="4H") == 2190` propagates through replay engine `sharpe_ratio` computation, не just unit test of function isolation. +20 LoC tests.
12. **Pre-committed failure branch для F** (insurance) — S33 ADR MUST include "if F fails T5 OR MC p>0.10, S34 = honest close v0.6 OR operator-driven spec amendment с explicit statistical-framework override statement" ПЕРЕД measurement (mirror S17/S22/ADR 0032/0037 BINDING precedent).
13. **CI baseline guard update** — `.github/workflows/ci.yml` baseline 773 passed needs update post-S33 test additions (~60-80 new tests). Otherwise CI guard becomes permanently non-binding.

### 2 OPTIONAL additions

14. **Ruff baseline file-scoped clean-on-touch** — каждый touched file ruff-clean on exit, не just CI guard-compliant. Prevents gradual drift (compounds к S34+ baseline degradation). ~5 min/file.
15. **Reviewer dispatch plan documented в S33 ADR** — S33 = formula/stats only → `quant-stats-reviewer` + `trading-logic-reviewer` only. Skip 5 dormant agents (`python-reviewer`, `architecture-reviewer`, `data-integrity-reviewer`, `security-auditor`, `bybit-api-reviewer`) для pure-backtest sprint. Anti-token-waste.

### S33 scope summary post-ROUND 2

**Original synthesis (6 actions) + 13 required + 2 optional = ~21 items total.** Estimate revised: **8-12 hours** (previous estimate 6-10h was naive — pre-registration discipline + property tests + schema migration add ~30% effort).

**Estimate breakdown:**
- T1: Q6 test debt fix + investigate root cause (1-2h per engineering analysis)
- T2: CC-D fix BOTH MC formulas + Item #2 property tests (1h)
- T3: E impl (DSR cross-trial: TrialEntry schema + migration guard + sigma_SR pooling) (2-3h)
- T4: Item #11 bars_per_year integration test + Item #10 WFA fold coverage validation (1-2h)
- T5: F backtest measurement run (BTC+ETH+SOL 4H mean-reversion S17-relaxed params, WFA train=1000/test=250) (2h compute time)
- T6: ADR 0050 + S33 sprint page + 9-item pre-registration checklist + Item #5 named constant + Item #12 failure branch (1-2h)
- Phase 5/7/8/9 standard (1-2h)

**Total: ~8-12 hours.**

- `brainstorm-init` skill (`.claude/skills/brainstorm-init/SKILL.md`) — PHASE 2 binding protocol
- ADR 0048 (S32d Kit Phase 3 final) — 8 candidate directions A-H
- ADR 0049 (S32e Kit Audit) — kit ready S33
- Sprint S22 (BTC 4H PASS partial) — S17-relaxed params reference
- Sprint S23 (v0.5 honest close) — T5=100 binding insight
- Sprint S27 (formula bug fixes) — CC6 WFA 4H window unaddressed
- Sprint S15 (multi-symbol failure) — anti-S15-recurrence learnings
- Hudson & Urquhart 2021 (heavy-tail t-stat critique) — CC-E reference
- Bailey & López de Prado (DSR + cross-trial) — quant prerequisite

---

## S34 Direction Consilium (post-S33 ship, 2026-04-27)

Operator delegated S34 direction к 3-agent consilium. Vote table:

### Vote summary

| Path | trader-expert | trading-logic | quant-stats | Consensus |
|------|---------------|---------------|-------------|-----------|
| **A(a) project pause** | APPROVE (default acceptable, equally defensible) | CONFIRM (clean, low-effort close) | RECOMMENDED (most rigorous) | ✅ ACCEPTABLE FALLBACK |
| **A(b) T5 floor amendment** | CONDITIONAL APPROVE (mandatory 10-item pre-commit list) | CONFIRM (minimal LoC, no new code paths) | DEFENSIBLE с conditions | ✅ **PRIMARY RECOMMENDED** |
| A(c-Donchian) | REJECT (no cheap falsification) | REVISE (FSM SHORT guard blocker — long_only=True invariant) | NOT recommended (N_trials penalty) | ❌ REJECT |
| A(c-ML XGBoost) | REJECT (n_eff=26 makes ML infeasible) | REVISE (HIGH effort 500-800 LoC + new deps) | NOT recommended (overfitting) | ❌ REJECT |
| A(c-HMM) | REJECT | REVISE (HIGH effort 400-600 LoC) | NOT recommended | ❌ REJECT |
| A(d) different timeframe (1D) | REJECT (T5 worse, not better — fewer trades) | CONCERN (pre-check needed: n_trades on 1D likely < T5) | NOT recommended (same T5 problem worse) | ❌ REJECT |
| **B override gates** | REJECT (precedent risk) | REVISE (real-money loss risk) | NOT recommended (abandons rigor) | ❌ STRONG REJECT |

### Final positions

- trader: CONFIRM_REVISE — A(b) с 10-item mandatory pre-commitment list
- trading-logic: CONFIRM_REVISE — A(b) primary / A(a) fallback / REVISE on Donchian (FSM blocker), ML/HMM (effort)
- quant-stats: (response truncated; institutional memory updated `memory_neff_asymptote_kish.md`; prior consistent с A(b) defensible + A(a) most rigorous)

### Mandatory pre-commitments S34 ADR (per trader 10-item list)

If operator chooses A(b), S34 ADR MUST lock следующее ДО measurement:

1. **T5 floor: 100 → 50** (cite Hudson & Urquhart 2021 crypto sparse-signal reality)
2. **n_eff threshold: ≥ 50** — n_eff applies Kish 1965 correction; raw n does NOT substitute (S33 lesson)
3. **MC threshold: ≤ 0.05** (tightened from 0.10 — partial compensation для floor relaxation)
4. **T6 OOS/IS: ≥ 0.7 UNCHANGED** — independently blocking, not relaxed
5. **acceptance_gate.sharpe_gate_passed: UNCHANGED** — fold-level gates remain at existing thresholds
6. **Operator written acknowledgment:** "Statistical evidence as of v0.6 DOES NOT support live deployment; this amendment reflects crypto-specific sample-size reality (Hudson & Urquhart 2021), not evidence of positive edge"
7. **Strategy params: `MEAN_REVERSION_S17_RELAXED_PARAMS` LOCKED** — no new parameter search permitted (anti-snooping)
8. **Backtest data period:** must extend through full available OHLCV history beyond S33 measurement date
9. **Multi-symbol: n_eff correction mandatory** — rho и Kish factor pre-registered
10. **N_trials counter starts ≥ 4** (accumulating prior trials в sigma_SR pooling)

### Engineering caveat (trading-logic)

A(b) gate change ~20 LoC + 5-10 tests + ADR amendment. **CRITICAL:** if amended gate STILL fails на S33 data (n_eff=26 < n_eff_threshold=50), operator MUST choose A(a) — gate change alone не enough.

**Pre-check before A(b) implementation:** check whether existing data (no new measurement) clears amended gates. If не clears — A(a).

### Strong reject Option B

ALL 3 agents REJECT B (override gates):
- trader: precedent risk + sets dangerous norm
- trading-logic: real-money loss risk (strategy demonstrated negative OOS edge — fold #3 BTC -32.68 catastrophic)
- quant: abandons statistical rigor

### S34 path forward

**Recommended (consensus):** A(b) с 10-item pre-commit list — minimal effort, leverages existing infra, scientifically defensible if conditions honored.

**Acceptable fallback:** A(a) project pause — most rigorous if operator concludes strategy class exhausted.

**STRONGLY REJECTED:** B override + A(c-ML/HMM/Donchian) + A(d) 1D timeframe.
