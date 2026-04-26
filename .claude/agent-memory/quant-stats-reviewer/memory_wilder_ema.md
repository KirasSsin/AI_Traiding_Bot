---
name: Wilder EMA hard rule (ADR 0011)
description: ADX/RSI/ATR/±DI must use Wilder smoothing alpha=1/n seeded with SMA(n); EMA crossovers use classical alpha=2/(n+1)
type: project
---

ADR 0011 binding rule:
- Wilder EMA: alpha = 1/n, seed = SMA of first n values. Used for: ADX, RSI, ATR, +DI, -DI.
- Classical EMA: alpha = 2/(n+1). Used for: EMA crossover (fast=12, slow=26).

TA-Lib native bindings (talib.ADX, talib.RSI, talib.ATR, talib.PLUS_DI, talib.MINUS_DI) implement Wilder internally. Do not double-smooth by wrapping in a custom EMA layer.

Warm-up NaN prefix: classical = n-1 bars; Wilder >= n bars; ADX double-smoothed = 2n-1 bars minimum.

**How to apply:** Any indicator formula review — verify which smoothing applies. "Looks like EMA" is not sufficient.
