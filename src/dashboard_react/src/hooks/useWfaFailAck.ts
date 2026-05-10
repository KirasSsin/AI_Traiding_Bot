import { useEffect, useState } from 'react'

// S46 T5 — WFA_FAIL acknowledgment state per architect Q4 REVISE.
// Operator must explicit ack — banner non-dismissible.
// Count distinct calendar days; downgrade to compact chip after REQUIRED_DAYS distinct days OR ack today.
// Chip never disappears entirely (epistemic disclosure permanent).

const STORAGE_KEY = 'wfa_fail_ack_v1'
const REQUIRED_DAYS = 3

export interface AckState {
  count: number
  dates: string[]  // YYYY-MM-DD ISO strings
}

function loadState(): AckState {
  if (typeof localStorage === 'undefined') {
    return { count: 0, dates: [] }
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { count: 0, dates: [] }
    const parsed = JSON.parse(raw) as Partial<AckState>
    return {
      count: typeof parsed.count === 'number' ? parsed.count : 0,
      dates: Array.isArray(parsed.dates) ? parsed.dates.map(String) : [],
    }
  } catch {
    return { count: 0, dates: [] }
  }
}

function saveState(state: AckState): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // localStorage may be disabled OR full — silent fail OK
  }
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10)
}

export interface UseWfaFailAckResult {
  showFullBanner: boolean  // show full-width banner
  showChip: boolean        // show compact chip
  ackedTotal: number       // total ack count (for display)
  distinctDays: number     // distinct calendar days acked
  ack: () => void          // explicit acknowledgment action
  reset: () => void        // testing helper — clear state
}

export function useWfaFailAck(): UseWfaFailAckResult {
  const [state, setState] = useState<AckState>(loadState)

  // Re-evaluate on mount (in case other tabs modified storage)
  useEffect(() => {
    setState(loadState())
  }, [])

  const today = todayISO()
  const distinctDays = new Set(state.dates).size
  const downgradeDone = distinctDays >= REQUIRED_DAYS
  const ackedToday = state.dates.includes(today)

  // Full banner shows if operator not yet downgraded AND not acked today
  const showFullBanner = !downgradeDone && !ackedToday
  // Chip shows everywhere else (always visible after first ack OR after downgrade)
  const showChip = !showFullBanner

  const ack = (): void => {
    const newDates = state.dates.includes(today) ? state.dates : [...state.dates, today]
    const newState: AckState = {
      count: state.count + 1,
      dates: newDates,
    }
    saveState(newState)
    setState(newState)
  }

  const reset = (): void => {
    saveState({ count: 0, dates: [] })
    setState({ count: 0, dates: [] })
  }

  return {
    showFullBanner,
    showChip,
    ackedTotal: state.count,
    distinctDays,
    ack,
    reset,
  }
}
