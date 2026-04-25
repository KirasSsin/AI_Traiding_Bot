---
title: Pre-S13 backlog — brainstorm verdicts trail (post-revert fresh start)
type: backlog
tags: [sprint-13, brainstorm, phase-2, verdicts, trader-expert, mvp-completion, post-revert]
created: 2026-04-25
updated: 2026-04-25
status: open
sources:
  - project/decisions/0014-walk-forward-train2000-test500.md
  - project/decisions/0016-bybit-spot-supersedes-binance.md
  - project/decisions/0027-sprint-12-live-demo-validation.md
  - project/architecture/acceptance-criteria.md
  - project/architecture/migration-plan.md
  - project/runbooks/live-demo-validation.md
---

# Pre-S13 backlog — fresh start

## Context (post-revert)

Prior S13 attempt aborted. Branch `feature/sprint-13-strategy-validation` deleted (9 commits, never pushed). Hot-fix `562d385` preserved on main (real production `_cmd_monitor` SQL bug found during 33min S12 demo validation start).

User direction: "**закончим MVP по старому описанию, без вводных что мы начали в 13 спринте**". Implies follow original migration-plan.md roadmap + acceptance-criteria.md gating flow без S13-introduced scope creep (dashboard wire + verdict_classifier были Q9/Q10 user-additive scope в discarded attempt).

## Critical context inherited (knowledge preserved, code wiped)

Prior S13 attempt ran T1-T6 measurement on existing 2.2y BTCUSDT 1H Parquet:
- **Verdict: HARD_FAIL**
- T1 Sharpe OOS: **-44.46** (auto HARD FAIL trigger: < 0)
- T2 Sortino OOS: -101.38
- T3 MaxDD: 1.1% (PASS)
- T4 Win rate: 30% @ avg RR 0.80 (FAIL)
- T5 n_trades OOS: **20** (FAIL — < 100 threshold)
- T6 OOS/IS Sharpe ratio: 1.14 (PASS)
- DSR: 0.045 (positive, informational)
- MC p-value: 0.048 (borderline pass)
- 4/6 criteria failed (t1, t2, t4, t5)

**Sample size critically low** (20 OOS trades) — verdict potentially noise-dominated. Per ADR 0014: K=5 folds × 500 test bars each = 2500 OOS bars; with EMA crossover на 1H = ~1-3 trades/week → 20 trades plausible но statistically under-powered.

User explicit response к prior ESC-1 (HARD FAIL pivot decision): **(c) Defer — see actual numbers, decide case-by-case**. Numbers seen → user pivoted к "восстановить S12 ship state, начать заново с старым flow".

## Project endpoint (immutable)

`acceptance-criteria.md` — 12 gating criteria для MVP DONE:
- System-level (S1-S6): infrastructure works
- Strategy-level (T1-T6): OOS only, MUST PASS перед Mainnet promotion
- DSR > 0, PBO < 0.5 supporting

**T1-T6 PASS = MVP DONE precondition.** Cannot skip per gating flow step 4-5.

## S13 PHASE 2 brainstorming questions (8 questions)

### Q1 — S13 scope ordering: 48h validation FIRST OR backtest re-attempt FIRST

**Question:** Per restored SPRINT_STATE next_action: "ACTIVE: 48h Bybit demo validation". User said "old flow". Options для S13 sequencing:

**Maintainer recommended option:** (b) Backtest re-attempt FIRST (5y backfill + WFA T1-T6 measurement) since 48h demo expects 0-3 trades anyway (per Q3 zero-trade clause) и не resolves T1-T6 gate.

**Alternatives considered:**
- (a) **48h validation first** — per restored SPRINT_STATE, original "old flow" — но не measures T1-T6, only structural infrastructure check. Statistically expected: 0 trades in 48h на 1H BTC EMA crossover. Calendar 2 days operator time.
- (b) **Backtest re-attempt first** (5y backfill 2020-2026 + WFA с bigger sample) — directly addresses HARD FAIL "small sample" hypothesis, gives definitive answer about edge existence. Calendar 1-2 sprints.
- (c) **Both в parallel** — operator runs 48h passive, dev builds backfill + WFA — но scope creep, 2 deliverables.
- (d) **48h skipped** — accept что 48h adds little vs T1-T6 gate; jump direct к backtest re-measurement.

