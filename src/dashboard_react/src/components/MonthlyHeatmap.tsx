// S46 T12 — MonthlyHeatmap: calendar grid of monthly PnL returns
// Rows = years, cols = 12 months. Intensity-scaled color per return magnitude.

import { useMemo } from 'react'
import type { EquityCurve } from '@/api/types'
import styles from './MonthlyHeatmap.module.css'

export interface MonthlyHeatmapProps {
  equityCurve: EquityCurve
}

const MONTH_LABELS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'] as const

interface MonthlyData {
  years: number[]
  cells: Map<number, Map<number, number>>  // year → month(0-11) → return%
}

/** Compute per-month PnL returns from cumulative equity_pct series. */
function computeMonthlyData(timestamps: number[], equityPct: number[]): MonthlyData {
  // Group samples by (year, month) — keep first + last equity_pct per group
  const groups = new Map<string, { first: number; last: number }>()

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
      groups.set(key, { first: val, last: val })
    } else {
      // last always updates; first stays at initial value
      existing.last = val
    }
  }

  // Build cells map: year → month → return%
  const cells = new Map<number, Map<number, number>>()
  let minYear = Infinity
  let maxYear = -Infinity

  groups.forEach((entry, key) => {
    const dashIdx = key.indexOf('-')
    const year = parseInt(key.slice(0, dashIdx), 10)
    const month = parseInt(key.slice(dashIdx + 1), 10)
    const ret = entry.last - entry.first  // cumulative pct diff = monthly return

    if (year < minYear) minYear = year
    if (year > maxYear) maxYear = year

    let yearMap = cells.get(year)
    if (yearMap === undefined) {
      yearMap = new Map<number, number>()
      cells.set(year, yearMap)
    }
    yearMap.set(month, ret)
  })

  // Build sorted years array spanning full range
  const years: number[] = []
  if (minYear !== Infinity) {
    for (let y = minYear; y <= maxYear; y++) {
      years.push(y)
    }
  }

  return { years, cells }
}

/** Dynamic cell background based on return magnitude. */
function cellStyle(value: number | undefined): React.CSSProperties {
  if (value === undefined) return { backgroundColor: 'transparent' }
  const intensity = Math.min(Math.abs(value) / 20, 1)   // saturates at ±20%
  const alpha = 0.15 + intensity * 0.55                   // 0.15..0.70 range
  if (value > 0) return { backgroundColor: `rgba(0, 255, 136, ${alpha})` }
  if (value < 0) return { backgroundColor: `rgba(255, 51, 102, ${alpha})` }
  return { backgroundColor: 'rgba(156, 163, 175, 0.10)' }  // zero = muted gray
}

/** Format return value for display in cell. */
function formatReturn(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

export function MonthlyHeatmap({ equityCurve }: MonthlyHeatmapProps) {
  const { timestamps, equity_pct } = equityCurve

  // Guard: need at least 2 samples
  if (timestamps.length < 2 || equity_pct.length < 2) {
    return (
      <div className={styles.container}>
        <div className={styles.title}>▸ MONTHLY RETURNS</div>
        <div className={styles.placeholder}>Insufficient data for monthly heatmap</div>
      </div>
    )
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const monthlyData = useMemo(
    () => computeMonthlyData(timestamps, equity_pct),
    [timestamps, equity_pct],
  )

  if (monthlyData.years.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.title}>▸ MONTHLY RETURNS</div>
        <div className={styles.placeholder}>Insufficient data for monthly heatmap</div>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <div className={styles.title}>▸ MONTHLY RETURNS</div>
      <div className={styles.grid}>
        {/* Header row: year label col + 12 month abbreviations */}
        <div className={styles.yearLabel} />
        {MONTH_LABELS.map((label) => (
          <div key={label} className={styles.monthHeader}>
            {label}
          </div>
        ))}

        {/* Data rows: one per year */}
        {monthlyData.years.map((year) => {
          const yearMap = monthlyData.cells.get(year)
          return [
            <div key={`year-${year}`} className={styles.yearLabel}>
              {year}
            </div>,
            ...Array.from({ length: 12 }, (_, month) => {
              const value = yearMap?.get(month)
              return (
                <div
                  key={`${year}-${month}`}
                  className={styles.cell}
                  style={cellStyle(value)}
                  title={value !== undefined ? `${year} ${MONTH_LABELS[month]}: ${formatReturn(value)}` : undefined}
                >
                  {value !== undefined && (
                    <span className={styles.cellText}>{formatReturn(value)}</span>
                  )}
                </div>
              )
            }),
          ]
        })}
      </div>
    </div>
  )
}
