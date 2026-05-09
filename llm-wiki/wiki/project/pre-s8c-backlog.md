---
title: Pre-S8c Backlog — gaps + bugs to discharge before brainstorm S8c
type: backlog
status: open
created: 2026-04-24
updated: 2026-04-24
sources:
  - project/SPRINT_STATE.md
  - project/log.md
---

# Pre-S8c Backlog

> Этот файл агрегирует все items, которые надо discharge'ить ДО старта PHASE 1 orient S8c.
> Основано на post-S8b audit (3 parallel Explore subagents + verification 2026-04-24).
> Закрыть → удалить файл (или archive в `wiki/project/archive/`).

## Bucket A — CRITICAL wiki gaps (single docs commit, 0 risk)

| # | Gap | Action | Verification |
|---|-----|--------|--------------|
| A1 | `coordinator.md` отсутствует (628 LoC, S7+S8a+S8b anchor) | Create `wiki/project/components/coordinator.md` — extract из state-machine.md + runtime-manager.md + ADR 0021/0022/0023. Обязательные секции: lifecycle, FSM dispatch (request_halt allow-list 3 codes), bootstrap idempotency, reconcile paths (4-valued verdicts), halt mechanics (γ primary-wins), arming TTL, RLock 6 protected mutation paths | `Read coordinator.md` + cross-link из state-machine.md + index.md entry |
| A2 | `sprint-08a-live-runtime.md` отсутствует | Create per `sprint-07-resilience.md` skeleton. Sources: ADR 0022 + plan + log.md lines 307-319 (S8a session-end) | wiki pattern compliance |
| A3 | `sprint-08b-carryover.md` отсутствует | Same skeleton. Sources: ADR 0023 + plan + log.md lines 358-382 (S8b ship section) | same |
| A4 | ADR 0022 НЕ в `index.md` (только 0023 на строке 120) | Add entry в `## Project — Decisions` секции между 0021 и 0023 | Grep 0022 в index.md returns hit |
| A5 | Tags `v0.1.0-alpha.4` + `alpha.5` missing in git, sprint-04/05 pages заявляют "pending PR merge" | Edit S4/S5 sprint pages frontmatter `tag:` → "(skipped, merged into alpha.6)". Add note в body про tag drift | `git tag --list` + sprint pages reconciled |

**Estimate:** 30-45 min. Single commit `docs(wiki): backfill S8a/S8b sprint pages + coordinator.md + ADR 0022 index + alpha tag drift`. Push → main без PR (0-risk docs).

### Bucket A+ — Additional findings from trader-expert cross-doc audit (2026-04-24)

