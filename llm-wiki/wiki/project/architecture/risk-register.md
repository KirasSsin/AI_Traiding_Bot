---
title: Risk Register (22 риска, 4 категории)
type: architecture
tags: [risk, iso31000, nist, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §13]
---

# Risk Register

**TL;DR:** 22 риска в 4 категориях (технические / рыночные / операционные / статистические). Framework: ISO 31000:2018 + NIST SP 800-30 Rev.1 (Risk = Likelihood × Impact с H/M/L scoring).

## Технические (6)

| # | Риск | P | Impact | Митигация |
|---|------|---|--------|-----------|
| T1 | WS dropout | H | $50–500 | dual WS (v0.2), WS watchdog 30s, exponential backoff reconnect |
| T2 | Rate-limit | M | $0–2000 | token bucket per bucket, read live limits from exchangeInfo |
| T3 | Server crash | L | $500–5000 | systemd watchdog `Restart=always`, SQLite WAL + nightly offsite dump |
| T4 | Clock drift | L | rejection | chrony ≥3 stratum-1 peers, 60s resync, HALT after 3 fails |
| T5 | DB corruption | L | $1K–10K | WAL mode, VACUUM INTO nightly, offsite backup |
| T6 | Stale data | M | $100–2000 | data-quality pipeline pre-indicator, 2·Δ threshold → halt |

## Рыночные (5)

| # | Риск | P | Impact | Митигация |
|---|------|---|--------|-----------|
| M1 | Flash crash | L | $1.5K–7.5K | flash detector `max(8%, 3·ATR)` → HALT+flatten+cancel-all |
| M2 | Exchange maintenance | H | $0–5K (depending on holding) | calendar-aware flatten pre-maintenance, no entries last hour |
| M3 | Regime change | H | $2K–8K gradual | monthly walk-forward re-optim, KS-test live-vs-backtest |
| M4 | Liquidity shock | L | $200–2K slippage | volume-adaptive sizing `limit ≤ k·rolling_median_volume` |
| M5 | Symbol delisting + USDT depeg | L | total-position | USDC fallback plan, stablecoin monitor |

## Операционные (5)

| # | Риск | P | Impact | Митигация |
|---|------|---|--------|-----------|
| O1 | Wrong API key prod/testnet | M | **catastrophic** | startup self-test: $0.01 place+cancel на known endpoint |
| O2 | Insufficient balance | M | $50–500 | pre-trade balance check + 10% cash floor |
| O3 | Wrong pair in config | L | **catastrophic** | config-as-code + CI validation + symbol whitelist |
| O4 | Config drift prod/test | M | $500–5K | hashes diff per env, immutable config prod, 4-eyes deploy |
| O5 | Unpatched OS | M | **catastrophic** (key exfiltration) | minimal Docker image + Trivy daily + WireGuard VPN + HW 2FA + IP whitelist + no-withdrawal + withdrawal whitelist |

## Статистические (5)

| # | Риск | P | Impact | Митигация |
|---|------|---|--------|-----------|
| S1 | Overfitting | H | $1K–10K gradual bleed | DSR (Bailey–López de Prado 2014), OOS/IS ≥0.7 gate, CPCV (v0.2+), parameter count ≤ log₂(n_trades), pre-registration of hypothesis |
| S2 | Look-ahead bias | M | silent | future-bar poison test в CI, `shift(1)` enforcement, property tests |
| S3 | Data snooping | H | inflated edge → oversize Kelly | Bonferroni/Holm correction, DSR |
| S4 | Survivorship bias | L | для BTC-only | BTC-only (survivorship non-issue) |
| S5 | Regime change invalidating backtest | H | $2K–15K | KS test / CUSUM on live-vs-backtest distribution, revert to Phase 1 if p<0.01 |

## Summary по категориям

- **High-likelihood risks:** T1 (WS dropout), M2 (exchange maintenance), M3 (regime change), S1 (overfitting), S3 (data snooping), S5 (regime change invalidating backtest).
- **Catastrophic potential:** O1 (wrong API key), O3 (wrong pair), O5 (unpatched OS).
- **Silent impact (hard to detect):** S2 (look-ahead bias), S3 (data snooping).

## Review cadence

- **Weekly:** incident log review, update likelihood/impact based on near-misses.
- **Monthly:** full risk register review, new risks added, mitigations audited.
- **Quarterly:** table-top exercise (simulated incident) для catastrophic risks.

## Framework

- **ISO 31000:2018** — risk management process: identify → analyse → evaluate → treat → monitor.
- **NIST SP 800-30 Rev.1** — H/M/L scoring для likelihood и impact.

## Sources

- Docs/MVP + ALL PROJECT/MVP.md §13.
- ISO 31000:2018 *Risk Management — Guidelines*.
- NIST SP 800-30 Rev.1 *Guide for Conducting Risk Assessments*.

## Related

- [[edge-cases]] — operational responses.
- [[acceptance-criteria]] — gating на overfit risks.
- [[../../trading/concepts/deflated-sharpe-ratio]]
