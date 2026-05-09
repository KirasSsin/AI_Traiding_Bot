---
title: Trade history — per-trade audit log (idempotent insert + AwareDatetime)
type: component
tags: [trade-history, audit, persistence, sqlite, sprint-4, sprint-5]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/risk/trade_history.py
  - migrations/002_risk.sql
  - migrations/003_trade_history_unique.sql
---

# Trade history — per-trade audit log

**TL;DR:** Персистит каждую закрытую сделку в SQLite с идемпотентной вставкой через `UNIQUE INDEX on entry_signal_id` и контрактом `AwareDatetime` (UTC) для всех временных меток.

## Definition / Purpose

`trade_history` — таблица аудит-лога, которая пишется на каждое закрытие позиции. Назначений три:

1. **Post-trade forensics** — полный per-trade record (symbol, qty, entry/exit price, PnL, fees, reason_code, kelly_phase, временные метки entry/exit/recorded).
2. **Kelly trade-count tracking** — `TradeHistoryRepository.count()` и `load_recent()` используются RiskManager'ом для определения Kelly-фазы (ADR 0012): `n < 30 → phase 1`, `n < 100 → phase 2`, `n < 200 → phase 3`, `n ≥ 200 → phase 4`.
3. **Crash-recovery idempotency** — `INSERT OR IGNORE` + `UNIQUE INDEX uq_trade_history_entry_signal` на `entry_signal_id` гарантируют, что повторный вызов `insert_closed_trade()` после краша не дублирует запись и не нарушает Kelly trade count.

**Чем отличается от `halt_log`** (S7 γ-persistence): `halt_log` пишется при каждом переходе CB в halt-состояние. `trade_history` пишется при каждом закрытии сделки (EXIT_TP / EXIT_SL / EXIT_RECONCILE_DETECTED и пр. по reason_code). Разные события, разные таблицы, разные readers.

## Публичный API

```python
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from src.risk.reason_codes import ReasonCode
from typing import Literal
from decimal import Decimal
from uuid import UUID

class TradeRecord(BaseModel):
    """Closed trade record. Decimal monetary, ISO-8601 UTC timestamps."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    trade_id: int | None = None          # None pre-insert; set by AUTOINCREMENT
    symbol: str
    entry_signal_id: UUID                # dedup key — UNIQUE INDEX
    entry_ts: AwareDatetime
    exit_ts: AwareDatetime
    qty: Decimal                         # gt=0
    entry_price: Decimal                 # gt=0
    exit_price: Decimal                  # gt=0
    pnl_quote: Decimal                   # signed (USDT)
    pnl_pct: Decimal                     # signed (e.g. 0.012 = +1.2%)
    fees_paid: Decimal                   # ge=0
    reason_code: ReasonCode
    kelly_phase: Literal[1, 2, 3, 4]
    recorded_at: AwareDatetime


class TradeHistoryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None: ...

    def insert_closed_trade(self, record: TradeRecord) -> int:
        """Insert and return trade_id. Idempotent on duplicate entry_signal_id.
        Returns existing trade_id if duplicate (INSERT OR IGNORE + SELECT fallback)."""
        ...

    def load_recent(
        self, *, window_days: int = 90, now: datetime | None = None
    ) -> list[TradeRecord]:
        """Load trades with exit_ts >= (now - window_days). ORDER BY exit_ts ASC."""
        ...

    def count(self) -> int:
        """SELECT COUNT(*) — used by RiskManager for Kelly phase determination."""
        ...
```

Нет методов `get_by_signal_id` или `list_recent` с `limit` — публичный интерфейс репозитория ограничен тремя методами выше. `_row_to_record()` — приватный статический метод для десериализации строки SQLite → `TradeRecord`.

## Схема (`trade_history` table)

