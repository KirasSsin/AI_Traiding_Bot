---
title: Backtest harness (replay engine + vector backtest + reporter + indicators + data collector)
type: component
tags: [backtest, replay, vector-backtest, reporter, indicators, sprint-2, deferred-s9]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/backtest/replay_engine.py
  - src/backtest/vector_backtest.py
  - src/backtest/reporter.py
  - src/backtest/indicators.py
  - src/backtest/data_collector.py
  - src/backtest/replay.py
---

# Backtest harness

> **Status: S2-era reference, no active development S3–S8b. DSR / MC permutations / WFA deferred to S9+.**

**TL;DR:** Загружает исторические OHLCV-данные из CSV/Parquet, прогоняет стратегию в bar-by-bar симуляции без look-ahead, вычисляет трейды и портфельные KPI, записывает CSV/JSON/HTML-артефакты.

## Overview

Пайплайн состоит из четырёх шагов: (1) `data_collector.load_market_data()` читает OHLCV из файла, нормализует колонки и фильтрует диапазон дат; (2) `replay_engine.run_replay()` прогоняет бар за баром, вызывая `indicators.calculate_indicators()` для предварительной обработки всего DataFrame; (3) `vector_backtest.VectorBacktester` предоставляет быструю pandas-векторизованную альтернативу для быстрой проверки корректности сигналов без bar-by-bar overhead; (4) `reporter.write_artifacts()` собирает equity-кривую, трейд-лог и сводку KPI в файлы.

Модуль написан в Sprint 2 как автономный инструмент для офлайн-проверки стратегии. Начиная с S3, активная разработка перешла на live-стек (`src/signalgen/`, `src/execution/`). Бэктест-модуль не трогался S3–S8b и исключён из ruff/mypy (`pyproject.toml`: `src/backtest/*` excluded pending retirement). Никаких гарантий форвард-совместимости нет.

Статистическая методология (WFA train=2000/test=500/K=5/embargo=20, MC sign-flip N=2000, DSR) задокументирована в ADR 0014 и 0015, но **не подключена** к репортеру — только концептуально описана.

## Replay engine (`src/backtest/replay_engine.py`)

Основной модуль, 315 LoC. Реализует bar-by-bar симуляцию с явной гарантией look-ahead-free: сигнал фиксируется на `close(T)`, вход — по `open(T+1)` следующего бара. Для этого сигнал попадает в `pending_entry` и материализуется в `position` только на следующей итерации, когда `timestamp_open == ts` текущего бара.

Управление позицией — простой state machine: либо `position is None`, либо открыта одна позиция (BUY / SELL). Выход триггерится по пяти причинам: `SL` (цена коснулась `position["sl"]`), `TP` (цена коснулась `position["tp"]`), `SIGNAL_FLIP` (противоположный сигнал, если не `long_only`), `EOD` (последний бар датафрейма), `KILL_SWITCH` (drawdown превысил `max_drawdown_pct`). Уровни SL/TP вычисляются от ATR: `sl = entry ± sl_atr_mult * atr`, `tp = entry ± tp_atr_mult * atr`. Проскальзывание применяется к ценам входа и выхода (но не к уровням SL/TP в проверке), комиссия — как доля от notional.

Equity записывается как mark-to-market на каждом баре (не только по трейдам), что обеспечивает корректный расчёт drawdown. При срабатывании kill-switch текущая позиция принудительно закрывается по `close` текущего бара, и цикл прерывается.

### Public API

- `run_replay(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]`
  Возвращает `{"equity_df": pd.DataFrame, "trades_df": pd.DataFrame, "metrics": Dict[str, float]}`.
- `_compute_metrics(equity_df, trades_df, initial_balance) -> Dict[str, float]`
  Приватная — вычисляет полный набор KPI (см. ниже).

### KPI, вычисляемые `_compute_metrics`

