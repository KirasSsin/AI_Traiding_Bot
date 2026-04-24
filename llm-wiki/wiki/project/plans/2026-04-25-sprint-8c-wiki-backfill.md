---
title: Sprint 8c — Wiki backfill + tooling debt + S8a/S8b carry-overs
type: plan
tags: [sprint-8c, plan, wiki, tooling, carry-over, hooks, methodology]
created: 2026-04-25
updated: 2026-04-25
status: completed
---

# Sprint 8c — Wiki backfill + tooling debt + S8a/S8b carry-overs

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discharge accumulated documentation debt + small code carry-overs from S8a/S8b + process hooks, before next feature sprint. Cohesive theme = "wiki backfill + tooling debt".

**Architecture:** docs-heavy batch с 1 file deletion (oco.py + 2 tests per Q4 binding verdict) + 1 type narrowing (`_set_halt(reason: ReasonCode)`) + 2 hook scripts + ADR amendments + 4 new wiki pages. No new features, no new ADRs (carry-over amendments only).

**Tech Stack:** Python 3.12, pytest, mypy --strict, ruff, structlog, bash hook scripts.

**Trace map (per Bucket C5 — mandatory section per writing-plans skill template):**

| Spec / decision | Tasks |
|-----------------|-------|
| PHASE 2 Q1 verdict (KEEP bracket.py + relabel) | T2 (current-state.md label fix CC2) |
| PHASE 2 Q2 verdict (single backtest-harness.md) | T3 |
| PHASE 2 Q3 verdict (kill-switch-cli.md + CLI commands) | T4 |
| PHASE 2 Q4 verdict (DELETE oco.py + 2 tests) | T1 |
| Bucket D wiki HIGH gaps | T5 (risk-override.md), T6 (trade-history.md) |
| Bucket D code carry-overs | T7 (`_set_halt(ReasonCode)`), T8 (test_config env-pollution fix) |
| Bucket E1+E2 ADR 0022 amend | T9 (transition count 73→74 + Context section S8b scope rewrite) |
| Bucket C5 (trace map mandatory) | T10 (writing-plans skill template + retro-add S5/S7/S8b plans) |
| Bucket C6 (`adr-index-sync-check.sh` hook) | T11 |
| Cross-cutting CC1 (orphan-audit) | already in PHASE 2 commit `3c979b9` (dev-workflow.md step 5b) — no task |
| Final HARD-GATE step 5+5a+6 | T12 (sprint-NN.md + index.md sync + canonical counts) |

---

## Task list

### Task 1 — DELETE oco.py + 2 tests (Q4 verdict)

**Files:**
- Delete: `src/execution/oco.py`
- Delete: `tests/unit/test_oco.py`
- Delete: `tests/integration/test_execution_oco_testnet.py`

- [ ] **Step 1: Verify zero callers (CC1 HARD-GATE re-application)**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
grep -rn "from src.execution.oco\|import oco\b\|src\.execution\.oco" src/ tests/ | grep -v "execution.oco_\|__pycache__\|\.pyc"
```

Expected output: only the 3 files we're deleting (oco.py self-refs + test_oco.py:3 + test_execution_oco_testnet.py:line). If anything else appears → STOP, escalate.

- [ ] **Step 2: Delete files via git rm**

```bash
git rm src/execution/oco.py tests/unit/test_oco.py tests/integration/test_execution_oco_testnet.py
```

- [ ] **Step 3: Verify pytest still passes (no regress, fewer tests)**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
```

Expected: 604-N passed (where N = tests deleted from test_oco.py); 0 new failures vs baseline.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(execution): remove ADR 0019 sub-decision 1 native-tpsl path (oco.py + 2 tests)

Per S8c PHASE 2 Q4 trader-expert verdict (CONFIRM with 3-file scope expansion).
ADR 0020 supersedes ADR 0019 sub-decision 1 (native tpslMode rejected for Spot V5).
bracket.py is the active 3-order Spot OCO emulation builder per ADR 0020 sub-decision 2.

