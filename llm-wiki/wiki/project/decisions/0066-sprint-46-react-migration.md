---
title: "0066. Sprint 46 — React migration + Anthropic/cyberpunk aesthetic pivot"
type: decision
tags: [adr, sprint-46, react-migration, ui-redesign, aesthetic-pivot, anthropic-style]
created: 2026-05-10
updated: 2026-05-10
status: accepted
sources:
  - llm-wiki/wiki/project/pre-s46-backlog.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-46-react-migration.md
---

# 0066. Sprint 46 — React migration + Anthropic/cyberpunk aesthetic pivot

**Status:** accepted
**Date:** 2026-05-10

## Контекст

S45 closed honest verdict 0/11 WFA_PASS. S46-S48 roadmap distributes 3 honest-close options across 3 sprints. S46 = UI redesign + honest close UI piece.

Operator binding decisions (после ROUND 1 + ROUND 2 brainstorm с trader-expert + override aesthetic/framework verdicts):

1. **Framework:** vanilla JS → React 18 + TypeScript strict + Vite + CSS Modules
2. **Aesthetic:** terminal (ADR 0039 LOCKED дашборд-дизайн) → Anthropic orange + cyberpunk hi-tech premium
3. **Honest close UI:** ack-gated NON-dismissible banner + WFA_FAIL badges per preset card

Architecture-reviewer pre-plan validation: **APPROVE_WITH_CONDITIONS** — 3 binding conditions C1+C2+C4 incorporated в plan + delivered в S46.

## Решения

### Decision A — React 18 stack

React 18.3.1 + TypeScript 5.5 strict + Vite 5.4 + CSS Modules + uPlot 1.6.31 wrapper. **NO Tailwind** (preserves design token flexibility per trader-expert Q1-NEW REVISE — параллельно даёт оператору возможность tweak palette без Tailwind config rebuild). Playwright E2E only S46; Vitest+RTL → S47.

### Decision B — Aesthetic pivot к Anthropic + cyberpunk (ADR 0039 amendment)

ADR 0039 (sprint-25 dashboard) amendment. Anthropic orange (`#cc785c`) primary, dark cyberpunk base (`#0a0a0a`), warm cream text, glass-morphism panels, neon accents. Preserves analytical seriousness через monospace data fonts (JetBrains Mono для tables/code), Inter sans для UI chrome.

Rationale: оператор показал Claude Signal cyberpunk references в S43 era + explicit S46 request "стилистика антропика и клад-кода".

### Decision C — Migration strategy

**All-at-once full rewrite** (НЕ inкрементальный port). Vanilla `src/dashboard/static/` + `src/dashboard/templates/` archived к `src/dashboard_legacy/`. New `src/dashboard_react/` с React 18 stack. FastAPI backend Python остаётся в `src/dashboard/` (imports unchanged).

Architect prescribed folder structure:
- `src/dashboard/` — Python backend (NOT renamed)
- `src/dashboard_react/` — React frontend с `package.json` inside
- `src/dashboard_legacy/` — archived vanilla
- `dist/` в `.gitignore`, built by `start-bot.sh` перед uvicorn

### Decision D — Architect binding conditions (delivered в S46)

- **C1 (HIGH):** Vite `outDir` → `src/dashboard_react/dist/`. FastAPI mounts `dist/`. NO separate Vite dev server `:5173` в production (CORS violation per ADR 0039 CC3 localhost-only). Dev `npm run dev` only с temp CORS env flag.
- **C2 (HIGH):** Node.js CI step в `.github/workflows/ci.yml` **AS PART OF S46** (NOT deferred к S47). Иначе broken TS compile = silent runtime failure для оператора.
- **C4 (MEDIUM):** `app.py` `TemplateResponse` → `FileResponse(dist/index.html)`. Jinja2 несовместим с content-hashed React build (Vite output `index-<hash>.js`).

### Decision E — Honest close UI piece (Option 1 visualization)

**Ack-gated NON-dismissible banner** per trader-expert Q4 ROUND 1 REVISE.

