# Metrics Engine HFT Core — Design Doc (2026-03-14)

## Architecture & Data Flow

**Goal:** Build an in-process, gRPC-ready MetricsEngine that delivers 15 real-time metrics with sub-millisecond latency, enabling Phase 3 HFT-grade decisioning while keeping migration to gRPC/C++ a one-line DI swap later.

**Scope:** Bybit V5 **Linear USDT Perp** only. Top-50 orderbook depth. Trade stream for VWAP/Kyle’s Lambda. Tickers stream for OI/Funding. MTF stack = 1m + 5m + 15m.

### Components

1. **BybitDataConsumer (extended)**
   - Subscriptions:
     - `orderbook.50.<symbol>` (L2 depth)
     - `publicTrade.<symbol>` (trades)
     - `tickers.<symbol>` (OI + funding + price stats)
     - `kline.<interval>.<symbol>` for 1m/5m/15m
   - Normalizes to typed internal events:
     - `OrderBookDelta`
     - `TradeTick`
     - `MarketStats` (OI, funding)
     - `Kline`

2. **OrderBook Manager**
   - Maintains **Top-50** book using sorted arrays or ordered structures for O(1) access to top levels and efficient aggregates.
   - Produces:
     - best bid/ask, mid, spread
     - weighted depth aggregates

3. **Event Bus + Fast-Path**
   - Primary path: `asyncio.Queue` for all events.
   - **Fast-Path:** if volume spike or OBI delta spike is detected, bypass queue and call MetricsEngine → Strategy/Risk → Executor in the same coroutine to minimize latency spikes.

4. **MetricsEngine (in-process, gRPC-ready)**
   - Consumes event stream, maintains sliding windows via `deque`/ring buffers.
   - Produces `MetricsSnapshot` (full 15 metrics + health flags) every 1s.
   - Exposes an interface compatible with future gRPC streaming (method signatures align to `market_data.proto`).

5. **Controller Integration**
   - `TradingController` passes `MetricsSnapshot` to `AdvancedStrategy` and `RiskManager`.
   - `data.json` extended with `metrics` block for UI.

6. **Latency Gate (Global)**
   - Measure `tick_received_ts` → `execute_signal_ts`.
   - If **> 100µs**, block order and log.

---

## Metrics Dictionary (15 Metrics)

All metrics calculated in real-time. Missing/invalid data yields `None` and triggers safety gate if critical.

1. **Order Book Imbalance (OBI)**
   - Weighted OBI with exponential decay: `w_i = exp(-0.5 * i)` for Top-50.
   - Output: `OBI_micro` (Top-5) and `OBI_macro` (Top-50).

2. **Kyle’s Lambda**
   - `λ = |Δmid| / volume`.
   - Computed on **volume bucket 5 BTC** (not time-bars).

3. **Hurst Exponent (H)**
   - Computed on last **120 closed 1m** prices (`max_lag=20`).

4. **Tick-to-Trade Latency**
   - `latency_us = t_execute - t_tick`.
   - Global block when `latency_us > 100`.

5. **HMM Regime Score**
   - HMM features: returns, ATR, OBI_micro, OBI_macro.
   - Output: 0 (Range), 1 (Trend), 2 (Volatile).

6. **Cointegration Z-Score (ETH/BTC)**
   - `Spread = P_ETH - β * P_BTC`.
   - `VWAP_Spread = VWAP_ETH - β * VWAP_BTC`.
   - `Deviation = Spread - VWAP_Spread`.
   - Z-score on rolling **24h** window.
   - `β` computed by OLS on rolling 24h, **updated hourly** and **locked during open trade**.

7. **Real Volatility (ATR)**
   - ATR on 1m, plus 5m/15m for MTF alignment.

8. **Open Interest Delta**
   - ΔOI over rolling **24h** from WS `tickers` stream.

9. **Funding Rate Cumulative**
   - Rolling 24h cumulative funding from WS `tickers`.

10. **Expected Shortfall (CVaR)**
   - Monte Carlo **Jump Diffusion** (5000–10000 sims).
   - Updated every 60s (not every tick).

11. **Fractional Kelly**
   - Calculated from win_rate / win_loss_ratio over **last 100 trades**.
   - Bounded by configured risk caps.

12. **MTF Alignment Score**
   - Uses 1m/5m/15m indicators.
   - **Recomputed intra‑bar** when OBI delta spike OR trade size spike occurs.

13. **VWAP Deviation**
   - `VWAP_1h` from trade stream.
   - `vwap_dev = (price - vwap_1h) / vwap_1h`.
   - Anchored VWAP reset triggers:
     - Volume spike > **3x** 24h avg **AND**
     - Price shock > **0.5%**
     - **Optional bonus:** OI drop flag for weighting/alerting

14. **Risk of Ruin**
   - Hybrid: config baseline + adjustment from last **100 trades**.

15. **Wavelet Denoising**
   - **Symlet‑6**, level **4**, soft threshold (pywt).
   - Produces “clean price” for select indicators.

---

## Safety & Execution Gates

1. **Latency Gate**
   - Hard block if `tick-to-trade latency > 100µs` (global gate).

2. **Signal Safety**
   - If critical metrics missing (OBI, Latency, OI) → strategy blocks trading.

3. **Stat-Arb Guardrails (ETH/BTC)**
   - Entry: `|Z| >= 2.5`
   - Exit: `|Z| <= 0.5`
   - Soft stop: `|Z| >= 4.5` with **reversal-based** exit
     - Exit when `Z` retraces by **0.2σ** from peak
   - Hard stop: `|Z| >= 5.0` immediate close
   - Cooldown: **6h** after hard stop
   - Post-cooldown: require ADF/Engle-Granger `p < 0.05` to resume

4. **ML Dependency Gate**
   - XGBoost is **fail-fast** if missing `libomp`.

---

## Testing Strategy

1. **Unit Tests**
   - OBI micro/macro correctness on synthetic books.
   - Kyle’s Lambda on synthetic volume buckets.
   - Hurst ≈ 0.5 on random walk.
   - ATR manual sanity checks.
   - VWAP deviation accuracy from fixed trades.
   - Wavelet denoise reduces variance.

2. **Integration Tests**
   - Simulated stream combining orderbook, trades, tickers.
   - Validate MetricsSnapshot fields update on schedule.
   - Verify latency gate blocks when > 100µs.

3. **Performance / Latency**
   - `test_metrics_latency.py`: measure tick → metrics → gating.
   - Target < 100µs typical, < 1ms under load.
   - **GC control:** disable GC during hot path in latency tests to avoid spikes.

4. **Failure Safety**
   - Missing data returns `None` and logs warning.
   - Critical-metric absence blocks trading rather than degrade silently.

---

## Rejected Alternatives

1. **Time-bars for Kyle’s Lambda** → Rejected. Volume buckets reduce noise and improve signal stability.
2. **Z-score entry at |Z| >= 2.0** → Rejected. Too many false entries in fat-tail crypto regimes.
3. **Anchored VWAP reset on volume OR price** → Rejected. AND condition avoids spoof/wash and thin-book spikes.
4. **REST polling for OI/Funding** → Rejected. WS is required for real-time reaction.
5. **Queue-only event bus** → Rejected. Fast-Path is required to avoid latency spikes.

---

## Open Items (for implementation)

- Confirm Bybit WS topic strings and payload shapes for orderbook/trades/tickers in current `pybit` version.
- Ensure orderbook snapshot+delta reconciliation is stable under reconnects.
- Decide whether to persist metrics history to disk for offline validation.
