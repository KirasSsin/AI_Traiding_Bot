// useStrategyContext — S48 T18 (architect C2 BINDING).
// Read/write `?strategy=<id>` URL query param. No Context/Zustand.

import { useState, useEffect, useCallback } from 'react'

const PARAM_NAME = 'strategy'

function readStrategy(): string | null {
  if (typeof window === 'undefined') return null
  const params = new URLSearchParams(window.location.search)
  return params.get(PARAM_NAME)
}

export function useStrategyContext() {
  const [currentStrategy, setCurrentStrategyState] = useState<string | null>(readStrategy)

  // Listen для URL changes (popstate when user navigates back/forward)
  useEffect(() => {
    const handler = () => setCurrentStrategyState(readStrategy())
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])

  const setCurrentStrategy = useCallback((strategyId: string | null) => {
    const url = new URL(window.location.href)
    if (strategyId === null) {
      url.searchParams.delete(PARAM_NAME)
    } else {
      url.searchParams.set(PARAM_NAME, strategyId)
    }
    // Use history.replaceState — no entry in browser history (silent update)
    window.history.replaceState({}, '', url.toString())
    setCurrentStrategyState(strategyId)
  }, [])

  return { currentStrategy, setCurrentStrategy }
}