`Total Return (%)`, `Max Drawdown (%)` (в % и USDT), `Sharpe Ratio` (аннуализирован ×√(24·365)), `Sortino Ratio`, `Win Rate (%)`, `Loss Rate (%)`, `Profit Factor`, `Gross Profit`, `Gross Loss`, `Net Profit`, `Total Trades`, `Expectancy` (в USDT), `Average Win`, `Average Loss`, `Total Commissions` (в USDT), `Average Holding Time (hours)`.

### Параметры из config

| Ключ | Путь | Default |
|------|------|---------|
| `initial_balance` | `trading.initial_balance` | 10000.0 |
| `commission_taker` | `trading.commission_taker` | 0.001 |
| `slippage` | `trading.slippage` | 0.0005 |
| `position_size_pct` | `trading.position_size_pct` | 10.0 |
| `max_drawdown_pct` | `trading.max_drawdown_pct` | 20.0 |
| `long_only` | `trading.long_only` | False |
| `sl_atr_mult` | `strategy.indicators.atr.sl_atr_mult` | 1.5 |
| `tp_atr_mult` | `strategy.indicators.atr.tp_atr_mult` | 3.0 |

## Vector backtest (`src/backtest/vector_backtest.py`)

73 LoC. Класс `VectorBacktester` — быстрая pandas/numpy-альтернатива для грубой проверки сигналов без bar-by-bar цикла. Принимает DataFrame с колонкой `signal` (1=long, -1=short, 0=flat), forward-fill'ит позицию, вычисляет логарифмические доходности стратегии со сдвигом на 1 бар (anti-look-ahead).

В отличие от `replay_engine`: нет SL/TP уровней, нет per-trade учёта qty, нет kill-switch. Возвращает три KPI: `Total Return (%)`, `Max Drawdown (%)`, `Sharpe Ratio` (аннуализируется ×√(365·24·60) — предполагает 1m данные; для 1h нужна коррекция). Используется как быстрый sanity-check перед полным replay.

### Public API

- `VectorBacktester(df, initial_capital=10000.0, maker_fee=0.001)`
- `run() -> dict` — возвращает `{"Total Return (%)": ..., "Max Drawdown (%)": ..., "Sharpe Ratio": ...}`

## Reporter (`src/backtest/reporter.py`)

107 LoC. Функция `write_artifacts(config, equity_df, trades_df, metrics)` записывает результаты `run_replay()` в директорию `output/` (конфигурируется через `config.output.directory`):

- `trade_log.csv` — все трейды с колонками `timestamp_open/close`, `direction`, цены, qty, fee, `net_pnl`, `exit_reason`, `holding_hours`.
- `equity_curve.csv` — mark-to-market баланс по каждому бару.
- `metrics_summary.json` — полный словарь KPI из `_compute_metrics`.
- `report.html` — интерактивный Plotly-отчёт с двумя панелями (equity curve + trade PnL bar chart). При отсутствии plotly — fallback на статичный HTML с таблицей метрик.

Выходные форматы управляются флагами `output.generate_csv/json/html` в конфиге. Слипейдж ADR 0010 (sqrt-формула) в репортере напрямую не применяется: slippage уже учтён в ценах входа/выхода внутри `replay_engine`.

## Indicators (`src/backtest/indicators.py`)

71 LoC. Функция `calculate_indicators(df, cfg) -> pd.DataFrame` — предобработка всего исторического DataFrame перед replay. Вычисляет EMA fast/slow (classical α=2/(n+1)), RSI (Wilder-style через ewm с alpha=1/n), ATR (Wilder-style через ewm) и сигнальную колонку.

Сигнал: `1` при EMA cross-up (fast пересекает slow снизу вверх) И RSI < порога `overbought` (default 68). Нет сигнала −1 (long-only по умолчанию в этом модуле). Параметры берутся из `strategy.indicators.ema/rsi/atr`.

**Важно:** этот модуль отдельный от `src/signalgen/indicators.py` (live-стек). Live-стек использует TA-Lib Wilder с коррекцией look-ahead (сигнал только на `close(T)`, не на T+1). Бэктест-индикаторы применяются batch к полному DataFrame — корректны для бэктеста, но не для инкрементального on_bar контракта live-стека.