```sql
-- migrations/002_risk.sql (Sprint 4 — Risk & Circuit Breakers schema)
CREATE TABLE trade_history (
    trade_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol           TEXT    NOT NULL,
    entry_signal_id  TEXT    NOT NULL,
    entry_ts         TEXT    NOT NULL,   -- ISO-8601 UTC AwareDatetime
    exit_ts          TEXT    NOT NULL,   -- ISO-8601 UTC AwareDatetime
    qty              TEXT    NOT NULL,   -- Decimal as string
    entry_price      TEXT    NOT NULL,   -- Decimal as string
    exit_price       TEXT    NOT NULL,   -- Decimal as string
    pnl_quote        TEXT    NOT NULL,   -- Decimal as string, signed
    pnl_pct          TEXT    NOT NULL,   -- Decimal as string, signed
    fees_paid        TEXT    NOT NULL,   -- Decimal as string
    reason_code      TEXT    NOT NULL,   -- ReasonCode.value
    kelly_phase      INTEGER NOT NULL CHECK(kelly_phase IN (1,2,3,4)),
    recorded_at      TEXT    NOT NULL    -- ISO-8601 UTC AwareDatetime
);

CREATE INDEX idx_trade_history_exit_ts     ON trade_history(exit_ts);
CREATE INDEX idx_trade_history_symbol_exit ON trade_history(symbol, exit_ts);

-- migrations/003_trade_history_unique.sql (Sprint 4 Task 7 follow-up)
CREATE UNIQUE INDEX IF NOT EXISTS uq_trade_history_entry_signal
    ON trade_history(entry_signal_id);
```

Миграции: `migrations/002_risk.sql` (DDL) + `migrations/003_trade_history_unique.sql` (UNIQUE INDEX). Forward-only per ADR 0003 (no DROP COLUMN, no destructive backfills).

## Idempotency contract

UNIQUE INDEX `uq_trade_history_entry_signal` на `entry_signal_id` обеспечивает идемпотентность:

- `INSERT OR IGNORE` — при дубликате строка не вставляется, `cursor.rowcount = 0`.
- Если `rowcount = 0` → fallback `SELECT trade_id WHERE entry_signal_id = ?` → возвращает существующий `trade_id`.
- Caller (RiskManager) безопасен для retry после краша: повторный `insert_closed_trade()` вернёт тот же `trade_id`, не дублирует запись, не портит Kelly trade count.

Это S4 Kelly trade-count requirement (ADR 0012): счётчик сделок должен быть точным. at-least-once delivery без дублирования.

## AwareDatetime contract

Все временные метки (`entry_ts`, `exit_ts`, `recorded_at`) — `pydantic.AwareDatetime` (tz-aware, UTC). Хранение в SQLite: TEXT ISO-8601 (`.isoformat()`). Чтение: `datetime.fromisoformat(row[N]).astimezone(UTC)`.

Per ADR 0007 (UTC ns-precision): naive datetime → pydantic поднимет `ValidationError` при создании `TradeRecord` (поле `entry_ts: AwareDatetime`). Defensive — нельзя нечаянно записать naive timestamp.

## Reader patterns (audit queries)

```sql
-- Trade count для Kelly phase determination (per ADR 0012)
-- load_recent(window_days=90) + count() в RiskManager
SELECT count(*) FROM trade_history;

-- Trades за окно (load_recent implementation)
SELECT trade_id, symbol, entry_signal_id, entry_ts, exit_ts, qty,
       entry_price, exit_price, pnl_quote, pnl_pct, fees_paid,
       reason_code, kelly_phase, recorded_at
FROM trade_history
WHERE exit_ts >= ?      -- cutoff = now - window_days
ORDER BY exit_ts ASC;

-- Win-rate для Wilson 95% CI (per ADR 0012, ADR 0018 sub-decision)
SELECT count(*) FILTER (WHERE pnl_quote > 0) * 1.0 / count(*)
FROM trade_history
WHERE exit_ts >= ?;

-- Recent trades для reconciliation / forensics
SELECT * FROM trade_history ORDER BY exit_ts DESC LIMIT 100;
```

## Migration reference

Две миграции, обе forward-only:

