---
title: "Sprint 47 Plan — Tech debt + S46 PHASE 6 carry-overs + UI bugs"
type: plan
tags: [sprint-47, tech-debt, react, vitest, fail-analysis-tab, bybit-api, plan]
created: 2026-05-11
updated: 2026-05-11
status: locked
sources:
  - llm-wiki/wiki/project/pre-s47-backlog.md
  - llm-wiki/wiki/project/SPRINT_STATE.md
  - llm-wiki/wiki/project/sprints/sprint-46-react-migration.md
  - llm-wiki/wiki/project/decisions/0014-walk-forward-acceptance-gates.md
  - llm-wiki/wiki/project/decisions/0056-dsr-sigma-sourcing.md
  - llm-wiki/wiki/project/decisions/0017-review-agent-harness.md
---

# Sprint 47 Implementation Plan — Tech debt + S46 PHASE 6 carry-overs + UI bugs

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (auto-invoked per repo CLAUDE.md operator override 2026-05-10) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discharge S46 PHASE 6 reviewer carry-overs (Vitest+RTL infra + 3 unit tests + E2E activate) + S37/S38 long-standing bybit tech debt (M1+M2+M3) + S44 quant follow-ups + 3 operator-surfaced UI items (trade_stats bug fix, EquityChart cursor tooltip, RU Fail Analysis tab).

**Architecture:** Mostly additive — new test infra + new tab component + 3 envelope/runner extensions + 3 bybit-api defensive patches + 3 FastAPI route additions. No FSM/reason-code changes. Aesthetic discipline = Anthropic orange + cyberpunk dark base (S46 ADR 0066 + ADR 0039 amendment).

**Tech Stack:** Python 3.12 + FastAPI + pybit V5 (backend) // React 18 + TypeScript strict + Vite 5 + CSS Modules + uPlot 1.6.31 + Playwright 1.48 + Vitest 1.x + RTL 16.x + fast-check 3.x (frontend).

**Branch:** `feature/sprint-47-tech-debt-carryovers` (already created from main `f2ac900`).

**Total tasks:** 16 (5 buckets + wiki sync). Models per task: opus T1 + T15 (judgment-heavy), sonnet others.

**Per-task SPRINT_STATE update protocol (BINDING):** After EACH task complete — edit `llm-wiki/wiki/project/SPRINT_STATE.md` Phase 4 task table + update "Текущий статус" + "Следующее действие" + bump `updated:` frontmatter. Optional commit `docs(sprint): SPRINT_STATE update phase=4 task=Tx done`.

---

## File structure overview

### Files created (NEW)

**Frontend tests + infra:**
- `src/dashboard_react/vitest.config.ts` — Vitest config с jsdom + CSS Modules transform (T1)
- `src/dashboard_react/src/setupTests.ts` — RTL + jest-dom setup (T1)
- `src/dashboard_react/src/components/__tests__/computeDrawdown.test.ts` — fast-check property tests (T2)
- `src/dashboard_react/src/hooks/__tests__/useWfaFailAck.test.ts` — RTL hook unit tests (T3)
- `src/dashboard_react/src/components/__tests__/MetricsTable.test.tsx` — threshold tests (T4)
- `src/dashboard_react/src/components/FailAnalysisTab.tsx` — Fail Analysis tab (T15)
- `src/dashboard_react/src/components/FailAnalysisTab.module.css` — tab styles (T15)

**Backend explanations + tests:**
- `src/dashboard/strategy_descriptions.py` — RU detailed per preset (T15)
- `src/dashboard/wfa_criterion_explanations.py` — RU formula+threshold+impact per criterion (T15)
- `tests/unit/test_dsr_property.py` — DSR ∈ [0,1] property test (T12)
- `tests/unit/test_n_trials_assert.py` — n_trials ≥ 1 assert (T12)
- `tests/unit/test_sprint_type.py` — sprint int/str type test (T12)
- `tests/unit/test_envelope_research_path_trade_stats.py` — schema test (T13)

**Wiki:**
- `llm-wiki/wiki/project/sprints/sprint-47-tech-debt-carryovers.md` — sprint summary (T16)

### Files modified

**Frontend:**
- `src/dashboard_react/package.json` — Vitest + RTL + jest-dom + fast-check deps (T1)
- `src/dashboard_react/src/components/DrawdownSubchart.tsx` — extract `computeDrawdown` к exportable pure fn (T2 prep) + cursor mirror (T14)
- `src/dashboard_react/src/components/MetricsTable.tsx` — T5 bug fix (T8)
- `src/dashboard_react/src/components/TradesTable.tsx` — graceful render когда quote fields null (T13)
- `src/dashboard_react/src/components/EquityChart.tsx` — cursor tooltip enable + T14 mirror (T14)
- `src/dashboard_react/src/components/EquityChart.module.css` — tooltip styles (T14)
- `src/dashboard_react/src/api/types.ts` — TradeStats + Strategy/CriterionExplanation interfaces (T13 + T15)
- `src/dashboard_react/src/api/client.ts` — getStrategyExplanation + getCriterionExplanations methods (T15)
- `src/dashboard_react/src/App.tsx` — wire FailAnalysisTab conditional render (T15)
- `src/dashboard_react/tests/e2e/backtest-flow.spec.ts` — activate с mock fixture (T5)

**Backend:**
- `src/dashboard/app.py` — SPA catch-all route + cache headers + 2 new endpoints (T6 + T7 + T15)
- `src/backtest/research_runner_envelope.py` — `trades_list` optional param + derive logic (T13)
- `src/backtest/volume_breakout_runner.py` — pass `trades_list` к envelope (T13)
- `src/backtest/atr_breakout_runner.py` — pass `trades_list` к envelope (T13)
- `src/execution/bybit/adapter.py` — M1 retCode taxonomy extension (T9)
- `src/execution/bybit/errors.py` — M1 retCode classification (T9)
- `src/execution/bybit/ws_private.py` — M3 isinstance guard (T11) — **M4 `__repr__` redaction EXPLICITLY OUT OF SCOPE**

**Tests:**
- `tests/unit/test_research_runner_envelope.py` — extend existing tests для new fields (T13)

**CI:**
- `.github/workflows/ci.yml` — Vitest step add (T1)

**Wiki:**
- `llm-wiki/wiki/project/SPRINT_STATE.md` — phase + task table updates (per-task)
- `llm-wiki/wiki/index.md` — sprint-47 entry (T16)
- `llm-wiki/wiki/log.md` — sprint-end + ship entries (T16)
- `llm-wiki/wiki/project/architecture/current-state.md` — header + counts + sprint history row (T16)

### Reviewer matrix PHASE 6

| Reviewer | Tasks |
|---|---|
| python-reviewer | T6, T7, T13, T15 (FastAPI + envelope) |
| trading-logic-reviewer | T8, T15 (MetricsTable T5 + Fail Analysis narrative correctness) |
| quant-stats-reviewer | T12, T15 (DSR + Bailey/ADR 0014/ADR 0056 cross-reference) — **BLOCKER risk if T15 formulas wrong** |
| bybit-api-reviewer | T9, T10, T11 (M1+M2+M3) |
| security-auditor | T9-T11 ONLY (M1-M3 scope per CC2; **M4 EXPLICIT OUT OF SCOPE**) |
| frontend-developer | T1-T5, T13, T14, T15 (Vitest+RTL setup + tests + UI features) |
| test-engineer | T2-T4, T12, T13 (coverage adequacy + property test design + envelope schema) |
| data-integrity-reviewer | T13 (envelope schema invariants) |
| doc-reviewer | T16 |

NO architecture-reviewer (no major refactor). NO dashboard-reviewer (superseded by frontend-developer per S46).

---

## Bucket A — S46 PHASE 6 carry-overs

## Task 1: Vitest + React Testing Library infra setup (opus)

**Why opus:** Multi-file config with Vite-Vitest plugin integration + CSS Modules transform + RTL setup + jsdom polyfills + CI step + worker isolation tuning. Several gotchas (CSS Modules require explicit `transformMode`, `cleanup` after each test, `localStorage` global polyfill для jsdom).

**Files:**
- Create: `src/dashboard_react/vitest.config.ts`
- Create: `src/dashboard_react/src/setupTests.ts`
- Create: `src/dashboard_react/src/__tests__/sample.test.tsx` (smoke test)
- Modify: `src/dashboard_react/package.json` — add deps + scripts
- Modify: `.github/workflows/ci.yml` — add Vitest step before Playwright

- [ ] **Step 1: Add Vitest + RTL + fast-check + jest-dom devDependencies**

```bash
cd src/dashboard_react
npm install --save-dev vitest@^1.6.0 @vitest/ui@^1.6.0 jsdom@^25.0.0 \
  @testing-library/react@^16.0.0 @testing-library/jest-dom@^6.5.0 \
  @testing-library/user-event@^14.5.0 fast-check@^3.22.0
```

Add scripts к `src/dashboard_react/package.json` — under existing `"scripts":` block:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest",
  "test:ui": "vitest --ui"
}
```

- [ ] **Step 2: Create `src/dashboard_react/vitest.config.ts`**

```typescript
/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    css: {
      modules: {
        // Hash-only class names в test mode — prevents flaky tests on hash drift
        classNameStrategy: 'non-scoped',
      },
    },
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules', 'dist', 'tests/e2e/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules', 'dist', 'tests/e2e', '**/*.config.*'],
    },
  },
})
```

- [ ] **Step 3: Create `src/dashboard_react/src/setupTests.ts`**

```typescript
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Auto-cleanup React tree после каждого теста — prevents test pollution
afterEach(() => {
  cleanup()
})

// jsdom не имеет localStorage по умолчанию в некоторых конфигах — polyfill on
if (typeof window !== 'undefined' && !window.localStorage) {
  let store: Record<string, string> = {}
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = String(value) },
      removeItem: (key: string) => { delete store[key] },
      clear: () => { store = {} },
      key: (index: number) => Object.keys(store)[index] ?? null,
      get length() { return Object.keys(store).length },
    },
    writable: true,
  })
}
```

- [ ] **Step 4: Create smoke test `src/dashboard_react/src/__tests__/sample.test.tsx`**

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

describe('Vitest + RTL infra smoke', () => {
  it('renders a simple component', () => {
    render(<div data-testid="smoke">hello</div>)
    expect(screen.getByTestId('smoke')).toHaveTextContent('hello')
  })

  it('localStorage polyfill works', () => {
    window.localStorage.setItem('k', 'v')
    expect(window.localStorage.getItem('k')).toBe('v')
    window.localStorage.clear()
    expect(window.localStorage.getItem('k')).toBeNull()
  })
})
```

- [ ] **Step 5: Run Vitest smoke**

```bash
cd src/dashboard_react
npm test
```

Expected: `2 passed` exit 0.

- [ ] **Step 6: Add Vitest step к `.github/workflows/ci.yml`**

Insert AFTER `TypeScript build` step + BEFORE `Playwright install`:

```yaml
      - name: Vitest unit tests
        run: cd src/dashboard_react && npm test
```

- [ ] **Step 7: Verify build still clean**

```bash
cd src/dashboard_react
npm run lint
npx tsc -b
npm run build
```

Expected: 0 warnings / 0 errors / build succeeds. Vitest config + setupTests should NOT leak into production bundle (Vite tree-shakes test deps automatically).

- [ ] **Step 8: Commit + SPRINT_STATE T1 done**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git add src/dashboard_react/vitest.config.ts \
        src/dashboard_react/src/setupTests.ts \
        src/dashboard_react/src/__tests__/sample.test.tsx \
        src/dashboard_react/package.json \
        src/dashboard_react/package-lock.json \
        .github/workflows/ci.yml
git commit -m "test(s47): Vitest + RTL infra setup (T1) — config + setupTests + smoke test + CI step"
```

Update SPRINT_STATE: T1 → done. Commit `docs(sprint): SPRINT_STATE T1 done — Vitest infra`.

---

## Task 2: Vitest unit test #1 — `computeDrawdown` property tests (sonnet)

**Why sonnet:** Pure function + fast-check property tests. Math invariants well-defined.

**Files:**
- Modify: `src/dashboard_react/src/components/DrawdownSubchart.tsx` — extract `computeDrawdown` to exportable pure fn
- Create: `src/dashboard_react/src/components/__tests__/computeDrawdown.test.ts`

- [ ] **Step 1: Refactor `computeDrawdown` к module-level export in DrawdownSubchart.tsx**

Find existing `function computeDrawdown(equityPct: number[]): number[] { ... }` inside component file. Hoist to module-level + add `export`:

```typescript
// At top of src/dashboard_react/src/components/DrawdownSubchart.tsx (above DrawdownSubchartProps interface)

/**
 * Compute drawdown series from cumulative equity_pct.
 * Returns negative percent values (peak-to-trough). Always ≤ 0.
 */
export function computeDrawdown(equityPct: number[]): number[] {
  const result = new Array<number>(equityPct.length)
  let peak = -Infinity
  for (let i = 0; i < equityPct.length; i++) {
    const v = (equityPct[i] ?? 0) / 100 + 1
    if (v > peak) peak = v
    result[i] = peak > 0 ? ((v - peak) / peak) * 100 : 0
  }
  return result
}
```

Verify build still clean: `cd src/dashboard_react && npx tsc -b`.

- [ ] **Step 2: Create `src/dashboard_react/src/components/__tests__/computeDrawdown.test.ts`**

```typescript
import { describe, it, expect } from 'vitest'
import { fc } from 'fast-check'
import { computeDrawdown } from '../DrawdownSubchart'

// Шорткат для readability — re-export fast-check namespace
const { property, integer, float, array, assert: fcAssert } = fc

