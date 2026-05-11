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

// ─── WFA path — Bailey 2014 thresholds (per ADR 0014) ─────────────────────

describe('MetricsTable — WFA path Bailey 2014 thresholds (per ADR 0014)', () => {
  it('T5 trade count: n=99 → FAIL (Bailey threshold ≥ 100, exclusive lower bound)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_FAIL',
      metrics: { t5_n_trades: 99, t1_sharpe_oos: 1.2, t3_max_drawdown: 0.15 },
      fold_sharpe_ratios: [1.1, 1.0, 0.9],
      dsr: 0.5,
      dsr_pass: true,
      mc_p_value: 0.04,
      n_trades: 99,
      sharpe: 1.2,
      win_rate: 0.5,
      total_pnl_pct: 5.0,
    } as unknown as BacktestResponse
    render(<MetricsTable result={r} />)

    // Строка T5 · Trade count — ищем bold заголовок ячейки
    const t5Label = screen.getByText(/T5 · Trade count \(n\)/i)
    const t5Row = t5Label.closest('tr')
    expect(t5Row).toBeTruthy()
    expect(t5Row!.textContent).toMatch(/99/)
    expect(t5Row!.textContent).toMatch(/FAIL/i)
  })

  it('T5 trade count: n=100 → PASS (Bailey threshold inclusive at 100)', () => {
    const r: BacktestResponse = {
      ...baseResponse,
      verdict: 'WFA_PASS',
      metrics: { t5_n_trades: 100 },
      fold_sharpe_ratios: [],
      dsr: 0.5,
      dsr_pass: true,
      mc_p_value: 0.04,
      n_trades: 100,
      sharpe: 1.2,
      win_rate: 0.5,
      total_pnl_pct: 5.0,
    } as unknown as BacktestResponse
    render(<MetricsTable result={r} />)

    const t5Label = screen.getByText(/T5 · Trade count \(n\)/i)
    const t5Row = t5Label.closest('tr')
    expect(t5Row!.textContent).toMatch(/100/)
    expect(t5Row!.textContent).toMatch(/PASS/i)
  })

  it('T1 Sharpe OOS > 3 → OVERFIT? warning (overfit detector)', () => {
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

    // Статус "OVERFIT?" должен быть в DOM (компонент рендерит 'OVERFIT?')
    expect(screen.getByText(/OVERFIT\?/)).toBeInTheDocument()
  })

  it('T3 Max Drawdown ≥ 25% → FAIL', () => {
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

    const t3Row = screen.getByText(/T3 · Max Drawdown/i).closest('tr')
    expect(t3Row!.textContent).toMatch(/FAIL/i)
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
})
