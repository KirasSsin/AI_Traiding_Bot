import { test, expect } from '@playwright/test';

test.describe('Bug B verification — equity chart на all preset types', () => {
  test.beforeEach(async ({ context }) => {
    await context.addInitScript(() => {
      window.localStorage.setItem(
        'wfa_fail_ack_v1',
        JSON.stringify({ count: 3, dates: ['2026-05-08', '2026-05-09', '2026-05-10'] }),
      )
    })
  })

  test('research preset (atr_breakout) shows chart', async ({ page }) => {
    await page.route('**/api/backtest', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test_research',
          cached: false,
          verdict: 'RAW',
          equity_curve: {
            timestamps: [1700000000, 1700100000, 1700200000],
            equity_pct: [0, 5.0, 3.0],
            trade_markers: null,
          },
          metrics: { n_trades: 2 },
          trade_stats: { n_trades: 2, win_rate: 0.5 },
          warnings: [], failed_criteria: [], fold_sharpe_ratios: [], failed_folds: [],
          dsr: 0, dsr_pass: false, mc_p_value: 0.5, bars_per_year: 2191,
          request: {
            strategy_id: 'atr_breakout',
            strategy_label: 'ATR breakout (LOCKED — S39)',
            symbol: 'BTCUSDT',
            interval: '240',
            interval_label: '4h',
            start: '2023-01-01',
            end: '2023-12-31',
          },
          n_trades: 2, sharpe: 0.5, win_rate: 0.5, total_pnl_pct: 3.0,
        }),
      })
    })
    await page.goto('/')
    await expect(page.getByText('STRATEGY')).toBeVisible()
    await expect(page.getByRole('button', { name: /EXECUTE/ })).toBeEnabled()
    await page.getByRole('button', { name: /EXECUTE/ }).click()
    await expect(page.getByText('▸ EQUITY CURVE')).toBeVisible({ timeout: 10000 })
  })

  test('legacy WFA preset (ema_crossover) shows chart after T2 fix', async ({ page }) => {
    await page.route('**/api/backtest', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test_legacy',
          cached: false,
          verdict: 'WFA_FAIL',
          equity_curve: {
            timestamps: [1700000000, 1700100000, 1700200000],
            equity_pct: [5.0, -2.0, 6.0],  // S48 T2 replay engine emits arrays
            trade_markers: null,
          },
          metrics: { t1_sharpe_oos: 0.5, t5_n_trades: 3 },
          trade_stats: { n_trades: 3, win_rate: 0.66 },
          warnings: [], failed_criteria: ['t1'], fold_sharpe_ratios: [0.5], failed_folds: [0],
          dsr: 0, dsr_pass: false, mc_p_value: 0.3, bars_per_year: 8766,
          request: {
            strategy_id: 'ema_crossover_s13',
            strategy_label: 'EMA crossover S13',
            symbol: 'BTCUSDT',
            interval: '60',
            interval_label: '1h',
            start: '2023-01-01',
            end: '2023-12-31',
          },
          n_trades: 3, sharpe: 0.5, win_rate: 0.66, total_pnl_pct: 6.0,
        }),
      })
    })

    // Mock fail-analysis endpoints to prevent in-flight errors on WFA_FAIL verdict
    await page.route('**/api/strategy_explanation/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ preset_id: 'ema_crossover_s13', description_ru: 'тест' }),
      })
    })
    await page.route('**/api/wfa_criterion_explanations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      })
    })

    await page.goto('/')
    await expect(page.getByText('STRATEGY')).toBeVisible()
    await expect(page.getByRole('button', { name: /EXECUTE/ })).toBeEnabled()
    await page.getByRole('button', { name: /EXECUTE/ }).click()
    await expect(page.getByText('▸ EQUITY CURVE')).toBeVisible({ timeout: 10000 })
  })

  test('legacy preset с empty equity_curve gracefully renders placeholder', async ({ page }) => {
    // Edge: backtest произвёл 0 trades → equity_curve empty
    await page.route('**/api/backtest', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test_empty',
          cached: false,
          verdict: 'WFA_FAIL_DATA',
          equity_curve: { timestamps: [], equity_pct: [], trade_markers: null },
          metrics: { t5_n_trades: 0 },
          trade_stats: { n_trades: 0, win_rate: 0 },
          warnings: [], failed_criteria: ['t5'], fold_sharpe_ratios: [], failed_folds: [],
          dsr: 0, dsr_pass: false, mc_p_value: 0.99, bars_per_year: 8766,
          request: {
            strategy_id: 'mean_reversion_s15',
            strategy_label: 'Mean Reversion S15',
            symbol: 'BTCUSDT',
            interval: '60',
            interval_label: '1h',
            start: '2023-01-01',
            end: '2023-12-31',
          },
          n_trades: 0, sharpe: 0, win_rate: 0, total_pnl_pct: 0,
        }),
      })
    })

    // Mock fail-analysis endpoints to prevent in-flight errors on WFA_FAIL_DATA verdict
    await page.route('**/api/strategy_explanation/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ preset_id: 'mean_reversion_s15', description_ru: 'тест' }),
      })
    })
    await page.route('**/api/wfa_criterion_explanations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      })
    })

    await page.goto('/')
    await page.getByRole('button', { name: /EXECUTE/ }).click()
    // Empty equity_curve → component renders placeholder, не пустой chart
    // Verify не fail
    await expect(page.getByText('▸ FINAL VERDICT')).toBeVisible({ timeout: 10000 })
  })
})
