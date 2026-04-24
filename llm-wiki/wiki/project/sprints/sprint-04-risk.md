---
title: Sprint 4 — Risk module (4-phase Kelly + L1/L2/L3/flash circuit breakers)
type: summary
tags: [sprint, sprint-4, risk, kelly, circuit-breakers, override]
created: 2026-04-23
updated: 2026-04-23
sources: [project/plans/2026-04-23-sprint-4-risk.md]
status: done
---

# Sprint 4 — Risk module

**Dates:** 2026-04-23
**Plan:** [[../plans/2026-04-23-sprint-4-risk]] (split into [[../plans/2026-04-23-sprint-4-risk-tasks-1-8]] / [[../plans/2026-04-23-sprint-4-risk-tasks-9-13]] / [[../plans/2026-04-23-sprint-4-risk-tasks-14-17]])
**Tag:** skipped — S4 merged into `v0.1.0-alpha.6` (consolidates S4+S5+S6 ship). Drift note: original plan tagged `v0.1.0-alpha.4 (pending PR merge)` 2026-04-23, но tag `alpha.4` never created. Reconciled 2026-04-25.
**Commit range:** `a5d38a8..HEAD` (17 commits включая wiki delivery)

## Goal

Реализовать risk-управление per ADR 0012 (4-phase Kelly + Wilson 95% CI) и ADR 0013 (L1/L2/L3/flash CB). Обеспечить look-ahead-free decision pipeline через `RiskManager.assess(signal, mark_price) -> RiskAssessment`. Добавить override mechanism для manual CB resume с config_hash anti-replay.

## Scope delivered

### Code — risk module (`src/risk/`)

- `reason_codes.py` — 29-code `StrEnum` (entry=6, scale/exits=8, rejects=8, halts=7). Wiki ранее заявлял 28 — typo исправлен в S4.
- `models.py` — `HaltState` enum (`L0|L1|L2|L3|FLASH`) + `RiskAssessment` frozen pydantic v2 value object.
- `sizing.py` — `compute_qty(equity, fraction, atr, price, k=1.5)` pure function.
- `kelly.py` — `KellyCaps` + 4 functions: `phase_from_trade_count`, `wilson_95_ci` (Agresti-Coull), `kelly_fraction`, `phase_adjusted_fraction`.
- `circuit_breakers.py` — `CircuitBreakerConfig` + `CircuitBreakerDetector` (stateless: `check_drawdown`, `check_flash`).
- `equity_tracker.py` — `EquityTracker` с 24h rolling HWM (NOT all-time peak — recovery после длинной просадки не блокируется навсегда).
- `trade_history.py` — `TradeHistoryRepository` + `TradeRecord`. UNIQUE INDEX на `entry_signal_id` для idempotent insert. `AwareDatetime` всюду.
- `override.py` — `CbOverride` + `OverrideStore` (file JSON, валидация по `config_hash`).
- `state_repo.py` — `StateRepository.update_many` для атомарного flush.
- `resume_cb.py` + `__main__.py` — CLI: `python -m src.risk.resume_cb --level L2 --reason "..." --duration-hours 24`.
- `manager.py` — `RiskManager` orchestrator. См. [[../components/risk-manager]].

### Code — config (`src/platform/config.py`)

13 новых полей `risk_*`:
- Kelly caps (`risk_kelly_phase{1,2,3,4}_cap`)
- CB thresholds (`risk_cb_l{1,2,3}_dd`, `risk_cb_flash_abs`, `risk_cb_flash_atr_mult`)
- Sizing/SL/TP (`risk_sl_atr_multiplier=1.5`, `risk_tp_atr_multiplier=3.0`)
- Override path (`risk_override_path`)

`Settings.config_hash()` — SHA-256 от `model_dump_json(...)` sort_keys для override anti-replay.

### Migrations

- `migrations/002_risk.sql` — `trade_history` + `equity_snapshots` (TEXT для Decimal money + CHECK constraints + 3 indexes).
- `migrations/003_trade_history_unique.sql` — UNIQUE INDEX `entry_signal_id` (forward-only fix Task 7 blocker).

### Cleanup

