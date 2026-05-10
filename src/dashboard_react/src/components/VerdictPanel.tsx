import type { BacktestResponse, Verdict, Warning } from '@/api/types'
import styles from './VerdictPanel.module.css'

interface VerdictPanelProps {
  result: BacktestResponse
}

// Maps Verdict union to CSS module class (non-null: keys guaranteed in .module.css)
function verdictClass(verdict: Verdict): string {
  switch (verdict) {
    case 'WFA_PASS':
    case 'PASS':
      return styles.verdictPass ?? ''
    case 'RAW':
      return styles.verdictRaw ?? ''
    case 'WFA_FAIL_DATA':
      return styles.verdictFailData ?? ''
    case 'WFA_FAIL':
    case 'FAIL':
    default:
      return styles.verdictFail ?? ''
  }
}

// Warning level → icon + CSS class
const WARNING_ICON: Record<Warning['level'], string> = {
  high: '⚠',
  warn: '▲',
  info: 'i',
}

function warningRowClass(level: Warning['level']): string {
  switch (level) {
    case 'high':
      return styles.warnHigh ?? ''
    case 'warn':
      return styles.warnMid ?? ''
    case 'info':
    default:
      return styles.warnInfo ?? ''
  }
}

// Three-valued WFA verdict display with warnings panel.
// Palette: Anthropic orange + cyberpunk neon — no terminal-green on PASS per ADR 0040 amendment.
export function VerdictPanel({ result }: VerdictPanelProps) {
  const { verdict, failed_criteria, warnings } = result

  return (
    <section className={styles.container}>
      {/* ── Verdict block ── */}
      <div className={styles.verdictBlock}>
        <div className={styles.verdictLabel}>▸ FINAL VERDICT</div>
        <div className={`${styles.verdictValue} ${verdictClass(verdict)}`}>
          {verdict}
        </div>

        {failed_criteria.length > 0 && (
          <div className={styles.failedRow}>
            <span className={styles.failedLabel}>FAILED CRITERIA:</span>
            {failed_criteria.map((criterion) => (
              <span key={criterion} className={styles.chip}>
                {criterion.toUpperCase()}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* ── Warnings panel — only when warnings present ── */}
      {warnings.length > 0 && (
        <div className={styles.warningsPanel}>
          <div className={styles.warningsTitle}>WARNINGS</div>
          {warnings.map((w, i) => (
            <div
              key={`${w.code}-${i}`}
              className={`${styles.warningRow} ${warningRowClass(w.level)}`}
            >
              <span className={styles.warnIcon} aria-hidden="true">
                {WARNING_ICON[w.level]}
              </span>
              <span className={styles.warnCode}>{w.code}</span>
              <span className={styles.warnMessage}>{w.message}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
