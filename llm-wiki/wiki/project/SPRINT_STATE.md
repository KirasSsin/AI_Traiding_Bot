---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-11  # S48 T15 done — GlossaryTab base component + types + API method (Bug E core)
sprint: 48
phase: 4-execution
branch: feature/sprint-48-ui-overhaul
tag: v0.1.0-alpha.47
---

## Текущий статус

**Sprint 47 SHIPPED** — squash-merge `116f789`, tag `v0.1.0-alpha.47`. Branch `feature/sprint-47-tech-debt-carryovers` deleted. Phase = between-sprints.

**S47 deliverables (16/16):** Vitest+RTL infra + 3 unit tests + backtest-flow E2E activate / SPA catch-all + cache headers + MetricsTable T5 fix / M1+M2+M3 bybit-api + DSR/n_trials/sprint trio / trade_stats research bug + EquityChart cursor tooltip + FailAnalysisTab RU narrative

**PHASE 6 (9 reviewers):** all APPROVE/AWC, 0 blockers. 5 pre-merge fixes applied (T5 UI threshold ≥100→≥50 / T1+T2 annualization note / T5 n_eff / FailAnalysisTab XSS sweep / strategy_metrics docstring).

**Honest accuracy:** 6 actual presets / T1-T6 informational / T5_FLOOR=50 (S34 ADR 0052) / MC p=0.05 / DSR Pearson kurtosis / 2 parallel ReasonCode enums clarified — main 56 unchanged, bybit-local +1 INVALID_PARAM

**S47 scope locked (16 tasks, 5 buckets)** per `pre-s47-backlog.md` rev 2:
- Bucket A (5): Vitest+RTL infra + 3 unit tests + backtest-flow E2E activate
- Bucket B (3): SPA catch-all + cache headers + MetricsTable T5 fix
- Bucket C (3): M1+M2+M3 bybit-api fixes
- Bucket D (1): DSR property + n_trials + sprint type bundled
- Bucket E (3): T14 trade_stats bug + T15 EquityChart cursor + T16 RU Fail Analysis tab

**Operator pivot 2026-05-11:** S48 = NEW strategies (Path B rejoin). Honest close ADR 0067 DROPPED. UI визуально approved.

**Brainstorm trail:** trader-expert ROUND 1+2 done. Q3+Q5 CONFIRM_REVISE → defer к S48 / mainnet ADR. Q1/Q2/Q4/Q6 CONFIRM. Q7 (operator UI validation) = APPROVED + 3 items surfaced (T14 BUG, T15 cursor, T16 fail analysis tab).

**Canonical counts (post-S47):** 16 states / 30 events / 74 transitions / **56** reason_codes UNCHANGED (T9 added INVALID_PARAM к bybit-local enum, не main) / 66 ADRs / **51** sprint pages / 48 components

**Last shipped:** S46 v0.1.0-alpha.46 squash-merge `0fcb3ff` (React 18 + Anthropic/cyberpunk + honest close UI piece). 22 tasks. PHASE 6 5 reviewers, 1 BLOCKER + 2 HIGH + 1 MEDIUM addressed. CI GREEN.

