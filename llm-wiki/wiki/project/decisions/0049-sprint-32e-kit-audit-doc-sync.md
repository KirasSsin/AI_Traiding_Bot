---
title: ADR 0049 — Sprint 32e Kit Audit + Doc Sync (post-S32 series review)
type: decision
tags: [adr, sprint-32e, kit-audit, doc-sync, retrospective, file-split]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/plans/2026-04-27-sprint-32e-kit-audit-doc-sync.md
  - project/decisions/0048-sprint-32d-kit-phase-3-improvements.md
  - project/architecture/kit-audit-2026-04-27.md
  - project/architecture/kit-overview-ru.md
  - project/architecture/tooling-inventory-ru.md
---

# ADR 0049 — Sprint 32e Kit Audit + Doc Sync

## Status

Accepted (2026-04-27) — implemented in S32e (`feature/sprint-32e-kit-audit-doc-sync` → tag `v0.1.0-alpha.32e`). Sub-sprint S32 series **post-completion audit** (operator initiated после S32d ship).

## Context

Operator request: "проведём ревью кита, проверим всё ли используется, всё ли нужно если нет — почему, обновим документацию".

Pre-plan empirical analysis (этот session) revealed:

1. **Doc drift:** kit-overview-ru.md "Best practices applied" section stale counts (MCP=6 real 8 / Subagents=9 real 11)
2. **File size violation:** tooling-inventory-ru.md = 60140 bytes ≈ 58.7KB exceeds 50KB safe Read threshold per CLAUDE.md sec 9 BINDING
3. **All 11 reviewer agents NEEDED** — 5 dormant DORMANT/READY due process sprints S27-S32d не trigger code reviewers by design
4. **All hooks (7 push + 2 UPS + 1 SS) NEEDED** — verified active каждый push S32 series
5. **8/8 MCP needed** — 2 (computer-use + Claude_in_Chrome) not trading-relevant но built-in harmless overhead
6. **All 5 project skills + ~50 plugin skills NEEDED**

**Conclusion:** ZERO removals. Action items = doc updates only.

## Options

**Option A: Audit only (no doc changes)**
- Pros: Quick documentation snapshot
- Cons: Drift remains, file size violation persists, не addresses operator's "обновим документацию" request

**Option B: Audit + doc updates + file split**
- Pros: Comprehensive — captures findings + applies fixes + resolves size violation. КУ ~50% / ~2 hours.
- Cons: 5 doc files touched

**Option C: Audit + remove "unused" components**
- Pros: Clean kit
- Cons: ❌ WRONG — empirical analysis показал ALL components NEEDED. Removing dormant agents = breaks future code sprints. Removing MCP не возможно (built-in).

## Decision

**Option B selected.** Sprint 32e = 5 changes:

| # | Change | Type | КУ % |
|---|--------|------|------|
| T1 | NEW kit-audit-2026-04-27.md (full audit findings) | Wiki design | 60% |
| T2 | Fix kit-overview-ru drift (Best practices section MCP 6→8 / Subagents 9→11) | Doc fix | 38% |
| T3 | Split tooling-inventory-ru.md (60KB → part 1 41KB + part 2 24KB) | File restructure | 70% |
| T4 | Update llm-wiki/CLAUDE.md (tooling-inventory split references + size example) | Doc sync | 30% |
| T5 | ADR 0049 + sprint-32e page + index/counts (48→49 ADRs / 35→36 sprints + part-2 file + audit doc) | Wiki sync | 42% |

**КУ avg ~48%** / ~2 hours (matches forecast).

### Audit findings highlights

- **11 reviewer agents:** 1 ACTIVE (trader-expert) + 10 DORMANT/READY (всё normal — process sprints S27-S32d, validation at S33+ trading)
- **10 hooks total** (7 push + 2 UPS + 1 SS): all ACTIVE. No removals.
- **8 MCP:** 6 active или ready, 2 (computer-use + Claude_in_Chrome) not trading-relevant but harmless. No removals.
- **5 project skills:** 3 ACTIVE every-sprint, 2 DORMANT/EXPLICIT — все NEEDED.
- **~50 plugin skills:** all heavily used или auto-loaded. NO removals.

### File split rationale (T3)

CLAUDE.md sec 9 BINDING: "Wiki-страницы должны оставаться < 50KB. Если близко — `<topic>.md` index + `<topic>-part-N.md`."

