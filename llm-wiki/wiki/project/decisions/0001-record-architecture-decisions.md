---
title: 0001. Record architecture decisions
type: decision
tags: [adr, v0.1, process, governance]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0001. Record architecture decisions

**Status:** Accepted
**Date:** 2026-04-19

## Context
В проекте торгового бота v0.1 накапливаются архитектурные решения (язык, хранилище,
биржа, таймфрейм, модели слиппеджа, sizing, circuit-breakers). Без формальной
фиксации решения теряются, обоснования забываются, спор возобновляется на каждом
code review. Нужен лёгкий, текстовый, версионируемый в git формат.

## Decision
We will record all architecturally significant decisions as Architecture Decision
Records (ADR) в формате Michael Nygard. Каждый ADR — markdown-файл в
`wiki/project/decisions/NNNN-slug.md` с YAML frontmatter, разделами Context /
Decision / Consequences / Alternatives / References. Статусы: `proposed`,
`accepted`, `deprecated`, `superseded`.

## Consequences
- (+) История решений иммутабельна и доступна через `git log`.
- (+) Новые участники находят "почему" за 1 файл, а не ищут по Slack/ревью.
- (+) Superseded-ADR остаются читаемыми (rationale сохраняется).
- (−) Требует дисциплины: каждое значимое решение = новый ADR.
- (−) Малые решения не должны попадать в ADR (иначе шум).
- (0) Нумерация монотонная, без ретро-вставок.

## Alternatives considered
- Wiki-страница "Decisions": (отвергнуто) нет версионирования рядом с кодом.
- Комментарии в PR: (отвергнуто) теряются при squash, не индексируются.
- RFC-процесс с обсуждением: (отвергнуто) избыточно для команды <5 человек на v0.1.

## References
- Michael Nygard, "Documenting Architecture Decisions" (2011)
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §11

## Связанные

- [[../sprints/sprint-01-foundation]] — спринт основания (Foundation), когда ADR-процесс был запущен