**Reasoning for recommended:**
- Per Q3 from prior S12 brainstorm (CONFIRMED): "zero-trade clause MANDATORY — 0-3 trades expected during 48h на 1H BTC EMA crossover"
- 48h validation = infrastructure check (FSM/reconcile/WS uptime), NOT edge validation
- T1-T6 = MVP gate per acceptance-criteria.md — must measure regardless
- Bigger sample (5y vs 2.2y) directly addresses "20 OOS trades = under-powered" finding
- Bybit V5 spot kline pagination available для backfill (per BybitRESTClient existing)

**Risk/concern:**
- Bybit Spot data може start later than 2020 (Bybit launched 2018, but spot trading may be later) → may need Binance fallback (ADR 0016 supersession concern)
- Backfill = ~5 min one-time vs 48h validation calendar — much faster path к verdict
- HIDDEN ASSUMPTION: bigger sample WILL flip HARD_FAIL → PASS (NOT guaranteed; could just confirm "no edge" с tighter confidence)

---

### Q2 — Если backtest re-attempt: scope per-sprint OR multi-sprint

**Question:** Backtest re-attempt = how to break in deliverables: single sprint OR split?

**Maintainer recommended option:** (b) Split — S13 = backfill + data infra; S14 = re-measurement + verdict.

**Alternatives considered:**
- (a) Single sprint (all-in-one) — backfill + WFA + verdict + dashboard wire — large scope (~10 tasks), risk subagent fatigue
- (b) **Split:** S13 backfill ONLY (wire `_cmd_backfill` from STUB к BybitRESTClient pagination + data_collector Parquet write) + S14 measurement (re-use prior S13 attempt code patterns: trade_extractor + strategy_metrics + verdict_classifier) — clean separation
- (c) Skip backfill (accept 2.2y limitation) → re-attempt с different strategy params (revision per ESC-1 option a) — but Q3 limit "exactly 1 tuning iter" means precarious

**Reasoning for recommended:**
- Backfill = mechanical task (wire existing components), good 1-sprint scope
- Measurement re-attempt benefits from prior code patterns но needs fresh write (we discarded)
- Split prevents "S13 = HUGE" anti-pattern, matches kit discipline

**Risk/concern:**
- Sequential = +1 sprint calendar (~1 week) vs parallel
- HIDDEN: prior S13 code wiped — we know patterns но need rewrite, not just resurrect

---

### Q3 — Backfill data source: Bybit Spot OR Binance fallback

**Question:** Bybit Spot may not have 5y BTCUSDT 1H data (launched 2018, spot trading later). Binance has 8+ years. What's the source?

**Maintainer recommended option:** (a) Try Bybit Spot first; if pre-2020 data unavailable, document gap honestly (start from earliest available) — preserve venue consistency per ADR 0016.

**Alternatives considered:**
- (a) **Bybit Spot only** — venue consistency per ADR 0016 (supersedes Binance). Если 2020+ available, use as-is. Document gap.
- (b) Binance fallback для pre-2020 — wider sample but venue mismatch (different fees/spreads)
- (c) Hybrid: Bybit для Bybit-available period + Binance для earlier — comparable BTC price across venues, но liquidity/spread different

**Reasoning for recommended:**
- ADR 0016 explicit: Bybit Spot supersedes Binance — venue consistency matters для realistic backtest
- BTC price across major venues highly correlated (~0.999) — minor venue difference negligible at 1H granularity
- Documented gap > silent venue mixing
- Operational simplicity: single venue API

**Risk/concern:**
- Если Bybit Spot 1H data starts 2022 → only 4y available, не much wider than current 2.2y
- HIDDEN: API rate limits на pagination (Bybit V5 — 5 req/sec) — backfill 5y × 8760 bars = 43800 bars ÷ 1000 per call = ~44 calls = manageable
- Если verdict still HARD FAIL on 5y → "no edge" confirmed более confidently

