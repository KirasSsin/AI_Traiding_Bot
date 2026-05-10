---
title: Pre-S46 Backlog — React migration + Anthropic/cyberpunk aesthetic + S43 carry-overs + honest close UI
type: backlog
tags: [sprint-46, react-migration, ui-redesign, aesthetic-pivot, anthropic-style, cyberpunk]
created: 2026-05-10
updated: 2026-05-10
status: active
sources:
  - llm-wiki/wiki/project/decisions/0040-sprint-26-dashboard-frontend-design.md
  - llm-wiki/wiki/project/decisions/0063-sprint-43-ui-polish.md
  - llm-wiki/wiki/project/decisions/0065-sprint-45-wfa-recalibration.md
---

# Pre-S46 Backlog

## Контекст

S45 shipped quant discipline + recalibration. Honest verdict: 0/11 WFA_PASS. S46-S48 roadmap distributes 3 honest-close options across 3 sprints. S46 = UI redesign + honest close UI piece.

**Operator decisions (binding):**
1. Framework migration: vanilla JS → **React 18 + TypeScript + Vite + CSS Modules**
2. Aesthetic pivot: terminal (ADR 0040 LOCKED) → **Anthropic/Claude-code style — оранжевая палитра + cyberpunk hi-tech premium**
3. Sprint scope: include S43 carry-overs + earlier S46 expansion + honest close UI piece. Defer items расписать в backlog для следующих спринтов.

## S46 PHASE 2 Brainstorming Trail

### ROUND 1 (trader-expert)

| Q | Topic | Verdict | Final |
|---|-------|---------|-------|
| Q1 | Framework | CONFIRM keep vanilla | **OPERATOR OVERRIDE → React** |
| Q2 | Aesthetic | CONFIRM keep terminal | **OPERATOR OVERRIDE → Anthropic/cyberpunk pivot** |
| Q3 | Scope order | CONFIRM honest close → S43 carry → expansion | locked |
| Q4 | WFA_FAIL UX | REVISE → ack-gated NON-dismissible banner | locked |
| Q5 | Integration depth | CONFIRM visualization only S46; server-side S47 | locked |
| Q6 | Live feed | CONFIRM defer S49+ | locked |
| Q7 | Mobile | CONFIRM defer S47+ | locked |

### ROUND 2 (trader-expert после React override)

| Q | Topic | Verdict | Final |
|---|-------|---------|-------|
| Q1-NEW | React stack | REVISE → CSS Modules не Tailwind | locked |
| Q2-NEW | Aesthetic confirm | CONFIRM keep terminal | **OPERATOR OVERRIDE → Anthropic/cyberpunk** |
| Q3-NEW | Migration strategy | CONFIRM all-at-once | locked |
| Q4-NEW | FastAPI keep | CONFIRM | locked |
| Q5-NEW | Testing | REVISE → Playwright E2E only S46; Vitest+RTL → S47 | locked |
| Q6-NEW | Honest close React | CONFIRM | locked |
| Q7-NEW | Task count | EXPAND → ~20-25 tasks | locked |

### Architecture-reviewer pre-plan validation

**Verdict:** APPROVE_WITH_CONDITIONS — 3 binding conditions:
- **C1 (HIGH):** ADR 0066 fix Vite `outDir` → `src/dashboard_react/dist/`. FastAPI mounts `dist/`. NO separate Vite dev server `:5173` в production (CORS violation per ADR 0039). Dev `npm run dev` only с temp CORS env flag.
- **C2 (HIGH):** Node.js CI step в `ci.yml` AS PART OF S46 (NOT S47). Иначе broken TS compile = silent runtime failure.
- **C4 (MEDIUM):** `app.py` `TemplateResponse` → `FileResponse` (Jinja2 incompatible с content-hashed React build).

