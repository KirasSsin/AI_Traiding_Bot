import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// ── Mock the API client ───────────────────────────────────────────────────────
vi.mock('@/api/client', () => ({
  ApiError: class ApiError extends Error {
    detail: string
    constructor(detail: string) {
      super(detail)
      this.detail = detail
    }
  },
  api: {
    getStrategies: vi.fn(),
    getIntervals: vi.fn(),
    getDataAvailability: vi.fn(),
    getKronosCoverage: vi.fn(),
    runBacktest: vi.fn(),
  },
}))

// ── Mock hooks (keep ConfigureBacktest's own logic under test) ────────────────
vi.mock('@/hooks/useStrategyInfo', () => ({ useStrategyInfo: () => ({ info: null }) }))
vi.mock('@/hooks/useStrategyContext', () => ({
  useStrategyContext: () => ({ setCurrentStrategy: vi.fn() }),
}))
vi.mock('@/hooks/useBybitBalance', () => ({
  useBybitBalance: () => ({ balance: 10000, source: 'fallback', loading: false, error: null }),
}))
vi.mock('@/components/shared/BalanceBadge', () => ({ BalanceBadge: () => null }))

import { api } from '@/api/client'
import { ConfigureBacktest } from '../ConfigureBacktest'

const COVERAGE = [
  { symbol: 'BTCUSDT', timeframe: '5m', startIso: '2026-01-01', endIso: '2026-04-26', nEntries: 33467 },
  { symbol: 'BTCUSDT', timeframe: '1h', startIso: '2026-02-02', endIso: '2026-04-26', nEntries: 2000 },
]

beforeEach(() => {
  vi.mocked(api.getStrategies).mockResolvedValue({
    kronos: { label: 'Kronos ML', optgroup: 'ML / Прогноз' },
  } as never)
  vi.mocked(api.getIntervals).mockResolvedValue([
    { id: '5', label: '5 minutes' },
    { id: '15', label: '15 minutes' },
    { id: '60', label: '1 hour' },
  ] as never)
  vi.mocked(api.getDataAvailability).mockResolvedValue({
    BTCUSDT: {
      '5': { bars: 1, start: '2023-01-01', end: '2026-04-26' },
      '15': { bars: 1, start: '2023-01-01', end: '2026-04-26' },
      '60': { bars: 1, start: '2023-01-01', end: '2026-04-26' },
    },
  } as never)
  vi.mocked(api.getKronosCoverage).mockResolvedValue(COVERAGE as never)
})

describe('ConfigureBacktest — Kronos coverage (S54 T3)', () => {
  it('auto-fills START/END from cached coverage and enables EXECUTE for a cached timeframe (5m)', async () => {
    render(<ConfigureBacktest onResult={vi.fn()} />)
    // First interval = "5" (5m) → cached → dates auto-filled.
    await waitFor(() => {
      const start = screen.getByDisplayValue('2026-01-01')
      expect(start).toBeTruthy()
    })
    expect(screen.getByDisplayValue('2026-04-26')).toBeTruthy()
    const execute = screen.getByRole('button', { name: /EXECUTE/i })
    expect(execute).not.toBeDisabled()
  })

  it('blocks EXECUTE and shows "не построен" for an uncached timeframe (15m)', async () => {
    render(<ConfigureBacktest onResult={vi.fn()} />)
    await waitFor(() => expect(screen.getByDisplayValue('2026-01-01')).toBeTruthy())

    // Switch timeframe to 15m (not in coverage).
    const tfSelect = screen.getByDisplayValue('5 minutes')
    fireEvent.change(tfSelect, { target: { value: '15' } })

    await waitFor(() => {
      expect(screen.getByText(/не построен/i)).toBeTruthy()
    })
    const execute = screen.getByRole('button', { name: /EXECUTE/i })
    expect(execute).toBeDisabled()
  })
})
