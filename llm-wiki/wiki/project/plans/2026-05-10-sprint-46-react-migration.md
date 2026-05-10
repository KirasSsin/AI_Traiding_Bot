---
title: "Sprint 46 — React migration + Anthropic/cyberpunk aesthetic + S43 carry-overs + honest close UI"
type: plan
tags: [sprint-46, react-migration, ui-redesign, aesthetic-pivot, anthropic-style, cyberpunk]
created: 2026-05-10
updated: 2026-05-10
status: ready
sources:
  - llm-wiki/wiki/project/pre-s46-backlog.md
---

# Sprint 46 — React Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate dashboard от vanilla JS к React 18 + TypeScript + Vite + CSS Modules. Pivot terminal aesthetic к Anthropic orange + cyberpunk hi-tech premium. Implement S43 deferred features (drawdown subchart, per-trade markers, monthly heatmap) + honest close UI piece (badges + ack-gated banner).

**Architecture:** New `src/dashboard_react/` (Vite + TS strict + CSS Modules + uPlot wrapper). Vanilla `src/dashboard/static/` + `templates/` archived к `src/dashboard_legacy/`. FastAPI backend unchanged — `app.py` serves React build via `FileResponse(dist/index.html)` + `StaticFiles(dist/)`. CI adds Node.js step. `start-bot.sh` runs `npm run build` перед uvicorn (per architect C1+C2+C4 binding conditions). All React components dispatched через `frontend-developer` agent (opus model).

**Tech Stack:** React 18.3+, TypeScript 5.x strict, Vite 5.x, CSS Modules (no Tailwind — preserves design tokens flexibility), uPlot 1.6.31 (vendored S43), Playwright 1.x (E2E), Python 3.12 (FastAPI backend unchanged). Vitest+RTL deferred к S47.

**Branch:** `feature/sprint-46-react-migration`

**Models:** opus T1 (React infra architecture-heavy), opus T2 (design token + aesthetic pivot judgment), opus T13 (ADRs), sonnet T3-T12, T14-T22.

---

## Architect Binding Conditions (MUST satisfy)

- **C1 (HIGH):** Vite `outDir` → `src/dashboard_react/dist/`. FastAPI mounts `dist/`. NO separate Vite dev server `:5173` в production (CORS violation per ADR 0039). Dev `npm run dev` only с temp CORS env flag.
- **C2 (HIGH):** Node.js CI step в `ci.yml` AS PART OF S46 (NOT S47).
- **C4 (MEDIUM):** `app.py` `TemplateResponse` → `FileResponse(dist/index.html)`.

## File Trace Map (PHASE 3 step 1a HARD-GATE)

| Path | Action | Tasks |
|------|--------|-------|
| `src/dashboard_react/package.json` | CREATE | T1 |
| `src/dashboard_react/tsconfig.json` | CREATE | T1 |
| `src/dashboard_react/vite.config.ts` | CREATE | T1 |
| `src/dashboard_react/.eslintrc.json` | CREATE | T1 |
| `src/dashboard_react/.prettierrc` | CREATE | T1 |
| `src/dashboard_react/index.html` | CREATE | T1 |
| `src/dashboard_react/src/main.tsx` | CREATE | T1 |
| `src/dashboard_react/src/App.tsx` | CREATE | T3 |
| `src/dashboard_react/src/styles/tokens.css` | CREATE | T2 |
| `src/dashboard_react/src/styles/globals.css` | CREATE | T2 |
| `src/dashboard_react/src/api/client.ts` | CREATE | T4 |
| `src/dashboard_react/src/api/types.ts` | CREATE | T4 |
| `src/dashboard_react/src/hooks/useStrategyInfo.ts` | CREATE | T5 |
| `src/dashboard_react/src/hooks/useWfaFailAck.ts` | CREATE | T5 |
| `src/dashboard_react/src/components/ConfigureBacktest.tsx` | CREATE | T6 |
| `src/dashboard_react/src/components/StrategyDescription.tsx` | CREATE | T7 |
| `src/dashboard_react/src/components/VerdictPanel.tsx` | CREATE | T8 |
| `src/dashboard_react/src/components/EquityChart.tsx` | CREATE | T9 |
| `src/dashboard_react/src/components/DrawdownSubchart.tsx` | CREATE | T10 |
| `src/dashboard_react/src/components/TradeMarkers.tsx` | CREATE | T11 |
| `src/dashboard_react/src/components/MonthlyHeatmap.tsx` | CREATE | T12 |
| `src/dashboard_react/src/components/MetricsTable.tsx` | CREATE | T13 |
| `src/dashboard_react/src/components/TradesTable.tsx` | CREATE | T14 |
| `src/dashboard_react/src/components/HistoryTab.tsx` | CREATE | T15 |
| `src/dashboard_react/src/components/DocumentationTab.tsx` | CREATE | T15 |
| `src/dashboard_react/src/components/WfaFailBadge.tsx` | CREATE | T16 |
| `src/dashboard_react/src/components/WfaFailBanner.tsx` | CREATE | T17 |
| `src/dashboard_react/playwright.config.ts` | CREATE | T18 |
| `src/dashboard_react/tests/e2e/backtest-flow.spec.ts` | CREATE | T18 |
| `src/dashboard_react/tests/e2e/wfa-fail-ack.spec.ts` | CREATE | T18 |
| `src/dashboard/app.py` | MODIFY (FileResponse + StaticFiles dist/) | T19 |
| `src/dashboard/static/` → `src/dashboard_legacy/static/` | MOVE | T20 |
| `src/dashboard/templates/` → `src/dashboard_legacy/templates/` | MOVE | T20 |
| `scripts/start-bot.sh` | MODIFY (npm build step) | T21 |
| `.github/workflows/ci.yml` | MODIFY (Node.js step) | T21 |
| `.gitignore` | MODIFY (`dist/`, `node_modules/`) | T21 |
| `llm-wiki/wiki/project/decisions/0040-sprint-26-dashboard-frontend-design.md` | MODIFY (amendment) | T22 |
| `llm-wiki/wiki/project/decisions/0066-sprint-46-react-migration.md` | CREATE | T22 |
| `llm-wiki/wiki/project/sprints/sprint-46-react-migration.md` | CREATE | T22 |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY | T22 |
| `llm-wiki/wiki/index.md` + `log.md` | MODIFY | T22 |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY (per-task) | every task |

