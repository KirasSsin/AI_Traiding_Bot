# research/donchian-may8 — HONEST CLOSE

**Date:** 2026-05-08
**Branch:** autoresearch/donchian-may8
**Verdict:** PARADIGM DEAD — S35 Donchian breakout long-only autoresearch class CLOSED
**Authority:** trader-expert ROUND 1 verdict (REVISE → option (f)) + maintainer concurrence + 2-line pre-check empirical confirmation

## Iterations summary

| Iter | Variant | Best train | Held-out | Verdict |
|------|---------|------------|----------|---------|
| 1 | Donchian raw S35 hyperparameter tuning (4D) | Sharpe +1.27 (L=11 E=5 P=13 ATR×0.61) | Sharpe **-3.23** | FAIL — overfit |
| 2 | Donchian + EMA trend filter (5D) | Sharpe +2.50 (L=15 E=6 P=7 ATR×2.5 EMA=0) | Sharpe **-2.05**, PnL -16% | FAIL — overfit; EMA filter empirically falsified |
| 3 | Vol regime gate (pre-check ONLY) | n/a | held-out projected n=12 < halt 20 | ABORTED before search — paradigm-dead confirmed |

## Statistical evidence (per Bailey & López de Prado 2014)

1. **Sign-flip overfit pattern:** train Sharpe positive → held-out Sharpe negative (2/2 iterations)
2. **N_trades structural ceiling:** baseline held-out n=29 < T5=50 ADR 0052 gate; ANY filter further reduces (vol filter projected 12)
3. **N_trials budget depleted:** ADR 0054 pre-registered N=5; effective N after iter 1+2 ≈ 73 (31+37+5 base)
4. **DSR penalty growing:** with each iteration, sigma_SR pooled grows → DSR ≥ 0.95 gate further from reach
5. **ADR 0054 pre-commit #8 protocol:** "FAIL conjoint → α direction CLOSED" — both iter 1 + iter 2 = FAIL conjoint

## Project pattern: 9th honest close

| # | Sprint/Iter | Strategy | Outcome |
|---|-------------|----------|---------|
| 1 | S14 | EMA crossover | FAIL |
| 2 | S16 | Mean-reversion strict | FAIL |
| 3 | S18 | Mean-reversion relaxed | FAIL |
| 4 | S21 | No improvement | FAIL |
| 5 | S22 | MR 4H partial PASS | FAIL conjoint |
| 6 | S23 | MR T5 unreachable | FAIL |
| 7 | S34 | Delta hindsight | FAIL |
| 8 | iter 1 | Donchian raw | FAIL |
| 9 | **iter 2** | **Donchian + EMA filter** | **FAIL** |

## Forward path (NOT in autoresearch scope)

Per trader-expert + SPRINT_STATE:

- **δ TESTNET (S36-S38 shipped):** forward profit path; operator activation in progress
- **Wait for δ data accumulation:** n=10 milestone triggers 12mo MAINNET-promotion ADR draft
- **v0.8+ research direction (operator decision):** funding-rate arb, on-chain momentum, volume breakout VWAP-anchored, ML/XGBoost — все require infrastructure/data outside research/ scope, formal kit cycle mandatory

## Files preserved

- `research/backtest_v2.py` — vectorized Donchian + EMA filter + ATR stop (reusable for future paradigms)
- `research/search_v2.py` — 5-dim search loop (reference template для future research toys)
- `research/prepare.py` — 80/20 train/held-out split (DO NOT MODIFY)
- `research/results.tsv` — full audit trail (35+ trial rows + 5 verdict rows)
- `research/run_v2.log` — iter 2 full search trace

## Operator escalation triggered (per autoresearch-iterate skill Step 3c-4)

**ESC-1:** Operator stated "wants iteration, not stop." Conflicts с paradigm-dead threshold (statistical-evidence standard MET) AND ADR 0054 pre-commit #8 protocol. Choose:
- (i) Accept honest close + redirect к δ TESTNET monitoring (recommended)
- (ii) Override protocol для one more iter — only permitted form = pre-check (already executed, falsified)

**ESC-2:** Forward strategy class for v0.8+ research direction. Options outside current search space:
- Funding-rate arbitrage (perps vs spot)
- On-chain momentum (different data infra)
- Volume breakout с VWAP anchor
- ML-driven (XGBoost) — still needs n≥500 train trades, not achievable single-symbol BTC 4H
Product-level decision — operator input required.

## Verdict authority

Trader-expert ROUND 1 returned REVISE on (a), recommended (f). Maintainer concurred (no ROUND 2 disagreement). 2-line pre-check (held-out projected n=12) empirically confirmed falsification. Per binding protocol: **autoresearch S35 line CLOSED**.