---

### Q4 — Acceptance-criteria.md gating flow expectation

**Question:** Original gating flow specifies "Walk-Forward + K=5 CV на 5 лет BTC 1H". Per S10 ADR 0025 + Q1 ADR 0028: existing 2.2y data adequate per WFA math (19441/5=3888 bars/fold > 2520 required). Stick с 2.2y OR enforce 5y per spec literal?

**Maintainer recommended option:** (a) Enforce 5y per spec literal — MVP gating flow says "5 лет", interpret literally, не accept 2.2y subset.

**Alternatives considered:**
- (a) **Enforce 5y** — spec literal interpretation, full statistical power
- (b) Accept 2.2y (math-justified) — current data adequate per ADR 0014 fold math
- (c) Tiered: 2.2y first (quick check), if verdict ambiguous → 5y (definitive)

**Reasoning for recommended:**
- Spec literally says "5 лет" — operator commitment trail
- 5y data captures multiple regimes (bear 2022, bull 2021, recovery 2023-2025)
- Bear-regime gap explicitly flagged как concern в prior CC2
- Doing it right ONCE > re-running multiple times с increasing N_trials

**Risk/concern:**
- If 5y still HARD FAIL → strong "no edge" verdict, no future "more data may help" excuse
- HIDDEN: Bybit может not have 5y → triggers Q3 venue decision

---

### Q5 — DSR + PBO gating activation

**Question:** Acceptance-criteria.md spec: "Gate: все T1-T6 green AND DSR > 0 AND PBO < 0.5". Prior S13 attempt computed DSR (0.045 PASS) but NOT PBO (Probability of Backtest Overfit). Activate full gate в S14 measurement OR defer PBO?

**Maintainer recommended option:** (b) Activate DSR gate + defer PBO к S15+ (PBO requires multi-strategy backtest infrastructure not implemented).

**Alternatives considered:**
- (a) Full gate including PBO — но PBO needs MCS (Monte Carlo Strategy Selection) framework, ~3 sprints scope
- (b) **DSR active, PBO deferred** — DSR formula-invariant (per Q7 prior), no extra infra; PBO defer until needed
- (c) Both deferred — accept T1-T6 only — но spec literal violation

**Reasoning for recommended:**
- DSR = single-strategy metric, computable via existing dsr.py (S9+S10)
- PBO = multi-strategy framework (López de Prado AFML Ch.11) — significant scope expansion
- Acceptance-criteria.md says "supporting metrics" для DSR/PBO — interpreted: required для PASS-decision но calibration timeline flexible

**Risk/concern:**
- Spec literal interpretation conflicts с pragmatic deferral
- HIDDEN: если strategy ultimately PASS T1-T6 + DSR but PBO would FAIL → false positive PASS verdict

---

### Q6 — 48h validation: skip OR run as separate operator activity

**Question:** Per restored SPRINT_STATE: 48h Bybit demo validation = next_action. Per Q1 recommended: backtest first. So 48h validation = skip OR run separately when ready?

**Maintainer recommended option:** (b) Decouple — run 48h validation в parallel-track operator activity, NOT block sprint cadence.

**Alternatives considered:**
- (a) Block S13 на 48h (sequential) — adds 2 days calendar
- (b) **Decouple:** 48h validation = operator background activity, не gates code sprint progression
- (c) Skip 48h entirely — но not measured = unknown infrastructure quality

**Reasoning for recommended:**
- 48h validation = infrastructure test (FSM/reconcile/WS), parallel к code work
- Сode sprint (backfill + WFA re-measure) doesn't need live demo running
- Operator can run 48h whenever convenient

**Risk/concern:**
- Если 48h surfaces critical bug (per 33min surfaced monitor SQL) → blocks future Mainnet anyway
- HIDDEN: operator may forget OR delay

---

### Q7 — HARD FAIL response framework (re-confirm ESC-1)

