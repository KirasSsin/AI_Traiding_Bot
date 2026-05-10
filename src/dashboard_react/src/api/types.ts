// S46 T4 — TypeScript types для FastAPI backend responses
// Mirror Python BacktestRequest + envelope structure (S43 + S44 + S45)

export interface StrategyMetadata {
  id: string
  label: string
  type: string
  description: string
  optgroup: string
  supported_combos?: [string, string][]
  locked_symbol?: string | null
  locked_interval?: string | null
}

export interface IntervalLabel {
  id: string
  label: string
}

export interface DataAvailabilityEntry {
  bars: number
  start: string
  end: string
}

export interface DataAvailability {
  [symbol: string]: {
    [interval: string]: DataAvailabilityEntry
  }
}

export interface BacktestRequest {
  strategy_id: string
  symbol: string
  interval: string
  start: string
  end: string
  force?: boolean
}

export interface Warning {
  level: 'high' | 'warn' | 'info'
  code: string
  message: string
}

export interface EquityCurve {
  timestamps: number[]
  equity_pct: number[]
}

export interface WfaParams {
  train_bars: number
  test_bars: number
  k_folds: number
  embargo_bars: number
  min_required: number
  actual: number
}

export interface TradeStats {
  n_trades: number
  win_rate: number
}

export type Verdict = 'WFA_PASS' | 'WFA_FAIL' | 'WFA_FAIL_DATA' | 'PASS' | 'FAIL' | 'RAW'

export interface BacktestRequestEcho {
  strategy_id: string
  strategy_label: string
  symbol: string
  interval: string
  interval_label: string
  start: string
  end: string
}

export interface BacktestResponse {
  run_id: string
  cached: boolean
  request: BacktestRequestEcho
  verdict: Verdict
  failed_criteria: string[]
  warnings: Warning[]
  equity_curve: EquityCurve
  bars_per_year: number
  acceptance_gate: string | null
  dsr: number | null
  dsr_pass: boolean | null
  mc_p_value: number | null
  metrics: Record<string, number>
  trade_stats: TradeStats
  wfa_params: WfaParams | null
  wfa_total_bars: number
  fold_sharpe_ratios: number[]
  failed_folds: number[]
  trades_dump: unknown[]
  n_trades: number
  sharpe: number
  win_rate: number
  total_pnl_pct: number
  runner: string
}

export interface RunSummary {
  run_id: string
  cached: boolean
  request: BacktestRequestEcho
  verdict: Verdict
  metrics: Record<string, number>
  dsr: number | null
  mc_p_value: number | null
  total_pnl_pct: number
  n_trades: number
  sharpe: number
  win_rate: number
}
