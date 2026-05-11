// HistoryTab RTL tests — S48 T14
// Covers: accordion expand (T13), ESC close, RU summary template branches.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { HistoryTab } from '../HistoryTab'

import * as apiClient from '@/api/client'

vi.mock('@/api/client', () => ({
  api: {
    getRuns: vi.fn().mockResolvedValue([
      {
        run_id: 'run1',
        cached: false,
        request: {
          strategy_id: 'ema_crossover_s13',
          strategy_label: 'EMA',
          symbol: 'BTC',
          interval: '60',
          interval_label: '1h',
          start: '2023-01-01',
          end: '2023-12-31',
        },
        verdict: 'WFA_FAIL',
        metrics: { t1_sharpe_oos: 0.5, t5_n_trades: 80 },
        dsr: null,
        mc_p_value: null,
        total_pnl_pct: -5.0,
        n_trades: 80,
        sharpe: 0.5,
        win_rate: 0.4,
      },
    ]),
    getRun: vi.fn().mockResolvedValue({
      run_id: 'run1',
      cached: false,
      verdict: 'WFA_FAIL',
      total_pnl_pct: -5.0,
      n_trades: 80,
      sharpe: 0.5,
      win_rate: 0.4,
      failed_criteria: ['t5_floor'],
      request: {
        strategy_id: 'ema_crossover_s13',
        strategy_label: 'EMA',
        symbol: 'BTC',
        interval: '60',
        interval_label: '1h',
        start: '2023-01-01',
        end: '2023-12-31',
      },
      trade_stats: {
        win_rate: 0.4,
        n_trades: 80,
        profit_factor: 0.85,
        initial_balance_quote: 10000,
        final_balance_quote: 9500,
      },
      warnings: [],
      metrics: { t1_sharpe_oos: 0.5, t5_n_trades: 80 },
      equity_curve: { timestamps: [], equity_pct: [] },
      bars_per_year: 8766,
      acceptance_gate: null,
      dsr: null,
      dsr_pass: null,
      mc_p_value: null,
      wfa_params: null,
      wfa_total_bars: 0,
      fold_sharpe_ratios: [],
      failed_folds: [],
      trades_dump: [],
      runner: 'test',
    }),
  },
}))

// ─── tests ───────────────────────────────────────────────────────────────────

describe('HistoryTab — accordion expand (S48 T13)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.api.getRuns).mockResolvedValue([
      {
        run_id: 'run1',
        cached: false,
        request: {
          strategy_id: 'ema_crossover_s13',
          strategy_label: 'EMA',
          symbol: 'BTC',
          interval: '60',
          interval_label: '1h',
          start: '2023-01-01',
          end: '2023-12-31',
        },
        verdict: 'WFA_FAIL' as const,
        metrics: { t1_sharpe_oos: 0.5, t5_n_trades: 80 },
        dsr: null,
        mc_p_value: null,
        total_pnl_pct: -5.0,
        n_trades: 80,
        sharpe: 0.5,
        win_rate: 0.4,
      } as import('@/api/types').RunSummary,
    ])
    vi.mocked(apiClient.api.getRun).mockResolvedValue({
      run_id: 'run1',
      cached: false,
      verdict: 'WFA_FAIL' as const,
      total_pnl_pct: -5.0,
      n_trades: 80,
      sharpe: 0.5,
      win_rate: 0.4,
      failed_criteria: ['t5_floor'],
      request: {
        strategy_id: 'ema_crossover_s13',
        strategy_label: 'EMA',
        symbol: 'BTC',
        interval: '60',
        interval_label: '1h',
        start: '2023-01-01',
        end: '2023-12-31',
      },
      trade_stats: {
        win_rate: 0.4,
        n_trades: 80,
        profit_factor: 0.85,
        initial_balance_quote: 10000,
        final_balance_quote: 9500,
      } as import('@/api/types').BacktestResponse['trade_stats'],
      warnings: [],
      metrics: { t1_sharpe_oos: 0.5, t5_n_trades: 80 },
      equity_curve: { timestamps: [], equity_pct: [] },
      bars_per_year: 8766,
      acceptance_gate: null,
      dsr: null,
      dsr_pass: null,
      mc_p_value: null,
      wfa_params: null,
      wfa_total_bars: 0,
      fold_sharpe_ratios: [],
      failed_folds: [],
      trades_dump: [],
      runner: 'test',
    } as import('@/api/types').BacktestResponse)
  })

  it('row click expands details panel', async () => {
    render(<HistoryTab />)
    await waitFor(() => expect(screen.getByText('EMA')).toBeInTheDocument())

    // Click the row
    fireEvent.click(screen.getByText('EMA').closest('tr')!)

    await waitFor(() => expect(screen.getByText('Начальный баланс')).toBeInTheDocument())
    expect(screen.getByText('Итоговый баланс')).toBeInTheDocument()
    expect(screen.getByText('Win rate')).toBeInTheDocument()
  })

  it('ESC key closes expanded row', async () => {
    render(<HistoryTab />)
    await waitFor(() => expect(screen.getByText('EMA')).toBeInTheDocument())

    fireEvent.click(screen.getByText('EMA').closest('tr')!)
    await waitFor(() => expect(screen.getByText('Начальный баланс')).toBeInTheDocument())

    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByText('Начальный баланс')).not.toBeInTheDocument())
  })

  it('RU summary text: WFA_FAIL branch says "не прошла WFA discipline"', async () => {
    render(<HistoryTab />)
    await waitFor(() => expect(screen.getByText('EMA')).toBeInTheDocument())

    fireEvent.click(screen.getByText('EMA').closest('tr')!)

    // Exact substring from renderSummary WFA_FAIL branch
    await waitFor(() =>
      expect(screen.getByText(/не прошла WFA discipline/)).toBeInTheDocument()
    )
  })
})
