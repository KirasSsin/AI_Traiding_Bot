// M7 fix tests — computeMonthlyData partition correctness
// Monthly return = last_of_month - last_of_prev_month (pct-point delta on cumulative series)
// This ensures months partition the total without gaps or double-counting.

import { describe, it, expect } from 'vitest'

// Pure computation extracted to monthlyHeatmapUtils for testability (M7 fix).
import { computeMonthlyData as computeMonthlyDataForTest } from '@/components/charts/monthlyHeatmapUtils'

// Helper: build unix timestamps for a specific year-month-day (UTC)
function ts(year: number, month: number, day: number): number {
  return Date.UTC(year, month - 1, day) / 1000
}

describe('computeMonthlyData — prior-month-close partition (M7)', () => {
  it('single month: return = last - first_sample_of_series', () => {
    // Only January data: 0% → 5%
    const timestamps = [ts(2024, 1, 1), ts(2024, 1, 15), ts(2024, 1, 31)]
    const equityPct = [0, 2, 5]
    const result = computeMonthlyDataForTest(timestamps, equityPct)
    expect(result.years).toEqual([2024])
    // January: last=5, prevClose=0 (start of series) → return = 5
    expect(result.cells.get(2024)?.get(0)).toBeCloseTo(5, 5)
  })

  it('two months: each month attributed correctly, no double-count', () => {
    // Jan: ends at 10%. Feb: ends at 15%.
    // Expected: Jan = 10, Feb = 15 - 10 = 5
    const timestamps = [
      ts(2024, 1, 10), ts(2024, 1, 31),
      ts(2024, 2, 1),  ts(2024, 2, 28),
    ]
    const equityPct = [3, 10, 11, 15]
    const result = computeMonthlyDataForTest(timestamps, equityPct)
    expect(result.years).toEqual([2024])
    const janReturn = result.cells.get(2024)?.get(0)  // month 0 = Jan
    const febReturn = result.cells.get(2024)?.get(1)  // month 1 = Feb
    // Jan: prior close = series start = first equityPct before Jan = 0 baseline
    // But with prior-month-close logic: prior month has no data → baseline = first value seen
    // Correction: prior close for Jan is the value BEFORE first Jan sample.
    // Since there's no data before Jan, baseline = 0 (implied start).
    // Jan close = 10, so Jan return = 10 - 0 = 10
    expect(janReturn).toBeCloseTo(10, 5)
    // Feb return = 15 - 10 = 5 (prior close = Jan last = 10)
    expect(febReturn).toBeCloseTo(5, 5)
  })

  it('returns sum reconciles to total cumulative pct change', () => {
    // 3 months: Jan ends 8%, Feb ends 20%, Mar ends 14%
    // Returns: Jan=8, Feb=12, Mar=-6. Sum=14 (total change from 0 to 14).
    const timestamps = [
      ts(2024, 1, 10), ts(2024, 1, 31),
      ts(2024, 2, 15), ts(2024, 2, 28),
      ts(2024, 3, 10), ts(2024, 3, 31),
    ]
    const equityPct = [2, 8, 12, 20, 18, 14]
    const result = computeMonthlyDataForTest(timestamps, equityPct)
    const jan = result.cells.get(2024)?.get(0) ?? 0
    const feb = result.cells.get(2024)?.get(1) ?? 0
    const mar = result.cells.get(2024)?.get(2) ?? 0
    expect(jan).toBeCloseTo(8, 5)
    expect(feb).toBeCloseTo(12, 5)
    expect(mar).toBeCloseTo(-6, 5)
    // Sum of monthly returns = total return (pct-point arithmetic)
    expect(jan + feb + mar).toBeCloseTo(14, 5)
  })

  it('cross-year boundary: Dec→Jan uses Dec last as Jan baseline', () => {
    // Dec 2023 ends at 10%. Jan 2024 ends at 13%.
    // Expected: Dec 2023 = 10, Jan 2024 = 3
    const timestamps = [
      ts(2023, 12, 15), ts(2023, 12, 31),
      ts(2024, 1, 10),  ts(2024, 1, 31),
    ]
    const equityPct = [5, 10, 11, 13]
    const result = computeMonthlyDataForTest(timestamps, equityPct)
    expect(result.years).toContain(2023)
    expect(result.years).toContain(2024)
    const dec2023 = result.cells.get(2023)?.get(11)  // month 11 = Dec
    const jan2024 = result.cells.get(2024)?.get(0)   // month 0 = Jan
    expect(dec2023).toBeCloseTo(10, 5)
    expect(jan2024).toBeCloseTo(3, 5)
  })

  it('single-sample month uses prior close correctly', () => {
    // Jan has 2 samples ending at 10. Feb has 1 sample at 12. Mar ends at 9.
    const timestamps = [
      ts(2024, 1, 1), ts(2024, 1, 31),
      ts(2024, 2, 28),
      ts(2024, 3, 15), ts(2024, 3, 31),
    ]
    const equityPct = [3, 10, 12, 8, 9]
    const result = computeMonthlyDataForTest(timestamps, equityPct)
    expect(result.cells.get(2024)?.get(0)).toBeCloseTo(10, 5)  // Jan
    expect(result.cells.get(2024)?.get(1)).toBeCloseTo(2, 5)   // Feb = 12-10
    expect(result.cells.get(2024)?.get(2)).toBeCloseTo(-3, 5)  // Mar = 9-12
  })
})
