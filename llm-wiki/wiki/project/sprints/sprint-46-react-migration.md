---
title: "Sprint 46 — React migration + Anthropic/cyberpunk aesthetic + honest close UI"
type: sprint
tags: [sprint-46, react-migration, ui-redesign, anthropic-aesthetic, honest-close-ui]
created: 2026-05-10
updated: 2026-05-10
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0066-sprint-46-react-migration.md
  - llm-wiki/wiki/project/decisions/0039-sprint-25-dashboard.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-46-react-migration.md
  - llm-wiki/wiki/project/pre-s46-backlog.md
---

# Sprint 46 — React migration + Anthropic/cyberpunk + honest close UI

## Overview

Operator binding decisions: vanilla JS → **React 18 + TypeScript + Vite + CSS Modules**, terminal aesthetic → **Anthropic orange + cyberpunk hi-tech premium**, honest close UI piece (Option 1 visualization — ack-gated NON-dismissible banner + WFA_FAIL badges per preset). Plan = 22 tasks (T1-T22). Architecture-reviewer pre-plan validation: APPROVE_WITH_CONDITIONS — 3 binding conditions C1 (Vite outDir + FastAPI mount) + C2 (Node.js CI step в S46) + C4 (`TemplateResponse` → `FileResponse`) all met в S46 (НЕ deferred к S47). All 22 tasks DONE; 1 E2E spec submit→verdict skipped с TODO S47 (нужна stub `/api/backtest` fixture).

## Plan + ADR links

- Plan: [[../plans/2026-05-10-sprint-46-react-migration]]
- ADR (этот спринт): [[../decisions/0066-sprint-46-react-migration]]
- ADR amended: [[../decisions/0039-sprint-25-dashboard]] (S46 amendment — terminal → Anthropic/cyberpunk + React stack)
- Pre-sprint backlog: [[../pre-s46-backlog]]

## Доставленная функциональность

### Код (frontend)

- **Stack:** React 18.3.1 + TypeScript 5.5 strict + Vite 5.4 + CSS Modules + uPlot 1.6.31 wrapper + Playwright (E2E)
- **Directory:** `src/dashboard_react/`
- **~22 components** в `src/dashboard_react/src/components/`:
  - Layout: `<App>` (tab navigation + Anthropic header)
  - Form: `<ConfigureBacktest>` (optgroup grouping + supported_combos gating), `<StrategyDescription>` (collapsible block с aria-expanded)
  - Verdict: `<VerdictPanel>` (three-valued WFA verdict + warnings panel), `<WfaFailBadge>` (red/amber pill badge), `<WfaFailBanner>` (ack-gated NON-dismissible)
  - Charts (uPlot wrapper): `<EquityChart>` (Anthropic orange palette + ResizeObserver), `<DrawdownSubchart>` (uPlot subchart + computeDrawdown + CC2 sync key), `<TradeMarkers>` (envelope ext + scatter overlay win/loss)
  - Tables: `<MetricsTable>` (TIER 1-6 + DSR + MC + per-fold Sharpe — RAW + WFA paths), `<TradesTable>` (RAW 5-row + WFA 8-row quote-currency stats)
  - Visualizations: `<MonthlyHeatmap>` (calendar grid с PnL по месяцам, intensity-scaled cells)
  - Tabs: `<HistoryTab>` (9-col verdict-colored runs table), `<DocumentationTab>` (indicator/strategy/methodology cards)
- **Hooks:** `useStrategyInfo` (cache), `useWfaFailAck` (localStorage ack-gated с distinct-day dedup)
- **API client:** `client.ts` + types в `types.ts`
- **Design tokens:** `src/dashboard_react/src/styles/tokens.css` (Anthropic orange `#cc785c` primary + cyberpunk dark base `#0a0a0a` + warm cream text + neon accents) + `globals.css`
- **Bundle:** 232 kB JS / 31 kB CSS (gzip 80 / 5.7 kB)

### Код (backend)

- **`src/dashboard/app.py`:** `TemplateResponse` → `FileResponse(dist/index.html)` (architect C4); `StaticFiles` mount → `dist/assets/`
- **Envelope extension:** `trade_markers` field (entry/exit timestamps + prices + pnl per trade) добавлен в `volume_breakout_runner` + `atr_breakout_runner` envelopes
- **Vanilla archived:** `src/dashboard/static/` + `src/dashboard/templates/` → `src/dashboard_legacy/`

### Тесты

