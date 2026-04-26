---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 21
phase: 8-ship
branch: feature/sprint-21-honest-close-v04
tag: v0.1.0-alpha.21
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**v0.4 honest close. S21 ready к ship (tag `v0.1.0-alpha.21`).** 23 спринтов завершено. **4 strategy hypotheses tested across 4.81y BTC — all FAIL conjoint per acceptance-criteria.md**. S17 partial signal preserved (1H regime-specific institutional knowledge). Hudson & Urquhart 2021 empirically validated. cross_trial_sharpes archived к v0.4-final.json + reset для v0.5 readiness (3rd archival, mirrors S16/S18). 4-th honest close в проекте (S14+S16+S18+S21).

**Final v0.1 status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages)
- Strategy validation: ❌ NEGATIVE (EMA crossover на 1H BTC = no edge, verified 2 measurements 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable)
- Tag `v0.1.0-alpha.14` = honest close marker (alpha suffix preserved — NOT MVP final)

## Последний спринт (S21 — v0.4 honest close)

Documentation only + cross_trial_sharpes archival. NO code changes. Pre-committed per ADR 0034 amendment 3 BINDING (S20 T5 failthrough triggered).
- T1 ADR 0036 accepted
- T2 sprint-21-honest-close-v04.md
- T3 cross_trial_sharpes.json → _v0.4-final.json archival + reset к [] для v0.5 fresh-start
- T4 wiki sync (current-state TL;DR + ADR 35→36, sprint pages 22→23, +S21 row)
- T5 log.md sprint-end
- T6 SPRINT_STATE → between-sprints, tag alpha.21
- T7 PHASE 8 ship — pending

4 strategy hypotheses tested (S13+S15+S17+S20) all FAIL conjoint. S17 partial signal preserved (MC p=0.01 stat-sig + DSR=1.0 + T1=25.99 на 1H BTC — regime-specific institutional knowledge для v0.5-A hybrid ML). Hudson & Urquhart 2021 empirically validated (15M mean-reversion degrades for BTC). Frequency-dimension hypothesis FALSIFIED.

4-th honest close в проекте (S14+S16+S18+S21). Pattern: documentation + archival, no measurement re-run.

## Следующее действие

```
S21 PHASE 8 ship: gh pr create + squash merge + tag v0.1.0-alpha.21.

v0.4 closed honest. 4 strategy hypotheses tested. S17 partial signal preserved.
data/cross_trial_sharpes_v0.4-final.json archived, fresh [] для v0.5.

Operator decides v0.5 direction (no commitment):
(v0.5-A) Hybrid 1H mean-reversion + ML XGBoost — STRONGEST evidence-supported per S17
(v0.5-B) HMM regime-switch + mean-reversion — addresses fold concentration
(v0.5-C) 4H mean-reversion test — cheap (1-2 sprints), counter-evidence
(v0.5-D) Project pause — 4 hypotheses tested, freeze

4-th honest close в проекте. Per Bailey 2014: v0.5 fresh hypothesis resets DSR baseline cleanly.
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