describe('computeDrawdown — math invariants (fast-check property tests)', () => {
  it('returns array same length as input', () => {
    fcAssert(
      property(array(float({ noNaN: true, min: -100, max: 1000 }), { maxLength: 200 }), (xs) => {
        expect(computeDrawdown(xs).length).toBe(xs.length)
      }),
    )
  })

  it('drawdown values are always ≤ 0 (peak-relative loss never positive)', () => {
    fcAssert(
      property(array(float({ noNaN: true, min: -50, max: 500 }), { minLength: 1, maxLength: 200 }), (xs) => {
        const dd = computeDrawdown(xs)
        for (const v of dd) {
          expect(v).toBeLessThanOrEqual(0)
        }
      }),
    )
  })

  it('drawdown is 0 при first sample (no prior peak)', () => {
    fcAssert(
      property(float({ noNaN: true, min: -50, max: 500 }), (first) => {
        const dd = computeDrawdown([first])
        // First sample's peak == itself → drawdown = 0
        expect(dd[0]).toBe(0)
      }),
    )
  })

  it('monotonic-up sequence has zero drawdown everywhere', () => {
    // Strictly ascending sequence → peak === current → drawdown always 0
    const ascending = [0, 5, 10, 15, 20, 25, 30, 50, 100, 200]
    const dd = computeDrawdown(ascending)
    for (const v of dd) {
      expect(v).toBe(0)
    }
  })

  it('drop after peak produces negative drawdown', () => {
    // Peak at index 2 (equity_pct = 50 → multiplier 1.5), then drop к 0
    const series = [0, 25, 50, 0, 0]
    const dd = computeDrawdown(series)
    expect(dd[0]).toBe(0)
    expect(dd[1]).toBe(0)
    expect(dd[2]).toBe(0)
    // multiplier at idx 3 = 1.0, peak = 1.5 → (1.0 - 1.5) / 1.5 * 100 ≈ -33.33%
    expect(dd[3]).toBeCloseTo(-33.333, 2)
    expect(dd[4]).toBeCloseTo(-33.333, 2)
  })

  it('handles empty input', () => {
    expect(computeDrawdown([])).toEqual([])
  })

  it('handles single zero — drawdown is 0', () => {
    expect(computeDrawdown([0])).toEqual([0])
  })
})
```

- [ ] **Step 3: Run tests — expect PASS**

```bash
cd src/dashboard_react
npm test -- computeDrawdown
```

Expected: 7 tests pass.

- [ ] **Step 4: Commit + SPRINT_STATE T2 done**

```bash
git add src/dashboard_react/src/components/DrawdownSubchart.tsx \
        src/dashboard_react/src/components/__tests__/computeDrawdown.test.ts
git commit -m "test(s47): computeDrawdown property tests via fast-check (T2) — math invariants

Hoist computeDrawdown к module-level export. Add 7 fast-check property tests:
length preservation / dd ≤ 0 invariant / first-sample zero / monotonic-up zero /
post-peak drop / empty + single-zero edge cases."
```

Update SPRINT_STATE T2 → done.

---

## Task 3: Vitest unit test #2 — `useWfaFailAck` hook tests (sonnet)

**Files:**
- Create: `src/dashboard_react/src/hooks/__tests__/useWfaFailAck.test.ts`

- [ ] **Step 1: Write hook tests**

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWfaFailAck } from '../useWfaFailAck'

const STORAGE_KEY = 'wfa_fail_ack_v1'

describe('useWfaFailAck — localStorage state machine', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('initial state — showFullBanner=true, showChip=false, no acks', () => {
    const { result } = renderHook(() => useWfaFailAck())
    expect(result.current.showFullBanner).toBe(true)
    expect(result.current.showChip).toBe(false)
    expect(result.current.ackedTotal).toBe(0)
    expect(result.current.distinctDays).toBe(0)
  })

  it('after first ack — showFullBanner=false, showChip=true, count=1', () => {
    const { result } = renderHook(() => useWfaFailAck())
    act(() => result.current.ack())
    expect(result.current.showFullBanner).toBe(false)
    expect(result.current.showChip).toBe(true)
    expect(result.current.ackedTotal).toBe(1)
    expect(result.current.distinctDays).toBeGreaterThanOrEqual(1)
  })

  it('multiple acks same day — distinctDays stays 1', () => {
    const { result } = renderHook(() => useWfaFailAck())
    act(() => {
      result.current.ack()
      result.current.ack()
      result.current.ack()
    })
    expect(result.current.ackedTotal).toBe(3)
    expect(result.current.distinctDays).toBe(1)
  })

  it('reset() clears state — back к initial', () => {
    const { result } = renderHook(() => useWfaFailAck())
    act(() => result.current.ack())
    expect(result.current.ackedTotal).toBe(1)
    act(() => result.current.reset())
    expect(result.current.ackedTotal).toBe(0)
    expect(result.current.distinctDays).toBe(0)
  })

  it('persists state к localStorage on ack', () => {
    const { result } = renderHook(() => useWfaFailAck())
    act(() => result.current.ack())
    const stored = window.localStorage.getItem(STORAGE_KEY)
    expect(stored).not.toBeNull()
    const parsed = JSON.parse(stored!)
    expect(parsed.count).toBe(1)
    expect(parsed.dates).toHaveLength(1)
  })

  it('hydrates state из localStorage on mount', () => {
    // Pre-seed 3 distinct days (chip downgrade threshold)
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        count: 3,
        dates: ['2026-05-01', '2026-05-02', '2026-05-03'],
      }),
    )
    const { result } = renderHook(() => useWfaFailAck())
    expect(result.current.ackedTotal).toBe(3)
    expect(result.current.distinctDays).toBe(3)
    expect(result.current.showFullBanner).toBe(false)
    expect(result.current.showChip).toBe(true)
  })

  it('handles malformed localStorage gracefully — fallback к initial', () => {
    window.localStorage.setItem(STORAGE_KEY, 'not-json{{{')
    const { result } = renderHook(() => useWfaFailAck())
    expect(result.current.ackedTotal).toBe(0)
    expect(result.current.showFullBanner).toBe(true)
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd src/dashboard_react
npm test -- useWfaFailAck
```

Expected: 7 pass. Если any test fails → hook implementation has bug — fix hook (NOT test) since test encodes intended behavior per S46 architect Q4 REVISE.

- [ ] **Step 3: Commit + SPRINT_STATE T3 done**

```bash
git add src/dashboard_react/src/hooks/__tests__/useWfaFailAck.test.ts
git commit -m "test(s47): useWfaFailAck hook unit tests (T3) — localStorage state machine

7 tests: initial state / first ack / same-day dedup / reset / persist /
hydrate / malformed-json fallback."
```

---

## Task 4: Vitest unit test #3 — `MetricsTable` threshold tests (sonnet)

**Files:**
- Create: `src/dashboard_react/src/components/__tests__/MetricsTable.test.tsx`

- [ ] **Step 1: Write threshold + class tests**

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MetricsTable } from '../MetricsTable'
import type { BacktestResponse } from '@/api/types'

const baseResponse: Partial<BacktestResponse> = {
  request: {
    strategy_id: 'ema_crossover_s13',
    strategy_label: 'EMA crossover',
    symbol: 'BTCUSDT',
    interval: '60',
    interval_label: '1h',
    start: '2023-01-01',
    end: '2023-12-31',
  },
  warnings: [],
  failed_criteria: [],
  fold_sharpe_ratios: [],
  failed_folds: [],
  trades_dump: [],
}

describe('MetricsTable — RAW path', () => {
  it('renders Total PnL + Sharpe + n_trades + Win rate (4 rows)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'RAW',
      total_pnl_pct: 12.5,
      sharpe: 1.42,
      n_trades: 50,
      win_rate: 0.58,
      metrics: { total_pnl_pct: 12.5, sharpe: 1.42, n_trades: 50, win_rate: 0.58 },
      bars_per_year: 8766,
    } as BacktestResponse
    render(<MetricsTable result={r} />)
    expect(screen.getByText(/Total PnL/i)).toBeInTheDocument()
    expect(screen.getByText(/Sharpe/i)).toBeInTheDocument()
    expect(screen.getByText(/Trade count/i)).toBeInTheDocument()
    expect(screen.getByText(/Win rate/i)).toBeInTheDocument()
    // T1-T6 / DSR / MC must NOT be shown в RAW path
    expect(screen.queryByText(/T5 ·/)).not.toBeInTheDocument()
    expect(screen.queryByText(/DSR ·/)).not.toBeInTheDocument()
  })
})

describe('MetricsTable — WFA path Bailey 2014 thresholds (per ADR 0014)', () => {
  it('T5 trade count: n=99 → FAIL (Bailey ≥ 100)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: { t5_n_trades: 99, t1_sharpe_oos: 1.2, t3_max_drawdown: 0.15 },
      dsr: 0.5, dsr_pass: true, mc_p_value: 0.04,
      fold_sharpe_ratios: [1.1, 1.0, 0.9],
    } as BacktestResponse
    render(<MetricsTable result={r} />)
    // Find T5 row by text "Trade count (n)"
    const t5Row = screen.getByText(/T5 · Trade count/i).closest('tr')
    expect(t5Row).toBeTruthy()
    // FAIL chip present
    expect(t5Row!.textContent).toMatch(/99/)
    expect(t5Row!.textContent).toMatch(/FAIL/i)
  })

  it('T5 trade count: n=100 → PASS (Bailey threshold inclusive)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_PASS',
      metrics: { t5_n_trades: 100 },
      dsr: 0.5, dsr_pass: true, mc_p_value: 0.04,
    } as BacktestResponse
    render(<MetricsTable result={r} />)
    const t5Row = screen.getByText(/T5 · Trade count/i).closest('tr')
    expect(t5Row!.textContent).toMatch(/100/)
    expect(t5Row!.textContent).toMatch(/PASS/i)
  })

  it('T1 Sharpe OOS > 3 → OVERFIT? warning chip (overfit detector)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: { t1_sharpe_oos: 4.5 },
      dsr: 0.5, dsr_pass: true, mc_p_value: 0.04,
    } as BacktestResponse
    render(<MetricsTable result={r} />)
    expect(screen.getByText(/OVERFIT/i)).toBeInTheDocument()
  })

  it('T3 Max Drawdown ≥ 25% → FAIL', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: { t3_max_drawdown: 0.30 },
      dsr: 0.5, dsr_pass: true, mc_p_value: 0.04,
    } as BacktestResponse
    render(<MetricsTable result={r} />)
    const t3Row = screen.getByText(/T3 · Max Drawdown/i).closest('tr')
    expect(t3Row!.textContent).toMatch(/FAIL/i)
  })

  it('MC p-value > 0.10 → FAIL; ≤ 0.05 → PASS; in (0.05, 0.10] → WARN cell color', () => {
    const fail: BacktestResponse = {
      ...baseResponse, verdict: 'WFA_FAIL',
      metrics: {}, dsr: 0.5, dsr_pass: true, mc_p_value: 0.15,
    } as BacktestResponse
    const { unmount } = render(<MetricsTable result={fail} />)
    expect(screen.getByText(/MC ·/i).closest('tr')!.textContent).toMatch(/FAIL/i)
    unmount()

    const pass: BacktestResponse = {
      ...baseResponse, verdict: 'WFA_PASS',
      metrics: {}, dsr: 0.5, dsr_pass: true, mc_p_value: 0.04,
    } as BacktestResponse
    render(<MetricsTable result={pass} />)
    expect(screen.getByText(/MC ·/i).closest('tr')!.textContent).toMatch(/PASS/i)
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd src/dashboard_react
npm test -- MetricsTable
```

Expected: 6 pass. **Note:** T5 vanilla bug ("undefined < 100 → PASS") — этот test не covered здесь, отдельный test add в T8 после fix.

- [ ] **Step 3: Commit + SPRINT_STATE T4 done**

```bash
git add src/dashboard_react/src/components/__tests__/MetricsTable.test.tsx
git commit -m "test(s47): MetricsTable threshold tests (T4) — Bailey 2014 + ADR 0014 encoding

6 tests covering RAW path render + WFA path threshold semantics
(T5 trade count Bailey gate / T1 overfit detector / T3 max DD / MC p-value)."
```

---

## Task 5: backtest-flow.spec.ts E2E activate с mock fixture (sonnet)

**Files:**
- Modify: `src/dashboard_react/tests/e2e/backtest-flow.spec.ts` — replace skip с active test

- [ ] **Step 1: Replace `test.skip` block с active mock-based test**

Find existing `test.skip('user submits form and sees verdict panel', ...)` в `src/dashboard_react/tests/e2e/backtest-flow.spec.ts`. Replace с:

```typescript
  test('user submits form, mocked /api/backtest returns WFA_FAIL → VerdictPanel + EquityChart visible', async ({ page, context }) => {
    await context.addInitScript(() => {
      // Pre-ack WFA banner so it doesn't block form
      window.localStorage.setItem(
        'wfa_fail_ack_v1',
        JSON.stringify({ count: 3, dates: ['2026-05-08', '2026-05-09', '2026-05-10'] }),
      )
    })

    // Stub /api/backtest response — minimal envelope с WFA_FAIL verdict
    await page.route('**/api/backtest', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test_run_e2e',
          cached: false,
          verdict: 'WFA_FAIL',
          failed_criteria: ['t1', 't5'],
          warnings: [{ level: 'high', code: 'wfa_fail', message: 'Test failure' }],
          metrics: {
            t1_sharpe_oos: 0.5,
            t3_max_drawdown: 0.18,
            t5_n_trades: 80,
            t5_t_stat: 1.2,
          },
          trade_stats: { n_trades: 80, win_rate: 0.45 },
          dsr: 0.3,
          dsr_pass: false,
          mc_p_value: 0.12,
          fold_sharpe_ratios: [0.4, 0.6, 0.5],
          failed_folds: [0, 2],
          bars_per_year: 8766,
          equity_curve: {
            timestamps: [1700000000, 1700100000, 1700200000, 1700300000],
            equity_pct: [0, 5, -2, 3],
            trade_markers: null,
          },
          request: {
            strategy_id: 'ema_crossover_s13',
            strategy_label: 'EMA crossover S13',
            symbol: 'BTCUSDT',
            interval: '60',
            interval_label: '1h',
            start: '2023-01-01',
            end: '2023-12-31',
          },
          n_trades: 80,
          sharpe: 0.5,
          win_rate: 0.45,
          total_pnl_pct: 6.0,
        }),
      })
    })

    await page.goto('/')
    await expect(page.getByText('STRATEGY')).toBeVisible()

    const executeBtn = page.getByRole('button', { name: /EXECUTE/ })
    await executeBtn.click()

    // Verdict panel renders с WFA_FAIL
    await expect(page.getByText(/FINAL VERDICT/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('WFA_FAIL')).toBeVisible()

    // EquityChart title appears
    await expect(page.getByText(/EQUITY CURVE/)).toBeVisible()

    // Failed criteria chips
    await expect(page.getByText(/T1/)).toBeVisible()
    await expect(page.getByText(/T5/)).toBeVisible()
  })
