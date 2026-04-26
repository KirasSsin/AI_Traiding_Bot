---
name: Project stack patterns
description: Canonical Python patterns for AI Trading Bot v0.1 — Decimal, structlog, pydantic v2, asyncio
type: project
---

- Decimal hygiene (money path): use `Decimal(str(x))` never `Decimal(float_value)`. Quantize after multiply in hot paths (Kelly, sizing, slippage). Forbidden in src/risk/, src/execution/, src/marketdata/, src/backtest/, src/analytics/.
- structlog: `log.info("event_name", key=value)` — never f-strings in messages. Required keys for trading events: symbol, bar_close_time or bracket_id, reason_code.
- pydantic v2: `model_config = ConfigDict(...)` (not v1 `class Config`). Forbidden: `@validator`, `Config` inner class.
- asyncio: no `time.sleep` in async code. sqlite3 in `async def` must use `asyncio.to_thread`. Every `create_task` tracked in a set.
- sqlite3: WAL mode, Decimal stored as TEXT (never REAL), datetime as ISO-8601 UTC TEXT, writes wrapped in `with self._conn:`.
- Python 3.12 required — project uses StrEnum, PEP 604 unions, modern pydantic-settings. Venv: `.venv/bin/python`.
