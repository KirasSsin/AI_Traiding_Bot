---
title: Pre-S35 Backlog — v0.7+ Direction Consilium ROUND 3 BINDING
type: backlog
tags: [pre-sprint, sprint-35, v07-direction, consilium-round-3, binding, testnet-demo, donchian, risk-mgmt, ru]
created: 2026-04-27
updated: 2026-04-27
status: active
sources:
  - project/decisions/0051-sprint-34-honest-close-v06.md
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - .claude/agent-memory/trader-expert/v07_direction_consilium.md
---

# Pre-S35 Backlog — v0.7+ Direction Consilium ROUND 3

## Контекст

Post-S34 ship (v0.6 chapter end). Operator directive: "Зайди в агентов трейдеров и задай им эти вопросы с твоей рекомендацией. Пусть они проведут консилиум с brainstorming по дальнейшему пути и решат. Их решение и начнём реализовывать."

3-agent ROUND 3 консилиум на расширенный set v0.7+ опций (включая δ TESTNET live demo) после data audit, который математически закрыл (b) (n_eff проекция 37-41 < 50 amended threshold).

## Data audit outcome (ROUND 3 trigger)

| Параметр | Значение |
|----------|----------|
| BTC/ETH/SOL 4H bars | 7273 (3.31y actual: 2023-01-01 → 2026-04-26) |
| Bybit max history available | 2021-07-02 (additional 1.5y dormant) |
| Full extension period | 4.81y |
| Projected n_raw (full extension multi-symbol) | ~95 |
| Kish factor (rho=0.75 BTC-ETH-SOL) | 2.5 |
| **Projected n_eff** | **37-41** |
| Amended threshold (ADR 0052) | ≥ 50 |
| **Verdict** | **(b) STRUCTURALLY IMPOSSIBLE** |

Trader-expert ROUND 2 pre-condition triggered: "If n_eff < 50 even with full extension → immediately pivot к (c) as primary". (b) eliminated mathematically. γ (extend data) PERMANENTLY CLOSED per Bailey 2014 discipline.

## Expanded options ROUND 3

| Option | Description | Vote | Reason |
|--------|-------------|------|--------|
| α | Donchian breakout 4H long-only | WEAK YES — parallel synthetic | 7th hypothesis, N_trials=5 DSR penalty, ~280 LoC, orthogonal paradigm, long-only FSM compatible |
| β | Pause v0.7+ indefinitely | CONDITIONAL YES — fallback | 33 sprints invested, infrastructure mature, valid if investment exhausted |
| γ | Extend data + retry (b) | NO — PERMANENTLY CLOSED | n_eff 37-41 < 50 structural impossibility |
| **δ** | **TESTNET live demo** | **YES — PRIMARY** | S12 infrastructure exists, S17+S22 MC p≤0.02 best evidence, real-time accumulation bypasses T5 structural problem |
| ε | Pairs/stat arb | NO — DEFER к v0.8+ | rho=0.75 NEGATIVE для pairs (low spread variance), wrong sequencing |
| ζ | Risk management refactor (Kelly 0.25× cap, ATR SL) | YES — complement bundled S35 | ~200 LoC, applies regardless primary direction |

## CONSENSUS BINDING decision

**δ (LIVE DEMO TESTNET) primary + α (Donchian 4H long-only) parallel synthetic + ζ (risk management) complement → S35 bundle.**

3 agents CONFIRM:
- **trader-expert:** "BINDING DECISION: δ primary + α parallel + ζ complement bundled into S35"
- **trading-logic-reviewer:** "CONFIRM δ as primary with conditions stated. CONFIRM α as secondary path if operator declines live demo. CONFIRM β as clean fallback"
- **quant-stats-reviewer:** "CONFIRM. The statistical case for δ is compelling and scientifically sound. S22 evidence is real (DSR=0.996, MC p=0.018 post-fix, joint p ≈ 0.0007 under null)"

## 8 pre-commitments (ROUND 3 BINDING)

