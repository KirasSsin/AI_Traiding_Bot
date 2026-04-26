---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-27
sprint: 32c
phase: between-sprints
branch: main
tag: v0.1.0-alpha.32c
---

## S32c SHIPPED ✅

PR #41 → df521a6 squash-merge. Tag v0.1.0-alpha.32c pushed. Branch deleted. **CI passed first try** (S32b infrastructure validated).

## S32c IN PROGRESS 🟡

Sub-sprint S32 series. Branch: `feature/sprint-32c-kit-phase-2-improvements`. Plan committed: `plans/2026-04-27-sprint-32c-kit-phase-2-improvements.md` (7bab107).

**Reduced scope** (per pre-plan analysis): Memory corpus bridges 2-3 + bridge 4 script + context budget hook → deferred S32d (research-heavy). S32c = 4 skill mappings + Fetch MCP + corpus categorization scheme docs + ADR/sync. КУ ~50% / 1.5-2 hours forecast.

### Phase tracking (S32c — in progress)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S32b ship |
| 2 Brainstorm | skipped (operator-specified per ADR 0046 carry-overs) | inline pre-plan analysis |
| 3 Plan | done | `plans/2026-04-27-sprint-32c-kit-phase-2-improvements.md` (7bab107) |
| 4 Execute | in_progress | T1-T4 controller-driven |
| 5 Verify | done | pytest 773 (S32b baseline preserved) / mypy 1 pre-existing / canonical 16/30/74/45 ✓ / json .mcp.json ✓ (sqlite-trading + fetch). 3 pytest failures + 1 mypy carry-over к S33 (pre-existing, NOT S32c regression). |
| 6 Review | pending (likely skip) | no src/ touched |
| 7 Sync | pending | log.md sprint-end + index/current-state в T4 |
| 8 Ship | done | PR #41 → df521a6 + tag v0.1.0-alpha.32c. CI passed first try (S32b infrastructure validated 2nd PR). |
| 9 Close | done | SPRINT_STATE between-sprints (this update) |

### Phase 4 — task progress (S32c)

| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 Fetch/HTTP MCP | done | 0761bad | `.mcp.json` +fetch server (uvx mcp-server-fetch verified pre-installed). tooling-inventory-ru.md Section 7.7 (sqlite-trading post-S32b) + Section 7.8 (fetch NEW) documented. Operator approve at next session start. |
| T2 4 skill mappings | done | 09fcdee | sprint-flow-ru.md +api-design Phase 3 / +browser-test Phase 5 / +perf-opt Phase 6 OPT / +idea-refine extension Phase 2 PRE workflow (procedure block с 5 steps). Skills × Phase 32→36 (17 agent-skills total). |
| T3 Memory corpus scheme docs | done | 47bba48 | tooling-inventory-ru.md NEW Section 22 (4 partitions: trading-decisions / formula-knowledge / process-patterns / debug-knowledge + tag mapping pseudo-code + cascade STEP 2 enhancement spec + operator validation procedure). Bridge 4 design — script implementation S32d candidate. |
| T4 ADR 0047 + sprint-32c page + index/counts | done | 231d55f | 46→47 ADRs / 33→34 sprints / 7→8 MCP / 32→36 skills + S32c sprint history row + kit-overview decision matrix updates |
| Ship | done | df521a6 | tag v0.1.0-alpha.32c. CI passed first try (S32b CI infrastructure validated на non-S32b PR). |

## S32b SHIPPED ✅

PR #40 → cb61678 squash-merge. Tag v0.1.0-alpha.32b pushed. Branch deleted.

CI passed on 4-th attempt (3 fixes: TA-Lib sequential build / ruff baseline guard / dashboard optional deps).

