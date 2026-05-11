---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-11  # S47 PHASE 4-EXECUTION COMPLETE (16/16) → PHASE 5-VERIFY
sprint: 47
phase: 5-verify
branch: feature/sprint-47-tech-debt-carryovers
tag: v0.1.0-alpha.46
---

## Текущий статус

**Sprint 47 PHASE 4 execution COMPLETE (16/16). PHASE 5-VERIFY in progress.** Все 5 бакетов DONE: Bucket A (T1-T5 Vitest+RTL infra + 3 unit tests + E2E activate) + Bucket B (T6-T8 SPA catch-all + cache headers + MetricsTable T5 fix) + Bucket C (T9-T11 M1+M2+M3 bybit-api) + Bucket D (T12 DSR property + n_trials + sprint type trio) + Bucket E (T13 trade_stats bug + T14 cursor tooltip + T15 FailAnalysisTab). **T16 DONE (wiki sync: sprint-47 page + index + log + current-state counts 56→57 + 50→51 sprint pages).**

**S47 scope locked (16 tasks, 5 buckets)** per `pre-s47-backlog.md` rev 2:
- Bucket A (5): Vitest+RTL infra + 3 unit tests + backtest-flow E2E activate
- Bucket B (3): SPA catch-all + cache headers + MetricsTable T5 fix
- Bucket C (3): M1+M2+M3 bybit-api fixes
- Bucket D (1): DSR property + n_trials + sprint type bundled
- Bucket E (3): T14 trade_stats bug + T15 EquityChart cursor + T16 RU Fail Analysis tab

**Operator pivot 2026-05-11:** S48 = NEW strategies (Path B rejoin). Honest close ADR 0067 DROPPED. UI визуально approved.

**Brainstorm trail:** trader-expert ROUND 1+2 done. Q3+Q5 CONFIRM_REVISE → defer к S48 / mainnet ADR. Q1/Q2/Q4/Q6 CONFIRM. Q7 (operator UI validation) = APPROVED + 3 items surfaced (T14 BUG, T15 cursor, T16 fail analysis tab).

**Canonical counts (post-S47):** 16 states / 30 events / 74 transitions / **57** reason_codes (+1 INVALID_PARAM T9) / 66 ADRs / **51** sprint pages / 48 components

**Last shipped:** S46 v0.1.0-alpha.46 squash-merge `0fcb3ff` (React 18 + Anthropic/cyberpunk + honest close UI piece). 22 tasks. PHASE 6 5 reviewers, 1 BLOCKER + 2 HIGH + 1 MEDIUM addressed. CI GREEN.

## Phase tracking

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | Session start orient + git state verified |
| 2 Brainstorm | done | trader-expert R1+R2, pre-s47-backlog rev 2 (16 tasks 5 buckets) |
| 3 Plan | done | superpowers:writing-plans → 2026-05-11-sprint-47-tech-debt-carryovers.md |
| 4 Execute | done | T1-T16 16/16 all committed |
| 5 Verify | done | pytest 1037 pass / mypy 0 / Vitest 23 / Playwright 4 / lint+tsc+build clean |
| 6 Review | done | 9 reviewers APPROVE/AWC, 0 blockers; HIGH+MEDIUM fixes applied pre-merge |
| 7 Sync | done | wiki sync committed (T16) — sprint-47 page + index + log + current-state |
| 8 Ship | in_progress | PR #58 → squash-merge + tag v0.1.0-alpha.47 pending |
| 9 Close | pending | post-merge SPRINT_STATE → between-sprints |

## Следующее действие

**PHASE 5 verify** — запустить: pytest -x -q + mypy --strict src/ + Vitest + Playwright + lint+tsc+build + canonical counts verify (reason_codes=57 в ci.yml line 133). После GREEN → PHASE 6 reviewers (9: python + trading-logic + quant-stats + bybit-api + security-auditor + frontend-developer + test-engineer + data-integrity + doc) → PHASE 7 wiki sync (done — T16) → PHASE 8 ship.

## S47-S49 ROADMAP (operator decisions 2026-05-10 + 2026-05-11 PIVOT)

### S47 — Frontend doraботки + bugs + tech debt carry-overs (~16 tasks LOCKED)