**Folder structure (architect prescribed):**
- `src/dashboard/` — Python backend (NOT renamed)
- `src/dashboard_react/` — React frontend с `package.json` inside
- `src/dashboard_legacy/` — archived vanilla
- `dist/` в `.gitignore`, built by `start-bot.sh` перед uvicorn

**Reviewer matrix:** `dashboard-reviewer` нужно обновить под React-scope ИЛИ роль передать `frontend-developer` agent (operator created `~/.claude/agents/frontend-developer.md`, model=opus, color=cyan).

## S46 Scope (locked)

### In-scope (~22 tasks)

1. **React infrastructure** (5 tasks):
   - `src/dashboard_react/` создан с Vite + TypeScript strict + CSS Modules + uPlot wrapper
   - `package.json` (React 18, TypeScript, Vite, uPlot, Playwright)
   - `tsconfig.json` (strict mode, no implicit any)
   - `vite.config.ts` (outDir → `src/dashboard_react/dist/`)
   - `.eslintrc` + `prettier` config
   - `scripts/start-bot.sh` updated — `npm run build` перед uvicorn

2. **CI/CD updates** (1 task):
   - `.github/workflows/ci.yml` — Node.js setup + `npm ci` + `npm run build` + Playwright E2E step (per architect C2)

3. **FastAPI backend integration** (1 task):
   - `app.py` — `TemplateResponse` → `FileResponse(dist/index.html)` per architect C4
   - StaticFiles mount → `dist/` directory

