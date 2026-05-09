---
title: Platform — Logging (structlog JSON)
type: component
tags: [platform, logging, structlog, observability]
created: 2026-04-20
updated: 2026-04-20
sources: [src/platform/logging.py, tests/unit/test_logging.py]
status: stable
---

# Platform — Logging

**TL;DR:** structlog → stdlib logging → stdout в JSON-формате. Все логи имеют обязательные ключи `event`, `level`, `timestamp`.

## Definition / Purpose

Файл `src/platform/logging.py` экспортирует две функции:

- `configure_logging(level: str = "INFO") -> None` — идемпотентная настройка. Вызывает `structlog.reset_defaults()` + `logging.basicConfig` + `structlog.configure(...)`. Можно вызывать несколько раз безопасно.
- `get_logger(name: str) -> BoundLogger` — обёртка над `structlog.get_logger`.

## Key properties

- **JSON renderer** — `structlog.processors.JSONRenderer()` в конце pipeline.
- **Обязательные поля** в payload: `event` (сообщение), `level` (lowercase), `timestamp` (ISO-8601, UTC, ключ `timestamp`).
- **Контекст**: `structlog.contextvars.merge_contextvars` — позволяет биндить контекст через `bind_contextvars(...)`.
- **Stack info / exc_info** — автоматически рендерится для `logger.exception(...)`.

## Usage

```python
from src.platform.logging import configure_logging, get_logger

configure_logging(level="INFO")
log = get_logger("platform.startup")
log.info("boot", component="marketdata", version="0.1.0-alpha.1")
# → {"event": "boot", "level": "info", "timestamp": "...", "component": "marketdata", "version": "0.1.0-alpha.1"}
```

## Related

- [[../sprints/sprint-01-foundation]] — sprint where logging module was created
- [[../architecture/stack-v0.1]] — structlog >=24.1 в deps.
- [[../architecture/domain-events]] — все domain events логируются через этот же pipeline.

## Sources

- `src/platform/logging.py`
- `tests/unit/test_logging.py` — проверяет наличие обязательных JSON-ключей.
