---
title: 0009. SemVer + Keep a Changelog
type: decision
tags: [adr, v0.1, versioning, release, governance]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0009. SemVer + Keep a Changelog

**Status:** Accepted
**Date:** 2026-04-19

## Context
Бот изменяется инкрементально: новые стратегии, биржи, поля схемы, risk-правила.
Без формального версионирования невозможно: (а) воспроизвести чужой run,
(б) понять, сломает ли апдейт сохранённый state, (в) согласовать миграции
SQLite/Parquet. Нужны простые, общепринятые соглашения.

## Decision
We will follow Semantic Versioning 2.0 (`MAJOR.MINOR.PATCH`) для тегов релизов
и Keep a Changelog 1.1 для `CHANGELOG.md`. Правила:
- **MAJOR** — breaking: изменение схемы БД/Parquet, несовместимая
  risk/strategy-семантика, удаление публичного API.
- **MINOR** — новая стратегия, новая биржа, новое поле с default'ом (обратно
  совместимо).
- **PATCH** — багфиксы, документация, performance без изменения поведения.

## Consequences
- (+) Любая версия боту/стратегии — самодокументирующаяся.
- (+) Автоматизация возможна (release-please/towncrier) при росте.
- (+) Runs логируют `bot_version` → reproducibility.
- (−) Дисциплина: каждый merge в main требует правки CHANGELOG.
- (−) 0.x допускает breaking в MINOR — мы явно оговариваем это до 1.0.
- (0) Отдельные версии для стратегий (`strategy.v1`) имеют смысл — зафиксируем
  в отдельном ADR, если понадобится.

## Alternatives considered
- CalVer (YYYY.MM.DD): отвергнуто — не сигнализирует breaking changes.
- Только git tags без changelog: отвергнуто — нет human-readable истории.
- Conventional Commits без SemVer: отвергнуто — хорошо дополняет, но не заменяет.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §11
- https://semver.org/spec/v2.0.0.html
- https://keepachangelog.com/en/1.1.0/
