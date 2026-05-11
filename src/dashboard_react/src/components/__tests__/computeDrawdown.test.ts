import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { computeDrawdown } from '@/utils/computeDrawdown'

// Шорткат для readability
const { property, float, array, assert: fcAssert } = fc

describe('computeDrawdown — math invariants (fast-check property tests)', () => {
  it('returns array same length as input', () => {
    fcAssert(
      property(array(float({ noNaN: true, min: -100, max: 1000 }), { maxLength: 200 }), (xs) => {
        expect(computeDrawdown(xs).length).toBe(xs.length)
      }),
    )
  })

  it('drawdown values are always ≤ 0 (peak-relative loss never positive)', () => {
    fcAssert(
      property(array(float({ noNaN: true, min: -50, max: 500 }), { minLength: 1, maxLength: 200 }), (xs) => {
        const dd = computeDrawdown(xs)
        for (const v of dd) {
          expect(v).toBeLessThanOrEqual(0)
        }
      }),
    )
  })

  it('drawdown is 0 при first sample (no prior peak)', () => {
    fcAssert(
      property(float({ noNaN: true, min: -50, max: 500 }), (first) => {
        const dd = computeDrawdown([first])
        // First sample's peak == itself → drawdown = 0
        expect(dd[0]).toBe(0)
      }),
    )
  })

  it('monotonic-up sequence has zero drawdown everywhere', () => {
    // Strictly ascending sequence → peak === current → drawdown always 0
    const ascending = [0, 5, 10, 15, 20, 25, 30, 50, 100, 200]
    const dd = computeDrawdown(ascending)
    for (const v of dd) {
      expect(v).toBe(0)
    }
  })

  it('drop after peak produces negative drawdown', () => {
    // Peak at index 2 (equity_pct = 50 → multiplier 1.5), then drop к 0
    const series = [0, 25, 50, 0, 0]
    const dd = computeDrawdown(series)
    expect(dd[0]).toBe(0)
    expect(dd[1]).toBe(0)
    expect(dd[2]).toBe(0)
    // multiplier at idx 3 = 1.0, peak = 1.5 → (1.0 - 1.5) / 1.5 * 100 ≈ -33.33%
    expect(dd[3]).toBeCloseTo(-33.333, 2)
    expect(dd[4]).toBeCloseTo(-33.333, 2)
  })

  it('handles empty input', () => {
    expect(computeDrawdown([])).toEqual([])
  })

  it('handles single zero — drawdown is 0', () => {
    expect(computeDrawdown([0])).toEqual([0])
  })
})
