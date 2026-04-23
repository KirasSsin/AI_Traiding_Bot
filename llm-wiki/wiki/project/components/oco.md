---
title: Execution — OCO bracket builder (native Bybit tpslMode)
type: component
tags: [execution, oco, bracket, sl, tp, sprint-5]
created: 2026-04-23
updated: 2026-04-23
sources: [src/execution/oco.py, tests/unit/test_oco.py, project/decisions/0019-sprint-5-execution-decisions.md]
status: stable
---

# Execution — OCO bracket

**TL;DR:** Pure-function builder of native Bybit `tpslMode=Full` brackets — SL = entry − k_sl·ATR (tick DOWN), TP = entry + k_tp·ATR (tick UP). v0.1 LONG-only.

## Definition / Purpose

Строит параметры OCO-брэкета для нативного Bybit механизма `tpslMode=Full` (не эмулированного). При native tpslMode биржа сама отменяет противоположную ногу при срабатывании любой из двух (SL/TP) — cancel-on-fill гарантирован exchange.

Snap-to-tick: SL округляется вниз (ROUND_DOWN), TP вверх (ROUND_UP) — чтобы цены прошли биржевые price-filter без отклонения.

## Interface

```python
@dataclass
class OcoParams:
    symbol: str
    side: OrderSide          # v0.1: только BUY (LONG)
    entry_price: Decimal
    atr: Decimal             # > 0
    k_sl: Decimal            # множитель ATR для SL (e.g. Decimal("1.5"))
    k_tp: Decimal            # множитель ATR для TP (e.g. Decimal("3.0"))
    tick_size: Decimal       # минимальный шаг цены инструмента

@dataclass
class OcoOrder:
    stop_loss: Decimal       # entry_price - k_sl * atr, snapped ROUND_DOWN
    take_profit: Decimal     # entry_price + k_tp * atr, snapped ROUND_UP
    tpsl_mode: str           # всегда "Full"

def build_oco_order(params: OcoParams) -> OcoOrder: ...
```

## Key properties

- LONG-only в v0.1: `side != BUY` → `ValueError`.
- SL уровень округляется вниз (ROUND_DOWN), TP вверх (ROUND_UP) — биржа не отклонит за price-tick.
- `atr <= 0` → `ValueError`.
- Pure function: нет I/O, нет state, детерминирована.

## Related

- `[[../decisions/0019-sprint-5-execution-decisions]]` — sub-decision 1 (native tpslMode).
- `[[bybit-adapter]]` — потребитель: передаёт `take_profit`/`stop_loss`/`tpsl_mode` в `place_market_order`.
- `[[../../trading/concepts/reason-codes]]` — `EXIT_SL_HIT`, `EXIT_TP_HIT`, `EXIT_OCO_PARTIAL_TIMEOUT`.

## Sources

- `src/execution/oco.py`, `tests/unit/test_oco.py`.
