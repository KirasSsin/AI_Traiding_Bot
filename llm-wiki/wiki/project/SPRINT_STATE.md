---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-11  # S48 T24 done — wiki sync (24/24) → phase=5-verify
sprint: 48
phase: 5-verify
branch: feature/sprint-48-ui-overhaul
tag: v0.1.0-alpha.48
---

## Текущий статус

**S48 PHASE 4 COMPLETE (24/24)** — все задачи выполнены. Переход к PHASE 5 verify.

**S48 deliverables (24/24):**
- Bucket 0 (T1): component subdirs refactor C5
- Bucket A (T2-T7): backend (replay equity_curve + account_service C1 + /api/bybit/balance + glossary_data + /api/glossary C3 + RunRecord balance/win_rate)
- Bucket B (T8-T14): frontend bugs A/D/F/G/H (EquityChart tooltip + equity-chart E2E + MetricsTable divider + FailAnalysisTab chips + DocumentationTab ▸ remove + HistoryTab accordion + HistoryTab RTL tests)
- Bucket C (T15-T19): Bug E GlossaryTab (base + useStrategyContext C2 + filter edge case + search + App nav)
- Bucket D (T20-T22): Bug C Bybit balance (useBybitBalance + BalanceBadge + ConfigureBacktest integration)
- Bucket E (T23-T24): Bug I RU enforcement + wiki sync

**Architect bindings met:** C1/C2/C3/C4/C5 все выполнены.

**Canonical counts (post-S48):** 16 states / 30 events / 74 transitions / **56** reason_codes UNCHANGED / 66 ADRs / **52** sprint pages / Vitest 32 / Playwright 7 / pytest 1056+

## Phase tracking (S48 — current sprint)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | Continuous session post-S47 ship |
| 2 Brainstorm | done | trader-expert R1+R2, pre-s48-backlog v3 (24 tasks 6 buckets), pre-plan FE+architect dispatch |
| 3 Plan | done | superpowers:writing-plans → 2026-05-11-sprint-48-ui-overhaul.md commit `aa66b1a` |
| 4 Execute | **done** | 24/24 tasks complete. T24 wiki sync done (sprint-48 page + index + log + current-state). |
| 5 Verify | **in_progress** | pytest + mypy + Vitest + Playwright + lint+tsc+build |
| 6 Review | pending | 9 reviewers parallel (frontend-developer PRIMARY + architecture-reviewer C1-C5 verify + python + bybit-api + security-auditor + trading-logic + test-engineer + data-integrity + doc) |
| 7 Sync | done | wiki sync T24 complete |
| 8 Ship | pending | tag v0.1.0-alpha.48 |
| 9 Close | pending | SPRINT_STATE between-sprints + log ship entry |

## Phase tracking (S47 — previous shipped)

| Phase | Status |
|---|---|
| 1-9 all | done v0.1.0-alpha.47 squash-merge `116f789` |

## Следующее действие

**PHASE 5 — verify gates:** `pytest + mypy + Vitest + Playwright + lint+tsc+build`. Затем PHASE 6 reviewers parallel (9 агентов).

## S48-S50 ROADMAP (operator decisions 2026-05-11)

### S48 — UI Overhaul (SHIPPED → PHASE 5 verify)

**24/24 tasks done** — see `sprint-48-ui-overhaul.md` canonical summary. Architect C1-C5 all met.

### S49 — Косметика + carry-overs (~10-15 задач)

Маленький полировочный спринт. Operator добавит items post-S48 review. Предварительный scope: color tokens / typography / a11y / Vitest #4+#5 / README npm / F8 / Item #7+#10 / MonthlyHeatmap / typing / BybitAdapterError / RTL tests / wiki cleanup.

### S50 — NEW STRATEGIES (Path B activation)

**TBD после S49 ships.** Brainstorm: strategy direction / symbol scope / timeframe / acceptance criteria.

### Permanently deferred (no clear sprint owner)

- 12mo MAINNET-promotion ADR (нужен δ live data accumulation — irrelevant до S48 strategy validates)
- Live trade feed widget (YAGNI — 0 live trades)
- Honest close code piece (preset `disabled: bool` + 422 reject) — DROPPED per operator pivot
- M4 `__repr__` security redaction — defer к когда mainnet activation real

---

## История спринтов (где искать)

**SPRINT_STATE — only current.** Historical sprint sections archived и распределены:

**Per-sprint canonical (preferred):**
- **`llm-wiki/wiki/project/sprints/sprint-NN-<slug>.md`** — canonical per-sprint summary pages (50 pages, S1-S46) — primary lookup для "что было в SN"

**Chronological:**
- **`llm-wiki/wiki/log.md`** — append-only journal с per-sprint ship entries (S1 → S46+) — для "когда что произошло"

**SPRINT_STATE pre-trim raw archive (S46 post-ship 2026-05-11):**
- [[archive/SPRINT_STATE-archive-part-1]] — S33-S46 historical sections (46 KB)
- [[archive/SPRINT_STATE-archive-part-2]] — S5-S32e historical sections (38 KB)
- Source: git commit `cbf3328` (last pre-trim snapshot, 86 KB / 1239 lines)

**Cross-cutting:**
- **`llm-wiki/wiki/project/architecture/current-state.md`** — sprint history table + canonical counts evolution

---

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`. Инструкции → repo CLAUDE.md.
