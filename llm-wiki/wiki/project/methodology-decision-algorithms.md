---
title: Methodology — Decision Algorithms
type: architecture
tags: [methodology, dispatch, anti-bloat, batch, parallel]
created: 2026-04-24
updated: 2026-04-24
status: stable
---

# Methodology — Decision Algorithms

**TL;DR:** Правила контроллера для dispatch по риску, batch-критерии и параллельный запуск.

## Anti-bloat (по размеру изменения)

| LoC | Action |
|-----|--------|
| < 50 + tests pass | L5 domain reviewer (если scope hit) ИЛИ ничего |
| 50–200 | L5 domain + опционально L4 `code-review-and-quality` |
| > 200 ИЛИ money/security/persistence | Full L5 + L4 (`code-review-and-quality` + `security-and-hardening`) |
| Cross-module архитектурное | L3 brainstorm + plan first |

## Batch criteria (объединяем tasks в один dispatch)

- Same domain (2 pydantic models → Tasks 3+4 batched)
- Same file group (CLI + entry point → одна задача)
- ≤ 5 RED→GREEN cycles total в одном subagent

## Parallel dispatch (несколько Agent calls в одном message)

**ALWAYS параллельно:**
- trading-logic-reviewer + python-reviewer (разный scope)
- trading-logic-reviewer + quant-stats-reviewer (разный scope)
- spec-reviewer task N + implementer task N+1 (если spec review ~5 min)
- два независимых implementer (разные файлы, 0 shared state)

**NEVER параллельно:**
- implementer → fix → re-review (зависимые)
- migration runner → tests reading DB (depends on schema)
- task N+1 если N+1 imports N's code

## Read-tool guard

- Unknown file → `wc -c` first
- > 50KB → Grep + offset Read (никогда полный Read)