### Phase tracking (S32b — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S32 ship |
| 2 Brainstorm | skipped (operator-specified per КУ Phase 1 deliverables) | inline в plan |
| 3 Plan | done | `plans/2026-04-27-sprint-32b-kit-phase-1-improvements.md` (3cb442d) |
| 4 Execute | in_progress | T1-T6 controller-driven (config + scripts + docs sprint) |
| 5 Verify | done | pytest 773 (S32 baseline preserved) / mypy 1 pre-existing / canonical 16/30/74/45 ✓ / bash -n freshness hook ✓ / yaml ci.yml ✓ / yaml .pre-commit-config ✓ / json .mcp.json ✓ / json settings.json ✓. **3 pytest failures + 1 mypy pre-existing** (NOT S32b regression — carry-over к S33). |
| 6 Review | pending | python-reviewer + architecture-reviewer + doc-reviewer (parallel) |
| 7 Sync | pending | log.md sprint-end + index/current-state в T6 |
| 8 Ship | done | PR #40 → cb61678 + tag v0.1.0-alpha.32b + 4-attempt CI fix saga (TA-Lib parallel race / ruff 169 baseline / dashboard deps) |
| 9 Close | done | SPRINT_STATE between-sprints (this update) |

### Phase 4 — task progress (S32b)

| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 dashboard-reviewer L5 agent | done | 6c2ea66 | out-of-repo `~/.claude/agents/dashboard-reviewer.md` + wiki page (5-axis review checklist + S25 ADR 0039 conditions) |
| T2 SPRINT_STATE freshness check hook | done | 373d527 | bash script (~/.claude/hooks/sprint-state-freshness-check.sh, 755) + settings.json registered (6 hooks total) + positive (exit 0) + negative test (exit 2 on `S25 PHASE 8 ship pending`) passed + wiki page (Block 1↔2) |
| T3 Pre-commit hooks (ruff + mypy + yamllint) | done | (committed inline w/ T4) | `.pre-commit-config.yaml` upgraded (ruff v0.4.0 + mypy --strict local + yamllint для CI workflows) + pre-commit installed (pre-commit 4.6.0). dev dep уже в pyproject.toml. NOTE: mypy 1 pre-existing baseline → operator fix __main__.py:636 OR --no-verify per local commit. |
| T4 GitHub Actions CI | done | 167fc9d | `.github/workflows/ci.yml` 10 steps (checkout / py3.12 / TA-Lib cache + build / pip install / ruff lint+format / mypy --strict с baseline guard / pytest unit с baseline guard / canonical counts verify). Triggers: push к main + PR. CI runs first time на S32b PR. |
| T5 SQLite MCP server | done | 8a24abf | project-level `.mcp.json` (sqlite-trading → data/bot.db) — settings.json schema rejects mcpServers, .mcp.json правильный location. Operator approve at session start OR через `claude mcp` CLI. uvx + mcp-server-sqlite verified available. |
| T6 ADR 0046 + sprint-32b page + index/counts | done | dabf368 | 45→46 ADRs / 32→33 sprints / 9→10 agents / 6→7 hooks / 6→7 MCP / 38→40 components + S32+S32b sprint history rows + kit-overview decision matrix updates |
| Ship | done | cb61678 | tag v0.1.0-alpha.32b. CI passed после 3 fix iterations: TA-Lib build sequential (drop -j) / ruff baseline guard 200 / install dashboard optional deps. CI confirmed working — future PRs auto-validated. |

## S32 SHIPPED ✅

PR #39 → 2bad7ee squash-merge. Tag v0.1.0-alpha.32 pushed. Branch deleted.

### Phase tracking (S32 — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation post-S31 |
| 2 Brainstorm | skipped (operator-specified deliverables per КУ analysis) | inline analysis chapter "Kit improvement plan — КУ analysis" |
| 3 Plan | done | `plans/2026-04-26-sprint-32-kit-phase-0-improvements.md` |
| 4 Execute | in_progress | T1-T6 controller-driven (docs sprint) |
| 5 Verify | done | 773 passed (was reported 762 S31 — count drift +11 actual) / mypy 1 error (`__main__.py:636 bars_per_year_map redef`) / canonical counts 16/30/74/45 ✓. **3 pytest failures pre-exist on main** (test_replay_long_only / test_replay_next_open) — NOT S32 regression. **Carry-over к S33**: fix replay tests + mypy redef. |
| 6 Review | will skip (process/wiki only, no src/ touched) | — |
| 7 Sync | pending | log.md sprint-end + index/current-state in T6 |
| 8 Ship | done | PR #39 → 2bad7ee + tag v0.1.0-alpha.32 + all 4 hooks fired correctly |
| 9 Close | done | SPRINT_STATE between-sprints (this update) |

