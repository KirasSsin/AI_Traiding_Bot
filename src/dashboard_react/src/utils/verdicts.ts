// Shared verdict classification — single source of truth для research-vs-WFA dispatch.
// Prevents drift: каждый RAW dispatch site должен использовать RESEARCH_VERDICTS,
// иначе новые research-verdicts (S52 RAW_PRETRAIN_LEAKAGE_SUSPECTED) falls through к
// WFA-gate branch → misrenders as failed acceptance gate (S55 HIGH DASH-01).
//
// Research (non-gated) verdicts: full-period backtests без WFA OOS discipline.
//   - RAW                            — research presets (atr_breakout/volume_breakout)
//   - RAW_PRETRAIN_LEAKAGE_SUSPECTED — Kronos ML exploratory (S52 honest leakage label)
//
// Эти verdicts НЕ являются failed WFA gates — они exploratory, рендерятся как
// reduced/research view, не red-fail acceptance gate.

import type { Verdict } from '@/api/types'

export const RESEARCH_VERDICTS: ReadonlySet<Verdict> = new Set<Verdict>([
  'RAW',
  'RAW_PRETRAIN_LEAKAGE_SUSPECTED',
])

// True если verdict — research (non-gated). Null/undefined → false (treated as WFA).
export function isResearchVerdict(verdict: Verdict | null | undefined): boolean {
  return verdict != null && RESEARCH_VERDICTS.has(verdict)
}
