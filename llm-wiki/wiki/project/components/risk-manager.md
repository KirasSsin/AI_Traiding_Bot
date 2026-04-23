---
title: RiskManager (orchestrator)
type: component
tags: [risk, orchestrator, look-ahead, v0.1]
created: 2026-04-23
updated: 2026-04-23
status: stable
sources: [src/risk/manager.py, ADR 0012, ADR 0013, ADR 0018]
---

# RiskManager — risk module orchestrator

**TL;DR:** Точка входа Risk модуля. Композирует `EquityTracker`, `CircuitBreakerDetector`, `Kelly` (4-phase + Wilson lower bound), `compute_qty`, `OverrideStore`, `StateRepository`, `TradeHistoryRepository`. Возвращает `RiskAssessment` (frozen pydantic v2). Enforces look-ahead invariant (`assessed_at >= signal.generated_at`).

## Public API

`src/risk/manager.py`:

```python
class RiskManager:
    def __init__(self, *, conn: Connection, settings: Settings,
                 clock: Callable[[], datetime] = ...) -> None: ...

    # Lifecycle
    def load_state(self) -> None
    def persist_state(self) -> None  # via update_equity flush

    # Hot path
    def update_equity(self, *, realized: Decimal, unrealized: Decimal,
                      ts: datetime) -> None
    def on_bar_close(self, bar: object) -> None
    def assess(self, signal: Signal, *, mark_price: Decimal) -> RiskAssessment

    # Persistence
    def record_closed_trade(self, record: TradeRecord) -> int
```

`Signal` — `src/signalgen/models.py`. `RiskAssessment` — `src/risk/models.py` (frozen pydantic v2).

## Decision pipeline (assess)

```
                       ┌────────────────────────┐
signal + mark_price → │  1. clock() → assessed_at │
                       │  2. assert assessed_at >= signal.generated_at  ← LOOK-AHEAD GATE
                       │  3. override = OverrideStore.read_active(now, expected_config_hash)
                       │  4. if prev_close: check_flash → maybe escalate to FLASH
                       │  5. if current_halt != L0:
                       │        if override matches level → continue
                       │        else → reject(HALT_DRAWDOWN_L*|HALT_FLASH_CRASH)
                       │  6. n = trades.count(); phase = phase_from_trade_count(n)
                       │  7. p, b = _compute_p_b(phase)   ← Wilson lower bound for 3/4
                       │  8. f = phase_adjusted_fraction(phase, p, b, KellyCaps)
                       │  9. qty = compute_qty(equity, f, atr, price, k=sl_mult)
                       │ 10. qty = quantize(8dp); if qty <= 0 → REJECT_MIN_NOTIONAL
                       │ 11. sl = price - sl_mult·ATR; tp = price + tp_mult·ATR
                       │ 12. return RiskAssessment(approved=True, qty, sl, tp, ...)
                       └────────────────────────┘
```

## Invariants (CRITICAL)

| # | Invariant | Enforcement |
|---|---|---|
| 1 | **Look-ahead:** `assessed_at >= signal.generated_at` | `ValueError` raised in `assess` step 2 |
| 2 | **Halt severity ordering:** L3 > L2 > L1 > L0; FLASH > L3 | `_halt_severity` table + `if new > current: escalate` |
| 3 | **Wilson lower bound for phases 3/4** | `_compute_p_b` returns `wilson_95_ci(...)[0]`, not `wins/total` |
| 4 | **Override match required:** override применяется ТОЛЬКО если `override.level == current_halt` | step 5 check |
| 5 | **Atomic equity flush:** equity snapshot + state update в одной транзакции | `EquityTracker.record` + `StateRepository.update_many` (no separate commits) |
| 6 | **Decimal everywhere monetary:** `qty`, `sl`, `tp`, `equity`, `fraction` — Decimal; `p, b` — float (statistical) | type signatures + tests |

## Reason code mapping

| Outcome | `RiskAssessment.reason_code` | `approved` |
|---|---|---|
| Entry approved | `ENTRY_LONG_TREND_FOLLOWING` | True |
| L1/L2/L3 active, no override | `HALT_DRAWDOWN_L1\|L2\|L3` | False |
| Flash detected, no override | `HALT_FLASH_CRASH` | False |
| `qty == 0` after quantize | `REJECT_MIN_NOTIONAL` | False |

См. [[../../trading/concepts/reason-codes]] (29 enum). v0.1 не маппит `REJECT_INVALID_SIGNAL` / `REJECT_ZERO_QTY` отдельно — см. ADR 0018 для rationale.

## State persistence schema

`migrations/002_risk.sql` + `003_trade_history_unique.sql`:

- `trade_history` — closed trades (UNIQUE INDEX on `entry_signal_id` для idempotent insert)
- `equity_snapshots` — каждый equity update (`realized`, `unrealized`, `source`)
- `state` (existing) — CB current level + override metadata

CB level survive restart через `RiskManager.load_state()` → читает `risk:cb:current_level` из `state` table.

## Settings (config_hash anti-replay)

`Settings.config_hash()` возвращает SHA-256 от `model_dump_json()` (sort keys). `OverrideStore.read_active` отвергает override с `config_hash` не совпадающим с текущим — защита от подмены конфига при активном override.

## Tests

- Unit: 8 файлов (`test_risk_*`) — каждый компонент изолированно
- Integration: `tests/integration/test_risk_flow.py` — 50-bar synthetic price series, 8 сценариев (normal entry → L1 escalation → L2 halt → manual resume → flash → recovery)

## Related

- [[../decisions/0012-4-phase-kelly-sizing]] — Kelly source of truth
- [[../decisions/0013-circuit-breakers-l1-l2-l3-flash]] — CB source of truth
- [[../decisions/0018-sprint-4-risk-decisions]] — Sprint 4 sub-decisions (R:R, reason codes mapping, Wilson lower bound contract, L0 naming)
- [[kelly]] [[circuit-breakers]] [[sizing]] [[override]] — sub-components
- [[../../trading/concepts/look-ahead-bias]] — invariant context