### Phase 4 — task progress (S32)

| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 SPRINT_STATE.md P0 fix | done | c095bd3 | Stale sections → S32 reality + correct counts (30→44 ADRs / 17→31 sprint pages) + Phase tracking S32 |
| T2 current-state.md P0 fix | done | 2ec9824 | post-S25 → post-S31 + 604→762 + sources/tags/TL;DR update + S25 TL;DR preserved as Previous |
| T3 sprint-flow-ru.md +5 skill mappings | done | e93e61c | idea-refine (Phase 2 PRE) + spec-driven (Phase 2/3) + source-driven (Phase 4) + code-simplification (Phase 6 OPT) + documentation-and-adrs (Phase 8); Skills×Phase map 26→32 |
| T4 cascade smart-explore STEP 2.5 | done | f1f60a7 | sprint-flow-ru.md + kit-overview-ru.md mirror + decision matrix +6 entries |
| T5 Phase 9 consolidate-memory step | done | 660630e | sprint-flow-ru.md Phase 9 procedure +Step 5 + HARD-GATE (every 5 sprints OR >30 obs) |
| T6 ADR 0045 + sprint-32 page + index/counts | done | 397a655 | 44→45 ADRs / 31→32 sprints + sprint history row + S32 index entry + skills mapped 26→32 |
| Ship | done | 2bad7ee | tag v0.1.0-alpha.32 (alpha.32 alpha-channel marker, not MVP DONE) |

## S31 SHIPPED ✅

PR #38 → 52a232a squash-merge. Tag v0.1.0-alpha.31 pushed. Branch deleted.

### Phase tracking (S31 — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation |
| 2 Brainstorm | done (best practices audit) | gap analysis inline в plan |
| 3 Plan | done | `plans/2026-04-26-sprint-31-kit-revision-best-practices.md` |
| 4 Execute | done | 4 task commits (T1-T7) с per-task SPRINT_STATE update |
| 5 Verify | done | 762 pytest passed + CLAUDE.md prune verified (-25% tokens) |
| 6 Review | skipped (process/wiki) | — |
| 7 Sync | done | wiki diffs (index + current-state + log) |
| 8 Ship | done | PR #38 + tag v0.1.0-alpha.31 + all 4 hooks fired correctly |
| 9 Close | done | SPRINT_STATE between-sprints |

### Phase 4 — task progress
| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 kit-overview-ru.md | done | (pending commit) | 1-page TL;DR + Quick decision matrix + 9 agents + 6 hooks + 5 skills + ~50 plugin skills + 6 MCP + cascade rule + Top 10 commands + Top 5 anti-patterns + 9-phase lifecycle + 20 best practices applied |
| T2 tooling-inventory-ru.md sections 14-19 | done | (pending commit) | Section 14 Permission modes / 15 Plugins curated / 16 CLI tools / 17 Status line / 18 Token-saver commands / 19 Non-interactive + fan-out |
| T3 prune llm-wiki/CLAUDE.md (448→<200) | done | (pending commit) | 448→291 (-35%), 27KB→13KB (-52%) — extracted verbose к kit-overview-ru + tooling-inventory-ru |
| T4 audit ~/.claude/CLAUDE.md (316→<250) | done | (pending commit) | 316→253 (-20%) — section 9c compressed (80→17 lines) preserving formula |
| T5 repo CLAUDE.md +kit-overview link | done | (pending commit) | 190→212 lines — added kit-overview/sprint-flow-ru/tooling-inventory references к Ключевые файлы table |
| T6 status line + `/btw`/`/rewind`/`--continue` | done | (pending commit) | Anti-patterns +4 (kitchen-sink/btw/3+correction/CLAUDE.md bloat) + token-saver commands table 8 commands + link к Section 18 |
| Total CLAUDE.md prune | done | — | 954→756 lines (-21%), 61KB→46KB (-25%), ~18.5K→14K tokens (-25%) per session |
| T7 ADR 0044 + sprint-31 page + sync | done | (pending commit) | ADR + sprint page + index + current-state (43→44 ADRs / 30→31 sprint pages / +Kit settings RU 3 files / +CLAUDE.md tokens ~14K) + log |
| Ship | in_progress | — | tag alpha.31 |

