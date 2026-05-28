import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useStrategyContext } from '../useStrategyContext'

describe('useStrategyContext — URL query param state (S48 T18)', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/')
  })

  it('initial state — null when no query param', () => {
    const { result } = renderHook(() => useStrategyContext())
    expect(result.current.currentStrategy).toBeNull()
  })

  it('initial state — reads existing query param', () => {
    window.history.replaceState({}, '', '/?strategy=ema_crossover_s13')
    const { result } = renderHook(() => useStrategyContext())
    expect(result.current.currentStrategy).toBe('ema_crossover_s13')
  })

  it('setCurrentStrategy updates URL + state', () => {
    const { result } = renderHook(() => useStrategyContext())
    act(() => result.current.setCurrentStrategy('mean_reversion_s15'))
    expect(result.current.currentStrategy).toBe('mean_reversion_s15')
    expect(window.location.search).toBe('?strategy=mean_reversion_s15')
  })

  it('setCurrentStrategy(null) clears URL param', () => {
    window.history.replaceState({}, '', '/?strategy=ema_crossover_s13&other=foo')
    const { result } = renderHook(() => useStrategyContext())
    act(() => result.current.setCurrentStrategy(null))
    expect(result.current.currentStrategy).toBeNull()
    expect(window.location.search).toBe('?other=foo')
  })

  // M2 (S49) — multi-instance sync. history.replaceState does NOT emit popstate,
  // so a second mounted hook instance must learn of changes via a custom event.
  it('M2 — two hook instances stay in sync on setCurrentStrategy', () => {
    const a = renderHook(() => useStrategyContext())
    const b = renderHook(() => useStrategyContext())
    expect(a.result.current.currentStrategy).toBeNull()
    expect(b.result.current.currentStrategy).toBeNull()

    // Instance A writes → instance B must reflect the new value (live, no reload).
    act(() => a.result.current.setCurrentStrategy('mean_reversion_s17_relaxed'))
    expect(a.result.current.currentStrategy).toBe('mean_reversion_s17_relaxed')
    expect(b.result.current.currentStrategy).toBe('mean_reversion_s17_relaxed')

    // Reverse direction: B clears → A reflects null.
    act(() => b.result.current.setCurrentStrategy(null))
    expect(b.result.current.currentStrategy).toBeNull()
    expect(a.result.current.currentStrategy).toBeNull()
  })

  it('M2 — removes custom event listener on unmount (no leak)', () => {
    const removeSpy = vi.spyOn(window, 'removeEventListener')
    const { unmount } = renderHook(() => useStrategyContext())
    unmount()
    const events = removeSpy.mock.calls.map((c) => c[0])
    expect(events).toContain('popstate')
    expect(events).toContain('strategychange')
    removeSpy.mockRestore()
  })
})
