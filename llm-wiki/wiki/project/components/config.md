---
title: Platform — Settings (config)
type: component
tags: [platform, config, pydantic-settings]
created: 2026-04-20
updated: 2026-04-20
sources: [src/platform/config.py, tests/unit/test_config.py, .env.example]
status: stable
---

# Platform — Settings

**TL;DR:** Единственная точка входа для runtime-конфига. `Settings` (pydantic-settings v2) читает env/`.env`, валидирует ключи Binance, флаги trading, пути, уровень логирования.

## Definition / Purpose

Класс `Settings(BaseSettings)` в `src/platform/config.py`. Загружается из `.env` файла + переменных окружения (case-insensitive, extra="ignore"). Все пути типизированы как `pathlib.Path`.

## Key properties

- **Binance**: `binance_api_key`, `binance_api_secret`, `binance_env: Literal["testnet", "mainnet"]` (по умолчанию `testnet`).
- **Runtime flags**: `trading_enabled: bool`, `live_trading: bool`. Invariant: `live_trading=true` требует `trading_enabled=true` (model_validator, защита от случайного prod-запуска).
- **Paths**: `data_dir`, `log_dir`, `db_path`, `parquet_dir` — все `Path`, нет дефолтов (обязательны).
- **Observability**: `sentry_dsn: str | None`, `log_level: Literal["DEBUG","INFO","WARNING","ERROR"]` (default INFO).

## Related

- [[../sprints/sprint-01-foundation]] — sprint where Settings was created
- [[../architecture/stack-v0.1]] — стек и версии.
- [[../decisions/0006-pydantic-v2-for-domain-models]] — ADR за pydantic v2.
- `.env.example` в корне — шаблон всех env-переменных.

## Sources

- `src/platform/config.py`
- `tests/unit/test_config.py` (3 теста: load from env / invalid env rejected / live-trading invariant)
