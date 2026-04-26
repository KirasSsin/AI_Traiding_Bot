---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 19
phase: between-sprints
branch: main
tag: v0.1.0-alpha.19
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**S19 ready к ship (tag `v0.1.0-alpha.19`) — v0.4-A architectural prep complete.** 21 спринтов завершено: S1-S7 + S8a + S8b + S8c + S9 + S10 + S11 + S12 + S13 + S14 + S15 + S16 + S17 + S18 + S19. **Joint trader+architecture verdict on v0.4 direction:** Option (A) BTC 15M mean-reversion с 7 combined amendments BINDING. **3 architectural Conditions APPLIED**: A1 interval_map fix / A2 heal_max_bars semantic refactor / A3 annualization parameterization (prevents 2× Sharpe understimate at 15M). **15M backfill complete:** 167,383 bars BTCUSDT 15M. S20 = measurement sprint (pre-registered).

**Final v0.1 status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages)
- Strategy validation: ❌ NEGATIVE (EMA crossover на 1H BTC = no edge, verified 2 measurements 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable)
- Tag `v0.1.0-alpha.14` = honest close marker (alpha suffix preserved — NOT MVP final)

## Последний спринт (S19 — v0.4-A architectural sprint, BTC 15M prep)

Joint trader+architecture brainstorm verdict per user directive. 7 combined amendments BINDING. Architectural sprint, NO measurement (S20 = measurement sprint).
- T0 Bybit 15M data verified (BTC ≥ 2021-07-15, 4.78y available)
- T1 ADR 0034 accepted
- T2 rest.py interval_map → single-dict refactor (Condition A1)
- T3 heal_max_bars semantic refactor + bootstrap wiring (Condition A2)
- T4 annualization parameterization 3 files + CLI --interval (Condition A3 — HIGH, prevents 2× Sharpe understimate)
- T5 WFA params kept ADR 0014 defaults (test=500 bars at 15M = ~5.2 days adequate)
- T6 15M backfill BTCUSDT — 167,383 bars
- T7 sprint-19 page + wiki sync
- T8 PHASE 8 ship — pending

S20 pre-registered (BINDING):
```bash
SPRINT_N=20 .venv/bin/python -m src wfa --symbol BTCUSDT --interval 15 \
  --start 2021-07-15 --end 2026-04-26
```
T5 floor 150 trades (T-Amendment 1). Fold concentration check (T-Amendment 2). N_trials=1 fresh.

## Следующее действие

```
S19 PHASE 8 ship: gh pr create + squash merge + tag v0.1.0-alpha.19.

v0.4-A architectural prep complete. 7 amendments applied. 167K bars BTCUSDT 15M ready.

S20 = WFA 15M measurement (BINDING per ADR 0034):
SPRINT_N=20 .venv/bin/python -m src wfa --symbol BTCUSDT --interval 15 \
  --start 2021-07-15 --end 2026-04-26

Verdict criteria (BINDING):
- T5 < 150 → FAIL count alone, t_stat skipped
- T5 ≥ 150 + fold concentration check
- All T1-T6 + DSR + MC PASS conjoint → MVP DONE strategy criteria → S21+ S1-S6 system + Mainnet
- FAIL → S21 honest close v0.4 (4 hypotheses tested = scientific contribution)
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
