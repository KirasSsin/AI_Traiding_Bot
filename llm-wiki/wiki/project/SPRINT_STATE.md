---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 17
phase: 8-ship
branch: feature/sprint-17-btc-mean-reversion-relaxed
tag: v0.1.0-alpha.17
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**S17 ready к ship (tag `v0.1.0-alpha.17`).** 19 спринтов завершено: S1-S7 + S8a + S8b + S8c + S9 + S10 + S11 + S12 + S13 + S14 + S15 + S16 + S17. **MVP retry hypothesis #3 = FAIL T5 count only** (59 trades < 100), **5/6 PASS + DSR=1.0 + MC p=0.01 stat-sig** = first time positive direction по most criteria. Per ADR 0032 amendment 3 BINDING → S18 = honest close v0.1 (3 hypotheses tested = publishable scientific contribution).

**Final v0.1 status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages)
- Strategy validation: ❌ NEGATIVE (EMA crossover на 1H BTC = no edge, verified 2 measurements 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable)
- Tag `v0.1.0-alpha.14` = honest close marker (alpha suffix preserved — NOT MVP final)

## Последний спринт (S17 — BTC-only mean-reversion relaxed, MVP retry hypothesis #3)

Config tuning + measurement. Per S17 PHASE 2 brainstorm trader EXPAND verdict с 3 amendments.
- T1 ADR 0032 accepted (BTC-only, RSI 35/65 + BB 1.5σ, NO variance cap, T5 failthrough)
- T2 indicators.py mean_reversion branch (NO change — config-driven from S15)
- T3 _run_wfa_single_symbol config update (relaxed thresholds) + sprint env var fix
- T4 measurement BTC-only --symbol BTCUSDT 4.81y → **VERDICT FAIL T5 count only** (59 trades < 100)
- T5 sprint-17 page + ADR + wiki sync (this commit)
- T6 PHASE 8 ship — pending

Strategy criteria results: T1=25.99 PASS, T2=4446 PASS, T3=2.8% PASS, T4 win 47.5%/RR 154.5 PASS, **T5 FAIL n=59**, T6=0.712 PASS, **DSR=1.0 PASS**, **MC p=0.01 PASS** stat-sig.

Per ADR 0032 amendment 3 BINDING: T5 count <100 → FAIL → **S18 = honest close v0.1** (3 hypotheses tested).

Critical insight: strategy edge IS real on BTC mean-reversion regime (5/6 + DSR + MC sig — first time observed), но sample insufficient на 1H BTC alone. Future MVP-DONE attempts требуют higher-frequency timeframe / hybrid ML / multi-symbol revival (out of MVP scope).

## Следующее действие

```
S17 PHASE 8 ship: gh pr create + squash merge + tag v0.1.0-alpha.17.

S17 verdict: FAIL T5 count only (59 < 100), но 5/6 + DSR + MC sig = strategy edge real.
Per ADR 0032 amendment 3 BINDING → S18 = honest close v0.1.

Then S18 docs-only sprint:
- ADR 0033 v0.1 honest close (3 hypotheses tested negative across 4.81y BTC)
- sprint-18-honest-close-v01.md
- Document MC p=0.01 statistically significant signal observed (institutional knowledge)
- Archive cross_trial_sharpes.json к _v0.1-final.json
- Tag v0.1.0-alpha.18 = v0.1 final honest close marker

After S18: operator decides v0.4 direction (no commitment):
- Different timeframe (15M/4H — Q3 blockers documented)
- Hybrid ML filter (S17 evidence supports — partial signal exists)
- Multi-symbol revival (out of MVP scope per user 2026-04-26)
- Project pause
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
