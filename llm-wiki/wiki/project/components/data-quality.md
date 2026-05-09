---
title: Bar price quality detector — REST-vs-REST deviation
type: component
tags: [marketdata, data-quality, halt, sprint-9]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/marketdata/quality.py
  - src/runtime/manager.py
---

# Bar price quality detector

**TL;DR:** Single-instance in-memory baseline detector comparing current REST closed bar price vs previously observed REST closed bar (per-process). Threshold = 0.5% relative deviation (Settings tunable: `runtime_quality_threshold_pct`). Per-bar cadence. Triggers `HALT_DATA_QUALITY` via existing `RISK_HALT` event path (no new FSM event/state). Wired в `RuntimeManager._poll_bar_and_strategy` BEFORE strategy consumes bar (halt is terminal — `_stopping=True` set, main loop exits).

## Публичный API

| Symbol | Path | Role |
|--------|------|------|
| `BarPriceQualityDetector.__init__` | `src/marketdata/quality.py::BarPriceQualityDetector.__init__` | raise ValueError if threshold ≤ 0 |
| `BarPriceQualityDetector.check` | `src/marketdata/quality.py::BarPriceQualityDetector.check` | returns True if abs deviation > threshold |

## Why REST-vs-REST (not WS+REST)

Per `pre-s9-backlog.md` Q1 verdict (REVISE accepted by maintainer):
- WS kline subscription does not exist (`ws_private` only subscribes order + wallet + execution).
- Wiring WS kline contradicts S8a ADR 0022 async/sync deferral к S9+.
- WS partial-bar updates create false-positive risk при per-bar comparison.
- REST-vs-REST consecutive bar deviation 0.5% on 1H BTCUSDT @ ~$100k = ~$500 instantaneous move — catches stuck/corrupted feed без new infrastructure.

## Инварианты (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | First call no baseline → returns False | `if prior is None: return False` | `tests/unit/test_quality_detector.py::test_first_poll_skips_no_prior_baseline` |
| 2 | Symmetric — abs(deviation) used | `abs(current - prior)` | `tests/unit/test_quality_detector.py::test_negative_deviation_uses_absolute_value` |
| 3 | Defensive — prior_close ≤ 0 returns False | `if prior <= 0: return False` | `tests/unit/test_quality_detector.py::test_zero_prior_close_defensive` |
| 4 | Threshold > 0 enforced at construction | `if threshold_pct <= 0: raise ValueError` | `tests/unit/test_quality_detector.py::test_negative_threshold_rejected` |
| 5 | Strict > comparison (boundary value not halt) | `if deviation_pct > threshold` | `tests/unit/test_quality_detector.py::test_threshold_at_boundary` |
| 6 | Single-instance (per-process) baseline, lost on restart | instance-only `_last_close` field | code review (docstring) |
| 7 | RuntimeManager sets `_stopping=True` on halt (terminal) | `manager.py:152` after request_halt | `tests/unit/test_runtime_manager.py::test_quality_detector_halts_on_consecutive_bar_deviation` |
| 8 | Quality check BEFORE strategy.on_bar (no bad data к strategy) | `manager.py:151` before `bar_tick` log | `test_quality_detector_halts_on_consecutive_bar_deviation` (call_count == 1) |

## Halt routing

Per ADR 0023 invariant — `HALT_DATA_QUALITY` added к `_REQUEST_HALT_CODES` allow-list. Coordinator routes via existing `RISK_HALT` event path:

```
RuntimeManager._poll_bar_and_strategy()
    bar = bar_source.poll()
    if bar_source.should_halt(threshold=stall): request_halt(HALT_BAR_POLL_STALL); return
    if bar is None: return
    if quality_detector.check(current_close=bar.close):    # S9 Q1 — quality check
        coordinator.request_halt(reason=ReasonCode.HALT_DATA_QUALITY)
        self._stopping = True   # halt terminal — main loop must exit
        return
    # ... strategy.on_bar(bar) etc.
```

## Конфигурация

`Settings.runtime_quality_threshold_pct: Decimal = Decimal("0.005")` — default 0.5%. Tunable per environment (e.g. lower threshold для prod, looser для testnet).

## Logging

Halt event logs structured warning `data_quality.deviation_exceeds_threshold` с key=value pairs (prior_close, current_close, deviation_pct quantized к 6 d.p. для log hygiene, threshold_pct).

## Referenced by

- [[runtime-manager]] — owns detector lifecycle; calls `check` after each `BarSource.poll()` returns new bar
- [[bar-poller]] — provides input data (BarSource closed bars)
- [[../runbooks/halt-recovery]] — operator runbook covers HALT_DATA_QUALITY (Operational class group — defer category mapping check к runbook update)

## Связанные

- [[../sprints/sprint-09-data-quality-types-analytics]] — sprint where data-quality detector was created
- [[../decisions/0024-sprint-9-data-quality-types-analytics]] — origin ADR (Q1)
- [[../decisions/0023-halt-code-fsm-event-mapping]] — `_REQUEST_HALT_CODES` invariant (HALT_DATA_QUALITY added к allow-list)
- [[coordinator]] — `request_halt` halt entry-point + RISK_HALT event routing
- [[circuit-breakers]] — sister halt detectors (drawdown / flash crash)
- [[../architecture/edge-cases]] — edge case catalog: gap/stale/OHLC-inconsistent triggers.

## Sources

- `src/marketdata/quality.py` — implementation
- `src/runtime/manager.py::_poll_bar_and_strategy` — integration point
- `src/platform/config.py::runtime_quality_threshold_pct` — Settings field
- `tests/unit/test_quality_detector.py` (8 tests)
- `tests/unit/test_runtime_manager.py::test_quality_detector_*` (2 tests)
- `tests/unit/test_coordinator_request_halt.py::test_request_halt_data_quality_routes_to_risk_halt` (1 test)
- `tests/property/test_request_halt_mapping.py` (HALT_DATA_QUALITY в _REQUEST_HALT_CODES)