| # | Gap | Action | Priority |
|---|-----|--------|----------|
| A6 | ADR 0023 `sources:` frontmatter cites `coordinator.md` (line 10) — broken reference (page doesn't exist) | Unblocked by A1 completion — automatic fix | HIGH (chain-dep) |
| A7 | ADR 0021 body links только к plan, NO sprint page back-link | Add `**Sprint page:** [[../sprints/sprint-07-resilience]]` в ADR 0021 References section | HIGH |
| A8 | ADR 0022 body — NO plan ref + NO sprint page ref (оба missing) | Add both links в ADR 0022 References (once sprint page exists — A2) | HIGH |
| A9 | ADR 0023 — add plan + sprint page links (after A3) | Same pattern | HIGH |
| A10 | ADR 0018 References — NO `[[../sprints/sprint-04-risk]]` back-link (sprint → ADR present, reverse missing) | Add one-line в ADR 0018 References | MEDIUM |
| A11 | ADR 0017 frontmatter `sources: []` empty + sprint-03 does NOT reference 0017 (both directions missing) | Add `sources: [project/sprints/sprint-03-strategy-port]` в ADR 0017. Add `[[../decisions/0017-review-agent-harness]]` в sprint-03 Related | MEDIUM |
| A12 | `EXIT_RECONCILE_DETECTED` categorization drift — source `reason_codes.py:87` places в ADR 0021 block (comment says "# Scale / exits (10)"), wiki `reason-codes.md` says "### Scale / exits (11)" | Either move enum entry в Scale/exits block + update comment `(11)`, ИЛИ add clarifying note в wiki. Arithmetic still reaches 45 — low impact but audit risk | MEDIUM |
| A13 | 5 component pages mention "coordinator" by name но Related section НЕ links (state-machine.md, reconciler.md, oco.md, runtime-manager.md, ws-private-consumer.md) | Add `[[coordinator]]` в Related section каждой. Unblocked by A1 | MEDIUM (chain-dep) |
| A14 | `sprint-04-risk.md` mentions 3 sub-plan files by name но не links (parent → children missing) | Add `[[../plans/2026-04-23-sprint-4-risk-tasks-1-8]]` + -9-13 + -14-17 | LOW |

**Updated Estimate:** 45-60 min. Same commit as Bucket A.

## Bucket B — User-reported bugs (TBD)

User flagged "пара багов" 2026-04-24. Awaiting specifics. Когда поступят — добавить как B1, B2, ... + classification (HIGH/MEDIUM) + sprint scope decision (pre-S8c batch vs S8c task).

- [ ] **B1** TBD (waiting user input)
- [ ] **B2** TBD (waiting user input)

## Bucket DRIFT — Doc/wiki staleness (deeper investigation 2026-04-24)

Found на 2-м проходе после user's "ты должен найти такие места" challenge. CRITICAL category — wiki dev'aет stale facts → trader gets stale verdicts → bad sprint decisions.

| # | Drift | Evidence | Fix | Priority |
|---|-------|----------|-----|----------|
| D1 | `wiki/project/architecture/current-state.md` frozen 2026-04-19 — описывает PRE-S1 legacy codebase (`src/core/`, `controller.py` top-level — давно удалены). 9 спринтов never reflected | Frontmatter `updated: 2026-04-19`. Body lists modules не существующие в HEAD | Either rewrite to reflect post-S8b state OR archive (`status: superseded`) + create new `current-state-v0.1-alpha.8b.md`. **Recommend rewrite + add to PHASE 8 mandatory update list** | CRITICAL |
| D2 | `~/.claude/agents/trader-expert.md` line 8 hardcoded "29 events / 59 transitions / 42 reason codes" stale by 2 sprints. Real = 74 / 45. Trader делает domain decisions на stale facts | Direct read | Replace hardcoded numbers with reference: "current state (see `wiki/project/architecture/current-state.md` for live counts; FSM total grows per ADRs 0019-0023)". Lazy-load pattern | CRITICAL |
| D3 | `wiki/project/components/execution-state-machine.md` TL;DR "59 пар, S7 после dedup" — real 74 | Direct read line 13 | Update TL;DR + amend "Last sync" footer | HIGH |
| D4 | Reason codes count drift — нет canonical statement. Chain через ADR 0019→0020→0021→0022 to find live value | grep `wiki/` for "reason codes" returns 6 different counts (31, 39, 42, 44, 45) in different files | Create `wiki/project/architecture/canonical-counts.md` ИЛИ extend `current-state.md` с table: { FSM states / events / transitions / reason codes } + "Last update: ADR XXXX". All other wiki refs → link there | HIGH |
| D5 | `sprints/README.md` template line 35 "Sprint N → v0.1.0-alpha.N" — S4/S5 broke pattern (no tags), README не упоминает exception | Read README.md | Add exception note: "S4/S5 — tags skipped, merged into alpha.6 (см. backlog A5 / sprint pages)" | LOW |

**Estimate D1-D5:** +60 min (D1 = 30 min rewrite, D2 = 5 min, D3 = 5 min, D4 = 15 min, D5 = 5 min). Combine with Bucket A batch.

### Pattern (для kit update)

- **CANONICAL counts source:** `current-state.md` (или dedicated `canonical-counts.md`) держит single source of truth для FSM/reason codes/components counts.
- **All other wiki refs** должны link там, NOT inline number. Если number встречается inline где-то — это drift по умолчанию.
- **PHASE 8 step 5 HARD-GATE** должен включать: "Update `current-state.md` if FSM/reason codes/components numbers changed this sprint."
- **trader-expert.md** не hardcode numbers — он Reads `current-state.md` per Sprint context priming. Numbers automatically fresh.

## Bucket C — Process improvements (kit updates, applied inline)

Чтобы будущих спринтах gaps не повторялись — обновлены 2026-04-24:

- [x] **C1** PHASE 8 finishing — mandatory checkpoint "Create sprint-NN.md before tag push" (см. dev-workflow.md Phase 8)
- [x] **C2** PHASE 8 finishing — mandatory checkpoint "Add new ADRs to index.md before tag push" (см. dev-workflow.md Phase 8)
- [x] **C3** Trader-expert prompt — "Sprint context priming" section listing canonical files to load on every dispatch (см. trader-expert.md)
- [x] **C4** Sprint summary doc canonical pattern documented в CLAUDE.md (sprint-NN.md = source of truth для "что было в спринте N")
- [ ] **C5** Trace map mandatory section в `writing-plans` skill template (S5/S7/S8b планы missing — retro-add) — defer in S8c
- [ ] **C6** Pre-merge hook `adr-index-sync-check.sh` — block push если new ADR not in index.md (mirror `adr-agent-sync-check.sh`) — defer in S8c

## Bucket D — S8c sprint scope candidates (after Bucket A done)

Cohesive theme = "Wiki backfill + tooling debt". Brainstorm в PHASE 2 S8c.

**Wiki (HIGH gaps):**
- `kill-switch-cli.md` (или extend `__main__.py` docs) — ADR 0022 sub-decision 5
- `risk-override.md` — security-critical 147 LoC
- `trade-history.md` — audit log 118 LoC
- `backtest-harness.md` (replay_engine + reporter + vector_backtest объединить, 535 LoC)
- `bracket.py` decision — deprecate marker ИЛИ delete (нужен trader-expert verdict)

**Code carry-overs S8a/S8b:**
- `_set_halt(reason: str → ReasonCode)` cleanup
- ADR 0022 narrative count amend (73 → 74) per S8b T7 fix-up
- Pre-existing test_config.py env-pollution fix (3 failures)
- Pre-existing test_risk_flow OverrideStore signature drift
- Pre-existing mypy 44 errors (coordinator.py LocalState undef, storage.py/gaps.py untyped pyarrow, reconciler.py None union-attr)

**Process (Bucket C deferred):**
- C5 trace map retro-add для S5/S7/S8b
- C6 ADR↔index sync hook
- Sprint 4 parent index — add child-table

## S8c PHASE 2 brainstorming — trader-expert verdicts (2026-04-25)

ROUND 1 dispatch (3 design questions Q1/Q2/Q3) + ROUND 2 dispatch on Q1 disagreement (per binding PHASE 2 protocol).

### Q1 — `src/execution/bracket.py` disposition

- **ROUND 1 maintainer:** DELETE (orphan)
- **ROUND 1 trader:** REVISE — KEEP+RELABEL. Evidence: 4 test files import (test_bracket_builder, test_bracket_fee_aware_qty, test_bracket_lifecycle_invariants, test_demo_bracket_happy_path).
- **Maintainer verification:** confirms 4 tests + ALSO `src/execution/coordinator.py:19` production import (`BracketParams, build_bracket, make_order_link_id`) — DELETE = startup ModuleNotFoundError = production outage.
- **ROUND 2 trader (BINDING):** CONFIRM_REVISE. KEEP `bracket.py` as-is (active ADR 0020 implementation). Plot twist: `src/execution/oco.py` is the actual S5-era ADR 0019 sub-decision 1 orphan candidate.
- **ROUND 2 maintainer follow-up verification (CC1 lesson):** trader's "oco.py zero test imports" CLAIM IS WRONG — `tests/unit/test_oco.py:3` imports `build_oco_order, OcoParams, OcoOrder`. Trader's research incomplete (Read oco.py content but didn't grep test imports).
- **Final accepted decisions:**
  - **bracket.py:** KEEP (binding ROUND 2 verdict, solid evidence). No new wiki page (oco.md lines 13-83 already document bracket.py correctly).
  - **current-state.md label fix:** `bracket (legacy 100)` → `bracket (oco-builder, ADR 0020 sub-decision 2, 101 LoC)`.
  - **oco.py:** Q4 dispatched + LOCKED below.

### Q4 — `src/execution/oco.py` disposition (ROUND 1, CONFIRM verdict)

- **ROUND 1 maintainer:** DELETE both `oco.py` + `tests/unit/test_oco.py` (2 files)
- **ROUND 1 trader (BINDING):** CONFIRM with scope expansion — DELETE **3 files** (third caught via CC1 grep — maintainer missed):
  1. `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/src/execution/oco.py` (55 LoC)
  2. `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/unit/test_oco.py`
  3. `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/integration/test_execution_oco_testnet.py` — already `pytest.mark.skip` permanently at line 27 ("ADR 0020 sub-decision 1: native tpsl path removed; superseded by Coordinator bracket")
- **Maintainer verification:** `ls + head` confirmed file exists + skip mark verified at line 27. Trader's claim solid.
- **No hidden coupling found:** `bracket.py` имеет полностью independent API (BracketParams/BracketLegs/build_bracket/compute_oco_qty), zero re-exports / shared symbols / shared helpers с oco.py.
- **Wiki follow-up:** ADR 0019 wiki page Consequences section — add one-line note "sub-decision 1 implementation (`oco.py`) removed in S8c; git history preserved."
- **Final accepted decision:** DELETE 3 files в S8c plan (single mechanical task, no further brainstorm).

### CC1 recursive lesson (process gap closure)

PHASE 8 step **5b NEW HARD-GATE** added в `dev-workflow.md` (commit pending in S8c plan):
- Orphan-audit grep MUST include `tests/` directory
- ANY orphan claim by ANYONE (controller OR subagent) MUST verify via grep before action
- Recursive — caught Q1 (bracket.py NOT orphan) AND Q4 expansion (3rd file `test_execution_oco_testnet.py` discovered)

### Q2 — Backtest harness wiki documentation scope

- **ROUND 1 maintainer:** SINGLE consolidated `backtest-harness.md`
- **ROUND 1 trader (BINDING):** CONFIRM. Single page covering 6 files. Add "S2-era reference, no active dev" marker. Document `replay.py` (8 LoC stub) under "Deferred / stubs" subsection. Add Open questions section noting deferred DSR + MC + WFA → S9+.
- **Final accepted decision:** Create `wiki/project/components/backtest-harness.md` per recommendation. Update `current-state.md` backtest row + index.md.

### Q3 — Kill-switch CLI documentation scope

- **ROUND 1 maintainer:** Dedicated `kill-switch-cli.md`
- **ROUND 1 trader (BINDING):** CONFIRM. Standalone operator-reference page. `runtime-manager.md` carries one-line "see also". `runbooks/halt-recovery.md` links from operator section. ADD: fold `__main__.py` "python -m src run/backfill/reconcile-only" entry-point wiring into kill-switch-cli.md "Commands" section (avoids 4th tiny page).
- **Final accepted decision:** Create `wiki/project/components/kill-switch-cli.md` covering kill-switch + all 4 CLI subcommands. Cross-link runtime-manager.md + halt-recovery.md.

### Cross-cutting concerns (ROUND 1 trader, both items applied)

- **CC1 — orphan-audit grep gap:** `grep -rn "from src.X" src/` MUST include `tests/` directory. Original Q1 audit miss = process-level gap. Fix: PHASE 8 hard-gate checklist update (см. development-workflow.md). **Already showed up in ROUND 2 too** — trader claimed oco.py orphan but missed `test_oco.py:3` import. CC1 applies recursively: every orphan claim MUST be verified by maintainer with `grep src/ tests/` before action.
- **CC2 — current-state.md label drift:** "bracket (legacy 100)" propagates as false prior into every future trader-expert dispatch. Fix in S8c plan.

### Items NOT requiring brainstorm (mechanical → straight в Bucket D plan)

- `risk-override.md` (147 LoC, security-critical wiki backfill)
- `trade-history.md` (118 LoC audit log wiki backfill)
- `_set_halt(reason: str → ReasonCode)` cleanup (S8a/S8b carry-over)
- ADR 0022 narrative count amend (73 → 74) + Context section S8b scope rewrite (Bucket E1+E2 batch)
- C5 — trace map mandatory + retro-add S5/S7/S8b plans
- C6 — `adr-index-sync-check.sh` hook (mirror `adr-agent-sync-check.sh`)
- pre-existing test_config.py env-pollution fix (3 failures)
- PHASE 8 checklist update — orphan-audit grep includes `tests/` (CC1)
- current-state.md `bracket` row label correction (CC2)

### Decision rationale (logged for ADR draft)

- Q1 binding: trader prevented DELETE catastrophe (production import + 4 tests). Round 2 surfaced even bigger evidence (coordinator.py:19) than ROUND 1.
- Iterative justify protocol working as designed: caught factual error в maintainer's recommendation that would have shipped без brainstorm.
- ROUND 2 trader's secondary claim (oco.py orphan) NOT auto-accepted because maintainer verified `test_oco.py:3` exists — supported evidence only, NOT silent verdict extension.

## Bucket E — Trader bonus findings (post-batch re-verify 2026-04-25)

Discovered by trader-expert during pre-S8c batch re-verification. Non-blocking, defer to S8c at next ADR 0022 amendment session.

| # | Gap | Action | Priority |
|---|-----|--------|----------|
| E1 | ADR 0022 Context section still describes original S8b scope (Analytics per-fill + execution topic + WS+REST epsilon-halt) — actual S8b was pivoted to carry-over fixes + ADR 0023 | Amend ADR 0022 Context при next touch (same session как E2 + ADR 0022 narrative count 73 → 74) | LOW |
| E2 | ADR 0022 narrative transition count = 73 (live = 74 after S8b T7 fix-up) | Amend at next ADR 0022 touch | LOW |

Both folded into single S8c amendment commit when ADR 0022 next requires touch.

## Bucket F — Wiki drift discovered during S8c execution (2026-04-25)

| # | Gap | Action | Priority |
|---|-----|--------|----------|
| F1 | `wiki/runbooks/halt-recovery.md` (also referenced as `wiki/project/runbooks/halt-recovery.md`) doesn't exist. Referenced from: `runtime-manager.md` Related section, `index.md`, plans S6/S7/S8c, T4 just added new ref в `kill-switch-cli.md`. S6 + S7 plans had tasks to create it — apparently never completed OR file was deleted. | Two paths: (a) Create halt-recovery.md per S6/S7 plan stubs (operator post-mortem procedures для всех HALT_* codes). Brainstorm scope first (SIGNIFICANT page, multi-section operator runbook). (b) Remove all dead refs across wiki (smaller but loses operator workflow doc). **Recommend (a)** — operator runbook = critical для production readiness. Defer to S9 (separate "operator readiness" sprint) ИЛИ extend S8c if scope allows. | HIGH |

Discovery story: T4 implementer (Q3 kill-switch-cli) попытался добавить cross-link к `runbooks/halt-recovery.md` — found dir missing. Root cause = previous sprints planned creation but execution dropped/skipped. Pattern лесон: PHASE 8 step 5 HARD-GATE should also verify all wiki cross-refs точки на existing files (broken-link audit). Будущий C7 candidate for next process improvement.

## Closed (archive section)

**Bucket A (5) + A+ (9) + DRIFT (5) = 19 items** — all DONE на ветке `feature/pre-s8c-wiki-backfill`, commit `72bfc97` (+ off-by-one fix follow-up). Trader-expert re-verification 2026-04-25: 11/11 + 5/5 bonus DRIFT items PASS. python-reviewer (A12 1-line src change): APPROVED.

## Связанные документы

- [[sprints/sprint-08c-wiki-backfill]] — Sprint 8c (wiki backfill + tooling debt)