Pre-S32e: tooling-inventory-ru.md = 58.7KB (violation).

S32e split:
- `tooling-inventory-ru.md` (NOW 41KB): TL;DR + decision matrix + Sections 1-13
- `tooling-inventory-ru-part-2.md` (NEW 24KB): Sections 14-24

Both files < 50KB ✓. Operator + Claude can `Read` каждый file без offset/limit hacks.

### Why audit page (T1) и не just commit findings к existing doc?

Audit = snapshot in time (2026-04-27 post-S32 series). Future audits get separate dated files (kit-audit-YYYY-MM-DD.md pattern) для historical comparison. Не overwrite past findings.

## Consequences

### Positive

1. **Doc drift resolved** — kit-overview Best practices section now accurate (MCP 8 / Subagents 11)
2. **File size violation resolved** — tooling-inventory split, both parts < 50KB
3. **Audit snapshot committed** — kit-audit-2026-04-27.md provides reference для future kit work decisions
4. **Honest "all needed" finding** — prevents premature removal of dormant agents (which would break S33+ trading work)
5. **Pattern established** — future audits = NEW dated audit page (не overwrite)
6. **CLAUDE.md updated** — references current state (tooling split + audit page + 11 agents + 36 skills)

### Negative

1. **Cross-references к Section 14+ now require part-2 file path** — TOC link added к part-1 mitigates
2. **Audit valid only при snapshot date** — re-audit needed после future kit changes (likely S40+)
3. **No actual kit pruning** — operator wanted "проверим всё ли нужно" implying possible removals; honest answer = no removals justified

### Neutral

1. No code regression risk — config + docs only sprint
2. No FSM / reason codes / canonical state changes (16/30/74/45 unchanged)
3. Pattern continues S28-S32d (9-th consecutive non-trading sprint) — S32 series extends к S32e
4. CI infrastructure (S32b) validates 4th PR (S32e)

## Implementation

Per plan `2026-04-27-sprint-32e-kit-audit-doc-sync.md`:
- T1 → af3991e (kit-audit-2026-04-27.md NEW)
- T2 → cf293c7 (kit-overview-ru drift fix)
- T3 → d5d6773 (tooling-inventory split)
- T4 → e7d7e09 (llm-wiki/CLAUDE.md update)
- T5 → (this commit)

Tag: `v0.1.0-alpha.32e`.

## Follow-ups

**S33 trading sprint preparation (operator action — same as ADR 0048):**
1. Approve `fetch` MCP at next session start (one-time prompt)
2. Decide ESC-1/2/3 (multi-symbol / "in profit" / 4H operational)
3. Brainstorm S33 scope (8 candidates per ADR 0048)

**Test debt (carry-over к first trading sprint):**
- 3 pytest failures (test_replay_long_only / test_replay_next_open)
- 1 mypy error (__main__.py:636 bars_per_year_map redef)
- ~169 ruff baseline cleanup

**Trading carry-overs (BLOCKED — operator):**
- ESC-1 / ESC-2 / ESC-3

**Kit work future (low priority — per audit recommendation):**
- Re-audit при S40+ (likely after corpus > 100 obs)
- bybit-api-reviewer first real-world validation at S33+ Bybit-touching sprint
- Bridge 4 corpus partition implementation — only if corpus precision degrades

**Doc maintenance:**
- development-workflow.md status decision (operator) — possibly superseded by sprint-flow-ru.md
- Future audit dated pages (kit-audit-YYYY-MM-DD.md pattern)

## Related

- ADR 0017 (review-agent harness) — L5 agent matrix (11 agents)
- ADR 0044 (S31 best practices) — kit baseline
- ADR 0045/0046/0047/0048 (S32 Phase 0/1/2/3) — direct predecessors
- ADR 0049 (this) — Kit audit + doc sync
- Sprint S32 / S32b / S32c / S32d / S32e (this) — S32 series Phase 0/1/2/3 + audit
- [[../architecture/kit-audit-2026-04-27]] — full audit findings (этот sprint deliverable)
- [[../architecture/tooling-inventory-ru]] — Part 1 (post-split)
- [[../architecture/tooling-inventory-ru-part-2]] — Part 2 (NEW S32e)
- CLAUDE.md sec 9 — Read tool guard 50KB threshold (triggers split)
