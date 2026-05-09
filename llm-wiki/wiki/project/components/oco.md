---
title: "Components: OCO (Spot emulation)"
type: component
tags: [execution, oco, bracket, spot, sprint-6, sprint-7]
created: 2026-04-23
updated: 2026-04-24
status: stable
sources: [project/decisions/0020-sprint-6-execution-spot-oco-emulation, project/decisions/0021-sprint-7-resilience]
---

# Components: OCO (Spot emulation)

**TL;DR:** Эмулированный 3-ордерный Spot OCO-брэкет: Entry Market Buy → Limit Sell @ TP (GTC) → Stop Market Sell @ SL (IOC-silent). Нативный `tpslMode=Full` отклонён биржей с retCode 170130 (probe v1 / ADR 0020 sub-decision 1). Модуль `src/execution/bracket.py` — чистые функции без I/O; `src/execution/coordinator.py` владеет lifecycle брэкета.

## Архитектура

### bracket.py — чистое API

`src/execution/bracket.py` содержит только pure-функции и frozen-датаклассы. Никакого I/O, никакого состояния.

**Константы ролей:**

```python
ROLE_ENTRY = "entry"
ROLE_TP    = "tp"
ROLE_SL    = "sl"
```

**Датаклассы:**

```python
@dataclass(frozen=True, slots=True)
class BracketParams:
    symbol:           str
    entry_side:       Literal["Buy", "Sell"]
    entry_qty:        Decimal
    tp_price:         Decimal
    sl_trigger_price: Decimal
    base_coin:        str
    qty_step:         Decimal

@dataclass(frozen=True, slots=True)
class BracketLeg:
    role:          Role
    symbol:        str
    side:          Literal["Buy", "Sell"]
    qty:           Decimal
    order_type:    str
    price:         Decimal | None
    trigger_price: Decimal | None
    order_link_id: str
    time_in_force: str

@dataclass(frozen=True, slots=True)
class BracketLegs:
    entry: BracketLeg
    tp:    BracketLeg
    sl:    BracketLeg
```

**Функции:**

```python
def make_order_link_id(*, bracket_id: str, role: Role, attempt: int) -> str:
    """Детерминированный orderLinkId. Bybit V5 max 36 chars.
    Raises ValueError, если результат > 36 символов."""
    ...

def build_bracket(params: BracketParams, *, bracket_id: str, attempt: int = 1) -> BracketLegs:
    """Строит тройку ног брэкета. Pure-функция."""
    ...

def compute_oco_qty(
    *,
    cum_exec_qty:  Decimal,
    cum_exec_fee:  Decimal,
    fee_currency:  str,
    base_coin:     str,
    qty_step:      Decimal,
) -> Decimal:
    """G5 fee-aware sizing. ROUND_DOWN."""
    ...
```

## Схема orderLinkId

Формат: `oco-{bracket_id}-{role}-{attempt}`

| Поле | Значение |
|---|---|
| `bracket_id` | 8-символьный префикс UUIDv4 (первые 8 hex-цифр) |
| `role` | `entry` / `tp` / `sl` |
| `attempt` | Начинается с 1; увеличивается при retry в `arm_oco` |
| Максимальная длина | 36 символов (ограничение Bybit V5) |

Пример: `oco-a1b2c3d4-tp-1` (18 символов).

Bybit отклоняет дублирующий `orderLinkId` с retCode 10006 — именно поэтому при retry необходимо увеличивать `attempt`. Поле `attempt` позволяет детерминированно генерировать уникальный ID без хранения глобального счётчика.

## G5 fee-aware sizing

Bybit Spot списывает комиссию с BASE-coin (BTC), а не с quote (USDT). Если выставить TP/SL-ноги с сырым `cumExecQty` (игнорируя комиссию), образуется «пыль», которую нельзя отменить — брэкет застревает навсегда.

**Формула:**

| Условие | Результат |
|---|---|
| `fee_currency == base_coin` | `oco_qty = step_floor(cum_exec_qty - cum_exec_fee)` |
| `fee_currency != base_coin` | `oco_qty = cum_exec_qty` (комиссия не шейвит base-qty) |

**step_floor:**

```
step_floor(x) = floor(x / qty_step) * qty_step   [ROUND_DOWN]
```

Функция `compute_oco_qty` возвращает `Decimal("0")` если `net <= 0` (защита от экстремальной комиссии).

## Sibling-cancel-on-Triggered

**ADR 0020 sub-decision 6.**

При WS-событии `orderStatus=Triggered` для SL-ноги coordinator немедленно вызывает `cancel_order(order_id=tp_order_id)`.

**Классификация race-условий:**

| retCode | Интерпретация | Действие |
|---|---|---|
| `110001` | `REJECT_ORDER_ALREADY_TERMINAL` — TP уже исполнился между Triggered и cancel | Нефатально; продолжаем |
| любой другой | Непредвиденная ошибка отмены | FSM → `SIBLING_CANCEL_FAILED` |

**FSM-пути:**

```
OCO_ARMED + SL_TRIGGERED → EXIT_SIBLING_CANCELLING
EXIT_SIBLING_CANCELLING + SIBLING_CANCELLED → FLAT
EXIT_SIBLING_CANCELLING + SIBLING_CANCEL_FAILED → EXIT_SIBLING_CANCEL_FAILED
EXIT_SIBLING_CANCEL_FAILED + SIBLING_CANCELLED → FLAT
EXIT_SIBLING_CANCEL_FAILED + RISK_HALT → HALTED   (retry island)
```

## EXIT_SL_RESIDUAL

**ADR 0020 sub-decision 7.**

