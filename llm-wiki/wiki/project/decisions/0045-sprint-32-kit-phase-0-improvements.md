---
title: ADR 0045 — Sprint 32 Kit Improvement Phase 0 (P0 staleness fixes + 5 skill mappings + cascade smart-explore + Phase 9 consolidate-memory)
type: decision
tags: [adr, sprint-32, kit-improvement, phase-0, p0-fixes, skill-mappings, cascade-step-2-5, consolidate-memory, ku-driven]
created: 2026-04-26
updated: 2026-04-27
status: accepted
sources:
  - project/plans/2026-04-26-sprint-32-kit-phase-0-improvements.md
  - project/decisions/0044-sprint-31-kit-revision-best-practices.md
  - project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md
  - project/SPRINT_STATE.md
  - project/architecture/current-state.md
  - project/architecture/sprint-flow-ru.md
  - project/architecture/kit-overview-ru.md
---

# ADR 0045 — Sprint 32 Kit Improvement Phase 0

## Статус

Accepted (2026-04-27) — implemented in S32 (`feature/sprint-32-kit-phase-0-improvements` → tag `v0.1.0-alpha.32`).

## Контекст

Post-S31 ship operator-driven review session (2026-04-26) выявил:

**P0 staleness (документация рассинхронизирована):**
1. `SPRINT_STATE.md` "Текущий статус" + "Последний спринт" + "Следующее действие" sections устарели на 4 спринта (S27 → S31 reality). "Следующее действие" = "S27 PHASE 8 ship" при S31 between-sprints. Counts: 30 ADRs / 17 sprint pages → реальные 44 ADRs / 31 sprint pages.
2. `current-state.md` title + H1 + TL;DR = "post-S25" при реальном S31. Test counts: 604 vs реальные 762. Frontmatter sources/tags не обновлены с S25.

**Cost of staleness:**
- Каждая сессия: orient phase читает stale state → 1-2 turn confusion → ~800-1500 токенов / сессия
- 5-8 сессий/спринт × 1000 токенов = 4000-12000 токенов/спринт wasted
- HARD-GATE risk: phase-advance.sh / sprint-flow-check.sh могут validate против stale counts

**Ecosystem audit gaps (КУ analysis):**
- 13 из 21 agent-skills не mapped в kit flow
- `claude-mem:smart-explore` exists но never в cascade rule
- `anthropic-skills:consolidate-memory` exists но never в Phase 9
- 5 high-ROI skill additions с avg КУ=57% remained unintegrated

**Trading work blocked:** ESC-1/2/3 pending operator → S32 trading slot занимаем kit work.

## Варианты

**Option A: Single big sprint covering Phase 0+1+2 (CI + SQLite MCP + skill additions)**
- Pros: всё сразу
- Cons: скоп слишком большой; CI setup требует новый dependency stack; risk regression

**Option B: Phased rollout — Phase 0 docs only сначала, Phase 1 (CI/MCP) отдельный sprint S33+**
- Pros: minimal risk; high ROI per минута (КУ avg 57% за 45 мин); leaves S33 capacity для CI setup; docs sprint pattern доказан S28-S31
- Cons: improvements распределены across multiple sprints

**Option C: Skip kit work, force operator на ESC-1/2/3 decision NOW**
- Pros: unblocks trading work
- Cons: ignores P0 staleness (compounds each session); operator decision pre-mature без kit Phase 0 in place

## Решение

**Option B selected.** Sprint 32 = Kit Phase 0 = doc-only sprint covering 6 changes:

| # | Change | Impact |
|---|--------|--------|
| T1 | SPRINT_STATE.md P0 fix | Stops orient confusion (~4-12K tokens/sprint saved) |
| T2 | current-state.md P0 fix | Correct canonical counts in HARD-GATEs |
| T3 | +5 skill mappings sprint-flow-ru.md (idea-refine / spec-driven / source-driven / code-simplification / documentation-and-adrs) | Fills explicit gaps в Phase 2/3/4/6/8 |
| T4 | Cascade smart-explore STEP 2.5 (sprint-flow + kit-overview mirror) | Token-optimized structural code lookup (-30-50% vs naked grep+read) |
| T5 | Phase 9 consolidate-memory step (every 5 sprints OR >30 observations) | Cross-session knowledge retention |
| T6 | ADR 0045 + sprint-32 page + index sync + counts 44→45 / 31→32 | Wiki consistency per kit rules |