4. **Design token system** (2 tasks):
   - `src/dashboard_react/src/styles/tokens.css` — Anthropic orange palette (#cc785c primary, dark base #0a0a0a, premium accents)
   - Cyberpunk hi-tech effects: subtle gradients, animated panel borders, glass-morphism backgrounds, premium shadows
   - ADR 0040 amendment — pivot terminal → Anthropic/cyberpunk

5. **Core component migration** (8 tasks):
   - `<App>` — top-level layout
   - `<ConfigureBacktest>` — strategy + symbol + interval form (port S43 logic)
   - `<StrategyDescription>` — collapsible description block (port S43)
   - `<VerdictPanel>` — three-valued WFA verdict с three-color mapping (port S44)
   - `<EquityChart>` — uPlot wrapper component (port S43)
   - `<MetricsTable>` — TIER 1-6 + DSR + MC table
   - `<TradesTable>` — trade stats
   - `<HistoryTab>` + `<DocumentationTab>`

6. **New features (S43 carry-overs)** (4 tasks):
   - `<DrawdownSubchart>` — uPlot stacked y-series (architect CC2 — share x-axis с EquityChart)
   - `<TradeMarkers>` — entry/exit dots overlay (envelope API extension needed)
   - `<MonthlyHeatmap>` — calendar grid с PnL по месяцам
   - WFA_FAIL_DATA distinct color (S43 dashboard-reviewer concern)

7. **Honest close UI piece (Option 1 visualization)** (3 tasks):
   - `<WfaFailBadge>` — red badge per preset card
   - `<WfaFailBanner>` — ack-gated NON-dismissible banner с localStorage hook (count + day dedup, chip downgrade after 3 distinct days)
   - Banner text: "Все 11 стратегий не прошли WFA discipline (S45). Подтверди понимание перед использованием preset."

8. **Tests** (2 tasks):
   - Playwright E2E — critical flows (run backtest, verify result render, verify ack-gate flow)
   - Vitest+RTL unit tests → S47 (per trader Q5-NEW REVISE)

9. **Wiki sync** (1 task):
   - ADR 0066 (S46 React migration + aesthetic pivot)
   - ADR 0040 amendment (terminal → Anthropic/cyberpunk)
   - sprint-46 page + index.md + log.md + current-state.md

### Deferred к S47

- Vitest + React Testing Library unit tests (~8-10 test files)
- Mobile responsive layout
- Dark/light theme switch (cyberpunk уже dark; light mode скorее всего не нужен — defer indefinitely OR re-evaluate в S47)
- Tech debt batch (F8/M1-M4/Item 7/Item 10)
- Honest close code piece (preset disabled flag, server-side 422 reject)

### Deferred к S48

- Live trade feed widget (YAGNI — 0 live trades)
- Honest close finalize (ADR 0067 portfolio close)
- v0.1 wrap-up

### Deferred к S49+

- Live feed widget when actual live trading happens
- 12mo MAINNET-promotion ADR (когда δ live data accumulates)

## Cross-cutting concerns

- **Architect C1 BINDING:** Vite outDir + FastAPI mount, NO separate dev server в prod
- **Architect C2 BINDING:** Node.js CI step в S46
- **Architect C4 BINDING:** TemplateResponse → FileResponse
- **Architect CC2:** Drawdown subchart uPlot stacked OR sync plugin (NOT separate instance)
- **Architect CC3:** Per-trade markers нуждаются envelope API extension (entry+exit timestamps)
- **Operator pivot CC:** Anthropic palette = #cc785c (warm coral) primary, dark cyberpunk base, premium accents. ADR 0040 amendment mandatory
- **Reviewer matrix CC:** dashboard-reviewer → передать frontend-developer agent OR update под React patterns

## Escalations к user

ALL RESOLVED:
- ESC-1 aesthetic: **Anthropic/cyberpunk pivot** (operator binding)
- ESC-2 framework: **React** (operator binding)
- ESC-3 ADR numbering: S46=0066, S48=0067, plan через PHASE 3

## Files identified для edit (PHASE 3 plan input)

CREATE:
- `src/dashboard_react/package.json`
- `src/dashboard_react/tsconfig.json`
- `src/dashboard_react/vite.config.ts`
- `src/dashboard_react/.eslintrc`
- `src/dashboard_react/index.html`
- `src/dashboard_react/src/main.tsx`
- `src/dashboard_react/src/App.tsx`
- `src/dashboard_react/src/components/*.tsx` (8 components above + 4 new + 2 honest close = ~14 components)
- `src/dashboard_react/src/styles/tokens.css` (Anthropic palette)
- `src/dashboard_react/src/styles/globals.css`
- `src/dashboard_react/src/api/client.ts`
- `src/dashboard_react/src/hooks/useStrategyInfo.ts`
- `src/dashboard_react/src/hooks/useWfaFailAck.ts`
- `src/dashboard_react/playwright.config.ts`
- `src/dashboard_react/tests/e2e/*.spec.ts`

MOVE:
- `src/dashboard/static/` → `src/dashboard_legacy/static/` (archive vanilla)
- `src/dashboard/templates/` → `src/dashboard_legacy/templates/`

MODIFY:
- `src/dashboard/app.py` — TemplateResponse → FileResponse, StaticFiles → dist/
- `scripts/start-bot.sh` — `npm run build` step
- `.github/workflows/ci.yml` — Node.js setup
- `.gitignore` — `dist/`, `node_modules/`
- `pyproject.toml` — no change (Python deps unchanged)

CREATE wiki:
- `llm-wiki/wiki/project/decisions/0066-sprint-46-react-migration-aesthetic-pivot.md`
- `llm-wiki/wiki/project/sprints/sprint-46-react-migration.md`

MODIFY wiki:
- `llm-wiki/wiki/project/decisions/0040-sprint-26-dashboard-frontend-design.md` — amendment (terminal → Anthropic/cyberpunk)
- `llm-wiki/wiki/project/architecture/current-state.md` — header + counts
- `llm-wiki/wiki/index.md`
- `llm-wiki/wiki/log.md`
- `llm-wiki/wiki/project/SPRINT_STATE.md`

## Next phase

PHASE 3 — `superpowers:writing-plans` skill creates `2026-05-10-sprint-46-react-migration.md` plan. Auto-invoke `superpowers:subagent-driven-development` после plan saved (per kit override S45).