| Файл | Содержимое |
|------|-----------|
| `migrations/002_risk.sql` | DDL: `trade_history` + `equity_snapshots` + 2 indexes |
| `migrations/003_trade_history_unique.sql` | `CREATE UNIQUE INDEX IF NOT EXISTS uq_trade_history_entry_signal` |

Migrations runner (`src/platform/storage/`) применяет их в порядке filename prefix. `IF NOT EXISTS` в M003 безопасен при повторном прогоне (идемпотентен).

## Инварианты (CRITICAL — verified by tests + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | `INSERT OR IGNORE` + `UNIQUE INDEX uq_trade_history_entry_signal` on `entry_signal_id` — crash-idempotent Kelly trade count | `migrations/003_trade_history_unique.sql` + `src/risk/trade_history.py::TradeHistoryRepository.insert_closed_trade` | `tests/unit/test_risk_trade_history.py::test_duplicate_entry_signal_id_returns_existing_id` |
| 2 | `AwareDatetime` (UTC) for all timestamps — naive datetime → ValueError | `src/risk/trade_history.py::TradeRecord` model validators + ADR 0007 | `tests/unit/test_risk_trade_history.py::test_naive_datetime_rejected` |
| 3 | Migrations forward-only (`002_risk.sql` + `003_trade_history_unique.sql`) | migrations/ + ADR 0003 | (review rule) |

## Referenced by

- [[risk-manager]] — primary writer: `insert_closed_trade()` на каждое position closure
- [[kelly]] — phase selection reads trade count from `TradeHistoryRepository.count()`
- [[../decisions/0012-4-phase-kelly-sizing]] — Kelly phases ADR defines count thresholds (n<30, n<100, n<200, n≥200) consumed from this table

## Связанные

- [[../sprints/sprint-04-risk]] — sprint where trade-history table and TradeRecord were created
- [[../sprints/sprint-05-execution]] — sprint where idempotency (UNIQUE INDEX) was hardened
- [[risk-manager]] — primary writer: вызывает `insert_closed_trade()` на каждое закрытие позиции; читает `count()` для Kelly phase
- [[kelly]] — 4-phase sizing читает trade count из `count()` / `load_recent()` (ADR 0012)
- [[storage]] — SQLite WAL persistence layer; migrations runner
- [[circuit-breakers]] — Kelly phase влияет на sizing при L1 warn (half-size)
- [[reconciler]] — S7: при `HEAL_ENTRY_FILLED` / `EXITED` verdict может инициировать запись через RiskManager
- [[../decisions/0012-4-phase-kelly-sizing]] — Kelly phase thresholds (n<30/100/200/≥200)
- [[../decisions/0018-sprint-4-risk-decisions]] — Wilson 95% CI lower bound для фаз 3/4
- [[../decisions/0007-utc-timestamps-ns-precision]] — AwareDatetime + UTC ISO-8601 contract
- [[../architecture/storage]] — SQLite schema для `trade_history` таблицы.

## Открытые вопросы

- **Trade closure caller** — RiskManager вызывает `insert_closed_trade()` напрямую, или через Coordinator при `EXIT_*` reason code? Надо верифицировать grep `TradeHistoryRepository.insert_closed_trade` по callers в `src/`.
- **Retention policy** — TTL отсутствует. Таблица растёт бесконечно. v0.2 archival policy для old trades не запланирована (деферировано).
- **window_days=90 default** — hardcoded в `load_recent()`. Kelly phase читает `count()` (весь history), не windowed. `load_recent` — для reconciliation/forensics, не для phase calc. Уточнить использование.

## Sources

- `src/risk/trade_history.py` (118 LoC) — `TradeRecord` + `TradeHistoryRepository` (insert_closed_trade / load_recent / count / _row_to_record)
- `migrations/002_risk.sql` — DDL (Sprint 4)
- `migrations/003_trade_history_unique.sql` — UNIQUE INDEX follow-up (Sprint 4 Task 7)
- ADR 0007 (UTC-ns AwareDatetime)
- ADR 0012 (Kelly phases from trade count)
- ADR 0018 (Wilson CI, sprint-4 risk decisions)
