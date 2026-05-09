---
title: HaltGate Wire-up Component (S36)
type: component
tags: [component, runtime, halt-gate, testnet-demo, sprint-36, ru]
created: 2026-04-27
updated: 2026-04-27
status: stable
sources:
  - src/runtime/manager.py
  - src/risk/halt_gate.py
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/components/halt-gate.md
---

# HaltGate Wire-up

**TL;DR:** RuntimeManager._tick HaltGate evaluation per ADR 0055 SD-3 + SD-4. Fires production halt path когда settings.s35_demo_active=True. State-source methods (T3) feed inputs. HaltTrigger → ReasonCode dispatch via module-level mapping.

## Назначение

S35 T2 created HaltGate (pure function evaluator). S36 T4 wired к live runtime. _tick() now: kill_switch → check_alive → halt_gate (NEW) → poll_bar_and_strategy. Halt fires BEFORE strategy on_bar — no new positions opened.

## Архитектура подключения

```
RuntimeManager._tick()
  |
  if settings.s35_demo_active:
    _check_halt_gate()
      | Compute inputs (T3 state-source methods):
      |-- intraday_dd <-- EquityTracker.intraday_dd_pct()
      |-- multiday_dd <-- (HWM since activation_ts - current) / HWM
      |-- consecutive_losses <-- TradeHistoryRepository.consecutive_losses(symbol)
      +-- months_since_last_trade <-- (now - last_trade_ts) // 30
      | HaltGate.evaluate(...)
      | trigger? -> _HALT_TRIGGER_TO_REASON[trigger] -> coordinator.request_halt(reason)
      +-- self._stopping = True (no auto-resume per ADR 0055 SD-5)
```

## Персистентность состояния

Activation timestamp persisted в SQLite via `StateRepository`:
- Key: `runtime:halt_gate:activation_ts` (per architecture-reviewer namespace convention)
- Value: `{"value": "2026-04-27T..."}`
- Written ONCE on first call, instance-cached afterward (per architecture-reviewer MEDIUM fix)
- Read on bot restart → multiday HWM window preserved across sessions

## Маппинг HaltTrigger → ReasonCode (ADR 0055 SD-4)

| HaltTrigger | ReasonCode | Numeric |
|-------------|------------|---------|
| `DD_INTRADAY` | `HALT_S36_DD_INTRADAY` | 46 |
| `DD_MULTIDAY` | `HALT_S36_DD_MULTIDAY` | 47 |
| `CONSECUTIVE_LOSSES` | `HALT_S36_CONSECUTIVE_LOSSES` | 48 |
| `NO_TRADE_TIMEOUT` | `HALT_S36_NO_TRADE_TIMEOUT` | 49 |

Distinct codes preserve audit-log attribution (NOT reused HALT_DRAWDOWN_L*).

## DI-поверхность (S36)

RuntimeManager constructor extended +3 required kwargs:
- `equity_tracker: EquityTracker`
- `trade_repo: TradeHistoryRepository`
- `state_repo: StateRepository`

Sourced from RiskManager properties (`risk_manager.equity_tracker / trade_repo / state_repo`) для shared SQLite connection.

## Протокол возобновления после halt (ADR 0055 SD-5)

HaltGate-triggered halt = NO automatic resume. `_stopping=True` exits bot cleanly. Operator must:
1. Review halt_log audit trail (reason + DD/streak/timeout values)
2. Document review findings
3. Manual FSM reset через `--reconcile-only` CLI subcommand OR new ADR
4. Restart с adjusted Settings (operator decision)

## Тесты

7 integration tests в `tests/integration/test_halt_gate_wireup.py`:
- DD_INTRADAY trigger fires HALT_S36_DD_INTRADAY
- CONSECUTIVE_LOSSES trigger fires HALT_S36_CONSECUTIVE_LOSSES
- DD_MULTIDAY trigger fires HALT_S36_DD_MULTIDAY (added per trading-logic C1 review)
- NO_TRADE_TIMEOUT trigger fires HALT_S36_NO_TRADE_TIMEOUT (added per trading-logic C1 review)
- No-trigger path returns False
- Demo-inactive bypass returns False without computation
- activation_ts persisted on first call, NOT overwritten

Property test (T5): all 4 HALT_S36_* codes correctly dispatch к FSM HALTED state.

## Перенос к S37+

- security HIGH: symbol fail-closed semantic (currently warning + skip)
- security HIGH: activation_ts integrity hardening (SQLite tamper-detection)
- trading-logic C2: clock injection для testability
- trading-logic C3: coordinator.symbol public property (replace _symbol private access)
- architecture MEDIUM: RiskSharedDeps refactor (Demeter violation)

## Связанные

- [[../decisions/0055-sprint-36-delta-activation]] — primary ADR
- [[../decisions/0053-sprint-35-testnet-live-demo]] — δ activation predecessor
- [[halt-gate]] — pure HaltGate dataclass component (S35)
- [[runtime-manager]] — owning lifecycle component
