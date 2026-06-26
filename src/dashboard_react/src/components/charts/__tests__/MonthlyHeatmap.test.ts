// DASH-02 (S55) fix tests — computeMonthlyData TRUE monthly return.
// Monthly return = ratio of equity multipliers, NOT a delta of compounded
// cumulative percentages. With mult_i = 1 + equity_pct_i/100,
// month return % = (mult_close / mult_prev_close - 1) * 100
// (prev baseline mult = 1.0 for the first month).
// Subtracting two compounded cumulative pcts overstates returns the further
// equity is from 0% — exactly where the high-return presets live.

import { describe, it, expect } from 'vitest'

// Pure computation extracted to monthlyHeatmapUtils for testability.
import { computeMonthlyData as computeMonthlyDataForTest } from '@/components/charts/monthlyHeatmapUtils'

// Helper: build unix timestamps for a specific year-month-day (UTC)
function ts(year: number, month: number, day: number): number {
  return Date.UTC(year, month - 1, day) / 1000
}

describe('computeMonthlyData — multiplier-ratio monthly return (DASH-02)', () => {
  it('single month: return = month-end cumulative (baseline mult = 1.0)', () => {
    // Only January data: 0% → 5%
    const timestamps = [ts(2024, 1, 1), ts(2024, 1, 15), ts(2024, 1, 31)]
    const equityPct = [0, 2, 5]
    const result = computeMonthlyDataForTest(timestamps, equityPct)
    expect(result.years).toEqual([2024])
    // January: mult_close=1.05, baseline=1.0 → (1.05/1.0 - 1)*100 = 5
    expect(result.cells.get(2024)?.get(0)).toBeCloseTo(5, 5)
  })

  it('two months: each month is the period return, not a pct-point delta', () => {
    // Jan ends at 10%. Feb ends at 15%.
    // Jan = (1.10/1.00 - 1)*100 = 10.0
    // Feb = (1.15/1.10 - 1)*100 = 4.5454...  (NOT 5.0 from delta)
    const timestamps = [
      ts(2024, 1, 10), ts(2024, 1, 31),
      ts(2024, 2, 1),  ts(2024, 2, 28),
    ]
    const equityPct = [3, 10, 11, 15]
    const result = computeMonthlyDataForTest(timestamps, equityPct)
    expect(result.years).toEqual([2024])
    const janReturn = result.cells.get(2024)?.get(0)  // month 0 = Jan
    const febReturn = result.cells.get(2024)?.get(1)  // month 1 = Feb
    expect(janReturn).toBeCloseTo(10, 5)
    expect(febReturn).toBeCloseTo((1.15 / 1.10 - 1) * 100, 5)  // ≈ 4.5455
  })

  it('large cumulative: 800% → 850% month-end yields ≈ +5.6%, NOT +50%', () => {
    // The core DASH-02 bug: subtracting compounded cumulative pcts (850-800=50)
    // grossly overstates a real ~5.6% monthly return at high equity.
    const timestamps = [
      ts(2024, 1, 10), ts(2024, 1, 31),
      ts(2024, 2, 15), ts(2024, 2, 28),
    ]
    const equityPct = [780, 800, 820, 850]
    const result = computeMonthlyDataForTest(timestamps, equityPct)
    const febReturn = result.cells.get(2024)?.get(1) ?? 0  // month 1 = Feb
    // Feb = (9.50/9.00 - 1)*100 = 5.5555...
    expect(febReturn).toBeCloseTo((9.5 / 9.0 - 1) * 100, 5)  // ≈ 5.5556
    expect(febReturn).not.toBeCloseTo(50, 0)
  })

  it('monthly returns compound (product) back to total cumulative, not sum', () => {
    // 3 months: Jan ends 8%, Feb ends 20%, Mar ends 14%.
    // Jan = (1.08/1.00 - 1)*100 = 8.0
    // Feb = (1.20/1.08 - 1)*100 = 11.111...
    // Mar = (1.14/1.20 - 1)*100 = -5.0
    // Product of multipliers = 1.14 = final cumulative (1 + 14/100).
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
    expect(feb).toBeCloseTo((1.2 / 1.08 - 1) * 100, 5)  // ≈ 11.1111
    expect(mar).toBeCloseTo(-5, 5)
    // Compounding the per-month multipliers reconciles to total cumulative (1.14).
    const product = (1 + jan / 100) * (1 + feb / 100) * (1 + mar / 100)
    expect(product).toBeCloseTo(1.14, 5)
  })

  it('cross-year boundary: Dec→Jan uses Dec multiplier as Jan baseline', () => {
    // Dec 2023 ends at 10%. Jan 2024 ends at 13%.
    // Dec 2023 = (1.10/1.00 - 1)*100 = 10.0
    // Jan 2024 = (1.13/1.10 - 1)*100 = 2.7272...
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
    expect(jan2024).toBeCloseTo((1.13 / 1.10 - 1) * 100, 5)  // ≈ 2.7273
  })

  it('single-sample month uses prior multiplier as baseline', () => {
    // Jan ends at 10. Feb single sample at 12. Mar ends at 9.
    // Jan = (1.10/1.00 - 1)*100 = 10.0
    // Feb = (1.12/1.10 - 1)*100 = 1.8181...
    // Mar = (1.09/1.12 - 1)*100 = -2.6785...
    const timestamps = [
      ts(2024, 1, 1), ts(2024, 1, 31),
      ts(2024, 2, 28),
      ts(2024, 3, 15), ts(2024, 3, 31),
    ]
    const equityPct = [3, 10, 12, 8, 9]
    const result = computeMonthlyDataForTest(timestamps, equityPct)
    expect(result.cells.get(2024)?.get(0)).toBeCloseTo(10, 5)  // Jan
    expect(result.cells.get(2024)?.get(1)).toBeCloseTo((1.12 / 1.10 - 1) * 100, 5)  // Feb ≈ 1.8182
    expect(result.cells.get(2024)?.get(2)).toBeCloseTo((1.09 / 1.12 - 1) * 100, 5)  // Mar ≈ -2.6786
  })
})
