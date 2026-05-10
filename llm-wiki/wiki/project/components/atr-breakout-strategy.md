---
title: ATRBreakoutStrategy Component
type: component
tags: [component, signalgen, atr-breakout, long-only, sprint-40, locked-pre-registration, autoresearch, ru]
created: 2026-05-10
updated: 2026-05-10
status: active
sources:
  - src/signalgen/atr_breakout_strategy.py
  - src/backtest/atr_breakout_runner.py
  - project/decisions/0060-sprint-40-atr-breakout-pre-registration.md
---

# ATRBreakoutStrategy

**TL;DR:** Long-only ATR breakout стратегия (S40 autoresearch production integration per ADR 0060 LOCKED). Autoresearch iter 1 BTCUSDT 4H. Backtest verdict = **PASS** — 8.7y +819.81% / Sharpe 1.11 / 5/5 sub-periods positive (первый 5/5 в истории проекта). **S42:** Dashboard preset переименован в `atr_breakout` (unified, 10 combos). `verdict: "RAW"` + `RAW_FULL_PERIOD` warning chip до S43 WFA retrofit (per ADR 0062).

## Назначение

Pre-registered 9th hypothesis (N_trials=9 cumulative: S13/S15/S17/S20/S22/S33/S35/S39/S40) per ADR 0060. Anti-snooping LOCKED params + symbol + timeframe BEFORE production integration.

## LOCKED параметры (`ATR_BREAKOUT_LOCKED_PARAMS`)

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| `atr_period` | 9 | Wilder ATR для breakout band |
| `atr_breakout_mult` | 2.5 | Entry/exit band multiplier |
| `atr_stop_period` | 21 | Wilder ATR для trailing stop |
| `atr_stop_mult` | 1.5 | Stop = entry_close - ATR_stop × 1.5 |
| `signal_side_mode` | `"long_only"` | FSM SignalSide invariant |

Символ: BTCUSDT. Таймфрейм: 4H. **НЕ ИЗМЕНЯТЬ без нового ADR.**

## Публичный API

### ATRBreakoutStrategy (src/signalgen/atr_breakout_strategy.py)

```python
class ATRBreakoutStrategy:
    def __init__(self, *, symbol: str) -> None: ...
    def on_bar(self, bar: Bar) -> Signal | None: ...
```

Warmup gate: `max(atr_period, atr_stop_period) + 3 = 24` bars. До warmup возвращает `None`.

### run_atr_breakout_backtest (src/backtest/atr_breakout_runner.py)

```python
def run_atr_breakout_backtest(
    *,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]: ...
# Returns: {n_trades, total_pnl_pct, sharpe, win_rate, trades}
```

## Логика входа/выхода

**Индексация** (в `on_bar(bar_T)`): после append buffer, `closes[-1]=T`, `closes[-2]=T-1`, `closes[-3]=T-2`.

**Вход (LONG) — сигнал на bar(T), fill at open(T+1):**
```
close[T-1] > close[T-2] + 2.5 × ATR[T-2]
AND current_side == FLAT
```

**Выход — приоритет 1 (ATR reverse):**
```
close[T-1] < close[T-2] - 2.5 × ATR[T-2]
→ EXIT_FLAT_ATR_REVERSE
```

**Выход — приоритет 2 (ATR stop intrabar):**
```
bar.low ≤ entry_close - 1.5 × ATR_stop[-1]
→ EXIT_FLAT_ATR_STOP_AB
```

## ReasonCodes (S40 +3)

| Код | Описание | Направление |
|-----|----------|-------------|
| `ENTRY_LONG_ATR_BREAKOUT` | Вход в long (ATR breakout выше band) | → LONG |
| `EXIT_FLAT_ATR_REVERSE` | Выход — обратный ATR breakdown | → FLAT |
| `EXIT_FLAT_ATR_STOP_AB` | Выход — ATR stop triggered (atr_breakout специфичный) | → FLAT |

