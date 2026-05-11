// BalanceBadge — S48 T21. Visual states для useBybitBalance hook.

import styles from './BalanceBadge.module.css'

interface BalanceBadgeProps {
  source: string
  balance: number
  loading: boolean
  error: string | null
}

export function BalanceBadge({ source, balance, loading, error }: BalanceBadgeProps) {
  if (loading) {
    return (
      <div className={`${styles.badge} ${styles.badgeLoading}`}>
        <span className={styles.dot}>◌</span> Fetching balance…
      </div>
    )
  }
  if (source === 'bybit_v5') {
    return (
      <div className={`${styles.badge} ${styles.badgeLive}`}>
        <span className={styles.dot}>●</span> LIVE · Bybit V5
      </div>
    )
  }
  if (source === 'cached') {
    return (
      <div className={`${styles.badge} ${styles.badgeCached}`}>
        <span className={styles.dot}>◐</span> CACHED · last known
      </div>
    )
  }
  // fallback
  return (
    <div className={`${styles.badge} ${styles.badgeFallback}`} title={error ?? 'No API keys'}>
      <span className={styles.dot}>⚠</span> OFFLINE — fallback ${balance.toFixed(0)}
    </div>
  )
}
