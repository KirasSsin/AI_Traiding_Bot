import { useState } from 'react'
import { ConfigureBacktest } from './components/ConfigureBacktest'
import { VerdictPanel } from './components/VerdictPanel'
import { EquityChart } from './components/EquityChart'
import { DrawdownSubchart } from './components/DrawdownSubchart'
import { MonthlyHeatmap } from './components/MonthlyHeatmap'
import type { BacktestResponse } from './api/types'
import styles from './App.module.css'

type Tab = 'backtest' | 'documentation' | 'history'

const TABS: { id: Tab; num: string; label: string }[] = [
  { id: 'backtest', num: '01', label: 'BACKTEST' },
  { id: 'documentation', num: '02', label: 'DOCUMENTATION' },
  { id: 'history', num: '03', label: 'HISTORY' },
]

export function App() {
  const [activeTab, setActiveTab] = useState<Tab>('backtest')
  const [result, setResult] = useState<BacktestResponse | null>(null)

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoMark}>◉</span>
          <div>
            <h1 className={styles.title}>
              QUANT<span className={styles.accent}>::</span>TERMINAL
            </h1>
            <p className={styles.subtitle}>
              AI TRADING BOT // BACKTEST INTERFACE // v0.1.0-alpha.46
            </p>
          </div>
        </div>
        <div className={styles.statusGroup}>
          <div className={styles.status}>
            <span className={styles.statusDot} /> SYSTEM READY
          </div>
          <div className={styles.statusMuted}>DEMO MODE · LOCALHOST · NO MAINNET</div>
        </div>
      </header>

      <nav className={styles.tabNav} role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`${styles.tabBtn} ${activeTab === tab.id ? styles.active : ''}`}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            aria-selected={activeTab === tab.id}
          >
            <span className={styles.tabNum}>{tab.num}</span>
            <span className={styles.tabLabel}>{tab.label}</span>
          </button>
        ))}
      </nav>

      <main className={styles.main}>
        {activeTab === 'backtest' && (
          <>
            <ConfigureBacktest onResult={setResult} />
            {result && <VerdictPanel result={result} />}
            {result?.equity_curve && (
              <>
                <EquityChart equityCurve={result.equity_curve} syncKey="equity-dd-sync" />
                <DrawdownSubchart equityCurve={result.equity_curve} syncKey="equity-dd-sync" />
                <MonthlyHeatmap equityCurve={result.equity_curve} />
              </>
            )}
          </>
        )}
        {activeTab === 'documentation' && (
          <div className={styles.placeholder}>
            <h2>Documentation tab</h2>
            <p>Indicators / Multipliers / Strategies / Methodology — T15</p>
          </div>
        )}
        {activeTab === 'history' && (
          <div className={styles.placeholder}>
            <h2>History tab</h2>
            <p>Cached runs table — T15</p>
          </div>
        )}
      </main>

      <footer className={styles.footer}>
        <span>QUANT::TERMINAL · S46 React migration · </span>
        <a href="https://github.com/KirasSsin/AI_Traiding_Bot" target="_blank" rel="noopener noreferrer">
          GitHub
        </a>
      </footer>
    </div>
  )
}
