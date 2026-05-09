---
title: 0044. Sprint 31 — Kit Revision per Anthropic Best Practices + Single Tools-Overview File (kit-overview-ru.md)
type: decision
date: 2026-04-26
sprint: 31
tags: [adr, sprint-31, kit-revision, best-practices, kit-overview, claude-md-prune, ru]
sources:
  - project/architecture/kit-overview-ru.md
  - project/architecture/tooling-inventory-ru.md
  - project/architecture/sprint-flow-ru.md
  - project/decisions/0017-review-agent-harness.md
  - project/decisions/0041-sprint-28-process-enforcement.md
  - project/decisions/0042-sprint-29-superpowers-integration.md
  - project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md
  - https://docs.claude.com/en/code/best-practices
status: accepted
---

# 0044. Sprint 31 — Kit Revision per Best Practices

**Status:** accepted
**Date:** 2026-04-26

## Контекст

Operator directive 2026-04-26 после S30 ship:

> "Все наши используемые инструменты (Все настройки нашего кита) укажем в одном файле. А также проведи по ним ревизию, на основе лучших твоих практик [Anthropic Claude Code best practices URL provided]."
>
> "А также загляни к себе во внутреннюю кодовую базу и используемые инструменты, и адаптируй наш кит под максимальное качество и в тоже время экономию токенов без деградации результата. Ожидаемый результат — увеличение производительности."
>
> "Если нужно вносить правки в глобальные настройки или настройки проекта, учитывай что мы CLAUDE.md делили на файлы."

### Pre-S31 baseline

| Metric | Value | Status |
|--------|-------|--------|
| CLAUDE.md (repo) | 190 lines / 14 KB | OK |
| llm-wiki/CLAUDE.md | 448 lines / 27 KB | **BLOATED** |
| ~/.claude/CLAUDE.md | 316 lines / 20 KB | BORDERLINE |
| **Total per-session load** | **954 lines / 61 KB / ~18.5K tokens** | **Над best practices threshold** |

Per best practices: "Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"

### Best practices gap analysis

20 best practices reviewed против current kit. Gaps identified:
- ❌ CLAUDE.md prune не сделан
- ❌ Auto mode permissions не documented
- ❌ Sandboxing не documented
- ❌ Plugin curation no inventory
- ❌ `/btw` для side questions не documented
- ❌ `/rewind` checkpoints не documented
- ❌ `--continue` / `--resume` не documented
- ❌ Non-interactive `claude -p` не documented
- ❌ Fan-out parallel sessions не used
- ❌ Status line (`/statusline`) не configured
- ❌ CLI tools (gh / git / pytest etc) не documented explicit
- ❌ Single tools-overview file отсутствует

## Решения

### Decision 1: Create kit-overview-ru.md (single source of truth)

**Rationale:** Operator wants "все инструменты в одном файле". Не replacement для existing docs (sprint-flow-ru.md / tooling-inventory-ru.md) — gateway entry-point с TL;DR + links к detail.

**Content:**
- Quick decision matrix ("что invoke когда")
- 9 reviewer agents (model + role)
- 6 active hooks
- 5 project skills + ~50 plugin skills (4 plugins)
- 6 MCP servers
- Critical files navigation
- Top 10 commands
- Top 5 anti-patterns
- 9-phase sprint lifecycle
- 20 best practices applied
- Sprint history last 10

### Decision 2: Expand tooling-inventory-ru.md sections 14-19

**Rationale:** Operator wants best practices revision. 6 NEW sections cover gaps:
- **Section 14** Permission modes (default / auto / acceptEdits / dontAsk / bypassPermissions / plan) + sandboxing + allowlists
- **Section 15** Plugin curation (4 active plugins с versions + install commands)
- **Section 16** CLI tools explicit list (gh / git / pytest / mypy / ruff / bash -n) + trading-specific scripts + discovery pattern
- **Section 17** Status line + context tracking (`/statusline`)
- **Section 18** Token-saver commands (`/btw` / `/rewind` / `/clear` / `/compact` / `--continue`) с discipline + anti-patterns
- **Section 19** Non-interactive mode (`claude -p`) + fan-out patterns + `--allowedTools` + parallel sessions Writer/Reviewer

### Decision 3: PRUNE all 3 CLAUDE.md files

**Rationale:** Per best practices "for each line ask: would removing cause Claude to make mistakes?" Bloated CLAUDE.md = ignored rules.

**Method:** Extract verbose explanations к wiki pages (kit-overview-ru.md / tooling-inventory-ru.md). Preserve critical content (operational rules, anti-patterns).

