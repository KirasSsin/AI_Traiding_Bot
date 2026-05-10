// MetricsTable — TIER 1-T6 + DSR + MC acceptance gate (WFA path) + RAW reduced view
// Faithful port из vanilla src/dashboard/static/dashboard.js строк 432-513.
// BUG PARITY priority over improvement: thresholds + null/undefined handling точно как vanilla.
// References: ADR 0014 (acceptance gates), Bailey 2014 (DSR + n≥100 sample size).

import type { BacktestResponse } from '@/api/types'
import styles from './MetricsTable.module.css'

interface MetricsTableProps {
  result: BacktestResponse
}

// ─── helpers ─────────────────────────────────────────────────────────────

// `Record<string, number>` access под noUncheckedIndexedAccess даёт `number | undefined`.
// Vanilla code сравнивает `=== null` и `< threshold` — undefined trips comparisons как NaN.
// Унифицируем: null | undefined → null. Нумерик passes through.
type Nullish = number | null | undefined

function fmt(value: Nullish, digits: number): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

function fmtPct(value: Nullish, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

// Threshold cell class: `>=` PASS если val >= threshold; `<` PASS если val < threshold.
// null/undefined → FAIL (vanilla parity).
function cellCls(value: Nullish, threshold: number, op: '>=' | '<' = '>='): string {
  if (value === null || value === undefined) return styles.metricFail ?? ''
  const passes = op === '>=' ? value >= threshold : value < threshold
  return passes ? (styles.metricPass ?? '') : (styles.metricFail ?? '')
}

// ─── RAW path (research presets — atr_breakout/volume_breakout) ──────────
// Reduced 4-row table, no T1-T6/DSR/MC — see RAW_FULL_PERIOD warning + S43 retrofit note.

function RawMetricsTable({ result }: MetricsTableProps) {
  const m = result.metrics
  const totalPnl: Nullish = m.total_pnl_pct ?? result.total_pnl_pct
  const sharpeVal: Nullish = m.sharpe ?? result.sharpe
  const nTr: number = m.n_trades ?? result.n_trades ?? 0
  const winR: Nullish = m.win_rate ?? result.win_rate

  const totalPnlCls =
    totalPnl !== null && totalPnl !== undefined && totalPnl > 0
      ? styles.metricPass ?? ''
      : styles.metricFail ?? ''

  const sharpeCls =
    sharpeVal !== null && sharpeVal !== undefined && sharpeVal >= 1
      ? styles.metricPass ?? ''
      : styles.metricWarn ?? ''

  return (
    <section className={styles.container}>
      <div className={styles.title}>▸ ACCEPTANCE GATE METRICS</div>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>METRIC</th>
            <th>VALUE</th>
            <th>NOTE</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Total PnL</td>
            <td className={totalPnlCls}>
              <strong>{fmt(totalPnl, 2)}%</strong>
            </td>
            <td>Full-period training (no WFA OOS split)</td>
          </tr>
          <tr>
            <td>Sharpe (annualized)</td>
            <td className={sharpeCls}>{fmt(sharpeVal, 4)}</td>
            <td>per-trade Sharpe × √(bars/year ÷ mean_holding)</td>
          </tr>
          <tr>
            <td>Trade count (n)</td>
            <td>{nTr}</td>
            <td>Full-period (no train/test split)</td>
          </tr>
          <tr>
            <td>Win rate</td>
            <td>{fmtPct(winR)}</td>
            <td>—</td>
          </tr>
          <tr>
            <td colSpan={3} className={styles.footerNote}>
              ▸ T1-T6 / DSR / MC acceptance gates skipped — see RAW_FULL_PERIOD
              warning above (WFA retrofit pending S43)
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  )
}

// ─── WFA path (replay engine — ema_crossover/mean_reversion/donchian) ────

function WfaMetricsTable({ result }: MetricsTableProps) {
  const m = result.metrics

  // Pull metric values (Record<string, number> → number | undefined под noUncheckedIndexedAccess).
  const t1: Nullish = m.t1_sharpe_oos
  const t2: Nullish = m.t2_sortino_oos
  // Anomaly guard flag — Record<string, number> stores 0/1; truthy check matches vanilla.
  const t2Guard: boolean = Boolean(m.t2_sortino_anomaly_guard)
  const t3: Nullish = m.t3_max_drawdown
  const t4Wr: Nullish = m.t4_win_rate
  const t4Rr: Nullish = m.t4_avg_rr
  const t5n: Nullish = m.t5_n_trades
  const t5Mean: Nullish = m.t5_mean_pnl_pct
  const t5T: Nullish = m.t5_t_stat
  const t6: Nullish = m.t6_oos_is_sharpe_ratio_mean

  // T1 — Sharpe OOS: null/<1 FAIL; >3 OVERFIT? warn; else PASS
  const t1Cls =
    t1 === null || t1 === undefined
      ? styles.metricFail ?? ''
      : t1 > 3
        ? styles.metricWarn ?? ''
        : t1 >= 1
          ? styles.metricPass ?? ''
          : styles.metricFail ?? ''
  const t1Status =
    t1 === null || t1 === undefined || t1 < 1
      ? 'FAIL'
      : t1 > 3
        ? 'OVERFIT?'
        : 'PASS'

  // T2 — Sortino OOS: anomaly guard → N/A + GUARD (warn); else cellCls(t2, 1.5)
  const t2Cls = t2Guard ? styles.metricWarn ?? '' : cellCls(t2, 1.5)
  const t2Status = t2Guard
    ? 'GUARD'
    : t2 === null || t2 === undefined || t2 < 1.5
      ? 'FAIL'
      : 'PASS'

  // T3 — Max Drawdown: PASS если < 0.25; null OR >= 0.25 → FAIL
  const t3Cls = cellCls(t3, 0.25, '<')
  const t3Status =
    t3 === null || t3 === undefined || t3 >= 0.25 ? 'FAIL' : 'PASS'

  // T5 n trades — vanilla parity: undefined < 100 = false → PASS (sic). Match exactly.
  const t5nCls =
    t5n !== null && t5n !== undefined && t5n < 100
      ? styles.metricFail ?? ''
      : styles.metricPass ?? ''
  const t5nStatus =
    t5n !== null && t5n !== undefined && t5n < 100 ? 'FAIL' : 'PASS'

  // T5 mean PnL — null OR <=0 → FAIL
  const t5MeanCls =
    t5Mean === null || t5Mean === undefined || t5Mean <= 0
      ? styles.metricFail ?? ''
      : styles.metricPass ?? ''
  const t5MeanStatus =
    t5Mean === null || t5Mean === undefined || t5Mean <= 0 ? 'FAIL' : 'PASS'

  // T5 t-stat — cellCls(>=2)
  const t5TCls = cellCls(t5T, 2.0)
  const t5TStatus =
    t5T === null || t5T === undefined || t5T < 2 ? 'FAIL' : 'PASS'

  // T6 — OOS/IS ratio: cellCls(>=0.7)
  const t6Cls = cellCls(t6, 0.7)
  const t6Status =
    t6 === null || t6 === undefined || t6 < 0.7 ? 'FAIL' : 'PASS'

  // DSR — explicit dsr_pass boolean drives both cells
  const dsrCls = result.dsr_pass
    ? styles.metricPass ?? ''
    : styles.metricFail ?? ''
  const dsrStatus = result.dsr_pass ? 'PASS' : 'FAIL'

  // MC — value cell tri-color (PASS / WARN / FAIL); status cell binary (PASS if ≤0.05 else FAIL).
  // Vanilla parity: null/undefined mc_p_value → FAIL pure (no WARN).
  const mc = result.mc_p_value
  const mcCls =
    mc !== null && mc !== undefined && mc <= 0.05
      ? styles.metricPass ?? ''
      : mc !== null && mc !== undefined && mc > 0.10
        ? styles.metricFail ?? ''
        : mc !== null && mc !== undefined
          ? styles.metricWarn ?? ''
          : styles.metricFail ?? ''
  const mcStatusCls =
    mc !== null && mc !== undefined && mc <= 0.05
      ? styles.metricPass ?? ''
      : styles.metricFail ?? ''
  const mcStatus =
    mc !== null && mc !== undefined && mc <= 0.05 ? 'PASS' : 'FAIL'

  return (
    <section className={styles.container}>
      <div className={styles.title}>▸ ACCEPTANCE GATE METRICS</div>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>METRIC</th>
            <th>VALUE</th>
            <th>THRESHOLD</th>
            <th>STATUS</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>T1 · Sharpe OOS (annualized)</td>
            <td className={t1Cls}>{fmt(t1, 2)}</td>
            <td>{'≥ 1.0 (>3.0 = overfit)'}</td>
            <td className={t1Cls}>{t1Status}</td>
          </tr>
          <tr>
            <td>T2 · Sortino OOS</td>
            <td className={t2Cls}>{t2Guard ? 'N/A' : fmt(t2, 2)}</td>
            <td>≥ 1.5</td>
            <td className={t2Cls}>{t2Status}</td>
          </tr>
          <tr>
            <td>T3 · Max Drawdown</td>
            <td className={t3Cls}>{fmtPct(t3)}</td>
            <td>{'< 25%'}</td>
            <td className={t3Cls}>{t3Status}</td>
          </tr>
          <tr>
            <td>T4 · Win rate</td>
            <td>{fmtPct(t4Wr)}</td>
            <td>≥ 45%@RR≥1.5 OR ≥ 35%@RR≥2</td>
            <td>—</td>
          </tr>
          <tr>
            <td>T4 · Avg RR</td>
            <td>{fmt(t4Rr, 2)}</td>
            <td>—</td>
            <td>—</td>
          </tr>
          <tr className={styles.boldRow}>
            <td>
              <strong>T5 · Trade count (n)</strong>
            </td>
            <td className={t5nCls}>
              <strong>{t5n ?? '—'}</strong>
            </td>
            <td>≥ 100 (Bailey 2014)</td>
            <td className={t5nCls}>{t5nStatus}</td>
          </tr>
          <tr>
            <td>T5 · Mean PnL %</td>
            <td className={t5MeanCls}>{fmtPct(t5Mean, 4)}</td>
            <td>{'> 0'}</td>
            <td className={t5MeanCls}>{t5MeanStatus}</td>
          </tr>
          <tr>
            <td>T5 · t-stat</td>
            <td className={t5TCls}>{fmt(t5T, 2)}</td>
            <td>≥ 2.0</td>
            <td className={t5TCls}>{t5TStatus}</td>
          </tr>
          <tr>
            <td>T6 · OOS/IS Sharpe ratio mean</td>
            <td className={t6Cls}>{fmt(t6, 2)}</td>
            <td>≥ 0.7 (overfit detector)</td>
            <td className={t6Cls}>{t6Status}</td>
          </tr>
          <tr>
            <td>DSR · Deflated Sharpe Ratio</td>
            <td className={dsrCls}>{fmt(result.dsr, 4)}</td>
            <td>{'> 0'}</td>
            <td className={dsrCls}>{dsrStatus}</td>
          </tr>
          <tr>
            <td>MC · p-value (sign-flip)</td>
            <td className={mcCls}>{fmt(mc, 4)}</td>
            <td>≤ 0.05</td>
            <td className={mcStatusCls}>{mcStatus}</td>
          </tr>
        </tbody>
      </table>

      <FoldsSubtable result={result} />
    </section>
  )
}

// ─── Per-fold Sharpe subtable (WFA path only; skipped if empty) ──────────

function FoldsSubtable({ result }: MetricsTableProps) {
  const folds = result.fold_sharpe_ratios
  if (!folds || folds.length === 0) return null
  const failed = new Set(result.failed_folds)

  return (
    <>
      <div className={styles.foldsTitle}>▸ PER-FOLD SHARPE RATIOS</div>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>FOLD</th>
            <th>SHARPE RATIO</th>
            <th>STATUS</th>
          </tr>
        </thead>
        <tbody>
          {folds.map((s, i) => {
            const isFailed = failed.has(i)
            const cls = isFailed
              ? styles.metricFail ?? ''
              : s >= 0.7
                ? styles.metricPass ?? ''
                : styles.metricWarn ?? ''
            const status = isFailed ? '✗ < 0.7' : '✓'
            return (
              <tr key={i}>
                <td>#{i}</td>
                <td className={cls}>{fmt(s, 4)}</td>
                <td className={cls}>{status}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </>
  )
}

// ─── public component ────────────────────────────────────────────────────

export function MetricsTable({ result }: MetricsTableProps) {
  if (result.verdict === 'RAW') {
    return <RawMetricsTable result={result} />
  }
  return <WfaMetricsTable result={result} />
}
