---
title: Pre-S39 Backlog — volume_breakout production + tech debt + augmentation investigation
type: backlog
tags: [pre-sprint, sprint-39, volume-breakout, autoresearch-integration, tech-debt, augmentation, ru]
created: 2026-05-09
updated: 2026-05-09
status: active
sources:
  - BACKLOG.md
  - autoresearch/donchian-may8:research/FINAL_STRATEGY.md
  - autoresearch/donchian-may8:research/CLOSE.md
  - llm-wiki/wiki/project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - llm-wiki/wiki/project/decisions/0054-sprint-35-donchian-pre-registration.md
  - llm-wiki/wiki/project/decisions/0058-sprint-38-delta-parallel-hardening.md
---

# Pre-S39 Backlog

## Контекст

Autoresearch iter 8-10 на 4H BTCUSDT нашёл `volume_breakout` (Donchian channel + volume confirmation + ATR stop):

| Метрика | Значение |
|---------|----------|
| Held-out (8mo BEAR 2025-08-26 → 2026-04-26) | Sharpe **+9.96** / PnL **+20.42%** / n=17 |
| Full backtest (3.3y 2023-01-01 → 2026-04-26) | PnL **+122.66%** / annualized **+36.96%/y** |
| Total trials | 4.51M (4510 sweeps × 10 strategies) |
| PASS rate | 4.72% (213/4510) |
| PASS sweeps Sharpe > 5 | 127 (robustness signal) |
| Selected sweep | #1644 — в centroid cluster 213 PASS |
| Other 9 strategies на same sweep | ВСЕ negative held-out (differential edge) |

