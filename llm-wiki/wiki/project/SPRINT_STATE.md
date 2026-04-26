---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 27
phase: between-sprints
branch: feature/sprint-27-formula-bug-fixes
tag: v0.1.0-alpha.27
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**S27 SHIPPED. Formula bug fixes (5 bugs).** 27 спринтов завершено. Audit infrastructure (`scripts/audit_formulas.py` + `data/formulas_audit_v1.json` + dashboard auto-refresh). Trader+logic-reviewer parallel brainstorm verdict: 4 bugs found (1 HIGH, 2 MEDIUM, 1 INFO/CC5, 1 LOW), all fixed TDD (5 commits, 762 passed). Sweep re-run post-fix: verdict count unchanged (0 PASS / 30 FAIL — bugs не fundamentally изменили acceptance gate outcomes), но reason codes diverse (187 SL / 141 TP / 2 TIME_STOP), ema_crossover SOLUSDT 4H pnl +88→+131 (RSI warm-up fix), audit reproducible (MC seed=42 default).

**Status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 30 ADRs + 17 sprint pages)
- Formula correctness: ✅ FIXED (5 bugs eliminated, measurement instrument trustworthy)
- Strategy validation: ❌ NEGATIVE (still 0 PASS / 30 FAIL — structural failures, не formula bugs)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 still unreachable single-symbol 4H)

## Последний спринт (S27 — formula bug fixes)

Operator-driven audit sprint. 5 bugs (T1-T5) fixed TDD, audit re-run. ESC items для S28+ pending operator decision.

- T1 HIGH replay_engine bars_per_year parameterization (annualization)
- T2 MEDIUM Sortino canonical downside_dev (Sortino & Price 1994)
- T3 MEDIUM RSI/ATR warm-up gating (mask first period bars NaN)
- T4 INFO/CC5 trade_extractor preserve actual reason_code (SL/TP/SIGNAL_FLIP/EOD/KILL_SWITCH)
- T5 LOW MC seed=42 default (reproducibility)
- T6 audit re-run + diff snapshot (data/formulas_audit_v1_post_s27.json)
- T7 ADR 0040 + sprint-27 page + wiki sync
- T8 PHASE 8 ship pending

## Следующее действие

```
S27 PHASE 8 ship: gh pr create + squash merge + tag v0.1.0-alpha.27.

Operator decides ESC items для S28+ scope:
- ESC-1 Multi-symbol authorization (S28 expanded scope beyond BTCUSDT MVP)
- ESC-2 "In profit" vs "pass acceptance criteria" — different goals (live pilot ETH 4H pre-S28?)
- ESC-3 Operational implications 4H multi-symbol (3 simultaneous positions, 1-5 day holds)

Trader-expert backlog (S28-S32):
- S28 Multi-symbol 4H mean_reversion (n≈135 → T5 PASS) — depends ESC-1
- S29 Regime filter + SMA50 trend gate (CC2 fold concentration)
- S30 SL calibration {1.0/1.25/1.5}×ATR + t-stat power validation
- S31 Donchian 4H breakout (independent hypothesis)
- S32 DSR cross-trial sigma_SR + MC power audit (closes S14 Q2 carry-over)
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