Deletes:
- src/execution/oco.py (55 LoC, ADR 0019/1 implementation)
- tests/unit/test_oco.py (5 tests covering deleted code only)
- tests/integration/test_execution_oco_testnet.py (already pytest.mark.skip per ADR 0020)

git history preserves full content via 'git show <SHA>:src/execution/oco.py'."
```

---

### Task 2 — current-state.md bracket row label fix (CC2)

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/current-state.md`

- [ ] **Step 1: Locate bracket row in execution/ table**

Grep `bracket (legacy 100)` в `current-state.md` — should be в `## Структура src/` table.

- [ ] **Step 2: Edit row label**

Replace:
```
| `execution/` | coordinator (628), state_machine (170), state_repo (148), reconciler (278), oco, bracket (legacy 100), models, bybit/{adapter, ws_private, rest} | ~1500 |
```

With:
```
| `execution/` | coordinator (628), state_machine (170), state_repo (148), reconciler (278), bracket (oco-builder, ADR 0020 sub-decision 2, 101 LoC), models, bybit/{adapter, ws_private, rest} | ~1500 |
```

(Also drop `oco,` since we deleted it в T1.)

- [ ] **Step 3: Update component count в canonical-counts table**

If component pages count changed (we add backtest-harness + kill-switch-cli + risk-override + trade-history + bracket section в oco.md = +4 new pages), update "Component pages | **22**" → "**26**" with note in "Last update" column.

(Update will be applied iteratively as T3-T6 land.)

- [ ] **Step 4: Commit**

```bash
git commit -m "docs(wiki): current-state.md bracket row label fix (CC2 from S8c brainstorm)

bracket row labeled 'legacy 100' factually wrong per Q1 ROUND 2 verdict —
bracket.py is the ACTIVE ADR 0020 sub-decision 2 implementation, not legacy.
Drop oco from execution/ row (deleted в T1)."
```

---

### Task 3 — Create backtest-harness.md (Q2 verdict)

**Files:**
- Create: `llm-wiki/wiki/project/components/backtest-harness.md`
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (backtest row "(open gap — S8c)" → wiki link)

- [ ] **Step 1: Read backtest src/ files**

```bash
wc -l src/backtest/*.py
ls src/backtest/
```

- [ ] **Step 2: Write backtest-harness.md skeleton** per existing component pattern (see `bybit-adapter.md` for multi-file directory pattern).

Required sections:
- frontmatter (title, type=component, tags, created/updated, sources [all 6 .py files + ADR refs], status=stable)
- TL;DR (1 sentence) + "S2-era reference, no active dev S3-S8b" marker prominently
- 6 sub-sections (per Q2 verdict): Overview / Replay engine (largest) / Vector backtest (legacy WFA-ready) / Reporter (KPI + plots) / Indicators (pre-computed series) / Data collector (historical fetch) / Replay (stub, deferred)
- Open questions (deferred to S9+: DSR integration, MC permutation harness, WFA)
- Related (other components)
- Sources

- [ ] **Step 3: Add wiki/index.md entry**

Under `## Project — Components`:
```markdown
- [[project/components/backtest-harness]] — backtest pipeline: replay engine + vector backtest + reporter + indicators + data collector. S2-era reference, S9+ DSR/MC/WFA deferred.
```

- [ ] **Step 4: Update current-state.md backtest row**

Replace `(open gap — S8c)` → `[[../components/backtest-harness]]`.

- [ ] **Step 5: Commit**

```bash
git commit -m "docs(wiki): backtest-harness.md NEW (Q2 verdict — single page для 6 backtest files)"
```

---

### Task 4 — Create kill-switch-cli.md (Q3 verdict)

