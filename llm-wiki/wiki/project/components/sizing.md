---
title: Position Sizing (compute_qty)
type: component
tags: [risk, sizing, atr, v0.1]
created: 2026-04-23
updated: 2026-04-23
status: stable
sources: [src/risk/sizing.py]
---

# Position Sizing — compute_qty

**TL;DR:** Pure function. ATR-based stop-distance position sizing. `qty = (fraction · equity) / (k · ATR)`. Все inputs `Decimal`. `k` инжектится из Settings (default `1.5`).

## Публичный API

`src/risk/sizing.py`:

```python
def compute_qty(
    equity: Decimal,
    fraction: Decimal,
    atr: Decimal,
    price: Decimal,
    k: Decimal = Decimal("1.5"),
) -> Decimal
```

`price` параметр зарезервирован (текущая формула не использует, но интерфейс готов под notional-pricing рефакторинг).

## Formula

```
qty = (fraction × equity) / (k × ATR)
```

- **fraction** — output `kelly.phase_adjusted_fraction` (equity fraction at risk).
- **equity** — current total equity (`realized + unrealized`) в quote currency.
- **ATR(14)** — volatility proxy, в той же quote currency что и `equity`.
- **k** — stop-distance multiplier. SL ставится на `entry − k·ATR`. Default `1.5` per Settings.

Интуиция: если SL на расстоянии `k·ATR` от entry, и мы готовы потерять `fraction × equity` при стопе, тогда qty получается из деления.

## Defensive contracts

- Negative inputs → `ValueError`.
- `fraction == 0` ИЛИ `atr == 0` → returns `Decimal("0")` (caller pre-check expected, но не падаем).
- Все вычисления в Decimal — никаких float casts (см. `~/.claude/CLAUDE.md` §3, ADR 0007).

## Quantization (caller responsibility)

`compute_qty` возвращает full-precision Decimal. **Округление до exchange precision выполняется в `RiskManager.assess`:**

```python
qty = qty.quantize(Decimal("0.00000001"))  # 8 dp Bybit Spot
if qty <= 0:
    return self._reject(..., REJECT_MIN_NOTIONAL)
```

Reason: тесты `compute_qty` остаются numerically deterministic; precision-policy живёт в orchestrator'е и может меняться per venue (Bybit Spot 8dp, perpetuals другая).

## Settings binding

```toml
risk_sl_atr_multiplier = "1.5"   # k для compute_qty + SL placement
risk_tp_atr_multiplier = "3.0"   # TP placement (R:R = 2:1)
```

## Tests

`tests/unit/test_risk_sizing.py` — formula correctness, zero/edge cases, ValueError на negatives.

## Связанные

- [[kelly]] — источник `fraction`
- [[risk-manager]] — caller, выполняет quantization + min-notional reject
- [[../../trading/concepts/kelly-phases]] — формульная мотивация
