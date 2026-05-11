// HistoryTab — T15a: backtest run history table (self-contained, fetches /api/runs).
// Vanilla port: src/dashboard/static/dashboard.js lines 524-562 (loadHistory).
// 9-column table; RAW vs WFA cell logic per vanilla S42.3 + S44 T8.
// S48 T13: inline accordion expand — Bug H per FE design doc + architect C4.

import { useState, useEffect, useCallback, Fragment } from 'react'
import { api } from '@/api/client'
import type { RunSummary, BacktestResponse, Verdict } from '@/api/types'
import { WfaFailBadge } from '../shared/WfaFailBadge'
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

// ─── TradeStatsExtended — local interface для null-safe access to backend-added fields.
// Avoids breaking MetricsTable/TradesTable by extending shared TradeStats.
// Type tightening deferred to S49 carry-over.

interface TradeStatsExtended {
  n_winners?: number | null
  n_losers?: number | null
  total_pnl_pct?: number | null
  total_pnl_quote?: number | null
  total_commissions_quote?: number | null
  avg_win_quote?: number | null
  avg_loss_quote?: number | null
  profit_factor?: number | null
  initial_balance_quote?: number | null
  final_balance_quote?: number | null
  win_rate?: number
  n_trades?: number
}

// ─── RunDetailsPanel ──────────────────────────────────────────────────────

function renderSummary(details: BacktestResponse): string {
  const verdict = details.verdict
  const preset = details.request.strategy_label ?? details.request.strategy_id
  const failedCriteria = details.failed_criteria ?? []
  const winRate = ((details.trade_stats?.win_rate ?? 0) * 100).toFixed(1)
  const totalPnl = (details.total_pnl_pct ?? 0).toFixed(2)

  if (verdict === 'WFA_PASS' || verdict === 'PASS') {
    return (
      `Стратегия "${preset}" сработала: пройдены все обязательные acceptance gates. ` +
      `Win rate ${winRate}%, total PnL ${totalPnl}%. Strategy показала статистически значимый edge.`
    )
  }
  if (verdict === 'WFA_FAIL' || verdict === 'FAIL') {
    const primaryFailed = failedCriteria[0] ?? 'unknown'
    return (
      `Стратегия "${preset}" не прошла WFA discipline. Provoking criterion: ${primaryFailed}. ` +
      `Total PnL ${totalPnl}%, win rate ${winRate}%. ` +
      `Использовать в live НЕ рекомендуется — см. Glossary вкладку для деталей.`
    )
  }
  if (verdict === 'WFA_FAIL_DATA') {
    return (
      `Стратегия "${preset}" не прошла из-за недостатка данных (n_trades < 50 OR fold count < 5). ` +
      `Не статистически значимый результат. Требуется больше OOS sample data.`
    )
  }
  if (verdict === 'RAW') {
    return (
      `Стратегия "${preset}" — full-period backtest без WFA discipline. ` +
      `Total PnL ${totalPnl}%, win rate ${winRate}%. ` +
      `Подвержен look-ahead bias. Не basis для live decisions.`
    )
  }
  return `Verdict ${verdict ?? '—'}. Total PnL ${totalPnl}%.`
}

