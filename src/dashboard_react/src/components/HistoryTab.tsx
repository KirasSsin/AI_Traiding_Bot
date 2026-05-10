// HistoryTab — T15a: backtest run history table (self-contained, fetches /api/runs).
// Vanilla port: src/dashboard/static/dashboard.js lines 524-562 (loadHistory).
// 9-column table; RAW vs WFA cell logic per vanilla S42.3 + S44 T8.

import { useState, useEffect } from 'react'
import { api } from '@/api/client'
import type { RunSummary, Verdict } from '@/api/types'
import { WfaFailBadge } from './WfaFailBadge'
import styles from './HistoryTab.module.css'

// ─── helpers ─────────────────────────────────────────────────────────────

type Nullish = number | null | undefined

function fmt(value: Nullish, digits: number): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

function verdictCellClass(verdict: Verdict): string {
  switch (verdict) {
    case 'WFA_PASS':
    case 'PASS':
      return styles.verdictPass ?? ''
    case 'RAW':
      return styles.verdictRaw ?? ''
    case 'WFA_FAIL_DATA':
      return styles.verdictWarn ?? ''
    case 'WFA_FAIL':
    case 'FAIL':
    default:
      return styles.verdictFail ?? ''
  }
}

// ─── Row component ────────────────────────────────────────────────────────

function HistoryRow({ run }: { run: RunSummary }) {
  const req = run.request
  const m = run.metrics
  const isRaw = run.verdict === 'RAW'

  const strategy = (req.strategy_label || req.strategy_id || '').substring(0, 50)
  const symbol = req.symbol || '—'
  const tf = req.interval_label || req.interval || '—'
  const rangeStart = (req.start || '—').slice(0, 10)
  const rangeEnd = (req.end || '—').slice(-5)
  const range = `${rangeStart}…${rangeEnd}`

  // RAW: show envelope sharpe + n_trades + total_pnl_pct; WFA: show T1 + T5 + DSR
  const sharpeCell = isRaw ? fmt(m.sharpe ?? run.sharpe, 2) : fmt(m.t1_sharpe_oos, 2)
  const nTradesVal = isRaw ? (m.n_trades ?? run.n_trades) : m.t5_n_trades
  const pnlCell = isRaw
    ? `${fmt(m.total_pnl_pct ?? run.total_pnl_pct, 1)}%`
    : fmt(run.dsr, 3)
  const mcCell = isRaw ? '—' : fmt(run.mc_p_value, 3)

  return (
    <tr className={styles.row}>
      <td>{strategy}</td>
      <td>{symbol}</td>
      <td>{tf}</td>
      <td className={styles.rangeCell}>{range}</td>
      <td className={verdictCellClass(run.verdict)}>
        {run.verdict || '—'}{' '}
        <WfaFailBadge verdict={run.verdict} size="sm" />
      </td>
      <td>{sharpeCell}</td>
      <td>{nTradesVal != null ? nTradesVal : '—'}</td>
      <td>{pnlCell}</td>
      <td>{mcCell}</td>
    </tr>
  )
}

// ─── public component ────────────────────────────────────────────────────

export function HistoryTab() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api.getRuns()
      .then((data) => { if (!cancelled) setRuns(data) })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load history')
        }
      })
    return () => { cancelled = true }
  }, [])

  // Loading state
  if (runs === null && error === null) {
    return (
      <section className={styles.container}>
        <div className={styles.title}>▸ HISTORY</div>
        <p className={styles.stateMsg}>Loading history...</p>
      </section>
    )
  }

  // Error state
  if (error !== null) {
    return (
      <section className={styles.container}>
        <div className={styles.title}>▸ HISTORY</div>
        <p className={styles.stateMsgError}>Failed to load history</p>
      </section>
    )
  }

  const safeRuns = runs ?? []

  // Empty state
  if (safeRuns.length === 0) {
    return (
      <section className={styles.container}>
        <div className={styles.title}>▸ HISTORY</div>
        <p className={styles.emptyMsg}>NO RUNS · execute first backtest above</p>
      </section>
    )
  }

  return (
    <section className={styles.container}>
      <div className={styles.title}>▸ HISTORY · {safeRuns.length} RUNS</div>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>STRATEGY</th>
              <th>SYMBOL</th>
              <th>TF</th>
              <th>RANGE</th>
              <th>VERDICT</th>
              <th>SHARPE / T1</th>
              <th>N TRADES / T5</th>
              <th>PnL % / DSR</th>
              <th>MC P</th>
            </tr>
          </thead>
          <tbody>
            {safeRuns.map((run) => (
              <HistoryRow key={run.run_id} run={run} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
