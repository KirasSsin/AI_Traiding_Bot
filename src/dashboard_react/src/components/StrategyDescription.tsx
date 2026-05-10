import { useState } from 'react'
import { useStrategyInfo } from '@/hooks/useStrategyInfo'
import styles from './StrategyDescription.module.css'

interface StrategyDescriptionProps {
  strategyId: string
}

// Collapsible strategy description block.
// Renders pre-authored HTML from STRATEGY_PRESETS (XSS-safe — server-controlled, not user input).
export function StrategyDescription({ strategyId }: StrategyDescriptionProps) {
  const [expanded, setExpanded] = useState(false)
  const { info, loading } = useStrategyInfo(strategyId)

  // Nothing to show while fetching
  if (loading && !info) return null

  const toggle = () => setExpanded((prev) => !prev)

  return (
    <section className={styles.container}>
      <button
        className={styles.toggleBtn}
        onClick={toggle}
        aria-expanded={expanded}
        type="button"
      >
        <span className={styles.arrow} aria-hidden="true">
          {expanded ? '▾' : '▸'}
        </span>
        <span className={styles.btnLabel}>Strategy Description</span>
      </button>

      {expanded && (
        <div className={styles.body}>
          {info?.description ? (
            // pre-authored HTML from STRATEGY_PRESETS dict — XSS-safe per vanilla comment line 235
            <div dangerouslySetInnerHTML={{ __html: info.description }} />
          ) : (
            <p className={styles.empty}>No description available.</p>
          )}
        </div>
      )}
    </section>
  )
}
