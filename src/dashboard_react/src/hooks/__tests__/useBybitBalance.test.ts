import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useBybitBalance } from '../useBybitBalance'

vi.mock('@/api/client', () => ({
  api: { getBalance: vi.fn() },
}))

import { api } from '@/api/client'
const getBalanceMock = vi.mocked(api.getBalance)

describe('useBybitBalance (S48 T20)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('loads then populates balance + source on success', async () => {
    getBalanceMock.mockResolvedValueOnce({
      source: 'bybit_v5',
      total_equity_usdt: 12345.67,
      fetched_at_iso: '2026-05-11T00:00:00Z',
    })
    const { result } = renderHook(() => useBybitBalance())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.balance).toBe(12345.67)
    expect(result.current.source).toBe('bybit_v5')
    expect(result.current.error).toBeNull()
  })

  it('falls back to cached localStorage on API failure', async () => {
    localStorage.setItem('bybit_balance_cache_v1', JSON.stringify({
      source: 'bybit_v5',
      total_equity_usdt: 9999,
      fetched_at_iso: '2026-05-10T00:00:00Z',
    }))
    getBalanceMock.mockRejectedValueOnce(new Error('Network'))
    const { result } = renderHook(() => useBybitBalance())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.balance).toBe(9999)
    expect(result.current.source).toBe('cached')
  })

  it('uses FALLBACK_BALANCE when API fails and no cache', async () => {
    getBalanceMock.mockRejectedValueOnce(new Error('Network'))
    const { result } = renderHook(() => useBybitBalance())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.balance).toBe(10000)
    expect(result.current.error).not.toBeNull()
  })

  it('writes to localStorage on successful bybit_v5 fetch', async () => {
    getBalanceMock.mockResolvedValueOnce({
      source: 'bybit_v5',
      total_equity_usdt: 5000,
      fetched_at_iso: '2026-05-11T00:00:00Z',
    })
    const { result } = renderHook(() => useBybitBalance())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(localStorage.getItem('bybit_balance_cache_v1')).not.toBeNull()
  })
})