## Backtest Evidence (ADR 0060)

| Метрика | Значение | Примечание |
|---------|----------|------------|
| Период | 8.7y (2017-08-17 → 2026-04-30) | Binance 4H BTCUSDT |
| Additive PnL | **+819.81%** | Sequential, 0.1% комиссия + 0.05% slippage |
| n_trades | **69** | |
| Sharpe | **1.11** | Annualized |
| Sub-periods | **5/5 positive** | Equal chunks 635 дней каждый |
| Данные | Binance parquet (`data/BTCUSDT_4h_binance.parquet`) | Bybit с 2023 — недостаточно |

## Profit Invariant (HARD-GATE)

Phase 5 gate: `tests/integration/test_atr_breakout_baseline_floor.py` (8 тестов)

```
8.7y PnL ≥ +819.31% (±0.5%) AND n_trades = 69
5/5 sub-periods positive
Production runner: PnL ≥ +819.31%, n_trades ≈ 69 (±2)
Sharpe ≥ 0.5
```

## Конфигурация

Dashboard preset `atr_breakout` (`src/dashboard/backtest_runner.py`) — **S42 unified preset (replaces `atr_breakout_iter_endless` + 9 S41 presets)**:
- `type`: `"atr_breakout"` → envelope dispatch к `atr_breakout_runner` + `build_research_runner_envelope()`
- `supported_combos`: 10 (symbol, interval) пар — server-side params lookup в `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[(sym, tf)]`
- Frontend `applyComboGates()` greys out invalid sym/TF combinations
- Returns 17-key dashboard contract dict via `src/backtest/research_runner_envelope.py::build_research_runner_envelope()`
- `verdict: "RAW"` + `RAW_FULL_PERIOD` warning chip (WFA retrofit pending S43)
- Invalid combos rejected с 422 через `GET /api/strategy/{id}/info` enforcement

**Примечание:** Acceptance gate (WFA + DSR + MC + T1-T6) temporarily skipped. S43 будет retrofit per ADR 0062.

## Инварианты

1. **Long-only** — `signal_side_mode = "long_only"`. SHORT сигналы никогда не генерируются.
2. **No look-ahead** — `on_bar(bar)` использует только `closes[-2]` и `closes[-3]` (T-1 и T-2). ATR[-2] вычисляется на исторических данных — нет snooping на current bar close для signal check.
3. **Single-producer** — instance привязан к одному символу. Coordinator single-writer invariant.
4. **Immutable params** — `ATR_BREAKOUT_LOCKED_PARAMS` frozen. Изменение требует нового ADR.
5. **Warmup gate** — 24 bars до первого сигнала. Ранние bars → `None`.
6. **Wilder ATR exact port** — `_wilder_atr()` static method = verbatim copy autoresearch `_atr()`.

## Тесты

- `tests/unit/test_atr_breakout_strategy.py` — 8 unit tests (params, warmup, entry, exit, long-only)
- `tests/unit/test_reason_codes_s40.py` — 4 reason code tests
- `tests/integration/test_atr_breakout_baseline_floor.py` — 8 Phase 5 HARD-GATE tests

## Связанные

- [[../decisions/0062-sprint-42-atr-breakout-hardening]] — ADR 0062 S42 retrofit: envelope contract + preset consolidation (current)
- [[../decisions/0060-sprint-40-atr-breakout-pre-registration]] — ADR 0060 LOCKED params + acceptance criteria (superseded by 0062)
- [[../sprints/sprint-42-atr-breakout-hardening]] — S42 sprint (envelope retrofit)
- [[../sprints/sprint-40-atr-breakout-production]] — S40 sprint (original implementation)
- [[volume-breakout-strategy]] — сестринская стратегия (S39, same envelope wrap applied S42)
- [[strategy]] — EmaCrossoverAdxRsiStrategy (основная production стратегия, FSM контракт)
- [[indicators]] — Wilder ATR shared pattern
