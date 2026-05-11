import type {
  StrategyMetadata,
  IntervalLabel,
  DataAvailability,
  BacktestRequest,
  BacktestResponse,
  RunSummary,
  DocsEnvelope,
  StrategyExplanation,
  CriterionExplanation,
  GlossaryResponse,
  BalanceResponse,
} from './types'

const BASE_URL = ''  // same-origin (FastAPI serves React build per architect C1+C4)

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`HTTP ${status}: ${detail}`)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const errJson = await res.json() as { detail?: string }
      if (errJson.detail) detail = errJson.detail
    } catch {
      // body не JSON — keep statusText
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  getStrategies: (): Promise<Record<string, StrategyMetadata>> =>
    request('/api/strategies'),

  getStrategyInfo: (id: string): Promise<StrategyMetadata> =>
    request(`/api/strategy/${id}/info`),

  getIntervals: (): Promise<IntervalLabel[]> => request('/api/intervals'),

  getDataAvailability: (): Promise<DataAvailability> =>
    request('/api/data/availability'),

  runBacktest: (payload: BacktestRequest): Promise<BacktestResponse> =>
    request('/api/backtest', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getRuns: (): Promise<RunSummary[]> => request('/api/runs'),

  getRun: (runId: string): Promise<BacktestResponse> =>
    request(`/api/runs/${runId}`),

  getDocs: (): Promise<DocsEnvelope> => request('/api/docs'),

  // S47 T15 — Fail Analysis tab
  getStrategyExplanation: (presetId: string): Promise<StrategyExplanation> =>
    request(`/api/strategy_explanation/${encodeURIComponent(presetId)}`),

  getCriterionExplanations: (): Promise<Record<string, CriterionExplanation>> =>
    request('/api/wfa_criterion_explanations'),

  // S48 T15 — Glossary tab (Bug E core)
  getGlossary: (): Promise<GlossaryResponse> => request('/api/glossary'),

  // S48 T20 — Bybit balance
  getBalance: (): Promise<BalanceResponse> => request('/api/bybit/balance'),
}
