---
title: ReasonCode enums — два параллельных пространства имён
type: component
tags: [reason-codes, schema, bybit, taxonomy, canonical-counts]
created: 2026-05-11
updated: 2026-05-11
status: stable
sources:
  - src/risk/reason_codes.py
  - src/execution/bybit/errors.py
---

# ReasonCode enums — два параллельных пространства имён

**TL;DR:** в проекте существуют ДВА независимых `ReasonCode` StrEnum. Добавление члена в один НЕ меняет счётчик другого. Важно для canonical counts CI и sprint wiki narratives.

## Контекст

В S47 T9 добавили `INVALID_PARAM` к bybit-local enum. Wiki-narrative ошибочно написала `reason_codes 56→57` (имея в виду главный enum). Главный остался 56. CI canonical counts сфлейлил, выяснили — путаница между двумя enum'ами. ADR 0047 T9 урок.

## Главный enum: `src/risk/reason_codes.py:ReasonCode`

- **56 членов** (после S47; последнее добавление S40 +3: HALT_ATR_*)
- Tracked by `.github/workflows/ci.yml` «Canonical counts verify» step
- Используется: `src/risk/manager.py`, `src/execution/coordinator.py`, `src/runtime/runtime_manager.py`, dashboard, audit JSONL
- Семантические категории: Entry (7) / Scale+Exit (13) / Rejects (9) / Halts (27)
- **Canonical count track:** да — `reason_codes` ключ в CI canonical counts dict

## Bybit-local enum: `src/execution/bybit/errors.py:ReasonCode`

- **9 членов** (после S47 T9): `CLOCK_DRIFT`, `WRONG_API_KEY`, `RATE_LIMIT_HIT`, `EXCHANGE_MAINTENANCE`, `INSUFFICIENT_BALANCE`, `FILTER_VIOLATION`, `REJECT_ORDER_ALREADY_TERMINAL`, `INVALID_PARAM`, `UNKNOWN_ERROR`
- Используется: `src/execution/bybit/adapter.py` через `map_error()` (Bybit V5 retCode → domain code)
- Параллельное пространство имён: имена пересекаются с главным enum'ом, но это независимый класс
- **Canonical count track:** нет — CI НЕ считает этот enum
- `_MAP` dict: Bybit retCode integer → `ReasonCode` member (`10001`, `10002`, `10003`, `10006`, `10016`, `110001`, `110007`, `110017`, `170131`, `170140`, `170213`, `170213`)

## Правила для агентов и sprint narratives

| Ситуация | Правильная формулировка |
|----------|------------------------|
| Добавлен член в `src/risk/reason_codes.py` | «reason_codes N→N+1» (canonical count меняется) |
| Добавлен член в `src/execution/bybit/errors.py` | «bybit-local ReasonCode +1 (main enum unchanged, canonical stays N)» |
| CI canonical counts fail | Проверь ТОЛЬКО `src/risk/reason_codes.py:ReasonCode` — bybit-local enum здесь не причём |

## Anti-pattern (S47 lesson)

```
# WRONG (S47 T9 ошибка):
"Canonical counts reason_codes 56→57 (added INVALID_PARAM)"

# CORRECT:
"Canonical counts reason_codes=56 UNCHANGED
 bybit-local ReasonCode (src/execution/bybit/errors.py) +1: INVALID_PARAM для retCode 10001"
```

## Проверка live counts

```bash
# Главный enum (canonical):
source .venv/bin/activate
python -c "from src.risk.reason_codes import ReasonCode; print(f'main: {len(list(ReasonCode))}')"

# Bybit-local (не canonical):
python -c "from src.execution.bybit.errors import ReasonCode; print(f'bybit-local: {len(list(ReasonCode))}')"
```

## Связанные страницы

- [[project/architecture/reason-codes-schema]] — JSON Schema для audit-record (SHA-256 chain)
- [[project/components/bybit-adapter]] — использует `map_error()` + bybit-local enum
- [[project/architecture/current-state]] — canonical counts table (отслеживает только main enum)