**No code changes.** No pytest impact (762 baseline preserved by construction).

### КУ rationale

Pre-decision analysis showed:
- Phase 0 КУ avg = 57% / time = 45 мин = **114 КУ/час** (best ROI per phase)
- Phase 1 (CI + SQLite MCP + freshness hook + dashboard-reviewer) = 63% КУ avg / 6 часов = **10.5 КУ/час** (separate sprint S33)
- Phase 2-3 = lower ROI, defer

### Skills × Phase map updated

After S32 update: **32 skills mapped** к kit flow (was 26). Distribution:
- 13 superpowers (unchanged)
- 5 project (unchanged)
- 13 agent-skills (was 8, +5 from this ADR)
- 1 anthropic-skills (consolidate-memory, NEW)

## Последствия

### Positive

1. **Token economy:** −15% per session estimated (P0 staleness fixed + smart-explore replaces grep+read sequences для structural lookups)
2. **Skill coverage:** 8 → 13 agent-skills mapped (62% → 100% of relevant AS catalog)
3. **Kit consistency:** Cascade rule = 5-step (был 4-step), explicit для structural vs text-match queries
4. **Memory hygiene:** Phase 9 HARD-GATE для consolidation prevents corpus bloat (currently 17 observations, ceiling ~30 before noise)
5. **Decision capture:** ADR creation per sprint = explicit step (was ad-hoc — risk of forgetting context)
6. **Bybit/API correctness:** source-driven-development в Phase 4 prevents S8a/S8b-class regressions при touching `src/execution/bybit/`

### Negative

1. **Skill discovery overhead:** 32 skills mapped → operator должен знать decision matrix. Mitigated через kit-overview-ru.md decision matrix (single page).
2. **Phase 9 complexity:** added Step 5 (consolidate-memory) с conditional trigger. Mitigated через clear conditions (sprint % 5 == 0 OR observations > 30).
3. **Cascade depth:** STEP 2.5 added — теперь 5 steps. Mitigated через "когда STEP 2.5 vs STEP 3" decision text inline.

### Neutral

1. No code regression risk — documentation-only sprint
2. No HARD-GATE changes — existing hooks (sprint-flow-check / phase-advance / adr-agent-sync / adr-index-sync / wiki-broken-link / caveman) unchanged
3. No new agents added (Phase 1 deferred к S33 — dashboard-reviewer comes тогда)

## Реализация

Per plan `2026-04-26-sprint-32-kit-phase-0-improvements.md`:
- T1 → c095bd3
- T2 → 2ec9824
- T3 → e93e61c
- T4 → f1f60a7
- T5 → 660630e
- T6 → (this commit)

Tag: `v0.1.0-alpha.32`.

## Дальнейшие действия

**S33 candidate (Kit Phase 1):**
- GitHub Actions CI setup (`AS:ci-cd-and-automation` + `.github/workflows/ci.yml`)
- Pre-commit hooks (ruff + mypy via pre-commit framework)
- SQLite MCP server connection (debug execution state / fills / halts)
- SPRINT_STATE freshness check hook (block push если "Следующее действие" ссылается на N-2 spring)
- `dashboard-reviewer` L5 agent (FastAPI + vanilla JS specialist)

**S34+ candidate (Kit Phase 2):**
- Memory corpus organization (bridges 2-4 deferred from S30)
- Context budget hook (>70% warn)
- AS:performance-optimization / AS:api-and-interface-design / AS:browser-testing-with-devtools mappings
- Fetch/HTTP MCP

**Carry-overs preserved (S27 trading backlog):**
- ESC-1 Multi-symbol authorization
- ESC-2 "In profit" vs "pass acceptance criteria" semantics
- ESC-3 4H multi-symbol operational implications

## Связанные документы

- ADR 0017 (review-agent harness) — parent matrix
- ADR 0041 (S28 process enforcement) — sprint-flow-check hook precedent
- ADR 0042 (S29 superpowers integration) — skills × phase map original
- ADR 0043 (S30 tier-2 agents) — cascade rule original (4-step)
- ADR 0044 (S31 best practices revision) — direct predecessor + skill counts baseline (8 AS mapped)
- ADR 0045 (this) — Phase 0 KU-driven additions (8 → 13 AS mapped)
- Anthropic Claude Code best practices: https://docs.claude.com/en/code/best-practices
- Pre-S32 КУ analysis: session 2026-04-26 chapter "Kit improvement plan — КУ analysis"
