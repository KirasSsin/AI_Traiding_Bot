// DocumentationTab — T15b: indicators/multipliers/strategies/methodology cards.
// Vanilla port: src/dashboard/static/dashboard.js lines 567-702 (loadDocs + render*).
// Fetches /api/docs on mount; renders 4 sections in vertical stack.
//
// XSS-safety note: HTML fields (description, formula, entry_logic, etc.) come from
// server-side authored dicts (not user input) — dangerouslySetInnerHTML is intentional.
// Plain-text fields are interpolated directly (React auto-escapes).

import { useState, useEffect } from 'react'
import { api } from '@/api/client'
import type {
  DocsEnvelope,
  IndicatorDoc,
  MultiplierDoc,
  StrategyDoc,
  MethodologyDoc,
} from '@/api/types'
import styles from './DocumentationTab.module.css'

// ─── Indicator cards ──────────────────────────────────────────────────────

function IndicatorCard({ ind }: { ind: IndicatorDoc }) {
  const hasParams = Object.keys(ind.params_in_strategies).length > 0

  return (
    <article className={styles.docCard}>
      <div className={styles.cardHeader}>
        <div>
          <div className={styles.cardName}>{ind.name}</div>
          <div className={styles.cardFullname}>{ind.full_name}</div>
        </div>
        <div className={styles.categoryChip}>{ind.category}</div>
      </div>
      <div className={styles.cardAuthor}>{ind.author}</div>
      {/* description may contain <strong>/<em> HTML from server — intentional */}
      <p dangerouslySetInnerHTML={{ __html: ind.description }} />
      <div className={styles.formulaBlock}>{ind.formula}</div>
      <div className={styles.cardSection}>
        <h4>Range</h4>
        <p>{ind.range}</p>
      </div>
      {ind.interpretation.length > 0 && (
        <div className={styles.cardSection}>
          <h4>Interpretation</h4>
          <ul>
            {ind.interpretation.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {hasParams && (
        <div className={styles.cardSection}>
          <h4>Параметры в стратегиях</h4>
          <table className={styles.paramsTable}>
            <tbody>
              {Object.entries(ind.params_in_strategies).map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className={styles.cardSource}>{ind.source}</div>
    </article>
  )
}

// ─── Multiplier cards ─────────────────────────────────────────────────────

function MultiplierCard({ mul }: { mul: MultiplierDoc }) {
  return (
    <article className={styles.docCard}>
      <div className={styles.cardHeader}>
        <div>
          <div className={styles.cardName}>{mul.name}</div>
          {/* id + default are plain text — auto-escaped */}
          <div className={styles.cardFullname}>
            <code>{mul.id}</code> · default = {mul.default}
          </div>
        </div>
      </div>
      {/* description may contain HTML — intentional */}
      <p dangerouslySetInnerHTML={{ __html: mul.description }} />
      <div className={styles.cardSection}>
        <h4>Tradeoff</h4>
        {/* tradeoff may contain HTML — intentional */}
        <p className={styles.tradeoffText} dangerouslySetInnerHTML={{ __html: mul.tradeoff }} />
      </div>
      {/* TODO S47 — full vanilla parity for multipliers details (range, impact table) */}
    </article>
  )
}

// ─── Strategy cards ───────────────────────────────────────────────────────

function StrategyCard({ strat }: { strat: StrategyDoc }) {
  const hasParams = Object.keys(strat.key_params).length > 0

  return (
    <article className={styles.strategyCard}>
      <div className={styles.strategyMain}>
        <div className={styles.strategyCategory}>{strat.category}</div>
        <div className={styles.strategyName}>{strat.name}</div>
        {/* tagline may contain HTML — intentional */}
        <div
          className={styles.strategyTagline}
          dangerouslySetInnerHTML={{ __html: strat.tagline }}
        />
        <div className={styles.strategySection}>
          <h5>Entry logic</h5>
          {/* entry_logic may contain HTML — intentional */}
          <p dangerouslySetInnerHTML={{ __html: strat.entry_logic }} />
        </div>
        <div className={styles.strategySection}>
          <h5>Exit logic</h5>
          {/* exit_logic may contain HTML — intentional */}
          <p dangerouslySetInnerHTML={{ __html: strat.exit_logic }} />
        </div>
        <div className={styles.strategySection}>
          <h5>Historical results</h5>
          {/* historical_results may contain HTML — intentional */}
          <div dangerouslySetInnerHTML={{ __html: strat.historical_results }} />
        </div>
        <div className={styles.strategySection}>
          <h5>Best for</h5>
          {/* best_for may contain HTML — intentional */}
          <div dangerouslySetInnerHTML={{ __html: strat.best_for }} />
        </div>
      </div>
      <aside className={styles.strategyAside}>
        {strat.indicators_used.length > 0 && (
          <>
            <h5>Indicators used</h5>
            <div className={styles.indicatorChips}>
              {strat.indicators_used.map((x) => (
                <span key={x} className={styles.indicatorChip}>{x}</span>
              ))}
            </div>
          </>
        )}
        {hasParams && (
          <>
            <h5>Key parameters</h5>
            <table className={styles.paramsTable}>
              <tbody>
                {Object.entries(strat.key_params).map(([k, v]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
        {strat.academic_reference && (
          <div className={styles.academicRef}>{strat.academic_reference}</div>
        )}
      </aside>
    </article>
  )
}

// ─── Methodology cards ────────────────────────────────────────────────────

function MethodologyCard({ meth }: { meth: MethodologyDoc }) {
  const hasCriteria = meth.criteria && meth.criteria.length > 0

  return (
    <article className={styles.docCard}>
      {(meth.name || meth.purpose) && (
        <div className={styles.cardHeader}>
          <div>
            {meth.name && <div className={styles.cardName}>{meth.name}</div>}
            {meth.purpose && <div className={styles.cardFullname}>{meth.purpose}</div>}
          </div>
        </div>
      )}
      {/* description may contain HTML — intentional */}
      {meth.description && (
        <p dangerouslySetInnerHTML={{ __html: meth.description }} />
      )}
      {meth.formula && (
        <div className={styles.formulaBlock}>{meth.formula}</div>
      )}
      {/* params may contain HTML — intentional */}
      {meth.params && (
        <div className={styles.cardSection}>
          <h4>Params</h4>
          <p dangerouslySetInnerHTML={{ __html: meth.params }} />
        </div>
      )}
      {meth.interpretation && meth.interpretation.length > 0 && (
        <div className={styles.cardSection}>
          <h4>Interpretation</h4>
          <ul>
            {meth.interpretation.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {hasCriteria && (
        <div className={styles.cardSection}>
          <h4>Criteria</h4>
          <table className={styles.paramsTable}>
            <tbody>
              {(meth.criteria ?? []).map((c, idx) => (
                <tr key={idx}>
                  <td><strong>{c.id}</strong> · {c.metric}</td>
                  <td>
                    {c.threshold}
                    {c.note && (
                      /* note may contain HTML — intentional */
                      <span
                        className={styles.criteriaNote}
                        dangerouslySetInnerHTML={{ __html: c.note }}
                      />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {meth.source && (
        <div className={styles.cardSource}>{meth.source}</div>
      )}
      {/* TODO S47 — full vanilla parity for methodology details */}
    </article>
  )
}

// ─── Section wrapper ──────────────────────────────────────────────────────

function DocSection({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className={styles.section}>
      <div className={styles.sectionTitle}>{title}</div>
      <div className={styles.cardsGrid}>{children}</div>
    </div>
  )
}

// ─── public component ────────────────────────────────────────────────────

export function DocumentationTab() {
  const [docs, setDocs] = useState<DocsEnvelope | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api.getDocs()
      .then((data) => { if (!cancelled) setDocs(data) })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load documentation')
        }
      })
    return () => { cancelled = true }
  }, [])

  // Loading state
  if (docs === null && error === null) {
    return (
      <section className={styles.container}>
        <div className={styles.title}>▸ DOCUMENTATION</div>
        <p className={styles.stateMsg}>Loading documentation...</p>
      </section>
    )
  }

  // Error state
  if (error !== null) {
    return (
      <section className={styles.container}>
        <div className={styles.title}>▸ DOCUMENTATION</div>
        <p className={styles.stateMsgError}>Failed to load documentation</p>
      </section>
    )
  }

  const d = docs!

  return (
    <section className={styles.container}>
      <div className={styles.title}>▸ DOCUMENTATION</div>

      {d.indicators.length > 0 && (
        <DocSection title="INDICATORS">
          {d.indicators.map((ind) => (
            <IndicatorCard key={ind.name} ind={ind} />
          ))}
        </DocSection>
      )}

      {d.multipliers.length > 0 && (
        <DocSection title="MULTIPLIERS">
          {d.multipliers.map((mul) => (
            <MultiplierCard key={mul.id} mul={mul} />
          ))}
        </DocSection>
      )}

      {d.strategies.length > 0 && (
        <DocSection title="STRATEGIES">
          {d.strategies.map((strat, idx) => (
            <StrategyCard key={`${strat.name}-${idx}`} strat={strat} />
          ))}
        </DocSection>
      )}

      {d.methodology.length > 0 && (
        <DocSection title="METHODOLOGY">
          {d.methodology.map((meth, idx) => (
            <MethodologyCard key={idx} meth={meth} />
          ))}
        </DocSection>
      )}
    </section>
  )
}
