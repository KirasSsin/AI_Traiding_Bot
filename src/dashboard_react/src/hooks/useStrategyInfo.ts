import { useEffect, useState } from 'react'
import { api, ApiError } from '@/api/client'
import type { StrategyMetadata } from '@/api/types'

// Module-level cache survives component remounts (port S42 _strategyInfoCache pattern)
const cache: Record<string, StrategyMetadata> = {}

export interface UseStrategyInfoResult {
  info: StrategyMetadata | null
  loading: boolean
  error: ApiError | null
}

export function useStrategyInfo(strategyId: string | null): UseStrategyInfoResult {
  const [info, setInfo] = useState<StrategyMetadata | null>(
    strategyId && cache[strategyId] ? cache[strategyId] : null
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    if (!strategyId) {
      setInfo(null)
      setError(null)
      return
    }
    if (cache[strategyId]) {
      setInfo(cache[strategyId])
      setError(null)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    api
      .getStrategyInfo(strategyId)
      .then((data) => {
        if (cancelled) return
        cache[strategyId] = data
        setInfo(data)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        if (err instanceof ApiError) {
          setError(err)
        } else {
          setError(new ApiError(0, String(err)))
        }
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [strategyId])

  return { info, loading, error }
}