## Data collector (`src/backtest/data_collector.py`)

94 LoC. Функция `load_market_data(config) -> pd.DataFrame` читает данные из файла:

- `source = "csv"` → читает CSV из `data.csv_path` (default `data/BTCUSDT_1h.csv`).
- `source = "parquet"` → читает Parquet из `data.parquet_path` (default `data/BTCUSDT_1h.parquet`); при ошибке — fallback на CSV.

Постобработка: нормализация имён колонок (lowercase + trim), приведение `time`→`timestamp` (pd.to_datetime), валидация обязательных колонок OHLCV (raise ValueError если нет), числовое приведение, сортировка по timestamp, фильтрация диапазона `data.start_date`/`end_date`.

Parquet-путь соответствует хранилищу OLAP по ADR 0003 (`data/` директория), но механизм записи в Parquet — вне этого модуля (рукописные файлы или внешний download). Нет интеграции с Bybit kline API — только локальные файлы.

Alias `load_data()` → `load_market_data()` для обратной совместимости со старой документацией.

## Deferred / stubs

- `src/backtest/replay.py` (8 LoC) — compatibility shim: `from src.backtest.replay_engine import run_replay; __all__ = ["run_replay"]`. Существует как placeholder для внешних вызовов, ссылающихся на модуль по старому имени. Реализации нет.

## Open questions (deferred S9+)

- **DSR (Deflated Sharpe Ratio)** — интеграция по Bailey–López de Prado. Нужен MC-харнесс + коррекция на skew/kurt/N конфигураций. Теоретическое описание: [[../decisions/0015-sign-flip-mc-permutations-n2000]]; концептуальный wiki: [[../../trading/concepts/deflated-sharpe-ratio]].
- **MC permutation harness** — sign-flip N=2000 per ADR 0015 концептуально задокументирован, но не подключён к репортеру. `reporter.write_artifacts()` не принимает MC p-value.
- **WFA (walk-forward analysis)** — train=2000/test=500/K=5/embargo=20 per ADR 0014 не реализован как run-loop. `replay_engine.run_replay()` — однопроходный, без fold-splitting.
- **Parquet write pipeline** — `data_collector` только читает; механизм загрузки и сохранения исторических klines в Parquet не существует в репозитории.
- **Аннуализация VectorBacktester** — `Sharpe × √(365·24·60)` предполагает 1m данные; при 1h данных формулу нужно исправить на `× √(365·24)`.

## Related

- [[indicators]] — live `src/signalgen/indicators.py` (TA-Lib Wilder ADX/RSI/ATR + classical EMA crossover)
- [[strategy]] — live strategy on_bar контракт
- [[../decisions/0014-walk-forward-train2000-test500]] — train=2000, test=500, K=5, embargo=20
- [[../decisions/0015-sign-flip-mc-permutations-n2000]] — sign-flip MC N=2000 как primary test
- [[../decisions/0010-sqrt-slippage-model]] — sqrt-формула slippage (учтена в replay_engine, не в репортере напрямую)
- [[../../trading/concepts/walk-forward-validation]] — концептуальное описание WFA
- [[../../trading/concepts/deflated-sharpe-ratio]] — DSR по Bailey–López de Prado
- [[../../trading/concepts/monte-carlo-permutations]] — MC sign-flip + block-bootstrap

## Sources

- `src/backtest/replay_engine.py` (315 LoC) — bar-by-bar simulation + KPI
- `src/backtest/vector_backtest.py` (73 LoC) — vectorized quick-check
- `src/backtest/reporter.py` (107 LoC) — artifact writer (CSV/JSON/HTML)
- `src/backtest/indicators.py` (71 LoC) — batch EMA/RSI/ATR + signal
- `src/backtest/data_collector.py` (94 LoC) — CSV/Parquet loader
- `src/backtest/replay.py` (8 LoC) — compatibility shim
- ADR 0010 (sqrt slippage), ADR 0014 (WFA), ADR 0015 (MC sign-flip)