- Removed legacy `src/risk/risk_manager.py` (старая stub) и `src/core/math_engine.py` (mock Kelly).
- `src/risk/__init__.py` обновлён — экспортирует `RiskManager` из нового модуля.

### Tests

- Unit (8 файлов): `test_risk_settings.py`, `test_risk_models.py`, `test_risk_migration.py`, `test_risk_sizing.py`, `test_risk_kelly.py`, `test_risk_equity_tracker.py`, `test_risk_circuit_breakers.py`, `test_risk_trade_history.py`, `test_risk_override.py`, `test_risk_state_repo.py`, `test_risk_manager.py`.
- Integration: `tests/integration/test_risk_flow.py` — 50-bar synthetic price series, 8 сценариев (normal entry → L1 escalation → L2 halt → manual resume → flash detection → recovery → re-entry).
- **Total:** 308 tests passing на момент integration задачи (Task 15).

### Wiki

- Components: [[../components/kelly]], [[../components/circuit-breakers]], [[../components/sizing]], [[../components/risk-manager]].
- Concept fix: [[../../trading/concepts/reason-codes]] (28→29).
- ADR: [[../decisions/0018-sprint-4-risk-decisions]].

## Tasks (17 total)

| # | Task | Status | Commit |
|---|---|---|---|
| 1 | Migration 002 (trade_history + equity_snapshots) | done | `a5d38a8` |
| 2 | Settings risk fields + config_hash | done | `4db822e` |
| 3+4 | ReasonCode enum + HaltState + RiskAssessment | done | `70182b9` |
| 5 | `sizing.compute_qty` + property test | done | `de68236` |
| 6 | 4-phase Kelly + Wilson 95% CI | done | `9b7f5d4` |
| 7 | TradeHistoryRepository (+ Task 7 blocker fix) | done | `ce934a4`, `2723029` |
| 8 | EquityTracker 24h HWM | done | `5594662` |
| 9 | CircuitBreakerDetector | done | `01c6b3f` |
| 10+11+13 | OverrideStore + StateRepository + resume_cb CLI | done | `f095610` |
| 12 | RiskManager orchestrator + look-ahead invariant | done | `df4e4e5` |
| 14 | Legacy cleanup (`risk_manager.py`, `math_engine.py`) | done | `01da928` |
| 15 | Integration test 50-bar flow | done | `5b872a6` |
| 16+17 | Wiki + ADR delivery | done | this commit |

## Decisions made (collected in ADR 0018)

1. **R:R = 2:1 default** (`sl_mult=1.5`, `tp_mult=3.0` ATR units).
2. **REJECT_INVALID_SIGNAL / REJECT_ZERO_QTY НЕ распаковываются отдельно** — current MIN_NOTIONAL/RISK_EXCEEDED достаточно. Re-evaluate в S5 (executor).
3. **Wilson lower bound contract** для phases 3/4 (не точечная оценка).
4. **L0 = explicit naming** (NOT `null`) для halt state.
5. **Reason codes mapping table** — приведена в `reason_codes.py` docstring + ADR 0018.

## Follow-ups for v0.2+

- `EXIT_TRAILING_STOP` / `SCALE_*` коды зарезервированы, не имплементятся.
- `REJECT_INVALID_SIGNAL` отдельный код — рассмотреть в S5 если executor нужно различать.
- VoltAgent `security-auditor` review для `override.py` (file IO, JSON deserialization, config_hash) — приоритет S5 при работе с API keys.

## Verification

```bash
pytest -q                    # 308 passed
mypy src/                    # 0 errors
ruff check src/ tests/       # 0 errors
python -m src.risk.resume_cb --help   # CLI works
```

## Related

- [[../plans/2026-04-23-sprint-4-risk]]
- [[../components/risk-manager]] [[../components/kelly]] [[../components/circuit-breakers]] [[../components/sizing]]
- [[../decisions/0012-4-phase-kelly-sizing]] [[../decisions/0013-circuit-breakers-l1-l2-l3-flash]] [[../decisions/0018-sprint-4-risk-decisions]]
- [[../../trading/concepts/kelly-phases]] [[../../trading/concepts/circuit-breakers]] [[../../trading/concepts/reason-codes]]
