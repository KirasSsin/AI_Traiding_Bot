---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-11  # S46 SHIPPED → between-sprints; SPRINT_STATE trimmed S5-S45 history → log.md + sprint-NN pages
sprint: 46
phase: between-sprints
branch: main
tag: v0.1.0-alpha.46
---

## Текущий статус

**Sprint 46 SHIPPED** — squash-merge `0fcb3ff`, tag `v0.1.0-alpha.46`. Branch `feature/sprint-46-react-migration` deleted. Phase = between-sprints.

**S46 deliverables:**
- React 18 + TS strict + Vite + CSS Modules dashboard (~22 components, 235 kB JS / 31 kB CSS gzip 81/5.7)
- Anthropic orange (#cc785c) + cyberpunk dark base aesthetic (ADR 0039 amended)
- Honest close UI: WfaFailBadge per preset + ack-gated NON-dismissible WfaFailBanner с distinct-day dedup + chip downgrade after 3 ack days
- Vanilla archived `src/dashboard_legacy/`; FastAPI serves React build via FileResponse
- envelope `trade_markers` extension (5 parallel arrays per trade) for EquityChart scatter overlay
- CI Node.js 20 + npm ci + TS build + Playwright E2E (3 pass / 1 skip)
- ADRs: 0066 NEW, 0039 amended

**Architect bindings (ALL MET per architecture-reviewer PHASE 6):** C1 (outDir+mount) / C2 (CI Node) / C4 (FileResponse) / CC2 (uPlot.sync) / CC3 (envelope ext)

**Canonical counts:** 16 states / 30 events / 74 transitions / 56 reason_codes / 66 ADRs / 50 sprint pages / 48 components

## Следующее действие

`/sprint-orient` для S47 brainstorm OR explicit operator pivot. PHASE 1 trigger когда operator says "S47" / "next sprint" / "carry-overs".

## S47-S48 ROADMAP (operator decision 2026-05-10)

### S47 — Tech debt batch + honest close code piece + S46 carry-overs (~14-18 tasks)

**S46 PHASE 6 carry-overs (priority):**
- Vitest + React Testing Library unit tests (test-engineer priority list: `computeDrawdown` invariants → `computeMonthlyData` → `useWfaFailAck` hook → `MetricsTable` helpers → `VerdictPanel` mapping)
- `backtest-flow.spec.ts` activate via `page.route('/api/backtest', ...)` mock fixture
- SPA catch-all FastAPI route (architect MEDIUM — needed if React Router added)
- React asset HTTP cache headers (python-reviewer MEDIUM)
- Multiplier card range/impact + Methodology full detail (T15 TODO markers)
- MetricsTable T5 vanilla bug parity cleanup (`undefined < 100 → PASS`)
- README npm install note
- A11y: tablist ARIA + `--color-text-disabled` contrast

**S37/S38 long-standing tech debt (Option 3):**
- F8 block_size constant unification (quant LOW)
- M1-M4 bybit-api fixes: retCode taxonomy / pybit response shape guards / WS data isinstance / `__repr__` secret redaction (security)
- Item #7 RiskSharedDeps backward-compat shim cleanup
- Item #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended boundary scenarios

**S44 reviewer follow-ups:**
- DSR ∈ [0,1] property test (test-engineer C2)
- WindowSplitter k_folds=1 edge case
- numpy RuntimeWarning suppress (pytest filterwarnings)
- Cross_trial_log read failure test (test-engineer C4)
- Trading-logic C2-C4 minor (sigma_sr docs, n_eff comment, trial_oos_sharpe annualization)

**Honest close Option 1 code piece:** preset `disabled: bool` flag в STRATEGY_PRESETS, dispatch reject disabled presets с 422

**S45 quant follow-ups:** n_trials assert (>=1), sprint int/str type test

**Reviewers PHASE 6:** quant-stats + trading-logic + python + test + doc + bybit-api-reviewer + security-auditor (M4 secret redaction)

### S48 — Honest close finalize + polish leftover (~8-10 tasks)

- **Option 1 finalize (honest portfolio close per ESC-1):** ADR 0067 — formal portfolio close decision; mark all 11 presets `status: superseded`; update acceptance-criteria.md + current-state.md + README с честным state; archive presets к `_legacy/` OR keep selectable с big WARNING (operator brainstorm decision)
- **UI polish leftover:** anything deferred from S46 (mobile responsive / theme switch / live feed re-evaluate)
- **Tech debt leftover:** anything deferred from S47
- **v0.1 wrap-up:** semver bump к v0.1.0 stable? OR keep alpha indefinitely? Operator decision

**Reviewers PHASE 6:** doc-reviewer (mandatory ADR 0067) + trading-logic + python

### Carry-overs к S49+

- 12mo MAINNET-promotion ADR (нужен δ live data accumulation)
- Live trade feed widget (deferred S49+ per YAGNI — 0 live trades)
- Path B (new strategies) — operator excluded entirely

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