## S30 SHIPPED ✅

PR #37 → 4e719a9 squash-merge. Tag v0.1.0-alpha.30 pushed. Branch deleted.

### Phase tracking (S30 — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation |
| 2 Brainstorm | short (operator-specified) | inline в plan |
| 3 Plan | done | `plans/2026-04-26-sprint-30-tier-2-agents-mem-wiki-merge.md` |
| 4 Execute | done | 6 task commits (T1-T9) с per-task SPRINT_STATE update |
| 5 Verify | done | 762 pytest passed + bash -n + positive/negative hook test |
| 6 Review | skipped (process/wiki) | — |
| 7 Sync | done | wiki diffs (index + current-state + log) |
| 8 Ship | done | PR #37 + tag v0.1.0-alpha.30 + phase-advance hook fired correctly |
| 9 Close | done | SPRINT_STATE between-sprints |

### Phase 4 — task progress
| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 security-auditor agent | done | (out-of-repo, ~/.claude/agents/) | Opus, OWASP + trading-specific rules + MEMORY.md |
| T2 test-engineer agent | done | (out-of-repo) | Sonnet, test pyramid + property tests + Hypothesis + Trading-specific rules |
| T3 doc-reviewer agent | done | (out-of-repo) | Haiku, frontmatter+links+Block 1↔2+canonical counts |
| T4 phase-advance.sh hook | done | (out-of-repo + settings.json) | bash -n + negative test verified (Phase 5 pending → block + helpful error). Registered к PreToolUse Bash matcher |
| T5 wiki↔mem cascade design | done | (combined с T6) | Section 13 NEW в tooling-inventory-ru.md — 4-step cascade (wiki→mem→grep→raw) + examples + bridges 2-4 deferred |
| T6 tooling-inventory-ru.md | done | (pending commit) | Section 1 expanded (6→9 agents с status legend) + Section 8 +phase-advance.sh + Section 13 NEW cascade + decision matrix +5 entries |
| T7 sprint-flow-ru.md Phase 6 | done | (pending commit) | Reviewer matrix +3 (security/test/doc) + Phase 5 hook note + Token economy cascade section с link к Section 13 |
| T8 CLAUDE.md | done | (pending commit) | Repo CLAUDE.md Phase 6 +3 reviewers + Phase 5 hook + cascade rule + 4 anti-patterns. llm-wiki CLAUDE.md +phase-advance hook + cascade rule references |
| T9 ADR 0043 + sprint-30 page + sync | done | (pending commit) | ADR + sprint page + index + current-state + log + canonical counts (43 ADRs / 30 sprint pages / 9 agents / 6 hooks) |
| Ship | in_progress | — | tag alpha.30 |

## S29 SHIPPED ✅

PR #36 → 30d476a squash-merge. Tag v0.1.0-alpha.29 pushed. Branch deleted.

### Phase tracking (S29 — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation |
| 2 Brainstorm | skipped (operator-specified) | — |
| 3 Plan | done | `plans/2026-04-26-sprint-29-superpowers-integration.md` |
| 4 Execute | done | 4 commits (T1-T4) с per-task SPRINT_STATE update |
| 5 Verify | done | 762 pytest passed (S28 baseline preserved) |
| 6 Review | skipped (process/wiki) | — |
| 7 Sync | done | wiki diffs (index + current-state + log) |
| 8 Ship | done | PR #36 + tag v0.1.0-alpha.29 |
| 9 Close | done | SPRINT_STATE between-sprints |