---

## Task 1: React infrastructure setup (Vite + TS + ESLint + Prettier)

**Why opus:** Architecture-heavy — Vite config, TS strict mode, build pipeline integration с FastAPI must satisfy architect C1.

**Files:**
- Create: `src/dashboard_react/package.json`
- Create: `src/dashboard_react/tsconfig.json`
- Create: `src/dashboard_react/vite.config.ts`
- Create: `src/dashboard_react/index.html`
- Create: `src/dashboard_react/src/main.tsx`
- Create: `src/dashboard_react/.eslintrc.json`
- Create: `src/dashboard_react/.prettierrc`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "ai-trading-bot-dashboard",
  "private": true,
  "version": "0.1.0-alpha.46",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "test:e2e": "playwright test",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "uplot": "1.6.31"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@typescript-eslint/eslint-plugin": "^8.0.0",
    "@typescript-eslint/parser": "^8.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "eslint": "^9.0.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.0",
    "prettier": "^3.3.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "@playwright/test": "^1.48.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json (strict mode)**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src", "tests"]
}
```

- [ ] **Step 3: Create vite.config.ts (architect C1 compliance)**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    // Architect C1 BINDING: outDir = src/dashboard_react/dist/ (FastAPI mounts this)
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
    rollupOptions: {
      output: {
        // Content-hashed assets для cache busting
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
  },
  server: {
    // Architect C1 BINDING: dev server только для `npm run dev`,
    // production serves through FastAPI dist mount
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',  // dev-time API proxy
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
```

- [ ] **Step 4: Create index.html (Vite entry)**

```html
<!DOCTYPE html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>QUANT::TERMINAL — AI Trading Bot</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create main.tsx**

```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './styles/globals.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

- [ ] **Step 6: Create .eslintrc.json**

```json
{
  "root": true,
  "env": { "browser": true, "es2022": true },
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended"
  ],
  "ignorePatterns": ["dist", ".eslintrc.json"],
  "parser": "@typescript-eslint/parser",
  "plugins": ["react-refresh"],
  "rules": {
    "react-refresh/only-export-components": ["warn", { "allowConstantExport": true }],
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/no-explicit-any": "error"
  }
}
```

- [ ] **Step 7: Create .prettierrc**

```json
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "es5",
  "printWidth": 100,
  "tabWidth": 2
}
```

- [ ] **Step 8: Install + verify build**

```bash
cd src/dashboard_react
npm install 2>&1 | tail -5
npm run build 2>&1 | tail -10
ls -la dist/
```

Expected: `dist/index.html` + `dist/assets/main-*.js` generated.

- [ ] **Step 9: Commit**

```bash
git add src/dashboard_react/package.json src/dashboard_react/tsconfig.json src/dashboard_react/vite.config.ts src/dashboard_react/index.html src/dashboard_react/src/main.tsx src/dashboard_react/.eslintrc.json src/dashboard_react/.prettierrc
git commit -m "feat(s46): React infrastructure — Vite + TS strict + ESLint + Prettier"
```

- [ ] **Step 10: SPRINT_STATE update T1 done**

---

## Task 2: Design tokens — Anthropic palette + cyberpunk hi-tech (opus)

**Why opus:** Aesthetic pivot judgment. Anthropic orange + cyberpunk premium = design language decisions.

**Files:**
- Create: `src/dashboard_react/src/styles/tokens.css`
- Create: `src/dashboard_react/src/styles/globals.css`

- [ ] **Step 1: Create tokens.css (Anthropic + cyberpunk palette)**

```css
/* S46 — Anthropic + Cyberpunk hi-tech premium aesthetic
 * Operator pivot from terminal (ADR 0040 LOCKED) к Anthropic orange + cyberpunk style
 * ADR 0040 amendment + ADR 0066 document this decision.
 */
:root {
  /* Anthropic primary palette */
  --color-anthropic-orange: #cc785c;       /* warm coral — Anthropic brand */
  --color-anthropic-orange-light: #e89679; /* lighter coral для hover */
  --color-anthropic-orange-dark: #a85d44;  /* darker coral для pressed */
  --color-anthropic-cream: #f5e6d3;        /* warm off-white text */

  /* Cyberpunk dark base */
  --color-bg-base: #0a0a0a;          /* near-black base */
  --color-bg-panel: #141414;         /* slightly lifted panels */
  --color-bg-panel-hover: #1f1f1f;   /* hover state */
  --color-bg-glass: rgba(20, 20, 20, 0.65);  /* glass-morphism */

  /* Text hierarchy */
  --color-text-primary: var(--color-anthropic-cream);
  --color-text-secondary: #a8a8a8;
  --color-text-muted: #6e6e6e;
  --color-text-disabled: #4a4a4a;

  /* Status colors (cyberpunk neon) */
  --color-success: #00ff88;          /* neon green for PASS */
  --color-warn: var(--color-anthropic-orange);  /* orange для warn (RAW, WFA_FAIL_DATA) */
  --color-danger: #ff3366;           /* neon red для FAIL */
  --color-info: #00d4ff;             /* neon cyan для info */

  /* Borders + accents */
  --color-border-subtle: rgba(204, 120, 92, 0.15);
  --color-border-default: rgba(204, 120, 92, 0.30);
  --color-border-strong: rgba(204, 120, 92, 0.60);
  --color-border-glow: 0 0 12px rgba(204, 120, 92, 0.45);

  /* Cyberpunk effects */
  --gradient-anthropic: linear-gradient(135deg, var(--color-anthropic-orange) 0%, var(--color-anthropic-orange-dark) 100%);
  --gradient-glass: linear-gradient(135deg, rgba(204, 120, 92, 0.08) 0%, rgba(204, 120, 92, 0.02) 100%);
  --shadow-premium: 0 8px 32px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  --shadow-neon: 0 0 20px var(--color-anthropic-orange);

  /* Typography */
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  --font-sans: 'Inter', 'SF Pro Display', system-ui, sans-serif;

  /* Spacing scale */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;

  /* Radii */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;

  /* Transitions */
  --transition-fast: 0.12s ease-out;
  --transition-default: 0.2s ease-out;
}
```

