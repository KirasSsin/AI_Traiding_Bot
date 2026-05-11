import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWfaFailAck } from '../useWfaFailAck'

const STORAGE_KEY = 'wfa_fail_ack_v1'

describe('useWfaFailAck — localStorage state machine', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('initial state — showFullBanner=true, showChip=false, no acks', () => {
    const { result } = renderHook(() => useWfaFailAck())
    expect(result.current.showFullBanner).toBe(true)
    expect(result.current.showChip).toBe(false)
    expect(result.current.ackedTotal).toBe(0)
    expect(result.current.distinctDays).toBe(0)
  })

  it('after first ack — showFullBanner=false, showChip=true, count=1', () => {
    const { result } = renderHook(() => useWfaFailAck())
    act(() => result.current.ack())
    expect(result.current.showFullBanner).toBe(false)
    expect(result.current.showChip).toBe(true)
    expect(result.current.ackedTotal).toBe(1)
    expect(result.current.distinctDays).toBeGreaterThanOrEqual(1)
  })

  it('multiple acks same day — distinctDays stays 1', () => {
    // Each act() flushes React state; same-day date dedup ensures distinctDays=1.
    // Note: multiple ack() calls inside one act() batch against same closure state
    // so count increments per-flush, not per-call. Wrap each in its own act().
    const { result } = renderHook(() => useWfaFailAck())
    act(() => result.current.ack())
    act(() => result.current.ack())
    act(() => result.current.ack())
    expect(result.current.ackedTotal).toBe(3)
    expect(result.current.distinctDays).toBe(1)
  })

  it('reset() clears state — back to initial', () => {
    const { result } = renderHook(() => useWfaFailAck())
    act(() => result.current.ack())
    expect(result.current.ackedTotal).toBe(1)
    act(() => result.current.reset())
    expect(result.current.ackedTotal).toBe(0)
    expect(result.current.distinctDays).toBe(0)
  })

  it('persists state to localStorage on ack', () => {
    const { result } = renderHook(() => useWfaFailAck())
    act(() => result.current.ack())
    const stored = window.localStorage.getItem(STORAGE_KEY)
    expect(stored).not.toBeNull()
    const parsed = JSON.parse(stored!)
    expect(parsed.count).toBe(1)
    expect(parsed.dates).toHaveLength(1)
  })

  it('hydrates state from localStorage on mount', () => {
    // Pre-seed 3 distinct days (REQUIRED_DAYS threshold — triggers chip downgrade)
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        count: 3,
        dates: ['2026-05-01', '2026-05-02', '2026-05-03'],
      }),
    )
    const { result } = renderHook(() => useWfaFailAck())
    expect(result.current.ackedTotal).toBe(3)
    expect(result.current.distinctDays).toBe(3)
    expect(result.current.showFullBanner).toBe(false)
    expect(result.current.showChip).toBe(true)
  })

  it('handles malformed localStorage gracefully — fallback to initial', () => {
    window.localStorage.setItem(STORAGE_KEY, 'not-json{{{')
    const { result } = renderHook(() => useWfaFailAck())
    expect(result.current.ackedTotal).toBe(0)
    expect(result.current.showFullBanner).toBe(true)
  })
})
