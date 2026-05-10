// WfaFailBadge — T16: inline pill badge for WFA_FAIL / WFA_FAIL_DATA / FAIL verdicts.
// Renders null for non-fail verdicts (WFA_PASS, PASS, RAW).

import type { Verdict } from '@/api/types'
import styles from './WfaFailBadge.module.css'

interface WfaFailBadgeProps {
  verdict: Verdict | null | undefined
  size?: 'sm' | 'md'
}

export function WfaFailBadge({ verdict, size = 'sm' }: WfaFailBadgeProps) {
  if (!verdict) return null

  // WFA_FAIL_DATA → amber/warning style with distinct label
  if (verdict === 'WFA_FAIL_DATA') {
    return (
      <span className={`${styles.badge} ${styles.warn} ${styles[size]}`}>
        WFA FAIL · DATA
      </span>
    )
  }

  // WFA_FAIL or FAIL → red danger style
  if (verdict === 'WFA_FAIL' || verdict === 'FAIL') {
    return (
      <span className={`${styles.badge} ${styles.fail} ${styles[size]}`}>
        WFA FAIL
      </span>
    )
  }

  // WFA_PASS, PASS, RAW → no badge
  return null
}
