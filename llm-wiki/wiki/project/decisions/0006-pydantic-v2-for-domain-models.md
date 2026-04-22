---
title: 0006. Pydantic v2 for domain models
type: decision
tags: [adr, v0.1, validation, serialization, domain]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0006. Pydantic v2 for domain models

**Status:** Accepted
**Date:** 2026-04-19

## Context
Domain-модели (Order, Trade, Signal, Position, RiskState, Config) пересекают
границы: REST JSON ↔ Python ↔ SQLite/Parquet ↔ логи. Нужен единый слой
runtime-валидации и сериализации с разумной производительностью и type hints,
совместимый с IDE/mypy.

## Decision
We will use Pydantic v2 (pydantic-core на Rust) для всех domain-моделей и для
типизированной загрузки YAML-конфигов. Frozen-модели (`model_config =
ConfigDict(frozen=True)`) для value-объектов; `strict=True` на границах
(входной JSON от биржи, конфиг).

## Consequences
- (+) Валидация на границе → inner-код оперирует проверенными типами.
- (+) Pydantic v2 в ~5–50× быстрее v1 (pydantic-core на Rust) — не бутылочное
  горлышко даже для tick-level адаптеров.
- (+) `model_dump()/model_validate()` — прямая интеграция с JSON/dict/ORM.
- (+) Отличная mypy-интеграция.
- (−) Runtime-валидация всё ещё стоит CPU — отключать её в hot-loop после
  границы через plain dataclasses, если profiling покажет.
- (−) Breaking changes между v1 и v2 — мы начинаем сразу с v2, риск нулевой.
- (0) Замена на attrs+cattrs возможна, но выгоды не видно.

## Alternatives considered
- attrs + cattrs: отвергнуто — больше boilerplate для валидации JSON-границ.
- Plain dataclasses: отвергнуто — нет runtime-валидации, руками писать парсеры.
- msgspec: рассматривался — быстрее, но меньшая экосистема и зрелость.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §3
- Pydantic v2 docs: https://docs.pydantic.dev/2.0/