**Question:** Prior ESC-1 = (c) "defer — see actual numbers, decide case-by-case". Numbers seen (HARD_FAIL on 2.2y). User pivoted к re-start с old flow + bigger sample. Re-confirm ESC-1 framework для NEW S14 measurement verdict?

**Maintainer recommended option:** (c) Same defer pattern — see actual S14 5y verdict, decide case-by-case (not pre-commit к pivot direction).

**Alternatives considered:**
- (a) Pre-commit "PASS → Mainnet, FAIL → abandon" — clean binary
- (b) Pre-commit "PASS → Mainnet, FAIL → 1 tuning iter, FAIL again → abandon" — Q3-style discipline
- (c) **Defer same pattern** — operator (user) sees S14 numbers, decides
- (d) Pre-commit "FAIL → switch к different strategy family" — abandons EMA crossover entirely

**Reasoning for recommended:**
- Repetitive defer = no decision-making burden upfront
- Numbers may be ambiguous (T1-T6 PASS but DSR < 0; OR T1 PASS but n_trades=80 < 100)
- Case-by-case allows nuanced response

**Risk/concern:**
- Defer = operator decision burden every iteration
- HIDDEN: defer may delay project closure indefinitely если verdicts always borderline

---

### Q8 — Dashboard scope: re-include OR strict skip per "without S13-introduced"

**Question:** User direction said "без вводных что мы начали в 13 спринте" — implies skip dashboard (Q10 was user-additive scope в discarded attempt). НО dashboard reuses existing `web/dashboard.html` artifact already в repo. Skip altogether OR include в data path?

**Maintainer recommended option:** (a) Skip — strict literal "without S13-introduced". Existing HTML stays as live trading mockup. CLI JSON output only for backtest.

**Alternatives considered:**
- (a) **Skip dashboard wire** — strict adherence к user direction; CLI JSON sufficient для verdict review
- (b) Minimal include — only data.json writer (no HTML changes) — half-step
- (c) Full include — dashboard wire from prior attempt — re-introduces "S13 scope creep" user wanted к skip

**Reasoning for recommended:**
- User explicit: skip "S13-introduced" scope
- CLI JSON output sufficient for verdict (already implemented in existing _cmd_wfa)
- Dashboard wire = optional UX, не affects verdict accuracy

**Risk/concern:**
- Operator может want visual review для T1-T6 verdict — CLI JSON less ergonomic
- HIDDEN: rebuilding dashboard later = same scope work, just deferred

---

## ROUND 1 verdicts (TRADER-EXPERT, complete)

**CC1 verification (mandatory):** Trader Q4 spec inconsistency claim VERIFIED via grep:
- `acceptance-criteria.md` line 53: "Walk-Forward + K=5 CV на **5 лет** BTC 1H"
- `migration-plan.md` S7 AC: "Walk-forward на **2y** BTC 1H-данных"
- **Internal contradiction в spec — CONFIRMED.** Trader Q4 REVISE = factual correction, не engineering judgment dispute. Same pattern as S12 Q6 (endpoint string).

| # | Question | ROUND 1 verdict | Type | Final accepted | Wiki/code follow-ups |
|---|----------|-----------------|------|----------------|----------------------|
| Q1 | S13 scope ordering | **CONFIRM** | agree | (b) Backtest re-attempt first | — |
| Q2 | Sprint split granularity | **EXPAND** | reframe | Conditional split based on Bybit data availability check (PHASE 3 step 1: REST probe earliest 1H BTCUSDT timestamp) | PHASE 3 add data availability pre-check |
| Q3 | Backfill venue source | **CONFIRM** | agree | (a) Bybit only, document gap | — |
| Q4 | 5y enforcement | **REVISE-FACTUAL** | spec inconsistency caught | (c) Tiered: ≥3.5y → use, <3.5y → escalate user. Strict 5y rejected (acceptance-criteria 5y vs migration-plan 2y contradiction) | **Reconcile spec docs**: amend acceptance-criteria.md gating step 1 + ESC-2 user acknowledgment relaxation |
| Q5 | DSR + PBO gating | **CONFIRM** | agree | (b) DSR active, PBO defer S15+ | — |
| Q6 | 48h validation timing | **CONFIRM** | agree | (b) Decouple — operator parallel track, не block sprint | Operator briefing: 48h NOT optional, run before Mainnet |
| Q7 | HARD FAIL response framework | **REVISE-DISAGREE** | challenges prior ESC-1=c | (b) Pre-commit framework: PARTIAL FAIL → exactly 1 tuning iter с pre-specified params → re-measure (N_trials=2) → any FAIL = HARD FAIL abandon. Auto HARD FAIL: T1 < 0 OR T3 > 35%. **REQUIRES USER RE-AUTHORIZATION (ESC-1)** | Override prior ESC-1=c defer pattern |
| Q8 | Dashboard scope | **CONFIRM** | agree | (a) Skip dashboard wire, CLI JSON sufficient | — |

