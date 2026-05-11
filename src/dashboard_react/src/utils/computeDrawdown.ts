/**
 * Compute drawdown series from cumulative equity_pct.
 * Returns negative percent values (peak-to-trough). Always ≤ 0.
 */
export function computeDrawdown(equityPct: number[]): number[] {
  const result = new Array<number>(equityPct.length)
  let peak = -Infinity
  for (let i = 0; i < equityPct.length; i++) {
    // Convert cumulative % to multiplier: e.g. 12 → 1.12
    const v = (equityPct[i] ?? 0) / 100 + 1
    if (v > peak) peak = v
    // Drawdown as negative percent: (current - peak) / peak * 100
    result[i] = peak > 0 ? ((v - peak) / peak) * 100 : 0
  }
  return result
}
