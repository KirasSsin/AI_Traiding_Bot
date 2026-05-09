---
title: Pre-S15 backlog — v0.2 retry direction (post-S14 honest close)
type: backlog
tags: [sprint-15, brainstorm, phase-2, verdicts, trader-expert, architecture-reviewer, v0.2-retry, post-mvp-direction]
created: 2026-04-26
updated: 2026-04-26
status: open
sources:
  - project/decisions/0029-sprint-14-honest-close.md
  - project/sprints/sprint-14-honest-close.md
  - project/decisions/0002-python-only-for-mvp.md
  - project/decisions/0005-1h-timeframe-mvp.md
  - project/decisions/0016-bybit-spot-supersedes-binance.md
---

# Pre-S15 backlog — v0.2 retry direction

## Context (post-S14 honest close)

S14 shipped (PR #22, tag `v0.1.0-alpha.14`). v0.1 honest close. Strategy validation NEGATIVE. Per S14 ADR 0029: future direction options deferred к operator (revision / multi-symbol / timeframe / pause).

**User initiated S15 brainstorm с 4 specific questions (verbatim):**
1. "Какая стратегия наиболее economical для retry в v0.2?"
2. "Multi-symbol BTC+ETH+SOL viable per ADR 0016 venue policy?"
3. "15M timeframe требует архитектурных изменений?"
4. "ML-driven signal filter (XGBoost) feasible в существующем pipeline?"

**Routing per user direction:**
- trader-expert: ALL 4 questions (product/strategy verdict primary)
- architecture-reviewer: Q2 + Q3 + Q4 (technical feasibility verdict secondary)
- After verdicts: "На основании их ответов начинай кодить" — execute coding в S15

## S14 constraint (T5 unreachability) drives Q1-Q4 design

Per S14 ADR 0029: EMA crossover на 1H BTC fires ~1 trade per 5-10 days. T5 ≥100 trades requires ~1/day = 5x frequency gap. Any v0.2 strategy direction must address this — either through:
- Higher signal-frequency strategy family (Q1)
- Multi-symbol aggregation (Q2: 3x via BTC+ETH+SOL)
- Higher-frequency timeframe (Q3: 15M = 4x)
- ML filter that captures more weak signals (Q4)

## S15 PHASE 2 brainstorming questions (4 questions)

### Q1 — Most economical retry strategy для v0.2

**Question:** Which strategy family most likely к pass T1-T6 acceptance criteria с minimum scope expansion?

**Maintainer recommended option:** (a) Mean-reversion (RSI extreme + Bollinger Bands)

**Alternatives considered:**
- (a) **Mean-reversion (RSI extreme + Bollinger Bands)** — reuses existing RSI indicator + adds Bollinger Bands. Inherently higher frequency (oversold/overbought conditions ~1 trade per 2-5 days vs EMA crossover ~1 per 5-10 days). Same Wilder/classical idiom (per ADR 0011)
- (b) Regime-switch (HMM detection on volatility) — adds context layer + market regime filter. May or may not increase frequency. Higher complexity (HMM training pipeline)
- (c) ML-driven (XGBoost classifier) — addresses signal frequency through filter logic. Major scope (Q4 separate)
- (d) Momentum breakout (Donchian channels) — cleaner trend signals, но BTC trends frequent (similar EMA crossover frequency profile)
- (e) Multi-strategy ensemble (mean-reversion + breakout AND-gated) — highest complexity, lowest frequency

**Reasoning for recommended:**
- Mean-reversion на crypto historically performant (BTC mean-reverts on 1H timeframe per academic literature — Hudson & Urquhart 2021)
- RSI indicator already implemented (S3, ADR 0011 — Wilder)
- Bollinger Bands = trivial addition (mean ± 2σ), no new TA-Lib function needed (use existing ATR adaptation OR pandas rolling.std)
- Higher signal frequency naturally addresses S14 T5 unreachability constraint
- Same FSM + risk + execution pipeline (no architectural change)
- Cost: 1-2 sprints (strategy file + parameter tuning + WFA re-measurement)

**Risk/concern:**
- Mean-reversion fails в strong trending regimes (2021 bull, 2024 bull) — opposite failure mode of trend-following EMA crossover
- HIDDEN ASSUMPTION: BTC 1H mean-reverts (literature suggests yes, но empirical varies by year)
- Same N_trials accumulation problem (each strategy attempt = N_trials++ для DSR penalty)
- T5 ≥100 trades may STILL be hard к hit (RSI extremes 30/70 also rare on 1H BTC — would need RSI 35/65 OR additional triggers)

---

### Q2 — Multi-symbol BTC+ETH+SOL viable per ADR 0016?

**Question:** Add ETHUSDT + SOLUSDT alongside BTCUSDT (3-symbol portfolio) для 3x signal frequency aggregation. Compatible с ADR 0016 (Bybit Spot venue policy) + current Coordinator single-symbol invariant?

**Maintainer recommended option:** (a) Viable — within ADR 0016 (all on Bybit Spot), но requires architecture-reviewer verdict on Coordinator-per-symbol pattern OR multi-coordinator orchestrator.

**Alternatives considered:**
- (a) **Coordinator-per-symbol pattern** — instantiate N independent Coordinator+Reconciler+ExecutionStateRepo+RiskManager per symbol (requires multi-row execution_state schema OR per-symbol DB). Architecture-reviewer assesses.
- (b) Multi-symbol Coordinator (single instance handling N symbols) — major refactor, breaks single-writer-per-symbol invariant per ADR 0022
- (c) Sequential symbol rotation (one symbol active at a time) — simpler, но defeats multi-symbol benefit
- (d) Skip multi-symbol — single symbol still possible с different strategy choice (Q1 + Q3)

**Reasoning for recommended:**
- ADR 0016 = Bybit Spot venue. ETHUSDT + SOLUSDT both on Bybit Spot ⇒ no venue policy violation
- 3x signal frequency aggregate (BTC ~20 trades + ETH ~25 + SOL ~30 = ~75 OOS trades). Still likely < 100 T5 floor, but closer
- Coordinator architecture (S5+S6+S7+S8a) designed для single symbol per instance. Pattern (a) replicates instances, doesn't refactor invariant
- ExecutionStateRepo schema: PRIMARY KEY = symbol → already supports multi-row per-symbol
- BarSource per symbol (S8a) — already designed independent
- Architectural feasibility: HIGH (replication pattern, не refactor)

**Risk/concern:**
- Risk model (Kelly + circuit breakers): currently global. Multi-symbol → per-symbol Kelly OR aggregate Kelly?
- Capital allocation across 3 symbols (e.g. 33% each) — new ADR needed
- Demo trading API rate limits (Bybit V5: 5 req/sec) — 3x WS subscriptions OK, REST polling 3x rate
- HIDDEN: liquidity differences across symbols (BTC > ETH > SOL spread) — slippage model may need per-symbol calibration
- ETH/SOL data availability на Bybit Spot — may differ from BTC's 2021-07-02 start date

---

### Q3 — 15M timeframe требует architectural changes?

**Question:** Switch from 1H к 15M bars (4x signal frequency). Current architecture (BarSource interval="60", WFA params для 1H, ADR 0005 baseline) compatible?

**Maintainer recommended option:** (a) Mostly compatible — param changes + ADR 0005 amendment. Architecture-reviewer assesses.

**Alternatives considered:**
- (a) **15M baseline** — change BarSource interval="15", WFA params (train=2000, test=500 stay но calendar coverage shrinks 4x), strategy indicators warmup ~12.5 hours instead 50 hours. ADR 0005 amendment.
- (b) Multi-timeframe (15M signal + 1H regime context) — adds complexity, requires new WFA framework
- (c) 4H timeframe (lower frequency, cleaner trends) — opposite direction, не addresses T5
- (d) Skip timeframe change — single timeframe 1H stays, address T5 другими means

**Reasoning for recommended:**
- BybitRESTClient.get_klines interval_map: `{"60": "1h"}` — currently single entry. Easy extension к add `{"15": "15m"}` (per Bybit V5 docs).
- BarSource.interval: configurable parameter, accepts string. No architecture refactor needed.
- WFA params (ADR 0014): train=2000 / test=500 / K=5 / embargo=20. На 15M = 2000 × 15min = 500 hours = 21 days train. На 1H = 2000 hours = 83 days. Both adequate calendar coverage.
- Calendar coverage 4.81y × 4 = ~19y-equivalent OOS samples (~80 OOS trades expected с EMA crossover, ~150 с mean-reversion)
- ADR 0005 amendment: minor (timeframe change preserves spirit of "single timeframe baseline")
- Cost: 1-2 sprints (config change + ADR amendment + WFA re-measurement)

**Risk/concern:**
- 15M noisier than 1H — strategy edge may evaporate (Sharpe ratio higher in lower frequencies)
- ADR 0005 amendment needs trader+architecture verdict on academic literature (15M crypto edge studies)
- Backfill 4.81y × 4 = ~169K bars (vs 42K). Bybit pagination 169 calls × ~0.7s = ~2 minutes. Acceptable.
- Indicator warmup faster (12.5h vs 50h) — less data lost к warmup
- HIDDEN: Bybit 15M data availability may start later than 1H (smaller community early)

---

### Q4 — ML-driven (XGBoost) signal filter feasible?

**Question:** Add ML inference layer (XGBoost classifier filter on existing EMA signals) per pre-S1 Mimo bot reference + ADR 0002 v0.2 deferral. Feasible в existing pipeline?

**Maintainer recommended option:** (c) DEFER к v0.3+ — too large scope, requires ML training infrastructure + feature engineering + model registry + rollback strategy. Не lowest-cost retry path.

**Alternatives considered:**
- (a) Full ML pipeline (XGBoost + training + inference + registry) — 5-10 sprints scope. Per ADR 0002: "XGBPredictor / src/ml/ — deferred → v0.2".
- (b) Inference-only (use pre-trained model via ONNX) — avoids training infra, но need pre-trained model source. Pre-S1 Mimo bot had this reference — но code was deleted.
- (c) **DEFER к v0.3+** (recommended) — focus v0.2 retry на simpler strategy family (Q1) OR multi-symbol (Q2) OR timeframe (Q3) first
- (d) Hybrid: rules-based primary (Q1 mean-reversion) + ML filter on top — combines strategy revision + ML, complexity multiplied

**Reasoning for recommended:**
- ADR 0002 explicit: "XGBPredictor / src/ml/ (deferred → v0.2)" — но v0.2 was scope expansion premise, не commitment
- ML pipeline = significant new infra: training data prep + feature engineering + cross-validation + hyperparameter tuning + model serialization (ONNX) + inference layer (Python skl_ensemble OR onnxruntime) + model registry + monitoring + rollback
- Cost vs benefit: 5-10 sprints OR more, edge probability unknown (ML often disappointing на raw price data per López de Prado AFML Ch.7)
- v0.2 retry economical path = simpler strategy first, ML defer pending empirical evidence из simpler attempts
- ML-as-filter (option d) = compounding complexity — better к verify base strategy works first

**Risk/concern:**
- "Best practice" trap: assuming ML adds value because it's modern technique. Often не replicates на crypto raw data.
- Training data look-ahead bias: feature engineering MUST use only-past data per fold (López de Prado AFML purged-CV)
- Model decay: production model needs periodic retraining, deployment infrastructure not built
- HIDDEN: Mimo bot reference suggests ML filter approach existed pre-S1 — but code deleted, may have been just aspirational

---

## ROUND 1 verdicts (TRADER-EXPERT + ARCHITECTURE-REVIEWER, complete)

**Source-claim verification (CC1 lesson) outcomes:**
- ✅ Q1 RSI filter-vs-trigger semantic verified: `src/signalgen/strategy.py:128` — RSI used as filter on EMA crossover. Mean-reversion = RSI as primary trigger → NEW strategy class required (not param change)
- ✅ Q1 DSR cross-trial blocker verified: `src/__main__.py:443` `compute_dsr(trades=all_trades, n_trials=1)` hardcoded → T0 prereq for S15
- ✅ Q2 ExecutionStateRepo PRIMARY KEY=symbol verified: `migrations/0003_execution_state.sql` confirmed multi-row per-symbol support
- ❌ Q2 NEW BLOCKER: `src/risk/trade_history.py:85-93` `load_recent` no symbol filter → Kelly contamination across symbols (HIGH severity)
- ✅ Q3 interval_map KeyError verified: `src/marketdata/bybit/rest.py:66-67` `{"60":"1h"}` only
- ✅ Q3 heal_max_age_seconds 1H coupling verified: `src/platform/config.py:97-102` "1 bar period of v0.1 (1H)" → 15M production safety bug
- ❌ Q3 trader's WS hardcoded claim REFUTED: `src/marketdata/bybit/ws.py:30-33` topic config-driven (not 3rd blocker)
- ✅ Q3 BarSource compatibility: `src/runtime/bar_source.py:23-37` `_INTERVAL_MS` already includes "15"
- ✅ Q3 CLI hardcoded sites: `src/__main__.py:131,191,205,335` — "60" + "_1h.parquet" hardcoded
- ✅ Q4 WFA fold-only verified: `src/backtest/walk_forward.py` no purged-CV → CPCV requires new framework

| # | Question | TRADER verdict | ARCHITECTURE verdict | Final accepted |
|---|----------|----------------|----------------------|----------------|
| Q1 | Most economical retry strategy | **REVISE-ADDITIVE** — mean-reversion correct, NEW strategy class `MeanReversionRsiBBStrategy` required, DSR cross-trial = T0 prereq | n/a (product) | Mean-reversion accepted. NEW strategy class. T0 = DSR cross-trial fix |
| Q2 | Multi-symbol viable per ADR 0016 | **CONFIRM** — Coordinator-per-symbol replication, but не solves T5 alone | **APPROVE_WITH_CONDITIONS** — `load_recent` symbol-filter HIGH BLOCKER, ADR 0022 invariant preserved, rate limits OK | Multi-symbol accepted с `load_recent` fix mandatory. Capital allocation new ADR deferred (Kelly per-symbol natural) |
| Q3 | 15M timeframe architectural | **REVISE-material** — 2 hard blockers (interval_map + heal_max_age) | **APPROVE_WITH_CONDITIONS** — interval_map trivial, heal_max_age semantic refactor (`heal_max_age_bars` instead of seconds) | DEFERRED к S16+ — Option B chosen |
| Q4 | ML XGBoost feasible | **CONFIRM** — defer к v0.3+ (root cause = no edge, не signal noise) | **CONFIRM defer** — purged-CV requires new framework, 5-10 sprint scope | Defer к v0.3+. NOT in S15 |

## Cross-cutting concerns (trader + architecture flagged)

- **CC1 (Trader)**: Q1+Q3 confound — mean-reversion на 15M = high noise, RSI<30 fires on momentum moves not mean-reversion. Validate Q1 на 1H first.
- **CC2 (Trader)**: DSR cross-trial sigma_SR = BLOCKING prereq для any S15 WFA. T0 task.
- **CC3 (Trader)**: Q2 alone не solves T5 (~70-90 trades aggregate vs 100 floor). Needs Q1.
- **CC4 (Trader)**: heal_max_age_seconds 1H coupling — production safety bug at 15M (deferred к S16 since Q3 deferred).
- **CC5 (Trader)**: N_trials grows per measurement → DSR penalty severe с -44.46 anchor. Pre-register RSI thresholds (ESC-2).
- **CC6 (Architecture)**: Multi-symbol + 15M = 12x compute load (deferred since Q3 deferred).
- **CC7 (Architecture)**: ADR 0022 single-writer invariant PRESERVED under Coordinator-per-symbol replication (not violated).
- **CC8 (Architecture)**: Capital allocation cross-symbol exposure caps = new ADR (deferred — natural per-symbol Kelly suffices for v0.2 baseline).

## ESC-1 RESOLUTION (combination choice)

**Trader recommendation: Option B (Q1+Q2)**
**Architecture recommendation: Option B (Q1+Q2)**
**Maintainer accepts: Option B**

S15 = mean-reversion (RSI extreme + Bollinger Bands) на 1H × 3 symbols (BTCUSDT + ETHUSDT + SOLUSDT). Q3 (15M) deferred к S16 if S15 fails T5. Q4 (ML) deferred к v0.3+.

Rationale: lowest architectural risk (replication pattern, не refactor), bounded code changes (`load_recent` fix + DI fan-out + CLI `--symbols`), ~3x signal frequency aggregate, preserves 1H signal quality, sequential strategy validation.

## ESC-2 RESOLUTION (RSI threshold pre-registration)

**Pre-registered binding parameters для S15 (locked BEFORE WFA run, no post-result tuning):**

LONG entry: RSI(14) < 30 AND close < lower_BB(20, 2σ)
EXIT: RSI(14) > 70 OR close > upper_BB(20, 2σ) OR ATR(14) trailing stop hit

Conservative AND-gated trigger. Estimated frequency: ~15-25 trades per symbol × 3 symbols × 4.81y ≈ 75-125 OOS trades aggregate. T5 borderline expected — acceptable per "honest measurement" framework. If T5 fails, S16 will widen к OR-gated OR add 15M (Q3).

N_trials accounting: S15 = trial #2 (S13 trial #1 = -44.46 Sharpe). DSR cross-trial sigma_SR via T0 task.

## Architecture-reviewer dispatch — COMPLETE

Both trader-expert + architecture-reviewer ROUND 1 returned. Both converge on Option B. NO ROUND 2 iterative justify needed (trader REVISE-ADDITIVE accepts maintainer's option (a); architecture APPROVE_WITH_CONDITIONS aligns с trader).

## USER FINAL DECISION (autonomous mode)

Per user direction "На основании их ответов начинай кодить": maintainer applies engineering judgment per agent verdicts.

**S15 scope locked:** Q1 + Q2 (Option B). Pre-registered RSI 30/70 + BB(20, 2σ) AND-gated. T0 = DSR cross-trial sigma_SR fix. Q3+Q4 deferred.

Next: ADR 0030 → Plan → Execute via subagent-driven.

## Related

- [[decisions/0029-sprint-14-honest-close]] — S14 honest close (T5 unreachability constraint)
- [[decisions/0028-sprint-13-strategy-validation]] — S13 measurement results
- [[decisions/0002-python-only-for-mvp]] — Python-only stack (Q4 ML constraint)
- [[decisions/0005-1h-timeframe-mvp]] — 1H baseline (Q3 amendment target)
- [[decisions/0016-bybit-spot-supersedes-binance]] — Bybit Spot venue (Q2 multi-symbol policy)
- [[decisions/0030-sprint-15-mean-reversion-multi-symbol]] — Sprint 15 ADR
- [[sprints/sprint-15-mean-reversion-multi-symbol]] — Sprint 15 page
- [[architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
