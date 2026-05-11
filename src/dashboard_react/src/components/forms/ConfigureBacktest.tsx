import { useEffect, useMemo, useState } from 'react'
import { api, ApiError } from '@/api/client'
import { useStrategyInfo } from '@/hooks/useStrategyInfo'
import { useStrategyContext } from '@/hooks/useStrategyContext'
import { useBybitBalance } from '@/hooks/useBybitBalance'
import { BalanceBadge } from '@/components/shared/BalanceBadge'
import type {
  BacktestRequest,
  BacktestResponse,
  DataAvailability,
  IntervalLabel,
  StrategyMetadata,
} from '@/api/types'
import styles from './ConfigureBacktest.module.css'

const OPTGROUP_ORDER = ['Тренд-следование', 'Возврат к среднему', 'Прорывы']

interface ConfigureBacktestProps {
  onResult: (result: BacktestResponse, initialBalance: number) => void
}

export function ConfigureBacktest({ onResult }: ConfigureBacktestProps) {
  const [strategies, setStrategies] = useState<Record<string, StrategyMetadata>>({})
  const [intervals, setIntervals] = useState<IntervalLabel[]>([])
  const [availability, setAvailability] = useState<DataAvailability>({})
  const [strategyId, setStrategyId] = useState<string>('')
  const [symbol, setSymbol] = useState<string>('')
  const [interval, setInterval] = useState<string>('')
  const [start, setStart] = useState<string>('2023-01-01')
  const [end, setEnd] = useState<string>('2026-04-26')
  const [force, setForce] = useState<boolean>(false)
  const [initialBalance, setInitialBalance] = useState<number>(10000)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { setCurrentStrategy } = useStrategyContext()
  const { balance: bybitBalance, source, loading: balLoading, error: balError } = useBybitBalance()

  // Sync initialBalance from Bybit once loaded
  useEffect(() => {
    if (!balLoading && bybitBalance > 0) {
      setInitialBalance(bybitBalance)
    }
  }, [balLoading, bybitBalance])

  // Strategy info with supported_combos for gating
  const { info: strategyInfo } = useStrategyInfo(strategyId || null)

  // Initial load
  useEffect(() => {
    let cancelled = false
    Promise.all([api.getStrategies(), api.getIntervals(), api.getDataAvailability()])
      .then(([strats, ivs, avail]) => {
        if (cancelled) return
        setStrategies(strats)
        setIntervals(ivs)
        setAvailability(avail)
        const firstId = Object.keys(strats)[0]
        if (firstId) setStrategyId(firstId)
        const firstSym = Object.keys(avail).sort()[0]
        if (firstSym) setSymbol(firstSym)
        const firstIv = ivs[0]?.id
        if (firstIv) setInterval(firstIv)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setSubmitError(err instanceof Error ? err.message : String(err))
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Group strategies by optgroup (port S43 pattern)
  const groupedStrategies = useMemo(() => {
    const grouped: Record<string, { id: string; label: string }[]> = {}
    for (const [id, meta] of Object.entries(strategies)) {
      const group = meta.optgroup || 'Прочие'
      if (!grouped[group]) grouped[group] = []
      grouped[group].push({ id, label: meta.label })
    }
    return grouped
  }, [strategies])

  const orderedGroups = useMemo(() => {
    const known = OPTGROUP_ORDER.filter((g) => groupedStrategies[g])
    const extras = Object.keys(groupedStrategies).filter((g) => !OPTGROUP_ORDER.includes(g))
    return [...known, ...extras]
  }, [groupedStrategies])

  // Combo gating — disabled options based on strategyInfo
  const { disabledSymbols, disabledIntervals } = useMemo(() => {
    if (!strategyInfo) return { disabledSymbols: new Set<string>(), disabledIntervals: new Set<string>() }

    // Legacy locked single combo (S39 pattern)
    if (strategyInfo.locked_symbol || strategyInfo.locked_interval) {
      const allSyms = new Set(Object.keys(availability))
      const allIvs = new Set(intervals.map((i) => i.id))
      const disabledSym = new Set<string>()
      const disabledIv = new Set<string>()
      if (strategyInfo.locked_symbol) {
        for (const s of allSyms) if (s !== strategyInfo.locked_symbol) disabledSym.add(s)
      }
      if (strategyInfo.locked_interval) {
        for (const i of allIvs) if (i !== strategyInfo.locked_interval) disabledIv.add(i)
      }
      return { disabledSymbols: disabledSym, disabledIntervals: disabledIv }
    }

    // Multi-combo gate (S42 pattern)
    const supported = strategyInfo.supported_combos
    if (!supported || supported.length === 0) {
      return { disabledSymbols: new Set<string>(), disabledIntervals: new Set<string>() }
    }
    const validSyms = new Set(supported.map(([s]) => s))
    const allSyms = new Set(Object.keys(availability))
    const disabledSym = new Set<string>()
    for (const s of allSyms) if (!validSyms.has(s)) disabledSym.add(s)

    // For current symbol — valid intervals
    const validIvsForSym = new Set(supported.filter(([s]) => s === symbol).map(([, i]) => i))
    const allIvs = new Set(intervals.map((i) => i.id))
    const disabledIv = new Set<string>()
    for (const i of allIvs) {
      if (validIvsForSym.size > 0) {
        if (!validIvsForSym.has(i)) disabledIv.add(i)
      }
    }
    return { disabledSymbols: disabledSym, disabledIntervals: disabledIv }
  }, [strategyInfo, symbol, availability, intervals])

  // Auto-correct symbol/interval if disabled by combo gate
  useEffect(() => {
    if (symbol && disabledSymbols.has(symbol)) {
      const validSym = Object.keys(availability).find((s) => !disabledSymbols.has(s))
      if (validSym) setSymbol(validSym)
    }
  }, [disabledSymbols, symbol, availability])

  useEffect(() => {
    if (interval && disabledIntervals.has(interval)) {
      const validIv = intervals.find((i) => !disabledIntervals.has(i.id))
      if (validIv) setInterval(validIv.id)
    }
  }, [disabledIntervals, interval, intervals])

  // Data availability info for selected symbol+interval
  const dataInfo = useMemo(() => {
    if (!symbol || !interval) return null
    return availability[symbol]?.[interval] ?? null
  }, [symbol, interval, availability])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError(null)
    const payload: BacktestRequest = {
      strategy_id: strategyId,
      symbol,
      interval,
      start,
      end,
      force,
      initial_balance: initialBalance,
    }
    try {
      const result = await api.runBacktest(payload)
      onResult(result, initialBalance)
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.detail : String(err)
      setSubmitError(`Backtest error:\n${msg}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={styles.panel}>
      <div className={styles.panelLabel}>&gt; CONFIGURE_BACKTEST</div>
      <form onSubmit={handleSubmit} className={styles.grid}>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>STRATEGY</span>
          <select
            value={strategyId}
            onChange={(e) => { setStrategyId(e.target.value); setCurrentStrategy(e.target.value) }}
            className={styles.select}
          >
            {orderedGroups.map((group) => (
              <optgroup key={group} label={group}>
                {groupedStrategies[group]!.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span className={styles.fieldLabel}>SYMBOL</span>
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className={styles.select}
          >
            {Object.keys(availability).sort().map((s) => (
              <option key={s} value={s} disabled={disabledSymbols.has(s)}>
                {s}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span className={styles.fieldLabel}>TIMEFRAME</span>
          <select
            value={interval}
            onChange={(e) => setInterval(e.target.value)}
            className={styles.select}
          >
            {intervals.map((iv) => (
              <option key={iv.id} value={iv.id} disabled={disabledIntervals.has(iv.id)}>
                {iv.label}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span className={styles.fieldLabel}>START</span>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className={styles.input}
          />
        </label>

        <label className={styles.field}>
          <span className={styles.fieldLabel}>END</span>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className={styles.input}
          />
        </label>

        <label className={styles.field}>
          <span className={styles.fieldLabel}>INITIAL BALANCE (USDT)</span>
          <div className={styles.balanceRow}>
            <input
              type="number"
              min={100}
              step={100}
              value={initialBalance}
              onChange={(e) => setInitialBalance(Number(e.target.value))}
              className={styles.input}
            />
            <BalanceBadge source={source} balance={bybitBalance} loading={balLoading} error={balError} />
          </div>
        </label>

        <label className={`${styles.field} ${styles.fieldCheckbox}`}>
          <input
            type="checkbox"
            checked={force}
            onChange={(e) => setForce(e.target.checked)}
          />
          <span>FORCE_RECOMPUTE</span>
        </label>

        <div className={styles.fieldAction}>
          <button type="submit" disabled={submitting || !strategyId} className={styles.btnPrimary}>
            <span className={styles.btnText}>{submitting ? '⏵ EXECUTING' : '▶ EXECUTE'}</span>
            <span className={styles.btnMeta}>{submitting ? 'running...' : '~30-60s'}</span>
          </button>
        </div>
      </form>

      <div className={styles.dataInfo}>
        {dataInfo ? (
          <span className={styles.ok}>
            &#9658; DATA OK &middot; {dataInfo.bars.toLocaleString()} bars &middot; {dataInfo.start.slice(0, 10)} &rarr; {dataInfo.end.slice(0, 10)}
          </span>
        ) : (
          <span className={styles.warn}>
            &#9888; No data for {symbol} {interval}
          </span>
        )}
      </div>

      {submitError && <div className={styles.error}>{submitError}</div>}
    </div>
  )
}