- [ ] **Step 2: Create globals.css (base reset + cyberpunk effects)**

```css
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');
@import './tokens.css';

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  background-color: var(--color-bg-base);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#root {
  min-height: 100vh;
  background:
    radial-gradient(ellipse at top, rgba(204, 120, 92, 0.04) 0%, transparent 50%),
    radial-gradient(ellipse at bottom, rgba(0, 212, 255, 0.02) 0%, transparent 50%),
    var(--color-bg-base);
}

/* Cyberpunk scan overlay (subtle) */
#root::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg,
    transparent 0px,
    transparent 2px,
    rgba(255, 255, 255, 0.005) 2px,
    rgba(255, 255, 255, 0.005) 4px
  );
  z-index: 1;
}

button, input, select {
  font-family: inherit;
  font-size: inherit;
}

a {
  color: var(--color-anthropic-orange);
  text-decoration: none;
  transition: color var(--transition-fast);
}
a:hover {
  color: var(--color-anthropic-orange-light);
}

/* Code/monospace contexts */
code, pre, .mono {
  font-family: var(--font-mono);
}
```

- [ ] **Step 3: Verify Vite picks up CSS**

```bash
cd src/dashboard_react && npm run build 2>&1 | tail -5
```

Expected: build succeeds, CSS bundled.

- [ ] **Step 4: Commit + SPRINT_STATE T2 done**

```bash
git add src/dashboard_react/src/styles/
git commit -m "feat(s46): Anthropic + cyberpunk design tokens (orange palette + neon accents + glass-morphism)"
```

---

## Task 3: Top-level App component

**Files:**
- Create: `src/dashboard_react/src/App.tsx`
- Create: `src/dashboard_react/src/App.module.css`

- [ ] **Step 1: Create App.tsx (tab navigation skeleton)**

```typescript
import { useState } from 'react'
import styles from './App.module.css'

type Tab = 'backtest' | 'documentation' | 'history'

export function App() {
  const [activeTab, setActiveTab] = useState<Tab>('backtest')

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoMark}>◉</span>
          <div>
            <h1 className={styles.title}>QUANT<span className={styles.accent}>::</span>TERMINAL</h1>
            <p className={styles.subtitle}>AI TRADING BOT // BACKTEST INTERFACE // v0.1.0-alpha.46</p>
          </div>
        </div>
        <div className={styles.status}>
          <span className={styles.statusDot} /> SYSTEM READY
        </div>
      </header>

      <nav className={styles.tabNav}>
        {(['backtest', 'documentation', 'history'] as const).map((tab, i) => (
          <button
            key={tab}
            className={`${styles.tabBtn} ${activeTab === tab ? styles.active : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            <span className={styles.tabNum}>{String(i + 1).padStart(2, '0')}</span>
            <span className={styles.tabLabel}>{tab.toUpperCase()}</span>
          </button>
        ))}
      </nav>

      <main className={styles.main}>
        {activeTab === 'backtest' && <div>Backtest tab placeholder (T6+)</div>}
        {activeTab === 'documentation' && <div>Documentation tab (T15)</div>}
        {activeTab === 'history' && <div>History tab (T15)</div>}
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Create App.module.css**

```css
.app {
  position: relative;
  z-index: 2;
  max-width: 1600px;
  margin: 0 auto;
  padding: var(--space-6);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--space-6);
  border-bottom: 1px solid var(--color-border-subtle);
  margin-bottom: var(--space-6);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.logoMark {
  font-size: 2rem;
  color: var(--color-anthropic-orange);
  text-shadow: var(--shadow-neon);
}

.title {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.25rem;
  letter-spacing: 0.05em;
}

.accent {
  color: var(--color-anthropic-orange);
}

.subtitle {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--color-text-muted);
  letter-spacing: 0.1em;
  margin-top: 0.25rem;
}

.status {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.15em;
  color: var(--color-success);
}

.statusDot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
  margin-right: 0.5rem;
  box-shadow: 0 0 8px var(--color-success);
}

.tabNav {
  display: flex;
  gap: var(--space-2);
  border-bottom: 1px solid var(--color-border-subtle);
  margin-bottom: var(--space-6);
}

.tabBtn {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  padding: var(--space-3) var(--space-6);
  cursor: pointer;
  transition: color var(--transition-fast);
  border-bottom: 2px solid transparent;
}

.tabBtn:hover {
  color: var(--color-text-primary);
}

.tabBtn.active {
  color: var(--color-anthropic-orange);
  border-bottom-color: var(--color-anthropic-orange);
}

.tabNum {
  font-size: 0.65rem;
  opacity: 0.6;
}

.main {
  min-height: 60vh;
}
```

