---
title: Current State — инвентаризация существующего кода
type: architecture
tags: [current-state, inventory, baseline]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [src/, Docs/current_bot/README_RU.md, Docs/current_bot/IMPLEMENTATION_NOTES.md]
---

# Current State (на 2026-04-19)

**TL;DR:** Существующий код — **Phase 1 MVP на Bybit** (perpetual futures, linear, 1m bars, EMA+RSI+ATR). **НЕ** Binance Spot 1H. Математический стек (Hurst, Kelly, CVaR, HMM) заложен, но XGBPredictor и HMM не задействованы в live-сигнале. Нет TA-Lib, pydantic, SQLite/Parquet, DDD-структурирования.

## Структура `src/`

| Модуль | Файлы | Назначение |
|--------|-------|-----------|
| `core/` | `models.py`, `math_engine.py` | Dataclass-модели (Kline, Signal, Order) + базовая математика (Hurst, ADF, Kelly, CVaR). |
| `data/` | `consumer.py` | `BybitDataConsumer` — интеграция с pybit (WS + REST fallback), буфер свечей в памяти, REST seed. |
| `strategy/` | `strategy.py`, `hmm_regime.py`, `order_flow.py` | `AdvancedStrategy` (EMA12/26 + RSI + ATR), HMM regime-detector (скелет), OrderFlowAnalyzer (OBI, Kyle's Lambda). |
| `risk/` | `risk_manager.py` | `RiskManager` с kill-switch (5% DD), fractional Kelly (0.5-Kelly), fixed fractional risk (1%/trade), CVaR tracking. |
| `execution/` | `executor.py` | `BybitExecutor` — market orders, normalize qty/step, testnet/demo/live modes, mock при `live_trading=False`. |
| `gateway/` | `market_data_pb2.py`, `..._grpc.py` | gRPC stubs (заготовка для микросервисной архитектуры, не интегрирована). |
| `backtest/` | `vector_backtest.py` | `VectorBacktester` — pandas-based, KPI (Return, MaxDD, Sharpe). |
| `ml/` | `models.py` | `XGBPredictor` (binary classification, **не используется** в live). |
| `controller.py` | — | `TradingController` — оркестратор, asyncio event loop, sync с Bybit executions, export → `web/data.json`. |
| `main.py` (top-level) | — | Entry point: `asyncio.run(controller.start())` + HTTP сервер для `web/dashboard.html`. |

## Стек реально используется

```
Python (version ?)
├── asyncio                    ✓ (везде async/await)
├── pandas                     ✓ (буфер свечей, EMA через .ewm())
├── numpy                      ✓ (math engine)
├── aiohttp                    ✓ (через pybit)
├── pybit (локальная, v5)      ✓ (Bybit Unified Trading)
├── scipy                      ✓ (linregress, norm, t — в math_engine)
├── statsmodels                ✓ (adfuller — ADF test)
├── hmmlearn                   ✓ (скелет GaussianHMM, без fit)
├── xgboost                    ✓ (import, не используется)
└── pytest                     ✓ (4 теста в test_math.py)

НЕ используется:
├── TA-Lib                     ✗
├── pydantic (v2)              ✗ (используются @dataclass)
├── uvloop                     ✗
├── SQLAlchemy / SQLite        ✗ (всё в памяти)
├── Parquet                    ✗
├── structlog                  ✗
└── grpcio (runtime)           ✗ (только stubs)
```

## Биржа и символ

- **Venue:** Bybit Linear (perpetual futures, category `linear`).
- **Symbol:** BTCUSDT.
- **Timeframe:** **1m** (в `main.py` interval="1"; MVP-спека требует 1H).
- **Modes:** `testnet=True` / `demo=True` / `live_trading=False` (по умолчанию mock).
- **Keys:** жёстко вписаны в `main.py` (тестовые).
- **Data source:** pybit WebSocket kline + REST fallback (polling 1-2s).

## Стратегия (AdvancedStrategy)

- EMA12, EMA26 (через pandas `.ewm()` — classical EMA).
- RSI14 (через pandas, Wilder?).
- ATR14 (через pandas).
- Hurst exponent — вычисляется, в сигнале **не участвует** (только логирование).
- XGBPredictor, HMM — скелеты, не используются.

**Сигнал:** `fast_ema > slow_ema` → LONG, наоборот → SHORT (futures), если RSI не в крайности. ADX **не реализован**.

## Risk management

- **Kill-switch:** daily DD > 5% → блокировка.
- **Fixed fractional:** 1% от капитала на трейд.
- **Fractional Kelly:** 0.5-Kelly при n ≥ 10 сделок.
- **CVaR:** история последних 100 трейдов.
- **Нет** многоуровневых circuit breakers (L1/L2/L3/flash).
- **Нет** Kelly 4 фаз.

## Execution

- MARKET orders на Bybit linear.
- Normalization: qty → qtyStep, minOrderQty check через `get_instruments_info`.
- Mock-режим при `live_trading=False` (безопасность MVP).
- Sync executions каждую минуту через `get_executions`.
- **Нет:** OCO, limit orders, trailing stop, partial-fill handling.

## Data

- **REST seed:** 1000 свечей при старте (прогрев индикаторов).
- **WS:** kline stream с pybit.
- **Fallback:** REST polling при WS down.
- **Хранение:** **в памяти** (Python list до 1000 Kline objects).
- **Нет:** SQLite, Parquet, persistent storage.

## Backtest

- `VectorBacktester` — векторизованный, требует pre-populated DataFrame с `signal` column.
- KPI: Return %, MaxDD %, Sharpe (normalized на 365·24·60 для 1m).
- **Нет:** walk-forward, K-fold CV, Monte Carlo permutations, DSR.

## ML (вне MVP v0.1)

- `XGBPredictor` — скелет, 100 trees, depth 5, lr 0.05 — не используется в live.
- HMM — 3-компонент GaussianHMM, скелет без fit — не используется.

## Tests

- `tests/test_math.py` — 4 теста (hurst_random_walk, hurst_mean_reverting, cvar, fractional_kelly).
- **Нет:** unit tests для strategy, executor, risk_manager, data consumer.
- **Нет:** integration tests, property tests, lookahead detector.

## Controller & main

- Event loop: `asyncio.run(controller.start())`.
- Flow: new kline → `on_new_kline` → `strategy.on_kline()` → `risk_manager.evaluate()` → `executor.execute_signal()`.
- State export: каждую секунду → `web/data.json`.
- Sync trades: каждую минуту → `get_executions` → merge with local.
- Startup test: опциональная покупка+продажа на 100 USDT (проверка live-ключей).

## Документация в `Docs/current_bot/`

| Файл | Содержание |
|------|-----------|
| `README_RU.md` | Инструкция запуска на Bybit Testnet (6 шагов). |
| `IMPLEMENTATION_NOTES.md` | Реализованные фичи + ограничения MVP. |
| `Specification-Trading-Bot.md` | Фундаментальная спека (SMA/EMA/RSI/MACD/BB/ATR, GBM, HMM, order-flow, ML). |
| `Specification-Logic.md` | Расширенная математическая спека (Hurst, FFT, GBM+Jumps, OU, ADF, GARCH, microstructure) — **Phase 2/3**. |

## Что НЕ в scope v0.1 (согласно MVP-спеке)

Текущий код содержит много "лишнего" для MVP v0.1:

- **ML (XGBoost, HMM)** → вне scope v0.1 (MVP спека явно Python + TA-Lib без ML).
- **Order-flow (OBI, Kyle's Lambda)** → L2-стратегия, v0.3+.
- **gRPC gateway** → микросервис, v0.3+.
- **Hurst / ADF / FFT** → sophisticated regime detection, v0.2+.

Эти модули нужно либо **заморозить** (move to `legacy/` branch), либо **удалить** при миграции на MVP.

## Related

- [[overview]] — MVP v0.1 target.
- [[gap-analysis]] — разница current vs MVP.
- [[migration-plan]] — план перехода (создаётся на Этапе 2).
