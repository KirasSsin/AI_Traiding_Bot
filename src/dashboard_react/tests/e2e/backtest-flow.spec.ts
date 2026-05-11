import { test, expect } from '@playwright/test';

// Pre-seed 3 distinct days so WFA banner is in chip mode — doesn't block the form
const WFA_ACK_SEEDED = JSON.stringify({
  count: 3,
  dates: ['2026-05-07', '2026-05-08', '2026-05-09'],
});

test.describe('Backtest flow', () => {
  test('form renders with STRATEGY/SYMBOL/TIMEFRAME selects and EXECUTE button', async ({ page, context }) => {
    await context.addInitScript(() => {
      window.localStorage.setItem('wfa_fail_ack_v1', WFA_ACK_SEEDED);
    });
    await page.goto('/');

    // Form section label visible
    await expect(page.getByText('> CONFIGURE_BACKTEST')).toBeVisible();

    // All three field labels render after API data loads
    await expect(page.getByText('STRATEGY')).toBeVisible();
    await expect(page.getByText('SYMBOL')).toBeVisible();
    await expect(page.getByText('TIMEFRAME')).toBeVisible();

    // Execute button visible and enabled (strategyId populated after API load)
    const executeBtn = page.getByRole('button', { name: /EXECUTE/ });
    await expect(executeBtn).toBeVisible();
    await expect(executeBtn).toBeEnabled();
  });

  test('user submits form, mocked /api/backtest returns WFA_FAIL → VerdictPanel + EquityChart visible', async ({ page, context }) => {
    await context.addInitScript(() => {
      // Pre-ack WFA banner so it doesn't block form
      window.localStorage.setItem(
        'wfa_fail_ack_v1',
        JSON.stringify({ count: 3, dates: ['2026-05-08', '2026-05-09', '2026-05-10'] }),
      )
    })

    // Stub /api/backtest response — minimal envelope с WFA_FAIL verdict
    await page.route('**/api/backtest', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test_run_e2e',
          cached: false,
          verdict: 'WFA_FAIL',
          failed_criteria: ['t1', 't5'],
          warnings: [{ level: 'high', code: 'wfa_fail', message: 'Test failure' }],
          metrics: {
            t1_sharpe_oos: 0.5,
            t3_max_drawdown: 0.18,
            t5_n_trades: 80,
            t5_t_stat: 1.2,
          },
          trade_stats: { n_trades: 80, win_rate: 0.45 },
          dsr: 0.3,
          dsr_pass: false,
          mc_p_value: 0.12,
          fold_sharpe_ratios: [0.4, 0.6, 0.5],
          failed_folds: [0, 2],
          bars_per_year: 8766,
          equity_curve: {
            timestamps: [1700000000, 1700100000, 1700200000, 1700300000],
            equity_pct: [0, 5, -2, 3],
            trade_markers: null,
          },
          request: {
            strategy_id: 'ema_crossover_s13',
            strategy_label: 'EMA crossover S13',
            symbol: 'BTCUSDT',
            interval: '60',
            interval_label: '1h',
            start: '2023-01-01',
            end: '2023-12-31',
          },
          n_trades: 80,
          sharpe: 0.5,
          win_rate: 0.45,
          total_pnl_pct: 6.0,
        }),
      })
    })

    // S47 T15 added FailAnalysisTab fetching explanation endpoints when verdict ∈ FAILED.
    // Mock both к prevent in-flight fetch errors during test teardown.
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
    // Wait for strategies dropdown к hydrate (api/strategies returns) — submit no-op otherwise
    await expect(page.getByRole('button', { name: /EXECUTE/ })).toBeEnabled()

    const executeBtn = page.getByRole('button', { name: /EXECUTE/ })
    await executeBtn.click()

    // Verdict panel renders с WFA_FAIL
    await expect(page.getByText('▸ FINAL VERDICT')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('WFA_FAIL', { exact: true })).toBeVisible()

    // EquityChart title appears
    await expect(page.getByText('▸ EQUITY CURVE')).toBeVisible()

    // Failed criteria chips (scoped to FAILED CRITERIA row to avoid strict mode conflicts)
    const failedRow = page.getByText('FAILED CRITERIA:').locator('..')
    await expect(failedRow.getByText('T1', { exact: true })).toBeVisible()
    await expect(failedRow.getByText('T5', { exact: true })).toBeVisible()
  })
});
