// useBybitBalance — S48 T20.
// Fetch /api/bybit/balance с graceful fallback + localStorage cache.

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/api/client'
import type { BalanceResponse } from '@/api/types'

const CACHE_KEY = 'bybit_balance_cache_v1'
const FALLBACK_BALANCE = 10000

export function useBybitBalance() {
  const [balance, setBalance] = useState<number>(FALLBACK_BALANCE)
  const [source, setSource] = useState<string>('fallback')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [fetchedAt, setFetchedAt] = useState<string>('')

  const fetchBalance = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getBalance()
      setBalance(data.total_equity_usdt)
      setSource(data.source)
      setError(data.error ?? null)
      setFetchedAt(data.fetched_at_iso)
      // Cache successful fetches (not fallback)
      if (data.source === 'bybit_v5') {
        localStorage.setItem(CACHE_KEY, JSON.stringify(data))
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      // Try cache fallback
      const cached = localStorage.getItem(CACHE_KEY)
      if (cached) {
        try {
          const parsed = JSON.parse(cached) as BalanceResponse
          setBalance(parsed.total_equity_usdt)
          setSource('cached')
          setError(`Network error, using cached: ${msg}`)
          setFetchedAt(parsed.fetched_at_iso)
        } catch {
          setError(msg)
        }
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBalance()
  }, [fetchBalance])

  return { balance, source, error, loading, fetchedAt, refresh: fetchBalance }
}