## ROUND 2 status

**NOT INVOKED.** Two REVISE verdicts но neither warrants ROUND 2 trader iteration:

- **Q4** = factual correction of verified spec inconsistency (similar to S12 Q6 endpoint pattern). Trader provided source-cited evidence. Maintainer verified via grep (CC1). Accept REVISE; outcome decision = user product call (ESC-2 — relaxation of "5 лет" spec).
- **Q7** = trader re-asserts pre-commit discipline matching prior accepted ESC-1 framework (S13 prior attempt Q3 trader REVISE was identical structure). Это challenges user's previous ESC-1=c "defer-defer" choice. Per dev-workflow.md PHASE 2 step 7: user has authority on ESC items. **Escalate к user re-authorization** (ESC-1 RE-OPENED).

## Cross-cutting concerns (trader-flagged)

1. **CC1 (Q5+Q7) — N_trials tracking binding infrastructure:** Pre-commit HARD FAIL framework (Q7 REVISE) relies on accurate N_trials increment per measurement. Must be deliverable в S13 ADR, не aspirational note. DSR multi-testing correction (Bailey 2014) requires bounded N_trials.
2. **CC2 (Q3+Q4) — Bybit data availability = single biggest unknown:** PHASE 3 step 1 = REST API probe для earliest 1H BTCUSDT timestamp (2-min check). Resolves Q2 (split decision) + Q4 (target span) simultaneously.
3. **CC3 (Q7+acceptance-criteria) — Spec literal vs executable gate:** acceptance-criteria.md says "T1-T6 + DSR > 0 + PBO < 0.5". PBO deferred (Q5). ADR 0028 must explicitly document gate relaxation: "T1-T6 + DSR > 0; PBO defer pending MCS framework S15+".
4. **CC4 (Q4) — migration-plan vs acceptance-criteria contradiction:** "5 лет" vs "2y" — same project doc family, factually contradicts. Maintainer reconcile BEFORE PHASE 3 plan write. Это documentation correction, не judgment call.

## Escalation list для user (product/regulatory/business)

**ESC-1 RE-OPENED — Q7 pre-commit framework user authorization:**

Trader proposes binding pre-commit:
- **PASS:** all T1-T6 green + DSR > 0 → S14 Mainnet pilot Phase 1
- **PARTIAL FAIL:** 1-2 criteria miss (no auto-trigger) → exactly 1 pre-specified parameter adjustment → re-measure (N_trials=2) → any FAIL = HARD FAIL abandon
- **HARD FAIL:** auto-trigger (T1 Sharpe < 0 OR T3 MaxDD > 35%) OR 3+ criteria miss → immediate abandon EMA crossover family

**Question к user:** "Authorize Q7 pre-commit framework? Or re-confirm prior ESC-1=c defer-defer pattern (с risk of unbounded p-hacking iterations + DSR degradation)?"

**ESC-2 NEW — Q4 spec relaxation user acknowledgment:**

acceptance-criteria.md says "5 лет" literal. Trader proposes accept "max available Bybit data, floor 3.5y" из-за spec inconsistency с migration-plan.md (says 2y).

