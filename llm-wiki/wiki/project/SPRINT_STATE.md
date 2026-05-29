---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-29  # S50 PHASE 4 — T4 (SupertrendStrategy Lazybear + reason codes 63->65) done
sprint: 50
phase: 4-execution
branch: feature/sprint-50-supertrend
tag: v0.1.0-alpha.49
---

## Текущий статус

**S50 PHASE 4 execution.** Supertrend (freqtrade adaptation). Trader-expert ROUND 1+2 binding + operator decisions. ADR 0067 proposed. LOCKED: BTCUSDT 1H, hypothesis #10. Q1 pure Supertrend. Q3 1H (not 4H — T5 reachability). Q4 OPERATOR OVERRIDE: fix autoresearch held-out split → legitimate sweep (not literature defaults). 8-step execution order в pre-s50-backlog. Prereq CC2 (Wilder ATR extract) + CC3 (N_trials gap) + CC4 (held-out split).

**T3 (CC4 held-out split) DONE** — `2fc2cb7`. `split_train_heldout()` + `eval_heldout_once()` + HELDOUT_START/END constants в `scripts/autoresearch_endless.py`; sweep now train-only (ts < 2025-06-01) anti-champion-bias. 5 new tests (`tests/unit/test_autoresearch_heldout.py`). pytest 1359.

**S49 SHIPPED** — `571e4fa` tag v0.1.0-alpha.49 (full tech-audit, 1348 tests).

**Canonical counts (post-S49):** 16 states / 30 events / 74 transitions / **63** reason_codes (+7 H6) / 66 ADRs / **53** sprint pages / Vitest 43 / Playwright 7 / pytest 1350

## Phase tracking (S49 — current sprint)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | Session start post-S48 ship |
| 2 Brainstorm | done | Audit-only sprint — no brainstorm (tech-review scope) |
| 3 Plan | done | 9 reviewers → findings aggregated → audit plan |
| 4 Execute | done | All BLOCKER+HIGH+MEDIUM+LOW fixed TDD |
| 5 Verify | done | pytest 1350 / mypy 0 / Vitest 43 / Playwright 7 / lint+tsc+build clean |
| 6 Review | done | 6 re-review agents: ALL APPROVE, 0 regressions |
| 7 Sync | done | wiki sync: sprint-49 page + log + current-state + index + SPRINT_STATE |
| 8 Ship | done | PR #60 squash-merge `571e4fa`, tag v0.1.0-alpha.49 pushed |
| 9 Close | done | SPRINT_STATE between-sprints + log ship entry |

## Следующее действие

**S50 PHASE 4 — продолжить execution.** Done: T1, T2, T3 (CC4 held-out split, `2fc2cb7`). Next: остальные задачи по 8-step order в `pre-s50-backlog.md` (Supertrend strat T6, T5 reachability, T8 held-out winner eval via `eval_heldout_once`).

## S49-S51 ROADMAP (operator decisions 2026-05-29)

### S49 — Full Tech-Review Audit (SHIPPED → PHASE 8 ship in_progress)

**Все дефекты устранены** — see `sprint-49-tech-review-audit.md` canonical summary. T3 RESOLVED (binding verdict). 63 reason_codes. pytest 1350.

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

**SPRINT_STATE pre-trim archive (S46 post-ship):** [[archive/SPRINT_STATE-archive-part-1]] + [[archive/SPRINT_STATE-archive-part-2]]. Source git `cbf3328`.

**Cross-cutting:**
- **`llm-wiki/wiki/project/architecture/current-state.md`** — sprint history table + canonical counts evolution

---

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`. Инструкции → repo CLAUDE.md.
