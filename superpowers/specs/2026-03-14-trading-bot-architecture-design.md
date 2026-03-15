# Trading Bot Architecture Specification & Roadmap

## Overview

A modular, scalable algorithmic trading platform initially targeting cryptocurrency markets (Binance). The system is designed to evolve from a robust Mid-Frequency Trading (MFT) baseline to High-Frequency Trading (HFT) and complex statistical arbitrage, utilizing a firm foundational architecture (Python, asyncio, pandas/numpy) focused on infrastructure reliability and risk-first execution.

---

## Phase 1: The Backbone & Variant A (Mid-Frequency MVP)

**Goal:** Establish a "bulletproof" data pipeline, risk management gate, and execution engine. Deploy a simple, reliable strategy to validate the infrastructure over time without exposing capital to high-frequency micro-bugs.

### 1. Architecture Components
The system is divided into logical, decoupled units communicating asynchronously.

*   **Data Consumer:**
    *   **Role:** Subscribes to market data.
    *   **Implementation:** Connects to Binance via WebSockets (for live quotes/order book updates) and REST (for historical klines/candles).
    *   **Output:** Standardized OHLCV data structures/events.
*   **Controller (Orchestrator):**
    *   **Role:** The main `asyncio` event loop.
    *   **Implementation:** Routes data from the Consumer to the Strategy. If a signal is generated, routes it to the Risk Manager, then to the Executor.
*   **Strategy (Variant A - MFT):**
    *   **Role:** Generates Buy/Sell signals based on technical indicators.
    *   **Implementation:** Python + `pandas-ta`. Uses Moving Average Crossovers (e.g., EMA 12/26) or RSI thresholds on 5m/15m/1H timeframes.
    *   **Output:** `Signal(pair, direction, entry_price, expected_sl, expected_tp)`.
*   **Risk Manager (The Gatekeeper):**
    *   **Role:** Enforces survival. Operates on a *Risk-First* principle.
    *   **Implementation:** Intercepts every signal. Calculates position size (fractional, e.g., max 2% of capital). Checks Max Daily Drawdown (MDD) and consecutive losses. Acts as a strict Kill-Switch.
*   **Executor:**
    *   **Role:** Interacts with the exchange.
    *   **Implementation:** Highly robust `aiohttp` + websockets listener for Binance User Data Stream. Handles listenKey keepalives, exponential backoff on disconnects, and REST API for order placement.
*   **Logger/Monitor:**
    *   **Role:** Records everything for later analysis.
    *   **Implementation:** Logs signals, executions, errors, and current state to a local database (SQLite/PostgreSQL) or flat files.
*   **Vector Backtester:**
    *   **Role:** Validates strategies before live deployment.
    *   **Implementation:** A fast, loop-free (`.iterrows`-free) engine using `numpy`/`pandas` vector operations to simulate PnL, Drawdown, and Win-Rate over historical data.

### 2. Success Criteria for Phase 1
*   The Executor maintains a WebSocket connection to Binance for 72+ hours without crashing, successfully handling reconnects.
*   The Risk Manager correctly blocks orders that exceed defined risk limits.
*   The Vector Backtester processes 1 year of 1m candle data in under 5 seconds.
*   The Bot runs autonomously on a paper-trading or minimal-live account, executing the Variant A strategy.

---

## Phase 2: Variant C (Statistical Arbitrage & Cointegration)

**Goal:** Shift from directional guessing (Variant A) to market-neutral strategies, leveraging higher mathematics to profit from mean reversion.

### 1. Core Additions
*   **Math Engine (Python/SciPy):**
    *   Implement Augmented Dickey-Fuller (ADF) tests for stationarity.
    *   Implement Engle-Granger and Johansen tests for cointegration between asset pairs (e.g., BTC/USDT vs. ETH/USDT, or Spot vs. Perp Futures).
*   **Upgraded Strategy Module:**
    *   Calculate Z-scores of the spread between cointegrated assets in real-time.
    *   Generate signals to long the underperformer and short the overperformer when the Z-score exceeds a threshold (e.g., \> 2.0).
*   **Advanced Risk Manager:**
    *   Must handle simultaneous, multi-leg order execution risk.
    *   Incorporate portfolio-level VaR (Value at Risk) or CVaR.

---

## Phase 3: Variant B (High-Frequency / Order Flow & Machine Learning)

**Goal:** Compete at the microstructural level. Predict the next tick based on order book dynamics and latency optimization.

### 1. Core Additions
*   **Microstructure Features:**
    *   Calculate Order Book Imbalance (OBI) mathematically from Level 2 data in real-time.
    *   Calculate Kyle's Lambda (market impact) and track trade tape (Time & Sales) for aggressive buying/selling pressure.
*   **Performance Optimization (Crucial):**
    *   Python's GIL and standard `asyncio` may become bottlenecks for sub-100ms reactions.
    *   *Implementation Shift:* Rewrite the Data Consumer and Execution hot-paths. Options include compiling critical Python with `Numba`/`Cython`, or rewriting the Gateway in Rust/C++ and communicating via gRPC (Protocol Buffers).
*   **Machine Learning / AI Module:**
    *   Introduce Hidden Markov Models (HMM) for market regime detection.
    *   Use Online ML (e.g., River) or batch learners (XGBoost) trained on order book snapshots to predict short-term directional probabilities.
*   **Trainer Module:**
    *   Automated pipeline to evaluate model performance (last 30 days) and push updated weights/configs using a Canary deployment approach.

## Summary Checklist for Immediate Action (MVP Start)
1.  Initialize repository and modular structure (`data_consumer.py`, `executor.py`, etc.).
2.  Write the `VectorBacktester` class.
3.  Write the robust `BinanceExecutor` with WS keepalive.
4.  Write the `RiskManager` constraints.
5.  Tie together with `controller.py` and a basic EMA placeholder strategy.