1. δ is **TESTNET ONLY**. No MAINNET until 12-month TESTNET evidence reviewed by operator
2. Position sizing: Kelly 0.25× cap + ζ refactor applied **BEFORE** any live run
3. α Donchian N_trials=5 declared in ADR before any code
4. α Donchian parameters pre-registered before data inspection. No post-hoc tuning.
5. Halt criteria for δ: ≥5 consecutive losing trades OR ≥15% equity drawdown → TESTNET halt, operator review
6. γ (extend data try b) is PERMANENTLY CLOSED
7. ε (pairs/stat arb) deferred к v0.8+. Not in S35-S37 scope.
8. β (pause) remains valid operator option at any point — no coercion to continue

## Pre-committed PASS gates δ (LOCKED)

| Gate | Threshold | Source |
|------|-----------|--------|
| n trades | ≥ 50 | ADR 0052 amended T5 floor |
| Sharpe | ≥ 0.7 | T6 unchanged |
| Win rate | ≥ 40% | mean-reversion baseline |
| Max DD | ≤ 30% | risk management |
| MC p-value | ≤ 0.05 | ADR 0052 tightened |
| DSR | ≥ 0.95 | T2 unchanged |

## Pre-committed HALT criteria δ

- DD ≥ -20% intraday OR -15% multi-day → halt + S36 honest close
- 5 consecutive losing trades → operator review
- 6 месяцев без n ≥ 30 → halt + S36 honest close

## LOCKED parameters δ (Item #5+#7 ADR 0052)

- Strategy: `MeanReversionRsiBBStrategy` + `MEAN_REVERSION_S17_RELAXED_PARAMS`
- Symbol: BTCUSDT only (single-symbol bypasses correlation deflation)
- Timeframe: 4H (S22 validated)
- Capital: TESTNET only (zero MAINNET)
- N_trials: frozen (δ uses S22-validated, no new hypothesis)

## Operator acknowledgment template (verbatim per ADR 0052 — мандатори в S35 ADR)

> "Statistical evidence as of v0.6 DOES NOT support live deployment; this amendment reflects crypto-specific sample-size reality (Hudson & Urquhart 2021), not evidence of positive edge. I authorize TESTNET-only live demo using S22-validated mean-reversion strategy with halt criteria pre-committed. No real capital. n_trials counter remains frozen per Item #10."

## S35 task structure

| T | Task | Track | Note |
|---|------|-------|------|
| T1 | ζ Risk management refactor (Kelly 0.25× cap audit + ATR SL calibration) | δ-prep | bedrock first per pre-commitment #2 |
| T2 | δ TESTNET activation (halt criteria ADR + real-trade log protocol + FillRecorder validation) | δ | live activation |
| T3 | α Donchian ADR pre-registration (N_trials=5 LOCKED, params LOCKED, long-only FSM-compatible) | α | parallel synthetic |
| T4 | α Donchian implementation + backtest run + tests | α | parallel synthetic |
| T5 | Reconcile + sprint-35 page + index/counts sync | both | ship |

## Engineering blockers (Donchian)

- Donchian SHORT signals conflict с `long_only=True` FSM invariant (per ADR 0009)
- α implementation **long-only only** (FSM SignalSide=LONG/FLAT)
- Подтверждено trading-logic-reviewer

## Failure branch

If both:
- δ drawdown ≥ 15% within S35-S36 window
- AND α FAIL conjoint backtest

→ β (pause) per pre-commitment #8.

## Carry-overs preserved (S35 NOT addressing)

- bybit-api-reviewer first real-world validation (если live deployment ever)
- Bridge 4 corpus partition implementation (S40+ when corpus > 100 obs)
- t-stat heavy-tail correction (Hudson & Urquhart 2021 — CC-E)
- ESC-3 4 binding conditions (для multi-symbol если ever triggered)
- 3-way endpoint enum (DEMO/TESTNET/MAINNET) — Q6 future fix

## Related

- ADR 0050 (S33 Trading Restart — pre-committed failure branch trigger)
- ADR 0051 (S34 6-th honest close v0.6)
- ADR 0052 (S34 acceptance-criteria amendment LOCKED)
- pre-s33-backlog.md S34 Direction Consilium section
- `.claude/agent-memory/trader-expert/v07_direction_consilium.md` (trader binding ROUND 3 trail)
- [[decisions/0053-sprint-35-testnet-live-demo]] — Sprint 35 ADR (TESTNET live demo)
- [[decisions/0054-sprint-35-donchian-pre-registration]] — Sprint 35 ADR (Donchian pre-registration)
- [[sprints/sprint-35-testnet-donchian-risk]] — Sprint 35 page
