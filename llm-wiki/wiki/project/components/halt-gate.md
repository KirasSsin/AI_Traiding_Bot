---
title: HaltGate Component
type: component
tags: [component, risk, halt-criteria, sprint-35, testnet-demo, ru]
created: 2026-04-27
updated: 2026-04-27
status: stable
sources:
  - src/risk/halt_gate.py
  - project/decisions/0053-sprint-35-testnet-live-demo.md
  - project/pre-s35-backlog.md
---

# HaltGate

**TL;DR:** Pre-committed halt criteria evaluator для S35 δ TESTNET live demo. 4 приоритета-упорядоченных триггера (intraday DD, multi-day DD, consecutive losses, no-trade timeout). Frozen dataclass, pure function — no I/O, no globals.

## Назначение

Per pre-s35-backlog.md ROUND 3 binding HALT критерии — anti-snooping дисциплина LOCKED перед live activation. Оценивает, должна ли δ TESTNET сессия halt и trigger S36 honest close.

Ортогонален `CircuitBreakerDetector` (который оценивает session-level price-action drawdown). HaltGate оценивает session-behavioral метрики (loss streaks, signal frequency timeout).

## Public API

- `HaltGate.__init__(*, dd_intraday_threshold, dd_multiday_threshold, consecutive_losses_threshold, no_trade_months_threshold)` — frozen dataclass, валидирует все thresholds positive в `__post_init__`
- `HaltGate.evaluate(*, intraday_dd, multiday_dd, consecutive_losses, months_since_last_trade) -> HaltTrigger | None` — возвращает первый триггер или None если все pass

## Параметры (через src/platform/config.py)

| Setting | Default | Range | Source |
|---------|---------|-------|--------|
| `s35_halt_dd_intraday` | 0.20 | (0, 0.50] | pre-commit ROUND 3 |
| `s35_halt_dd_multiday` | 0.15 | (0, 0.50] | pre-commit ROUND 3 |
| `s35_halt_consecutive_losses` | 5 | [1, 20] | pre-commit ROUND 3 |
| `s35_halt_no_trade_months` | 6 | [1, 24] | pre-commit ROUND 3 |

Все 4 в `_HASH_ALLOWLIST` (ADR 0018 H1 — risk-decision fields invalidate CB override on change).

## Триггеры (приоритет)

1. `HaltTrigger.DD_INTRADAY` — самый срочный (flash drawdown)
2. `HaltTrigger.DD_MULTIDAY` — cumulative loss
3. `HaltTrigger.CONSECUTIVE_LOSSES` — degenerate-edge signal
4. `HaltTrigger.NO_TRADE_TIMEOUT` — signal-frequency starvation

Хранятся как StrEnum values (`S35_DD_INTRADAY` etc.) — написано к halt_log.context_json.

## Инварианты

- Все thresholds positive (валидирование в `__post_init__`, raises ValueError)
- First trigger wins (no AND-combination — most urgent fires immediately)
- Возвращает `None` если все checks pass
- Pure function — no I/O, no globals, frozen dataclass

## Wiring (S35 T5 статус)

HaltGate currently UNWIRED к RiskManager. T5 не wires в production execution path — backtest verdict α FAIL conjoint = δ activation deferred к S36+ pending operator decision. When wired:
- State source: `intraday_dd` от `EquityTracker.intraday_dd_pct()`, `consecutive_losses` от `TradeHistoryRepository.recent_streak()`, `months_since_last_trade` clock-derived от `TradeHistoryRepository.last_trade_ts()`.

## Related

- [[../decisions/0053-sprint-35-testnet-live-demo]] — δ TESTNET activation ADR
- [[../decisions/0052-sprint-34-acceptance-criteria-amendment]] — gate thresholds source
- [[../pre-s35-backlog]] — ROUND 3 binding consilium
- [[circuit-breakers]] — orthogonal price-action halt detector
