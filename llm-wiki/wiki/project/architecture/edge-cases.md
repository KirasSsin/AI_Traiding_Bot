---
title: Edge Case Catalog (24)
type: architecture
tags: [edge-cases, robustness, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §9]
---

# Edge Case Catalog

**TL;DR:** 24 edge-cases с чёткими detection и response. Ни один не должен приводить к undefined behavior.

## Таблица

| # | Edge case | Обнаружение | Действие |
|---|-----------|-------------|----------|
| 1 | Missing bar (gap) | Δt между барами > period | Синтетический NaN-бар с `data_quality=GAP`, **без forward-fill OHLC**; skip signal generation |
| 2 | Consecutive missing >3 bars | Счётчик GAP-bars | `HALT_DATA_QUALITY`; требовать 3 valid bars после resume |
| 3 | volume=0 bar | `v==0` | Accept (возможно на illiquid pair); volume-filter отвергнет если нужно |
| 4 | Duplicate timestamp | Same `openTime` дважды | Deduplicate, keep last (check `isClosed` flag) |
| 5 | Negative volume / price≤0 / OHLC inconsistent | Sanity check | Reject как corruption; re-fetch через REST; persistent → HALT |
| 6 | Stale bar (>1.5·Δ old) | `now − last_bar > 1.5·period` | Halt decisioning; listening continue |
| 7 | Out-of-order bar | `ts_new < ts_prev` | Reject, log, WS/REST sync check |
| 8 | WS dropout | No msg for 30s / heartbeat miss | Exponential backoff reconnect; dual WS optional (v0.2) |
| 9 | Clock drift >1s | chrony offset monitor | CLOCK_DRIFT → resync → retry; 3× fail → HALT |
| 10 | Rate limit | retCode 10006 или HTTP 429 + `Retry-After` header | Honor `Retry-After`; exponential backoff на 10006; `RateLimitHit` event |
| 11 | IP ban / service unavailable | retCode 10016 | HALT `EXCHANGE_MAINTENANCE`; retry после resume |
| 12 | Partial fill entry timeout | >T_fill=60s в PARTIAL_FILL | Cancel residual, adopt executed qty (check min filters) |
| 13 | Partial fill OCO leg | listStatus `PARTIALLY_FILLED` на leg | Немедленно re-issue защитный ордер на residual qty |
| 14 | Duplicate signal на том же баре | Signal registry по `bar_ref.closeTime` | Reject `REJECT_DUPLICATE_SIGNAL` |
| 15 | Insufficient balance | retCode 110007 | Reduce size до max feasible или reject `INSUFFICIENT_BALANCE` |
| 16 | Filter violation | retCode 170131/170140/170213 | Pre-submit local filter validator (BybitFilters); round qty до `basePrecision`, price до `tickSize`, ensure `qty·price ≥ minOrderAmt`; если невозможно → reject `FILTER_VIOLATION` |
| 17 | HTTP 5xx / network / unknown | HTTP 5xx, timeout, pybit exceptions | Query `GET /v5/order/realtime?orderId=X`; адоптить state; НЕ ретраить с новым orderLinkId |
| 18 | Server crash mid-fill | systemd restart с WAL SQLite | Reconcile при boot: `/openOrders` + `/account` + `/myTrades` from last tradeId |
| 19 | Config drift prod/test | Config hash on boot | CI-diff на PR; immutable config в prod; 4-eyes deploy |
| 20 | Wrong API key (prod/testnet) | Startup self-test: place+cancel $0.01 order на известном endpoint | Kill-switch при mismatch |
| 21 | Flash crash >10% в 1H | `\|Δprice\| > max(8%, 3·ATR)` на close | Immediate HALT, cancel-all, flatten |
| 22 | Listen-key expiry (60min) | Timer + WS-error | Refresh каждые 30min через PUT `/api/v3/userDataStream` |
| 23 | Exchange maintenance | Binance status RSS + `503` codes | Flatten positions pre-maintenance; no entries в последний час |
| 24 | USDT depeg (|1−price|>1%) | Stablecoin monitor | Flatten USDT exposure, alert |

## Принципы response

1. **Reject > Retry > Halt.** Сначала пытаемся reject (локальное решение без exchange). Потом retry (при ретраибельной ошибке). Halt — последний резерв.
2. **Consistency > Availability.** При расхождении local ≠ exchange предпочитаем HALT, чем trade с потенциально неверным state.
3. **Mandatory human review** после HALT L2/L3 — reconciliation checklist обязателен.
4. **Idempotency everywhere.** Retry с тем же `clientOrderId` не создаёт duplicate order (Binance enforced).

## Key references

- Binance API docs: [Error codes](https://binance-docs.github.io/apidocs/spot/en/#error-codes).
- Binance API docs: [Rate limits](https://binance-docs.github.io/apidocs/spot/en/#limits).
- Kirilenko–Kyle–Samadi–Tuzun (2017) "The Flash Crash" *JF* 72(3):967–998 — automatic halt rationale.

## Related

- [[state-machine]] — как edge-cases триггерят transitions.
- [[risk-register]] — качественная оценка impact/likelihood.
- [[../../trading/concepts/circuit-breakers]] — drawdown-based halts.
