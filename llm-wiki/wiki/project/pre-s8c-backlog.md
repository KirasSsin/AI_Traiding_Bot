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

## Closed (archive section)

(empty — first iteration)
