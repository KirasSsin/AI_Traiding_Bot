import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MetricsTable } from '../MetricsTable'
import type { BacktestResponse } from '@/api/types'

// Минимальная база — поля обязательные для BacktestResponse
const baseResponse = {
  run_id: 'test-run',
  cached: false,
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
  failed_folds: [],
  trades_dump: [],
  equity_curve: { timestamps: [], equity_pct: [] },
  bars_per_year: 8766,
  acceptance_gate: null,
  trade_stats: {} as unknown as BacktestResponse['trade_stats'],
  wfa_params: null,
  wfa_total_bars: 0,
  runner: 'test',
} as const

// ─── RAW path ──────────────────────────────────────────────────────────────

describe('MetricsTable — RAW path', () => {
  it('renders Total PnL + Sharpe + Trade count + Win rate (4 rows)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'RAW',
      total_pnl_pct: 12.5,
      sharpe: 1.42,
      n_trades: 50,
      win_rate: 0.58,
      metrics: { total_pnl_pct: 12.5, sharpe: 1.42, n_trades: 50, win_rate: 0.58 },
      fold_sharpe_ratios: [],
      dsr: null,
      dsr_pass: null,
      mc_p_value: null,
    } as unknown as BacktestResponse
    render(<MetricsTable result={r} />)

    // Все 4 строки RAW таблицы присутствуют
    expect(screen.getByText(/Total PnL/i)).toBeInTheDocument()
    expect(screen.getByText(/Sharpe \(annualized\)/i)).toBeInTheDocument()
    expect(screen.getByText(/Trade count \(n\)/i)).toBeInTheDocument()
    expect(screen.getByText(/Win rate/i)).toBeInTheDocument()

    // T1-T6 / DSR / MC НЕ должны отображаться в RAW path
    expect(screen.queryByText(/T5 · /)).not.toBeInTheDocument()
    expect(screen.queryByText(/DSR · /)).not.toBeInTheDocument()
    expect(screen.queryByText(/MC · /)).not.toBeInTheDocument()
  })
})

// ─── WFA path — ADR 0052 thresholds (S34 amendment) ──────────────────────

describe('MetricsTable — WFA path ADR 0052 thresholds (S34 amendment, T5_FLOOR=50)', () => {
  it('T5 trade count: n=49 → FAIL (ADR 0052 threshold ≥ 50, exclusive lower bound)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: { t5_n_trades: 49, t1_sharpe_oos: 1.2, t3_max_drawdown: 0.15 },
      fold_sharpe_ratios: [1.1, 1.0, 0.9],
      dsr: 0.5,
      dsr_pass: true,
      mc_p_value: 0.04,
      n_trades: 49,
      sharpe: 1.2,
      win_rate: 0.5,
      total_pnl_pct: 5.0,
    } as unknown as BacktestResponse
    render(<MetricsTable result={r} />)

    // Строка T5 · Trade count — ищем bold заголовок ячейки
    const t5Label = screen.getByText(/T5 · Trade count \(n\)/i)
    const t5Row = t5Label.closest('tr')
    expect(t5Row).toBeTruthy()
    expect(t5Row!.textContent).toMatch(/49/)
    expect(t5Row!.textContent).toMatch(/FAIL/i)
  })

  it('T5 trade count: n=50 → PASS (ADR 0052 threshold inclusive at 50)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_PASS',
      metrics: { t5_n_trades: 50 },
      fold_sharpe_ratios: [],
      dsr: 0.5,
      dsr_pass: true,
      mc_p_value: 0.04,
      n_trades: 50,
      sharpe: 1.2,
      win_rate: 0.5,
      total_pnl_pct: 5.0,
    } as unknown as BacktestResponse
    render(<MetricsTable result={r} />)

    const t5Label = screen.getByText(/T5 · Trade count \(n\)/i)
    const t5Row = t5Label.closest('tr')
    expect(t5Row!.textContent).toMatch(/50/)
    expect(t5Row!.textContent).toMatch(/PASS/i)
  })

  it('T1 Sharpe OOS > 3 → OVERFIT? badge в informational row (not PASS/FAIL chip)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: { t1_sharpe_oos: 4.5 },
      fold_sharpe_ratios: [],
      dsr: 0.5,
      dsr_pass: true,
      mc_p_value: 0.04,
      n_trades: 150,
      sharpe: 4.5,
      win_rate: 0.6,
      total_pnl_pct: 20.0,
    } as unknown as BacktestResponse
    render(<MetricsTable result={r} />)

    // OVERFIT? badge должен быть в DOM (inline badge в T1 informational row)
    expect(screen.getByText(/OVERFIT\?/)).toBeInTheDocument()
    // T1 row — status cell должен быть "—", не PASS/FAIL
    const t1Row = screen.getByText(/T1 · Sharpe OOS/i).closest('tr')
    expect(t1Row!.textContent).toMatch(/—/)
  })

  it('T3 Max Drawdown ≥ 25% → informational row, status "—" (not FAIL chip)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: { t3_max_drawdown: 0.30 },
      fold_sharpe_ratios: [],
      dsr: 0.5,
      dsr_pass: true,
      mc_p_value: 0.04,
      n_trades: 150,
      sharpe: 1.2,
      win_rate: 0.5,
      total_pnl_pct: 5.0,
    } as unknown as BacktestResponse
    render(<MetricsTable result={r} />)

    // T3 — informational row: value cell shows percentage, status cell = "—"
    const t3Row = screen.getByText(/T3 · Max Drawdown/i).closest('tr')
    expect(t3Row!.textContent).toMatch(/—/)
    // T3 is now informational — should NOT show FAIL text in status cell
    // (row contains "—" as status, not "FAIL")
    const cells = t3Row!.querySelectorAll('td')
    // 4th cell (STATUS) must be "—"
    expect(cells[3]?.textContent).toBe('—')
  })

  it('MC p-value > 0.10 → FAIL; ≤ 0.05 → PASS', () => {
    // FAIL case: mc_p_value = 0.15 (> 0.10)
    const fail: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: {},
      fold_sharpe_ratios: [],
      dsr: 0.5,
      dsr_pass: true,
      mc_p_value: 0.15,
      n_trades: 150,
      sharpe: 1.2,
      win_rate: 0.5,
      total_pnl_pct: 5.0,
    } as unknown as BacktestResponse
    const { unmount } = render(<MetricsTable result={fail} />)
    // Строка MC · p-value (sign-flip)
    const mcRowFail = screen.getByText(/MC · p-value/i).closest('tr')
    // Статус FAIL в последней ячейке строки
    expect(mcRowFail!.textContent).toMatch(/FAIL/i)
    unmount()

    // PASS case: mc_p_value = 0.04 (≤ 0.05)
    const pass: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_PASS',
      metrics: {},
      fold_sharpe_ratios: [],
      dsr: 0.5,
      dsr_pass: true,
      mc_p_value: 0.04,
      n_trades: 150,
      sharpe: 1.2,
      win_rate: 0.5,
      total_pnl_pct: 5.0,
    } as unknown as BacktestResponse
    render(<MetricsTable result={pass} />)
    const mcRowPass = screen.getByText(/MC · p-value/i).closest('tr')
    expect(mcRowPass!.textContent).toMatch(/PASS/i)
  })

  it('T5 trade count: undefined → FAIL (S47 T8 fix; vanilla bug — used to render PASS)', () => {
    const r = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: {},  // t5_n_trades missing entirely
      dsr: 0.5, dsr_pass: true, mc_p_value: 0.04,
    } as unknown as BacktestResponse
    render(<MetricsTable result={r} />)
    const t5Row = screen.getByText(/T5 · Trade count \(n\)/i).closest('tr')
    expect(t5Row!.textContent).toMatch(/—/)
    expect(t5Row!.textContent).toMatch(/FAIL/i)  // NOT PASS (vanilla bug fixed)
  })
})