**Scope per `pre-s47-backlog.md` rev 2** (5 buckets, 16 tasks):
- Bucket A (5): Vitest+RTL infra + 3 unit tests (computeDrawdown property + useWfaFailAck + MetricsTable threshold) + backtest-flow E2E activate
- Bucket B (3): SPA catch-all FastAPI route + asset cache headers + MetricsTable T5 bug fix
- Bucket C (3): M1 retCode taxonomy + M2 dict guards + M3 WS isinstance (BYBIT API fixes)
- Bucket D (1): DSR property test + n_trials assert + sprint int/str type test (bundled trio)
- Bucket E (3): T14 trade_stats empty bug fix + T15 EquityChart cursor tooltip + T16 Fail Analysis tab (RU detailed WHY-failed narrative)

**Out-of-scope S47:** M4 `__repr__` security redaction (defer mainnet ADR), Vitest tests #4/#5, A11y polish, README npm note, F8 constant unification, MonthlyHeatmap eslint cleanup, Item #7/#10, **honest close code piece (preset `disabled: bool` flag) — DROPPED indefinitely per operator pivot 2026-05-11 (Path B rejoin)**.

**Reviewers PHASE 6:** python + trading-logic + quant-stats + bybit-api + security-auditor (M1-M3 only) + frontend-developer + test-engineer + data-integrity + doc.

### S48 — NEW STRATEGIES (Path B rejoin — operator pivot 2026-05-11)

Original S48 = honest close finalize + ADR 0067. **PIVOT 2026-05-11:** operator explicit "через один [S48] будем делать новые стратегии". Path B (new strategies) was excluded 2026-05-10, **rejoin 2026-05-11**.

**Implications:**
- Honest close ADR 0067 (formal portfolio close) — DROPPED. Operator informed via S46 UI piece (badges + ack-gated banner) уже sufficient. Если новая стратегия WFA_PASS → honest UI organically lose relevance.
- v0.1 wrap-up semver — keep `alpha.N` indefinitely (Q6 verdict stands). No bump к v0.1.0 ждёт actual WFA_PASS preset.

**S48 brainstorm (TBD when S47 ships):**
- Strategy direction (mean-reversion / trend / momentum / volatility / multi-asset / ML-augmented)
- Symbol scope (BTC only / multi-symbol)
- Timeframe (existing 4H/D OR new 5m/15m/1h)
- Acceptance criteria (re-use ADR 0014 WFA gates OR adjust)

### S49+ — TBD

Operator: "Я не знаю, что там делать". Depends на S48 outcome (если new strategy WFA_PASS → mainnet prep ADR; если FAIL → another iteration OR pivot).

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

## Как обновлять этот файл

**BUDGET: ≤ 6 KB BINDING** (matches Read tool comfort-zone < 50 KB / 25k tokens limit с huge margin).

**Split fallback** (если current sprint state legitimately нужен > 6 KB — e.g. complex sprint с 30+ tasks + multiple architect bindings):
1. Trim approach FIRST — push detail к sprint-NN.md page (canonical) + log.md (chronological)
2. Если всё ещё > 6 KB → **indexed split** (per project convention `tooling-inventory-ru.md` + `tooling-inventory-ru-part-2.md`):
   - `SPRINT_STATE.md` (index + frontmatter + minimal current-state pointer ≤ 2 KB)
   - `SPRINT_STATE-part-2.md` (full current-sprint detail)
3. Pre-trim raw history снапшот → `archive/SPRINT_STATE-archive-part-N.md` (NOT lost; recoverable)

Anti-pattern (S46 post-ship 2026-05-11): file accumulated 86 KB / 1239 lines с S5-S45 history blocks → exceeded Read tool limit, blocked session-start orient. Pre-trim content preserved в `archive/SPRINT_STATE-archive-part-1.md` + `-part-2.md`.

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови frontmatter `updated:` + `phase:` + `tag:`
2. Перепиши "Текущий статус" — concise current-sprint state (≤ 15 bullets)
3. Обнови "Следующее действие" — конкретное, с командой если применимо
4. ROADMAP — keep next 2-3 sprints scope; older defer-list trim aggressively
5. **NEVER append** historical sprint sections — they go к `log.md` (append-only journal) + `sprint-NN.md` (canonical summary)

Per-task SPRINT_STATE update protocol (PHASE 4): edit "Текущий статус" + "Следующее действие" после КАЖДОЙ task complete (not only sprint end). Optional commit `docs(sprint): SPRINT_STATE update phase=4 task=Tx done`.
