---
title: Sprint 3 — Strategy port (EMA + ADX + RSI + ATR via TA-Lib)
type: sprint
tags: [sprint, sprint-3, strategy, signalgen, ta-lib, indicators]
created: 2026-04-22
updated: 2026-04-22
sources: [project/plans/2026-04-22-sprint-3-strategy-port.md]
status: completed
---

# Sprint 3 — Strategy port

**Dates:** 2026-04-22
**Plan:** [[../plans/2026-04-22-sprint-3-strategy-port]]
**Tag:** `v0.1.0-alpha.3`
**Commit range:** `dc1216e..9bbdc05` (16 коммитов; финал = HEAD на момент tag)

## Goal

Портировать EMA-crossover + ADX/RSI/ATR стратегию через TA-Lib; реализовать `on_bar(Bar) -> Signal | None` с enforced look-ahead-free invariants. Source: `migration-plan.md §S3`.

## Scope delivered

### Code — indicators
- `src/signalgen/indicators.py` — 6 функций: `ema(close, period, mode)` (classical/wilder), `rsi(close, period=14)`, `atr(high, low, close, period=14)`, `adx(...)`, `plus_di(...)`, `minus_di(...)`.
- Classical EMA: `talib.EMA` (α=2/(n+1)). Wilder EMA: собственная реализация (TA-Lib не поддерживает) — seed=SMA, recurrence α=1/n.
- RSI/ATR/ADX/±DI: прямые делегаты `talib.*` (Wilder by default).
- Shared `_validate_hlc` для shape+period контрактов (DRY).

### Code — strategy
- `src/signalgen/strategy.py` — `EmaCrossoverAdxRsiStrategy` stateful класс.
  - **Контракт:** `on_bar(bar: Bar) -> Signal | None`.
  - **FSM:** `current_side` ∈ {FLAT, LONG}; FLAT→LONG (entry), LONG→FLAT (signal-flip exit).
  - **Buffer:** `max(ema_slow, 2·adx_period, atr_period, rsi_period) + 5` баров.
  - **Skip-rules:** `is_closed=False`, wrong symbol, duplicate/out-of-order bar (close_time monotonicity guard), warm-up incomplete, NaN в snapshot.
  - **Entry LONG (`ENTRY_LONG_EMA_CROSS_UP`):** cross_up AND ADX>threshold AND +DI>-DI AND RSI<overbought AND current_side=FLAT.
  - **Exit FLAT (`EXIT_FLAT_SIGNAL_FLIP`):** EMA flip down AND -DI>+DI AND current_side=LONG.

### Code — config
- `src/platform/config.py` — 8 strategy полей в `Settings`: `strategy_ema_fast=12`, `strategy_ema_slow=26`, `strategy_adx_period=14`, `strategy_adx_threshold=Decimal("25")`, `strategy_rsi_period=14`, `strategy_rsi_oversold=Decimal("30")`, `strategy_rsi_overbought=Decimal("70")`, `strategy_atr_period=14`. Defaults from `wiki/trading/strategies/ema-crossover-adx-rsi.md`.

### Tests
- Unit: `tests/unit/test_indicators.py` (9 тестов), `tests/unit/test_strategy.py` (9 сценариев: warm-up, skip-non-closed, LONG happy, ADX/RSI rejection, wrong-symbol, FLAT flip, duplicate, out-of-order), `tests/unit/test_config.py` (+1 strategy_params test), `tests/unit/test_deps.py` (+TA-Lib import sanity).
- Property: `tests/property/test_lookahead.py` — hypothesis fuzzing (30 examples) проверяет `signal.generated_at >= signal.bar_close_time` invariant.

### Config
- `pyproject.toml`: добавлен `TA-Lib>=0.4.28` (Python binding к нативному TA-Lib 0.6.8); mypy override `talib`; `testpaths` расширен до `["tests/unit", "tests/property"]`.

### Wiki
- Components: [[../components/indicators]], [[../components/strategy]].
- Plan: [[../plans/2026-04-22-sprint-3-strategy-port]].
- Modified: `index.md`, `log.md`.

### Removed
- `src/strategy/` — пустая легаси-директория от S1 (содержала только пустой `__init__.py`).

## Decisions & deviations

