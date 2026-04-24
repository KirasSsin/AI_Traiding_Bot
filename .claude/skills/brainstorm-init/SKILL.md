---
name: brainstorm-init
description: Run PHASE 2 binding brainstorming protocol для AI Trading Bot v0.1 sprint scope decisions. Use proactively at sprint start with open scope/architecture questions OR when user says "брейнштурм", "brainstorm sprint scope", "design decision". Enforces structured questionnaire → trader-expert ROUND 1 → iterative justify ROUND 2 on REVISE-disagreement (CONFIRM_REVISE / CHANGED, BINDING, no round 3).
---

# Brainstorm Init — PHASE 2 binding protocol

## When to use

Project: AI Trading Bot v0.1. Triggers:
- New sprint начало с open scope/architecture questions
- Carry-over decisions от prior sprint требуют resolution
- User says "брейнштурм S<N>", "scope sprint", "design questions", "что решаем"
- Pre-S{N} backlog имеет Bucket B (user bugs) OR Bucket D (architectural decisions)

Skip если sprint = pure execution of approved ADR (no new decisions).

## Why binding protocol exists

Past violation S8b: maintainer asked user scope questions напрямую (без trader-expert ROUND 1) → quality miss. Past violation S8c Q1: maintainer DELETE bracket.py recommendation = catastrophic regression (production code, не orphan) — ROUND 2 trader-expert iterative justify caught it перед plan locked scope.

Per `dev-workflow.md` PHASE 2 step 3a-3f: ALL scope/architecture questions MUST go through trader-expert. User sees ONLY trader's escalation list (product/regulatory/business choices), не raw scope questions.

## Steps (imperative)

### Step 1: Collect open questions

Sources:
- Carry-overs из `pre-s{N-1}-backlog.md` Bucket B/D/E
- User explicit input
- Prior sprint open issues (sprint-{N-1}-*.md "Open issues" section)
- Methodology gaps (если cross-sprint)

### Step 2: Build structured questionnaire (per question)

Each question MUST have 5 fields:

```markdown
## Q<N> — <question topic>

**Question:** <verbatim text — точная формулировка>

**Maintainer recommended option:** <option A — твой выбор>

**Alternatives considered:**
- (a) <option> — pros/cons
- (b) <option> — pros/cons
- (c) <option> — pros/cons

**Reasoning for recommended:**
- <ссылка на wiki/ADR/код — why option A>
- <empirical evidence если есть>

**Risk/concern:**
- <что может сломаться если решение неверное>
- <hidden assumption>
```

Avoid обsolete questions (already decided в ADR) — verify mem-search первого:
```
mcp__plugin_claude-mem_mcp-search__smart_search "did we decide <topic>"
```

### Step 3: Dispatch trader-expert ROUND 1

```
Agent(subagent_type="trader-expert", prompt=<full questionnaire с context>)
```

Include в brief:
- Sprint context (SPRINT_STATE + log tail)
- Active ADR refs
- All N questions с 5-field structure
- Reference к dev-workflow.md PHASE 2 binding protocol

Trader returns per-question verdict: **CONFIRM** / **REVISE** / **DEFER** / **EXPAND** + cross-cutting concerns + escalation list для user.

### Step 4: Process verdicts

Per question:
- **CONFIRM** → option locked, идёт в ADR
- **REVISE (option == maintainer's recommendation, no disagreement)** → option locked + trader's rationale в ADR
- **REVISE (option != maintainer's recommendation)** → MUST go through Step 5 iterative justify loop
- **DEFER** → "Open questions → deferred to S{N+1}+" в ADR
- **EXPAND** → re-brainstorm на reframed question → возможен второй round 3a-3c

### Step 5: Iterative justify loop (на REVISE-disagreement, MANDATORY)

For each REVISE где chosen option != maintainer's recommendation:

```
Agent(subagent_type="trader-expert", prompt=<round 2 brief>)
```

ROUND 2 brief contains:
- Verbatim disputed question text
- ROUND 1 maintainer recommendation + reasoning
- ROUND 1 trader REVISE verdict (chosen option + rationale)
- Explicit prompt: "Re-evaluate. Why <X> over maintainer's <Y>? Perform deeper analysis: side-by-side compare <Y> vs <X>, fresh research, then return final verdict per Iterative justification protocol в твоём prompt."

Trader returns ONE of:
- **CONFIRM_REVISE** — round-1 stands. Provides:
  - Concrete risks в maintainer's <Y> (≥ 2 with citations)
  - Failure scenarios для <Y>
  - Why <X> wins
- **CHANGED** — new evidence flipped verdict. Provides:
  - Compare table (Y vs X vs Z if any)
  - Fresh research findings
  - New verdict (BINDING)

**ROUND 2 verdict BINDING. NO round 3.** Если maintainer still disagrees → escalate к user under "Open issues" с both rounds в evidence package.

### Step 6: Maintainer applies verdicts + persists trail

Document в `wiki/project/pre-s{N}-backlog.md` "S{N} PHASE 2 brainstorming" section:

Per question:
- ROUND 1 verdict
- ROUND 2 verdict (if invoked)
- Maintainer follow-up verification (если applies CC1 lesson — re-grep tests/ etc.)
- Final accepted decision
- Wiki/code follow-ups

### Step 7: User escalation (only if trader returned escalation list)

User sees ONLY:
- Trader's explicit escalation items (product/regulatory/business)
- Final verdict summary table (Q1/Q2/.../QN с CONFIRM_REVISE/CHANGED/CONFIRM)

Не показывай user raw round-1/2 trail — это noise. Synthesize.

### Step 8: ADR draft + transition к PHASE 3

```
Edit/Create wiki/project/decisions/NNNN-<slug>.md (status: proposed)
```

Each decision/sub-decision links к verdict trail. Update SPRINT_STATE: phase=2-brainstorming → 3-planning.

## Anti-patterns (НЕ делать)

- ❌ Asking user scope/architecture question directly БЕЗ trader-expert ROUND 1 (S8b violation)
- ❌ Accepting REVISE-disagreement без ROUND 2 iterative justify (S8b violation)
- ❌ Третий round trader (ROUND 2 BINDING)
- ❌ Skipping trader-expert потому что "очевидно" (Q1 ROUND 2 caught DELETE bracket.py = production catastrophe — "очевидное" было wrong)
- ❌ Дispatch trader без 5-field structured questionnaire (insufficient context = poor verdict)
- ❌ Silent extension of trader verdict beyond supported evidence (CC1 lesson — verify orphan claims via grep src/ tests/)

## Output to user

Brief acknowledgment:
- "PHASE 2 brainstorm started для S<N>"
- N questions collected
- Trader ROUND 1 dispatched
- (если applicable) ROUND 2 dispatched on Q<X>
- Final verdicts table
- Escalation items для user (если есть)

Не dump full trader output — persist в backlog + summarize.

## Related kit references

- Master SOP: `llm-wiki/wiki/project/architecture/development-workflow.md` PHASE 2 step 3a-3f
- Trader-expert prompt: `~/.claude/agents/trader-expert.md` (Iterative justification protocol section)
- Backlog pattern: `wiki/project/pre-s{N}-backlog.md`
- Binding protocol policy: `llm-wiki/CLAUDE.md` + repo `CLAUDE.md` "Brainstorming flow (PHASE 2) — BINDING protocol" section
- CC1 lesson (orphan-audit grep): PHASE 8 step 5b HARD-GATE