- [ ] **Step 3: Verify build**

```bash
cd src/dashboard_react && npm run build 2>&1 | tail -3
```

Expected: build succeeds.

- [ ] **Step 4: Commit + SPRINT_STATE T3 done**

```bash
git add src/dashboard_react/src/App.tsx src/dashboard_react/src/App.module.css
git commit -m "feat(s46): App component — tab navigation + Anthropic header"
```

---

## Task 4: API client + types

**Files:**
- Create: `src/dashboard_react/src/api/types.ts`
- Create: `src/dashboard_react/src/api/client.ts`

- [ ] **Step 1: Create types.ts (TypeScript types for FastAPI responses)**

```typescript
// S46 — TypeScript types для FastAPI backend responses
// Mirror Python BacktestRequest + envelope structure (S43 + S44)

export interface StrategyMetadata {
  id: string
  label: string
  type: string
  description: string
  optgroup: string
  supported_combos?: [string, string][]
  locked_symbol?: string | null
  locked_interval?: string | null
}

export interface IntervalLabel {
  id: string
  label: string
}

export interface DataAvailability {
  [symbol: string]: {
    [interval: string]: {
      bars: number
      start: string
      end: string
    }
  }
}

export interface BacktestRequest {
  strategy_id: string
  symbol: string
  interval: string
  start: string
  end: string
  force?: boolean
}

export interface Warning {
  level: 'high' | 'warn' | 'info'
  code: string
  message: string
}

export interface EquityCurve {
  timestamps: number[]   // unix seconds
  equity_pct: number[]
}

export interface WfaParams {
  train_bars: number
  test_bars: number
  k_folds: number
  embargo_bars: number
  min_required: number
  actual: number
}

export interface BacktestResponse {
  run_id: string
  cached: boolean
  request: {
    strategy_id: string
    strategy_label: string
    symbol: string
    interval: string
    interval_label: string
    start: string
    end: string
  }
  verdict: 'WFA_PASS' | 'WFA_FAIL' | 'WFA_FAIL_DATA' | 'PASS' | 'FAIL' | 'RAW'
  failed_criteria: string[]
  warnings: Warning[]
  equity_curve: EquityCurve
  bars_per_year: number
  acceptance_gate: string | null
  dsr: number | null
  dsr_pass: boolean | null
  mc_p_value: number | null
  metrics: Record<string, number>
  trade_stats: {
    n_trades: number
    win_rate: number
  }
  wfa_params: WfaParams | null
  wfa_total_bars: number
  fold_sharpe_ratios: number[]
  failed_folds: number[]
  trades_dump: unknown[]
  n_trades: number
  sharpe: number
  win_rate: number
  total_pnl_pct: number
  runner: string
}

export interface RunSummary {
  run_id: string
  cached: boolean
  request: BacktestResponse['request']
  verdict: BacktestResponse['verdict']
  metrics: Record<string, number>
  dsr: number | null
  mc_p_value: number | null
  total_pnl_pct: number
  n_trades: number
  sharpe: number
  win_rate: number
}
```

- [ ] **Step 2: Create client.ts (fetch wrapper)**

```typescript
import type {
  StrategyMetadata,
  IntervalLabel,
  DataAvailability,
  BacktestRequest,
  BacktestResponse,
  RunSummary,
} from './types'

const BASE_URL = ''  // same-origin (FastAPI serves React build)

class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`HTTP ${status}: ${detail}`)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  getStrategies: (): Promise<Record<string, StrategyMetadata>> =>
    request('/api/strategies'),

  getStrategyInfo: (id: string): Promise<StrategyMetadata> =>
    request(`/api/strategy/${id}/info`),

  getIntervals: (): Promise<IntervalLabel[]> =>
    request('/api/intervals'),

  getDataAvailability: (): Promise<DataAvailability> =>
    request('/api/data/availability'),

  runBacktest: (payload: BacktestRequest): Promise<BacktestResponse> =>
    request('/api/backtest', { method: 'POST', body: JSON.stringify(payload) }),

  getRuns: (): Promise<RunSummary[]> => request('/api/runs'),

  getRun: (runId: string): Promise<BacktestResponse> => request(`/api/runs/${runId}`),
}

export { ApiError }
```

- [ ] **Step 3: Verify TS compiles**

```bash
cd src/dashboard_react && npx tsc --noEmit 2>&1 | tail -5
```

Expected: 0 errors.

- [ ] **Step 4: Commit + SPRINT_STATE T4 done**

```bash
git add src/dashboard_react/src/api/
git commit -m "feat(s46): TypeScript API client + types для FastAPI backend"
```

---

## Task 5: React hooks (useStrategyInfo + useWfaFailAck)

**Files:**
- Create: `src/dashboard_react/src/hooks/useStrategyInfo.ts`
- Create: `src/dashboard_react/src/hooks/useWfaFailAck.ts`

- [ ] **Step 1: Create useStrategyInfo.ts (cached strategy info per S42 pattern)**

```typescript
import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import type { StrategyMetadata } from '@/api/types'

const cache: Record<string, StrategyMetadata> = {}

export function useStrategyInfo(strategyId: string | null): {
  info: StrategyMetadata | null
  loading: boolean
  error: Error | null
} {
  const [info, setInfo] = useState<StrategyMetadata | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!strategyId) {
      setInfo(null)
      return
    }
    if (cache[strategyId]) {
      setInfo(cache[strategyId])
      return
    }
    setLoading(true)
    api
      .getStrategyInfo(strategyId)
      .then((data) => {
        cache[strategyId] = data
        setInfo(data)
      })
      .catch(setError)
      .finally(() => setLoading(false))
  }, [strategyId])

  return { info, loading, error }
}
```