// ─── S48 T10 — Bug D: GATE-BLOCKING vs INFORMATIONAL sections ────────────

describe('MetricsTable — S48 T10 Bug D: section divider + grayed informational rows', () => {
  it('Bug D: sections GATE-BLOCKING + INFORMATIONAL + Glossary link present', () => {
    const r = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: { t5_n_trades: 80, t1_sharpe_oos: 0.5, t3_max_drawdown: 0.15 },
      fold_sharpe_ratios: [],
      dsr: 0.5,
      dsr_pass: false,
      mc_p_value: 0.06,
    } as unknown as BacktestResponse
    render(<MetricsTable result={r} />)

    expect(screen.getByText(/GATE-BLOCKING/)).toBeInTheDocument()
    expect(screen.getByText(/INFORMATIONAL/)).toBeInTheDocument()
    expect(screen.getByText(/Glossary/)).toBeInTheDocument()

    // T1 row — status должен быть "—", не PASS/FAIL chip (informational)
    const t1Row = screen.getByText(/T1 · Sharpe OOS/i).closest('tr')
    expect(t1Row).toBeTruthy()
    expect(t1Row!.textContent).toMatch(/—/)
  })

  it('Bug D: T5 gate-blocking row has PASS/FAIL chip (NOT in informational section)', () => {
    const r = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: { t5_n_trades: 30 },  // < 50 → FAIL
      fold_sharpe_ratios: [],
      dsr: 0.5,
      dsr_pass: false,
      mc_p_value: 0.06,
    } as unknown as BacktestResponse
    render(<MetricsTable result={r} />)

    // T5 gate-blocking row — FAIL chip должен быть
    const t5Row = screen.getByText(/T5 · Trade count/i).closest('tr')
    expect(t5Row!.textContent).toMatch(/FAIL/i)

    // DSR и MC — также gate-blocking, показывают FAIL chip
    const dsrRow = screen.getByText(/DSR · Deflated Sharpe/i).closest('tr')
    expect(dsrRow!.textContent).toMatch(/FAIL/i)

    const mcRow = screen.getByText(/MC · p-value/i).closest('tr')
    expect(mcRow!.textContent).toMatch(/FAIL/i)
  })
})