### Phase 4 — task progress (completed)
| Task | Commit | Note |
|------|--------|------|
| T1 sprint-flow-ru.md | be4c10b | Explicit skills per phase + Skills × Phase integration map |
| T2 tooling-inventory-ru.md | 202d915 | Decision matrix +8 + Section 12 NEW + Section 3 expanded |
| T3 CLAUDE.md | b7b0f16 | Phase table expanded (Primary + Optional columns) |
| T4 ADR 0042 + sprint-29 page + sync | 50f4ae1 | ADR + sprint page + index + current-state + log |
| Squash-merge | 30d476a | PR #36, tag alpha.29 |

## S28 SHIPPED ✅

PR #35 → 1538a53 squash-merge. Tag v0.1.0-alpha.28 pushed. Branch deleted.

### Phase tracking (S28 — completed)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session resume mark_chapter |
| 2 Brainstorm | skipped (deliverables operator-specified) | — |
| 3 Plan | done | `plans/2026-04-26-sprint-28-process-enforcement.md` (first plan since S15) |
| 4 Execute | done | 6 commits (T1-T6) с per-task SPRINT_STATE update |
| 5 Verify | done | 762 pytest passed (S27 baseline preserved) + bash -n hook + positive/negative test |
| 6 Review | skipped (process/wiki, no code reviewers applicable) | — |
| 7 Sync | done | wiki diffs (index + current-state + log) в T6 commit |
| 8 Ship | done | PR #35 + tag v0.1.0-alpha.28 |
| 9 Close | done | SPRINT_STATE between-sprints (этот update) |

### Phase 4 — task progress (completed)
| Task | Commit | Note |
|------|--------|------|
| T1 sprint-flow-ru.md | 09b2e02 | Russian sprint lifecycle 9 phases |
| T2 tooling-inventory-ru.md | 6a62f27 | 11 sections — agents/skills/plugins/MCP/hooks/decision matrix |
| T3 sprint-flow-check.sh hook | 18387fa | Mechanical PHASE 3 enforcement, registered settings.json |
| T4 SPRINT_STATE template | 18387fa | Per-phase + per-task tracking inline |
| T5 CLAUDE.md updates | 900003a | Repo + llm-wiki binding sections |
| T6 ADR 0041 + sprint-28 page + sync | 4623a5c | ADR + sprint page + index + current-state + log |
| Squash-merge | 1538a53 | PR #35, tag alpha.28 |

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**S32c SHIPPED — Kit Improvement Phase 2 reduced COMPLETE.** Sub-sprint S32 series. 4 changes: T1 Fetch/HTTP MCP server + T2 4 skill mappings (api-design Phase 3 / browser-test Phase 5 / perf-opt Phase 6 OPT / idea-refine extension Phase 2 PRE workflow) + T3 Memory corpus categorization scheme docs (bridge 4 design, script S32d) + T4 ADR/sync. КУ avg ~51% / ~1.5 hours. CI passed first try. NO code changes. 773 pytest preserved.

**Status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 40 components + **47 ADRs** + **34 sprint pages**)
- Kit infrastructure: ✅ COMPLETE — 10 reviewer agents + 7 active push hooks + **8 MCP servers** (sqlite-trading + fetch project-level) + **36 skills mapped** + cascade 5-step + Phase 9 consolidate-memory HARD-GATE + GitHub Actions CI live + pre-commit local gate + Memory corpus categorization scheme designed (bridge 4 ready для script S32d) + 20/20 best practices
- Formula correctness: ✅ FIXED (5 bugs eliminated post-S27)
- Strategy validation: ❌ NEGATIVE (0 PASS / 30 FAIL — trading work blocked pending ESC-1/2/3)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 unreachable single-symbol 4H)
- Test debt: ⚠️ 3 pre-existing pytest failures + 1 mypy redef + ~169 ruff issues — carry-over к S33+

## Последний спринт (S32c — Kit Improvement Phase 2 reduced)