function RunDetailsPanel({ details }: { details: BacktestResponse }) {
  const ts = details.trade_stats as TradeStatsExtended
  const initialBalance = ts.initial_balance_quote ?? 10000
  const totalPnlPct = details.total_pnl_pct ?? 0
  const finalBalance = ts.final_balance_quote ?? initialBalance * (1 + totalPnlPct / 100)
  const winRate = (ts.win_rate ?? details.win_rate ?? 0) * 100
  const loseRate = 100 - winRate
  const pnlUsdt = finalBalance - initialBalance
  const profitFactor = ts.profit_factor

  const summary = renderSummary(details)

  return (
    <div className={styles.detailsBody}>
      <div className={styles.detailsGrid}>
        <div className={styles.detailItem}>
          <span className={styles.detailLabel}>Начальный баланс</span>
          <span className={styles.detailValue}>${initialBalance.toFixed(2)}</span>
        </div>
        <div className={styles.detailItem}>
          <span className={styles.detailLabel}>Итоговый баланс</span>
          <span className={styles.detailValue}>${finalBalance.toFixed(2)}</span>
        </div>
        <div className={styles.detailItem}>
          <span className={styles.detailLabel}>Win rate</span>
          <span className={styles.detailValue}>{winRate.toFixed(1)}%</span>
        </div>
        <div className={styles.detailItem}>
          <span className={styles.detailLabel}>Lose rate</span>
          <span className={styles.detailValue}>{loseRate.toFixed(1)}%</span>
        </div>
        <div className={styles.detailItem}>
          <span className={styles.detailLabel}>Total PnL</span>
          <span className={totalPnlPct >= 0 ? styles.detailValuePos : styles.detailValueNeg}>
            {totalPnlPct >= 0 ? '+' : ''}${pnlUsdt.toFixed(2)}{' '}
            ({totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%)
          </span>
        </div>
        {profitFactor !== null && profitFactor !== undefined && (
          <div className={styles.detailItem}>
            <span className={styles.detailLabel}>Profit Factor</span>
            <span className={styles.detailValue}>{profitFactor.toFixed(2)}</span>
          </div>
        )}
      </div>
      <hr className={styles.detailsDivider} />
      <p className={styles.summary}>{summary}</p>
    </div>
  )
}

// ─── public component ────────────────────────────────────────────────────

export function HistoryTab() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  // S48 T13 — accordion state (single-open per architect C4)
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null)
  const [expandedDetails, setExpandedDetails] = useState<Record<string, BacktestResponse>>({})
  const [expandError, setExpandError] = useState<Record<string, string>>({})

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

  // ESC closes expanded row (architect C4 spec)
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setExpandedRunId(null)
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [])

  // fetch-on-click, no TTL cache (architect C4)
  const handleRowClick = useCallback(async (runId: string) => {
    if (expandedRunId === runId) {
      setExpandedRunId(null)
      return
    }
    setExpandedRunId(runId)
    if (!(runId in expandedDetails) && !(runId in expandError)) {
      try {
        const details = await api.getRun(runId)
        setExpandedDetails((prev) => ({ ...prev, [runId]: details }))
      } catch (err) {
        setExpandError((prev) => ({
          ...prev,
          [runId]: err instanceof Error ? err.message : 'Fetch failed',
        }))
      }
    }
  }, [expandedRunId, expandedDetails, expandError])

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
              <th className={styles.toggleHeader}></th>
            </tr>
          </thead>
          <tbody>
            {safeRuns.map((run) => {
              const req = run.request
              const m = run.metrics
              const isRaw = run.verdict === 'RAW'
              const isExpanded = expandedRunId === run.run_id
              const details = expandedDetails[run.run_id]
              const err = expandError[run.run_id]

              const strategy = (req.strategy_label || req.strategy_id || '').substring(0, 50)
              const symbol = req.symbol || '—'
              const tf = req.interval_label || req.interval || '—'
              const rangeStart = (req.start || '—').slice(0, 10)
              const rangeEnd = (req.end || '—').slice(-5)
              const range = `${rangeStart}…${rangeEnd}`

              const sharpeCell = isRaw ? fmt(m.sharpe ?? run.sharpe, 2) : fmt(m.t1_sharpe_oos, 2)
              const nTradesVal = isRaw ? (m.n_trades ?? run.n_trades) : m.t5_n_trades
              const pnlCell = isRaw
                ? `${fmt(m.total_pnl_pct ?? run.total_pnl_pct, 1)}%`
                : fmt(run.dsr, 3)
              const mcCell = isRaw ? '—' : fmt(run.mc_p_value, 3)

              return (
                <Fragment key={run.run_id}>
                  <tr
                    className={`${styles.row ?? ''} ${isExpanded ? (styles.rowExpanded ?? '') : ''}`}
                    onClick={() => { void handleRowClick(run.run_id) }}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); void handleRowClick(run.run_id) } }}
                    aria-expanded={isExpanded}
                    aria-controls={`row-detail-${run.run_id}`}
                    role="button"
                    tabIndex={0}
                  >
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
                    <td className={styles.toggleIcon}>{isExpanded ? '▾' : '▸'}</td>
                  </tr>
                  {isExpanded && (
                    <tr
                      id={`row-detail-${run.run_id}`}
                      role="region"
                      aria-label="Run details"
                    >
                      <td colSpan={10}>
                        <div className={styles.expandPanel}>
                          <button
                            className={styles.closeButton}
                            onClick={(e) => { e.stopPropagation(); setExpandedRunId(null) }}
                            aria-label="Закрыть"
                            type="button"
                          >
                            ✕ закрыть
                          </button>
                          {err ? (
                            <div className={styles.errorMsg}>Ошибка: {err}</div>
                          ) : !details ? (
                            <div className={styles.loadingMsg}>Загрузка деталей...</div>
                          ) : (
                            <RunDetailsPanel details={details} />
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
