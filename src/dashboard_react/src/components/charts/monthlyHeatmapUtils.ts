// M7 fix: pure monthly-return computation extracted for testability.
// Monthly return = last_of_month - last_of_prev_month (prior-month-close baseline).
// This partitions the total cumulative return without gaps or double-counting.

export interface MonthlyData {
  years: number[]
  cells: Map<number, Map<number, number>>  // year → month(0-11) → return%
}

/** Compute per-month PnL returns from a cumulative equity_pct series.
 *
 * Algorithm: scan chronologically, track last equity_pct per (year, month).
 * Monthly return = month_close - prior_month_close.
 * Baseline for the first month = 0 (implied start before any trade).
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

  // Build cells map: year → month → return% using prior-month-close as baseline.
  // prevClose starts at 0 (implied equity_pct before the series begins).
  const cells = new Map<number, Map<number, number>>()
  let minYear = Infinity
  let maxYear = -Infinity
  let prevClose = 0  // implicit start baseline

  for (const entry of groups.values()) {
    const { year, month, last } = entry
    const ret = last - prevClose  // pct-point delta from prior month's close
    prevClose = last              // this month's close becomes next month's baseline

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