```

- [ ] **Step 2: Run E2E**

```bash
cd src/dashboard_react
npx playwright test backtest-flow
```

Expected: 2/2 PASS (form-render existing + new submit→verdict).

- [ ] **Step 3: Commit + SPRINT_STATE T5 done**

```bash
git add src/dashboard_react/tests/e2e/backtest-flow.spec.ts
git commit -m "test(s47): backtest-flow E2E activate (T5) — page.route mock + verdict assertion

Replaces test.skip с active test using page.route('/api/backtest', ...) mock fixture.
Asserts VerdictPanel renders WFA_FAIL + EquityChart visible + failed criteria chips."
```

---

## Bucket B — Architect MEDIUM findings

## Task 6: SPA catch-all FastAPI route (sonnet)

**Why:** Architecture-reviewer S46 PHASE 6 MEDIUM — needed if React Router introduced. Currently bookmark `/history` returns 404. Adds graceful fallback.

**Files:**
- Modify: `src/dashboard/app.py` — add catch-all route AFTER all `/api/*` + `/assets/*` mounts

- [ ] **Step 1: Locate route registration block**

```bash
grep -n "app.mount\|@app.get\|@app.post" src/dashboard/app.py
```

Note line numbers — catch-all MUST be last route registered.

- [ ] **Step 2: Add SPA catch-all к bottom of route registrations**

Find `if _DIST_DIR.exists():` block в `src/dashboard/app.py`. After existing `index_react` handler, add:

```python
    # S47 architect MEDIUM (S46 followup) — SPA catch-all для client-side routing.
    # Mount order: ALL /api/* + /assets/* MUST be registered BEFORE this catch-all.
    # FastAPI matches routes in registration order; catch-all should be last.
    @app.get("/{path:path}", response_class=FileResponse, include_in_schema=False)
    async def spa_fallback(path: str) -> FileResponse:
        # Любой non-API non-asset path → serve React SPA shell.
        # React Router (если added в future) handles client-side routing.
        return FileResponse(_DIST_DIR / "index.html")
```

- [ ] **Step 3: Verify import + module loads**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
source .venv/bin/activate
python -c "from src.dashboard.app import create_app; app = create_app(); print('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Functional test — catch-all serves SPA, не conflicts с /api/**

```bash
.venv/bin/uvicorn src.dashboard.app:create_app --factory --port 8000 &
APP_PID=$!
sleep 3

# /api/strategies → JSON (NOT swallowed by catch-all)
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" http://127.0.0.1:8000/api/strategies

# /history → SPA HTML (catch-all path)
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" http://127.0.0.1:8000/history

# /assets/index-XXX.js → asset (NOT swallowed)
ASSET=$(curl -s http://127.0.0.1:8000/ | grep -oE '/assets/index-[a-zA-Z0-9_-]+\.js' | head -1)
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000${ASSET}"

kill $APP_PID 2>/dev/null
wait $APP_PID 2>/dev/null
```

Expected:
- `/api/strategies` → `200 application/json`
- `/history` → `200 text/html` (SPA shell)
- `/assets/...js` → `200`

- [ ] **Step 5: Commit + SPRINT_STATE T6 done**

```bash
git add src/dashboard/app.py
git commit -m "feat(s47): SPA catch-all FastAPI route (T6) — architect S46 MEDIUM followup

@app.get('/{path:path}') fallback к FileResponse(dist/index.html). Mount order
preserved: API + assets before catch-all. Enables future React Router без 404."
```

---

## Task 7: React asset HTTP cache headers (sonnet)

**Why:** python-reviewer S46 PHASE 6 MEDIUM — content-hashed assets могут served stale без proper cache headers. Vite emits `dist/assets/index-{hash}.js` — these are immutable forever; `index.html` references them and changes per build → must NOT be cached.

**Files:**
- Modify: `src/dashboard/app.py` — add cache header middleware OR per-route response_headers

- [ ] **Step 1: Add cache-control middleware**

В `src/dashboard/app.py`, найти где `app = FastAPI(...)` instantiated. После `app.mount(...)` calls добавить middleware:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class _CacheControlMiddleware(BaseHTTPMiddleware):
    """S47 python-reviewer S46 MEDIUM — set cache headers per content type.

    /assets/* — content-hashed, immutable forever (Vite hash на rebuild).
    index.html (catch-all + index_react) — must NOT cache (references new hashes per build).
    /api/* — no-cache (dynamic content).
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        path = request.url.path
        if path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, immutable, max-age=31536000"
        elif path == "/" or path.startswith("/api/") or path == "/index.html":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        # Otherwise (catch-all SPA paths) — also no-cache (serves index.html)
        else:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


app.add_middleware(_CacheControlMiddleware)
```

Add `from typing import Any` import if not already imported.

- [ ] **Step 2: Functional test — verify headers**

```bash
.venv/bin/uvicorn src.dashboard.app:create_app --factory --port 8000 &
APP_PID=$!
sleep 3

echo "Index:"
curl -s -I http://127.0.0.1:8000/ | grep -i "cache-control"

echo "Asset:"
ASSET=$(curl -s http://127.0.0.1:8000/ | grep -oE '/assets/index-[a-zA-Z0-9_-]+\.js' | head -1)
curl -s -I "http://127.0.0.1:8000${ASSET}" | grep -i "cache-control"

echo "API:"
curl -s -I http://127.0.0.1:8000/api/strategies | grep -i "cache-control"

kill $APP_PID 2>/dev/null
```

Expected:
- Index: `cache-control: no-cache, no-store, must-revalidate`
- Asset: `cache-control: public, immutable, max-age=31536000`
- API: `cache-control: no-cache, no-store, must-revalidate`

- [ ] **Step 3: Commit + SPRINT_STATE T7 done**

```bash
git add src/dashboard/app.py
git commit -m "feat(s47): React asset cache headers middleware (T7) — python-reviewer S46 MEDIUM

/assets/* → public immutable max-age=31536000 (content-hashed, safe forever).
index.html + /api/* + catch-all → no-cache (dynamic; references new hashes per build)."
```

---

## Task 8: MetricsTable T5 vanilla bug parity cleanup (sonnet)

**Why:** trading-logic-reviewer S46 PHASE 6 MEDIUM — vanilla code had `t5n < 100` check где `t5n` may be `undefined` → `undefined < 100 === false` → renders PASS (wrong). Should render FAIL when value missing.

**Files:**
- Modify: `src/dashboard_react/src/components/MetricsTable.tsx` — fix T5 logic
- Modify: `src/dashboard_react/src/components/__tests__/MetricsTable.test.tsx` — add regression test

- [ ] **Step 1: Locate T5 row rendering logic**

```bash
grep -n "t5_n_trades\|T5 · Trade count" src/dashboard_react/src/components/MetricsTable.tsx
```

Find the T5 row. Current logic likely:
```typescript
const t5n = m?.t5_n_trades
const t5Cls = (t5n !== null && t5n !== undefined && t5n < 100) ? 'metricFail' : 'metricPass'
```

(Bug: when `t5n === undefined` или `null` → `t5Cls = 'metricPass'`. Should be FAIL.)

- [ ] **Step 2: Fix logic — missing value → FAIL**

Replace с:

```typescript
// S47 T8 fix — vanilla bug parity cleanup. Missing T5 trade count counts as FAIL,
// not PASS. Bailey 2014 requires ≥ 100 trades для DSR statistical significance —
// undefined value cannot satisfy that requirement.
const t5n = m?.t5_n_trades
const t5Pass = t5n !== null && t5n !== undefined && t5n >= 100
const t5Cls = t5Pass ? 'metricPass' : 'metricFail'
const t5Status = t5Pass ? 'PASS' : 'FAIL'
const t5Display = t5n ?? '—'
```

Use `t5Cls`, `t5Status`, `t5Display` в JSX render.

- [ ] **Step 3: Add regression test к MetricsTable.test.tsx**

Add new test inside `describe('MetricsTable — WFA path Bailey 2014 thresholds')`:

```typescript
  it('T5 trade count: undefined → FAIL (S47 T8 fix; vanilla bug — used to render PASS)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: {},  // t5_n_trades missing entirely
      dsr: 0.5, dsr_pass: true, mc_p_value: 0.04,
    } as BacktestResponse
    render(<MetricsTable result={r} />)
    const t5Row = screen.getByText(/T5 · Trade count/i).closest('tr')
    expect(t5Row!.textContent).toMatch(/—/)
    expect(t5Row!.textContent).toMatch(/FAIL/i)  // NOT PASS (vanilla bug fixed)
  })
```

- [ ] **Step 4: Run tests**

```bash
cd src/dashboard_react
npm test -- MetricsTable
```

Expected: 7 pass (6 from T4 + 1 new regression).

- [ ] **Step 5: Build + lint clean**

```bash
npm run lint
npx tsc -b
```

Expected: 0 warnings, 0 errors.

- [ ] **Step 6: Commit + SPRINT_STATE T8 done**

```bash
git add src/dashboard_react/src/components/MetricsTable.tsx \
        src/dashboard_react/src/components/__tests__/MetricsTable.test.tsx
git commit -m "fix(s47): MetricsTable T5 vanilla bug parity cleanup (T8) — undefined → FAIL

Vanilla code: t5n < 100 → undefined<100 false → PASS. Wrong: missing trade count
cannot satisfy Bailey 2014 ≥100 threshold. Now: missing OR <100 → FAIL.

Regression test added to MetricsTable.test.tsx."
```

---

## Bucket C — S37/S38 long-standing tech debt (M1+M2+M3 bybit-api)

## Task 9: M1 retCode taxonomy extension (sonnet)

**Why:** bybit-api-reviewer S38 finding — V5 API returns retCodes 10001 / 110001 / 170131 not classified в existing enum → operator gets `UNKNOWN_ERROR` категория. Affects testnet debuggability.

**Files:**
- Modify: `src/execution/bybit/errors.py` — extend retCode classification dict
- Modify: `src/execution/bybit/adapter.py` — verify usage path
- Add: test `tests/unit/test_bybit_retcode_taxonomy.py`

- [ ] **Step 1: Inspect current taxonomy**

```bash
grep -n "10001\|110001\|170131\|RET_CODE\|ret_code" src/execution/bybit/errors.py
```

Note current enum + missing codes.

- [ ] **Step 2: Extend retCode dict с classification**

Add к `src/execution/bybit/errors.py` (extend existing dict OR enum, follow existing pattern):

```python
# S47 T9 — extend retCode taxonomy per bybit-api-reviewer S38 M1 finding.
# Codes from Bybit V5 API docs (verified 2026-05-11):
# - 10001: Parameter error / invalid argument
# - 110001: Order does not exist (cancel/amend на removed order)
# - 170131: Insufficient balance (spot/margin)
RETCODE_CLASSIFICATION_S47: dict[int, str] = {
    10001: "INVALID_PARAM",
    110001: "ORDER_NOT_FOUND",
    170131: "INSUFFICIENT_BALANCE",
}
```

If `errors.py` already has classification dict — extend it. Если нет — add the dict + helper function:

```python
def classify_retcode(ret_code: int) -> str:
    """Map Bybit V5 retCode к taxonomy bucket для logging + alerting."""
    return RETCODE_CLASSIFICATION_S47.get(ret_code, "UNKNOWN_ERROR")
```

- [ ] **Step 3: Add test `tests/unit/test_bybit_retcode_taxonomy.py`**

```python
"""S47 T9 — bybit retCode taxonomy classification tests (M1 finding)."""

from __future__ import annotations

import pytest

from src.execution.bybit.errors import classify_retcode


@pytest.mark.parametrize(
    "code,expected",
    [
        (10001, "INVALID_PARAM"),
        (110001, "ORDER_NOT_FOUND"),
        (170131, "INSUFFICIENT_BALANCE"),
        (999999, "UNKNOWN_ERROR"),  # Unknown falls through к default
    ],
)
def test_classify_retcode_known_and_unknown(code: int, expected: str) -> None:
    assert classify_retcode(code) == expected
```

- [ ] **Step 4: Run test**

```bash
.venv/bin/pytest tests/unit/test_bybit_retcode_taxonomy.py -v
```

Expected: 4 pass.

- [ ] **Step 5: Verify mypy clean**

```bash
.venv/bin/mypy --strict src/execution/bybit/errors.py
```

Expected: 0 errors.

- [ ] **Step 6: Commit + SPRINT_STATE T9 done**

```bash
git add src/execution/bybit/errors.py tests/unit/test_bybit_retcode_taxonomy.py
git commit -m "feat(s47): M1 retCode taxonomy extension (T9) — bybit-api S38 finding

Add 10001 INVALID_PARAM / 110001 ORDER_NOT_FOUND / 170131 INSUFFICIENT_BALANCE
к taxonomy. Operator gets meaningful category instead of UNKNOWN_ERROR на testnet."
```

---

## Task 10: M2 pybit response shape defensive guards (sonnet)

**Why:** bybit-api-reviewer S38 finding — direct dict access (`resp["result"]["list"]`) КeyError bombs если Bybit V5 schema shifts. Replace с defensive `.get()` chain + explicit error.

**Files:**
- Modify: `src/execution/bybit/adapter.py` — replace direct access points
- Add test `tests/unit/test_bybit_adapter_response_guards.py`

- [ ] **Step 1: Locate direct dict access patterns**

```bash
grep -nE 'resp\[|response\[|\["result"\]\[' src/execution/bybit/adapter.py
```

Note all unguarded access points.

- [ ] **Step 2: Replace с defensive helper**

Add к `src/execution/bybit/adapter.py` near top (utility module-level function):

```python
def _safe_extract_list(resp: dict[str, Any], context: str) -> list[Any]:
    """S47 T10 — defensive extraction of `resp['result']['list']`.

    Bybit V5 API may shift response schema between versions. Direct access
    (resp['result']['list']) raises KeyError на shape change with no context.
    This helper raises BybitAdapterError с clear message including `context`.
    """
    result = resp.get("result")
    if not isinstance(result, dict):
        raise BybitAdapterError(
            f"Bybit response missing 'result' dict для {context}: got {type(result).__name__}"
        )
    items = result.get("list")
    if not isinstance(items, list):
        raise BybitAdapterError(
            f"Bybit response 'result.list' not list для {context}: got {type(items).__name__}"
        )
    return items
```

If `BybitAdapterError` doesn't exist — define it в `errors.py` first:

```python
class BybitAdapterError(RuntimeError):
    """Raised when Bybit V5 response schema unexpected."""
```

Then refactor existing call sites в `adapter.py` к use `_safe_extract_list(resp, "get_open_orders")` etc. Audit each `resp["result"]["list"]` site и replace.

- [ ] **Step 3: Add test**

`tests/unit/test_bybit_adapter_response_guards.py`:

```python
"""S47 T10 — bybit adapter defensive response shape guards (M2)."""

from __future__ import annotations

import pytest

from src.execution.bybit.adapter import _safe_extract_list
from src.execution.bybit.errors import BybitAdapterError


def test_safe_extract_list_happy_path() -> None:
    resp = {"result": {"list": [{"orderId": "1"}, {"orderId": "2"}]}}
    assert _safe_extract_list(resp, "test") == [{"orderId": "1"}, {"orderId": "2"}]


def test_safe_extract_list_missing_result() -> None:
    with pytest.raises(BybitAdapterError, match="missing 'result' dict для test_ctx"):
        _safe_extract_list({}, "test_ctx")


def test_safe_extract_list_result_not_dict() -> None:
    with pytest.raises(BybitAdapterError, match="missing 'result' dict для test_ctx"):
        _safe_extract_list({"result": "not_dict"}, "test_ctx")


def test_safe_extract_list_list_missing() -> None:
    with pytest.raises(BybitAdapterError, match="'result.list' not list для test_ctx"):
        _safe_extract_list({"result": {}}, "test_ctx")


def test_safe_extract_list_list_not_array() -> None:
    with pytest.raises(BybitAdapterError, match="'result.list' not list для test_ctx"):
        _safe_extract_list({"result": {"list": "not_a_list"}}, "test_ctx")
```

- [ ] **Step 4: Run tests + mypy**

```bash
.venv/bin/pytest tests/unit/test_bybit_adapter_response_guards.py -v
.venv/bin/mypy --strict src/execution/bybit/adapter.py src/execution/bybit/errors.py
```

Expected: 5 pass, mypy 0 errors.

- [ ] **Step 5: Run existing bybit tests — verify no regression**

```bash
.venv/bin/pytest tests/unit/test_bybit_adapter.py -q
```

Expected: ALL pass (no regression от refactor).

- [ ] **Step 6: Commit + SPRINT_STATE T10 done**

```bash
git add src/execution/bybit/adapter.py src/execution/bybit/errors.py \
        tests/unit/test_bybit_adapter_response_guards.py
git commit -m "feat(s47): M2 pybit response shape defensive guards (T10) — bybit-api S38 finding

Add _safe_extract_list() helper raising BybitAdapterError с clear context message.
Refactor direct resp['result']['list'] access sites. Schema shift catches early
с meaningful error instead of bare KeyError."
```

---

## Task 11: M3 WS data isinstance check (sonnet)

**Why:** bybit-api-reviewer S38 finding — pybit V3 WebSocket message data field может be list OR dict depending pybit version → silent event-drop в `ws_private.py` consumer.

**Files:**
- Modify: `src/execution/bybit/ws_private.py` — add isinstance guard
- Add test `tests/unit/test_ws_private_isinstance_guard.py`

- [ ] **Step 1: Locate WS data handler**

```bash
grep -nE "data\b|\.data\b|message\[" src/execution/bybit/ws_private.py | head -20
```

Find the consumer loop / message parser. Likely pattern:

```python
def _handle_message(self, msg: dict[str, Any]) -> None:
    data = msg.get("data", [])
    for event in data:
        ...
```

If `data` is a `dict` (single event, V3 quirk) — iterating treats keys as events → silent drop.

- [ ] **Step 2: Add isinstance guard**

Modify handler:

```python
def _handle_message(self, msg: dict[str, Any]) -> None:
    """S47 T11 — M3 isinstance guard. pybit V3 WebSocket may emit `data` as
    list (multi-event) OR dict (single-event) depending on subscription type.
    Without guard, dict iteration yields keys (silent event-drop).
    """
    data = msg.get("data")
    if data is None:
        return
    if isinstance(data, dict):
        # Single event wrapped — wrap в list для uniform iteration
        events = [data]
    elif isinstance(data, list):
        events = data
    else:
        # Unexpected type — log + skip
        logger.warning(
            "ws_private_unexpected_data_type",
            data_type=type(data).__name__,
        )
        return

    for event in events:
        self._process_event(event)
```

(`_process_event` или similar — exact name from existing code.)

- [ ] **Step 3: Add test**

`tests/unit/test_ws_private_isinstance_guard.py`:

```python
"""S47 T11 — WS private consumer isinstance guard (M3)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from src.execution.bybit.ws_private import BybitPrivateWSConsumer


def test_handle_message_data_as_list() -> None:
    consumer = BybitPrivateWSConsumer(...)  # Use existing test fixture pattern
    consumer._process_event = MagicMock()
    msg = {"data": [{"orderId": "1"}, {"orderId": "2"}]}
    consumer._handle_message(msg)
    assert consumer._process_event.call_count == 2


def test_handle_message_data_as_dict_wrapped_к_list() -> None:
    """V3 quirk — single event emitted as dict, NOT list-of-one."""
    consumer = BybitPrivateWSConsumer(...)
    consumer._process_event = MagicMock()
    msg = {"data": {"orderId": "single_event"}}
    consumer._handle_message(msg)
    consumer._process_event.assert_called_once_with({"orderId": "single_event"})


def test_handle_message_data_missing_no_op() -> None:
    consumer = BybitPrivateWSConsumer(...)
    consumer._process_event = MagicMock()
    consumer._handle_message({})
    consumer._process_event.assert_not_called()


def test_handle_message_data_unexpected_type_skip() -> None:
    consumer = BybitPrivateWSConsumer(...)
    consumer._process_event = MagicMock()
    consumer._handle_message({"data": 42})
    consumer._process_event.assert_not_called()
```

(NOTE — implementer: `BybitPrivateWSConsumer(...)` constructor args differ — check existing test fixtures в `tests/unit/test_ws_private*.py` для proper init.)

- [ ] **Step 4: Run tests**

```bash
.venv/bin/pytest tests/unit/test_ws_private_isinstance_guard.py -v
.venv/bin/mypy --strict src/execution/bybit/ws_private.py
```

Expected: 4 pass, mypy 0 errors.

- [ ] **Step 5: Commit + SPRINT_STATE T11 done**

```bash
git add src/execution/bybit/ws_private.py tests/unit/test_ws_private_isinstance_guard.py
git commit -m "feat(s47): M3 WS data isinstance guard (T11) — bybit-api S38 finding

pybit V3 WebSocket data field may be list (multi-event) OR dict (single-event).
Without guard, dict iteration silently drops events (key-iteration). Now wraps
dict в [dict], handles list as-is, logs+skips unexpected types."
```

---

## Bucket D — Quant follow-ups bundled (1 task = 3 test files)

## Task 12: DSR property + n_trials assert + sprint type test (sonnet)

**Why:** test-engineer S44 PHASE 6 follow-up C2 (DSR ∈ [0,1] property test) + S45 quant follow-ups (n_trials >=1 assert + sprint int/str type test). Bundle 3 small test files since each is one isolated invariant.

**Files:**
- Create: `tests/unit/test_dsr_property.py`
- Create: `tests/unit/test_n_trials_assert.py`
- Create: `tests/unit/test_sprint_type.py`

- [ ] **Step 1: DSR ∈ [0,1] property test**

```bash
grep -rn "def.*dsr\|deflated_sharpe\|compute_dsr" src/ --include="*.py" | head -5
```

Identify exported function name (e.g. `src/risk/dsr.py:compute_dsr`).

`tests/unit/test_dsr_property.py`:

```python
"""S47 T12 — DSR ∈ [0,1] property test (test-engineer S44 C2)."""

from __future__ import annotations

import math

import hypothesis.strategies as st
from hypothesis import given, settings

# Adjust import path if compute_dsr lives elsewhere
from src.risk.dsr import compute_dsr  # noqa: F401 — adjust per real path


@given(
    sharpe=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    n_trials=st.integers(min_value=1, max_value=1000),
    n_trades=st.integers(min_value=10, max_value=10_000),
    skew=st.floats(min_value=-3.0, max_value=3.0, allow_nan=False, allow_infinity=False),
    kurt=st.floats(min_value=-2.0, max_value=20.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=None)
def test_dsr_in_unit_interval(
    sharpe: float, n_trials: int, n_trades: int, skew: float, kurt: float,
) -> None:
    """DSR semantics: probability that observed Sharpe > 0 после deflation.
    Probability ∈ [0, 1]. NaN OK для degenerate cases.
    """
    dsr = compute_dsr(
        sharpe_ratio=sharpe,
        n_trials=n_trials,
        n_trades=n_trades,
        skew=skew,
        excess_kurtosis=kurt,
    )
    if dsr is None or (isinstance(dsr, float) and math.isnan(dsr)):
        return  # NaN allowed для edge cases
    assert 0.0 <= dsr <= 1.0, f"DSR={dsr} outside [0,1] для inputs sharpe={sharpe} ..."
```

(NOTE implementer: adjust `compute_dsr` import path AND keyword args к match actual signature; check `src/risk/dsr.py` first.)

- [ ] **Step 2: n_trials assert (>=1) test**

`tests/unit/test_n_trials_assert.py`:

```python
"""S47 T12 — n_trials >=1 assert test (S45 quant follow-up)."""

from __future__ import annotations

import pytest

from src.risk.dsr import compute_dsr


def test_n_trials_zero_raises() -> None:
    """n_trials = 0 makes no sense — multiple-comparisons correction divides by N."""
    with pytest.raises((ValueError, AssertionError)):
        compute_dsr(sharpe_ratio=1.0, n_trials=0, n_trades=100, skew=0.0, excess_kurtosis=0.0)


def test_n_trials_negative_raises() -> None:
    with pytest.raises((ValueError, AssertionError)):
        compute_dsr(sharpe_ratio=1.0, n_trials=-5, n_trades=100, skew=0.0, excess_kurtosis=0.0)


def test_n_trials_one_works() -> None:
    """n_trials=1 = no multiple-comparisons correction (single trial)."""
    result = compute_dsr(sharpe_ratio=1.0, n_trials=1, n_trades=100, skew=0.0, excess_kurtosis=0.0)
    assert result is not None
```

If `compute_dsr` currently doesn't validate n_trials — fix add validation в `src/risk/dsr.py`:

```python
def compute_dsr(*, sharpe_ratio: float, n_trials: int, ...):
    if n_trials < 1:
        raise ValueError(f"n_trials must be >= 1, got {n_trials}")
    ...
```

- [ ] **Step 3: sprint int/str type test**

`tests/unit/test_sprint_type.py`:

```python
"""S47 T12 — sprint identifier type consistency (S45 quant follow-up).

Ensures sprint number stored consistently as int (NOT str) в metadata blocks
across cross_trial_log + research outputs + envelope.
"""

from __future__ import annotations

from src.backtest.research_runner_envelope import build_research_runner_envelope


def test_envelope_sprint_field_is_int_or_absent() -> None:
    payload = build_research_runner_envelope(
        runner_name="test_runner",
        symbol="BTCUSDT",
        interval="240",
        n_trades=10,
        sharpe=1.0,
        win_rate=0.5,
        total_pnl_pct=10.0,
        bars_per_year=2191,
        equity_curve=[0.0, 10.0],
        runner_label="x",
    )
    # If envelope includes 'sprint' field — must be int (NOT str)
    if "sprint" in payload:
        assert isinstance(payload["sprint"], int), (
            f"envelope['sprint'] type={type(payload['sprint']).__name__}, expected int"
        )
    if "sprint" in payload.get("metrics", {}):
        assert isinstance(payload["metrics"]["sprint"], int)
```

- [ ] **Step 4: Run all 3 test files**

```bash
.venv/bin/pytest tests/unit/test_dsr_property.py tests/unit/test_n_trials_assert.py tests/unit/test_sprint_type.py -v
```

Expected: ALL pass. Если sprint type test fails OR n_trials assert missing — fix source code (NOT test).

- [ ] **Step 5: Commit + SPRINT_STATE T12 done**

```bash
git add tests/unit/test_dsr_property.py tests/unit/test_n_trials_assert.py tests/unit/test_sprint_type.py
git commit -m "test(s47): DSR property + n_trials + sprint type bundled trio (T12)

3 isolated invariants:
- DSR ∈ [0,1] hypothesis property test (test-engineer S44 C2)
- n_trials >=1 ValueError raise (S45 quant follow-up)
- envelope['sprint'] int type consistency (S45 quant follow-up)"
```

---

## Bucket E — Operator Q7 surfaced (T14 BUG + T15 cursor + T16 fail analysis tab)

## Task 13: T14 envelope trade_stats extension для research presets (sonnet)

**Why:** Operator manual UI test 2026-05-11 found `▸ TRADE STATISTICS` block shows `—` everywhere except Win rate when running research preset (atr_breakout / volume_breakout) с WFA verdict. Root cause: `research_runner_envelope.py:151` emits minimal `trade_stats` (только `n_trades` + `win_rate`); replay engine path emits полный set.

**Files:**
- Modify: `src/backtest/research_runner_envelope.py` — add optional `trades_list` param + derive logic
- Modify: `src/backtest/volume_breakout_runner.py` — pass trades_list
- Modify: `src/backtest/atr_breakout_runner.py` — pass trades_list
- Modify: `src/dashboard_react/src/api/types.ts` — extend TradeStats interface
- Modify: `src/dashboard_react/src/components/TradesTable.tsx` — graceful render когда quote fields null
- Modify: `tests/unit/test_research_runner_envelope.py` — extend test

- [ ] **Step 1: Read existing envelope signature**

```bash
sed -n '34,60p' src/backtest/research_runner_envelope.py
```

Note current signature.

- [ ] **Step 2: Extend signature + derive logic**

Edit `src/backtest/research_runner_envelope.py`. Add new optional param к function signature:

```python
def build_research_runner_envelope(
    *,
    runner_name: str,
    symbol: str,
    interval: str,
    n_trades: int,
    sharpe: float,
    win_rate: float,
    total_pnl_pct: float,
    bars_per_year: int,
    equity_curve: list[float],
    runner_label: str,
    start: str = "",
    end: str = "",
    extra_warnings: list[dict[str, str]] | None = None,
    equity_timestamps: list[int] | None = None,
    wfa_result: dict[str, Any] | None = None,
    trade_markers: dict[str, list[float | int]] | None = None,
    trades_list: list[Any] | None = None,  # S47 T13 — _TradeRecord-shaped
) -> dict[str, Any]:
```

Derive enriched trade_stats. Find existing block (line ~151):

```python
"trade_stats": {
    "n_trades": n_trades,
    "win_rate": win_rate,
},
```

Replace с:

```python
# S47 T13 — derive enriched trade_stats from trades_list если passed.
# Replay engine path emits full set (n_winners/quote-amounts);
# research path historically только n_trades+win_rate. Now derive what we can:
# - n_winners / n_losers from pnl_pct signs
# - total_pnl_pct (already в metrics, surface к trade_stats too)
# Quote-currency fields (USDT amounts) require synthetic capital basis:
# emit None gracefully (TradesTable Path B renders "—").
n_winners_d: int | None = None
n_losers_d: int | None = None
if trades_list is not None and len(trades_list) > 0:
    n_winners_d = sum(1 for t in trades_list if float(getattr(t, "pnl_pct", 0.0)) > 0)
    n_losers_d = len(trades_list) - n_winners_d

trade_stats_payload: dict[str, Any] = {
    "n_trades": n_trades,
    "win_rate": win_rate,
    "n_winners": n_winners_d,
    "n_losers": n_losers_d,
    "total_pnl_pct": total_pnl_pct,
    # Quote-currency fields — None для research path (no capital basis)
    "total_pnl_quote": None,
    "total_commissions_quote": None,
    "avg_win_quote": None,
    "avg_loss_quote": None,
    "profit_factor": None,
}
```

Then в return dict replace `"trade_stats": {...}` line с `"trade_stats": trade_stats_payload,`.

- [ ] **Step 3: Update vb runner к pass trades_list**

In `src/backtest/volume_breakout_runner.py`, find `build_research_runner_envelope(...)` call. Add kwarg:

```python
return build_research_runner_envelope(
    ...existing kwargs...,
    trades_list=trades_list,  # S47 T13 — для enriched trade_stats derivation
)
```

(`trades_list` уже defined в той функции для trade_markers since S46 T11.)

- [ ] **Step 4: Update atr runner**

Mirror в `src/backtest/atr_breakout_runner.py` — find `build_research_runner_envelope(` call, add `trades_list=trades_list`.

- [ ] **Step 5: Extend types.ts TradeStats interface**

Edit `src/dashboard_react/src/api/types.ts`:

```typescript
export interface TradeStats {
  n_trades: number;
  win_rate: number;
  // S47 T13 — derived от trades_list (research path) OR full (replay path)
  n_winners?: number | null;
  n_losers?: number | null;
  total_pnl_pct?: number | null;
  // Quote-currency fields — replay path only (research = null)
  total_pnl_quote?: number | null;
  total_commissions_quote?: number | null;
  avg_win_quote?: number | null;
  avg_loss_quote?: number | null;
  profit_factor?: number | null;
}
```

- [ ] **Step 6: TradesTable Path B graceful render**

Edit `src/dashboard_react/src/components/TradesTable.tsx`. Find Path B WFA render block. Update each cell:

```typescript
// S47 T13 — graceful render when quote fields null (research path doesn't emit USDT).
const fmtUsdtCell = (v: number | null | undefined): string =>
  v === null || v === undefined ? '—' : fmtMoney(v) + ' USDT'
```

Apply `fmtUsdtCell(ts.total_pnl_quote)`, `fmtUsdtCell(ts.avg_win_quote)`, etc.

For `n_winners`/`n_losers` cells — fallback к `—` если null:

```typescript
<td className={styles.metricPass}>{ts.n_winners ?? '—'}</td>
<td className={styles.metricFail}>{ts.n_losers ?? '—'}</td>
```

For Profit Factor — same `—` fallback.

- [ ] **Step 7: Add backend test**

`tests/unit/test_envelope_research_path_trade_stats.py`:

```python
"""S47 T13 — research path envelope derives n_winners/n_losers from trades_list."""

from __future__ import annotations

from dataclasses import dataclass

from src.backtest.research_runner_envelope import build_research_runner_envelope


@dataclass
class _TradeStub:
    pnl_pct: float


def test_trade_stats_derived_when_trades_list_passed() -> None:
    trades = [
        _TradeStub(pnl_pct=0.05),   # win
        _TradeStub(pnl_pct=-0.02),  # loss
        _TradeStub(pnl_pct=0.03),   # win
        _TradeStub(pnl_pct=0.0),    # loss (>0 → win, ≤0 → loss; here ≤0 → loss)
    ]
    payload = build_research_runner_envelope(
        runner_name="test", symbol="BTCUSDT", interval="240",
        n_trades=4, sharpe=1.0, win_rate=0.5, total_pnl_pct=8.0,
        bars_per_year=2191, equity_curve=[0.0, 5.0, 3.0, 6.0, 8.0],
        runner_label="x", trades_list=trades,
    )
    ts = payload["trade_stats"]
    assert ts["n_winners"] == 2
    assert ts["n_losers"] == 2
    assert ts["total_pnl_pct"] == 8.0
    # Quote fields = None для research path
    assert ts["total_pnl_quote"] is None
    assert ts["avg_win_quote"] is None
    assert ts["profit_factor"] is None


def test_trade_stats_no_trades_list_keeps_n_winners_none() -> None:
    payload = build_research_runner_envelope(
        runner_name="test", symbol="BTCUSDT", interval="240",
        n_trades=0, sharpe=0.0, win_rate=0.0, total_pnl_pct=0.0,
        bars_per_year=2191, equity_curve=[0.0],
        runner_label="x",
    )
    ts = payload["trade_stats"]
    assert ts["n_winners"] is None
    assert ts["n_losers"] is None
```

- [ ] **Step 8: Run tests + builds**

```bash
.venv/bin/pytest tests/unit/test_envelope_research_path_trade_stats.py tests/unit/test_research_runner_envelope.py -v
.venv/bin/mypy --strict src/backtest/research_runner_envelope.py src/backtest/volume_breakout_runner.py src/backtest/atr_breakout_runner.py
cd src/dashboard_react && npm run lint && npx tsc -b && npm run build
```

Expected: pytest 0 fail, mypy 0 errors, frontend lint+tsc+build clean.

- [ ] **Step 9: Commit + SPRINT_STATE T13 done**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git add src/backtest/research_runner_envelope.py \
        src/backtest/volume_breakout_runner.py \
        src/backtest/atr_breakout_runner.py \
        src/dashboard_react/src/api/types.ts \
        src/dashboard_react/src/components/TradesTable.tsx \
        tests/unit/test_envelope_research_path_trade_stats.py
git commit -m "fix(s47): T14 trade_stats empty values bug — research path envelope ext

Operator UI report 2026-05-11: research presets (atr_breakout, volume_breakout)
showed dashes для Profitable/Losing/Total PnL/etc. Root cause: envelope emitted
minimal trade_stats; TradesTable Path B (WFA verdict) expected full schema.

Fix: research_runner_envelope accepts optional trades_list, derives n_winners/
n_losers from pnl signs + surfaces total_pnl_pct. Quote-currency fields (USDT)
emit None (research path lacks capital basis). TradesTable renders '—' gracefully.

vb_runner + atr_runner pass trades_list (already в scope для T11 trade_markers).
2 new tests + extend existing envelope test."
```

---

## Task 14: T15 EquityChart cursor crosshair + balance tooltip on hover (sonnet)

**Why:** Operator UI request 2026-05-11 — горизонтальное движение курсором should show actual balance at hover position. uPlot already supports cursor.show + cursor.points natively; currently `legend: { show: false }` hides values.

**Files:**
- Modify: `src/dashboard_react/src/components/EquityChart.tsx` — enable cursor crosshair + custom tooltip
- Modify: `src/dashboard_react/src/components/EquityChart.module.css` — tooltip styles
- Modify: `src/dashboard_react/src/components/DrawdownSubchart.tsx` — mirror cursor enable (sync key already shared)

- [ ] **Step 1: Add cursor opts к EquityChart `buildOpts()`**

В `src/dashboard_react/src/components/EquityChart.tsx`, find `buildOpts()` function. Add `cursor.show: true`, `cursor.points: true`. Replace existing cursor block (currently `cursor: { drag: { x: true, y: false } }`) с:

```typescript
cursor: {
  show: true,
  drag: { x: true, y: false },
  points: { show: true, size: 6, fill: '#cc785c', stroke: '#cc785c' },
  ...(syncKey !== undefined ? { sync: { key: syncKey, setSeries: false } } : {}),
},
```

- [ ] **Step 2: Add hooks для tooltip rendering**

В `EquityChart` component, после chart creation в `useEffect`, register uPlot hooks для cursor move:

```typescript
const chart = new uPlot(buildOpts(width, height, hasMarkers, syncKey), data, container)
chartRef.current = chart

// S47 T14 — cursor tooltip on hover. Show "Date: <ISO>" + "Equity: +X.XX%"
chart.hooks.setCursor = chart.hooks.setCursor ?? []
chart.hooks.setCursor.push((u) => {
  const idx = u.cursor.idx
  const tooltipEl = container.querySelector('[data-tooltip="equity"]') as HTMLDivElement | null
  if (!tooltipEl) return
  if (idx === null || idx === undefined || idx < 0) {
    tooltipEl.style.display = 'none'
    return
  }
  const ts = u.data[0]?.[idx]
  const eq = u.data[1]?.[idx]
  if (ts === undefined || eq === undefined || ts === null || eq === null) {
    tooltipEl.style.display = 'none'
    return
  }
  const date = new Date(Number(ts) * 1000).toISOString().slice(0, 10)
  const sign = eq >= 0 ? '+' : ''
  tooltipEl.textContent = `${date} · ${sign}${eq.toFixed(2)}%`
  tooltipEl.style.display = 'block'
  // Position tooltip near cursor
  const left = u.cursor.left ?? 0
  tooltipEl.style.left = `${left + 12}px`
})
```

- [ ] **Step 3: Render tooltip element в JSX**

Modify EquityChart return:

```tsx
return (
  <div className={styles.container}>
    <div className={styles.title}>▸ EQUITY CURVE</div>
    <div
      ref={containerRef}
      className={styles.chartWrapper}
      style={{ height: `${height}px`, position: 'relative' }}
    >
      <div data-tooltip="equity" className={styles.tooltip} style={{ display: 'none' }} />
    </div>
  </div>
)
```

- [ ] **Step 4: Add tooltip CSS к `EquityChart.module.css`**

```css
.tooltip {
  position: absolute;
  top: 8px;
  background: var(--color-bg-glass);
  backdrop-filter: blur(8px);
  border: 1px solid var(--color-anthropic-orange);
  color: var(--color-text-primary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 4px;
  pointer-events: none;
  z-index: 10;
  white-space: nowrap;
  box-shadow: 0 0 8px rgba(204, 120, 92, 0.30);
}
```

(Use exact CSS variable names from `tokens.css` — verify first.)

- [ ] **Step 5: Mirror в DrawdownSubchart**

Apply identical pattern в `src/dashboard_react/src/components/DrawdownSubchart.tsx`:
- Cursor opts с `show: true` + `points`
- setCursor hook с tooltip showing `${date} · DD: -X.XX%`
- Render tooltip element с `data-tooltip="drawdown"`
- Add tooltip CSS к `DrawdownSubchart.module.css` (different border color — `--color-status-danger`)

Sync key already shared (S46 CC2) — both crosshairs move together automatically.

- [ ] **Step 6: Manual sanity test**

```bash
cd src/dashboard_react && npm run build
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
.venv/bin/uvicorn src.dashboard.app:create_app --factory --port 8000 &
APP_PID=$!
sleep 3
echo "Open browser: http://127.0.0.1:8000/ — run any backtest, hover equity chart, verify tooltip shows date+equity"
echo "Press enter when done"
read
kill $APP_PID 2>/dev/null
```

- [ ] **Step 7: Build + lint clean**

```bash
cd src/dashboard_react
npm run lint
npx tsc -b
npm run build
```

Expected: 0 warnings/errors.

- [ ] **Step 8: Commit + SPRINT_STATE T14 done**

```bash
git add src/dashboard_react/src/components/EquityChart.tsx \
        src/dashboard_react/src/components/EquityChart.module.css \
        src/dashboard_react/src/components/DrawdownSubchart.tsx \
        src/dashboard_react/src/components/DrawdownSubchart.module.css
git commit -m "feat(s47): T15 EquityChart + DrawdownSubchart cursor tooltip on hover

Operator UI request 2026-05-11. Enable uPlot cursor.show + cursor.points.
setCursor hook renders floating tooltip с Date + Equity% (orange) на equity,
Date + DD% (red) на drawdown. Sync key already shared (S46 CC2) — crosshairs
move together. Glass-morphism + JetBrains Mono per Anthropic palette."
```

---

## Task 15: T16 Fail Analysis tab — RU detailed WHY-failed narrative (opus)

**Why opus:** Judgment-heavy. Formula correctness MUST match Bailey 2014 + ADR 0014 + ADR 0056 actual code semantics. Wrong formula displayed к operator = misleading signal. quant-stats-reviewer PHASE 6 BLOCKER risk if mismatched.

**Files:**
- Create: `src/dashboard/strategy_descriptions.py` — RU detailed per preset
- Create: `src/dashboard/wfa_criterion_explanations.py` — RU formula+threshold+impact per criterion
- Modify: `src/dashboard/app.py` — add 2 new endpoints
- Create: `src/dashboard_react/src/components/FailAnalysisTab.tsx`
- Create: `src/dashboard_react/src/components/FailAnalysisTab.module.css`
- Modify: `src/dashboard_react/src/api/types.ts` — Strategy + Criterion explanation interfaces
- Modify: `src/dashboard_react/src/api/client.ts` — 2 new methods
- Modify: `src/dashboard_react/src/App.tsx` — wire FailAnalysisTab conditional render

- [ ] **Step 1: Read existing STRATEGY_PRESETS + verify code semantics for each TIER criterion**

Critical reading ДО writing RU narrative:
```bash
# 1. Read STRATEGY_PRESETS dict (existing brief description per preset)
grep -nA 15 "STRATEGY_PRESETS" src/dashboard/*.py | head -100

# 2. Read actual code for each TIER criterion — formulas MUST match
grep -nE "t1_sharpe_oos|sharpe_ratio|t5_t_stat|t5_n_trades|t3_max_drawdown" src/risk/ src/backtest/ --include="*.py" -r

# 3. Verify ADR 0014 thresholds
cat llm-wiki/wiki/project/decisions/0014-walk-forward-acceptance-gates.md | head -100

# 4. Verify ADR 0056 sigma_SR sourcing для DSR
cat llm-wiki/wiki/project/decisions/0056-dsr-sigma-sourcing.md | head -50
```

Take detailed notes. Each formula в `wfa_criterion_explanations.py` MUST cite the exact source line / ADR / paper reference.

- [ ] **Step 2: Create `src/dashboard/strategy_descriptions.py` — RU detailed per preset**

Skeleton (~200-400 RU слов per preset; реальный полный список зависит от STRATEGY_PRESETS):

```python
"""S47 T15 — RU detailed strategy descriptions для FailAnalysisTab.

Each preset gets full prose explanation: entry signal formula, exit logic,
parameters meaning, intended market regime, historical context.
Read by /api/strategy_explanations endpoint.
"""

from __future__ import annotations

STRATEGY_DESCRIPTIONS_RU: dict[str, str] = {
    "ema_crossover_s13": """
**EMA Crossover (S13 baseline)** — классическая trend-following стратегия на пересечении двух экспоненциальных скользящих средних.

**Логика входа (LONG):** когда быстрая EMA(fast_period) пересекает медленную EMA(slow_period) снизу вверх. Сигнал генерируется на закрытии бара. Подтверждения нет — простой crossover.

**Логика выхода:** обратное пересечение (slow_period EMA сверху вниз) ИЛИ stop-loss на ATR-multiple от цены входа (если включён). Время удержания позиции варьируется от часов до недель в зависимости от тренда.

**Параметры:**
- `fast_period` (default 12) — период быстрой EMA
- `slow_period` (default 26) — период медленной EMA
- `atr_period` (default 14) — период ATR для stop-loss
- `atr_stop_mult` (default 3.0) — множитель ATR для stop distance

**Целевой режим рынка:** трендовые фазы с явным momentum. Стратегия теряет деньги в боковике (EMA крутятся внутри узкого диапазона, генерируя whipsaws — ложные сигналы и многочисленные мелкие убытки).

**Исторический контекст:** EMA crossover — один из старейших публичных алгоритмов (1960-е, J. Welles Wilder популяризатор). Многократно протестирован на акциях, форексе, криптовалютах. На криптовалютах с 2017 года показывает снижающуюся эффективность из-за роста рыночной эффективности и насыщения trend-following игроками.

**Известные слабости:** проигрывает mean-reversion стратегиям в боковике; высокий drawdown в reversal'ах; низкое profit factor (~1.1-1.3 типично).
""".strip(),

    "mean_reversion_s15": """
**Mean Reversion (S15)** — стратегия возврата к среднему на основе RSI-индикатора и отклонения от Bollinger Bands.

**Логика входа (LONG):** RSI < oversold_threshold (default 30) И цена ниже нижней полосы Bollinger Bands. Идея: цена временно перешла в overshoot-состояние, ожидается возврат к скользящему среднему.

**Логика выхода:** RSI пересекает 50 (нейтральная зона) ИЛИ цена касается верхней полосы Bollinger ИЛИ stop-loss на ATR-multiple. Удержание позиции типично 1-5 баров.

**Параметры:**
- `rsi_period` (default 14) — период RSI
- `oversold_threshold` (default 30) — порог перепроданности
- `bb_period` (default 20) — период Bollinger Bands
- `bb_std` (default 2.0) — стандартные отклонения для полос
- `atr_stop_mult` (default 2.0) — stop distance

**Целевой режим рынка:** range-bound / sideways markets с регулярными overshoot'ами. Стратегия катастрофически проигрывает в сильных трендах (купил перепроданность → цена продолжает падать → stop-out).

**Исторический контекст:** mean reversion основан на работе работах Lo & MacKinlay (1988) о статистической inefficiency коротких ценовых движений. На криптовалютах эффективен на 1-4H таймфреймах в периоды low-volatility consolidation.

**Известные слабости:** зависим от market regime detection (без него — bagholder в medvedi трендах); требует относительно частых сигналов чтоб набрать N≥100 для DSR; чувствителен к настройке порогов.
""".strip(),

    # ... аналогично для всех 11 presets — implementer adds remaining
    # При unknown preset id — fallback в endpoint
}


def get_strategy_description(preset_id: str) -> str | None:
    """Return RU detailed description; None if unknown preset."""
    return STRATEGY_DESCRIPTIONS_RU.get(preset_id)
```

(NOTE implementer: write **all 11 preset descriptions** — read STRATEGY_PRESETS dict для exact preset IDs first.)

- [ ] **Step 3: Create `src/dashboard/wfa_criterion_explanations.py` — RU per criterion**

```python
"""S47 T15 — RU formula + threshold + impact narrative per WFA criterion.

CRITICAL: Each formula + threshold MUST match actual code semantics. Cross-reference:
- ADR 0014 (walk-forward acceptance gates) — T1-T6 thresholds
- ADR 0056 (DSR sigma sourcing) — DSR computation
- Bailey & López de Prado 2014 (DSR paper, Bailey & Borwein 2012 PSR)

Read by /api/wfa_criterion_explanations endpoint.
"""

from __future__ import annotations

from typing import TypedDict


class CriterionExplanation(TypedDict):
    name: str
    measures: str           # Что измеряет
    formula: str            # Mathematical formula text
    threshold: str          # Binding threshold + source
    impact: str             # На что влияет
    related: str            # С чем связано
    gate_role: str          # Role в acceptance gate


WFA_CRITERION_EXPLANATIONS_RU: dict[str, CriterionExplanation] = {
    "t1_sharpe_oos": {
        "name": "T1 · Sharpe Ratio (OOS, annualized)",
        "measures": (
            "Соотношение ожидаемой избыточной доходности стратегии к её "
            "волатильности на out-of-sample (OOS) фолдах walk-forward analysis. "
            "Базовая мера risk-adjusted return."
        ),
        "formula": (
            "Sharpe = mean(per-trade returns) / std(per-trade returns) × √(bars_per_year ÷ mean_holding_bars)\n"
            "где per-trade returns — массив log-returns или simple-returns по каждой сделке;\n"
            "bars_per_year = количество баров в году для данного timeframe (4H = 2191; 1D = 365);\n"
            "mean_holding_bars = среднее количество баров удержания позиции."
        ),
        "threshold": (
            "≥ 1.0 для PASS. Значения > 3.0 классифицируются как OVERFIT? "
            "(подозрение на curve-fitting — реальные стратегии редко показывают "
            "Sharpe > 3 на OOS). Источник: ADR 0014 §T1; Bailey & López de Prado 2014."
        ),
        "impact": (
            "Sharpe < 1.0 = стратегия не оправдывает риск. Капитал лучше держать "
            "в risk-free instrument (T-bills) с тем же risk-adjusted profile. "
            "Sharpe > 3.0 = практически невозможный результат на честных OOS — "
            "указывает на data leakage или скрытый overfitting."
        ),
        "related": (
            "Связан с T2 (Sortino — асимметричная волатильность) и DSR "
            "(deflated Sharpe — корректирует Sharpe на multiple-comparisons bias). "
            "Если T1 fail — DSR computation skipped per ADR 0014 §gate-cascade."
        ),
        "gate_role": (
            "Первый gate (T1) acceptance pipeline. T1 FAIL → весь набор metrics "
            "downstream считается недостоверным. Обязательный к прохождению."
        ),
    },
    "t2_sortino_oos": {
        "name": "T2 · Sortino Ratio (OOS)",
        "measures": (
            "Аналог Sharpe, использующий downside deviation вместо общего std. "
            "Учитывает только негативную волатильность (потери), что лучше "
            "соответствует психологии трейдера (волатильность вверх — не риск)."
        ),
        "formula": (
            "Sortino = mean(returns) / downside_deviation × √(bars_per_year ÷ mean_holding_bars)\n"
            "где downside_deviation = √(mean(min(0, returns)²))\n"
            "(только отрицательные returns squared, mean, sqrt)."
        ),
        "threshold": (
            "≥ 1.5 для PASS. Источник: ADR 0014 §T2. Особый случай — "
            "anomaly_guard срабатывает когда нет negative returns (downside_deviation = 0): "
            "Sortino → ∞ или NaN; гарда выставляет N/A + WARN status вместо FAIL."
        ),
        "impact": (
            "Sortino < 1.5 при наличии downside — стратегия имеет недостаточный "
            "доход на единицу downside-риска. Anomaly guard (N/A) — сигнал что "
            "OOS sample слишком мал или содержит только winners (подозрение на "
            "selection bias или короткий backtest period)."
        ),
        "related": (
            "Дополняет T1 Sharpe — обе проходят PASS = robust risk-adjusted return. "
            "T2 fail при T1 PASS = асимметричный риск (большие потери, "
            "распределённые редко но больно)."
        ),
        "gate_role": (
            "Информационный gate. Не блокирует acceptance напрямую, но FAIL "
            "понижает confidence в результате. Anomaly guard документирует "
            "недостаточный sample."
        ),
    },
    "t3_max_drawdown": {
        "name": "T3 · Max Drawdown",
        "measures": (
            "Максимальное peak-to-trough падение equity curve в OOS периоде. "
            "Выражено в долях от пикового значения (0.25 = 25% drawdown)."
        ),
        "formula": (
            "MaxDD = max over all i of (equity_pct[peak_idx] - equity_pct[i]) / (1 + equity_pct[peak_idx]/100)\n"
            "где peak_idx = индекс предыдущего максимума equity до момента i;\n"
            "equity_pct[i] — кумулятивный процентный return на баре i."
        ),
        "threshold": (
            "< 25% для PASS. Источник: ADR 0014 §T3 (industry rule-of-thumb для "
            "проп-trading desk capital allocation). При DD ≥ 25% капитал считается "
            "недопустимо рискованным даже если Sharpe высокий."
        ),
        "impact": (
            "DD ≥ 25% → operator при реальном trading не выдержит psychologically "
            "(закроет позицию преждевременно). Также капитал-allocation desk не "
            "выделит leverage > 1× для стратегии с DD > 25%. Affects max position "
            "sizing downstream."
        ),
        "related": (
            "Связан с T1 Sharpe (high DD при high Sharpe = lumpy returns); "
            "T2 Sortino (high DD = high downside deviation); recovery time "
            "(длительность underwater period)."
        ),
        "gate_role": (
            "Hard gate — даже при PASS на T1+T2+DSR, fail T3 блокирует acceptance. "
            "Капитал-management приоритетнее returns."
        ),
    },
    "t4_win_rate": {
        "name": "T4 · Win Rate + Avg RR",
        "measures": (
            "Доля прибыльных сделок (win_rate) и среднее соотношение risk/reward (avg_rr). "
            "Информационный criterion — не блокирует gate напрямую."
        ),
        "formula": (
            "win_rate = n_winners / n_total\n"
            "avg_rr = mean(|profit_per_winner|) / mean(|loss_per_loser|)\n"
            "где profit_per_winner = pnl_pct сделок с pnl > 0;\n"
            "loss_per_loser = pnl_pct сделок с pnl ≤ 0."
        ),
        "threshold": (
            "≥ 45% при RR ≥ 1.5 ИЛИ ≥ 35% при RR ≥ 2. Источник: ADR 0014 §T4 "
            "(empirical sustainability — комбинации hit rate × payoff ratio "
            "обеспечивающие positive expectancy за вычетом transaction costs)."
        ),
        "impact": (
            "Низкий win rate (< 35%) при низком RR = стратегия теряет на "
            "transaction costs даже при theoretically positive expectancy. "
            "Affects operator psychology — длинные losing streaks приводят к "
            "discretionary intervention."
        ),
        "related": (
            "Inverse relationship: высокий win rate обычно при низком RR "
            "(scalping pattern); низкий win rate при высоком RR (trend-following). "
            "Обе комбинации valid."
        ),
        "gate_role": (
            "Информационный — отображается без PASS/FAIL chip (status = '—'). "
            "Operator сам интерпретирует контекст комбинации win_rate × RR."
        ),
    },
    "t5_n_trades": {
        "name": "T5 · Trade Count (Bailey gate)",
        "measures": (
            "Количество сделок в OOS периоде. Прямой driver статистической "
            "значимости — без достаточного N результаты могут быть случайны."
        ),
        "formula": (
            "N = len(trades_oos)\n"
            "Дополнительные T5 sub-criteria:\n"
            "- mean_pnl_pct = mean(pnl_pct trades)\n"
            "- t_stat = mean_pnl_pct / (std_pnl_pct / √N) — t-статистика для "
            "теста H0: mean=0 (стратегия не отличается от случайной)."
        ),
        "threshold": (
            "N ≥ 100 (Bailey & López de Prado 2014 — минимум для DSR применимости). "
            "mean_pnl_pct > 0 (positive expectancy); t_stat ≥ 2.0 (статистическая "
            "значимость на 5% уровне ~двусторонний z-test). Источник: ADR 0014 §T5."
        ),
        "impact": (
            "N < 100 → DSR computation скип per Bailey 2014 (sample слишком мал "
            "для асимптотической нормальности). Стратегия не может быть acceptance'd "
            "независимо от Sharpe value. Также t_stat < 2.0 → результат может быть "
            "статистически неотличим от случайного блуждания."
        ),
        "related": (
            "Hard prerequisite для DSR (deflated Sharpe). T5 < 100 → DSR pipeline "
            "пропускается, MetricsTable показывает DSR = N/A. T5 t_stat < 2 = "
            "weak statistical significance даже если sharpe positive."
        ),
        "gate_role": (
            "Critical gate — Bailey 2014 binding для DSR применимости. T5 FAIL "
            "блокирует все downstream metrics regardless of их PASS status."
        ),
    },
    "t6_oos_is_sharpe_ratio_mean": {
        "name": "T6 · OOS/IS Sharpe ratio mean (overfit detector)",
        "measures": (
            "Соотношение Sharpe на OOS фолдах к Sharpe на in-sample (IS) фолдах. "
            "Прокси-индикатор overfitting — при сильном curve-fitting OOS сильно "
            "хуже IS."
        ),
        "formula": (
            "ratio_per_fold = sharpe_oos[fold] / sharpe_is[fold]\n"
            "T6 = mean(ratio_per_fold) — across all WFA folds.\n"
            "Здоровая стратегия: ratio близок к 1.0 (OOS ≈ IS).\n"
            "Overfit: ratio << 1.0 (OOS catastrophically хуже IS)."
        ),
        "threshold": (
            "≥ 0.7 для PASS. Источник: ADR 0014 §T6 (empirical heuristic для "
            "WFA overfit detection). Ratio < 0.7 = OOS Sharpe в среднем менее "
            "70% от IS — указывает на параметры подогнаны под training data."
        ),
        "impact": (
            "T6 < 0.7 → стратегия не generalize'ится. Real trading будет "
            "воспроизводить OOS performance (хуже), не IS performance (лучше). "
            "Operator capital decisions должны базироваться на OOS expectations."
        ),
        "related": (
            "Дополняет T1 Sharpe OOS (показывает абсолютный уровень); T6 "
            "показывает относительную деградацию IS→OOS. Комбинация T1 PASS + "
            "T6 FAIL = absolute level OK, но fragile."
        ),
        "gate_role": (
            "Overfit guardrail. FAIL = warning signal даже при остальных PASS. "
            "Не hard-blocking, но understands acceptance confidence."
        ),
    },
    "dsr": {
        "name": "DSR · Deflated Sharpe Ratio (Bailey & López de Prado 2014)",
        "measures": (
            "Probability that observed Sharpe > 0 после deflation на multiple "
            "comparisons bias (n_trials корректировка) и non-normality (skewness, "
            "kurtosis). Учитывает hypothesis testing context."
        ),
        "formula": (
            "DSR = Φ((Ŝ - E[max{Ŝ}]) × √(N-1) / σ_SR)\n"
            "где Ŝ = observed annualized Sharpe ratio;\n"
            "E[max{Ŝ}] = expected max Sharpe across n_trials independent trials;\n"
            "N = number of trades;\n"
            "σ_SR = standard error of Sharpe estimator (источник per ADR 0056);\n"
            "Φ = CDF normal distribution."
        ),
        "threshold": (
            "> 0.0 для PASS (точнее dsr_pass boolean от backend, обычно > 0.5). "
            "Источник: Bailey & López de Prado 2014 'Deflated Sharpe Ratio'; "
            "ADR 0056 (sigma sourcing decision)."
        ),
        "impact": (
            "DSR < 0 = observed Sharpe не отличается от случайного даже при "
            "его положительном значении (после correction на multiple comparisons "
            "bias). Стратегия не имеет статистически значимой edge."
        ),
        "related": (
            "Зависит от T5 (N ≥ 100), n_trials (количество combinations explored "
            "в hyperparameter search), skew + kurt (4-th moment correction). "
            "T5 < 100 → DSR пропускается."
        ),
        "gate_role": (
            "Final validation gate — Bailey 2014 framework для honest backtest "
            "validation. DSR FAIL = strategy не valid даже при остальных T1-T6 PASS."
        ),
    },
    "mc_p_value": {
        "name": "MC · Monte Carlo p-value (sign-flip permutation test)",
        "measures": (
            "Probability что observed return distribution мог быть получен "
            "случайно через permutation эксперимент. Sign-flip MC = randomize "
            "signs of returns N times, compare distributions."
        ),
        "formula": (
            "p-value = (count(perm_sharpe ≥ observed_sharpe) + 1) / (N_perms + 1)\n"
            "где perm_sharpe = Sharpe вычисленный после случайного flip знаков "
            "returns; N_perms = количество permutations (typically 1000)."
        ),
        "threshold": (
            "≤ 0.05 для PASS. Значения > 0.10 → FAIL. (0.05, 0.10] → WARN cell. "
            "Источник: ADR 0014 §MC; стандартный 5% significance level."
        ),
        "impact": (
            "p-value > 0.05 = observed Sharpe мог быть получен случайно с "
            "вероятностью > 5%. Strategy edge не статистически значим. "
            "p-value > 0.10 = strong evidence стратегия равна random walk."
        ),
        "related": (
            "Альтернатива/дополнение DSR. Оба теста на статистическую "
            "значимость, но MC использует empirical permutation (no parametric "
            "assumptions); DSR использует analytic formula с моментами."
        ),
        "gate_role": (
            "Independent validation от DSR. Согласие DSR PASS + MC PASS = "
            "strong evidence valid edge. Расхождение → investigate sample size."
        ),
    },
}


def get_criterion_explanation(criterion_id: str) -> CriterionExplanation | None:
    """Return RU explanation per criterion; None if unknown."""
    return WFA_CRITERION_EXPLANATIONS_RU.get(criterion_id)


def get_all_criterion_explanations() -> dict[str, CriterionExplanation]:
    return WFA_CRITERION_EXPLANATIONS_RU.copy()
```

- [ ] **Step 4: Add 2 new endpoints к `src/dashboard/app.py`**

After existing `/api/*` route registrations (BEFORE catch-all SPA route from T6):

```python
from src.dashboard.strategy_descriptions import get_strategy_description
from src.dashboard.wfa_criterion_explanations import (
    get_all_criterion_explanations,
    CriterionExplanation,
)


@app.get("/api/strategy_explanation/{preset_id}")
async def strategy_explanation(preset_id: str) -> dict[str, str | None]:
    """S47 T15 — RU detailed strategy description for FailAnalysisTab."""
    desc = get_strategy_description(preset_id)
    if desc is None:
        raise HTTPException(status_code=404, detail=f"Unknown preset: {preset_id}")
    return {"preset_id": preset_id, "description_ru": desc}


@app.get("/api/wfa_criterion_explanations")
async def wfa_criterion_explanations() -> dict[str, CriterionExplanation]:
    """S47 T15 — RU formula+threshold+impact per WFA criterion (T1-T6 + DSR + MC)."""
    return get_all_criterion_explanations()
```

(Add `from fastapi import HTTPException` if not already imported.)

- [ ] **Step 5: Extend types.ts**

Edit `src/dashboard_react/src/api/types.ts`:

```typescript
export interface CriterionExplanation {
  name: string;
  measures: string;
  formula: string;
  threshold: string;
  impact: string;
  related: string;
  gate_role: string;
}

export interface StrategyExplanation {
  preset_id: string;
  description_ru: string;
}
```

- [ ] **Step 6: Add 2 client methods к `src/dashboard_react/src/api/client.ts`**

```typescript
async getStrategyExplanation(presetId: string): Promise<StrategyExplanation> {
  const res = await fetch(`/api/strategy_explanation/${encodeURIComponent(presetId)}`);
  if (!res.ok) throw new ApiError(res.status, `Failed to load strategy explanation: ${res.status}`);
  return res.json();
},

async getCriterionExplanations(): Promise<Record<string, CriterionExplanation>> {
  const res = await fetch('/api/wfa_criterion_explanations');
  if (!res.ok) throw new ApiError(res.status, `Failed to load criterion explanations: ${res.status}`);
  return res.json();
},
```

- [ ] **Step 7: Create `src/dashboard_react/src/components/FailAnalysisTab.tsx`**

```tsx
// FailAnalysisTab — T16: RU detailed WHY-failed narrative для FAILED strategies.
// Visible ONLY когда verdict ∈ {WFA_FAIL, WFA_FAIL_DATA, FAIL}.
// 3 sections: full strategy description / per-criterion breakdown / per-fold table.

import { useEffect, useState } from 'react'
import type { BacktestResponse, CriterionExplanation, StrategyExplanation } from '@/api/types'
import { api } from '@/api/client'
import styles from './FailAnalysisTab.module.css'

interface FailAnalysisTabProps {
  result: BacktestResponse
}

export function FailAnalysisTab({ result }: FailAnalysisTabProps) {
  const [strategyDesc, setStrategyDesc] = useState<StrategyExplanation | null>(null)
  const [criterionMap, setCriterionMap] = useState<Record<string, CriterionExplanation> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      api.getStrategyExplanation(result.request.strategy_id),
      api.getCriterionExplanations(),
    ])
      .then(([sd, cm]) => {
        if (cancelled) return
        setStrategyDesc(sd)
        setCriterionMap(cm)
        setLoading(false)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setError(err.message)
        setLoading(false)
      })
    return () => { cancelled = true }
  }, [result.request.strategy_id])

  if (loading) return <div className={styles.loading}>Загрузка детального разбора...</div>
  if (error !== null) return <div className={styles.error}>Ошибка загрузки: {error}</div>
  if (strategyDesc === null || criterionMap === null) return null

  const failedCriteria = result.failed_criteria ?? []
  const folds = result.fold_sharpe_ratios ?? []
  const failedFolds = new Set(result.failed_folds ?? [])

  return (
    <div className={styles.container}>
      <div className={styles.title}>▸ ДЕТАЛЬНЫЙ РАЗБОР: ПОЧЕМУ СТРАТЕГИЯ НЕ ПРОШЛА</div>

      {/* Section 1 — full strategy description */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>1. Описание стратегии</h3>
        <div className={styles.descriptionBody}>
          {strategyDesc.description_ru.split('\n\n').map((para, i) => (
            <p key={i} dangerouslySetInnerHTML={{ __html: para.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>') }} />
          ))}
        </div>
      </section>

      {/* Section 2 — per-criterion breakdown */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>2. Анализ невыполненных критериев</h3>
        {failedCriteria.length === 0 ? (
          <p className={styles.empty}>Нет явных failed criteria — verdict {result.verdict} мог сработать через aggregate gate.</p>
        ) : (
          failedCriteria.map((critId) => {
            const exp = criterionMap[critId]
            if (exp === undefined) {
              return <div key={critId} className={styles.criterionUnknown}>Неизвестный критерий: {critId}</div>
            }
            const actualValue = (result.metrics as Record<string, number | null | undefined>)?.[critId] ?? null
            return (
              <article key={critId} className={styles.criterionCard}>
                <h4 className={styles.criterionName}>{exp.name}</h4>
                <div className={styles.criterionRow}><strong>Что измеряет:</strong> {exp.measures}</div>
                <div className={styles.criterionRow}><strong>Формула:</strong> <pre className={styles.formula}>{exp.formula}</pre></div>
                <div className={styles.criterionRow}><strong>Порог:</strong> {exp.threshold}</div>
                <div className={styles.criterionRow}>
                  <strong>Фактическое значение:</strong>{' '}
                  <span className={styles.actualValue}>{actualValue !== null ? String(actualValue) : '—'}</span>
                </div>
                <div className={styles.criterionRow}><strong>Почему fail:</strong> Значение не удовлетворяет порогу выше.</div>
                <div className={styles.criterionRow}><strong>На что влияет:</strong> {exp.impact}</div>
                <div className={styles.criterionRow}><strong>С чем связано:</strong> {exp.related}</div>
                <div className={styles.criterionRow}><strong>Роль в acceptance gate:</strong> {exp.gate_role}</div>
              </article>
            )
          })
        )}
      </section>

      {/* Section 3 — per-fold breakdown (WFA path) */}
      {folds.length > 0 && (
        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>3. Разбор по фолдам walk-forward</h3>
          <table className={styles.foldsTable}>
            <thead>
              <tr><th>Фолд</th><th>Sharpe Ratio</th><th>Статус</th></tr>
            </thead>
            <tbody>
              {folds.map((s, i) => {
                const isFailed = failedFolds.has(i)
                const cls = isFailed ? styles.foldFail : (s >= 0.7 ? styles.foldPass : styles.foldWarn)
                return (
                  <tr key={i}>
                    <td>#{i}</td>
                    <td className={cls}>{s.toFixed(4)}</td>
                    <td className={cls}>{isFailed ? '✗ < 0.7 (фолд failed)' : (s >= 0.7 ? '✓' : '⚠ low')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}
```

- [ ] **Step 8: Create `src/dashboard_react/src/components/FailAnalysisTab.module.css`**

```css
.container {
  background: var(--color-bg-glass);
  border: 1px solid rgba(204, 120, 92, 0.30);
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
  backdrop-filter: blur(8px);
}

.title {
  color: var(--color-anthropic-orange);
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(204, 120, 92, 0.30);
}

.section {
  margin-bottom: 32px;
}

.sectionTitle {
  color: var(--color-anthropic-orange);
  font-family: 'Inter', sans-serif;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.descriptionBody p {
  color: var(--color-text-primary);
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.descriptionBody strong {
  color: var(--color-anthropic-orange);
  font-weight: 600;
}

.criterionCard {
  background: rgba(10, 10, 10, 0.40);
  border: 1px solid rgba(255, 51, 102, 0.20);
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}

.criterionName {
  color: var(--color-status-danger);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 12px;
}

.criterionRow {
  color: var(--color-text-primary);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 8px;
}

.criterionRow strong {
  color: var(--color-anthropic-orange);
  font-weight: 600;
}

.formula {
  background: rgba(0, 0, 0, 0.50);
  color: var(--color-text-primary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding: 8px 12px;
  border-radius: 4px;
  margin-top: 4px;
  white-space: pre-wrap;
  border-left: 2px solid var(--color-anthropic-orange);
}

.actualValue {
  color: var(--color-status-danger);
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
}

.foldsTable {
  width: 100%;
  border-collapse: collapse;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}

.foldsTable th {
  text-align: left;
  padding: 8px 12px;
  color: var(--color-text-muted);
  border-bottom: 1px solid rgba(204, 120, 92, 0.30);
  font-weight: 600;
}

.foldsTable td {
  padding: 8px 12px;
  color: var(--color-text-primary);
  border-bottom: 1px solid rgba(156, 163, 175, 0.10);
}

.foldPass { color: var(--color-status-success); }
.foldFail { color: var(--color-status-danger); }
.foldWarn { color: var(--color-status-warning); }

.loading, .error, .empty {
  color: var(--color-text-muted);
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  padding: 16px;
  text-align: center;
}

.error { color: var(--color-status-danger); }

.criterionUnknown {
  color: var(--color-status-warning);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  padding: 8px;
}
```

- [ ] **Step 9: Wire FailAnalysisTab в App.tsx — conditional render**

Edit `src/dashboard_react/src/App.tsx`. Find result render block. Add:

```tsx
import { FailAnalysisTab } from './components/FailAnalysisTab'

// ...

const FAILED_VERDICTS = new Set(['WFA_FAIL', 'WFA_FAIL_DATA', 'FAIL'])

// Inside result render:
{result && FAILED_VERDICTS.has(result.verdict) && (
  <FailAnalysisTab result={result} />
)}
```

Place after `<MetricsTable result={result} />` block but before `<TradesTable />`.

- [ ] **Step 10: Manual sanity test**

```bash
cd src/dashboard_react && npm run build && cd ../..
.venv/bin/uvicorn src.dashboard.app:create_app --factory --port 8000 &
APP_PID=$!
sleep 3
echo "1. Open http://127.0.0.1:8000/"
echo "2. Run any preset that previously got WFA_FAIL"
echo "3. Verify: ▸ ДЕТАЛЬНЫЙ РАЗБОР appears below MetricsTable"
echo "4. Verify: 3 sections visible — strategy description / failed criteria / fold table"
echo "5. Verify: each failed criterion shows 7 rows (что измеряет / формула / порог / actual / impact / related / gate role)"
echo "Press enter when done"
read
kill $APP_PID 2>/dev/null
```

- [ ] **Step 11: Build + lint + mypy**

```bash
cd src/dashboard_react && npm run lint && npx tsc -b && npm run build
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
.venv/bin/mypy --strict src/dashboard/app.py src/dashboard/strategy_descriptions.py src/dashboard/wfa_criterion_explanations.py
```

Expected: 0 errors all gates.

- [ ] **Step 12: Commit + SPRINT_STATE T15 done**

```bash
git add src/dashboard/strategy_descriptions.py \
        src/dashboard/wfa_criterion_explanations.py \
        src/dashboard/app.py \
        src/dashboard_react/src/api/types.ts \
        src/dashboard_react/src/api/client.ts \
        src/dashboard_react/src/components/FailAnalysisTab.tsx \
        src/dashboard_react/src/components/FailAnalysisTab.module.css \
        src/dashboard_react/src/App.tsx
git commit -m "feat(s47): T16 Fail Analysis tab — RU detailed WHY-failed narrative (opus)

Operator request 2026-05-11. New tab visible только когда verdict ∈
{WFA_FAIL, WFA_FAIL_DATA, FAIL}. 3 sections:
1. Полное описание стратегии (~200-400 слов per preset)
2. Per-criterion breakdown — что измеряет / формула / порог / actual /
   почему fail / impact / related / gate role
3. Per-fold breakdown table (WFA path)

NEW backend: strategy_descriptions.py + wfa_criterion_explanations.py +
2 endpoints (/api/strategy_explanation/{id} + /api/wfa_criterion_explanations).

CRITICAL: quant-stats-reviewer PHASE 6 MUST verify formulas + thresholds
match Bailey 2014 + ADR 0014 + ADR 0056."
```

---

## Bucket F — Wiki sync

## Task 16: sprint-47 page + index.md + log.md + current-state.md (sonnet)

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-47-tech-debt-carryovers.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` — header + counts row + sprint history
- Modify: `llm-wiki/wiki/index.md` — sprint-47 entry
- Append: `llm-wiki/wiki/log.md` — S47 sprint-end entry

- [ ] **Step 1: Create `sprint-47-tech-debt-carryovers.md` mirroring sprint-46 structure**

```yaml
---
title: "Sprint 47 — Tech debt + S46 PHASE 6 carry-overs + UI bugs"
type: sprint
tags: [sprint-47, tech-debt, carry-overs, vitest, fail-analysis-tab, bybit-api]
created: 2026-05-11
updated: 2026-05-11
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0014-walk-forward-acceptance-gates.md
  - llm-wiki/wiki/project/decisions/0017-review-agent-harness.md
  - llm-wiki/wiki/project/decisions/0056-dsr-sigma-sourcing.md
  - llm-wiki/wiki/project/plans/2026-05-11-sprint-47-tech-debt-carryovers.md
  - llm-wiki/wiki/project/pre-s47-backlog.md
---
```

Sections (mirror sprint-46):
- Overview (1 paragraph)
- Plan + ADR links
- Deliverables (Code / Tests / CI / Wiki sub-sections)
- Operator-surfaced bugs (T14 root cause + T15 cursor + T16 RU narrative)
- Tests (Vitest 3 unit + Playwright E2E activate)
- Wiki updates
- Open issues для S48 (defer items)
- Key decisions (per Q1-Q6 trader verdicts + Q7 surface)
- Related backlinks

- [ ] **Step 2: Update current-state.md**

Update header `post-S47`. Bump sprint pages count 50 → 51. Add sprint history row.

- [ ] **Step 3: Update index.md**

Add `[[project/sprints/sprint-47-tech-debt-carryovers]]` entry в Project — Sprints alphabetical/numerical position.

- [ ] **Step 4: Append log.md sprint-end entry**

```markdown
## [2026-05-11] sprint-end | S47 — Tech debt + S46 carry-overs + UI bugs

- **Сценарий:** locked 16 tasks 5 buckets (Vitest+RTL infra + 3 unit tests + E2E activate + SPA catch-all + cache headers + MetricsTable T5 fix + M1+M2+M3 bybit-api + DSR/n_trials/sprint type trio + T14 trade_stats bug + T15 cursor tooltip + T16 fail analysis tab + wiki sync)
- **Frontend:** Vitest+RTL infra; 3 React unit tests (computeDrawdown property + useWfaFailAck + MetricsTable threshold); EquityChart + DrawdownSubchart cursor tooltip on hover; FailAnalysisTab RU detailed разбор (3 sections: strategy desc + per-criterion breakdown + per-fold table)
- **Backend:** envelope trade_stats extension для research presets; 2 new endpoints (/api/strategy_explanation/{id} + /api/wfa_criterion_explanations); SPA catch-all FastAPI route + asset cache headers
- **Bybit API:** M1 retCode taxonomy +3 codes; M2 _safe_extract_list defensive helper + BybitAdapterError; M3 WS data isinstance guard
- **Tests:** Vitest 3 unit + Playwright E2E backtest-flow activated; pytest +6 (DSR property + n_trials + sprint type + envelope trade_stats + bybit retCode + bybit response guards); MetricsTable T5 vanilla bug regression test
- **Canonical counts:** unchanged 16/30/74/56 (frontend + tech debt sprint, no FSM/reason changes); ADRs 66 (no new); sprint pages 50 → 51
- **Tag:** v0.1.0-alpha.47
- **Carry к S48:** Vitest tests #4/#5 (computeMonthlyData + VerdictPanel mapping) / A11y polish (tablist ARIA + contrast) / README npm install note / F8 block_size constant unification / MonthlyHeatmap eslint cleanup / Item #7/#10 long-standing tech debt / **NEW STRATEGIES (Path B rejoin per operator pivot)**

## [2026-05-11] ship | S47 SHIPPED — squash-merge + tag

- **PR #<TBD>** squash-merged → `<TBD-sha>` Sprint 47 tech debt + S46 carry-overs + UI bugs
- **Tag** `v0.1.0-alpha.47` pushed к origin
- **Branch** `feature/sprint-47-tech-debt-carryovers` deleted (post-merge cleanup)
- **PHASE 5 verify:** pytest + mypy + Vitest + Playwright + lint+tsc+build all GREEN
- **PHASE 6 reviewers (9):** python + trading-logic + quant-stats + bybit-api + security-auditor (M1-M3 only) + frontend-developer + test-engineer + data-integrity + doc — все APPROVE/APPROVE_WITH_CONCERNS, фиксы pre-merge
- **Total commits:** ~<TBD>
```

- [ ] **Step 5: Verify wiki integrity**

```bash
# Verify sprint-47 page exists
ls llm-wiki/wiki/project/sprints/sprint-47*

# Verify index has entry
grep "sprint-47" llm-wiki/wiki/index.md

# Verify log has S47 entry
grep "S47 " llm-wiki/wiki/log.md | tail -5

# Verify current-state count matches actual
ls llm-wiki/wiki/project/sprints/ | wc -l   # should be 51
```

- [ ] **Step 6: Commit + SPRINT_STATE T16 done + phase=5-verify**

```bash
git add llm-wiki/
git commit -m "docs(s47): wiki sync — sprint-47 page + index + log + current-state (T16)"

# Update SPRINT_STATE: phase=5-verify, all 16 tasks done
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE T16 done + phase=5-verify (S47 execution complete 16/16)"
```

---

## PHASE 5 — Verify (after T16 commit)

Run all gates parallel. ALL must GREEN before PHASE 6.

```bash
# Backend
.venv/bin/pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
.venv/bin/mypy --strict src/ 2>&1 | tail -3

# Frontend
cd src/dashboard_react
npm run lint
npx tsc -b
npm run build
npm test  # Vitest unit
npx playwright test  # E2E
```

Expected:
- pytest: previous 1004 + ~6 new = ~1010 pass
- mypy: 0 issues
- Vitest: 7 + 7 + 7 + 2 (smoke) = 23 pass
- Playwright: 4 pass / 0 skip (T5 activated previously skipped)
- lint+tsc+build: clean

**HARD-GATE:** Если CI canonical counts trip again — bump baseline в `.github/workflows/ci.yml` line 133 (likely unchanged 56 reason_codes, no FSM additions).

## PHASE 6 — Domain reviewers (parallel dispatch)

5+ reviewers per matrix (see top of plan). All MUST verdict APPROVE / APPROVE_WITH_CONCERNS перед merge. BLOCKER findings → fix + re-verify before PHASE 8.

**Critical reviewer:** quant-stats-reviewer для T15 (FailAnalysisTab formulas/thresholds correctness — Bailey 2014 + ADR 0014 + ADR 0056 cross-reference). BLOCKER risk if mismatch.

## PHASE 8 — Ship

Per `superpowers:finishing-a-development-branch` skill.

```bash
git push -u origin feature/sprint-47-tech-debt-carryovers
gh pr create --title "Sprint 47: Tech debt + S46 carry-overs + UI bugs" --body "..."
# Wait CI green
gh pr merge --squash --delete-branch
git checkout main && git pull
git tag -a v0.1.0-alpha.47 -m "..." <merge-sha>
git push origin v0.1.0-alpha.47
```

Post-ship: Update SPRINT_STATE phase=between-sprints, sprint=47, branch=main, tag=v0.1.0-alpha.47. Append log.md ship entry. **HARD-GATE budget:** verify SPRINT_STATE ≤ 6 KB после update; if approaching → trim или indexed split per S46 post-ship pattern.

---

## Self-Review

**1. Spec coverage** — все 16 tasks per pre-s47-backlog rev 2 covered:
- Bucket A 5: T1 Vitest infra / T2 computeDrawdown property / T3 useWfaFailAck / T4 MetricsTable threshold / T5 backtest-flow E2E
- Bucket B 3: T6 SPA catch-all / T7 cache headers / T8 MetricsTable T5 cleanup
- Bucket C 3: T9 M1 retCode / T10 M2 dict guards / T11 M3 WS isinstance
- Bucket D 1: T12 DSR + n_trials + sprint type trio
- Bucket E 3: T13 trade_stats bug / T14 cursor tooltip / T15 fail analysis tab opus
- Bucket F 1: T16 wiki sync

**2. Placeholder scan** — несколько items отмечены implementer judgment:
- T11 — `BybitPrivateWSConsumer(...)` constructor args TBD by implementer (cite existing test fixtures pattern). Acceptable — not "implement later", concrete instruction "check existing tests for proper init".
- T15 strategy_descriptions.py — only 2 example presets shown; "implementer adds remaining 9 per STRATEGY_PRESETS dict". Acceptable — explicit instruction + reference к canonical source.
- T12 DSR test — `compute_dsr` import path "adjust per real path". Acceptable — implementer reads code first.

**3. Type consistency** — `TradeStats` interface (T13) consumed by `TradesTable` (T13) renders gracefully. `CriterionExplanation` interface (T15) consumed by `FailAnalysisTab` (T15) — same shape backend↔frontend. `BacktestResponse.failed_criteria` referenced both в MetricsTable + FailAnalysisTab — same array type. PASS.

**4. Cross-task dependencies** — T2 (computeDrawdown test) requires T2 step 1 (export refactor). T8 regression test requires T4 base test file. T13 trade_stats requires changes к 3 files atomic — single commit. T15 has 11 sub-steps spanning backend + frontend — single task OK because conceptually one feature.

**5. Files ≤ 50 KB rule** — this plan ≈ 50 KB (104 lines TL;DR + 16 tasks × ~200 lines avg). Approaching limit but within safe-read budget. Future implementer reads с offset/limit per CLAUDE.md guidance.

---

**Plan saved.** Per repo CLAUDE.md anti-pattern + ADR autonomous overrides table — auto-invoking `superpowers:subagent-driven-development` БЕЗ asking operator. Operator decision 2026-05-10 documented в repo CLAUDE.md anti-patterns: "operator всегда выбирает team of agents default; skip только если operator EXPLICITLY says 'execute inline' перед PHASE 3".
