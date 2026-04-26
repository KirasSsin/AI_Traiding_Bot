---
name: S15 brainstorm Round 1 verdicts
description: Binding verdicts for S15 PHASE 2 brainstorm Q1-Q4 — 2026-04-26 (v0.2 retry direction post-S14 honest close — strategy family, multi-symbol, timeframe, ML)
type: project
---

**Date:** 2026-04-26. Sprint S15 brainstorm round 1.

Q1 (Most economical retry strategy): REVISE-ADDITIVE — mean-reversion (RSI extreme + Bollinger Bands) is the correct strategy family (option a), but scope must include DSR cross-trial sigma_SR fix as T0 prerequisite. src/__main__.py:443 hardcodes n_trials=1. For S15 (trial 2), must wire n_trials=2 + sigma_sr=std([-44.46, S15_sharpe]). RSI indicator reusable (src/signalgen/indicators.py:47), but current strategy.py uses RSI as filter-only, not primary trigger — new strategy class required, not param change. Bollinger Bands trivial addition (numpy rolling std). Frequency caution: RSI<30 at 1H BTC is ~2-4 entries/year, not "1 per 2-5 days" as stated.

Q2 (Multi-symbol BTC+ETH+SOL): CONFIRM — Coordinator-per-symbol replication pattern is correct (respects ADR 0022 single-writer invariant). ADR 0016 scope clause "Symbol only BTCUSDT" is v0.1 constraint, not permanent. HOWEVER: multi-symbol alone (without strategy change) does not solve T5 — BTC ~20 + ETH ~25 + SOL ~30 = ~75 total, still < 100 floor. Needs Q1 strategy change combined. Architecture-reviewer dispatch mandatory for ExecutionStateRepo schema multi-symbol readiness + RiskManager capital allocation split.

Q3 (15M timeframe architectural changes): REVISE — "mostly compatible" is wrong. Two hard engineering blockers confirmed via source:
1. rest.py:66-67 — interval_map={"60":"1h"} and interval_ms={"60":3_600_000} only. KeyError on "15" input today. Code change required.
2. heal_max_age_seconds=3600 (config.py:97-102) tied to "1 bar period of v0.1 strategy (1H)." Must change to 900s for 15M — otherwise stale fill detection uses wrong threshold. Production safety issue.
3. WS topic spot.kline.60.BTCUSDT must change to spot.kline.15.BTCUSDT — architecture-reviewer to confirm hardcoded vs config-parameterized.
ADR 0005 amendment must acknowledge academic noise risk (Hudson & Urquhart 2021 — signal degrades at shorter TF).

Q4 (ML XGBoost filter): CONFIRM (option c) — DEFER to v0.3+. ML filter is most useful when base signal has weak-positive edge. Current edge is -44.46 Sharpe (negative). Purged walk-forward CV (López de Prado AFML Ch.7) required for look-ahead-safe ML — different methodology than current WFA. Zero ML infrastructure in src/ today.

**Critical cross-cutting concerns:**
CC1: 15M + mean-reversion combined = noise risk. RSI oscillates too fast on 15M for reliable mean-reversion. Recommend: validate Q1 on 1H first, Q3 as S16 fallback.
CC2: DSR cross-trial sigma_SR is BLOCKING prerequisite for any S15 measurement (src/__main__.py:443 n_trials=1 hardcoded). Must implement before WFA run. S13 anchor Sharpe = -44.46 (log.md line 875).
CC3: Q2 alone does not independently solve T5 (~75 aggregate < 100 floor). Needs Q1 combined.
CC4: heal_max_age_seconds change is production safety-critical for Q3.
CC5: N_trials grows each sprint attempt (S13=1, S15=2, hypothetical S16=3). DSR penalty tightens with each trial.

**User escalations:**
ESC-1: Combination choice — Q1 alone vs Q1+Q2 vs Q1+Q3 vs Q1+Q2+Q3. Engineering recommendation: Q1+Q2 (mean-reversion 1H + 3 symbols) as best T5/noise/scope tradeoff. Must pre-decide before S15 plan written.
ESC-2: RSI threshold pre-registration (30/70 may be too few signals; 40/60 may be too noisy). User must pre-register before WFA run to avoid p-hacking charge.