**Selected params (sweep#1644 LOCKED):**
```
lookback_n=9, exit_lookback_n=8
vol_window=10, vol_mult=1.4563
atr_period=9, atr_stop_mult=2.9663
Timeframe=4H, Symbol=BTCUSDT, Side=LONG_ONLY
```

**Status:** strategy не интегрирована в main. Живёт в branch `autoresearch/donchian-may8`. Reference implementation: `research/strategies.py:355 strat_volume_breakout`.

**Carry-overs из S38 (BLOCKERS для δ TESTNET production):**
- H1 rate-limit backoff отсутствует (REST adapter)
- H2 WS reconnect verification (нет тестов)
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT property tests boundary

**Carry-overs cleanup (after S38):**
- Item #7 RiskSharedDeps backward-compat shim removal
- F8 `_MC_BLOCK_SIZE` unification (20 vs 30)

**Wiki gap:**
- `reason-codes.md` body 42 codes → должно быть 50 (S36+S37 не synced); в S39 будет +3 (volume_breakout) → итог 53

---

## S39 PHASE 2 brainstorming — 9 questions для trader-expert ROUND 1

### Q1 — Params LOCKED verbatim

**Question:** Зафиксировать sweep#1644 params verbatim (без post-observation tuning) per Bailey 2014 anti-snooping discipline?

**Maintainer recommended option:** (a) LOCK verbatim в ADR-0059. Никаких corrections к 4 знаков после запятой `vol_mult=1.4563` / `atr_stop_mult=2.9663`.

**Alternatives considered:**
- (b) Round к 2 sigfigs (vol_mult=1.46, atr_stop_mult=2.97) — clean params; но эмпирическое свидетельство = exact 4-digit sweep#1644
- (c) Re-search в narrow neighborhood — превращает в new search loop, Bailey blowup

**Reasoning for (a):**
- ADR 0054 pre-commit #8 protocol BINDING для autoresearch results
- 213 PASS centroid cluster includes exact sweep#1644 — robustness signal
- Anti-snooping: ANY tuning post-observation = data snooping

**Risk/concern:**
- 4-digit precision feels overspecified — но это empirical artifact, не theoretical
- Forward live data может show degradation (small-sample bias) — это управляется Gate 2 paper-trade

---

### Q2 — Gate 2 forward paper-trade timing

**Question:** Forward paper-trade 30 days N≥10 signals — BEFORE merge tag alpha.39 OR после?

**Maintainer recommended option:** (b) После tag (как S35 Donchian pre-registration model — strategy LOCKED+shipped, gate validation на runtime δ TESTNET).

**Alternatives considered:**
- (a) BEFORE merge — задерживает sprint на 30+ дней, нарушает sprint cadence
- (c) Skip Gate 2 entirely — нарушает delta-activation-playbook protocol
- (d) Reduce к N≥5 — недостаточно power для verdict

**Reasoning for (b):**
- ADR 0053+0055 pattern: pre-registration ships → Gate 2 validates on runtime
- Sprint cadence preservation: ship → measure → next sprint reacts к verdict
- Operator runs δ TESTNET parallel to S40 work

**Risk/concern:**
- Если Gate 2 FAIL → strategy в production, требует subsequent honest close sprint (10-th)
- δ TESTNET infrastructure stable post-S38 — readiness verified

---

### Q3 — Track E scope (M1-M4 + 12mo MAINNET ADR)

**Question:** Включаем bybit-api M1-M4 + 12mo MAINNET ADR draft в S39 OR defer?

**Maintainer recommended option:** Partial — **M3+M4 IN** (T7 Priority 3+4 tests, безопасно), **M1+M2 + MAINNET ADR DEFER к S40+**.

**Alternatives considered:**
- (a) ALL IN — spreads sprint scope thin, increases blocker risk
- (c) ALL DEFER — leaves cosmetic security gaps (M4 secret redaction = LOW HIGH)
- (d) Only M4 (security) — minimal cleanup

**Reasoning:**
- M3 (WS shape guard) + M4 (repr secret redaction) = small, security-relevant, T7 already provided test code
- M1 (retCode taxonomy) + M2 (response shape assertion) = cosmetic, не blocker
- 12mo MAINNET ADR draft = trigger n=10 DSR first; премature без δ data

**Risk/concern:**
- M4 secret redaction LOW в severity but security-auditor invocation если sprint touches money paths
- DEFER M1+M2 → сохраняем в BACKLOG.md под `Найдено при ревью`

---

### Q4 — llm-wiki/CLAUDE.md 316 lines

**Question:** Прунить llm-wiki/CLAUDE.md (316 lines, превышает 250-line best-practice threshold) в S39 OR оставить?

**Maintainer recommended option:** (b) DEFER (не блокер). Нет signs that file is ignored.

**Alternatives considered:**
- (a) Прунить в S39 — anti-bloat, но нет immediate evidence что file too long causes problems
- (c) Split в meta-rules + reference — adds complexity

**Reasoning:**
- repo CLAUDE.md threshold для bootstrap anchor (loaded every session)
- llm-wiki/CLAUDE.md = reference document, читается опционально
- Pruning без specific issue = optimization без measurement

**Risk/concern:** none

---

### Q5 — Sizing policy для volume_breakout

**Question:** Какая sizing policy для нового volume_breakout: текущая Kelly 0.25× (per ADR 0012) OR change?

**Maintainer recommended option:** (a) **KEEP Kelly 0.25× per ADR 0012** (no policy change в S39).

**Alternatives considered:**
- (b) Full Kelly (no cap) — projected $10k → $12k/3.3y но big drawdowns
- (c) Half Kelly (0.5×) — middle ground ~$6k/3.3y
- (d) Fixed fractional 1-2% per trade — $2-3k/3.3y

**Reasoning:**
- ADR 0012 4-phase Kelly = product policy, sprint scope не меняет
- Kelly amendment = separate ADR + brainstorm (не в S39 scope)
- Conservative sizing protects δ TESTNET evidence accumulation phase

**Risk/concern:**
- "+4-5% projected" в FINAL_STRATEGY.md = Kelly 0.25× artifact, не strategy weakness
- Operator must understand: backtest +20.42% != live +20.42% при 0.25× cap

---

### Q6 — Stat case в ADR-0059

**Question:** Какое evidence primary в ADR-0059: 3.3y full backtest OR 8mo held-out?

**Maintainer recommended option:** (c) **3.3y full primary, 8mo held-out secondary**.

**Alternatives considered:**
- (a) 8mo held-out primary (anti-snooping pure form) — but n=17 narrow CI
- (b) Both equally weighted — confusing для reader

**Reasoning:**
- 3.3y: PnL +122.66%, ~150 trades, multiple regimes (bull+bear+range)
- 8mo: PnL +20.42%, n=17, single bear regime
- 3.3y full period was NOT reused 4510x (only held-out 8mo was)
- 3.3y stat power >> 8mo

**Risk/concern:**
- 3.3y train-test entire period overlap с search → some leakage
- Mitigation: present BOTH в ADR с explicit caveats per Bailey 2014

---

### Q7 — UI dashboard ENFORCE 4H+BTCUSDT для volume_breakout

**Question:** Dashboard preset должен ENFORCE timeframe=4H + symbol=BTCUSDT (lock dropdowns) OR allow user override?

**Maintainer recommended option:** (a) **ENFORCE** — params LOCKED только на 4H BTCUSDT validated; другие комбинации = unvalidated.

**Alternatives considered:**
- (b) Allow override с warning banner — risk user runs unvalidated combo, sees random PnL, makes wrong inferences
- (c) Allow override but not display PnL для unvalidated — confusing UX

**Reasoning:**
- ADR 0054 pre-registration pattern: locked strategy = locked configuration
- Iter 1-7 empirical evidence: 1H/15M/5M = 0 PASS для volume_breakout
- ENFORCE prevents misleading "what if" exploration

**Risk/concern:**
- Operator может захотеть test ETH/SOL — но это новый strategy validation cycle, separate sprint

---

### Q8 — Cherry-pick research/ artifacts в main

**Question:** Cherry-pick `research/FINAL_STRATEGY.md` + `CLOSE.md` + `results.tsv` в main (audit trail для ADR-0059) OR оставить только в branch?

**Maintainer recommended option:** (a) Cherry-pick три файла в `wiki/research-evidence/` (новый раздел) — audit trail доступен из main, не требует переключение веток.

**Alternatives considered:**
- (b) Только link на ветку в ADR — fragile (ветка может быть rebased/deleted)
- (c) Полный merge ветки в main — overkill, тянет search infrastructure

**Reasoning:**
- ADR-0059 evidence section ссылается на 213 PASS distribution — нужен access в main
- `research/FINAL_STRATEGY.md` = canonical strategy spec
- `research/CLOSE.md` = iter 1-7 falsification record (важный context)
- `research/results.tsv` = full audit trail (4510 rows; ~15-20 KB)

**Risk/concern:**
- New wiki section `research-evidence/` — нужен entry в index.md
- Files уже в branch — не lost; но cherry-pick = better discoverability

---

### Q9 — Profit augmentation investigation (HARD constraint)

**Question:** Может ли augmentation существующими проектными индикаторами (EMA classical / ADX Wilder / RSI Wilder / ATR Wilder) увеличить baseline profit (held-out S=9.96 PnL+20.42% / 3.3y +122.66%) для volume_breakout 4H BTCUSDT?

**HARD constraint:** profit после S39 MUST NOT уменьшиться. Любое изменение требует backtest replication ≥ baseline на BOTH 3.3y full AND 8mo held-out.

**Maintainer recommended option:** (a) trader-expert ROUND 1 investigates 4 candidates:
- **EMA200 trend filter** — entry only когда close > EMA200 (фильтр против тренда)
- **ADX(14) gate** — entry only когда ADX > 25 (тренд сильный)
- **RSI(14) cap** — block entry если RSI > 70 (overbought guard)
- **ATR regime filter** — entry only когда ATR > rolling_mean(20) (volatility expansion)

If any candidate имеет theoretical evidence для improvement → pre-register hypothesis в ADR 0059, run autoresearch R-mode на augmented version (~2-4h), decide via backtest comparison. If no candidate worth testing → CONFIRM baseline LOCK, S39 ships sweep#1644 verbatim.

**Alternatives considered:**
- (b) Skip augmentation entirely, baseline LOCKED — fastest, но возможный leave money on table
- (c) Test all 4 candidates exhaustively — Bailey multi-comparison penalty
- (d) Defer augmentation к S40 — clean separation но S39 не reaches potential

**Reasoning for (a):**
- Iter 1-2 на Donchian с EMA filter = empirically falsified (CLOSE.md train +2.50 → held-out -2.05 PnL -16%)
- НО volume_breakout уже имеет volume gate (filters noise) → trend filter может быть additional signal independent of volume
- ADX/RSI gates новые для этой стратегии — не tested
- 4 candidates limited scope — prevents Bailey blowup

**Risk/concern:**
- **Bailey 2014:** post-hoc indicator addition = data snooping unless pre-registered
- **n_trades reduction:** filters снижают n=17 дальше — wider CI
- **centroid escape:** augmented params могут вытолкнуть из stable 213-PASS cluster
- **iter 1-2 evidence:** trend filter falsified для Donchian-class на 4H BTC — но volume_breakout differs structurally

**Decision tree:**
```
trader-expert ROUND 1:
   ├── CONFIRM baseline LOCK (no augmentation worth)
   │      → S39 ships sweep#1644 verbatim
   │
   ├── REVISE → proposes augmentation X
   │      → ADR pre-registration of augmentation hypothesis
   │      → autoresearch R-mode на augmented (2-4h)
   │      → GATE: augmented ≥ baseline на 3.3y AND 8mo
   │           - PASS → adopt augmented, S39 ships
   │           - FAIL → fallback к baseline sweep#1644
   │
   └── DEFER (insufficient time)
          → baseline в S39, augmentation = S40+ scope
```

---

## Phase 5 verify HARD-GATE (NEW for S39)

`tests/integration/test_volume_breakout_baseline_floor.py`:
- 3.3y replication PnL ≥ +122.66% (±0.5% replication tolerance)
- 8mo held-out replication PnL ≥ +20.42%
- FAIL → blocks merge

---

## ROUND 1 verdicts (trader-expert, 2026-05-09)

| Q | Verdict | Final decision |
|---|---------|----------------|
| Q1 | CONFIRM | LOCK sweep#1644 verbatim в `VOLUME_BREAKOUT_LOCKED_PARAMS` |
| Q2 | CONFIRM | Gate 2 после tag alpha.39; ADR-0059 fallback clause "FAIL → S40 honest close" |
| Q3 | CONFIRM | M3+M4 IN; M1+M2 + 12mo MAINNET ADR DEFER → pre-s40 |
| Q4 | CONFIRM | Defer llm-wiki/CLAUDE.md prune |
| Q5 | CONFIRM + amendment | Kelly 0.25× + mandatory disclosure (4 пункта) в ADR-0059 |
| Q6 | **REVISE → (a)** | **8mo held-out PRIMARY, 3.3y SECONDARY с contamination label** (Bailey champion-bias) |
| Q7 | CONFIRM | UI ENFORCE locked_symbol+locked_interval; backend 422 |
| Q8 | CONFIRM | Cherry-pick → `wiki/research-evidence/` + index.md NEW section |
| **Q9** | **EXPAND** | **3 options требуют ESC-1 operator decision:**<br>- **A (recommended)** baseline LOCK now, ATR filter → S40+<br>- **B (допустимо)** single ATR filter pre-registered binary test (PASS = ≥1% PnL improvement on BOTH 3.3y+8mo AND n_trades ≥ 12)<br>- C (REJECTED) 4-candidate model — multi-comparison penalty<br>EMA200/RSI/ADX rejected: EMA200 falsified iter 1-2, RSI inverted economics для breakout, ADX borderline |

### Maintainer response к Q6 REVISE

**ACCEPT** trader REVISE → option (a). Argument о champion-bias методологически корректен:
- 3.3y period покрыт WFA folds × 4510 sweeps = implicitly compared
- 8mo held-out был отделён до search loop — единственная чистая OOS evidence
- ROUND 2 NOT triggered (no maintainer disagreement)

### Cross-cutting concerns (accepted)

- **CC1** Phase 5 test через production pipeline (`indicators.py` → `replay_engine.py` → `backtest_runner.py`), не simplified
- **CC2** reason-codes wiki sync 42→53 (S36+S37 backlog + S39 +3)
- **CC3** N_trials counter в ADR-0059 (volume_breakout = hypothesis #8+)
- **CC4** Track B (H1+H2+Item#10) MUST complete BEFORE volume_breakout TESTNET activation
- **CC5** n=17 95% CI calculation в ADR-0059 (Sharpe ±1.5-2.0)
- **CC6** Profit invariant = BOTH gates (3.3y ≥ +122.66% AND 8mo ≥ +20.42%), не averaged

### Escalation BLOCKING (ESC-1) — RESOLVED 2026-05-09

**Operator decision: Option A — Baseline LOCK now.**

- ATR filter (и любые augmentation candidates) → S40+ как отдельная pre-registered hypothesis
- Clean anti-snooping discipline
- S39 ships volume_breakout sweep#1644 verbatim
- ~14 tasks scope (без A-aug track)

---

## После brainstorm verdicts → PHASE 3 plan

Tracks (зависят от verdicts):
- **Track A** — volume_breakout production integration (A0-A7, ~7-9 tasks)
- **Track A-aug** — conditional augmentation testing (only if Q9 verdict = REVISE w/ candidate)
- **Track B** — H1, H2, Item #10 critical (3 tasks)
- **Track C** — Item #7 shim, F8 cleanup (2 tasks)
- **Track D** — reason-codes wiki sync (1 task)
- **Track E** — M3+M4 tests (conditional на Q3 verdict, ~2 tasks)

**Estimated:** 14-18 tasks. Tag `v0.1.0-alpha.39`.