**Files:**
- Create: `llm-wiki/wiki/project/components/kill-switch-cli.md`
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/project/components/runtime-manager.md` (add cross-link)
- Modify: `llm-wiki/wiki/runbooks/halt-recovery.md` (add cross-link)
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (`__main__.py` row update)

- [ ] **Step 1: Read sources**

```bash
cat src/__main__.py
```

ADR refs: 0022 sub-decision 5 (sentinel-file CLI) + 0022 sub-decision 6 (entry-point) + 0023 (KILL_SWITCH_REQUESTED dispatch invariant) + S8b T4 (atomic write).

- [ ] **Step 2: Write kill-switch-cli.md skeleton**

Required sections:
- frontmatter (title, type=component, tags [cli, kill-switch, operator, sprint-8a, sprint-8b], sources [src/__main__.py, ADRs, S8b T4 commit])
- TL;DR (operator-facing CLI artifact)
- Commands subsection (per Q3 verdict — fold all 4 subcommands here):
  - `python -m src run` (RuntimeManager start, blocking)
  - `python -m src backfill --from --to`
  - `python -m src reconcile-only`
  - `python -m src kill` (sentinel write — main focus)
- `python -m src kill` deep dive: sentinel path (`Settings.runtime_kill_switch_path`), atomic write semantics (os.open + os.replace, S8b T4), RuntimeManager polling (each tick), FSM dispatch (KILL_SWITCH_REQUESTED → KILLED 11 transitions per ADR 0022)
- Recovery (operator manually deletes sentinel + restart)
- ADR references (0022 sub-decisions 5+6, 0023, S8b T4)
- Out of scope / deferred (SIGUSR1 deferred per ADR 0022, REST endpoint v0.2)
- Related (runtime-manager, halt-recovery, coordinator, execution-state-machine)

- [ ] **Step 3: Cross-link from runtime-manager.md "Kill-switch" subsection**

Add `[[kill-switch-cli]]` link в existing "### `python -m src kill`" subsection.

- [ ] **Step 4: Cross-link from runbooks/halt-recovery.md**

Append "see `[[../project/components/kill-switch-cli]]` for CLI semantics" в KILL_SWITCH_REQUESTED section.

- [ ] **Step 5: Add wiki/index.md entry**

```markdown
- [[project/components/kill-switch-cli]] — operator-facing CLI: kill (sentinel-file atomic write) + run + backfill + reconcile-only. ADR 0022 sub-decisions 5+6 + ADR 0023.
```

- [ ] **Step 6: Update current-state.md __main__.py row**

Replace `(open gap — S8c)` → `[[../components/kill-switch-cli]]`.

- [ ] **Step 7: Commit**

```bash
git commit -m "docs(wiki): kill-switch-cli.md NEW (Q3 verdict — dedicated operator-facing CLI page)"
```

---

### Task 5 — Create risk-override.md (Bucket D mechanical)

**Files:**
- Create: `llm-wiki/wiki/project/components/risk-override.md`
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (risk-override gap close)

- [ ] **Step 1: Read source**

```bash
cat src/risk/override.py
```

147 LoC, security-critical (HMAC-signed override file для CB resume).

- [ ] **Step 2: Write risk-override.md skeleton**

Sections: frontmatter (sprint-4 + sprint-7 tags, sources `src/risk/override.py` + `src/risk/resume_cb.py` + ADR 0018) + TL;DR (CbOverride file + HMAC signing + config_hash anti-replay) + API (CbOverride, OverrideStore) + File format (JSON layout) + HMAC signing semantics (key from settings, anti-replay via config_hash) + Atomic write pattern (os.open + os.replace + finally cleanup — same as kill-switch S8b T4) + CLI integration (`src/risk/resume_cb.py`) + Security considerations (key rotation, file permissions 0o600) + Related (kill-switch-cli, risk-manager) + Sources.

- [ ] **Step 3: index.md + current-state.md entries**

- [ ] **Step 4: Commit**

```bash
git commit -m "docs(wiki): risk-override.md NEW (Bucket D — security-critical 147 LoC backfill)"
```

---

### Task 6 — Create trade-history.md (Bucket D mechanical)

**Files:**
- Create: `llm-wiki/wiki/project/components/trade-history.md`
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (trade-history gap close)

- [ ] **Step 1: Read source**

```bash
cat src/risk/trade_history.py
```

118 LoC audit log (TradeHistoryRepository + TradeRecord, UNIQUE INDEX entry_signal_id, AwareDatetime).

- [ ] **Step 2: Write trade-history.md skeleton**

Sections: frontmatter + TL;DR (per-trade audit log с idempotent insert) + API (TradeHistoryRepository, TradeRecord) + Schema (`trade_history` table fields) + Idempotency (UNIQUE INDEX on entry_signal_id) + AwareDatetime contract + Reader patterns (audit queries) + Migration ref + Related (risk-manager, reconciler, reason-codes) + Sources.

- [ ] **Step 3: index.md + current-state.md entries**

- [ ] **Step 4: Commit**

```bash
git commit -m "docs(wiki): trade-history.md NEW (Bucket D — 118 LoC audit log backfill)"
```

---

### Task 7 — `_set_halt(reason: ReasonCode)` type narrow (S8a/S8b carry-over)

**Files:**
- Modify: `src/execution/coordinator.py` (`_set_halt` signature `reason: str` → `reason: ReasonCode`)
- Test: existing `tests/unit/test_coordinator_*.py` (no new test, signature compat verified by mypy)

- [ ] **Step 1: Read current signature**

```bash
grep -n "_set_halt" src/execution/coordinator.py
```

Current at line 569: `def _set_halt(self, *, reason: str, last_event: ExecutionEvent, extra: dict | None = None,)`.

- [ ] **Step 2: Run mypy baseline**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
mypy --strict src/ 2>&1 | tail -3
```