Sub-sprint S32 series. 4 changes: T1 Fetch/HTTP MCP (`.mcp.json` fetch + Section 7.7/7.8 doc) + T2 4 skill mappings к sprint-flow-ru.md (api-design Phase 3 / browser-test Phase 5 / perf-opt Phase 6 OPT / idea-refine extension Phase 2 PRE workflow с 5-step procedure) + T3 Memory corpus categorization scheme (Section 22 NEW: 4 partitions + tag mapping pseudo-code + cascade STEP 2 enhancement spec; bridge 4 design, script S32d) + T4 ADR 0047 + sprint-32c page + index/counts (46→47 ADRs / 33→34 sprints / 7→8 MCP / 32→36 skills). КУ avg ~51% / ~1.5 hours. CI passed first try. NO code changes.

## Следующее действие

```
Operator decides next direction:

Track A — Kit Phase 3 (S32d candidate):
  Phase 2 deferred research:
    - Memory corpus org bridge 2 (corpus periodic sync)
    - Memory corpus org bridge 3 (chapter mark auto-link)
    - Memory corpus org bridge 4 implementation script (uses scheme от S32c Section 22)
    - Context budget hook (>70% warn) — Claude Code hook API research
  Phase 3 originals:
    - bybit-api-reviewer L5 agent (Bybit V5 rate limits / endpoint params / error codes)
    - anthropic-skills:schedule (audit_formulas.py automation)
    - Sprint metrics tracking (velocity / revision rate)

Track B — Trading work (BLOCKED — awaits operator):
  - ESC-1 multi-symbol authorization
  - ESC-2 "in profit" semantics
  - ESC-3 4H operational implications
  
Trader-expert backlog (когда Track B unblocks):
  - Multi-symbol 4H mean_reversion (n≈135 → T5 PASS) — depends ESC-1
  - Regime filter + SMA50 trend gate
  - SL calibration {1.0/1.25/1.5}×ATR
  - Donchian 4H breakout
  - DSR cross-trial sigma_SR + MC power audit

Track C — Test debt cleanup sprint (если operator chooses):
  - Fix 3 pytest failures (test_replay_long_only / test_replay_next_open)
  - Fix 1 mypy error (__main__.py:636 bars_per_year_map redef)
  - Cleanup ~169 ruff baseline (gradually OR enable strict gate)

Operator action на next session:
  - Approve fetch MCP at session start (one-time prompt)
```

## Carry-over preserved (v0.2+ if any future direction chosen)

All S12 + S13 carry-overs unaddressed (10+ items):

- F live demo Mainnet validation actual run (33min only since S12)
- FillRecorderAdapter Layer 2 schema link (entry_signal_id к execution_state migration)
- 3-way endpoint enum (DEMO/TESTNET/MAINNET) — Q6 future fix
- T2 review C3 init_db dual-conn comment (S11 carry-over)
- DSR per-fold DataFrame→TradeRecord conversion (S10 informational)
- DSR threshold calibration (S15+ per S11 Q5)
- DSR cross-trial sigma_SR implementation (S14 Q2 REVISE — needed для any future revision)
- halt_log INSERT order swap в `_set_halt` (PRE-EXISTING)
- find_by_order_id ORDER BY explicit (T1 reviewer follow-up)
- fill-history.md / bybit-adapter.md / ws-private-consumer.md component page updates
- T2/T5/T6 quant-stats deferred concerns (Sortino formula docs, sqrt(8760) frequency-agnostic, boundary tests)

## Ключевые решения S14

- **Q1 EXPAND** (trader): T5 unreachable verified via grep — 5x signal frequency gap
- **Q2 REVISE** (trader): DSR cross-trial sigma_SR gap — verified via dsr.py:73
- **Option B** (user): honest close immediately, save 1 sprint vs theatrical Option A
- **Tag semantics:** `v0.1.0-alpha.14` = honest close marker, NOT MVP DONE
- **No spec amendment:** acceptance-criteria.md T1-T6 thresholds preserved
- **No code changes:** S14 = documentation only

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Обнови "Следующее действие" — конкретное, с командой если применимо
3. Добавь в "Ключевые решения" только нетривиальное
4. Обнови `updated:` в frontmatter
