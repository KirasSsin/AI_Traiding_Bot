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

// T11 — per-trade entry/exit markers для EquityChart scatter overlay
export interface TradeMarkers {
  entry_timestamps: number[]
  exit_timestamps: number[]
  entry_prices: number[]
  exit_prices: number[]
  pnl_pcts: number[]
}

export interface EquityCurve {
  timestamps: number[]
  equity_pct: number[]
  trade_markers?: TradeMarkers | null  // T11 — absent/null when no trades
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
  // Core counts (always present)
  n_trades: number
  win_rate: number
  // S47 T13 — derived from trades_list (research path) OR full (replay path)
  n_winners?: number | null
  n_losers?: number | null
  total_pnl_pct?: number | null
  // Quote-currency fields — replay path only (research path = null)
  total_pnl_quote?: number | null
  total_commissions_quote?: number | null
  avg_win_quote?: number | null
  avg_loss_quote?: number | null
  profit_factor?: number | null
}

// Documentation tab types (T15b — /api/docs envelope)
export interface IndicatorDoc {
  name: string
  full_name: string
  category: string
  author: string
  description: string       // HTML — use dangerouslySetInnerHTML
  formula: string
  range: string
  interpretation: string[]
  params_in_strategies: Record<string, string>
  source: string
}

export interface MultiplierDoc {
  name: string
  id: string
  default: number | string
  description: string       // HTML — use dangerouslySetInnerHTML
  tradeoff: string          // HTML — use dangerouslySetInnerHTML
}

export interface StrategyDoc {
  category: string
  name: string
  tagline: string           // HTML — use dangerouslySetInnerHTML
  entry_logic: string       // HTML — use dangerouslySetInnerHTML
  exit_logic: string        // HTML — use dangerouslySetInnerHTML
  historical_results: string // HTML — use dangerouslySetInnerHTML
  best_for: string          // HTML — use dangerouslySetInnerHTML
  indicators_used: string[]
  key_params: Record<string, string | number>
  academic_reference: string
}

export interface MethodologyCriteria {
  id: string
  metric: string
  threshold: string
  note: string              // HTML — use dangerouslySetInnerHTML
}

export interface MethodologyDoc {
  name?: string
  purpose?: string
  source?: string
  description?: string      // HTML — use dangerouslySetInnerHTML
  formula?: string
  params?: string           // HTML — use dangerouslySetInnerHTML
  interpretation?: string[]
  criteria?: MethodologyCriteria[]
}

export interface DocsEnvelope {
  indicators: IndicatorDoc[]
  multipliers: MultiplierDoc[]
  strategies: StrategyDoc[]
  methodology: MethodologyDoc[]
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

// S47 T15 — Fail Analysis tab types
export interface CriterionExplanation {
  name: string
  measures: string
  formula: string
  threshold: string
  impact: string
  related: string
  gate_role: string
}

export interface StrategyExplanation {
  preset_id: string
  description_ru: string
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

// S48 T15 — Glossary tab types (Bug E core)
export interface GlossaryEntry {
  section: string
  description_ru: string
  applies_to: string[]
  adr_ref?: string | null
}

export interface GlossaryResponse {
  entries: Record<string, GlossaryEntry>
  strategy_to_metrics: Record<string, string[]>
  sections: string[]
}
