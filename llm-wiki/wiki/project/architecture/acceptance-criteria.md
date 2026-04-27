---
title: Acceptance Criteria (S1–S6, T1–T6)
type: architecture
tags: [acceptance-criteria, testing, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §10]
---

# Acceptance Criteria v0.1

**TL;DR:** 6 system-level критериев (инфраструктура работает) + 6 strategy-level (OOS only). Strategy-критерии — gating (не принять → не mainnet).

## System-level (6 — infrastructure works)

| # | Критерий | Порог | Метод измерения |
|---|----------|-------|-----------------|
| S1 | Uptime | ≥99.5% rolling 30d (excluding documented Binance downtime) | Heartbeat 1/s, Prometheus |
| S2 | WS reconnect time | p99 < 5s from disconnect to first new tick | WS client timestamps, histogram |
| S3 | P&L reconciliation | ≥99.99% (local vs `/account` + `/myTrades`) | Nightly diff; fail if >1 bp for >1 day |
| S4 | Dashboard update latency | p95 < 2s from fill event to UI | Grafana histogram |
| S5 | Config hot-reload | Non-critical params 0s downtime; critical require restart | SIGHUP reload, chaos test |
| S6 | Zero API key leaks | 0 secrets в git/logs/images | `gitleaks`, `trufflehog` в CI, IP whitelist + no-withdrawal permission |

## Strategy-level (6 — strategy works, OOS only)

| # | Критерий | Порог | Обоснование |
|---|----------|-------|-------------|
| T1 | Sharpe OOS (annualized net) | ≥1.0 | Реалистичный target; >2.0 suspicious; >3.0 almost certainly overfit (Hudson–Urquhart 2021) |
| T2 | Sortino OOS | ≥1.5 | Trend-following с positive skew должен показывать Sortino > Sharpe |
| T3 | MaxDD | <25% | Trend-following на BTC historically 15–30%; <10% suspicious |
| T4 | Win rate | ≥45% при RR≥1.5 OR ≥35% при RR≥2.0 | Trend-following typically 35–50%; >65% suspicious |
| T5 | Math expectation per-trade | >0 с t-stat >2.0 | Guards против random-noise edge; требует n≥100 OOS trades |
| T6 | OOS/IS Sharpe ratio | ≥0.7 | Primary overfit-detector; degradation >30% red flag |

## Supporting metrics (не gating)

- **Deflated Sharpe Ratio (DSR)** > 0 — учитывает multiple testing. См. [[../../trading/concepts/deflated-sharpe-ratio]].
- **Probability of Backtest Overfit (PBO)** < 0.5 — PBO > 0.5 означает, что IS-winner проигрывает случайному в OOS.
- **Calmar** > 0.5.

## Что НЕ acceptance criteria (и почему)

- Raw annual return — зависит от leverage, не отражает risk-adjusted edge.
- Profit factor один — коррелирует с Sharpe, не даёт независимой информации.
- Max consecutive losses — волатилен на малых n, легко overfit.

## Gating flow

```
1. Walk-Forward + K=5 CV на 5 лет BTC 1H¹
2. Compute OOS Sharpe, Sortino, MaxDD, win rate, t-stat, OOS/IS ratio
3. Compute DSR учитывая N конфигураций (N ≤ 45 по MinBTL)
4. Gate: все T1-T6 green AND DSR > 0² AND PBO < 0.5³
5. Если pass: promote to live (с Kelly Phase 1 — 1% fixed)
6. Live trading накапливает реальные trades → Kelly phase progression
```

**Footnotes (S13 PHASE 2 reconciliation):**

¹ **Data span — 5 лет = aspirational, floor 3.5y.** `migration-plan.md` S7 AC says "2y BTC 1H-данных" (retrospective minimum); this gating flow says "5 лет" (target). Reconciliation per S13 ADR 0028: target 5y, fallback к **max available Bybit Spot data, floor 3.5y** for K=5 fold statistical adequacy (ADR 0014: 12,600 bars min; 3.5y × 8760 = 30,660 bars). Если Bybit Spot earliest 1H BTCUSDT timestamp > 2022 → escalate к user. Per ADR 0016: NO Binance fallback (venue consistency).

² **DSR gate active S13+** per S13 PHASE 2 Q5 CONFIRM. N_trials tracking: each measurement attempt increments N_trials (CC1 binding infrastructure). N_trials > 1 requires sigma_sr (cross-fold Sharpe std) per Bailey eq. 12 (S10 implementation).

³ **PBO gate deferred S15+** — PBO requires MCS (Monte Carlo Strategy Selection) framework not implemented в v0.1 (~3 sprints scope expansion). S13 measurement uses **T1-T6 + DSR > 0 only** (PBO gate documented as deferred, not silently dropped).

## Revalidation cadence

- **Monthly walk-forward re-optimization** на последние 5 лет + свежие 1 месяц live data.
- **Regime shift monitor:** KS-test live returns distribution vs backtest; p<0.01 → revert к Kelly Phase 1.

## Sources

- Halls-Moore (2015) *Successful Algorithmic Trading* Ch. Performance Measurement.
- López de Prado (2018) *Advances in Financial ML* Ch.14.
- Bailey–López de Prado (2014) "The Deflated Sharpe Ratio" *JPM* 40(5):94–107.
- Hudson & Urquhart (2021) "Technical trading and cryptocurrencies" *Annals of OR* 297:191–220.

## Related

- [[../../trading/concepts/walk-forward-validation]]
- [[../../trading/concepts/deflated-sharpe-ratio]]
- [[../../trading/concepts/monte-carlo-permutations]]
- [[risk-register]]

---

## S34 Amendment (LOCKED ADR 0052 — pending operator acknowledgment for v0.7+ resumption)

Per S34 consilium consensus + ADR 0052 LOCKED:

| Threshold | v0.5 (original) | v0.7+ (amended LOCKED) |
|-----------|----------------|-----------------------|
| T5 n_trades raw floor | 100 | **50** |
| T5 n_eff threshold (NEW) | N/A | **≥ 50** (Kish 1965 mandatory) |
| MC p-value threshold | ≤ 0.10 | **≤ 0.05** (tightened) |
| T6 OOS/IS Sharpe ratio | ≥ 0.7 | ≥ 0.7 UNCHANGED |
| DSR | ≥ 0.95 | ≥ 0.95 UNCHANGED |
| acceptance_gate.sharpe_gate_passed | per-fold strict | UNCHANGED |

**LOCKED — no further modifications without new ADR + operator written acknowledgment.**

**Operator acknowledgment required (template per ADR 0052):**

> "Statistical evidence as of v0.6 DOES NOT support live deployment; this amendment reflects crypto-specific sample-size reality (Hudson & Urquhart 2021), not evidence of positive edge."

See [[../decisions/0052-sprint-34-acceptance-criteria-amendment]] для full rationale + 10-item pre-commit list + operator acknowledgment template.

**S34 T1 pre-check outcome:** S33 data на amended gates STILL FAILS 4/5 (n_eff 26<<50, MC 0.52>>0.05, T6 -2.84<<0.7, DSR 0.919<0.95). Amendment alone insufficient — future resumption requires NEW measurement sprint.