- [ ] **Step 2: Create useWfaFailAck.ts (S46 ack-gated localStorage hook)**

```typescript
import { useEffect, useState } from 'react'

const STORAGE_KEY = 'wfa_fail_ack'
const REQUIRED_DAYS = 3  // chip downgrade after 3 distinct calendar days

interface AckState {
  count: number
  dates: string[]  // YYYY-MM-DD strings
}

function loadState(): AckState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { count: 0, dates: [] }
    return JSON.parse(raw) as AckState
  } catch {
    return { count: 0, dates: [] }
  }
}

function saveState(state: AckState): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

export function useWfaFailAck(): {
  showFullBanner: boolean
  showChip: boolean
  ack: () => void
} {
  const [state, setState] = useState<AckState>(loadState)

  // Re-evaluate on mount
  useEffect(() => {
    setState(loadState())
  }, [])

  const today = new Date().toISOString().slice(0, 10)
  const distinctDays = new Set(state.dates).size
  const downgradeDone = distinctDays >= REQUIRED_DAYS

  // Full banner shows если still в acknowledgment phase OR today not yet acked
  const ackedToday = state.dates.includes(today)
  const showFullBanner = !downgradeDone && !ackedToday
  const showChip = downgradeDone || ackedToday

  const ack = (): void => {
    const newDates = state.dates.includes(today) ? state.dates : [...state.dates, today]
    const newState: AckState = { count: state.count + 1, dates: newDates }
    saveState(newState)
    setState(newState)
  }

  return { showFullBanner, showChip, ack }
}
```

- [ ] **Step 3: Verify TS compiles**

```bash
cd src/dashboard_react && npx tsc --noEmit 2>&1 | tail -3
```

Expected: 0 errors.

- [ ] **Step 4: Commit + SPRINT_STATE T5 done**

```bash
git add src/dashboard_react/src/hooks/
git commit -m "feat(s46): React hooks — useStrategyInfo (cache) + useWfaFailAck (localStorage)"
```

---

## Task 6: ConfigureBacktest component (form)

**Files:**
- Create: `src/dashboard_react/src/components/ConfigureBacktest.tsx`
- Create: `src/dashboard_react/src/components/ConfigureBacktest.module.css`

Implementation: form с strategy/symbol/interval/start/end fields. Group strategies by `optgroup` (S42 pattern). Use `useStrategyInfo` для combo gating. Submit → `api.runBacktest()`. ~150 lines TypeScript + ~100 lines CSS.

- [ ] **Step 1: Implement ConfigureBacktest.tsx с strategy/symbol/interval form, optgroup grouping, supported_combos gating, submit handler**
- [ ] **Step 2: Implement ConfigureBacktest.module.css с Anthropic glass-morphism styling**
- [ ] **Step 3: Wire into App.tsx (replace placeholder)**
- [ ] **Step 4: Verify build + manual smoke (run `npm run dev` → form renders с dropdowns)**
- [ ] **Step 5: Commit + SPRINT_STATE T6 done**

(Full implementation code authored by `frontend-developer` agent при subagent dispatch — operator agent invocation pattern.)

---

## Task 7: StrategyDescription component

Port S43 collapsible description block. ~80 lines.

- [ ] Implementation + commit + SPRINT_STATE T7 done

---

## Task 8: VerdictPanel component (three-valued WFA verdict)

Port S44 verdict mapping (WFA_PASS / WFA_FAIL / WFA_FAIL_DATA / RAW) с Anthropic color scheme. ~100 lines.

- [ ] Implementation + commit + SPRINT_STATE T8 done

---

## Task 9: EquityChart component (uPlot wrapper)

Port S43 uPlot integration. React wrapper для uPlot lifecycle (mount/unmount/destroy). ~120 lines.

- [ ] Implementation + commit + SPRINT_STATE T9 done

---

## Task 10: DrawdownSubchart component (architect CC2 — share x-axis с EquityChart)

uPlot stacked y-series OR sync plugin. Share x-axis cursor с EquityChart. ~100 lines.

- [ ] Implementation + commit + SPRINT_STATE T10 done

---

## Task 11: TradeMarkers component (architect CC3 — envelope API extension needed)

Pre-task: extend `research_runner_envelope.py` к emit `entry_timestamps` + `exit_timestamps` + `entry_prices` + `exit_prices` arrays. Then React component overlays dots на EquityChart. ~80 lines + ~30 lines Python.

- [ ] Backend extension + React overlay + commit + SPRINT_STATE T11 done

---

## Task 12: MonthlyHeatmap component (calendar grid)

Computes monthly returns from equity_curve. CSS grid 12-cols × N years. Color-coded cells. ~120 lines.

- [ ] Implementation + commit + SPRINT_STATE T12 done

---

## Task 13: MetricsTable component (TIER 1-6 + DSR + MC) — opus

**Why opus:** Logic for three-valued verdict rendering (WFA_PASS / WFA_FAIL / WFA_FAIL_DATA / RAW) — different table content per verdict.

Port S44 metrics rendering: full table для WFA_*, simplified для RAW. ~150 lines.

- [ ] Implementation + commit + SPRINT_STATE T13 done

---

## Task 14: TradesTable component

Trade stats (n_trades, win_rate, profitable, losing). RAW mode shows simplified. ~80 lines.

- [ ] Implementation + commit + SPRINT_STATE T14 done

---

## Task 15: HistoryTab + DocumentationTab components

Port S43 cached runs table + docs render. ~150 lines combined.

- [ ] Implementation + commit + SPRINT_STATE T15 done

---

## Task 16: WfaFailBadge component (per preset card)