Bybit Spot Stop молча переписывает `timeInForce=GTC` → `IOC` (probe v3-D). Если SL заполнен частично, остаток base-coin необходимо выгрузить Market-Sell'ом для полного выхода из позиции.

**FSM-путь:**

```
OCO_ARMED + PARTIAL_FILL → EXIT_SL_RESIDUAL
EXIT_SL_RESIDUAL + RESIDUAL_FLATTENED → FLAT
EXIT_SL_RESIDUAL + FLATTEN_FAILED → HALTED
```

Coordinator вычисляет residual qty как разницу между `entry_qty` и фактически исполненным объёмом SL-ноги, затем размещает Market Sell с этим qty.

## Flatten cascade

**ADR 0020 sub-decision 10.**

Аварийный flatten (триггеры: `HALT_RECONCILE_DIVERGENCE`, оператор halt, и т.д.):

1. `cancel_all_orders(symbol)` — освободить заблокированный баланс.
2. `get_wallet_balance(coin=BTC)` — прочитать `free_qty = walletBalance - locked`.
3. `step_floor(free_qty)` → `place_order(orderType=Market, side=Sell, qty)`.
4. При ошибке: один retry с `qty -= qty_step` (обходит step-quantization race).
5. Второй сбой: FSM → `FLATTEN_FAILED` → `HALTED`. Оператор: `runbooks/halt-recovery.md#halt_flatten_failed`.

## OCO_ARMING TTL

**ADR 0020 sub-decision 11.**

Если entry заполнен, но размещение TP/SL занимает более 60 секунд, Coordinator переводит FSM:

```
OCO_ARMING + BRACKET_TIMEOUT → HALTED
```

60 секунд покрывают сетевой jitter и API backoff. Предотвращает бесконечное зависание в состоянии `OCO_ARMING`.

## Bootstrap idempotency

**ADR 0020 sub-decision 9.**

При рестарте `Coordinator.bootstrap()`:

1. Читает `get_open_orders` + `get_order_history` для символа.
2. Парсит активные `orderLinkId`, соответствующие паттерну `oco-{bracket_id}-*-{attempt}`.
3. Определяет максимальный `attempt` среди найденных.
4. Устанавливает `last_attempt_num = max(found_attempt, current_attempt)`.

Это предотвращает ошибку дублирующегося `orderLinkId` (retCode 10006) при retry после рестарта.

## FSM — сводка

FSM v3 (`src/execution/state_machine.py`): **16 состояний, 29 событий, 59 уникальных переходов**. S7 удалил 2 silent dup-keys (legacy S5 `OCO_ARMED+TP_HIT` / `OCO_ARMED+PARTIAL_FILL`, ранее перекрывались S6 OVERRIDE-блоком; ruff F601 в final review) и добавил 6 transitions для bootstrap reconcile + 4-valued verdicts (ADR 0021 sub-decisions 1, 3).

## S7 — entry_order_id capture (ADR 0021 sub-decision 1)

`Coordinator.start_bracket()` пишет `entry_ack.order_id` в `oco_main_order_id` **до** ожидания filled-эха через WS. Без этого reconciler не мог адресовать ENTRY_PENDING-ордер для `get_order(order_id=...)`, и HEAL_ENTRY_FILLED-путь был мёртв.

Также передаётся `expected_oco_qty=entry_qty` для qty-cross-check в reconciler classifier'е.

## Инварианты (CRITICAL — verified by tests + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | `compute_oco_qty` subtracts `cum_exec_fee` only when `fee_currency == base_coin` — ROUND_DOWN to `qty_step` | `src/execution/bracket.py::compute_oco_qty` + ADR 0020 sub-decision 6 | `tests/unit/test_bracket_fee_aware_qty.py::test_qty_subtracts_fee_when_fee_currency_matches_base` |
| 2 | Returns `Decimal("0")` if net<=0 (extreme-fee guard, bracket must abort, NOT fill dust) | `src/execution/bracket.py::compute_oco_qty` zero-guard | `tests/unit/test_bracket_fee_aware_qty.py::test_qty_zero_when_fee_exceeds_qty` |
| 3 | SL payload omits `timeInForce` (Bybit silent GTC→IOC) | `src/execution/bybit/adapter.py::BybitMarketAdapter.place_stop_market_order` + ADR 0020 sub-decision 6 | (probe-validated) |
| 4 | `make_order_link_id` deterministic format `oco-{bracket_id}-{role}-{attempt}` (idempotent retry) | `src/execution/bracket.py::make_order_link_id` + ADR 0020 sub-decision 9 | `tests/unit/test_bracket_builder.py::test_make_order_link_id_pattern_and_length` |

## Связанные

- [[coordinator]] — owns OCO arming lifecycle (`start_bracket` + `arm_oco` + `flatten`); 8 RLock-protected methods (S8a)
- [[reconciler]] — walletBalance-as-truth партнёр + 4-valued verdicts (S7)
- [[execution-state-machine]] — FSM v3 (16 состояний, 29 событий, 59 переходов)
- [[bybit-adapter]] — 6 новых методов + banned-field guard
- [[ws-private-consumer]] — pybit close-hook + check_alive watchdog (S7)
- [[../decisions/0020-sprint-6-execution-spot-oco-emulation]]
- [[../decisions/0021-sprint-7-resilience]]
- [[../../trading/concepts/reason-codes]] — 42 reason-кода (S7: +3)
- [[../runbooks/halt-recovery]] — операторские процедуры

## Sources

- `project/decisions/0020-sprint-6-execution-spot-oco-emulation.md` (ADR 0020) — первичный источник всех sub-decisions.
- `src/execution/bracket.py` — реализация pure API.
- `src/execution/state_machine.py` — FSM v2: состояния, события, переходы.
