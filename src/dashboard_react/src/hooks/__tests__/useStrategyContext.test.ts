import { describe, it, expect, beforeEach } from 'vitest'
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
})