Red badge `WFA_FAIL` для preset selection. Shows на every WFA_FAIL preset в dropdown (или separate visualization). ~50 lines.

- [ ] Implementation + commit + SPRINT_STATE T16 done

---

## Task 17: WfaFailBanner component (ack-gated NON-dismissible per architect Q4 REVISE)

Persistent banner top-of-page. localStorage hook (`useWfaFailAck`). Three states:
1. Full-width banner с button "I acknowledge WFA_FAIL (S45) — proceed"
2. After 3 distinct days OR ack today — compact persistent chip
3. Chip never disappears entirely

~100 lines TypeScript + ~80 lines CSS.

- [ ] Implementation + commit + SPRINT_STATE T17 done

---

## Task 18: Playwright E2E tests (critical flows)

**Files:**
- Create: `src/dashboard_react/playwright.config.ts`
- Create: `src/dashboard_react/tests/e2e/backtest-flow.spec.ts`
- Create: `src/dashboard_react/tests/e2e/wfa-fail-ack.spec.ts`

- [ ] **Step 1: Playwright config**

```typescript
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://127.0.0.1:8000',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'cd ../.. && .venv/bin/python -m src.dashboard.app',
    url: 'http://127.0.0.1:8000',
    reuseExistingServer: !process.env.CI,
  },
})
```

- [ ] **Step 2: backtest-flow.spec.ts**

```typescript
import { test, expect } from '@playwright/test'

test('user runs backtest и sees verdict', async ({ page }) => {
  await page.goto('/')
  // Acknowledge WFA_FAIL banner first
  await page.getByRole('button', { name: /acknowledge.*proceed/i }).click()
  // Select strategy
  await page.selectOption('select[name="strategy_id"]', 'atr_breakout')
  // Symbol + interval
  await page.selectOption('select[name="symbol"]', 'BTCUSDT')
  await page.selectOption('select[name="interval"]', '240')
  // Run
  await page.getByRole('button', { name: /execute/i }).click()
  // Verify verdict appears (one of three values)
  await expect(page.locator('[data-testid="verdict-value"]')).toContainText(/WFA_(PASS|FAIL|FAIL_DATA)/)
  // Equity chart renders
  await expect(page.locator('[data-testid="equity-chart"]')).toBeVisible()
})
```

- [ ] **Step 3: wfa-fail-ack.spec.ts**

```typescript
import { test, expect } from '@playwright/test'

test('WFA_FAIL banner ack-gated, persists на reload до ack', async ({ page, context }) => {
  await context.clearCookies()
  await page.goto('/')
  // Banner visible
  await expect(page.locator('[data-testid="wfa-fail-banner"]')).toBeVisible()
  // Reload — still visible
  await page.reload()
  await expect(page.locator('[data-testid="wfa-fail-banner"]')).toBeVisible()
  // Ack
  await page.getByRole('button', { name: /acknowledge.*proceed/i }).click()
  // Banner downgrades к chip
  await expect(page.locator('[data-testid="wfa-fail-banner"]')).not.toBeVisible()
  await expect(page.locator('[data-testid="wfa-fail-chip"]')).toBeVisible()
})
```

- [ ] **Step 4: Run E2E**

```bash
cd src/dashboard_react
npx playwright install chromium
npx playwright test 2>&1 | tail -10
```

Expected: 2/2 PASS.

- [ ] **Step 5: Commit + SPRINT_STATE T18 done**

```bash
git add src/dashboard_react/playwright.config.ts src/dashboard_react/tests/
git commit -m "test(s46): Playwright E2E — backtest flow + WFA_FAIL ack-gate"
```

---

## Task 19: FastAPI backend integration (architect C4 binding condition)

**Files:**
- Modify: `src/dashboard/app.py` — `TemplateResponse` → `FileResponse(dist/index.html)` + `StaticFiles(dist/)`

- [ ] **Step 1: Modify create_app() в app.py**

Replace:
```python
@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    ...TemplateResponse...
```

С:
```python
from fastapi.responses import FileResponse

# Architect C1+C4 BINDING — serve React build от src/dashboard_react/dist/
_DIST_DIR = _DIR.parent / "dashboard_react" / "dist"

if _DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(_DIST_DIR / "assets")), name="assets")

    @app.get("/", response_class=FileResponse)
    async def index_react() -> FileResponse:
        return FileResponse(_DIST_DIR / "index.html")
else:
    @app.get("/", response_class=HTMLResponse)
    async def index_missing() -> HTMLResponse:
        return HTMLResponse(
            "<h1>React build missing</h1><p>Run <code>npm run build</code> в src/dashboard_react/</p>",
            status_code=503,
        )
```

- [ ] **Step 2: Remove Jinja2 TemplateResponse code (legacy moved в T20)**

- [ ] **Step 3: Verify FastAPI starts с new mount**

```bash
cd src/dashboard_react && npm run build && cd ../..
.venv/bin/python -m src.dashboard.app &
sleep 3
curl -s http://127.0.0.1:8000/ | head -c 200
kill %1
```

Expected: HTML с `<div id="root"></div>` returned.

- [ ] **Step 4: Commit + SPRINT_STATE T19 done**

```bash
git add src/dashboard/app.py
git commit -m "feat(s46): FastAPI serves React build (FileResponse + StaticFiles dist/) per architect C4"
```

---

## Task 20: Archive vanilla dashboard

**Files:**
- Move: `src/dashboard/static/` → `src/dashboard_legacy/static/`
- Move: `src/dashboard/templates/` → `src/dashboard_legacy/templates/`

- [ ] **Step 1: Move files**

```bash
mkdir -p src/dashboard_legacy
mv src/dashboard/static src/dashboard_legacy/static
mv src/dashboard/templates src/dashboard_legacy/templates
ls -la src/dashboard_legacy/
ls -la src/dashboard/
```