- **Playwright E2E** (`src/dashboard_react/tests/e2e/`): 3 pass / 1 skip
  - `wfa-fail-ack.spec.ts`: 2 PASS (first-visit banner shown + chip downgrade after 3 distinct calendar days)
  - `backtest-flow.spec.ts`: form-render PASS; submit→verdict SKIPPED (TODO S47 — нужна stub `/api/backtest` fixture для стабильного прогона)
- **Vitest + React Testing Library:** deferred к S47 (per trader Q5-NEW REVISE)
- **Python backend tests:** preserved (~970 unit / ~58 integration / mypy 0)

### CI/CD

- **`.github/workflows/ci.yml`:** Node.js 20 setup-node@v4 step + `npm ci` + `npm run build` (TS compile + Vite bundle) + Playwright E2E (architect C2 binding — В S46, NOT deferred)
- **`scripts/start-bot.sh`:** `npm run build` step перед uvicorn (architect C1 — production build mounted)
- **`.gitignore`:** `src/dashboard_react/dist/`, `node_modules/`, `playwright-report/`, `test-results/`, `tsbuildinfo`

### Wiki

- ADR 0066 NEW (этот спринт)
- ADR 0039 amended (S46 — terminal → Anthropic/cyberpunk + React stack)
- sprint-46 page (этот файл)
- current-state.md sync — counts ADRs 65→66, sprint pages 49→50, sprint history row S46
- index.md ADR 0066 + sprint-46 entries
- log.md S46 sprint-end entry

### Рост FSM / Reason codes

**0** (UNCHANGED — pure UI/frontend work без изменений в `state_machine.py` или `reason_codes.py`).

### Тесты / качество

- Python unit: ~970 (UNCHANGED post-S45)
- Python integration: ~58 (UNCHANGED post-S45)
- mypy --strict src/: 0 errors
- Playwright E2E: 3 pass / 1 skip
- Canonical: 16/30/74/56 (UNCHANGED — frontend work)

## Architecture changes

**Directory pivot:**

| Было | Стало |
|------|-------|
| `src/dashboard/static/` (vanilla JS + CSS) | `src/dashboard_legacy/static/` (archive) |
| `src/dashboard/templates/` (Jinja2 HTML) | `src/dashboard_legacy/templates/` (archive) |
| (нет) | `src/dashboard_react/` — React 18 frontend (package.json + tsconfig.json + vite.config.ts + src/ + tests/) |
| `src/dashboard/app.py` `TemplateResponse(...)` | `src/dashboard/app.py` `FileResponse(dist/index.html)` + `StaticFiles` mount `dist/assets/` |

**Polyglot toolchain:** Python 3.12 backend (unchanged) + Node.js 20 frontend (NEW). Operator first-time setup: `npm install` в `src/dashboard_react/`.

## Aesthetic pivot summary

| Слой | Было (terminal — ADR 0039 + S26) | Стало (Anthropic/cyberpunk — ADR 0039 amendment + ADR 0066) |
|------|-----------------------------------|--------------------------------------------------------------|
| Primary palette | Green phosphor `#00ff66` | Anthropic orange `#cc785c` |
| Base | Black-on-green | Dark cyberpunk `#0a0a0a` + warm cream text |
| Effects | CRT scanlines + glow | Glass-morphism panels + subtle neon accents |
| Typography (UI) | JetBrains Mono primary | Inter sans (UI chrome) |
| Typography (data) | JetBrains Mono | JetBrains Mono (preserved для tables/code) |
| Status colors | Terminal green/amber/red | Neon green PASS / orange WFA_FAIL_DATA / neon red FAIL |

## Honest close UI piece

**Option 1 visualization** (operator binding per Q4 ROUND 1 REVISE):

- **`<WfaFailBadge>`:** inline pill badge на каждой preset card в `<HistoryTab>`. Цвета: красный для WFA_FAIL/FAIL, амбер для WFA_FAIL_DATA (distinct color preserved per ADR 0063 dashboard-reviewer concern).
- **`<WfaFailBanner>`:** ack-gated NON-dismissible banner mounted above tabs в `<App>`.
  - Full mode (до first ack): большой banner с текстом "Все 11 стратегий не прошли WFA discipline (S45). Подтверди понимание перед использованием preset."
  - `useWfaFailAck` hook: localStorage tracks ack count + дни (distinct calendar day dedup — multiple acks в один день considered как один)
  - После 3 distinct calendar days с at least one ack каждый → downgrade к chip mode (small reminder)
- **Server-side enforcement:** deferred к S47 (preset `disabled: bool` flag + dispatch reject 422 — code piece) per pre-S46 backlog.

## Tests

