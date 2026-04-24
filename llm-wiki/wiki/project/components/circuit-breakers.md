---
title: Circuit Breakers (L1/L2/L3/Flash)
type: component
tags: [risk, circuit-breakers, drawdown, v0.1]
created: 2026-04-23
updated: 2026-04-23
status: stable
sources: [src/risk/circuit_breakers.py, ADR 0013]
---

# Circuit Breakers — L1/L2/L3/Flash

**TL;DR:** Stateless detector над `(peak, current)` и `(bar_close, prev_close, atr)`. Возвращает `HaltState` enum. Thresholds инжектятся через `CircuitBreakerConfig` из `Settings` — никаких magic numbers в коде.

## Public API

`src/risk/circuit_breakers.py`:

```python
@dataclass(frozen=True)
class CircuitBreakerConfig:
    l1_dd: Decimal           # 0.15
    l2_dd: Decimal           # 0.22
    l3_dd: Decimal           # 0.30
    flash_abs: Decimal       # 0.08
    flash_atr_mult: Decimal  # 3.0

class CircuitBreakerDetector:
    def check_drawdown(self, *, peak: Decimal, current: Decimal) -> HaltState
    def check_flash(self, *, bar_close: Decimal, prev_close: Decimal, atr: Decimal) -> bool
```

`HaltState` (`src/risk/models.py`): `L0 | L1 | L2 | L3 | FLASH`. `L0` = no halt.

## Levels (ADR 0013)

| Level | Trigger | Reason code | Action (executor) |
|---|---|---|---|
| L0 | DD < 15% | — | normal trading |
| L1 | 15% ≤ DD < 22% | `HALT_DRAWDOWN_L1` | warn + reduce next entry size 50% |
| L2 | 22% ≤ DD < 30% | `HALT_DRAWDOWN_L2` | halt 24h, no new entries |
| L3 | DD ≥ 30% | `HALT_DRAWDOWN_L3` | full stop, manual resume only |
| Flash | one-bar drop > `max(8%, 3·ATR/prev_close)` | `HALT_FLASH_CRASH` | immediate halt |

DD% computed as `(peak − current) / peak`. `peak` приходит из `EquityTracker.peak_equity_24h(now=ts)` — 24h rolling HWM (NOT all-time, чтобы recovery после длинной просадки не блокировал систему вечно).

## Defensive contracts

- `peak ≤ 0` → `L0` (нет смысла считать drawdown без капитала).
- `current ≥ peak` → `L0` (нет drawdown).
- `prev_close ≤ 0` → `check_flash` returns `False` (defensive).
- `check_drawdown` возвращает **highest** triggered level (severity ordering: L3 > L2 > L1 > L0).

## State persistence

CB state хранится в SQLite `state` table (NOT в RAM only — survive restart):

```json
key: "risk:cb:current_level"
value: {"level": "L2", "triggered_at": "2026-04-23T...", "peak_equity": "10000", "dd_pct": "0.225"}
```

`RiskManager.update_equity` flush'ит атомарно через `StateRepository.update_many` после каждого equity snapshot.

## Override (manual resume)

CB level downgrade требует `CbOverride` запись (см. [[risk-override]]). Файловый JSON, валидируется по `expected_config_hash` (anti-replay). Применяется только если `override.level == current_halt`.

CLI: `python -m src.risk.resume_cb --level L2 --reason "..." --duration-hours 24`.

## Settings binding

```toml
risk_cb_l1_dd        = "0.15"
risk_cb_l2_dd        = "0.22"
risk_cb_l3_dd        = "0.30"
risk_cb_flash_abs    = "0.08"
risk_cb_flash_atr_mult = "3.0"
risk_override_path   = "data/risk_override.json"
```

## Tests

`tests/unit/test_risk_circuit_breakers.py` — boundary tests на каждый порог + flash при разных ATR + defensive cases (`peak=0`, `current>peak`).

## Invariants (CRITICAL — verified by tests + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | `check_drawdown` returns highest triggered level (L3>L2>L1>L0 — never partial/unclear) | `src/risk/circuit_breakers.py` priority logic + ADR 0013 | `tests/unit/test_risk_circuit_breakers.py` |
| 2 | `peak<=0` → L0 defensive (no halt on uninitialized state) | `src/risk/circuit_breakers.py` guard | `tests/unit/test_risk_circuit_breakers.py` |
| 3 | Flash: `prev_close<=0` → False defensive | `src/risk/circuit_breakers.py` flash guard | `tests/unit/test_risk_circuit_breakers.py` |
| 4 | Stateless detector — no I/O, caller owns persistence | `src/risk/circuit_breakers.py` no module-level state | (architecture rule) |

## Related

- [[../decisions/0013-circuit-breakers-l1-l2-l3-flash]] — source of truth
- [[../../trading/concepts/circuit-breakers]] — концепции и тестовые сценарии
- [[risk-manager]] — orchestration + escalation logic
- [[risk-override]] — manual resume mechanism