- `useWfaFailAck` localStorage hook — count ack events + день дедуп (одна запись per calendar day independently от количества кликов)
- Full banner shows до first ack
- После 3 distinct calendar days с at least one ack каждый → downgrade к "chip" mode (small reminder)
- WFA_FAIL badges на preset cards в HistoryTab
- WFA_FAIL_DATA distinct color preserved (S43 dashboard-reviewer concern из ADR 0063)

Banner text верстается RU: "Все 11 стратегий не прошли WFA discipline (S45). Подтверди понимание перед использованием preset."

## Последствия

**Pros:**
- Modern React stack — easier extension future (component composition vs DOM mutation)
- Anthropic premium aesthetic = professional brand alignment с операторским видением
- Honest close UX disciplined (ack-gated НЕ dismissible — оператор не может скрыть disclosure случайным кликом)
- Architect binding conditions met = no silent runtime failures (CI catches TS compile errors)
- TypeScript strict — type-safe envelope contracts с FastAPI backend

**Cons:**
- Polyglot toolchain (Python backend + Node.js frontend) — `npm install` step required first time
- Bigger sprint (~22 tasks) vs typical S40-S45 (~8-12 tasks)
- Vanilla dashboard archived → operator должен `npm install` first time
- ADR 0039 amendment — first aesthetic pivot since S26 (Bloomberg-pro × CRT terminal)
- Bundle size 232 kB JS / 31 kB CSS (gzip 80 / 5.7 kB) — acceptable но больше vanilla

**Carry-overs к S47:**
- Vitest + React Testing Library unit tests (~8-10 test files)
- Multiplier card range/impact detail (T15 deferred — TODO S47 marker в `DocumentationTab`)
- Methodology full detail card (T15 deferred — TODO S47 marker)
- `backtest-flow.spec.ts` E2E submit→verdict (T18 SKIPPED — нужна stub `/api/backtest` fixture для стабильного прогона)
- MetricsTable T5 vanilla parity bug (`undefined < 100 → PASS`) — preserved from vanilla, flagged для S47 cleanup
- MonthlyHeatmap `eslint-disable react-hooks/rules-of-hooks` for hooks-after-guard (cosmetic — fix если PHASE 6 reviewer flags)
- Mobile responsive layout
- Dark/light theme switch (cyberpunk dark default; light mode скорее всего не нужен — re-evaluate S47)
- Tech debt batch (F8/M1-M4/Item 7/Item 10 — long-standing S37/S38)
- Honest close code piece (preset `disabled: bool` flag в `STRATEGY_PRESETS`, dispatch reject disabled presets с 422)

**Carry-overs к S48:**
- Live trade feed widget (deferred S49+ — YAGNI per 0 live trades currently)
- Honest close finalize ADR 0067 — formal portfolio close decision document
- v0.1 wrap-up (semver bump к v0.1.0 stable? OR keep alpha indefinitely?)

## Verification

- React build succeeds — Vite `npm run build` outputs `dist/` без errors
- All TypeScript types strict — `tsc --noEmit` clean
- Playwright E2E PASS:
  - `wfa-fail-ack.spec.ts` 2/2 (first-visit banner + chip downgrade after 3 days)
  - `backtest-flow.spec.ts` form-render PASS; submit→verdict SKIPPED (carry-over S47)
- FastAPI mounts `dist/` корректно — `FileResponse(dist/index.html)` + `StaticFiles` mount `/assets/` (architect C1+C4)
- Node.js CI step runs (architect C2) — `.github/workflows/ci.yml` setup-node@v4 + npm ci + npm run build + Playwright

## Связанные

- [[../sprints/sprint-46-react-migration]]
- [[../plans/2026-05-10-sprint-46-react-migration]]
- [[../pre-s46-backlog]]
- [[0039-sprint-25-dashboard]] (amended S46 — terminal → Anthropic/cyberpunk)
- [[0063-sprint-43-ui-polish]] (uPlot vendored for vanilla; reused в React via wrapper)
- [[0064-sprint-44-wfa-retrofit]] (WFA_FAIL verdicts surfaced в honest-close UI)
- [[0065-sprint-45-wfa-recalibration]] (S45 0/11 PASS triggered S46-S48 honest-close roadmap)
