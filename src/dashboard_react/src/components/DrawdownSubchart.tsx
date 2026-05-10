// S46 T10 — DrawdownSubchart: uPlot drawdown subchart
// Architect CC2: shares x-axis cursor with EquityChart via uPlot.sync key

import { useEffect, useMemo, useRef } from 'react'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'
import type { EquityCurve } from '@/api/types'
import styles from './DrawdownSubchart.module.css'

export interface DrawdownSubchartProps {
  equityCurve: EquityCurve
  /** uPlot sync group key — must match EquityChart syncKey for cursor sharing */
  syncKey?: string
  /** Chart height in pixels (default 140 — smaller than main equity chart) */
  height?: number
}

/**
 * Converts cumulative equity_pct series to drawdown percent series.
 * Drawdown is always <= 0 (0 = at peak, negative = below peak).
 */
function computeDrawdown(equityPct: number[]): number[] {
  const result = new Array<number>(equityPct.length)
  let peak = -Infinity
  for (let i = 0; i < equityPct.length; i++) {
    // Convert cumulative % to multiplier: e.g. 12 → 1.12
    const v = (equityPct[i] ?? 0) / 100 + 1
    if (v > peak) peak = v
    // Drawdown as negative percent: (current - peak) / peak * 100
    result[i] = peak > 0 ? ((v - peak) / peak) * 100 : 0
  }
  return result
}

function buildSeries(): uPlot.Series[] {
  return [
    // x-axis placeholder (required by uPlot)
    {},
    {
      label: 'Drawdown %',
      stroke: '#ff3366',                    // cyberpunk danger red
      fill: 'rgba(255, 51, 102, 0.15)',     // translucent red under-curve
      width: 1.5,
      points: { show: false },
    },
  ]
}

function buildOpts(width: number, height: number, syncKey?: string): uPlot.Options {
  const axisFont = "11px 'JetBrains Mono', monospace"

  return {
    width,
    height,
    cursor: {
      drag: { x: true, y: false },
      // CC2: sync cursor with EquityChart when syncKey provided
      ...(syncKey !== undefined
        ? { sync: { key: syncKey, setSeries: false } }
        : {}),
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
      // y-axis (drawdown %, always negative)
      {
        stroke: '#9ca3af',
        grid: { stroke: 'rgba(156, 163, 175, 0.10)', width: 1 },
        ticks: { stroke: 'rgba(156, 163, 175, 0.20)', width: 1 },
        font: axisFont,
        values: (_self: uPlot, ticks: number[]) =>
          ticks.map((v) => `${v.toFixed(1)}%`),
      },
    ],
    scales: {
      x: { time: true },
    },
  }
}

export function DrawdownSubchart({
  equityCurve,
  syncKey,
  height = 140,
}: DrawdownSubchartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<uPlot | null>(null)

  const isEmpty =
    equityCurve.timestamps.length === 0 || equityCurve.equity_pct.length === 0

  // Compute drawdown once per equity_pct change (memoized)
  const drawdownSeries = useMemo(
    () => computeDrawdown(equityCurve.equity_pct),
    [equityCurve.equity_pct],
  )

  useEffect(() => {
    if (isEmpty) return
    const container = containerRef.current
    if (container === null) return

    const width = container.clientWidth || 800

    // uPlot AlignedData: [xs, ...ys]
    const data: uPlot.AlignedData = [
      equityCurve.timestamps,
      drawdownSeries,
    ]

    const chart = new uPlot(buildOpts(width, height, syncKey), data, container)
    chartRef.current = chart

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
  }, [equityCurve.timestamps, drawdownSeries, height, isEmpty, syncKey])

  if (isEmpty) {
    return (
      <div className={styles.container}>
        <div className={styles.placeholder}>No drawdown data</div>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <div className={styles.title}>▸ DRAWDOWN</div>
      <div
        ref={containerRef}
        className={styles.chartWrapper}
        style={{ height: `${height}px` }}
      />
    </div>
  )
}
