// WfaFailBanner — T17: ack-gated NON-dismissible banner per architect Q4 REVISE.
// Three modes: full banner (unacknowledged) → chip (after 3 distinct days) → null (never).
// All user-facing strings in Russian per repo language rules.

import { useState } from 'react'
import { useWfaFailAck } from '@/hooks/useWfaFailAck'
import styles from './WfaFailBanner.module.css'

export function WfaFailBanner() {
  const { showFullBanner, showChip, ackedTotal, distinctDays, ack } = useWfaFailAck()
  const [ackJustDone, setAckJustDone] = useState(false)

  // Neither mode active — safety guard (should not happen with current hook semantics)
  if (!showFullBanner && !showChip) return null

  // ─── Chip mode: permanent compact reminder after 3 distinct ack days ──────
  if (showChip) {
    return (
      <div className={styles.chip} role="status" aria-label="WFA честный вердикт S45">
        ⚠ WFA discipline: 0/11 presets · S45 honest
      </div>
    )
  }

  // ─── Full banner: requires explicit operator acknowledgment ───────────────
  const handleAck = () => {
    ack()
    setAckJustDone(true)
    // Brief "confirmed" state — button disabled, then hook state transitions naturally
    setTimeout(() => setAckJustDone(false), 1500)
  }

  return (
    <div className={styles.banner} role="alert" aria-live="assertive">
      {/* Icon column */}
      <div className={styles.iconCol} aria-hidden="true">⚠</div>

      {/* Text body */}
      <div className={styles.textBody}>
        <div className={styles.bannerTitle}>ВНИМАНИЕ · S45 HONEST VERDICT</div>
        <p className={styles.bannerBody}>
          Все 11 стратегий не прошли WFA discipline (S45 final). Подтверди понимание
          перед использованием preset для live или paper trading.
        </p>
        <p className={styles.bannerMeta}>
          Ack count: {ackedTotal} · Distinct days: {distinctDays}/3
        </p>
      </div>

      {/* CTA column — only ack progresses state; no dismiss/close affordance */}
      <div className={styles.ctaCol}>
        <button
          className={styles.ackBtn}
          onClick={handleAck}
          disabled={ackJustDone}
          aria-label="Подтвердить понимание WFA вердикта"
        >
          {ackJustDone ? '✓ Подтверждено' : '▸ Я ПОНИМАЮ'}
        </button>
      </div>
    </div>
  )
}