- **Wilder EMA — собственная реализация.** TA-Lib `EMA` поддерживает только classical (α=2/(n+1)). Для `mode="wilder"` написана прямая recurrence `α=1/n` с SMA-seed. **Rationale:** ADR 0011 требует Wilder для oscillators; чтобы единая `ema()` функция покрывала оба режима — единая точка валидации/тестирования.
- **Crafted-bars test fixture для LONG entry — re-tuned.** Plan-spec fixture (`60 bars × -0.2` + `20 bars × +1.5`) **не проходила** — резкий rally толкал RSI > 70 раньше, чем EMA12 успевал пересечь EMA26 (известное свойство MACD-style стратегии: oscillator сигналит overbought до crossover). Изменили rally на `30 bars × +0.2` (gentler, longer) — cross-up ландит на idx=74 с ADX=50.5, +DI=16.0, -DI=7.6, RSI=67.1; все gates проходят. Wick offsets `±0.5` уменьшены до `±0.3` для соответствия меньшему candle range.
- **Duplicate/OOO guard на уровне strategy.** BarBuilder (S2) уже гарантирует monotonic close_time, но добавлен defense-in-depth check в `on_bar()`: `if self._bars and bar.close_time <= self._bars[-1].close_time: return None`. **Rationale:** strategy не должна полагаться на upstream-инвариант для безопасности indicator buffer.
- **Indicator computation на full buffer каждый bar.** Простая реализация — пересчёт EMA/ADX/RSI/ATR на всём буфере. Для 1H + buffer ≤ 100 баров это <5ms. Incremental update — v0.2 refinement, не нужен на 1H.
- **`_last_signal_close_time` поле объявлено но не используется в S3.** Зарезервировано для S6 (event-bus dedup) / S5 (OCO bracket attach). Mypy `--strict` не возражает на unused field.

## Verification

- `make check`: **green** — ruff clean, mypy --strict clean, **84/84 passed** (83 unit + 1 property).
- TDD: каждый task RED → GREEN → commit (16 коммитов).
- Subagent-driven execution: 14 task-agent dispatches (haiku × 7, sonnet × 6, opus × 1 для critical LONG entry); inline-verification в controller сессии.

## Impact on downstream

- **S4 (Risk)** получает: `Signal` instance с `atr_14` в snapshot — готово для `qty = f·equity/(1.5·ATR)` Kelly sizing. `adx_14`/`rsi_14` могут использоваться как regime-индикаторы для CB tuning.
- **S5 (Execution)** получает: `Signal → Order` pipeline; `bar_close_time` для SL/TP attach к Entry; `reason_code` для audit log.
- **S6 (Event Bus)** получает: точку эмиссии `SignalGenerated` event; `signal_id` (UUID4) для idempotency.
- **S7 (Backtest)** получает: deterministic strategy object — `on_bar` чистая функция от `(bar, internal state)`, легко replay'ится на Parquet архиве.

## Follow-ups carried forward

- [ ] **Crafted-bars fixture refactor**. Сейчас `_crafted_bars_for_long_entry` дублируется логика в `test_strategy_emits_flat_on_signal_flip` (3 phases: down/up/down). Вынести общий генератор `_synthetic_trend(phases: list[tuple[int, float]])`. **Target:** S4 если время.
- [ ] **`_last_signal_close_time` field**. Объявлено в `__init__`, не используется. Удалить или wire up в S6 (event-bus dedup gate).
- [ ] **Performance bench**. `make check` за 0.97s включая 30 hypothesis examples — приемлемо. Но индикаторы пересчитываются на full buffer; при переходе к 1m timeframe (v0.2+) это ~3000 баров/час → может потребоваться incremental update. **Target:** S7 backtest perf check.
- [ ] **`test_strategy_emits_flat_on_signal_flip` — крафт Phase C** (`60 bars × -0.3`) hardcoded. Если параметры strategy (ema_slow=26, adx=14) изменятся в Settings — fixture может перестать producing FLAT. Param-sensitive — не fail-prone, но fragile.

## Related

- Plan: [[../plans/2026-04-22-sprint-3-strategy-port]]
- Components: [[../components/indicators]], [[../components/strategy]], [[../components/models]]
- Architecture: [[../architecture/migration-plan]] §S3, [[../architecture/execution-timing]]
- ADR: [[../decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover]], [[../decisions/0017-review-agent-harness]] (review-agent harness first activated в S3)
- Trading: [[../../trading/strategies/ema-crossover-adx-rsi]], [[../../trading/indicators/ema]], [[../../trading/indicators/adx]], [[../../trading/indicators/rsi]], [[../../trading/indicators/atr]]
- Prior sprint: [[sprint-02-bybit-venue-migration]]