Expected: 44 errors baseline.

- [ ] **Step 3: Edit signature + verify call sites still type-check**

Change `reason: str` → `reason: ReasonCode`. Check ALL call sites pass ReasonCode (not raw str). Special case `result.halt_reason or "HALT_RECONCILE_DIVERGENCE"` (line 109) — `result.halt_reason` already typed as `ReasonCode | None` per S7 reconciler? OR str fallback? Verify, fix if drift.

- [ ] **Step 4: Run pytest + mypy**

```bash
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
mypy --strict src/ 2>&1 | tail -3
```

Expected: pytest 0 new fails. mypy ≤ 44 errors (T7 should not increase; ideally net -1 if narrows resolved any inferred Any).

- [ ] **Step 5: Commit**

```bash
git commit -m "fix(execution): _set_halt(reason: ReasonCode) — type narrow per S8b carry-over

Internal wrapper signature parity with public request_halt(reason: ReasonCode).
Closes S8a/S8b carry-over item (см. pre-s8c-backlog.md Bucket D)."
```

---

### Task 8 — Pre-existing test_config.py env-pollution fix

**Files:**
- Modify: `tests/unit/test_config.py` (3 failing tests — `test_missing_api_key_raises`, `test_missing_api_secret_raises`, `test_missing_hmac_key_raises`)

- [ ] **Step 1: Reproduce baseline failure**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/unit/test_config.py -v 2>&1 | tail -15
```

Expected: 3 fail (DID NOT RAISE ValidationError) — env pollution from `.env` overrides Settings construction.

- [ ] **Step 2: Identify fix pattern**

Issue: pydantic-settings reads `.env` even when test wants no env. Fix: use `monkeypatch.delenv("BYBIT_API_KEY", raising=False)` per missing field test, OR `Settings(_env_file=None)` to disable .env reading в test.

- [ ] **Step 3: Edit 3 failing tests**

Apply chosen pattern (recommend `monkeypatch.delenv` per test — explicit + isolated).

- [ ] **Step 4: Verify clean run**

```bash
pytest tests/unit/test_config.py -v 2>&1 | tail -5
```

Expected: all pass (no DID NOT RAISE).

- [ ] **Step 5: Commit**

```bash
git commit -m "fix(tests): test_config env-pollution via monkeypatch.delenv

