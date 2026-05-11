// GlossaryTab — S48 T15-T17 (Bug E core).
// RU расшифровка всех аббревиатур + dynamic per-strategy filter (T16) + search (T17).
// Architecture: section-based с sticky TOC. URL query state per architect C2.
//
// NOTE T15: import of `useStrategyContext` from `@/hooks/useStrategyContext` —
// hook is T18 deliverable, file does NOT exist yet. TypeScript/lint will error
// here until T18 lands; final integration verify в T19. Plan explicitly defers
// build verification к T19.

import { useEffect, useState, useMemo } from 'react'
import { api } from '@/api/client'
import type { GlossaryResponse, GlossaryEntry } from '@/api/types'
import { useStrategyContext } from '@/hooks/useStrategyContext'
import styles from './GlossaryTab.module.css'

const SECTION_LABELS: Record<string, string> = {
  verdict_status: 'Вердикты и символы статуса',
  gate_blocking_metrics: 'Gate-blocking metrics',
  informational_metrics: 'Informational metrics',
  trade_statistics: 'Торговая статистика',
  chart_vocabulary: 'Графики',
  monthly_heatmap: 'Heatmap по месяцам',
  warnings: 'Предупреждения',
  strategy_presets: 'Пресеты стратегий',
}

export function GlossaryTab() {
  const [glossary, setGlossary] = useState<GlossaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const { currentStrategy } = useStrategyContext()

  useEffect(() => {
    let cancelled = false
    api.getGlossary()
      .then((data) => {
        if (cancelled) return
        setGlossary(data)
        setLoading(false)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setError(err.message)
        setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  // Group entries by section (memoized)
  const entriesBySection = useMemo(() => {
    if (glossary === null) return {}
    const grouped: Record<string, Array<[string, GlossaryEntry]>> = {}
    for (const [term, entry] of Object.entries(glossary.entries)) {
      const section = entry.section
      if (!(section in grouped)) grouped[section] = []
      grouped[section]!.push([term, entry])
    }
    return grouped
  }, [glossary])

  // Applicable terms set per current strategy (T16)
  // Edge case: strategy selected but not in strategy_to_metrics map → treat as null (show all + warn)
  const applicableTerms = useMemo(() => {
    if (glossary === null || currentStrategy === null) return null
    const list = glossary.strategy_to_metrics[currentStrategy]
    if (list === undefined) {
      console.warn(`Glossary: strategy "${currentStrategy}" not in map — showing all entries`)
      return null
    }
    return new Set(list)
  }, [glossary, currentStrategy])

  // Filtered entries по search query (T17). Empty query → return per-section grouping.
  // Non-empty → flat results под единым ключом "search_results".
  const filteredEntries = useMemo(() => {
    if (glossary === null) return {} as Record<string, Array<[string, GlossaryEntry]>>
    const q = searchQuery.trim().toLowerCase()
    if (q === '') return entriesBySection
    const results: Array<[string, GlossaryEntry]> = []
    for (const [term, entry] of Object.entries(glossary.entries)) {
      if (term.toLowerCase().includes(q) || entry.description_ru.toLowerCase().includes(q)) {
        results.push([term, entry])
      }
    }
    return { search_results: results }
  }, [glossary, searchQuery, entriesBySection])

  // Anchor scroll on mount если location.hash present
  useEffect(() => {
    if (loading || glossary === null) return
    const hash = window.location.hash
    if (!hash.startsWith('#glossary-')) return
    const anchorId = hash.slice(1)
    setTimeout(() => {
      const el = document.getElementById(anchorId)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        el.classList.add(styles.entryHighlightPulse ?? '')
        setTimeout(() => el.classList.remove(styles.entryHighlightPulse ?? ''), 1500)
      }
    }, 200)
  }, [loading, glossary])

  if (loading) return <div className={styles.loading}>Загрузка глоссария...</div>
  if (error !== null) return <div className={styles.error}>Ошибка: {error}</div>
  if (glossary === null) return null

  return (
    <div className={styles.container}>
      <div className={styles.title}>▸ ГЛОССАРИЙ — РУССКИЕ ОБОЗНАЧЕНИЯ</div>

      <div className={styles.filterHeader}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Поиск по term или описанию..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {currentStrategy !== null && searchQuery.trim() === '' && (
          <span className={styles.filterHint}>
            Filter: <strong>{currentStrategy}</strong> — выделены применимые termы
          </span>
        )}
        {searchQuery.trim() !== '' && (
          <span className={styles.filterHint}>
            Поиск: <strong>"{searchQuery.trim()}"</strong>
          </span>
        )}
      </div>

      <div className={styles.layout}>
        {/* Sticky TOC — hidden during search (results — flat single section) */}
        {searchQuery.trim() === '' && (
          <nav className={styles.toc}>
            <h4 className={styles.tocTitle}>Содержание</h4>
            <ul>
              {glossary.sections.map((section) => (
                <li key={section}>
                  <a href={`#section-${section}`} className={styles.tocLink}>
                    {SECTION_LABELS[section] ?? section}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        )}

        {/* Sections — branch on search mode */}
        <div className={styles.sections}>
          {searchQuery.trim() !== '' ? (
            // Search mode: single flat section "Результаты поиска".
            // Design choice: keep applicable highlighting в search results тоже,
            // т.к. user может искать term для текущей стратегии (filter context useful).
            <section id="section-search-results" className={styles.section}>
              <h3 className={styles.sectionTitle}>
                Результаты поиска ({filteredEntries.search_results?.length ?? 0})
              </h3>
              {(filteredEntries.search_results ?? []).map(([term, entry]) => {
                const isApplicable = applicableTerms === null || applicableTerms.has(term)
                return (
                  <article
                    key={term}
                    id={`glossary-${term}`}
                    className={`${styles.entry} ${isApplicable ? styles.entryApplicable : styles.entryDimmed}`}
                  >
                    <div className={styles.entryHeader}>
                      <span className={styles.entryTerm}>{term}</span>
                      {entry.adr_ref && <span className={styles.entryAdrRef}>{entry.adr_ref}</span>}
                    </div>
                    <p className={styles.entryDescription}>{entry.description_ru}</p>
                    <div className={styles.entryAppliesTo}>
                      Используется в: {entry.applies_to.includes('*') ? 'все стратегии' : entry.applies_to.join(', ')}
                    </div>
                  </article>
                )
              })}
              {(filteredEntries.search_results ?? []).length === 0 && (
                <div className={styles.loading}>Ничего не найдено</div>
              )}
            </section>
          ) : (
            glossary.sections.map((section) => {
              const entries = entriesBySection[section] ?? []
              if (entries.length === 0) return null
              return (
                <section key={section} id={`section-${section}`} className={styles.section}>
                  <h3 className={styles.sectionTitle}>{SECTION_LABELS[section] ?? section}</h3>
                  {entries.map(([term, entry]) => {
                    const isApplicable = applicableTerms === null || applicableTerms.has(term)
                    return (
                      <article
                        key={term}
                        id={`glossary-${term}`}
                        className={`${styles.entry} ${isApplicable ? styles.entryApplicable : styles.entryDimmed}`}
                      >
                        <div className={styles.entryHeader}>
                          <span className={styles.entryTerm}>{term}</span>
                          {entry.adr_ref && <span className={styles.entryAdrRef}>{entry.adr_ref}</span>}
                        </div>
                        <p className={styles.entryDescription}>{entry.description_ru}</p>
                        <div className={styles.entryAppliesTo}>
                          Используется в: {entry.applies_to.includes('*') ? 'все стратегии' : entry.applies_to.join(', ')}
                        </div>
                      </article>
                    )
                  })}
                </section>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
