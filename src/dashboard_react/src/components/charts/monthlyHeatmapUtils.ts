// DASH-02 (S55) fix: pure monthly-return computation extracted for testability.
// True monthly return = ratio of equity MULTIPLIERS, not a delta of compounded
// cumulative percentages. The series is a COMPOUNDED cumulative equity_pct, so
// subtracting two cumulative pcts (month_close - prev_close) systematically
// overstates the period return — the further equity is from 0%, the worse:
// at +800% cumulative a real ~5.6% month reads as ~+50% (≈9× overstatement).

export interface MonthlyData {
  years: number[]
  cells: Map<number, Map<number, number>>  // year → month(0-11) → return%
}

/** Compute per-month PnL returns from a cumulative (compounded) equity_pct series.
 *
 * Algorithm: scan chronologically, track last equity_pct per (year, month).
 * Convert to multipliers (mult_i = 1 + equity_pct_i/100) and take the ratio:
 *   month return % = (mult_close / mult_prev_close - 1) * 100.
 * Baseline for the first month = 1.0 (implied equity multiplier before the series),
 * so the first cell = (mult_close / 1.0 - 1) * 100 = its cumulative at month-end.
 *
 * Note: per-month cells no longer SUM to the final cumulative — they COMPOUND
 * (product of multipliers reconciles to the total). That is the correct behaviour
 * for true period returns on a compounded curve.
 */
export function computeMonthlyData(timestamps: number[], equityPct: number[]): MonthlyData {
  // Group samples by (year, month) — keep only the last equity_pct per group (month-close).
  // Map insertion order is chronological (data arrives in order).
  const groups = new Map<string, { year: number; month: number; last: number }>()

  for (let i = 0; i < timestamps.length; i++) {
    const ts = timestamps[i]
    const val = equityPct[i]
    if (ts === undefined || val === undefined) continue

    const d = new Date(ts * 1000)
    const year = d.getUTCFullYear()
    const month = d.getUTCMonth()  // 0-11
    const key = `${year}-${month}`

    const existing = groups.get(key)
    if (existing === undefined) {
      groups.set(key, { year, month, last: val })
    } else {
      // last always updates as we process chronologically
      existing.last = val
    }
  }

  // Build cells map: year → month → return% using the prior-month-close
  // MULTIPLIER as baseline. prevMult starts at 1.0 (implied equity multiplier
  // before the series begins) so the first month's cell equals its cumulative.
  const cells = new Map<number, Map<number, number>>()
  let minYear = Infinity
  let maxYear = -Infinity
  let prevMult = 1.0  // implicit start baseline multiplier (equity_pct = 0%)

  for (const entry of groups.values()) {
    const { year, month, last } = entry
    const mult = 1 + last / 100        // this month's close as an equity multiplier
    const ret = (mult / prevMult - 1) * 100  // true period return on a compounded curve
    prevMult = mult                    // this month's multiplier becomes next month's baseline

    if (year < minYear) minYear = year
    if (year > maxYear) maxYear = year

    let yearMap = cells.get(year)
    if (yearMap === undefined) {
      yearMap = new Map<number, number>()
      cells.set(year, yearMap)
    }
    yearMap.set(month, ret)
  }

  // Build sorted years array spanning full range
  const years: number[] = []
  if (minYear !== Infinity) {
    for (let y = minYear; y <= maxYear; y++) {
      years.push(y)
    }
  }

  return { years, cells }
}
