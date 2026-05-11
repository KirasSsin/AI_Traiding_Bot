// S46 T9 — EquityChart: uPlot wrapper с Anthropic orange palette + ResizeObserver
// T10: syncKey prop для uPlot cursor sync с DrawdownSubchart
// T11: trade markers overlay — scatter series (wins green, losses red)

import { useEffect, useRef } from 'react'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'
import type { EquityCurve, TradeMarkers } from '@/api/types'
import styles from './EquityChart.module.css'

export interface EquityChartProps {
  equityCurve: EquityCurve
  height?: number
  /** T10: uPlot sync group key for x-axis cursor sharing with DrawdownSubchart */
  syncKey?: string
  /** @deprecated T10: use syncKey instead — kept for backward compat */
  onChartReady?: (chart: uPlot) => void
}

/**
 * T11 — Build aligned win/loss marker arrays sized to timestamps.
 * Each marker's x = exit_timestamp, y = equity_pct at that index.
 * O(N+M) via Map lookup: M = trades, N = equity bars.
 */
function buildMarkerSeries(
  timestamps: number[],
  equityPct: number[],
  markers: TradeMarkers,
): { wins: (number | null)[]; losses: (number | null)[] } {
  // Map exit timestamp → pnl_pct for O(1) lookup
  const exitToPnl = new Map<number, number>()
  markers.exit_timestamps.forEach((ts, i) => {
    exitToPnl.set(ts, markers.pnl_pcts[i] ?? 0)
  })

  const wins = new Array<number | null>(timestamps.length).fill(null)
  const losses = new Array<number | null>(timestamps.length).fill(null)

  timestamps.forEach((ts, i) => {
    const pnl = exitToPnl.get(ts)
    if (pnl === undefined) return
    const y = equityPct[i] ?? null
    if (pnl > 0) {
      wins[i] = y
    } else {
      losses[i] = y
    }
  })

  return { wins, losses }
}

// Build uPlot series array — extends с trade-marker scatter series when markers present
function buildSeries(hasMarkers: boolean): uPlot.Series[] {
  const base: uPlot.Series[] = [
    // x-axis series (required placeholder by uPlot)
    {},
    {
      label: 'Equity %',
      stroke: '#cc785c',                     // Anthropic orange
      fill: 'rgba(204, 120, 92, 0.12)',      // translucent orange under-curve
      width: 1.5,
      points: { show: false },
    },
  ]

  if (!hasMarkers) return base

  // T11 — scatter series for trade exit markers (no line, only points)
  return [
    ...base,
    {
      label: 'Win exit',
      stroke: '#00ff88',
      fill: '#00ff88',
      width: 0,
      // paths: null disables line rendering — scatter pattern per uPlot docs
      paths: (() => null) as unknown as uPlot.Series.PathBuilder,
      points: { show: true, size: 6, fill: '#00ff88', stroke: '#00ff88' },
    },
    {
      label: 'Loss exit',
      stroke: '#ff3366',
      fill: '#ff3366',
      width: 0,
      paths: (() => null) as unknown as uPlot.Series.PathBuilder,
      points: { show: true, size: 6, fill: '#ff3366', stroke: '#ff3366' },
    },
  ]
}

function buildOpts(width: number, height: number, hasMarkers: boolean, syncKey?: string): uPlot.Options {
  const axisFont = "11px 'JetBrains Mono', monospace"

  return {
    width,
    height,
    cursor: {
      show: true,
      drag: { x: true, y: false },
      // S47 T14: cursor dot on equity line
      points: { show: true, size: 6, fill: '#cc785c', stroke: '#cc785c' },
      // T10: attach to sync group when syncKey provided
      ...(syncKey !== undefined
        ? { sync: { key: syncKey, setSeries: false } }
        : {}),
    },
    legend: { show: false },
    series: buildSeries(hasMarkers),
    axes: [
      // x-axis (time)
      {
        stroke: '#9ca3af',
        grid: { stroke: 'rgba(156, 163, 175, 0.10)', width: 1 },
        ticks: { stroke: 'rgba(156, 163, 175, 0.20)', width: 1 },
        font: axisFont,
      },
      // y-axis (equity %)
      {
        stroke: '#9ca3af',
        grid: { stroke: 'rgba(156, 163, 175, 0.10)', width: 1 },
        ticks: { stroke: 'rgba(156, 163, 175, 0.20)', width: 1 },
        font: axisFont,
        values: (_self: uPlot, ticks: number[]) =>
          ticks.map((v) => `${v.toFixed(0)}%`),
      },
    ],
    scales: {
      x: { time: true },
    },
  }
}