Closes 3 pre-existing failures from .env interaction with pydantic-settings.
Carry-over from S8a (см. pre-s8c-backlog.md Bucket D)."
```

---

### Task 9 — ADR 0022 amendments (Bucket E1 + E2 batch)

**Files:**
- Modify: `llm-wiki/wiki/project/decisions/0022-sprint-8a-live-runtime.md`

- [ ] **Step 1: Locate transition count narrative**

```bash
grep -n "73\|transitions" llm-wiki/wiki/project/decisions/0022-sprint-8a-live-runtime.md | head -10
```

- [ ] **Step 2: Update count 73 → 74**

Replace narrative occurrences referencing `73 transitions` (S8a end-state count) with `74 (after S8b T7 fix-up adding (FLAT, RISK_HALT) — see ADR 0023)`.

- [ ] **Step 3: Update Context section S8b scope description**

Replace original S8b scope description ("Analytics per-fill table + execution topic subscription + WS+REST epsilon-halt consistency check") with corrected note: "S8b actually delivered S8a carry-over fixes + ADR 0023 halt-code mapping invariant — original analytics/epsilon-halt scope deferred to S9+."

- [ ] **Step 4: Add Amendment entry в References section**

```markdown
## Amendments

- 2026-04-25 (S8c): Transition count narrative updated 73 → 74 (S8b T7 fix-up). Context section S8b scope description corrected — actual S8b = carry-over + ADR 0023, not original analytics/epsilon-halt scope.
```

- [ ] **Step 5: Commit**

```bash
git commit -m "docs(adr-0022): amend transition count 73→74 + S8b actual scope correction (Bucket E1+E2)"
```

---

### Task 10 — Trace map mandatory section (Bucket C5)

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/development-workflow.md` (PHASE 3 step 1 update)
- Modify: `llm-wiki/wiki/project/plans/2026-04-23-sprint-5-execution.md` (retro-add)
- Modify: `llm-wiki/wiki/project/plans/2026-04-24-sprint-7-resilience.md` (retro-add)
- Modify: `llm-wiki/wiki/project/plans/2026-04-24-sprint-8b-carryover.md` (retro-add)

- [ ] **Step 1: Update dev-workflow.md PHASE 3**

Add binding requirement: "Plan MUST include 'trace map' section (sub-decision N → Tasks X,Y,Z) per writing-plans skill template. PHASE 3 plan review BLOCKS если missing."

- [ ] **Step 2-4: Retro-add trace map to S5/S7/S8b plans**

For each plan: read existing "Task Sequencing Rationale" / "Stage A-E" section, extract sub-decision → task mapping, add formal `## Trace map` section with table format matching this S8c plan.

- [ ] **Step 5: Commit (single batch)**

```bash
git commit -m "docs(methodology): trace map mandatory section in PHASE 3 + retro-add S5/S7/S8b plans (Bucket C5)"
```

---

### Task 11 — `adr-index-sync-check.sh` hook (Bucket C6)

**Files:**
- Create: `~/.claude/hooks/adr-index-sync-check.sh` (mirror `adr-agent-sync-check.sh` pattern)
- Modify: `~/.claude/settings.json` (register hook on `git push` PreToolUse)
- Create: `llm-wiki/wiki/project/components/adr-index-sync-hook.md` (component page mirror `adr-agent-sync-hook.md`)

- [ ] **Step 1: Read existing hook as template**

```bash
cat ~/.claude/hooks/adr-agent-sync-check.sh
```

- [ ] **Step 2: Write `adr-index-sync-check.sh`**

Logic: detect any new `wiki/project/decisions/NNNN-*.md` in commits being pushed; for each, grep `0NNN` in `wiki/index.md` — if missing → block push с message "ADR NNNN missing from index.md".

- [ ] **Step 3: chmod +x + register в settings.json**

Add PreToolUse Bash hook entry для git push (similar to adr-agent-sync-check).

- [ ] **Step 4: Test hook with dummy ADR (rollback after)**

Create temporary `wiki/project/decisions/0099-test.md`, commit, attempt push → expect block. Delete + amend.

- [ ] **Step 5: Create wiki page**