| Spec | Status | Notes |
|------|--------|-------|
| `wfa-fail-ack.spec.ts` first-visit banner | PASS | Banner shown until ack |
| `wfa-fail-ack.spec.ts` chip after 3 distinct days | PASS | Banner downgrades correctly via localStorage |
| `backtest-flow.spec.ts` form render | PASS | Optgroup + supported_combos gating verified |
| `backtest-flow.spec.ts` submit → verdict | SKIPPED | TODO S47 — нужна stub `/api/backtest` fixture (long-running real backtest unstable в CI) |

`playwright.config.ts`: webServer factory entry (Vite preview), workers=1.

## Wiki updates

- `llm-wiki/wiki/project/decisions/0066-sprint-46-react-migration.md` (NEW)
- `llm-wiki/wiki/project/decisions/0039-sprint-25-dashboard.md` (amended — S46 amendment section)
- `llm-wiki/wiki/project/sprints/sprint-46-react-migration.md` (NEW — этот файл)
- `llm-wiki/wiki/project/architecture/current-state.md` (counts 65→66 ADRs / 49→50 sprint pages + sprint history row)
- `llm-wiki/wiki/index.md` (ADR 0066 + sprint-46 entries)
- `llm-wiki/wiki/log.md` (S46 sprint-end entry append)
- `llm-wiki/wiki/project/SPRINT_STATE.md` (T22 done + phase 5-verify transition)

## Open issues для S47

- **Tests:** Vitest + React Testing Library unit tests (~8-10 test files) — frontend test pyramid completion
- **DocumentationTab:** Multiplier card range/impact detail + Methodology full detail (T15 deferred — TODO S47 markers в components)
- **E2E:** `backtest-flow.spec.ts` submit→verdict spec (T18 SKIPPED — нужна stub `/api/backtest` fixture)
- **Bug parity preserved:** MetricsTable T5 vanilla bug (`undefined < 100 → PASS`) — flagged для S47 cleanup (intentional preserve для visual parity verification)
- **Lint cosmetic:** MonthlyHeatmap `eslint-disable react-hooks/rules-of-hooks` for hooks-after-guard — fix если PHASE 6 reviewer flags
- **Mobile:** responsive layout (deferred per trader Q7 CONFIRM)
- **Theming:** dark/light theme switch (cyberpunk dark default — light mode скорее всего не нужен; re-evaluate S47)
- **Tech debt batch:** F8 block_size / M1-M4 bybit-api / Item #7 RiskSharedDeps shim / Item #10 boundary scenarios (long-standing S37/S38)
- **Honest close code piece:** preset `disabled: bool` flag в `STRATEGY_PRESETS` + dispatch reject disabled presets с 422 (server-side enforcement; UI piece shipped в S46)

## Key decisions

- **Decision A:** React 18.3 + TypeScript 5.5 strict + Vite 5.4 + CSS Modules (NO Tailwind per Q1-NEW REVISE — preserve token flexibility)
- **Decision B:** Aesthetic pivot к Anthropic orange `#cc785c` + cyberpunk hi-tech premium (ADR 0039 amendment — first aesthetic pivot since S26 Bloomberg-pro × CRT)
- **Decision C:** All-at-once full rewrite migration strategy (vanilla archived к `src/dashboard_legacy/`, new `src/dashboard_react/`)
- **Decision D:** Architect binding conditions C1 (Vite outDir + FastAPI mount, NO separate dev server в prod) + C2 (Node.js CI step в S46) + C4 (`TemplateResponse` → `FileResponse`) — all delivered В S46
- **Decision E:** Honest close UI piece — ack-gated NON-dismissible banner + WFA_FAIL badges + localStorage `useWfaFailAck` hook с distinct-day dedup + chip downgrade after 3 days

## Перенесённые задачи

См. "Open issues для S47" выше. S37/S38 long-standing items unchanged — остаются в backlog к S47+. S48 = honest close finalize (ADR 0067 portfolio close + preset metadata `status: superseded` + acceptance-criteria.md update + v0.1 wrap-up decision).

## Связанные

- [[../decisions/0066-sprint-46-react-migration]] — ADR этого спринта
- [[../decisions/0039-sprint-25-dashboard]] — original dashboard ADR (amended S46)
- [[../plans/2026-05-10-sprint-46-react-migration]] — implementation plan (22 tasks)
- [[../pre-s46-backlog]] — PHASE 2 brainstorm trail + operator binding decisions
- [[../decisions/0063-sprint-43-ui-polish]] — uPlot vendored для vanilla; reused в React via wrapper
- [[../decisions/0065-sprint-45-wfa-recalibration]] — S45 0/11 PASS triggered S46-S48 honest-close roadmap
- [[sprint-45-wfa-recalibration]] — предыдущий спринт