**Question к user:** "Acknowledge spec relaxation: '5 лет' → 'max available Bybit data, floor 3.5y'? Or enforce literal '5 лет' (forces Binance fallback violating ADR 0016 OR project block если Bybit < 5y available)?"

## Maintainer follow-ups (post-verdict)

- ✅ Verify Q4 spec inconsistency via grep (CC1) — VERIFIED
- ✅ Surface ESC-1 RE-OPENED + ESC-2 NEW к user

## USER FINAL DECISIONS (binding)

**User direction (verbatim):** "Давай по этому плану пойдём, там если что нас subagent трейдер сориентирует. Если есть что обновить, измени документацию и давай этого плана придерживаться."

User explicitly endorsed earlier maintainer-written roadmap (post-S12 ship section). Implicit decisions:

### ESC-1 RE-OPENED — DEFER pattern preserved (REJECT trader Q7 REVISE)

User's roadmap text: "S15 — Strategy gating verdict. T1-T6 pass? → mainnet promotion plan. T1-T6 fail? → strategy revision sprint OR project pivot decision".

This = case-by-case decision pattern, NOT pre-commit framework. User implicitly REJECTS trader Q7 pre-commit ("exactly 1 tuning iter" discipline). Original ESC-1=c "defer pattern" preserved.

**Risk acknowledged (per trader Q7 reasoning):** unbounded N_trials degrades DSR multi-testing correction over time. Maintainer must track N_trials explicitly per measurement attempt + surface DSR degradation в each gating decision.

### ESC-2 NEW — Tiered 5y target accepted (ACCEPT trader Q4 REVISE)

User's roadmap: "Backfill 5 лет BTC/USDT 1H + run python -m src wfa --start 2020 --end 2025". 5y literal target.

Per trader Q4 REVISE: если Bybit Spot не provides 5y → use max available (floor 3.5y per trader). PHASE 3 step 1 = REST API probe earliest 1H BTCUSDT timestamp determines actual span.

**Decision:** Target 5y, fallback к max-available-floor-3.5y. NOT enforce literal 5y если Bybit doesn't provide.

### S13 scope — (b) Backfill 5y data + WFA T1-T6 measurement

Per user's roadmap "S13 = pick ONE" + maintainer recommendation in earlier message + trader Q1 CONFIRM. Other candidates (a, c, d) deferred.

### Multi-sprint roadmap accepted (per maintainer's earlier message)

| Sprint | Scope | Calendar |
|--------|-------|----------|
| **S13** | Backfill 5y + WFA T1-T6 measurement | 1 sprint |
| **S14** | DSR threshold calibration + per-fold trade extraction (closes S10/S12 carry-over) | 1 sprint |
| **S15** | Strategy gating verdict (PASS → S16 Mainnet; FAIL → revision OR abandon decision) | 1 sprint |
| **S16-S19** | Mainnet pilot Kelly Phase 1→4 progression (calendar-gated, не development) | 6-12 months |
| **S20** | 30d uptime test + MVP DONE acceptance review | 1 sprint |

## Spec reconciliation (CC4 — amend acceptance-criteria.md)

`acceptance-criteria.md` gating step 1 says "5 лет BTC 1H" but `migration-plan.md` S7 AC says "2y BTC 1H". Internal contradiction. **Amend acceptance-criteria.md** к add reconciliation note: "5 лет = aspirational target; в practice — max available Bybit Spot data (floor 3.5y for K=5 fold statistical adequacy per ADR 0014). migration-plan.md S7 '2y' = retrospective minimum."

## Related

- [[decisions/0014-walk-forward-train2000-test500]] — WFA params
- [[decisions/0016-bybit-spot-supersedes-binance]] — venue policy (Q3 conflict point)
- [[decisions/0027-sprint-12-live-demo-validation]] — predecessor sprint
- [[architecture/acceptance-criteria]] — 12 gating criteria
- [[architecture/migration-plan]] — original 10-sprint roadmap
- [[runbooks/live-demo-validation]] — 48h validation playbook (Q6)