## Phase tracking (S48 — current sprint)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | Continuous session post-S47 ship |
| 2 Brainstorm | done | trader-expert R1+R2, pre-s48-backlog v3 (24 tasks 6 buckets), pre-plan FE+architect dispatch |
| 3 Plan | done | superpowers:writing-plans → 2026-05-11-sprint-48-ui-overhaul.md commit `aa66b1a` |
| 4 Execute | in_progress | T1 done (`610530a` component subdirs) + T2 done (`77567d2` equity_curve) + T3 done (`c2c0e93` account_service) + T4 done (`6517088` balance endpoint) + T5 done (glossary_data.py RU dict + STRATEGY_TO_METRICS_MAP, 40 entries, 8 tests) + T6 done (`9c870c2` /api/glossary endpoint, 3 tests) + T7 done (`f564581` RunRecord balance fields + win_rate, 5 tests, 1063 pass) — **Bucket A 7/7 complete** — T8 done (`22abf0d` EquityChart 3-line tooltip + initialBalance prop, 0 ESLint/tsc errors, 23 Vitest + 4 Playwright pass) + T9 done (`252309b` equity-chart-all-presets E2E: 3 tests research/WFA/empty — 7/7 Playwright pass) — **Bucket B T8+T9 done** — T10 done (`c231c79` MetricsTable GATE-BLOCKING/INFORMATIONAL divider + opacity 0.55 + Glossary link + 2 new tests, 25/25 Vitest pass) + T11 done (`f97ba8e` FailAnalysisTab chip list + Glossary links, removes Bug F "Неизвестный критерий: t1", 25/25 Vitest + 7/7 Playwright pass) — T12 done (`7a46b36` DocumentationTab remove ▸ prefix 4 card titles) + T13 done (`f219d32` HistoryTab accordion expand Bug H: single-open + ESC + RunDetailsPanel + renderSummary, 25 Vitest + 7 Playwright pass) + T14 done (`2827329` HistoryTab RTL tests: accordion expand + ESC close + RU summary WFA_FAIL branch, 3/3 Vitest pass, lint+tsc clean) — T15 done (GlossaryTab base component + GlossaryEntry/GlossaryResponse types + getGlossary() API method, section-based sticky-TOC layout + dynamic per-strategy filter primitive + anchor deeplink, ~146 TSX/168 CSS lines, lint/tsc deferred к T19 — useStrategyContext T18-pending) — T16-T24 (15/24 done, 9 pending) |
| 5 Verify | pending | pytest + mypy + Vitest + Playwright + lint+tsc+build |
| 6 Review | pending | 9 reviewers parallel (frontend-developer PRIMARY + architecture-reviewer C1-C5 verify + python + bybit-api + security-auditor + trading-logic + test-engineer + data-integrity + doc) |
| 7 Sync | pending | wiki sync (T24) |
| 8 Ship | pending | tag v0.1.0-alpha.48 |
| 9 Close | pending | SPRINT_STATE between-sprints + log ship entry |

## Phase tracking (S47 — previous shipped)

| Phase | Status |
|---|---|
| 1-9 all | done v0.1.0-alpha.47 squash-merge `116f789` |

## Следующее действие

S48 PHASE 4 — T16: GlossaryTab dynamic filter (opus).

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

### S48 — UI Overhaul (9 жалоб + Bybit balance + Glossary вкладка)

**Operator pivot REVISED 2026-05-11 evening:** S48 = UI Overhaul (was NEW strategies). NEW strategies → S50.

**Содержимое S48 (~22 задачи) per `pre-s48-backlog.md` v3:**
- Bug A: tooltip знак + динамический баланс USDT
- Bug B: chart на ВСЕХ стратегиях (extend replay engine equity_curve)
- Bug C: Bybit balance fetch (real account, не фиксированные $10000)
- Bug D: informational vs gate-blocking distinction в MetricsTable
- Bug E: НОВАЯ Glossary вкладка с RU расшифровкой всех аббревиатур + dynamic per-strategy
- Bug F: упростить FailAnalysisTab к "used / not used" (детали в Glossary)
- Bug G: убрать misleading треугольник в DocumentationTab
- Bug H: HistoryTab per-row expand с balance/winrate/PnL + RU summary
- Bug I: enforce RU language pattern в чате с operator

**Pre-plan validation MANDATORY:** architecture-reviewer + frontend-developer pre-design dispatch перед PHASE 3 plan lock (operator binding "плотно подключать FE + архитектора").

### S49 — Косметика + S47 carry-overs + post-S48 buffer (~10-15 задач)

**Operator decision 2026-05-11 evening:** S49 = маленький полировочный спринт. Operator посмотрит результат S48, добавит что не понравится в S49.

- Цвета вынести в дизайн-токены (`--color-status-fail/pass/warn`)
- Шрифты + spacing scale унификация
- Empty/loading/error states
- A11y minimum (контраст + tablist ARIA)
- Vitest тесты #4 (computeMonthlyData) + #5 (VerdictPanel)
- README npm install note
- F8/Item #7/Item #10 long-standing tech debt
- MonthlyHeatmap eslint cleanup
- BacktestResponse.metrics typing tighten
- mean_reversion S15/S17 LONG-only clarification
- BybitAdapterError structured context
- FailAnalysisTab + VerdictPanel RTL render tests
- Wiki narrative cleanup
- + что operator/maintainer добавит после оператор test S48

### S50 — NEW STRATEGIES (Path B activation, deferred 2 sprints)

**S50 brainstorm (TBD после S49 ships):**
- Strategy direction (mean-reversion / trend / momentum / volatility / multi-asset / ML-augmented)
- Symbol scope (BTC only / multi-symbol)
- Timeframe (existing 4H/D OR new 5m/15m/1h)
- Acceptance criteria (re-use ADR 0014 WFA gates OR adjust)

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
