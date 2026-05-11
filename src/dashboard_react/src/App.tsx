import { useState } from 'react'
import { ConfigureBacktest } from './components/forms/ConfigureBacktest'
import { VerdictPanel } from './components/metrics/VerdictPanel'
import { EquityChart } from './components/charts/EquityChart'
import { DrawdownSubchart } from './components/charts/DrawdownSubchart'
import { MonthlyHeatmap } from './components/charts/MonthlyHeatmap'
import { MetricsTable } from './components/metrics/MetricsTable'
import { TradesTable } from './components/metrics/TradesTable'
import { HistoryTab } from './components/tabs/HistoryTab'
import { DocumentationTab } from './components/tabs/DocumentationTab'
import { GlossaryTab } from './components/tabs/GlossaryTab'
import { WfaFailBanner } from './components/shared/WfaFailBanner'
import { FailAnalysisTab } from './components/shared/FailAnalysisTab'
import type { BacktestResponse, Verdict } from './api/types'

const FAILED_VERDICTS = new Set<Verdict>(['WFA_FAIL', 'WFA_FAIL_DATA', 'FAIL'])
import styles from './App.module.css'

type Tab = 'backtest' | 'documentation' | 'history' | 'glossary'

const TABS: { id: Tab; num: string; label: string }[] = [
  { id: 'backtest', num: '01', label: 'BACKTEST' },
  { id: 'documentation', num: '02', label: 'DOCUMENTATION' },
  { id: 'history', num: '03', label: 'HISTORY' },
  { id: 'glossary', num: '04', label: 'GLOSSARY' },
]

export function App() {
  const [activeTab, setActiveTab] = useState<Tab>('backtest')
  const [result, setResult] = useState<BacktestResponse | null>(null)
  // S48 T22: initialBalance wired from ConfigureBacktest (via useBybitBalance → onResult callback)
  const [initialBalance, setInitialBalance] = useState<number>(10000)

  function handleResult(response: BacktestResponse, balance: number) {
    setResult(response)
    setInitialBalance(balance)
  }

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

      <WfaFailBanner />

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
            <ConfigureBacktest onResult={handleResult} />
            {result && <VerdictPanel result={result} />}
            {result?.equity_curve && (
              <>
                <EquityChart equityCurve={result.equity_curve} syncKey="equity-dd-sync" initialBalance={initialBalance} />
                <DrawdownSubchart equityCurve={result.equity_curve} syncKey="equity-dd-sync" />
                <MonthlyHeatmap equityCurve={result.equity_curve} />
              </>
            )}
            {result && <MetricsTable result={result} />}
            {result && FAILED_VERDICTS.has(result.verdict) && (
              <FailAnalysisTab result={result} />
            )}
            {result && <TradesTable result={result} />}
          </>
        )}
        {activeTab === 'documentation' && <DocumentationTab />}
        {activeTab === 'history' && <HistoryTab />}
        {activeTab === 'glossary' && <GlossaryTab />}
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