- [ ] **Step 2: Verify FastAPI not broken (Jinja2 references already removed в T19)**

```bash
.venv/bin/python -c "from src.dashboard.app import create_app; app = create_app(); print('OK')"
```

Expected: prints OK без import errors.

- [ ] **Step 3: Commit + SPRINT_STATE T20 done**

```bash
git add src/dashboard_legacy/ src/dashboard/
git commit -m "feat(s46): archive vanilla dashboard к src/dashboard_legacy/"
```

---

## Task 21: CI/CD + start-bot.sh updates (architect C2 binding condition)

**Files:**
- Modify: `scripts/start-bot.sh` (add `npm run build` step)
- Modify: `.github/workflows/ci.yml` (Node.js setup + build + Playwright)
- Modify: `.gitignore` (`dist/`, `node_modules/`)

- [ ] **Step 1: Update start-bot.sh**

Find existing logic. Add BEFORE `python -m src`:

```bash
# S46 — React build step
if [ -d "src/dashboard_react" ]; then
  echo "▶ Building React dashboard..."
  cd src/dashboard_react
  if [ ! -d "node_modules" ]; then
    echo "▶ Installing npm dependencies (first run)..."
    npm install
  fi
  npm run build
  cd ../..
  echo "✓ React build complete"
fi
```

- [ ] **Step 2: Update ci.yml (Node.js setup + build + Playwright per architect C2)**

```yaml
# Add steps BEFORE existing pytest step:

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: src/dashboard_react/package-lock.json

      - name: Install npm deps
        run: cd src/dashboard_react && npm ci

      - name: TypeScript build
        run: cd src/dashboard_react && npm run build

      - name: Playwright install
        run: cd src/dashboard_react && npx playwright install --with-deps chromium

      - name: Playwright E2E tests
        run: cd src/dashboard_react && npx playwright test
```

- [ ] **Step 3: Update .gitignore**

```
# S46 React build artifacts
src/dashboard_react/dist/
src/dashboard_react/node_modules/
src/dashboard_react/playwright-report/
src/dashboard_react/test-results/
```

- [ ] **Step 4: Commit + SPRINT_STATE T21 done**

```bash
git add scripts/start-bot.sh .github/workflows/ci.yml .gitignore
git commit -m "feat(s46): CI/CD — Node.js setup + React build + Playwright (architect C2)"
```

---

## Task 22: ADR 0066 + ADR 0040 amendment + sprint-46 + wiki sync (opus)

**Why opus:** Aesthetic pivot decision documentation — judgment-heavy.

**Files:**
- Modify: `llm-wiki/wiki/project/decisions/0040-sprint-26-dashboard-frontend-design.md` (S46 amendment — aesthetic pivot)
- Create: `llm-wiki/wiki/project/decisions/0066-sprint-46-react-migration.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-46-react-migration.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (header / counts ADRs 65→66, sprint pages 49→50)
- Modify: `llm-wiki/wiki/index.md`
- Append: `llm-wiki/wiki/log.md`

- [ ] **Step 1: ADR 0040 amendment (terminal → Anthropic/cyberpunk)**

Append section к existing ADR 0040:

```markdown

## Поправка S46 (2026-05-10): Pivot к Anthropic + cyberpunk

Per S46 operator binding decision — pivot terminal aesthetic к Anthropic orange palette + cyberpunk hi-tech premium style. Rationale: operator showed Claude Signal cyberpunk references в S43 era + explicit S46 request "стилистика антропика и клад-кода".

