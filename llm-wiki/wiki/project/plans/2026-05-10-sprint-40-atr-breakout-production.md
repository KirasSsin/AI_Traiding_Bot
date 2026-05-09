---
title: Sprint 40 Plan — ATR breakout production integration
type: plan
tags: [sprint-40, atr-breakout, autoresearch-integration, locked, ru]
created: 2026-05-10
updated: 2026-05-10
status: done
---

# Sprint 40 Plan — ATR breakout production integration

**Дата:** 2026-05-10
**Ветка:** `feature/sprint-40-atr-breakout-production`
**ADR:** 0060

## Цель

Production integration autoresearch iter1 победителя `atr_breakout` (BTCUSDT 4H).
Результат autoresearch: +819.81% (8.7y additive) / Sharpe 1.11 / 69 trades / 5/5 sub-periods positive.

## Acceptance Criteria

- [ ] T1: +3 ReasonCode (53→56) — PASS
- [ ] T2: ATRBreakoutStrategy class с LOCKED params — PASS
- [ ] T3: Production runner + 8 integration baseline floor tests — PASS
- [ ] T4: Dashboard preset `atr_breakout_iter_endless` — PASS
- [ ] T5: Wiki docs (ADR 0060 + sprint page + component page + sync) — PASS
- [ ] T6: SPRINT_STATE update — PASS
- [ ] T7: git push + PR + merge + tag v0.1.0-alpha.40 — PASS

## LOCKED параметры (anti-snooping)

```python
atr_period=9, atr_breakout_mult=2.5, atr_stop_period=21, atr_stop_mult=1.5
symbol=BTCUSDT, interval=240 (4H), signal_side_mode="long_only"
```

## Техническое исполнение

1. TDD: RED → GREEN → COMMIT per task
2. Verbatim порт autoresearch_endless.py (Wilder ATR, backtest kernel, Binance parquet)
3. Отдельный runner bypasses replay_engine (те же структурные gaps что S39)
4. Phase 5 HARD-GATE: ±0.5% tolerance на baseline 819.81% / 69 trades / Sharpe 1.11

## Статус

Все задачи выполнены. Sprint DONE.
