// FailAnalysisTab — S47 T15: RU detailed WHY-failed narrative для FAILED strategies.
// Visible ONLY когда verdict ∈ {WFA_FAIL, WFA_FAIL_DATA, FAIL}.
// 3 sections: full strategy description / per-criterion chip list / per-fold table.
// S48 T11: section 2 упрощена к chip list — fixes "Неизвестный критерий: t1" (Bug F).

import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type {
  BacktestResponse,
  StrategyExplanation,
} from '@/api/types'
import { api } from '@/api/client'
import styles from './FailAnalysisTab.module.css'

// S48 T11 — canonical criterion list across both backend paths (replay + research)
// Per ADR 0014: gate-blocking + informational. Glossary вкладка provides детали.
const ALL_CRITERIA = [
  // Gate-blocking
  't5_floor', 'sharpe_gate', 'mc_gate', 'dsr_threshold', 'n_eff_threshold',
  // Informational
  't1', 't2', 't3', 't4', 't6',
]

const HUMAN_READABLE: Record<string, string> = {
  t5_floor: 'T5 · Trade count (gate-blocking)',
  sharpe_gate: 'Fold OOS/IS Sharpe (gate-blocking)',
  mc_gate: 'Monte Carlo p-value (gate-blocking)',
  dsr_threshold: 'DSR (gate-blocking)',
  n_eff_threshold: 'Effective sample size (gate-blocking)',
  t1: 'T1 · Sharpe OOS (informational)',
  t2: 'T2 · Sortino OOS (informational)',
  t3: 'T3 · Max Drawdown (informational)',
  t4: 'T4 · Win Rate (informational)',
  t6: 'T6 · OOS/IS Sharpe ratio (informational)',
}

// Safe markdown-bold renderer без dangerouslySetInnerHTML.
// Splits text on **...** markers; even-indexed segments = plain text, odd = bold.
function renderBoldMarkdown(text: string): ReactNode[] {
  const parts = text.split(/\*\*(.+?)\*\*/g)
  return parts.map((part, i) =>
    i % 2 === 0 ? part : <strong key={i}>{part}</strong>
  )
}

interface FailAnalysisTabProps {
  result: BacktestResponse
}

export function FailAnalysisTab({ result }: FailAnalysisTabProps) {
  const [strategyDesc, setStrategyDesc] = useState<StrategyExplanation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api.getStrategyExplanation(result.request.strategy_id)
      .then((sd) => {
        if (cancelled) return
        setStrategyDesc(sd)
        setLoading(false)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setError(err.message)
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [result.request.strategy_id])

  if (loading) {
    return <div className={styles.loading}>Загрузка детального разбора...</div>
  }
  if (error !== null) {
    return <div className={styles.error}>Ошибка загрузки: {error}</div>
  }
  if (strategyDesc === null) {
    return null
  }

  const failedCriteria: string[] = result.failed_criteria ?? []
  const folds: number[] = result.fold_sharpe_ratios ?? []
  const failedFolds = new Set<number>(result.failed_folds ?? [])

  return (
    <div className={styles.container}>
      <div className={styles.title}>▸ ДЕТАЛЬНЫЙ РАЗБОР: ПОЧЕМУ СТРАТЕГИЯ НЕ ПРОШЛА</div>

      {/* Section 1 — full strategy description */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>1. Описание стратегии</h3>
        <div className={styles.descriptionBody}>
          {strategyDesc.description_ru.split('\n\n').map((para, i) => (
            <p key={i}>{renderBoldMarkdown(para)}</p>
          ))}
        </div>
      </section>

      {/* Section 2 — per-criterion breakdown — S48 T11 simplified к chip list */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>2. Применимость критериев</h3>
        <ul className={styles.criteriaList}>
          {ALL_CRITERIA.map((critId) => {
            const isFailed = failedCriteria.includes(critId)
            const chipClass = isFailed ? styles.chipUsed : styles.chipNotUsed
            const chipText = isFailed ? '✓ Используется' : '✗ Не используется'
            const glossaryLink = `?strategy=${encodeURIComponent(result.request.strategy_id)}#glossary-${critId}`
            return (
              <li key={critId} className={styles.criterionRow}>
                <span className={styles.criterionName}>{HUMAN_READABLE[critId] ?? critId}</span>
                <span className={chipClass}>{chipText}</span>
                <a href={glossaryLink} className={styles.glossaryLink}>→ glossary</a>
              </li>
            )
          })}
        </ul>
      </section>

      {/* Section 3 — per-fold breakdown (WFA path) */}
      {folds.length > 0 && (
        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>3. Разбор по фолдам walk-forward</h3>
          <table className={styles.foldsTable}>
            <thead>
              <tr>
                <th>Фолд</th>
                <th>OOS/IS Sharpe</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {folds.map((s, i) => {
                const isFailed = failedFolds.has(i)
                const cls = isFailed
                  ? styles.foldFail
                  : s >= 0.7
                  ? styles.foldPass
                  : styles.foldWarn
                const status = isFailed
                  ? '✗ < 0.7 (фолд failed)'
                  : s >= 0.7
                  ? '✓ ≥ 0.7'
                  : '⚠ low'
                return (
                  <tr key={i}>
                    <td>#{i}</td>
                    <td className={cls}>{s.toFixed(4)}</td>
                    <td className={cls}>{status}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}