### Changes
- Primary palette: green phosphor → Anthropic orange (#cc785c)
- Base: black-on-green → dark cyberpunk (#0a0a0a) с warm cream text
- Effects: scanlines + CRT glow → glass-morphism panels + subtle neon accents
- Typography: JetBrains Mono primary → Inter sans (UI) + JetBrains Mono (data/code)
- Status colors: terminal green/amber/red → neon green PASS / orange WFA_FAIL_DATA / neon red FAIL

### Implementation
- Migration к React 18 + TypeScript + Vite + CSS Modules (см. ADR 0066)
- Design tokens в `src/dashboard_react/src/styles/tokens.css`
- Original terminal aesthetic preserved в `src/dashboard_legacy/`
```

- [ ] **Step 2: Write ADR 0066**

```markdown
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

Operator binding decisions:
1. Framework: vanilla JS → React 18 + TypeScript + Vite + CSS Modules
2. Aesthetic: terminal (ADR 0040 LOCKED) → Anthropic orange + cyberpunk hi-tech premium (ADR 0040 amendment)
3. Honest close UI: ack-gated NON-dismissible banner + WFA_FAIL badges

Architecture-reviewer pre-plan validation: APPROVE_WITH_CONDITIONS — 3 binding conditions C1+C2+C4 incorporated в plan.

## Решения

### Decision A — React 18 stack
React 18.3 + TypeScript 5.x strict + Vite 5.x + CSS Modules + uPlot wrapper. NO Tailwind (preserves design token flexibility per trader Q1-NEW REVISE). Playwright E2E only S46; Vitest+RTL → S47.

### Decision B — Aesthetic pivot к Anthropic + cyberpunk
ADR 0040 amendment. Anthropic orange (#cc785c) primary, dark cyberpunk base, glass-morphism panels, neon accents. Preserves analytical seriousness через monospace data fonts (JetBrains Mono для tables/code), Inter sans для UI chrome.

### Decision C — Migration strategy
All-at-once full rewrite. Vanilla `src/dashboard/static/` + `templates/` archived к `src/dashboard_legacy/`. New `src/dashboard_react/` с React 18 stack. FastAPI backend unchanged.

### Decision D — Architect binding conditions
- C1: Vite outDir → `dist/`. FastAPI mounts `dist/`. NO separate Vite dev server в production.
- C2: Node.js CI step в `ci.yml` AS PART OF S46 (NOT S47).
- C4: `app.py` `TemplateResponse` → `FileResponse(dist/index.html)`.

### Decision E — Honest close UI piece (Option 1 visualization)
Ack-gated NON-dismissible banner per trader Q4 ROUND 1 REVISE. localStorage hook (`useWfaFailAck`) — count + day dedup. Chip downgrade after 3 distinct calendar days. WFA_FAIL badges per preset card. WFA_FAIL_DATA distinct color preserved (S43).

## Последствия

**Pros:**
- Modern React stack — easier extension future
- Anthropic premium aesthetic = professional brand alignment
- Honest close UX disciplined (ack-gated не dismissible)
- Architect binding conditions met = no silent runtime failures

**Cons:**
- Polyglot toolchain (Python backend + Node.js frontend)
- Bigger sprint (~22 tasks) vs typical S40-S45 (~8-12)
- Vanilla dashboard archived — operator must `npm install` first time
- ADR 0040 amendment — first aesthetic pivot since S26

**Carry-overs к S47:**
- Vitest + React Testing Library unit tests
- Tech debt batch (F8/M1-M4/Item 7/Item 10)
- Honest close code piece (preset disabled flag, server-side 422 reject)

**Carry-overs к S48:**
- Live trade feed widget (deferred S49+ — YAGNI per 0 live trades)
- Honest close finalize ADR 0067

## Verification

- React build succeeds, all TS types strict
- Playwright E2E PASS (backtest flow + ack-gate)
- FastAPI mounts dist/ correctly (architect C1+C4)
- Node.js CI step runs (architect C2)

## Связанные

- [[../sprints/sprint-46-react-migration]]
- [[../plans/2026-05-10-sprint-46-react-migration]]
- [[../pre-s46-backlog]]
- [[0039-sprint-25-dashboard-architecture]]
- [[0040-sprint-26-dashboard-frontend-design]] (amended S46)
- [[0063-sprint-43-ui-polish]]
- [[0065-sprint-45-wfa-recalibration]]
```

- [ ] **Step 3: sprint-46 page** — analogous structure к sprint-45.

- [ ] **Step 4: current-state.md update** — header "post-S46" + ADRs 65→66 + sprint pages 49→50 + sprint history row

- [ ] **Step 5: index.md + log.md** appends

- [ ] **Step 6: Commit + SPRINT_STATE T22 done + phase=8-ship**

```bash
git add llm-wiki/
git commit -m "docs(s46): wiki sync — ADR 0066 + ADR 0040 amendment + sprint-46 + index/log/current-state"
```

---

## PHASE 6 — Domain Reviewers (MANDATORY before merge)

5 reviewers parallel:

| Reviewer | Focus |
|----------|-------|
| `frontend-developer` | **PRIMARY React reviewer** — TS strict, component patterns, hooks correctness, CSS Modules scope, accessibility |
| `architecture-reviewer` | Followup — verify C1+C2+C4 binding conditions met |
| `python-reviewer` | FastAPI integration (FileResponse + StaticFiles dist/) |
| `test-engineer` | Playwright E2E coverage adequacy |
| `doc-reviewer` | ADR 0066 + ADR 0040 amendment + sprint-46 page consistency |

NO dashboard-reviewer (vanilla JS scope — superseded by frontend-developer).

---

## PHASE 8 — Ship

```bash
.venv/bin/pytest tests/ -q -m integration  # Python backend tests still pass
cd src/dashboard_react && npm run build && npx playwright test 2>&1 | tail -5
.venv/bin/mypy --strict src/
git push -u origin feature/sprint-46-react-migration
gh pr create --title "Sprint 46: React migration + Anthropic/cyberpunk aesthetic + honest close UI" ...
# squash-merge after reviewers GREEN
git tag -a v0.1.0-alpha.46 -m "..." <merge-sha>
git push origin v0.1.0-alpha.46
```

---

## Self-Review Verification

**Spec coverage:**
- T1: React infra (Vite + TS + ESLint + Prettier) → backlog Decision A
- T2: Anthropic/cyberpunk design tokens → Decision B (ADR 0040 amendment)
- T3-T15: Component migration (App, Configure, Description, Verdict, Equity, Drawdown, Markers, Heatmap, Metrics, Trades, History, Documentation)
- T16-T17: Honest close UI (badge + ack-gated banner) → Decision E
- T18: Playwright E2E → Decision D testing
- T19: FastAPI integration → architect C4
- T20: Vanilla archive → Decision C migration strategy
- T21: CI/CD + start-bot → architect C1+C2
- T22: ADRs + wiki sync → Decision A+B+C+D+E

**Type consistency:**
- `BacktestResponse` consistent T4+T13+T14
- `useWfaFailAck` return shape `{showFullBanner, showChip, ack}` consistent T5+T17
- `useStrategyInfo` return `{info, loading, error}` consistent T5+T6
- `outDir: 'dist'` consistent T1+T19+T21

**Placeholder scan:** Tasks T6-T17 brief implementation summaries (full code authored by `frontend-developer` agent при subagent dispatch) — это intentional pattern, не placeholder. Each task has explicit Files + Steps + Commit + SPRINT_STATE update structure.

**Plan complete and saved to `llm-wiki/wiki/project/plans/2026-05-10-sprint-46-react-migration.md`.**

Auto-invoke `superpowers:subagent-driven-development` per kit override (NO operator confirmation needed — operator decision 2026-05-10 documented in repo CLAUDE.md anti-patterns).
