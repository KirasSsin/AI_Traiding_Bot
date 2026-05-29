// useStrategyContext — S48 T18 (architect C2 BINDING).
// Read/write `?strategy=<id>` URL query param. No Context/Zustand.

import { useState, useEffect, useCallback } from 'react'

const PARAM_NAME = 'strategy'
// M2 (S49) — custom event for cross-instance sync. history.replaceState does NOT
// emit popstate, so a second mounted hook instance never re-renders on a change
// made by another instance. We dispatch this event on every write + subscribe to it.
const STRATEGY_CHANGE_EVENT = 'strategychange'

function readStrategy(): string | null {
  if (typeof window === 'undefined') return null
  const params = new URLSearchParams(window.location.search)
  return params.get(PARAM_NAME)
}

export function useStrategyContext() {
  const [currentStrategy, setCurrentStrategyState] = useState<string | null>(readStrategy)

  // Listen for URL changes: popstate (browser back/forward) + strategychange
  // (M2 — same-document writes from another hook instance).
  useEffect(() => {
    const handler = () => setCurrentStrategyState(readStrategy())
    window.addEventListener('popstate', handler)
    window.addEventListener(STRATEGY_CHANGE_EVENT, handler)
    return () => {
      window.removeEventListener('popstate', handler)
      window.removeEventListener(STRATEGY_CHANGE_EVENT, handler)
    }
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
    // M2 — notify other mounted hook instances (replaceState emits no popstate).
    window.dispatchEvent(new Event(STRATEGY_CHANGE_EVENT))
  }, [])

  return { currentStrategy, setCurrentStrategy }
}