**Results:**

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| `CLAUDE.md` (repo) | 190 / 14 KB | 212 / 15 KB | +12 lines (+kit-overview links + S31 anti-patterns) |
| `llm-wiki/CLAUDE.md` | 448 / 27 KB | 291 / 13 KB | **-35% lines, -52% bytes** |
| `~/.claude/CLAUDE.md` | 316 / 20 KB | 253 / 17 KB | **-20% lines, -15% bytes** |
| **TOTAL** | **954 / 61 KB / ~18.5K tokens** | **756 / 46 KB / ~14K tokens** | **-21% lines, -25% tokens** |

**Tokens saved per session:** ~4,500 (× N sessions = significant compounding savings)

### Decision 4: Add 4 NEW anti-patterns + token-saver commands table к repo CLAUDE.md

**Rationale:** Best practices common failure patterns:
- Kitchen-sink session (long context + irrelevant accumulation)
- Side question в main thread (pollutes context)
- Correcting same issue 3+ times (cluttered с failed approaches)
- CLAUDE.md > 250 lines per file (bloated = ignored)

Token-saver commands table (8 commands) — quick reference inline в CLAUDE.md.

## Последствия

### Code / config changes

NONE in repo (process/wiki sprint).

Out-of-repo (`~/.claude/`):
- `~/.claude/CLAUDE.md` MODIFIED — pruned 316→253 lines

### Wiki changes (in-repo)

- `wiki/project/architecture/kit-overview-ru.md` NEW (single source of truth, ~300 lines)
- `wiki/project/architecture/tooling-inventory-ru.md` MODIFIED — Sections 14-19 NEW
- `llm-wiki/CLAUDE.md` PRUNED 448→291 lines (-35%)
- `CLAUDE.md` (repo) MODIFIED — kit-overview link + 4 NEW anti-patterns + token-saver table
- `wiki/project/decisions/0044-sprint-31-kit-revision-best-practices.md` NEW (this ADR)
- `wiki/project/sprints/sprint-31-kit-revision-best-practices.md` NEW
- `wiki/project/plans/2026-04-26-sprint-31-kit-revision-best-practices.md` NEW
- `wiki/index.md` MODIFIED — entries для S31 + ADR 0044
- `wiki/project/architecture/current-state.md` MODIFIED — sprint history row +S31 + canonical counts (43→44 ADRs, 30→31 sprint pages)
- `wiki/log.md` MODIFIED — sprint-end entry

### Backward compatibility

- All 6 existing reviewer agents preserved
- All 6 hooks preserved
- All 5 project skills preserved
- Existing CLAUDE.md split (3 files) preserved
- Existing wiki structure preserved
- Pruned content extracted к wiki pages (referenced via cross-links) — NOT lost

### Performance impact (expected)

- **Token economy:** -25% per session (~4,500 tokens saved)
- **Discoverability:** kit-overview-ru.md = 1-page entry vs scattered references
- **Quality:** less bloat → better adherence к rules per best practices
- **Skill invocation precision:** improved через decision matrix
- **Best practices coverage:** 20/20 documented (был 8/20)

### Carry-overs к S32+

S27 carry-overs (operator decision pending — BLOCKING trader-expert backlog):
- ESC-1 Multi-symbol authorization
- ESC-2 "In profit" vs "pass acceptance criteria"
- ESC-3 Operational implications 4H multi-symbol

S30 cascade bridges deferred:
- Bridge 2: wiki-mem-corpus-sync
- Bridge 3: chapter mark auto-link
- Bridge 4: frontmatter tags → corpus categorization

S31 carry-overs:
- Status line script automation (currently manual `/statusline`)
- Optional: `/skill-discover` slash command querying decision matrix
- Optional: enforce verification-before-completion checklist via hook (currently soft)
- Optional: dispatch-pattern detection (warn если sequential where parallel possible)

## Ссылки

- [[../architecture/kit-overview-ru]] — single source of truth (S31 NEW)
- [[../architecture/tooling-inventory-ru]] — full catalog (Sections 14-19 NEW S31)
- [[../architecture/sprint-flow-ru]] — обязательный 9-фаз процесс
- [[0017-review-agent-harness]] — review agents matrix policy
- [[0041-sprint-28-process-enforcement]] — process enforcement ADR
- [[0042-sprint-29-superpowers-integration]] — full superpowers integration
- [[0043-sprint-30-tier-2-agents-mem-wiki-merge]] — tier-2 agents + cascade
- [[../plans/2026-04-26-sprint-31-kit-revision-best-practices]] — S31 plan
- [[../sprints/sprint-31-kit-revision-best-practices]] — S31 page
- https://docs.claude.com/en/code/best-practices — Anthropic Claude Code best practices source
