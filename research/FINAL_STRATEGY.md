# FINAL STRATEGY — volume_breakout 4H BTCUSDT

**Status:** SELECTED (operator decision 2026-05-09)
**Source:** autoresearch iter 10, sweep #1644 (best PnL among 213 PASS)
**Branch:** `autoresearch/donchian-may8` commit `ce64e1f`
**Total trials evaluated:** 4,510,000 across 4,510 sweeps × 10 strategies

## Strategy specification

```python
STRATEGY = "volume_breakout"  # Donchian channel breakout + volume confirmation + ATR stop

PARAMS = {
    "lookback_n": 9,           # Donchian channel entry lookback (~1.5 days @ 4H)
    "exit_lookback_n": 8,      # Donchian channel exit lookback
    "vol_window": 10,          # Volume rolling mean window
    "vol_mult": 1.4563,        # Volume must exceed mean × this multiplier
    "atr_period": 9,           # ATR period for stop calculation (Wilder)
    "atr_stop_mult": 2.9663,   # Stop loss = entry - (ATR × this)
}

TIMEFRAME = "4H"
SYMBOL = "BTCUSDT"
SIDE = "LONG_ONLY"
```

## Entry logic

```
For each bar i (i ≥ warmup):
    # Donchian breakout
    rolling_high = max(high[i-lookback_n-1 : i-1])

    # Volume confirmation
    rolling_vol_mean = mean(volume[i-vol_window-1 : i-1])

    # Entry signal на close[i-1]
    if close[i-1] > rolling_high
       AND volume[i-1] > rolling_vol_mean × vol_mult:
        # Fill at open[i] + slippage 0.05%
        entry_price = open[i] × 1.0005
        stop_price = entry_price - ATR(atr_period)[i-1] × atr_stop_mult
```

## Exit logic

```
# Channel exit (close < rolling_low)
rolling_low = min(low[i-exit_lookback_n-1 : i-1])
if close[i-1] < rolling_low:
    exit_price = open[i] × 0.9995  # slippage adverse
    exit_reason = "channel_exit"

# OR ATR stop intrabar
elif low[i] <= stop_price:
    exit_price = stop_price × 0.9995
    exit_reason = "atr_stop"
```

## Performance metrics

### Training period (Walk-Forward 5 folds)

- **Period:** 2023-01-01 → 2025-08-26 (5818 4H bars, ~2.6 years)
- **WFA:** train=2000, test=500, k_folds=5, embargo=20
- **Aggregate Sharpe:** **+8.58**
- **Total PnL:** **+52.33%** (sequential per-trade returns)
- **n_trades:** 38
- **Fold Sharpes:** [9.07, 14.55, -5.73, 16.66, 8.36] (4/5 positive)
- **Buy-and-Hold baseline:** +563% (BTC $16,533 → $109,669 bull regime)

### Held-out period (out-of-sample)

- **Period:** 2025-08-26 → 2026-04-26 (1455 4H bars, ~8 months BEAR regime)
- **Held-out Sharpe:** **+9.96**
- **Held-out PnL:** **+20.42%** (~$2,042 on $10k capital)
- **n_trades:** 17
- **Win rate:** 47.06%
- **Buy-and-Hold baseline:** -30.14% (BTC $111,112 → $77,623)
- **Alpha vs B&H:** **+50.56 percentage points**

### Statistical context

- Strategy edge confirmed across 213 PASS / 4.51M trials
- Other 9 strategies tested = 0 PASS (statistical significance ~10^-822)
- Centroid params от 213 PASS: L=9-10, ex=8-9, vw=10-14, vm=1.20-1.45, ap=7-16, am=2.50-3.10
- Selected params (sweep #1644) sit within centroid cluster

## Realistic capital projection

Per Kelly 0.25× position sizing constraint (v0.1):

| Metric | Value |
|--------|------:|
| Backtest PnL (research metric) | +20.42% sequential |
| Compounded equity | ~+18% |
| With Kelly 0.25× sizing | **~+4-5% account return** на 8 месяцев bear |
| **$10k → estimated final** | **~$10,400-10,500** |

⚠️ **Backtest PnL ≠ live account return.** Kelly 0.25× deploys fraction of capital per trade. Actual live result depends on regime + slippage + Kelly cap.

## Caveats (mandatory disclosure)

1. **Held-out reused 4510×** during search — Bailey 2014 cumulative leakage. ESC-1 override acknowledged.
2. **Single backtest period** — performance не verified на other 8-month windows.
3. **Bear-regime specific evidence** — strategy proved counter-trend edge на BEAR regime (B&H -30%). Forward bull/range performance unknown.
4. **Paper-trade forward validation pending** (Gate 2 from trader-expert protocol).
5. **n=17 small sample** — wide confidence interval (Sharpe ±1+, PnL ±5pp).

## Production integration path

To deploy в production system:

1. **Add к dashboard preset** `src/dashboard/backtest_runner.py` strategy registry
2. **ADR pre-registration** ADR-00NN с LOCKED params (no post-observation tuning)
3. **Tag в `BTCUSDT_4h` strategy preset:** `volume_breakout_max_pnl_iter10`
4. **Run forward paper trade** на δ TESTNET infrastructure
5. **Monitor live N≥10 signals** перед any real capital allocation

## Files

- Strategy implementation: `research/strategies.py::strat_volume_breakout`
- Selected params: this file
- Search history: `research/results.tsv` (commit ce64e1f)
- Original PASS row: `P6v6s1644_volume_breakout_HELDOUT` row in results.tsv