export function EquityChart({ equityCurve, height = 320, syncKey, onChartReady }: EquityChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<uPlot | null>(null)

  // PHASE 6 frontend-developer HIGH fix: split equityCurve to granular deps so
  // unrelated parent re-renders (with new response object reference but same data)
  // don't tear down + rebuild the chart. Match DrawdownSubchart pattern.
  const { timestamps, equity_pct, trade_markers } = equityCurve
  const isEmpty = timestamps.length === 0 || equity_pct.length === 0

  useEffect(() => {
    if (isEmpty) return
    const container = containerRef.current
    if (container === null) return

    const width = container.clientWidth || 800

    // T11 — detect and build trade marker aligned arrays
    const markers = trade_markers ?? null
    const hasMarkers = markers !== null && markers.exit_timestamps.length > 0

    let data: uPlot.AlignedData
    if (hasMarkers && markers !== null) {
      const { wins, losses } = buildMarkerSeries(timestamps, equity_pct, markers)
      // AlignedData: [timestamps, equity_pct, win_markers, loss_markers]
      data = [timestamps, equity_pct, wins, losses]
    } else {
      // uPlot AlignedData: [xs, ...ys]
      data = [timestamps, equity_pct]
    }

    const opts = buildOpts(width, height, hasMarkers, syncKey)

    // S47 T14 — setCursor hook: floating tooltip showing Date + Equity%
    opts.hooks = {
      setCursor: [
        (u: uPlot) => {
          const idx = u.cursor.idx
          const tooltipEl = container.querySelector(
            '[data-tooltip="equity"]',
          ) as HTMLDivElement | null
          if (tooltipEl === null) return
          if (idx === null || idx === undefined || idx < 0) {
            tooltipEl.style.display = 'none'
            return
          }
          const ts = u.data[0]?.[idx]
          const eq = u.data[1]?.[idx]
          if (ts === undefined || ts === null || eq === undefined || eq === null) {
            tooltipEl.style.display = 'none'
            return
          }
          const date = new Date(Number(ts) * 1000).toISOString().slice(0, 10)
          const sign = eq >= 0 ? '+' : ''
          tooltipEl.textContent = `${date} · ${sign}${eq.toFixed(2)}%`
          tooltipEl.style.display = 'block'
          const left = u.cursor.left ?? 0
          tooltipEl.style.left = `${left + 12}px`
        },
      ],
    }

    const chart = new uPlot(opts, data, container)
    chartRef.current = chart

    onChartReady?.(chart)

    // ResizeObserver — обновляет ширину при изменении контейнера
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry === undefined) return
      const newWidth = Math.floor(entry.contentRect.width)
      if (newWidth > 0 && chartRef.current !== null) {
        chartRef.current.setSize({ width: newWidth, height })
      }
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      chart.destroy()
      chartRef.current = null
    }
  }, [timestamps, equity_pct, trade_markers, height, isEmpty, syncKey, onChartReady])

  if (isEmpty) {
    return (
      <div className={styles.container}>
        <div className={styles.placeholder}>
          No equity data available — legacy WFA preset без envelope
        </div>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <div className={styles.title}>▸ EQUITY CURVE</div>
      <div
        ref={containerRef}
        className={styles.chartWrapper}
        style={{ height: `${height}px`, position: 'relative' }}
      >
        {/* S47 T14 — floating tooltip rendered by setCursor hook */}
        <div data-tooltip="equity" className={styles.tooltip} style={{ display: 'none' }} />
      </div>
    </div>
  )
}
