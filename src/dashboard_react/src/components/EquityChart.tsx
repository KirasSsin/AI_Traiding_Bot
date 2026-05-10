// S46 T9 — EquityChart: uPlot wrapper с Anthropic orange palette + ResizeObserver
// Forward-compat: onChartReady callback exposed for T10 sync-key registration

import { useEffect, useRef } from 'react'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'
import type { EquityCurve } from '@/api/types'
import styles from './EquityChart.module.css'

export interface EquityChartProps {
  equityCurve: EquityCurve
  height?: number
  /** T10: register uPlot sync key after chart mounts */
  onChartReady?: (chart: uPlot) => void
}

// Build uPlot series array — not hard-coded count so T11 can extend
function buildSeries(): uPlot.Series[] {
  return [
    // x-axis series (required placeholder by uPlot)
    {},
    // T11: extend with trade-marker series here
    {
      label: 'Equity %',
      stroke: '#cc785c',                     // Anthropic orange
      fill: 'rgba(204, 120, 92, 0.12)',      // translucent orange under-curve
      width: 1.5,
      points: { show: false },
    },
  ]
}

function buildOpts(width: number, height: number): uPlot.Options {
  const axisFont = "11px 'JetBrains Mono', monospace"

  return {
    width,
    height,
    cursor: {
      drag: { x: true, y: false },
    },
    legend: { show: false },
    series: buildSeries(),
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

export function EquityChart({ equityCurve, height = 320, onChartReady }: EquityChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<uPlot | null>(null)

  const isEmpty =
    equityCurve.timestamps.length === 0 || equityCurve.equity_pct.length === 0

  useEffect(() => {
    if (isEmpty) return
    const container = containerRef.current
    if (container === null) return

    const width = container.clientWidth || 800

    // uPlot AlignedData: [xs, ...ys]
    const data: uPlot.AlignedData = [
      equityCurve.timestamps,
      equityCurve.equity_pct,
    ]

    const chart = new uPlot(buildOpts(width, height), data, container)
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
  }, [equityCurve, height, isEmpty, onChartReady])

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
        style={{ height: `${height}px` }}
      />
    </div>
  )
}