Mirror `adr-agent-sync-hook.md` skeleton. Document spec + acknowledge-flow + trigger conditions.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(tooling): adr-index-sync-check.sh hook — block push if new ADR not in index.md (Bucket C6)"
```

---

### Task 12 — PHASE 8 finalize (HARD-GATE checklist)

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-08c-wiki-backfill.md` (PHASE 8 step 5 HARD-GATE)
- Modify: `llm-wiki/wiki/index.md` (S8c entry в Sprints + new components verified)
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (canonical counts table — components +4, sprint pages +1; ADRs unchanged since no new ADR в S8c)
- Modify: `llm-wiki/wiki/project/SPRINT_STATE.md` (between-sprints + tag v0.1.0-alpha.8c)

- [ ] **Step 1: Run final pytest + mypy + canonical counts check**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
mypy --strict src/ 2>&1 | tail -3
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected:
- pytest 600+ passed (test_oco.py 5 deleted; test_config 3 fixed = net -2 vs S8b baseline 604) / 0 new fail
- mypy ≤ 44 errors (T7 may improve)
- Counts: states=16, events=30, transitions=74, reason_codes=45 (no FSM/reason changes в S8c)

- [ ] **Step 2: Create sprint-08c-wiki-backfill.md**

Mirror `sprint-08b-carryover.md` skeleton. Sources: this plan + log.md tail + commits.

Sections: Overview / Plan-ADR links (no new ADR; references 0022 amend) / Deliverables (T1-T11 grouped) / FSM growth (none) / Reason codes (45 unchanged) / Tests / Wiki updates / Open issues for S9+ / Key decisions / Related.

- [ ] **Step 3: Update wiki/index.md**

- Add sprint-08c entry под `## Project — Sprints`
- Add 4 new components (backtest-harness, kill-switch-cli, risk-override, trade-history) under `## Project — Components`

- [ ] **Step 4: Update current-state.md canonical counts**

- Component pages: 22 → 26 (+4)
- Sprint pages: 9 → 10 (+1)
- Last update column: "S8c (2026-04-25)"

- [ ] **Step 5: Update SPRINT_STATE.md**

- sprint: 8c-shipped
- phase: between-sprints
- branch: main
- tag: v0.1.0-alpha.8c
- updated: 2026-04-25

- [ ] **Step 6: Commit (single PHASE 8 batch)**

```bash
git commit -m "docs(sprint): S8c PHASE 8 finalize — sprint page + index sync + canonical counts

Per dev-workflow.md PHASE 8 step 5/5a/6 HARD-GATE checkpoints."
```

- [ ] **Step 7: Use superpowers:finishing-a-development-branch skill**

Push → PR → review → squash-merge → tag v0.1.0-alpha.8c → SPRINT_STATE between-sprints.

---

## Verification (post-merge)

- [ ] All 12 tasks committed + reviewed
- [ ] pytest 0 new regress
- [ ] mypy ≤ 44 errors
- [ ] Live counts verify (states=16, events=30, transitions=74, reason_codes=45)
- [ ] All 4 new wiki pages created + cross-linked
- [ ] ADR 0022 amendments landed
- [ ] Hook `adr-index-sync-check.sh` registered + functional
- [ ] Trace maps retro-added к S5/S7/S8b plans + dev-workflow.md PHASE 3 mandatory rule
- [ ] sprint-08c-wiki-backfill.md created
- [ ] Tag v0.1.0-alpha.8c pushed

---

## Self-review (writing-plans skill checklist)

**1. Spec coverage:** All Bucket D + Q1-Q4 verdicts + Bucket C5/C6 + Bucket E mapped to T1-T12. ✓

**2. Placeholder scan:** Zero TBD / TODO / "fill in details". Every step shows command OR exact code OR exact section to edit. ✓

**3. Type consistency:** `_set_halt(reason: ReasonCode)` consistent с S8b T1 public `request_halt(reason: ReasonCode)`. No new types introduced. ✓

**4. Bite-sized:** Most tasks ≤ 5 steps each. T1 = 4 steps (verify-delete-test-commit). T12 = 7 steps (PHASE 8 standard). All steps 2-5 minutes. ✓

**5. Plan size:** Single file, ~12K target. Under 50KB Read guard. ✓
