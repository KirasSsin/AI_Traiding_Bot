// FailAnalysisTab — S47 T15: RU detailed WHY-failed narrative для FAILED strategies.
// Visible ONLY когда verdict ∈ {WFA_FAIL, WFA_FAIL_DATA, FAIL}.
// 3 sections: full strategy description / per-criterion breakdown / per-fold table.

import { useEffect, useState } from 'react'
import type {
  BacktestResponse,
  CriterionExplanation,
  StrategyExplanation,
} from '@/api/types'
import { api } from '@/api/client'
import styles from './FailAnalysisTab.module.css'

interface FailAnalysisTabProps {
  result: BacktestResponse
}

export function FailAnalysisTab({ result }: FailAnalysisTabProps) {
  const [strategyDesc, setStrategyDesc] = useState<StrategyExplanation | null>(null)
  const [criterionMap, setCriterionMap] = useState<Record<string, CriterionExplanation> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      api.getStrategyExplanation(result.request.strategy_id),
      api.getCriterionExplanations(),
    ])
      .then(([sd, cm]) => {
        if (cancelled) return
        setStrategyDesc(sd)
        setCriterionMap(cm)
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
  if (strategyDesc === null || criterionMap === null) {
    return null
  }

  const failedCriteria: string[] = result.failed_criteria ?? []
  const folds: number[] = result.fold_sharpe_ratios ?? []
  const failedFolds = new Set<number>(result.failed_folds ?? [])

  const renderParagraph = (para: string, idx: number) => {
    // Render markdown-lite **bold** as <strong>
    const html = para.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    return <p key={idx} dangerouslySetInnerHTML={{ __html: html }} />
  }

  return (
    <div className={styles.container}>
      <div className={styles.title}>▸ ДЕТАЛЬНЫЙ РАЗБОР: ПОЧЕМУ СТРАТЕГИЯ НЕ ПРОШЛА</div>

      {/* Section 1 — full strategy description */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>1. Описание стратегии</h3>
        <div className={styles.descriptionBody}>
          {strategyDesc.description_ru.split('\n\n').map(renderParagraph)}
        </div>
      </section>

      {/* Section 2 — per-criterion breakdown */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>2. Анализ невыполненных критериев</h3>
        {failedCriteria.length === 0 ? (
          <p className={styles.empty}>
            Нет явных failed_criteria — vердикт {result.verdict} мог сработать через aggregate gate
            (например, недостаточно данных для WFA либо отсутствуют trades).
          </p>
        ) : (
          failedCriteria.map((critId) => {
            const exp = criterionMap[critId]
            if (exp === undefined) {
              return (
                <div key={critId} className={styles.criterionUnknown}>
                  Неизвестный критерий: {critId}
                </div>
              )
            }
            const metrics = result.metrics as Record<string, number | null | undefined> | undefined
            const actualRaw = metrics !== undefined ? metrics[critId] : undefined
            const actualValue: string =
              actualRaw === undefined || actualRaw === null
                ? '—'
                : typeof actualRaw === 'number'
                ? actualRaw.toFixed(4)
                : String(actualRaw)

            return (
              <article key={critId} className={styles.criterionCard}>
                <h4 className={styles.criterionName}>{exp.name}</h4>
                <div className={styles.criterionRow}>
                  <strong>Что измеряет:</strong> {exp.measures}
                </div>
                <div className={styles.criterionRow}>
                  <strong>Формула:</strong>
                  <pre className={styles.formula}>{exp.formula}</pre>
                </div>
                <div className={styles.criterionRow}>
                  <strong>Порог:</strong> {exp.threshold}
                </div>
                <div className={styles.criterionRow}>
                  <strong>Фактическое значение:</strong>{' '}
                  <span className={styles.actualValue}>{actualValue}</span>
                </div>
                <div className={styles.criterionRow}>
                  <strong>Почему fail:</strong> Значение не удовлетворяет порогу выше — см.
                  «Порог» и «Фактическое значение».
                </div>
                <div className={styles.criterionRow}>
                  <strong>На что влияет:</strong> {exp.impact}
                </div>
                <div className={styles.criterionRow}>
                  <strong>С чем связано:</strong> {exp.related}
                </div>
                <div className={styles.criterionRow}>
                  <strong>Роль в acceptance gate:</strong> {exp.gate_role}
                </div>
              </article>
            )
          })
        )}
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
