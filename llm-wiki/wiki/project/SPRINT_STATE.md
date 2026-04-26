---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 31
phase: 4-execution
branch: feature/sprint-31-kit-revision-best-practices
tag: v0.1.0-alpha.30
---

## Phase tracking (S31)

| Phase | Status | Artifact |
|-------|--------|----------|
| 1 Orient | done | session continuation |
| 2 Brainstorm | done (best practices audit inline в plan) | gap analysis |
| 3 Plan | done | `plans/2026-04-26-sprint-31-kit-revision-best-practices.md` |
| 4 Execute | in_progress | T1-T7 |
| 5 Verify | pending | — |
| 6 Review | skipped (process/wiki) | — |
| 7 Sync | pending | — |
| 8 Ship | pending | — |
| 9 Close | pending | — |

### Phase 4 — task progress
| Task | Status | Commit | Note |
|------|--------|--------|------|
| T1 kit-overview-ru.md | done | (pending commit) | 1-page TL;DR + Quick decision matrix + 9 agents + 6 hooks + 5 skills + ~50 plugin skills + 6 MCP + cascade rule + Top 10 commands + Top 5 anti-patterns + 9-phase lifecycle + 20 best practices applied |
| T2 tooling-inventory-ru.md sections 14-19 | in_progress | — | Permission modes / plugins / CLI / status line / token-saver / non-interactive |
| T3 prune llm-wiki/CLAUDE.md (448→<200) | pending | — | Extract verbose к wiki pages |
| T4 audit ~/.claude/CLAUDE.md (316→<250) | pending | — | Apply prune test |
| T5 repo CLAUDE.md +kit-overview link | pending | — | Minor refs |
| T6 status line + `/btw`/`/rewind`/`--continue` | pending | — | Token-saver patterns |
| T7 ADR 0044 + sprint-31 page + sync | pending | — | Wiki diffs |

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

**S30 SHIPPED. Tier-2 Agents + phase-advance hook + LLMWiki↔Claude-mem cascade.** 30 спринтов завершено. Operator-driven kit hardening. **3 NEW reviewer agents** (out-of-repo): security-auditor opus (OWASP + trading rules) / test-engineer sonnet (Hypothesis property + S27 lessons regression) / doc-reviewer haiku (frontmatter + Block 1↔2 sync + canonical counts). **NEW hook** phase-advance.sh — pre-merge Phase 5 verify enforcement (blocks `gh pr merge` если Phase 5 != done/skipped). **LLMWiki ↔ Claude-mem cascade rule** documentation-first: 4-step (wiki→mem→grep→raw), saves tokens via curated wiki priority. Bridges 2-4 (corpus sync / chapter mark auto-link / frontmatter tags) deferred к S31+. NO code changes. 762 pytest preserved. **9 reviewer agents + 6 active hooks.** S30 itself executed по proper kit flow per S28+S29 binding rules.

**Status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 30 ADRs + 17 sprint pages)
- Formula correctness: ✅ FIXED (5 bugs eliminated, measurement instrument trustworthy)
- Strategy validation: ❌ NEGATIVE (still 0 PASS / 30 FAIL — structural failures, не formula bugs)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 still unreachable single-symbol 4H)

## Последний спринт (S27 — formula bug fixes)

Operator-driven audit sprint. 5 bugs (T1-T5) fixed TDD, audit re-run. ESC items для S28+ pending operator decision.

- T1 HIGH replay_engine bars_per_year parameterization (annualization)
- T2 MEDIUM Sortino canonical downside_dev (Sortino & Price 1994)
- T3 MEDIUM RSI/ATR warm-up gating (mask first period bars NaN)
- T4 INFO/CC5 trade_extractor preserve actual reason_code (SL/TP/SIGNAL_FLIP/EOD/KILL_SWITCH)
- T5 LOW MC seed=42 default (reproducibility)
- T6 audit re-run + diff snapshot (data/formulas_audit_v1_post_s27.json)
- T7 ADR 0040 + sprint-27 page + wiki sync
- T8 PHASE 8 ship pending

## Следующее действие

```
S27 PHASE 8 ship: gh pr create + squash merge + tag v0.1.0-alpha.27.

Operator decides ESC items для S28+ scope:
- ESC-1 Multi-symbol authorization (S28 expanded scope beyond BTCUSDT MVP)
- ESC-2 "In profit" vs "pass acceptance criteria" — different goals (live pilot ETH 4H pre-S28?)
- ESC-3 Operational implications 4H multi-symbol (3 simultaneous positions, 1-5 day holds)

Trader-expert backlog (S28-S32):
- S28 Multi-symbol 4H mean_reversion (n≈135 → T5 PASS) — depends ESC-1
- S29 Regime filter + SMA50 trend gate (CC2 fold concentration)
- S30 SL calibration {1.0/1.25/1.5}×ATR + t-stat power validation
- S31 Donchian 4H breakout (independent hypothesis)
- S32 DSR cross-trial sigma_SR + MC power audit (closes S14 Q2 carry-over)
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
