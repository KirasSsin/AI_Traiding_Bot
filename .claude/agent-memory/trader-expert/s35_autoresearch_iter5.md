---
name: S35 autoresearch iter 5 verdict
description: Trader-expert ROUND 1 verdict on Donchian iter 5 pivot direction — CONFIRM (a) 15M with pre-sweep economic sanity gate
type: project
---

# S35 Autoresearch Iter 5 — 15M Sweet Spot Verdict

**Date:** 2026-05-08
**Context:** Iter 4 (5M) showed n_trades WIN (276-926) but PnL catastrophically negative (-94% to -262%) due to BTC 5M commission physics (0.05-0.15% bar move vs 0.3% round-trip cost).

## Verdict: CONFIRM (a) with mandatory pre-sweep amendment

**Maintainer recommendation (a) 15M accepted.** All alternatives rejected.

## Key reasoning

- (b) maker fees: unrealistic (breakout strategies require taker fills — maker orders sit behind breakout price, guaranteed fill impossible)
- (c) signal filter: multi-filter overfitting risk; Bailey 2014 = test one hypothesis per iteration
- (d) longer hold: arbitrary parameter dimension, doesn't fix commission physics at 5M
- (e) combo: attribution impossible, overfitting near-certain

15M is the cheapest clean test of "does commission-dominates-moves resolve at slightly longer timeframe?"

## Mandatory pre-sweep amendment

Before running full 91-trial × N-strategy sweep, compute median BTC 15M bar range over 2023-2026.
- If median < 0.25% → commission physics problem persists → close research direction immediately (no sweep)
- If median >= 0.25% → proceed to full sweep

This is a 5-minute check that can save 10+ minutes of compute and provides clean falsification criterion.

## WFA parameters for 15M

- BARS_PER_YEAR: 35040 (= 4 bars/hour × 24 × 365)
- parquet: BTCUSDT_15m.parquet (already exists — 167,383 bars from S19)
- WFA_TRAIN_BARS: 14016 (= ~5.5 months of 15M bars, comparable to S19 production train window)
- WFA_TEST_BARS: 3504 (= ~5 weeks of 15M bars)
- grids: rescale from 5M grids by ~4-6x (Donchian 25-100 range, Bollinger 25-75, EMA 12-100)
- 80/20 train/held-out split on BTCUSDT_15m.parquet

## Key success criterion

Operator goal = n_trades + PnL BOTH must be positive on held-out.
n_trades alone is not success (iter 4 proved 276-926 trades with -94% to -262% PnL = worthless).

## N_trials discipline (ADR 0054 anti-snooping)

Iter 5 = NEW N_trials family = 1. Do NOT pool with 4H/5M/1H trial counts.

## Why (a) is not paradigm-dead (unlike S35 iter 3 Donchian 4H verdict)

S35 iter 3 verdict (paradigm-dead) applied to 4H Donchian where n_trades structural ceiling was the blocker (n=21 << T5=50, no parameter set could generate enough trades). 5M has the opposite problem: too many trades but commission-negative. 15M sits between these and deserves one clean test before paradigm-dead verdict.
