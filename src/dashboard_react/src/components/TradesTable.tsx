// TradesTable — T14: trade statistics panel, RAW + WFA paths.
// Vanilla port: src/dashboard/static/dashboard.js lines 454-501.
// RAW: 5 rows (win/loss counts, win rate, total PnL, deferred note).
// WFA: 8 rows with quote-currency amounts from trade_stats envelope.

import type { BacktestResponse } from '@/api/types'
import styles from './TradesTable.module.css'

interface TradesTableProps {
  result: BacktestResponse
}

// ─── helpers ─────────────────────────────────────────────────────────────

type Nullish = number | null | undefined

function fmt(value: Nullish, digits: number): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

function fmtPct(value: Nullish, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

// Thousands-separated money с 2 decimal places; fallback '—' if null/undefined.
function fmtMoney(value: Nullish): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ─── RAW path (research presets) ─────────────────────────────────────────

function RawTradesTable({ result }: TradesTableProps) {
  const m = result.metrics
  const r = result

  const totalPnl: Nullish = m.total_pnl_pct ?? r.total_pnl_pct
  const winR: Nullish = m.win_rate ?? r.win_rate
  const nTr: number = m.n_trades ?? r.n_trades ?? 0
  const nWin: number | null = winR != null && nTr ? Math.round(nTr * winR) : null
  const nLos: number | null = nWin != null ? nTr - nWin : null

  const pnlCls = totalPnl != null && totalPnl > 0 ? styles.metricPass : styles.metricFail

  return (
    <section className={styles.container}>
      <div className={styles.title}>▸ TRADE STATISTICS</div>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>STAT</th>
            <th>VALUE</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Profitable trades</td>
            <td className={styles.metricPass ?? ''}>{nWin ?? '—'}</td>
          </tr>
          <tr>
            <td>Losing trades</td>
            <td className={styles.metricFail ?? ''}>{nLos ?? '—'}</td>
          </tr>
          <tr>
            <td>Win rate</td>
            <td>{fmtPct(winR)}</td>
          </tr>
          <tr>
            <td>Total PnL %</td>
            <td className={pnlCls ?? ''}>{fmt(totalPnl, 2)}%</td>
          </tr>
          <tr>
            <td colSpan={2} className={styles.footerNote}>
              ▸ Quote-currency stats (USDT amounts, profit factor, avg win/loss) deferred к S43 WFA retrofit
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  )
}

// ─── WFA path (replay engine) ─────────────────────────────────────────────

function WfaTradesTable({ result }: TradesTableProps) {
  const m = result.metrics
  const ts = result.trade_stats

  return (
    <section className={styles.container}>
      <div className={styles.title}>▸ TRADE STATISTICS</div>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>STAT</th>
            <th>VALUE</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Profitable trades</td>
            <td className={styles.metricPass ?? ''}>{ts.n_winners ?? '—'}</td>
          </tr>
          <tr>
            <td>Losing trades</td>
            <td className={styles.metricFail ?? ''}>{ts.n_losers ?? '—'}</td>
          </tr>
          <tr>
            <td>Win rate</td>
            <td>{fmtPct(m.t4_win_rate)}</td>
          </tr>
          <tr>
            <td>Total PnL</td>
            <td>{fmtMoney(ts.total_pnl_quote)} USDT</td>
          </tr>
          <tr>
            <td>Total Commissions</td>
            <td>{fmtMoney(ts.total_commissions_quote)} USDT</td>
          </tr>
          <tr>
            <td>Avg Win</td>
            <td>{fmtMoney(ts.avg_win_quote)} USDT</td>
          </tr>
          <tr>
            <td>Avg Loss</td>
            <td>{fmtMoney(ts.avg_loss_quote)} USDT</td>
          </tr>
          <tr>
            <td>Profit Factor</td>
            <td>{fmt(ts.profit_factor, 2)}</td>
          </tr>
        </tbody>
      </table>
    </section>
  )
}

// ─── public component ────────────────────────────────────────────────────

export function TradesTable({ result }: TradesTableProps) {
  if (result.verdict === 'RAW') {
    return <RawTradesTable result={result} />
  }
  return <WfaTradesTable result={result} />
}
